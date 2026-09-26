import json
import requests
import os
import re
import threading
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .gameplay_parser import GameplayLogParser
from .temp_file_manager import TempFileManager
from .database_manager import DatabaseManager
from .steam_api import SteamAPI

class OnlinePlayersMonitor:
    """
    Monitor de jogadores online baseado em logs de gameplay
    Detecta jogadores ativos e mantém status em tempo real
    """
    
    def __init__(self, db_manager: DatabaseManager, config_path: str = "data/config.json", gameplay_logs_path: str = None):
        self.db_manager = db_manager
        self.temp_manager = TempFileManager("data/temp")
        self.gameplay_parser = GameplayLogParser(self.temp_manager)
        self.steam_api = SteamAPI()
        
        # Configurações
        self.config = self._load_config(config_path)
        self.webhook_url = self._load_webhook_config()
        
        # Configurações de monitoramento
        self.activity_timeout_minutes = 30  # Considerar offline após 30 min sem atividade
        self.check_interval_seconds = 30    # Verificar a cada 30 segundos (pedido do usuário)
        self.gameplay_logs_path = gameplay_logs_path or 'C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\Logs'

        # Status dos jogadores
        try:
            self.online_players = self._get_online_players_from_database()
        except Exception as e:
            self.online_players = {}
        self.last_check_time = datetime.now()
        
        # Thread de monitoramento
        self.monitoring_thread = None
        self.is_monitoring = False
        
        # Controle de spam - última notificação enviada
        self.last_notification_time = None
        self.min_notification_interval = 120  # Mínimo 120 segundos entre atualizações (debounce)

        self._force_next_notification = False

        self._http = requests.Session()

        self._webhooks_v2_cache: Optional[Dict[str, Any]] = None
        self._players_online_state_cache: Dict[str, Any] = {}

        self._last_login_log_seen: Optional[str] = None
        
        print("OK OnlinePlayersMonitor inicializado")
        print(f"   Timeout de atividade: {self.activity_timeout_minutes} minutos")
        print(f"   Intervalo de verificação: {self.check_interval_seconds} segundos")
        print(f"   Intervalo mínimo entre notificações: {self.min_notification_interval} segundos")
        # Não expor caminho completo por segurança

    def _parse_discord_webhook_url(self, url: str) -> Optional[Dict[str, str]]:
        try:
            u = (url or "").strip()
            if not u:
                return None
            m = re.search(r"/api/webhooks/([0-9]+)/([^/\s]+)", u)
            if not m:
                return None
            return {"id": m.group(1), "token": m.group(2)}
        except Exception:
            return None

    def _load_webhooks_v2(self) -> Optional[Dict[str, Any]]:
        try:
            from core.webhooks.manager import WebhooksManager

            mgr = WebhooksManager("data/webhooks.json")
            return mgr.load_v2()
        except Exception:
            return None

    def _save_webhooks_v2(self, v2_data: Dict[str, Any]) -> bool:
        try:
            from core.webhooks.manager import WebhooksManager

            mgr = WebhooksManager("data/webhooks.json")
            mgr.replace_all_v2(v2_data, create_backup=True)
            return True
        except Exception:
            return False

    def _get_players_online_event_v2(self) -> Optional[Dict[str, Any]]:
        try:
            v2 = self._load_webhooks_v2()
            if not isinstance(v2, dict):
                return None
            events = v2.get("events")
            if not isinstance(events, dict):
                return None
            ev = events.get("players_online")
            if not isinstance(ev, dict):
                return None
            return ev
        except Exception:
            return None

    def _load_players_online_state(self) -> Dict[str, Any]:
        try:
            ev = self._get_players_online_event_v2()
            st = (ev or {}).get("state")
            if isinstance(st, dict):
                return dict(st)
        except Exception:
            pass

        return {}

    def _update_players_online_state(self, patch: Dict[str, Any]) -> None:
        try:
            v2 = self._load_webhooks_v2()
            if not isinstance(v2, dict):
                return
            events = v2.get("events")
            if not isinstance(events, dict):
                return
            ev = events.get("players_online")
            if not isinstance(ev, dict):
                return
            st = ev.get("state")
            if not isinstance(st, dict):
                st = {}
                ev["state"] = st

            for k, v in (patch or {}).items():
                st[k] = v
            self._save_webhooks_v2(v2)
        except Exception:
            pass

    def _get_players_online_channel_id(self) -> Optional[str]:
        try:
            ev = self._get_players_online_event_v2() or {}
            target = ev.get("target")
            if not isinstance(target, dict):
                return None
            chan = target.get("channel")
            if not isinstance(chan, dict):
                return None
            cid = chan.get("id")
            if cid is None:
                return None
            return str(cid).strip() or None
        except Exception:
            return None

    def _get_discord_bot_token(self) -> str:
        try:
            bot_cfg = (self.config or {}).get("discord_bot")
            if not isinstance(bot_cfg, dict):
                return ""
            return str(bot_cfg.get("bot_token") or "").strip()
        except Exception:
            return ""

    def _sanitize_discord_channel_name(self, name: str) -> str:
        try:
            s = str(name or "").strip()
            # Lowercase apenas ASCII (preserva emoji/unicode)
            s = "".join(ch.lower() if ch.isascii() else ch for ch in s)
            s = s.replace("_", "-")
            s = re.sub(r"\s+", "-", s)
            # Remover apenas caracteres de controle ASCII (0x00-0x1F, 0x7F)
            s = re.sub(r"[\x00-\x1f\x7f]", "", s)
            s = re.sub(r"-+", "-", s)
            s = s.strip("-")
            if not s:
                return "online"
            return s[:90]
        except Exception:
            return "online"

    def _get_current_discord_channel_name(self, channel_id: str) -> Optional[str]:
        try:
            token = self._get_discord_bot_token()
            if not token:
                return None
            r = None
            try:
                r = self._http.get(
                    f"https://discord.com/api/v10/channels/{channel_id}",
                    headers={
                        "Authorization": f"Bot {token}",
                        "Content-Type": "application/json",
                    },
                    timeout=15,
                )
                if int(getattr(r, "status_code", 0)) != 200:
                    return None
                try:
                    data = r.json()
                except Exception:
                    data = None
                if isinstance(data, dict):
                    nm = data.get("name")
                    if nm is not None:
                        return str(nm)
                return None
            finally:
                try:
                    if r is not None:
                        r.close()
                except Exception:
                    pass
        except Exception:
            return None

    def _rename_discord_channel_online_count(self, count: int) -> None:
        try:
            token = self._get_discord_bot_token()
            if not token:
                return
            channel_id = self._get_players_online_channel_id()
            if not channel_id:
                return

            current_name = self._get_current_discord_channel_name(channel_id) or "online"
            
            # Limpar o nome base removendo números e separadores no final do nome (ex: "online1313" -> "online")
            base = str(current_name).strip()
            base = re.sub(r"[|┃ \-~•·_]*\d+$", "", base).strip()
            
            # Determinar qual delimitador usar
            # Se o canal original contém "┃", usamos "┃" para manter o padrão visual do Discord
            # Caso contrário, usamos "-" para canais de texto padrão
            if "┃" in base:
                delimiter = "┃"
            elif "-" in str(current_name):
                delimiter = "-"
            else:
                delimiter = "-"
            
            base = self._sanitize_discord_channel_name(base)
            desired_name = f"{base}{delimiter}{int(count)}"
            r = None
            try:
                r = self._http.patch(
                    f"https://discord.com/api/v10/channels/{channel_id}",
                    json={"name": desired_name},
                    headers={
                        "Authorization": f"Bot {token}",
                        "Content-Type": "application/json",
                    },
                    timeout=15,
                )
                if int(getattr(r, "status_code", 0)) != 200:
                    try:
                        body = (r.text or "")[:200]
                    except Exception:
                        body = ""
                    print(
                        f"AVISO Falha ao renomear canal players_online para '{desired_name}': HTTP {getattr(r, 'status_code', 'N/A')} {body}"
                    )
            finally:
                try:
                    if r is not None:
                        r.close()
                except Exception:
                    pass
        except Exception:
            pass

    def _build_players_signature(self, current_online: Dict[str, Dict[str, Any]]) -> str:
        try:
            # Assinatura estável: apenas conjunto de steam_ids (evita mudar por tempo online)
            ids = sorted([str(k) for k in (current_online or {}).keys()])
            payload = "|".join(ids)
            return hashlib.sha1(payload.encode("utf-8", errors="ignore")).hexdigest()
        except Exception:
            return ""

    def _send_or_edit_players_online_message(self, embed: Dict[str, Any]) -> None:
        try:
            if not self.webhook_url:
                print("AVISO Webhook não configurado para jogadores online")
                return

            parsed = self._parse_discord_webhook_url(self.webhook_url)
            if not parsed:
                print("AVISO Webhook URL inválida para jogadores online")
                return

            payload = {"embeds": [embed]}

            # Enviar nova mensagem sempre (nao editar mensagem anterior)
            r2 = None
            try:
                r2 = self._http.post(
                    f"https://discord.com/api/webhooks/{parsed['id']}/{parsed['token']}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=15,
                )
                if int(getattr(r2, "status_code", 0)) in (200, 201, 204):
                    return

                try:
                    body = (r2.text or "")[:200]
                except Exception:
                    body = ""
                print(
                    f"ERRO Falha ao criar mensagem fixa players_online: HTTP {getattr(r2, 'status_code', 'N/A')} {body}"
                )
            finally:
                try:
                    if r2 is not None:
                        r2.close()
                except Exception:
                    pass

        except Exception as e:
            print(f"ERRO ao enviar/editar players_online: {e}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carregar configurações do arquivo config.json"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"AVISO Erro ao carregar config: {e}")
        return {}
    
    def _load_webhook_config(self) -> Optional[str]:
        """Carregar URL do webhook para jogadores online"""
        try:
            webhook_path = "data/webhooks.json"
            if os.path.exists(webhook_path):
                try:
                    from core.webhooks.manager import WebhooksManager

                    mgr = WebhooksManager(webhook_path)
                    webhooks = mgr.load()
                    if isinstance(webhooks, dict):
                        return webhooks.get('players_online')
                except Exception:
                    with open(webhook_path, 'r', encoding='utf-8') as f:
                        webhooks = json.load(f)
                        return webhooks.get('players_online')
        except Exception as e:
            print(f"AVISO Erro ao carregar webhook config: {e}")
        return None
    
    def start_monitoring(self):
        """Iniciar monitoramento em thread separada"""
        if self.is_monitoring:
            print("AVISO Monitoramento já está ativo")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        # logger.debug("Monitoramento de jogadores online iniciado")
    
    def stop_monitoring(self):
        """Parar monitoramento"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("OK Monitoramento de jogadores online parado")
    
    def _monitoring_loop(self):
        """Loop principal de monitoramento"""
        while self.is_monitoring:
            try:
                # Detectar se há novo arquivo de login atual
                latest_login_file = self._find_latest_login_log()
                if latest_login_file:
                    # Se nunca vimos este arquivo (ou mudou desde a última verificação), resetar estado
                    current_latest_name = getattr(self, 'current_latest_login_name', None)
                    latest_name = os.path.basename(latest_login_file)
                    if current_latest_name != latest_name:
                        # Atualizar referência e resetar estado do banco/memória
                        self.current_latest_login_name = latest_name
                        # Não marcar todo mundo offline: rotação do arquivo de login pode ocorrer enquanto
                        # ainda há jogadores online. O estado online será reconstruído no próximo ciclo
                        # combinando login + atividade recente de gameplay.
                        self._force_next_notification = True

                self._check_online_players()
                time.sleep(self.check_interval_seconds)
            except Exception as e:
                print(f"ERRO no loop de monitoramento: {e}")
                time.sleep(self.check_interval_seconds)
    
    def _check_online_players(self):
        """Verificar jogadores online lendo somente o login_*.log mais recente."""
        try:
            latest_login_file = self._find_latest_login_log()
            # Fonte de verdade: somente o login_*.log atual.
            # Se o arquivo atual mostrar 2, entao sao 2 online (sem carryover e sem complementar por gameplay).
            current_online = self._rebuild_online_from_login_file(login_file=latest_login_file)
            
            # 2. Detectar mudanças no status
            self._detect_status_changes(current_online)
            
            # 3. Sincronizar banco de dados com jogadores online e offline
            if current_online:
                self.db_manager.update_online_players(current_online)
                self.db_manager.mark_all_offline_except(list(current_online.keys()))
            else:
                self.db_manager.reset_all_players_online()
            
            # 4. Atualizar status atual
            self.online_players = current_online
            self.last_check_time = datetime.now()
            
            # logger.debug(f"Verificação concluída: {len(self.online_players)} jogadores online")
            
        except Exception as e:
            print(f"ERRO ao verificar jogadores online: {e}")

    def _rebuild_online_from_login_file(self, login_file: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Ler o login_*.log mais recente, copiar para temp e reconstruir a lista de online.
        Regra: online = último evento de login sem um logout posterior para o mesmo steam_id.
        """
        try:
            login_file = login_file or self._find_latest_login_log()
            if not login_file:
                print("AVISO Nenhum arquivo de login encontrado para reconstrução")
                return {}

            # Copiar para temp e ler tudo (evita arquivo em uso)
            temp_path = self.temp_manager.create_temp_copy(login_file)
            if not temp_path:
                print("ERRO Falha ao criar cópia temporária do arquivo de login")
                return {}

            try:
                # Ler todas as linhas (priorizar utf-16le, formato padrão dos logs SCUM)
                try:
                    with open(temp_path, 'r', encoding='utf-16le', errors='ignore') as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                except UnicodeError:
                    with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
            except Exception:
                # Fallback final para utf-8
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]

            finally:
                self.temp_manager.cleanup_temp_file(temp_path)

            # Percorrer todas as linhas e coletar últimos eventos por steam_id
            last_login_event: Dict[str, Dict[str, Any]] = {}
            last_logout_time: Dict[str, datetime] = {}

            for line in lines:
                if 'logged in at:' in line:
                    login_data = self._parse_login_event(line)
                    if login_data:
                        last_login_event[login_data['steam_id']] = login_data
                elif 'logged out at:' in line:
                    logout_data = self._parse_logout_event(line)
                    if logout_data:
                        last_logout_time[logout_data['steam_id']] = logout_data['logout_time']

            # Determinar quem está online: login_time > último logout_time (ou sem logout)
            current_online: Dict[str, Dict[str, Any]] = {}
            for steam_id, login_data in last_login_event.items():
                logout_time = last_logout_time.get(steam_id)
                if not logout_time or (login_data['login_time'] and login_data['login_time'] > logout_time):
                    current_online[steam_id] = {
                        'player_name': login_data['player_name'],
                        'player_id': login_data['player_id'],
                        'last_activity': login_data['login_time'],
                        'last_coordinates': login_data['coordinates'],
                        'activity_types': ['login'],
                        'total_activities': 1,
                    }

            print(f"OK Reconstruído via login log: {len(current_online)} jogadores online")
            return current_online

        except Exception as e:
            print(f"ERRO ao reconstruir jogadores a partir do login log: {e}")
            return {}
    
    def _get_online_players_from_database(self) -> Dict[str, Dict[str, Any]]:
        """Obter jogadores online do banco de dados.
        1) Tenta ler da tabela `players_online` (status em tempo real)
        2) Se vazio, faz fallback para deduzir a partir de `player_logins` (login sem logout)
        """
        try:
            # 1) Tabela dedicada players_online
            rows = self.db_manager.get_online_players_from_db()

            # Reset pós-restart: se surgiu um novo login_*.log e ainda não houve
            # nenhuma sessão registrada após a criação desse arquivo, não herdar
            # jogadores antigos da tabela players_online.
            try:
                latest_login_file = self._find_latest_login_log()
                if latest_login_file and os.path.exists(latest_login_file):
                    login_created_at = datetime.fromtimestamp(os.path.getctime(latest_login_file))
                    count_rows = self.db_manager.execute_query(
                        "SELECT COUNT(*) FROM player_logins WHERE timestamp >= ?",
                        (login_created_at.isoformat(),)
                    )
                    new_logins_count = count_rows[0][0] if count_rows and len(count_rows[0]) > 0 else 0
                    if new_logins_count == 0:
                        if rows:
                            print("AVISO Reset de jogadores online: novo login_*.log sem sessões; zerando lista.")
                        rows = []
                    # Guardar a referência de criação para uso no fallback
                    latest_login_created_at = login_created_at
                else:
                    latest_login_created_at = None
            except Exception:
                # Se algo falhar nessa heurística, seguir fluxo normal
                latest_login_created_at = None
            if not rows:
                # 2) Fallback: deduzir a partir de player_logins restrito AO NOVO ARQUIVO
                # Usar apenas entradas com timestamp >= criação do login_*.log mais recente
                # para evitar herdar players do arquivo antigo.
                if latest_login_created_at is not None:
                    query = """
                    SELECT DISTINCT p.steam_id, p.player_name, p.player_id,
                           pl.timestamp as last_activity,
                           pl.coordinates_x, pl.coordinates_y, pl.coordinates_z
                    FROM players p
                    JOIN player_logins pl ON p.steam_id = pl.steam_id
                    WHERE pl.action = 'login'
                      AND pl.timestamp >= ?
                      AND NOT EXISTS (
                          SELECT 1 FROM player_logins plo
                          WHERE plo.steam_id = pl.steam_id
                            AND plo.action = 'logout'
                            AND plo.timestamp > pl.timestamp
                      )
                    ORDER BY pl.timestamp DESC
                    """
                    rows = self.db_manager.execute_query(query, (latest_login_created_at.isoformat(),))
                else:
                    # Sem referência de arquivo novo, manter comportamento anterior porém ainda restrito a 2h
                    query = """
                    SELECT DISTINCT p.steam_id, p.player_name, p.player_id,
                           pl.timestamp as last_activity,
                           pl.coordinates_x, pl.coordinates_y, pl.coordinates_z
                    FROM players p
                    JOIN player_logins pl ON p.steam_id = pl.steam_id
                    WHERE pl.action = 'login'
                      AND pl.timestamp > datetime('now', '-2 hours')
                      AND NOT EXISTS (
                          SELECT 1 FROM player_logins plo
                          WHERE plo.steam_id = pl.steam_id
                            AND plo.action = 'logout'
                            AND plo.timestamp > pl.timestamp
                      )
                    ORDER BY pl.timestamp DESC
                    """
                    rows = self.db_manager.execute_query(query)
                if not rows:
                    print("AVISO Nenhum jogador online encontrado no banco")
                    return {}

            # Filtro final: se temos referência do arquivo novo, descartar linhas anteriores a ele
            filtered_rows = []
            for row in rows:
                try:
                    last_activity_val = row[3] if not isinstance(row, dict) else row.get('last_activity')
                    if isinstance(last_activity_val, str):
                        try:
                            last_dt = datetime.fromisoformat(last_activity_val.replace('Z', '+00:00'))
                        except Exception:
                            last_dt = datetime.fromisoformat(last_activity_val)
                    else:
                        last_dt = last_activity_val
                    if 'latest_login_created_at' in locals() and latest_login_created_at is not None:
                        if last_dt is not None and last_dt < latest_login_created_at:
                            # Ignorar registros anteriores ao arquivo novo
                            continue
                except Exception:
                    pass
                filtered_rows.append(row)

            rows = filtered_rows

            current_online: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                steam_id = row["steam_id"] if isinstance(row, dict) else row[0]
                player_name = row["player_name"] if isinstance(row, dict) else row[1]
                player_id = row["player_id"] if isinstance(row, dict) else row[2]
                last_activity = row["last_activity"] if isinstance(row, dict) else row[3]
                coordinates_x = row["coordinates_x"] if isinstance(row, dict) else row[4]
                coordinates_y = row["coordinates_y"] if isinstance(row, dict) else row[5]
                coordinates_z = row["coordinates_z"] if isinstance(row, dict) else row[6]

                # Converter last_activity para datetime se vier como string
                if isinstance(last_activity, str):
                    try:
                        last_activity_dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    except Exception:
                        # Formatos sem timezone
                        last_activity_dt = datetime.fromisoformat(last_activity)
                else:
                    last_activity_dt = last_activity

                current_online[steam_id] = {
                    'player_name': player_name,
                    'player_id': player_id,
                    'last_activity': last_activity_dt,
                    'last_coordinates': {
                        'x': coordinates_x,
                        'y': coordinates_y,
                        'z': coordinates_z
                    },
                    'activity_types': row.get('activity_types', []) if isinstance(row, dict) else ['login'],
                    'total_activities': row.get('total_activities', 1) if isinstance(row, dict) else 1,
                    'source': 'players_online_table' if isinstance(row, dict) and 'status' in row else 'login_fallback'
                }

            print(f"OK {len(current_online)} jogadores online encontrados no banco")
            for steam_id, player_data in current_online.items():
                print(f"   • {player_data['player_name']} ({steam_id})")

            return current_online

        except Exception as e:
            print(f"ERRO ao obter jogadores do banco: {e}")
            return {}
    
    def _check_login_logs(self) -> Dict[str, Any]:
        """Verificar logs de login para detectar mudanças"""
        try:
            # Encontrar arquivo de login mais recente
            login_file = self._find_latest_login_log()
            if not login_file:
                print("AVISO Nenhum arquivo de login encontrado")
                return {'new_logins': [], 'new_logouts': []}
            
            # Processar arquivo de login
            login_events = self._parse_login_log(login_file)
            
            return login_events
            
        except Exception as e:
            print(f"ERRO ao verificar logs de login: {e}")
            return {'new_logins': [], 'new_logouts': []}
    
    def _check_gameplay_logs(self) -> Dict[str, Any]:
        """Verificar logs de gameplay para confirmar atividade"""
        try:
            # Encontrar arquivo de gameplay mais recente
            gameplay_file = self._find_latest_gameplay_log()
            if not gameplay_file:
                print("AVISO Nenhum arquivo de gameplay encontrado")
                return {}
            
            # Processar arquivo de gameplay
            activities = self.gameplay_parser.parse_file(gameplay_file)
            if not activities:
                print("AVISO Nenhuma atividade encontrada no log de gameplay")
                return {}
            
            # Obter jogadores com atividade recente
            active_players = self.gameplay_parser.get_players_with_recent_activity(
                activities, self.activity_timeout_minutes
            )
            
            return active_players
            
        except Exception as e:
            print(f"ERRO ao verificar logs de gameplay: {e}")
            return {}
    
    def _combine_login_and_gameplay_data(self, login_changes: Dict[str, Any], gameplay_activities: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Combinar dados de login e gameplay para determinar jogadores online"""
        current_online = {}
        
        # 1. Obter todos os jogadores que fizeram login (de todo o arquivo)
        all_logins = self._get_all_recent_logins()
        all_logouts = self._get_all_recent_logouts()
        
        # 2. Adicionar jogadores que fizeram login e não fizeram logout
        for login_data in all_logins:
            steam_id = login_data['steam_id']
            # Verificar se não fez logout
            if not any(logout['steam_id'] == steam_id for logout in all_logouts):
                current_online[steam_id] = {
                    'player_name': login_data['player_name'],
                    'player_id': login_data['player_id'],
                    'last_activity': login_data['login_time'],
                    'last_coordinates': login_data['coordinates'],
                    'activity_types': ['login'],
                    'total_activities': 1,
                    'source': 'login_log'
                }
        
        # 3. Atualizar com atividades de gameplay
        for steam_id, activity_data in gameplay_activities.items():
            if steam_id in current_online:
                # Atualizar dados existentes com atividade de gameplay
                current_online[steam_id]['activity_types'].extend(activity_data['activity_types'])
                current_online[steam_id]['total_activities'] += activity_data['total_activities']
                current_online[steam_id]['source'] = 'both'
            else:
                # Adicionar novo jogador baseado apenas em gameplay
                current_online[steam_id] = activity_data
                current_online[steam_id]['source'] = 'gameplay_only'
        
        return current_online
    
    def _get_all_recent_logins(self) -> List[Dict[str, Any]]:
        """Obter todos os logins recentes do arquivo de login"""
        temp_path = None
        try:
            login_file = self._find_latest_login_log()
            if not login_file:
                return []
            
            # Criar cópia temporária para evitar bloqueio
            temp_path = self.temp_manager.create_temp_copy(login_file)
            if not temp_path:
                return []
            
            all_logins = []
            
            # Ler arquivo de login temporário
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Processar todas as linhas (não apenas as últimas)
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Procurar por eventos de login
                if 'logged in at:' in line:
                    login_data = self._parse_login_event(line)
                    if login_data:
                        all_logins.append(login_data)
            
            return all_logins
            
        except PermissionError:
            # Arquivo está bloqueado - silenciosamente ignorar
            return []
        except Exception as e:
            if "Permission denied" not in str(e) and "Errno 13" not in str(e):
                print(f"ERRO ao obter todos os logins: {e}")
            return []
        finally:
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _get_all_recent_logouts(self) -> List[Dict[str, Any]]:
        """Obter todos os logouts recentes do arquivo de login"""
        temp_path = None
        try:
            login_file = self._find_latest_login_log()
            if not login_file:
                return []
            
            # Criar cópia temporária para evitar bloqueio
            temp_path = self.temp_manager.create_temp_copy(login_file)
            if not temp_path:
                return []
            
            all_logouts = []
            
            # Ler arquivo de login temporário
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Processar todas as linhas (não apenas as últimas)
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Procurar por eventos de logout
                if 'logged out at:' in line:
                    logout_data = self._parse_logout_event(line)
                    if logout_data:
                        all_logouts.append(logout_data)
            
            return all_logouts
            
        except PermissionError:
            # Arquivo está bloqueado - silenciosamente ignorar
            return []
        except Exception as e:
            if "Permission denied" not in str(e) and "Errno 13" not in str(e):
                print(f"ERRO ao obter todos os logouts: {e}")
            return []
        finally:
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _find_latest_login_log(self) -> Optional[str]:
        """Encontrar o arquivo de login mais recente"""
        try:
            if not os.path.exists(self.gameplay_logs_path):
                print(f"AVISO Pasta de logs não encontrada: {self.gameplay_logs_path}")
                return None
            
            login_files = []
            for filename in os.listdir(self.gameplay_logs_path):
                if filename.startswith('login_') and filename.endswith('.log'):
                    file_path = os.path.join(self.gameplay_logs_path, filename)
                    if os.path.isfile(file_path):
                        login_files.append(file_path)
            
            if not login_files:
                print("AVISO Nenhum arquivo de login encontrado")
                return None
            
            # Retornar o arquivo mais recente com base no timestamp do NOME do arquivo
            # Formato esperado: login_YYYYMMDDHHMMSS.log OU login_YYYYMMDDHHMMSS?.log
            def file_key(path: str) -> str:
                name = os.path.basename(path)
                # Extrair parte numérica após 'login_'
                try:
                    base = name.split('login_')[1].split('.log')[0]
                except Exception:
                    base = name
                # Remover separadores não numéricos
                digits = ''.join(ch for ch in base if ch.isdigit())
                return digits
            latest_file = max(login_files, key=file_key)
            print(f"OK Arquivo de login mais recente: {os.path.basename(latest_file)}")
            return latest_file
            
        except Exception as e:
            print(f"ERRO ao encontrar arquivo de login: {e}")
            return None
    
    def _parse_login_log(self, login_file: str) -> Dict[str, Any]:
        """Processar arquivo de login para extrair eventos de login/logout"""
        temp_path = None
        try:
            # Criar cópia temporária para evitar bloqueio
            temp_path = self.temp_manager.create_temp_copy(login_file)
            if not temp_path:
                return {'logins': [], 'logouts': []}
            
            new_logins = []
            new_logouts = []
            
            # Ler arquivo de login temporário
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Processar últimas linhas (eventos mais recentes)
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            for line in recent_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Procurar por eventos de login
                if 'logged in at:' in line:
                    login_data = self._parse_login_event(line)
                    if login_data:
                        new_logins.append(login_data)
                
                # Procurar por eventos de logout
                elif 'logged out at:' in line:
                    logout_data = self._parse_logout_event(line)
                    if logout_data:
                        new_logouts.append(logout_data)
            
            return {
                'new_logins': new_logins,
                'new_logouts': new_logouts
            }
            
        except PermissionError:
            # Arquivo está bloqueado - silenciosamente ignorar
            return {'new_logins': [], 'new_logouts': []}
        except Exception as e:
            if "Permission denied" not in str(e) and "Errno 13" not in str(e):
                print(f"ERRO ao processar arquivo de login: {e}")
            return {'new_logins': [], 'new_logouts': []}
        finally:
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _parse_login_event(self, line: str) -> Optional[Dict[str, Any]]:
        """Extrair dados de um evento de login"""
        try:
            # Formato: 2025.10.18-04.02.43: '179.209.44.183 76561198209837253:Véio(211)' logged in at: X=-359050.000 Y=20451.000 Z=35716.000
            import re
            
            # Extrair timestamp
            timestamp_match = re.search(r'(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):', line)
            if not timestamp_match:
                return None
            
            # Extrair dados do jogador
            player_match = re.search(r"'[^']*\s+(\d+):([^(]+)\((\d+)\)'", line)
            if not player_match:
                return None
            
            steam_id = player_match.group(1)
            player_name = player_match.group(2)
            player_id = int(player_match.group(3))
            
            # Extrair coordenadas (aceita pontuação extra no final, ex: "3170.810.")
            coords_match = re.search(
                r'X=(-?\d+(?:\.\d+)?)(?:[.,])?\s+Y=(-?\d+(?:\.\d+)?)(?:[.,])?\s+Z=(-?\d+(?:\.\d+)?)(?:[.,])?',
                line
            )
            if not coords_match:
                return None
            
            coordinates = {
                'x': float(coords_match.group(1)),
                'y': float(coords_match.group(2)),
                'z': float(coords_match.group(3))
            }
            
            # Converter timestamp
            login_time = self._parse_timestamp(timestamp_match.group(1) + '-' + timestamp_match.group(2))
            if not login_time:
                return None
            
            return {
                'steam_id': steam_id,
                'player_name': player_name,
                'player_id': player_id,
                'login_time': login_time,
                'coordinates': coordinates
            }
            
        except Exception as e:
            print(f"ERRO ao extrair dados de login: {e}")
            return None
    
    def _parse_logout_event(self, line: str) -> Optional[Dict[str, Any]]:
        """Extrair dados de um evento de logout"""
        try:
            # Formato: 2025.10.18-04.20.35: '177.12.17.8 76561198140683162:Jovigono(322)' logged out at: X=-677322.312 Y=-247631.562 Z=12026.750
            import re
            
            # Extrair timestamp
            timestamp_match = re.search(r'(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):', line)
            if not timestamp_match:
                return None
            
            # Extrair dados do jogador
            player_match = re.search(r"'[^']*\s+(\d+):([^(]+)\((\d+)\)'", line)
            if not player_match:
                return None
            
            steam_id = player_match.group(1)
            player_name = player_match.group(2)
            player_id = int(player_match.group(3))
            
            # Extrair coordenadas (aceita pontuação extra no final, ex: "3170.810.")
            coords_match = re.search(
                r'X=(-?\d+(?:\.\d+)?)(?:[.,])?\s+Y=(-?\d+(?:\.\d+)?)(?:[.,])?\s+Z=(-?\d+(?:\.\d+)?)(?:[.,])?',
                line
            )
            if not coords_match:
                return None
            
            coordinates = {
                'x': float(coords_match.group(1)),
                'y': float(coords_match.group(2)),
                'z': float(coords_match.group(3))
            }
            
            # Converter timestamp
            logout_time = self._parse_timestamp(timestamp_match.group(1) + '-' + timestamp_match.group(2))
            if not logout_time:
                return None
            
            return {
                'steam_id': steam_id,
                'player_name': player_name,
                'player_id': player_id,
                'logout_time': logout_time,
                'coordinates': coordinates
            }
            
        except Exception as e:
            print(f"ERRO ao extrair dados de logout: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Converter timestamp do log para datetime"""
        try:
            # Formato: 2025.10.18-04.26.50
            parts = timestamp_str.split('-')
            if len(parts) != 2:
                return None
            
            date_part = parts[0].replace('.', '-')  # 2025-10-18
            time_part = parts[1].replace('.', ':')  # 04:26:50
            
            datetime_str = f"{date_part} {time_part}"
            return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            print(f"ERRO ao converter timestamp: {e}")
            return None
    
    def _find_latest_gameplay_log(self) -> Optional[str]:
        """Encontrar o arquivo de gameplay mais recente"""
        try:
            if not os.path.exists(self.gameplay_logs_path):
                print(f"AVISO Pasta de logs não encontrada: {self.gameplay_logs_path}")
                return None
            
            gameplay_files = []
            for filename in os.listdir(self.gameplay_logs_path):
                if filename.startswith('gameplay_') and filename.endswith('.log'):
                    file_path = os.path.join(self.gameplay_logs_path, filename)
                    if os.path.isfile(file_path):
                        gameplay_files.append(file_path)
            
            if not gameplay_files:
                print("AVISO Nenhum arquivo de gameplay encontrado")
                return None
            
            # Retornar o arquivo mais recente baseado no timestamp no NOME
            def file_key(path: str) -> str:
                name = os.path.basename(path)
                try:
                    base = name.split('gameplay_')[1].split('.log')[0]
                except Exception:
                    base = name
                digits = ''.join(ch for ch in base if ch.isdigit())
                return digits
            latest_file = max(gameplay_files, key=file_key)
            print(f"OK Arquivo de gameplay mais recente: {os.path.basename(latest_file)}")
            return latest_file
            
        except Exception as e:
            print(f"ERRO ao encontrar arquivo de gameplay: {e}")
            return None
    
    def _detect_status_changes(self, current_online: Dict[str, Dict[str, Any]]):
        """Detectar mudanças no status dos jogadores"""
        try:
            current_steam_ids = set(current_online.keys())
            previous_steam_ids = set(self.online_players.keys())
            
            # Jogadores que entraram online
            players_came_online = current_steam_ids - previous_steam_ids
            
            # Jogadores que saíram offline
            players_went_offline = previous_steam_ids - current_steam_ids

            if players_came_online:
                print(f"DEBUG Jogadores que entraram online: {list(players_came_online)}")
            if players_went_offline:
                print(f"DEBUG Jogadores que saíram offline: {list(players_went_offline)}")
            
            # Sincronizar atributos de quem entrou ou saiu no cache do SSM.db
            to_sync = list(players_came_online | players_went_offline)
            if to_sync:
                threading.Thread(target=self._sync_player_attributes_cache, args=(to_sync,), daemon=True).start()
            
            # Enviar notificação APENAS quando há mudanças reais
            should_send_notification = False
            force_send = bool(self._force_next_notification)
            
            if players_came_online or players_went_offline:
                # Mudanças reais: jogadores entraram ou saíram
                should_send_notification = True
                print(f"OK Mudanças detectadas: +{len(players_came_online)} jogadores entraram, -{len(players_went_offline)} jogadores saíram")
            elif len(current_online) == 0 and len(self.online_players) > 0:
                # Todos os jogadores saíram offline (mudança de >0 para 0)
                should_send_notification = True
                print("OK Todos os jogadores saíram offline - enviando notificação")
            elif force_send:
                # Forçar envio (útil para teste manual / pós-reset)
                should_send_notification = True
                print("OK Envio forçado de players_online")
            # Removido: elif len(current_online) == 0 and len(self.online_players) == 0
            # Não enviar notificação se já estava 0 e continua 0
            
            if should_send_notification:
                # Sem controle de spam: sempre enviar quando houver mudanças
                self._send_status_notification(
                    players_came_online,
                    players_went_offline,
                    current_online,
                    force=force_send,
                )
                self._force_next_notification = False
            else:
                print(f"OK Nenhuma mudança detectada: {len(current_online)} jogadores online")
            
        except Exception as e:
            print(f"ERRO ao detectar mudanças de status: {e}")

    def _sync_player_attributes_cache(self, steam_ids: List[str]):
        """Sincronizar atributos do SCUM.db para o player_attributes_cache do SSM.db"""
        if not steam_ids:
            return
            
        try:
            from app.extensions import get_services
            services = get_services()
            scum_db_path = services.get_scum_db_path()
            ssm_db_path = services.get_ssm_db_path()
        except Exception:
            scum_db_path = None
            ssm_db_path = None

        if not scum_db_path:
            try:
                base_dir = os.path.dirname(self.gameplay_logs_path)
                candidate = os.path.join(base_dir, "SCUM.db")
                if os.path.exists(candidate):
                    scum_db_path = candidate
            except Exception:
                pass
        if not scum_db_path:
            scum_db_path = "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"

        if not ssm_db_path:
            ssm_db_path = "data/SSM.db"

        if not os.path.exists(scum_db_path):
            print(f"AVISO: SCUM.db não encontrado em {scum_db_path} para sincronizar atributos")
            return

        try:
            from utils.scum_db_helper import scum_db_readonly_connection_strict
            from utils.scum_attributes_editor import resolve_prisoner_identifier, get_prisoner_attributes
            from core.database.connector import DatabaseConnector
        except ImportError as err:
            print(f"ERRO ao importar módulos necessários para sincronização de atributos: {err}")
            return

        print(f"INFO: Sincronizando atributos de {len(steam_ids)} jogadores do SCUM.db para o cache")

        try:
            with scum_db_readonly_connection_strict(scum_db_path) as scum_conn:
                scum_cursor = scum_conn.cursor()
                
                for steam_id in steam_ids:
                    try:
                        ident_info = resolve_prisoner_identifier(scum_cursor, steam_id)
                        if not ident_info:
                            continue
                        prisoner_id = ident_info["prisoner_id"]
                        attrs = get_prisoner_attributes(scum_cursor, prisoner_id)
                        if not attrs:
                            continue
                            
                        # Atualizar ou Inserir no SSM.db (incluindo prisoner_id)
                        with DatabaseConnector.get_connection(ssm_db_path, write_mode=True) as ssm_conn:
                            ssm_cursor = ssm_conn.cursor()
                            ssm_cursor.execute(
                                """
                                INSERT INTO player_attributes_cache (steam_id, strength, constitution, dexterity, intelligence, prisoner_id, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                                ON CONFLICT(steam_id) DO UPDATE SET
                                    strength = excluded.strength,
                                    constitution = excluded.constitution,
                                    dexterity = excluded.dexterity,
                                    intelligence = excluded.intelligence,
                                    prisoner_id = excluded.prisoner_id,
                                    updated_at = CURRENT_TIMESTAMP
                                """,
                                (
                                    steam_id,
                                    attrs.get("strength"),
                                    attrs.get("constitution"),
                                    attrs.get("dexterity"),
                                    attrs.get("intelligence"),
                                    prisoner_id
                                )
                            )
                            ssm_conn.commit()
                        print(f"OK: Cache de atributos atualizado para o jogador {steam_id} (prisoner_id={prisoner_id}): {attrs}")
                    except Exception as player_err:
                        print(f"ERRO ao sincronizar atributos do jogador {steam_id}: {player_err}")
                        
        except Exception as e:
            print(f"ERRO na transação de sincronização de atributos: {e}")
    
    def _send_status_notification(self, came_online: set, went_offline: set, current_online: Dict[str, Dict[str, Any]], force: bool = False):
        """Enviar notificação de mudança de status dos jogadores"""
        try:
            if not self.webhook_url:
                print("AVISO Webhook não configurado para jogadores online")
                return

            now = datetime.now()
            has_changes = bool(came_online or went_offline)
            if (not force) and (not has_changes) and self.last_notification_time:
                elapsed = (now - self.last_notification_time).total_seconds()
                if elapsed < self.min_notification_interval:
                    return

            online_count = len(current_online)
            signature = self._build_players_signature(current_online)

            state = self._load_players_online_state()
            last_sig = str(state.get("last_signature") or "")
            last_count = state.get("last_count")
            try:
                last_count_int = int(last_count) if last_count is not None else None
            except Exception:
                last_count_int = None

            # Se não mudou nada (count e conjunto), não atualiza
            if (not force) and last_sig and (last_sig == signature) and (last_count_int == int(online_count)):
                return

            # Debounce adicional usando state.last_updated_at
            try:
                last_updated_at = state.get("last_updated_at")
                if (not force) and (not has_changes) and last_updated_at:
                    try:
                        last_dt = datetime.fromisoformat(str(last_updated_at))
                        if (now - last_dt).total_seconds() < float(self.min_notification_interval):
                            return
                    except Exception:
                        pass
            except Exception:
                pass
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Criar embed com lista única de jogadores online
            embed = {
                "title": f"⚔️ SCUM Server ({online_count} online)",
                "color": 0x00FF00 if online_count > 0 else 0xFF0000,
                "footer": {
                    "text": f"SCUM Server Manager | Last update: {timestamp}"
                }
            }
            
            # Adicionar lista completa de jogadores online
            if current_online:
                online_list = []
                for steam_id, player_data in current_online.items():
                    # Calcular tempo online
                    last_activity = player_data.get('last_activity')
                    if last_activity:
                        time_online = datetime.utcnow() - last_activity
                        hours = int(time_online.total_seconds() // 3600)
                        minutes = int((time_online.total_seconds() % 3600) // 60)
                        
                        if hours > 0:
                            time_str = f"{hours}h {minutes}min"
                        else:
                            time_str = f"{minutes}min"
                    else:
                        time_str = "0min"
                    
                    online_list.append(f"• {player_data['player_name']} ({time_str})")

                # Respeitar limites do Discord:
                # - máximo 1024 caracteres por field.value
                # - máximo 25 fields por embed
                fields = []
                current_chunk = []
                current_len = 0
                max_value_len = 1024
                for line in online_list:
                    # +1 do \n
                    add_len = len(line) + (1 if current_chunk else 0)
                    if current_len + add_len > max_value_len:
                        fields.append(
                            {
                                "name": "Online Players:",
                                "value": "\n".join(current_chunk) if current_chunk else "• (empty)",
                                "inline": False,
                            }
                        )
                        current_chunk = [line]
                        current_len = len(line)
                    else:
                        current_chunk.append(line)
                        current_len += add_len

                    if len(fields) >= 25:
                        break

                if len(fields) < 25 and current_chunk:
                    fields.append(
                        {
                            "name": "Online Players:",
                            "value": "\n".join(current_chunk),
                            "inline": False,
                        }
                    )

                # Se estourar o limite de fields, indicar truncamento
                if len(fields) >= 25 and len(online_list) > sum(len(f["value"].split("\n")) for f in fields if f.get("value")):
                    fields[-1]["value"] = fields[-1]["value"] + "\n• ..."

                embed["fields"] = fields
            else:
                embed["fields"] = [{
                    "name": "Online Players:",
                    "value": "• No players online at the moment",
                    "inline": False
                }]
            
            self._send_or_edit_players_online_message(embed)

            # Atualizar titulo do canal com contador (via bot token), apenas quando o contador mudar.
            try:
                if force or (last_count_int is None) or (int(online_count) != int(last_count_int)):
                    self._rename_discord_channel_online_count(online_count)
                    
                    # Atualizar status (presença) e apelido do Bot no Discord
                    from core.discord_bot_service import DiscordBotService
                    svc = DiscordBotService._instance
                    if svc:
                        max_players = self.config.get("server", {}).get("max_players", 64)
                        svc.update_bot_status(int(online_count), max_players)
            except Exception as e_bot:
                print(f"AVISO: Falha ao atualizar status do Bot: {e_bot}")

            self.last_notification_time = now
            self._update_players_online_state(
                {
                    "last_signature": signature,
                    "last_count": int(online_count),
                    "last_updated_at": now.isoformat(),
                }
            )

            if came_online:
                print(f"OK Lista atualizada: {len(came_online)} jogadores entraram online")
            if went_offline:
                print(f"OK Lista atualizada: {len(went_offline)} jogadores saíram offline")
                
        except Exception as e:
            print(f"ERRO ao enviar notificação de status: {e}")
    
    def get_online_players(self) -> Dict[str, Any]:
        """Obter lista de jogadores online"""
        return {
            'players': self.online_players,
            'count': len(self.online_players),
            'last_check': self.last_check_time.isoformat(),
            'status': 'monitoring' if self.is_monitoring else 'stopped'
        }
    
    def get_online_players_list(self) -> List[Dict[str, Any]]:
        """Obter lista simplificada de jogadores online"""
        players_list = []
        for steam_id, player_data in self.online_players.items():
            # Obter informações adicionais do Steam API
            steam_info = self.steam_api.get_player_info(steam_id)
            
            player_info = {
                'steam_id': steam_id,
                'player_name': player_data['player_name'],
                'player_id': player_data['player_id'],
                'last_activity': player_data['last_activity'].isoformat(),
                'coordinates': player_data['last_coordinates'],
                'activity_types': player_data['activity_types'],
                'total_activities': player_data['total_activities'],
                'steam_info': steam_info
            }
            players_list.append(player_info)
        
        return players_list
    
    def force_check(self) -> Dict[str, Any]:
        """Forçar verificação imediata dos jogadores online"""
        # Forçar envio de notificação mesmo sem mudanças (útil para teste)
        self._force_next_notification = True
        self._check_online_players()
        return self.get_online_players()
