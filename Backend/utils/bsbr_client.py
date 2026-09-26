"""
BsbrClient - Cliente TCP nativo para comunicação com o mod BSBR-SCUM (Mazzotti).

O mod BSBR escuta em um socket TCP local (padrão 127.0.0.1:27100).
A cada comando enviado (terminado em \\n), o mod processa na thread do jogo,
retorna a resposta completa e fecha a conexão (ou aguarda).
"""
import socket
import time
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import StructuredLogger


class BsbrError(Exception):
    """Erro genérico de comunicação com o BSBR-SCUM."""
    pass


class BsbrConnectionError(BsbrError):
    """Falha de conexão com o socket do BSBR-SCUM."""
    pass


class BsbrTimeoutError(BsbrError):
    """Timeout aguardando resposta do BSBR-SCUM."""
    pass


class BsbrClient:
    """
    Cliente de conexão e execução de comandos para o mod BSBR-SCUM.
    Compatível com a interface do RconClient para uso transparente no SSM.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 27100,
        password: str = "",
        timeout: float = 10.0,
        logger: Optional[StructuredLogger] = None,
    ):
        self.host = host or "127.0.0.1"
        self.port = int(port or 27100)
        self.password = password
        self.timeout = float(timeout or 10.0)
        self.logger = logger
        self._sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """
        Verifica se a porta está acessível abrindo uma conexão rápida de teste.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            sock.close()
            if self.logger:
                self.logger.debug(f"BsbrClient conectado com sucesso a {self.host}:{self.port}")
        except ConnectionRefusedError as e:
            raise BsbrConnectionError(
                f"Não foi possível conectar ao BSBR-SCUM em {self.host}:{self.port} — Conexão recusada (servidor fora do ar ou mod não carregado)."
            ) from e
        except socket.timeout as e:
            raise BsbrTimeoutError(
                f"Timeout ao conectar ao BSBR-SCUM em {self.host}:{self.port} ({self.timeout}s)."
            ) from e
        except Exception as e:
            raise BsbrConnectionError(f"Erro ao conectar ao BSBR-SCUM: {e}") from e

    def send_command(self, command: str, delay_after: float = 0.0, origin: str = "SYSTEM") -> str:
        """
        Envia uma linha de comando ao mod e retorna a resposta de texto.

        O mod BSBR opera no modelo requisição/resposta por conexão:
        1. Conecta
        2. Envia <command>\n
        3. Lê até o encerramento do stream / resposta completa
        4. Fecha o socket
        """
        cmd_clean = command.strip()
        if not cmd_clean:
            return ""

        from utils.rcon_logger import RconLogger
        rcon_log = RconLogger.get_instance()
        t_start = time.perf_counter()
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            payload = (cmd_clean + "\n").encode("utf-8")
            sock.sendall(payload)

            # Ler resposta completa
            chunks = []
            while True:
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    chunks.append(data)
                except socket.timeout:
                    break

            raw_response = b"".join(chunks).decode("utf-8", errors="replace").strip()
            duration_ms = (time.perf_counter() - t_start) * 1000.0

            rcon_log.log_command(
                command=cmd_clean,
                response=raw_response,
                duration_ms=duration_ms,
                origin=origin,
                success=True,
            )

            if delay_after > 0:
                time.sleep(delay_after)

            return raw_response

        except ConnectionRefusedError as e:
            duration_ms = (time.perf_counter() - t_start) * 1000.0
            err_msg = f"Could not connect to {self.host}:{self.port} — Connection refused by target machine"
            rcon_log.log_error(command=cmd_clean, error=err_msg, duration_ms=duration_ms, origin=origin)
            raise BsbrConnectionError(err_msg) from e
        except socket.timeout as e:
            duration_ms = (time.perf_counter() - t_start) * 1000.0
            err_msg = f"Timeout ({self.timeout}s) waiting for response on {self.host}:{self.port}"
            rcon_log.log_error(command=cmd_clean, error=err_msg, duration_ms=duration_ms, origin=origin)
            raise BsbrTimeoutError(err_msg) from e
        except Exception as e:
            duration_ms = (time.perf_counter() - t_start) * 1000.0
            err_msg = f"Error executing command: {e}"
            rcon_log.log_error(command=cmd_clean, error=err_msg, duration_ms=duration_ms, origin=origin)
            raise BsbrError(err_msg) from e
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass


    def list_players(self) -> List[Dict[str, Any]]:
        """
        Executa 'players' ou 'ListPlayers' e retorna lista estruturada de jogadores.
        Suporta o formato tabular com pipes do BSBR ('ID | Nome | SteamID64') e o formato nativo do SCUM.
        """
        try:
            # Tenta comando 'players' do mod BSBR primeiro
            resp = self.send_command("players")
            if not resp or "sem resposta" in resp.lower() or "erro" in resp.lower():
                resp = self.send_command("ListPlayers")

            players = []
            for line in resp.splitlines():
                line = line.strip()
                if (
                    not line
                    or line.startswith("#")
                    or "jogador(es)" in line.lower()
                    or "players online" in line.lower()
                    or "alvo:" in line.lower()
                ):
                    continue

                # 1. Formato tabular oficial do BSBR-SCUM: "ID | Nome | SteamID64"
                if "|" in line:
                    pipe_parts = [p.strip() for p in line.split("|")]
                    if len(pipe_parts) == 3:
                        profile_id, name, steam_id = pipe_parts
                        players.append({
                            "profile_id": profile_id,
                            "name": name,
                            "steam_id": steam_id,
                            "raw": line,
                        })
                        continue

                # 2. Formato nativo SCUM: "76561198...:Nome(1)" ou espaço
                if ":" in line and "(" in line:
                    try:
                        s_id, rest = line.split(":", 1)
                        p_name = rest.split("(")[0].strip()
                        players.append({
                            "profile_id": "",
                            "name": p_name,
                            "steam_id": s_id.strip(),
                            "raw": line,
                        })
                        continue
                    except Exception:
                        pass

                # 3. Fallback genérico por espaços
                parts = line.split()
                if len(parts) >= 2:
                    if parts[0].isdigit() and len(parts[0]) >= 16:
                        players.append({
                            "profile_id": "",
                            "name": " ".join(parts[1:]),
                            "steam_id": parts[0],
                            "raw": line,
                        })
                    else:
                        players.append({
                            "profile_id": "",
                            "name": " ".join(parts[:-1]),
                            "steam_id": parts[-1].strip("()"),
                            "raw": line,
                        })
                else:
                    players.append({"profile_id": "", "name": line, "steam_id": "", "raw": line})

            return players
        except Exception as e:
            if self.logger:
                self.logger.warn(f"BsbrClient list_players error: {e}")
            return []


    def close(self) -> None:
        """Fecha qualquer socket remanescente."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
