"""
RconClient - Cliente RCON para comunicação com o mod scum_rcon (protocolo Source RCON).
"""
import re
import socket
import struct
import time
from typing import Any, List, Optional, Tuple


PACKET_TYPE_AUTH = 3
PACKET_TYPE_AUTH_RESPONSE = 2
PACKET_TYPE_EXECCOMMAND = 2
PACKET_TYPE_RESPONSE_VALUE = 0
RCON_AUTH_FAILED_ID = -1


class RconError(Exception):
    """Erro de comunicação RCON."""
    pass


class RconAuthError(RconError):
    """Falha na autenticação RCON."""
    pass


def is_rcon_tick_frozen(response: Optional[str]) -> bool:
    """
    Detecta se a resposta do RCON indica que a Game Thread (tick) do SCUM Server
    está parada/congelada ou sofreu timeout de execução.
    """
    if response is None:
        return True
    text = str(response).strip().lower()
    if not text:
        return True
    freeze_markers = (
        "sem resposta",
        "tick do jogo",
        "circuit_breaker_open",
        "server still starting",
        "socket timeout",
    )
    return any(marker in text for marker in freeze_markers)


def is_rcon_error_response(response: Optional[str], allow_empty: bool = False) -> bool:
    """
    Verifica se o corpo de resposta de um comando RCON indica falha de execução.
    """
    if response is None:
        return True
    text = str(response).strip()
    if not text:
        return not allow_empty
    lower = text.lower()
    if lower.startswith("erro:") or lower.startswith("error:"):
        return True
    error_markers = (
        "sem resposta",
        "tick do jogo",
        "circuit_breaker_open",
        "not online",
        "player not found",
        "server still starting",
        "unknown command",
        "failed to",
    )
    return any(marker in lower for marker in error_markers)



class RconClient:
    """
    Cliente RCON compatível com o protocolo Source RCON.
    Compatível com o mod scum_rcon (UE4SS).

    Uso:
        client = RconClient("127.0.0.1", 28015, "senha")
        client.connect()
        response = client.send_command("ListPlayers")
        client.close()

    Ou como context manager:
        with RconClient("127.0.0.1", 28015, "senha") as client:
            response = client.send_command("ListPlayers")
    """

    def __init__(self, ip: str, port: int, password: str, timeout: float = 5.0):
        self.ip = ip
        self.port = int(port)
        self.password = password
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._req_id = 1

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "RconClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Primitivas de baixo nível
    # ------------------------------------------------------------------

    def _build_packet(self, req_id: int, pkt_type: int, body: str) -> bytes:
        encoded = body.encode("utf-8")
        # size = req_id (4) + type (4) + body + null terminator (1) + padding (1)
        size = 4 + 4 + len(encoded) + 2
        packet = struct.pack(f"<iii{len(encoded)}sBB", size, req_id, pkt_type, encoded, 0, 0)
        return packet

    def _read_packet(self) -> Tuple[int, int, str]:
        """Reads a packet from the socket. Returns (req_id, pkt_type, body)."""
        if not self._sock:
            raise RconError("Socket not connected.")

        # Read packet size (4 bytes)
        size_data = self._recv_exactly(4)
        size = struct.unpack("<i", size_data)[0]

        # Read remaining packet data
        data = self._recv_exactly(size)
        if len(data) < 8:
            raise RconError(f"Packet too short ({len(data)} bytes).")

        req_id, pkt_type = struct.unpack("<ii", data[:8])
        body = data[8:-2].decode("utf-8", errors="ignore").strip("\x00")
        return req_id, pkt_type, body

    def _recv_exactly(self, n: int) -> bytes:
        """Reads exactly n bytes from the socket."""
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise RconError("Connection closed by server during read.")
            buf += chunk
        return buf

    def _next_id(self) -> int:
        self._req_id += 1
        if self._req_id > 65535:
            self._req_id = 2
        return self._req_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connects to the RCON server and authenticates."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        try:
            self._sock.connect((self.ip, self.port))
        except Exception as e:
            self._sock = None
            import sys
            import errno
            err_msg = str(e)
            if hasattr(e, 'errno') and e.errno is not None:
                if e.errno == errno.ECONNREFUSED or (sys.platform == 'win32' and e.errno == 10061):
                    err_msg = "Connection refused by the target machine"
                elif e.errno == errno.ETIMEDOUT or (sys.platform == 'win32' and e.errno == 10060):
                    err_msg = "Connection timed out"
            raise RconError(f"Could not connect to {self.ip}:{self.port} — {err_msg}") from e

        self._authenticate()

    def _authenticate(self) -> None:
        auth_id = 999  # Fixed authentication ID
        auth_pkt = self._build_packet(auth_id, PACKET_TYPE_AUTH, self.password)
        self._sock.sendall(auth_pkt)

        # The mod can send up to 2 packets during authentication
        for _ in range(3):
            try:
                req_id, pkt_type, body = self._read_packet()
            except socket.timeout:
                raise RconAuthError("Timeout waiting for authentication response.")

            if pkt_type == PACKET_TYPE_AUTH_RESPONSE:
                if req_id == RCON_AUTH_FAILED_ID:
                    raise RconAuthError("Incorrect RCON password.")
                if req_id == auth_id:
                    return  # successfully authenticated

        raise RconAuthError("Unexpected authentication response.")

    def send_command(self, command: str, delay_after: float = 0.1, origin: str = "SYSTEM") -> str:
        """
        Sends a command and returns the response as string.

        Args:
            command: Command to send (e.g. "ListPlayers").
            delay_after: Delay in seconds after sending before reading response.
            origin: Origin tag for logging (e.g. "SHOP", "DISCORD", "SYSTEM").

        Returns:
            Server response text.
        """
        from utils.rcon_logger import RconLogger
        rcon_log = RconLogger.get_instance()
        t_start = time.perf_counter()

        if not self._sock:
            err_msg = "Not connected. Call connect() first."
            rcon_log.log_error(command=command, error=err_msg, origin=origin)
            raise RconError(err_msg)

        try:
            req_id = self._next_id()
            pkt = self._build_packet(req_id, PACKET_TYPE_EXECCOMMAND, command)
            self._sock.sendall(pkt)

            if delay_after > 0:
                time.sleep(delay_after)

            resp_id, _, body = self._read_packet()
            duration_ms = (time.perf_counter() - t_start) * 1000.0
            is_lp = command.strip().lower() == "listplayers"
            is_err = is_rcon_error_response(body, allow_empty=is_lp)
            rcon_log.log_command(
                command=command,
                response=body,
                duration_ms=duration_ms,
                origin=origin,
                success=not is_err,
            )
            return body
        except socket.timeout as e:
            duration_ms = (time.perf_counter() - t_start) * 1000.0
            rcon_log.log_error(command=command, error=f"Socket timeout: {e}", duration_ms=duration_ms, origin=origin)
            return ""
        except Exception as e:
            duration_ms = (time.perf_counter() - t_start) * 1000.0
            rcon_log.log_error(command=command, error=str(e), duration_ms=duration_ms, origin=origin)
            raise


    def close(self) -> None:
        """Fecha a conexão com o servidor RCON."""
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    # ------------------------------------------------------------------
    # Helpers de alto nível
    # ------------------------------------------------------------------

    def list_players_online(self) -> List[str]:
        """
        Executa ListPlayers e retorna uma lista de SteamIDs dos jogadores online.

        Returns:
            Lista de strings com SteamIDs online. Ex: ["76561198040636105", ...]
        """
        response = self.send_command("ListPlayers")
        return _parse_steam_ids_from_listplayers(response)

    def list_players_full(self) -> List[dict]:
        """
        Executa ListPlayers e retorna dados completos de cada jogador.

        Returns:
            Lista de dicts com os campos:
              - index (int): número de ordem na lista
              - name (str): nome do personagem
              - steam_id (str): SteamID64
              - fame (int): pontos de fama
              - account_balance (int): saldo da conta
              - gold_balance (int): saldo de ouro
              - location_x (float | None)
              - location_y (float | None)
              - location_z (float | None)
        """
        response = self.send_command("ListPlayers")
        return parse_listplayers_response(response)

    def is_player_online(self, steam_id: str) -> bool:
        """Verifica se um jogador com o SteamID dado está online."""
        online = self.list_players_online()
        return str(steam_id) in online

    def spawn_item(self, item_class: str, qty: int, steam_id: str) -> str:
        """
        Spawna um item nos pés de um jogador via SteamID.

        Args:
            item_class: Classe do item. Ex: "Hiking_Backpack_01_03"
            qty: Quantidade a spawnar.
            steam_id: SteamID64 do jogador alvo.

        Returns:
            Resposta do servidor RCON.
        """
        cmd = f"spawnitem {item_class} {int(qty)} Location {steam_id}"
        return self.send_command(cmd)

    def spawn_vehicle(self, vehicle_class: str, steam_id: str) -> str:
        """
        Spawna um veículo próximo de um jogador via SteamID.

        Args:
            vehicle_class: Classe do veículo. Ex: "BPC_RIS"
            steam_id: SteamID64 do jogador alvo.

        Returns:
            Resposta do servidor RCON.
        """
        cmd = f"spawnvehicle {vehicle_class} 1 Location {steam_id}"
        return self.send_command(cmd)

    # ------------------------------------------------------------------
    # Método estático de diagnóstico
    # ------------------------------------------------------------------

    @staticmethod
    def test_connection(ip: str, port: int, password: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Tests the RCON connection without keeping the socket open.

        Returns:
            (success: bool, message: str)
        """
        def is_scum_running() -> bool:
            import sys
            if sys.platform != "win32":
                return False
            import subprocess
            try:
                out = subprocess.check_output(
                    'tasklist /FI "IMAGENAME eq SCUMServer.exe" /NH',
                    shell=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return "SCUMServer.exe" in out
            except Exception:
                return False

        try:
            client = RconClient(ip, int(port), password, timeout=timeout)
            client.connect()
            # Sends an innocuous command to verify communication works
            resp = client.send_command("ListPlayers")
            client.close()
            return True, f"Successfully connected! Response: {resp[:80] if resp else '(no response)'}"
        except RconAuthError as e:
            return False, f"Authentication failed: {e}"
        except RconError as e:
            if not is_scum_running():
                return False, f"Connection failed: {e}\n\n⚠️ SCUMServer.exe seems to be stopped or offline."
            return False, f"Connection failed: {e}"
        except Exception as e:
            if not is_scum_running():
                return False, f"Unexpected error: {e}\n\n⚠️ SCUMServer.exe seems to be stopped or offline."
            return False, f"Unexpected error: {e}"


# ------------------------------------------------------------------
# Utilitário de parsing
# ------------------------------------------------------------------

def _parse_steam_ids_from_listplayers(response: str) -> List[str]:
    """Parseia a resposta do ListPlayers e extrai apenas os SteamIDs."""
    return [p["steam_id"] for p in parse_listplayers_response(response)]


def parse_listplayers_response(response: str) -> List[dict]:
    """
    Parseia a resposta completa do comando ListPlayers.

    Formato confirmado do mod scum_rcon (UE4SS):

        1. Pedreiro
        Steam: Pedreiro (76561198040636105)
        Fame: 4
        Account balance: 0
        Gold balance: 0
        Location: X=-326764.000 Y=7495.000 Z=35788.141

    Returns:
        Lista de dicts com: index, name, steam_id, fame,
        account_balance, gold_balance, location_x, location_y, location_z
    """
    import re

    players: List[dict] = []
    if not response or not response.strip():
        return players

    # Dividir a resposta em blocos por jogador (separados por linha de índice "N. Nome")
    # Cada bloco começa com uma linha como "  1. Pedreiro"
    blocks = re.split(r"\n(?=\s*\d+\.\s+\S)", response.strip())

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        player: dict = {
            "index": None,
            "name": "",
            "steam_id": "",
            "fame": 0,
            "account_balance": 0,
            "gold_balance": 0,
            "location_x": None,
            "location_y": None,
            "location_z": None,
        }

        # Linha de índice: "1. Pedreiro"
        m_index = re.match(r"^\s*(\d+)\.\s+(.+)", block)
        if m_index:
            player["index"] = int(m_index.group(1))
            player["name"] = m_index.group(2).strip()

        # Steam: Nome (SteamID)
        m_steam = re.search(r"Steam:\s+.*\((\d{17})\)", block)
        if m_steam:
            player["steam_id"] = m_steam.group(1)
        else:
            # Sem SteamID = bloco inválido
            continue

        # Fame: N
        m_fame = re.search(r"Fame:\s*(\d+)", block)
        if m_fame:
            player["fame"] = int(m_fame.group(1))

        # Account balance: N
        m_bal = re.search(r"Account balance:\s*(\d+)", block)
        if m_bal:
            player["account_balance"] = int(m_bal.group(1))

        # Gold balance: N
        m_gold = re.search(r"Gold balance:\s*(\d+)", block)
        if m_gold:
            player["gold_balance"] = int(m_gold.group(1))

        # Location: X=... Y=... Z=...
        m_loc = re.search(
            r"Location:\s*X=([\-\d.]+)\s+Y=([\-\d.]+)\s+Z=([\-\d.]+)",
            block,
        )
        if m_loc:
            try:
                player["location_x"] = float(m_loc.group(1))
                player["location_y"] = float(m_loc.group(2))
                player["location_z"] = float(m_loc.group(3))
            except ValueError:
                pass

        players.append(player)

    return players


# ------------------------------------------------------------------
# Helpers de configuração
# ------------------------------------------------------------------

def load_rcon_config_from_file(config_path: str = "data/config.json") -> dict:
    """
    Carrega as configurações da seção 'rcon' do config.json.

    Returns:
        Dicionário com ip, port, password, enabled.
    """
    import json
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("rcon", {})
    except Exception:
        return {}


def query_live_mod_version(client: RconClient) -> dict:
    """
    Envia o comando 'version' via RCON e analisa a resposta estruturada do BSBR-SCUM.
    Exemplo de resposta do mod:
        bsbr_scum 0.3.0
        Source RCON on 28015, API on 27100
        options: split_replies=0, elevate=1
    """
    try:
        raw = client.send_command("version", origin="VERSION_CHECK")
        if not raw:
            return {"online": False, "raw": None}

        info: dict = {
            "online": True,
            "raw": raw.strip(),
            "version": None,
            "elevate": None,
            "split_replies": None,
            "source_port": None,
            "api_port": None,
        }

        lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        if lines:
            # Linha 1: "bsbr_scum 0.3.0"
            m_ver = re.search(r"(?:bsbr_scum|version)?\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)", lines[0], re.IGNORECASE)
            if m_ver:
                info["version"] = m_ver.group(1)

        # Buscar portas e opções em todo o texto
        m_ports = re.search(r"Source RCON on (\d+),\s*API on (\d+)", raw, re.IGNORECASE)
        if m_ports:
            info["source_port"] = int(m_ports.group(1))
            info["api_port"] = int(m_ports.group(2))

        m_elevate = re.search(r"elevate\s*=\s*(\d+)", raw, re.IGNORECASE)
        if m_elevate:
            info["elevate"] = int(m_elevate.group(1))

        m_split = re.search(r"split_replies\s*=\s*(\d+)", raw, re.IGNORECASE)
        if m_split:
            info["split_replies"] = int(m_split.group(1))

        return info
    except Exception as e:
        return {"online": False, "error": str(e), "raw": None}


def get_rcon_client_from_config(config_path: str = "data/config.json") -> Optional[Any]:
    """
    Retorna uma instância do RconClient conectada ao mod BSBR-SCUM
    (protocolo Source RCON nativo, porta padrão 28015).
    Retorna None se o RCON estiver desabilitado em config.json.
    """
    cfg = load_rcon_config_from_file(config_path)
    if not cfg.get("enabled", False):
        return None

    ip = str(cfg.get("ip", "127.0.0.1") or "127.0.0.1")
    port = int(cfg.get("port", 28015) or 28015)
    password = str(cfg.get("password", "") or "")

    # Se a senha estiver vazia no config.json, tentar resgatar do config.ini do mod
    if not password:
        try:
            import json
            with open(config_path, "r", encoding="utf-8") as f:
                full_cfg = json.load(f)
            bin_dir = full_cfg.get("paths", {}).get("scum_server", {}).get("binaries_directory", "")
            if bin_dir:
                from utils.rcon_mod_manager import RconModManager
                mgr = RconModManager()
                mod_cfg = mgr.get_installed_config(bin_dir)
                if mod_cfg and mod_cfg.get("password"):
                    password = mod_cfg["password"]
        except Exception:
            pass

    return RconClient(ip, port, password)

