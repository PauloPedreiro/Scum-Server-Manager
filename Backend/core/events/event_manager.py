import sqlite3



import threading



import time



import requests



import json



from datetime import datetime, timedelta



from typing import Dict, Any, List, Optional



from core.database.connector import DatabaseConnector



from core.rcon_queue_manager import RconQueueManager



from core.webhooks.manager import WebhooksManager



from utils.logger import StructuredLogger







HOMOLOGATION_WEBHOOK = "https://discord.com/api/webhooks/1518287982560415816/dbpUCb77mCpcccp2kUvQyzVd1r8XgxxhZIv_-Hyx1m7jq5YotdRAoDnp_XR5OB0Icx0m"







class EventManager:



    _instance: Optional['EventManager'] = None



    _lock = threading.Lock()







    @classmethod



    def get_instance(cls, ssm_db_path: str = "data/SSM.db", logger: Optional[Any] = None) -> 'EventManager':



        with cls._lock:



            if cls._instance is None:



                cls._instance = cls(ssm_db_path=ssm_db_path, logger=logger)



            return cls._instance







    def __init__(self, ssm_db_path: str = "data/SSM.db", logger: Optional[Any] = None):



        self.ssm_db_path = ssm_db_path



        self.logger = logger or StructuredLogger()



        self._running = False



        self._thread: Optional[threading.Thread] = None



        self.ensure_tables()







    def ensure_tables(self):



        """Inicializa as tabelas necessárias no SSM.db se não existirem."""



        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



            cursor = conn.cursor()



            



            # Tabela de configurações de eventos



            cursor.execute("""



                CREATE TABLE IF NOT EXISTS event_configs (



                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,



                    name TEXT UNIQUE NOT NULL,



                    description TEXT,



                    webhook_url TEXT,



                    duration_minutes INTEGER NOT NULL DEFAULT 60,



                    recurrence_interval_minutes INTEGER,



                    schedule_type TEXT DEFAULT 'manual', -- 'manual', 'daily', 'interval'



                    schedule_value TEXT, -- time like '14:00' or interval in minutes



                    status TEXT DEFAULT 'inactive', -- 'inactive', 'active'



                    last_start_time TEXT,



                    last_recurrence_time TEXT,



                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP



                )



            """)







            # Tabela de coordenadas associadas ao evento



            cursor.execute("""



                CREATE TABLE IF NOT EXISTS event_coordinates (



                    coord_id INTEGER PRIMARY KEY AUTOINCREMENT,



                    event_id INTEGER,



                    name TEXT NOT NULL,



                    x REAL NOT NULL,



                    y REAL NOT NULL,



                    z REAL NOT NULL,



                    FOREIGN KEY(event_id) REFERENCES event_configs(event_id) ON DELETE CASCADE



                )



            """)







            # Tabela de comandos iniciais a serem executados no evento



            cursor.execute("""



                CREATE TABLE IF NOT EXISTS event_startup_commands (



                    startup_id INTEGER PRIMARY KEY AUTOINCREMENT,



                    event_id INTEGER,



                    command_string TEXT NOT NULL,



                    order_index INTEGER DEFAULT 0,



                    recurrence_interval_minutes INTEGER DEFAULT NULL,



                    last_execution_time TEXT DEFAULT NULL,



                    FOREIGN KEY(event_id) REFERENCES event_configs(event_id) ON DELETE CASCADE



                )



            """)







            # Verificar e adicionar colunas de recorrência por comando na tabela event_startup_commands se não existirem



            cursor.execute("PRAGMA table_info(event_startup_commands)")



            cols = [col[1] for col in cursor.fetchall()]



            if cols and "recurrence_interval_minutes" not in cols:



                cursor.execute("ALTER TABLE event_startup_commands ADD COLUMN recurrence_interval_minutes INTEGER DEFAULT NULL")



            if cols and "last_execution_time" not in cols:



                cursor.execute("ALTER TABLE event_startup_commands ADD COLUMN last_execution_time TEXT DEFAULT NULL")







            # Tabela de comandos homologados (testados com sucesso)



            cursor.execute("""



                CREATE TABLE IF NOT EXISTS tested_commands (



                    command_id INTEGER PRIMARY KEY AUTOINCREMENT,



                    command_string TEXT UNIQUE NOT NULL,



                    requires_coordinates INTEGER DEFAULT 0,



                    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,



                    status TEXT NOT NULL



                )



            """)







            # Migração caso a coluna requires_coordinates não exista



            cursor.execute("PRAGMA table_info(tested_commands)")



            columns = [col[1] for col in cursor.fetchall()]



            if columns and "requires_coordinates" not in columns:



                cursor.execute("ALTER TABLE tested_commands ADD COLUMN requires_coordinates INTEGER DEFAULT 0")







            # Migração para a tabela event_configs (aviso prévio de 30 min e rastreio de mensagens)



            cursor.execute("PRAGMA table_info(event_configs)")



            ev_cols = [col[1] for col in cursor.fetchall()]



            if ev_cols and "last_warning_time" not in ev_cols:



                cursor.execute("ALTER TABLE event_configs ADD COLUMN last_warning_time TEXT DEFAULT NULL")



            if ev_cols and "discord_message_ids" not in ev_cols:



                cursor.execute("ALTER TABLE event_configs ADD COLUMN discord_message_ids TEXT DEFAULT NULL")







            # Homologar comando default na primeira versão



            cursor.execute("""



                INSERT OR IGNORE INTO tested_commands (command_string, requires_coordinates, status)



                VALUES ('#ScheduleWorldEvent BP_CargoDropEvent', 1, 'success')



            """)







            # Sanetizar registros antigos com coordenadas duplicadas da tabela



            cursor.execute("""



                DELETE FROM tested_commands



                WHERE command_string LIKE '#ScheduleWorldEvent BP_CargoDropEvent %'



            """)







    def start(self):



        """Inicia o loop do agendador de eventos em background."""



        try:



            now = datetime.now()



            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



                conn.row_factory = sqlite3.Row



                cur = conn.execute("SELECT event_id, name, status, last_start_time, duration_minutes, discord_message_ids FROM event_configs")



                events = cur.fetchall()



            



            for ev in events:



                event_id = ev["event_id"]



                status = ev["status"]



                discord_message_ids = ev["discord_message_ids"]



                



                if status == "active":



                    last_start_str = ev["last_start_time"]



                    if last_start_str:



                        try:



                            last_start = datetime.fromisoformat(last_start_str)



                            elapsed_minutes = (now - last_start).total_seconds() / 60.0



                            duration = ev["duration_minutes"]



                            if elapsed_minutes >= duration:



                                self.logger.info(f"Evento {ev['name']} expirou enquanto o SSM estava desligado. Finalizando...")



                                self.stop_event(event_id)



                                continue



                            else:



                                # Evento ainda ativo — garantir mensagem no canal



                                self.logger.info(f"Evento ativo detectado na inicialização: {ev['name']}. Verificando mensagem no canal...")



                                ev_dict = dict(ev)



                                threading.Thread(



                                    target=self._ensure_event_message_exists,



                                    args=(ev_dict,),



                                    daemon=True



                                ).start()



                        except Exception as e:



                            self.logger.error(f"Erro ao verificar expiração do evento {ev['name']}: {e}")



                



                if status == "inactive" and discord_message_ids:



                    self.logger.info(f"Limpando mensagens pendentes do Discord para o evento inativo: {ev['name']}")



                    self._clear_discord_messages(event_id)



        except Exception as e:



            self.logger.error(f"Erro ao realizar limpeza de eventos na inicialização: {e}")







        with self._lock:



            if self._running:



                return



            self._running = True



            self._thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="EventSchedulerThread")



            self._thread.start()



            self.logger.info("EventScheduler iniciado")







    def _ensure_event_message_exists(self, event_config: dict):

        """Verifica se a mensagem do evento ainda existe no Discord. Se não, recria."""

        try:

            import time as _time

            _time.sleep(5)  # aguarda bot estar pronto



            bot_token = self._get_bot_token()

            channel_id = self._get_event_channel_id()

            if not bot_token or not channel_id:

                return



            event_id = event_config["event_id"]



            # Busca status e IDs de mensagens salvas no banco

            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:

                conn.row_factory = sqlite3.Row

                cur = conn.execute("SELECT status, name, discord_message_ids FROM event_configs WHERE event_id = ?", (event_id,))

                row = cur.fetchone()



            if not row or row["status"] != "active":

                self.logger.info(f"Verificação abortada: o evento {event_id} ({event_config.get('name')}) não está mais ativo.")

                return



            msg_ids = []

            if row and row["discord_message_ids"]:

                msg_ids = [m.strip() for m in row["discord_message_ids"].split(",") if m.strip()]



            # Verifica se alguma mensagem do bot ainda existe

            message_exists = False

            for entry in msg_ids:

                if not entry.startswith("bot:"):

                    continue

                msg_id = entry[4:]

                try:

                    res = requests.get(

                        f"https://discord.com/api/v10/channels/{channel_id}/messages/{msg_id}",

                        headers={"Authorization": f"Bot {bot_token}"},

                        timeout=10

                    )

                    if res.status_code == 200:

                        message_exists = True

                        break

                except Exception:

                    pass



            if not message_exists:

                self.logger.info(f"Mensagem do evento '{event_config['name']}' não encontrada no Discord. Recriando...")

                # Limpa IDs inválidos do banco

                with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:

                    conn.execute("UPDATE event_configs SET discord_message_ids = NULL WHERE event_id = ?", (event_id,))

                # Reenvia a mensagem de início com o botão

                self._send_discord_notification(event_config, "start")

            else:

                self.logger.info(f"Mensagem do evento '{event_config['name']}' confirmada no Discord.")

        except Exception as e:

            self.logger.error(f"Erro ao verificar/recriar mensagem do evento {event_config.get('name', '?')}: {e}")



    def stop(self):



        """Para o loop do agendador de eventos."""



        with self._lock:



            if not self._running:



                return



            self._running = False



        if self._thread:



            self._thread.join(timeout=3.0)



            self._thread = None



        self.logger.info("EventScheduler parado")







    def parse_scum_coordinates_in_command(self, command: str) -> str:



        """



        Detecta se a string do comando contém coordenadas no formato SCUM:



        {X=... Y=... Z=...|P=...}



        E substitui pelo formato limpo: X Y 0 apenas se for o comando #ScheduleWorldEvent.



        """



        if not command:



            return command



        # Apenas converte para X Y 0 se for o comando #ScheduleWorldEvent



        if not command.strip().startswith("#ScheduleWorldEvent"):



            return command



        import re



        coord_pattern = r'\{X=([\d\.\-]+)[,\s]+Y=([\d\.\-]+)[,\s]+Z=([\d\.\-]+)[^}]*\}'



        match = re.search(coord_pattern, command)



        if match:



            x = match.group(1)



            y = match.group(2)



            replacement = f"{x} {y} 0"



            return re.sub(coord_pattern, replacement, command)



        return command







    def check_requires_coordinates(self, original_command: str) -> bool:



        """



        Verifica se a string de comando original enviada pelo admin exige/contém coordenadas.



        """



        if not original_command:



            return False



        



        command_clean = original_command.strip()



        



        # Caso 1: Contém o formato de telemetria SCUM {X=... Y=...}



        if "{X=" in command_clean or "Y=" in command_clean:



            return True



            



        # Caso 2: Contém coordenadas prontas no final (ex: #ScheduleWorldEvent BP_CargoDropEvent 123 456 0)



        import re



        if re.search(r'#ScheduleWorldEvent\s+\w+\s+[\d\.\-]+', command_clean):



            return True



            



        return False







    def test_command(self, command: str) -> Dict[str, Any]:



        """



        Executa um comando RCON de teste imediatamente sem inserir automaticamente na lista de homologados.



        """



        # 1. Verificar se requer coordenadas com base no input original



        requires_coords = 1 if self.check_requires_coordinates(command) else 0



        



        # 2. Filtrar/sanitizar coordenadas para execução RCON



        runnable_command = self.parse_scum_coordinates_in_command(command)



        



        self.logger.info(f"Testando comando RCON: {runnable_command}")



        rcon_mgr = RconQueueManager.get_instance()



        



        try:



            # Executa com alta prioridade



            response = rcon_mgr.execute_command_sync(runnable_command, delay_after=0.1, priority=1, timeout=15.0)



            



            # Enviar relatório para o webhook homologador global



            self.send_homologation_webhook(runnable_command, "success")



            



            return {"success": True, "response": response}



        except Exception as e:



            error_str = str(e)



            self.logger.error(f"Erro ao testar comando RCON: {error_str}")



            



            # Enviar relatório para o webhook homologador global



            self.send_homologation_webhook(runnable_command, "failed", error_str)



            



            return {"success": False, "response": error_str}







    def sanitize_tested_command(self, command: str) -> str:



        """



        Sanitiza o comando testado para evitar salvar registros duplicados com coordenadas.



        Por exemplo: '#ScheduleWorldEvent BP_CargoDropEvent 304552.750 -878289.000 0'



        deve ser salvo simplesmente como '#ScheduleWorldEvent BP_CargoDropEvent'.



        """



        if not command:



            return command



        command_clean = command.strip()



        import re



        # Combina '#ScheduleWorldEvent <NomeDoEvento>' seguido por um ou mais números



        match = re.match(r'^(#ScheduleWorldEvent\s+\w+)(?:\s+[\d\.\-]+)+$', command_clean)



        if match:



            return match.group(1)



        return command_clean







    def _register_tested_command(self, command: str, status: str, requires_coordinates: int = 0):



        try:



            command = self.sanitize_tested_command(command)



            # Se for um comando que conhecemos que exige coordenadas, como #ScheduleWorldEvent, garantir que seja 1



            if command.startswith('#ScheduleWorldEvent'):



                requires_coordinates = 1



                



            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



                conn.execute("""



                    INSERT OR REPLACE INTO tested_commands (command_string, requires_coordinates, status, tested_at)



                    VALUES (?, ?, ?, datetime('now'))



                """, (command, requires_coordinates, status))



        except Exception as e:



            self.logger.error(f"Erro ao salvar comando testado no banco: {e}")







    def send_homologation_webhook(self, command: str, status: str, error_details: Optional[str] = None):



        """Envia o comando testado para a API de homologação do SSM."""



        def run():



            try:



                title = "🔧 Comando Homologado com Sucesso" if status == "success" else "❌ Falha no Teste de Comando"



                color = 0x00FF00 if status == "success" else 0xFF0000



                



                embed = {



                    "title": title,



                    "color": color,



                    "fields": [



                        {"name": "Comando", "value": f"`{command}`", "inline": False},



                        {"name": "Status", "value": status.upper(), "inline": True},



                        {"name": "Data", "value": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "inline": True}



                    ],



                    "footer": {"text": "SSM 3.0 Homologation Engine"}



                }



                



                if error_details:



                    embed["fields"].append({"name": "Erro", "value": f"```{error_details}```", "inline": False})







                payload = {"embeds": [embed]}



                requests.post(HOMOLOGATION_WEBHOOK, json=payload, timeout=10)



            except Exception as e:



                self.logger.error(f"Falha ao enviar webhook de homologação: {e}")







        threading.Thread(target=run, daemon=True).start()







    def _get_bot_token(self) -> Optional[str]:

        """Lê o bot token do config.json."""

        try:

            import os

            config_path = "data/config.json"

            if not os.path.exists(config_path):

                return None

            with open(config_path, "r", encoding="utf-8") as f:

                config = json.load(f)

            return config.get("discord_bot", {}).get("bot_token") or None

        except Exception as e:

            self.logger.error(f"Erro ao ler bot_token do config: {e}")

            return None



    def _get_event_channel_id(self) -> Optional[str]:

        """Lê o channel_id do canal de eventos do webhooks.json."""

        try:

            mgr = WebhooksManager("data/webhooks.json")

            raw = mgr.get_webhook_config("events") if hasattr(mgr, "get_webhook_config") else None

            if raw and isinstance(raw, dict):

                return str(raw.get("target", {}).get("channel", {}).get("id") or "")

            # Fallback: parse JSON diretamente

            import os

            wh_path = "data/webhooks.json"

            if os.path.exists(wh_path):

                with open(wh_path, "r", encoding="utf-8") as f:

                    wh_data = json.load(f)

                events_cfg = wh_data.get("events", {}).get("events", {})

                return str(events_cfg.get("target", {}).get("channel", {}).get("id") or "")

        except Exception as e:

            self.logger.error(f"Erro ao ler channel_id de eventos: {e}")

        return None



    def _send_discord_notification(self, event_config: Dict[str, Any], stage: str, extra_msg: str = ""):

        """Envia notificações de eventos para o Discord."""

        if stage == "recurrence":

            return

        def run():
            def format_minutes(minutes) -> str:
                try:
                    mins = int(minutes)
                    if mins <= 0:
                        return "0m"
                    h = mins // 60
                    m = mins % 60
                    if h > 0 and m > 0:
                        return f"{h}h {m}m"
                    elif h > 0:
                        return f"{h}h"
                    return f"{m}m"
                except Exception:
                    return f"{minutes}m"

            try:

                # 1. Determinar o webhook correto a usar

                webhook_url = event_config.get("webhook_url")

                if not webhook_url:

                    # Tenta ler do webhooks.json global

                    try:

                        mgr = WebhooksManager("data/webhooks.json")

                        webhook_url = mgr.get_webhook("events")

                    except Exception:

                        pass



                if not webhook_url:

                    self.logger.warn("Nenhum webhook configurado para notificações de eventos")

                    return



                # 2. Montar embed

                if stage == "warning":

                    title = f"🔔 [WARNING] Event Starting Soon: {event_config['name']}"

                    description = event_config.get("description") or "Get ready!"

                    color = 0xF1C40F # Laranja/Amarelo

                elif stage == "start":

                    title = f"📅 Event Started: {event_config['name']}"

                    description = event_config.get("description") or "No description."

                    color = 0x00FF00 # Verde

                else: # end

                    title = f"🏁 Event Finished: {event_config['name']}"

                    description = "The event has ended."

                    color = 0xE74C3C # Vermelho



                embed = {

                    "title": title,

                    "description": description,

                    "color": color,

                    "fields": [

                        {"name": "Duration", "value": format_minutes(event_config['duration_minutes']), "inline": True},

                    ],

                    "footer": {"text": "SSM 3.0 Event Engine"}

                }



                if event_config.get("recurrence_interval_minutes"):

                    embed["fields"].append({

                        "name": "Recurrence Interval",

                        "value": format_minutes(event_config['recurrence_interval_minutes']),

                        "inline": True

                    })



                if extra_msg:

                    embed["fields"].append({"name": "Details", "value": extra_msg, "inline": False})



                # 3. Para stage=start: enviar via bot REST API (necessário para botões interativos)

                if stage == "start":

                    bot_token = self._get_bot_token()

                    channel_id = self._get_event_channel_id()

                    if bot_token and channel_id:

                        payload = {

                            "embeds": [embed],

                            "components": [

                                {

                                    "type": 1,

                                    "components": [

                                        {

                                            "type": 2,

                                            "style": 1,

                                            "label": "Pegar Código",

                                            "custom_id": f"teleport_event:{event_config['event_id']}",

                                            "emoji": {"name": "🌀"}

                                        }

                                    ]

                                }

                            ]

                        }

                        res = requests.post(

                            f"https://discord.com/api/v10/channels/{channel_id}/messages",

                            json=payload,

                            headers={"Authorization": f"Bot {bot_token}"},

                            timeout=10

                        )

                        if res.status_code in (200, 201):

                            try:

                                msg_id = res.json().get("id")

                                if msg_id:

                                    self._append_discord_message_id(event_config["event_id"], msg_id, source="bot")

                            except Exception as e:

                                self.logger.error(f"Erro ao obter ID da mensagem do bot: {e}")

                        else:

                            self.logger.error(f"Erro ao enviar mensagem de inicio via bot: {res.status_code} {res.text}")

                        return

                    else:

                        self.logger.warn("bot_token ou channel_id não disponível para mensagem de início com botão")



                # 4. Para outros stages: usar webhook padrão

                payload = {"embeds": [embed]}

                url_with_wait = webhook_url

                if "?" not in webhook_url:

                    url_with_wait = webhook_url + "?wait=true"

                else:

                    url_with_wait = webhook_url + "&wait=true"



                res = requests.post(url_with_wait, json=payload, timeout=10)

                if res.status_code in (200, 201, 204):

                    try:

                        msg_id = res.json().get("id")

                        if msg_id:

                            self._append_discord_message_id(event_config["event_id"], msg_id, source="webhook")

                    except Exception as e:

                        self.logger.error(f"Erro ao obter ID da mensagem do Discord: {e}")

            except Exception as e:

                self.logger.error(f"Erro ao enviar notificação de evento: {e}")



        threading.Thread(target=run, daemon=True).start()







    def _append_discord_message_id(self, event_id: int, msg_id: str, source: str = "webhook"):

        """Persiste ID de mensagem no banco, prefixando com 'bot:' se enviada pelo bot."""

        try:

            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:

                cursor = conn.execute("SELECT discord_message_ids FROM event_configs WHERE event_id = ?", (event_id,))

                row = cursor.fetchone()

                current_ids = []

                if row and row[0]:

                    current_ids = [m.strip() for m in row[0].split(",") if m.strip()]

                entry = f"bot:{msg_id}" if source == "bot" else str(msg_id)

                current_ids.append(entry)

                conn.execute("UPDATE event_configs SET discord_message_ids = ? WHERE event_id = ?", (",".join(current_ids), event_id))

        except Exception as e:

            self.logger.error(f"Erro ao salvar ID de mensagem do Discord no banco: {e}")







    def _clear_discord_messages(self, event_id: int):
        # Limpar códigos temporários de teleporte deste evento do JSON
        try:
            import os
            import json
            import threading
            from pathlib import Path
            codes_file = str(Path(self.ssm_db_path).parent / "event_teleport_codes.json")
            if os.path.exists(codes_file):
                lock = threading.Lock()
                with lock:
                    with open(codes_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if "codes" in data:
                        new_codes = {}
                        for code, entry in data["codes"].items():
                            if entry.get("event_id") != event_id:
                                new_codes[code] = entry
                        data["codes"] = new_codes
                        
                        with open(codes_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"Códigos temporários de teleporte do evento {event_id} foram limpos.")
        except Exception as e:
            self.logger.error(f"Erro ao limpar códigos de teleporte do evento {event_id} no JSON: {e}")

        # Busca a URL do webhook

        event = self.get_event(event_id)

        if not event:

            return



        webhook_url = event.get("webhook_url")

        if not webhook_url:

            try:

                mgr = WebhooksManager("data/webhooks.json")

                webhook_url = mgr.get_webhook("events")

            except Exception:

                pass



        # Busca as mensagens salvas

        msg_ids = []

        try:

            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:

                cursor = conn.execute("SELECT discord_message_ids FROM event_configs WHERE event_id = ?", (event_id,))

                row = cursor.fetchone()

                if row and row[0]:

                    msg_ids = [m.strip() for m in row[0].split(",") if m.strip()]

                conn.execute("UPDATE event_configs SET discord_message_ids = NULL WHERE event_id = ?", (event_id,))

        except Exception as e:

            self.logger.error(f"Erro ao ler/limpar IDs de mensagens do Discord no banco: {e}")

            return



        if not msg_ids:

            return



        bot_token = self._get_bot_token()



        # Deleta as mensagens no Discord de forma assíncrona

        def run_delete():

            for entry in msg_ids:

                try:

                    if entry.startswith("bot:"):

                        # Mensagem enviada pelo bot: deletar via REST API com bot token

                        msg_id = entry[4:]

                        channel_id = self._get_event_channel_id()

                        if bot_token and channel_id:

                            res = requests.delete(

                                f"https://discord.com/api/v10/channels/{channel_id}/messages/{msg_id}",

                                headers={"Authorization": f"Bot {bot_token}"},

                                timeout=10

                            )

                            self.logger.info(f"Deleção bot msg {msg_id} retornou status {res.status_code}")

                    else:

                        # Mensagem enviada via webhook: deletar via webhook API

                        if webhook_url:

                            del_url = f"{webhook_url}/messages/{entry}"

                            res = requests.delete(del_url, timeout=10)

                            self.logger.info(f"Deleção webhook msg {entry} retornou status {res.status_code}")

                except Exception as ex:

                    self.logger.error(f"Erro ao deletar mensagem {entry} do Discord: {ex}")



        threading.Thread(target=run_delete, daemon=True).start()







    def _get_restart_cooldown_remaining(self) -> float:



        """Retorna o tempo restante (em segundos) se estiver no período de restart (até 5 min depois), ou 0.0."""



        import os



        try:



            config_path = "data/config.json"



            if not os.path.exists(config_path):



                return 0.0



            



            with open(config_path, "r", encoding="utf-8") as f:



                config = json.load(f)



            



            scheduler_cfg = config.get("scheduler", {})



            if not scheduler_cfg.get("enabled", True):



                return 0.0



                



            restart_times = scheduler_cfg.get("restart_times", [])



            if not restart_times:



                return 0.0



                



            now = datetime.now()



            for time_str in restart_times:



                try:



                    hour, minute = map(int, time_str.split(":"))



                    restart_dt = datetime.combine(now.date(), datetime.min.time().replace(hour=hour, minute=minute))



                    



                    diff_seconds = (now - restart_dt).total_seconds()



                    if 0.0 <= diff_seconds <= 300.0:



                        return 300.0 - diff_seconds



                        



                    yesterday_restart_dt = restart_dt - timedelta(days=1)



                    diff_seconds_y = (now - yesterday_restart_dt).total_seconds()



                    if 0.0 <= diff_seconds_y <= 300.0:



                        return 300.0 - diff_seconds_y



                except ValueError:



                    continue



        except Exception as e:



            self.logger.error(f"Erro ao calcular tempo restante do cooldown de restart: {e}")



            



        return 0.0







    def _is_in_restart_cooldown(self) -> bool:



        """Retorna True se estiver atualmente no período de cooldown de restart."""



        return self._get_restart_cooldown_remaining() > 0.0







    def start_event(self, event_id: int) -> bool:



        """Inicia um evento manualmente ou agendado."""



        event = self.get_event(event_id)



        if not event:



            return False







        self.logger.info(f"Iniciando evento: {event['name']}")



        



        # Parar qualquer outro evento ativo para evitar duplicidade de mensagens



        try:



            with DatabaseConnector.get_connection(self.ssm_db_path) as conn:



                conn.row_factory = sqlite3.Row



                cur = conn.execute("SELECT event_id, name FROM event_configs WHERE status = 'active' AND event_id != ?", (event_id,))



                active_events = cur.fetchall()



            for ae in active_events:



                self.logger.info(f"Parando evento ativo anterior '{ae['name']}' antes de iniciar o novo evento '{event['name']}'")



                self.stop_event(ae["event_id"])



        except Exception as e:



            self.logger.error(f"Erro ao parar eventos ativos anteriores: {e}")



        



        # Clear any previous messages (like warning messages) before starting the event



        self._clear_discord_messages(event_id)



        



        now_str = datetime.now().isoformat()



        



        # Atualiza status no banco de dados



        try:



            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



                conn.execute("""



                    UPDATE event_configs 



                    SET status = 'active', last_start_time = ?, last_recurrence_time = ?



                    WHERE event_id = ?



                """, (now_str, now_str, event_id))



        except Exception as e:



            self.logger.error(f"Erro ao atualizar status do evento para ativo: {e}")



            return False







        # Envia a notificação do Discord

        self._send_discord_notification(event, "start")



        # Registra view persistente no bot para o botão de teleporte

        try:

            from core.discord_bot_service import DiscordBotService

            svc = DiscordBotService._instance if hasattr(DiscordBotService, '_instance') else None

            if svc and svc._bot:

                svc._bot.register_event_view(event_id)

        except Exception as e:

            self.logger.error(f"Erro ao registrar view de evento no bot: {e}")







        # Executa comandos iniciais



        self._execute_event_commands(event_id)



        return True







    def stop_event(self, event_id: int) -> bool:



        """Finaliza um evento."""



        event = self.get_event(event_id)



        if not event:



            return False







        self.logger.info(f"Finalizando evento: {event['name']}")



        



        # Atualiza status no banco de dados



        try:



            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



                conn.execute("""



                    UPDATE event_configs 



                    SET status = 'inactive'



                    WHERE event_id = ?



                """, (event_id,))



        except Exception as e:



            self.logger.error(f"Erro ao atualizar status do evento para inativo: {e}")



            return False







        # Limpa as notificações do Discord do canal



        self._clear_discord_messages(event_id)



        return True







    def _execute_event_commands(self, event_id: int):



        """Busca os comandos do evento e enfileira-os com 10 segundos de cooldown."""



        def run_exec():



            cooldown_left = self._get_restart_cooldown_remaining()



            if cooldown_left > 0:



                self.logger.info(f"Aguardando {cooldown_left:.1f} segundos para executar os comandos do evento {event_id} devido ao reinício do servidor.")



                time.sleep(cooldown_left)







            commands = self.list_startup_commands(event_id)



            if not commands:



                return







            now_str = datetime.now().isoformat()



            rcon_mgr = RconQueueManager.get_instance()



            for idx, cmd in enumerate(commands):



                cmd_str = cmd["command_string"]



                # Cooldown de 10 segundos entre cada comando usando delay_after



                rcon_mgr.enqueue_command(cmd_str, delay_after=10.0, priority=10)



                self.logger.debug(f"Comando do evento {event_id} enfileirado: '{cmd_str}'")







            try:



                with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



                    conn.execute("""



                        UPDATE event_startup_commands



                        SET last_execution_time = ?



                        WHERE event_id = ?



                    """, (now_str, event_id))



            except Exception as e:



                self.logger.error(f"Erro ao atualizar tempo de execução dos comandos: {e}")







        threading.Thread(target=run_exec, daemon=True).start()







    def _scheduler_loop(self):



        """Loop do agendador rodando a cada 10 segundos para verificar eventos ativos e agendados."""



        self.logger.info("Loop do EventScheduler rodando...")



        



        while self._running:



            try:



                now = datetime.now()



                events = self.list_events()







                for ev in events:



                    event_id = ev["event_id"]



                    status = ev["status"]



                    last_start_str = ev.get("last_start_time")



                    last_recurrence_str = ev.get("last_recurrence_time")



                    duration = ev["duration_minutes"]



                    recurrence = ev.get("recurrence_interval_minutes")







                    # 1. Tratar eventos ativos



                    if status == "active" and last_start_str:



                        last_start = datetime.fromisoformat(last_start_str)



                        elapsed_minutes = (now - last_start).total_seconds() / 60.0







                        # Verificar se o tempo de duração expirou



                        if elapsed_minutes >= duration:



                            self.stop_event(event_id)



                            continue







                        # Se estiver no cooldown de restart (5 min), suspender comandos recorrentes



                        if self._is_in_restart_cooldown():



                            self.logger.info(f"Comandos recorrentes do evento '{ev['name']}' suspensos devido ao reinício do servidor.")



                            continue







                        # Verificar recorrência global do evento (caso configurada)



                        if recurrence and last_recurrence_str:



                            last_recur = datetime.fromisoformat(last_recurrence_str)



                            recur_elapsed_minutes = (now - last_recur).total_seconds() / 60.0







                            if recur_elapsed_minutes >= recurrence:



                                self.logger.info(f"Recorrência de {recurrence} min atingida para o evento: {ev['name']}")



                                now_str = now.isoformat()



                                # Atualiza o last_recurrence_time no banco



                                with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



                                    conn.execute("""



                                        UPDATE event_configs SET last_recurrence_time = ? WHERE event_id = ?



                                    """, (now_str, event_id))



                                



                                # Envia notificação



                                self._send_discord_notification(ev, "recurrence")



                                # Executa os comandos novamente



                                self._execute_event_commands(event_id)



                                continue







                        # Verificar recorrência individual por comando



                        commands = self.list_startup_commands(event_id)



                        rcon_mgr = RconQueueManager.get_instance()



                        for cmd in commands:



                            cmd_recur = cmd.get("recurrence_interval_minutes")



                            last_exec_str = cmd.get("last_execution_time")



                            



                            ref_time_str = last_exec_str or last_start_str



                            if cmd_recur and cmd_recur > 0 and ref_time_str:



                                ref_time = datetime.fromisoformat(ref_time_str)



                                recur_elapsed_minutes = (now - ref_time).total_seconds() / 60.0



                                



                                if recur_elapsed_minutes >= cmd_recur:



                                    self.logger.info(f"Recorrência de comando ({cmd_recur} min) atingida para: {cmd['command_string']} no evento {ev['name']}")



                                    now_str = now.isoformat()



                                    



                                    try:



                                        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



                                            conn.execute("""



                                                UPDATE event_startup_commands 



                                                SET last_execution_time = ? 



                                                WHERE startup_id = ?



                                            """, (now_str, cmd["startup_id"]))



                                    except Exception as e:



                                        self.logger.error(f"Erro ao atualizar last_execution_time do comando {cmd['startup_id']}: {e}")



                                    



                                    # Envia notificação



                                    self._send_discord_notification(ev, "recurrence", extra_msg=f"Executando novamente: `{cmd['command_string']}`")



                                    # Enfileira o comando



                                    rcon_mgr.enqueue_command(cmd["command_string"], delay_after=10.0, priority=10)







                    # 2. Tratar agendamento automático de eventos inativos



                    elif status == "inactive" and ev["schedule_type"] != "manual":



                        schedule_type = ev["schedule_type"]



                        schedule_val = ev.get("schedule_value")



                        last_warning_str = ev.get("last_warning_time")







                        if schedule_type == "daily" and schedule_val:



                            try:



                                time_part = schedule_val



                                weekdays_part = None



                                if "|" in schedule_val:



                                    time_part, weekdays_part = schedule_val.split("|", 1)



                                



                                target_time = datetime.strptime(time_part.strip(), "%H:%M").time()



                                



                                # Envia aviso de 30 minutos antes se estiver no intervalo



                                target_dt = datetime.combine(now.date(), target_time)



                                diff_seconds = (target_dt - now).total_seconds()



                                minutes_until_start = diff_seconds / 60.0







                                if 0.0 <= minutes_until_start <= 30.0:



                                    # Verificar dia da semana



                                    allowed_weekday = True



                                    if weekdays_part:



                                        current_js_weekday = (now.weekday() + 1) % 7



                                        allowed_weekdays = [int(w) for w in weekdays_part.split(",") if w.strip().isdigit()]



                                        if current_js_weekday not in allowed_weekdays:



                                            allowed_weekday = False



                                    



                                    if allowed_weekday:



                                        already_run_or_warned = False



                                        if last_start_str:



                                            try:



                                                last_start = datetime.fromisoformat(last_start_str)



                                                if last_start.date() == now.date():



                                                    already_run_or_warned = True



                                            except Exception:



                                                pass



                                        if last_warning_str:



                                            try:



                                                last_warn = datetime.fromisoformat(last_warning_str)



                                                if last_warn.date() == now.date():



                                                    already_run_or_warned = True



                                            except Exception:



                                                pass



                                        



                                        if not already_run_or_warned:



                                            self.logger.info(f"Sending 30-minute warning for event: {ev['name']}")



                                            self._send_discord_notification(ev, "warning", extra_msg=f"The event will start in 30 minutes at {time_part.strip()}.")



                                            



                                            # Salvar last_warning_time no banco



                                            with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



                                                conn.execute("""



                                                    UPDATE event_configs SET last_warning_time = ? WHERE event_id = ?



                                                """, (now.isoformat(), event_id))







                                if now.time() >= target_time:



                                    # Verificar se o dia de hoje está nos dias de semana especificados (0=Dom, 1=Seg, ..., 6=Sáb)



                                    if weekdays_part:



                                        current_js_weekday = (now.weekday() + 1) % 7



                                        allowed_weekdays = [int(w) for w in weekdays_part.split(",") if w.strip().isdigit()]



                                        if current_js_weekday not in allowed_weekdays:



                                            continue



                                    



                                    # Verificar se já rodou hoje



                                    should_start = True



                                    if last_start_str:



                                        last_start = datetime.fromisoformat(last_start_str)



                                        if last_start.date() == now.date():



                                            should_start = False



                                    



                                    if should_start:



                                        self.start_event(event_id)



                            except Exception as e:



                                self.logger.error(f"Erro ao processar agendamento diário do evento {event_id}: {e}")







                        elif schedule_type == "interval" and schedule_val:



                            try:



                                interval_minutes = int(schedule_val)



                                should_start = False



                                if not last_start_str:



                                    should_start = True



                                else:



                                    last_start = datetime.fromisoformat(last_start_str)



                                    if (now - last_start).total_seconds() / 60.0 >= interval_minutes:



                                        should_start = True



                                



                                if should_start:



                                    self.start_event(event_id)



                            except Exception as e:



                                self.logger.error(f"Erro ao processar agendamento por intervalo do evento {event_id}: {e}")







            except Exception as e:



                self.logger.error(f"Erro no loop do EventScheduler: {e}")







            # Dorme por 10 segundos



            time.sleep(10)







    # ============================================================================



    # CRUD DE CONFIGURAÇÃO DE EVENTOS



    # ============================================================================







    def create_event(self, name: str, description: str = "", webhook_url: Optional[str] = None, 



                     duration_minutes: int = 60, recurrence_interval_minutes: Optional[int] = None, 



                     schedule_type: str = "manual", schedule_value: Optional[str] = None) -> int:



        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



            cursor = conn.execute("""



                INSERT INTO event_configs 



                (name, description, webhook_url, duration_minutes, recurrence_interval_minutes, schedule_type, schedule_value, status)



                VALUES (?, ?, ?, ?, ?, ?, ?, 'inactive')



            """, (name, description, webhook_url, duration_minutes, recurrence_interval_minutes, schedule_type, schedule_value))



            return cursor.lastrowid







    def update_event(self, event_id: int, name: str, description: str = "", webhook_url: Optional[str] = None, 



                     duration_minutes: int = 60, recurrence_interval_minutes: Optional[int] = None, 



                     schedule_type: str = "manual", schedule_value: Optional[str] = None) -> bool:



        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



            conn.execute("""



                UPDATE event_configs



                SET name = ?, description = ?, webhook_url = ?, duration_minutes = ?, 



                    recurrence_interval_minutes = ?, schedule_type = ?, schedule_value = ?



                WHERE event_id = ?



            """, (name, description, webhook_url, duration_minutes, recurrence_interval_minutes, schedule_type, schedule_value, event_id))



            return True







    def delete_event(self, event_id: int) -> bool:
        # Limpa as notificações do Discord antes de deletar o registro do banco
        try:
            self._clear_discord_messages(event_id)
        except Exception as e:
            self.logger.error(f"Erro ao limpar mensagens do Discord ao deletar evento: {e}")

        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:
            conn.execute("DELETE FROM event_configs WHERE event_id = ?", (event_id,))
            return True







    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:



        with DatabaseConnector.get_connection(self.ssm_db_path) as conn:



            cursor = conn.execute("SELECT * FROM event_configs WHERE event_id = ?", (event_id,))



            row = cursor.fetchone()



            return dict(row) if row else None







    def list_events(self) -> List[Dict[str, Any]]:



        with DatabaseConnector.get_connection(self.ssm_db_path) as conn:



            cursor = conn.execute("SELECT * FROM event_configs ORDER BY event_id DESC")



            return [dict(row) for row in cursor.fetchall()]







    # ============================================================================



    # GERENCIAMENTO DE COORDENADAS



    # ============================================================================







    def add_coordinate(self, event_id: int, name: str, x: float, y: float, z: float) -> int:



        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



            cursor = conn.execute("""



                INSERT INTO event_coordinates (event_id, name, x, y, z)



                VALUES (?, ?, ?, ?, ?)



            """, (event_id, name, x, y, z))



            return cursor.lastrowid







    def remove_coordinate(self, coord_id: int) -> bool:



        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



            conn.execute("DELETE FROM event_coordinates WHERE coord_id = ?", (coord_id,))



            return True







    def list_coordinates(self, event_id: int) -> List[Dict[str, Any]]:



        with DatabaseConnector.get_connection(self.ssm_db_path) as conn:



            cursor = conn.execute("SELECT * FROM event_coordinates WHERE event_id = ? ORDER BY coord_id ASC", (event_id,))



            return [dict(row) for row in cursor.fetchall()]







    # ============================================================================



    # GERENCIAMENTO DE COMANDOS DE EVENTOS



    # ============================================================================







    def add_startup_command(self, event_id: int, command_string: str, order_index: int = 0, recurrence_interval_minutes: Optional[int] = None) -> int:



        command_string = self.parse_scum_coordinates_in_command(command_string)



        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



            cursor = conn.execute("""



                INSERT INTO event_startup_commands (event_id, command_string, order_index, recurrence_interval_minutes)



                VALUES (?, ?, ?, ?)



            """, (event_id, command_string, order_index, recurrence_interval_minutes))



            return cursor.lastrowid







    def remove_startup_command(self, startup_id: int) -> bool:



        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



            conn.execute("DELETE FROM event_startup_commands WHERE startup_id = ?", (startup_id,))



            return True







    def update_startup_command(self, startup_id: int, recurrence_interval_minutes: Optional[int]) -> bool:



        with DatabaseConnector.get_connection(self.ssm_db_path, write_mode=True) as conn:



            conn.execute("""



                UPDATE event_startup_commands 



                SET recurrence_interval_minutes = ?



                WHERE startup_id = ?



            """, (recurrence_interval_minutes, startup_id))



            return True







    def list_startup_commands(self, event_id: int) -> List[Dict[str, Any]]:



        with DatabaseConnector.get_connection(self.ssm_db_path) as conn:



            cursor = conn.execute("""



                SELECT * FROM event_startup_commands 



                WHERE event_id = ? 



                ORDER BY order_index ASC, startup_id ASC



            """, (event_id,))



            return [dict(row) for row in cursor.fetchall()]







    # ============================================================================



    # LISTA DE COMANDOS TESTADOS / HOMOLOGADOS



    # ============================================================================







    def list_tested_commands(self) -> List[Dict[str, Any]]:



        with DatabaseConnector.get_connection(self.ssm_db_path) as conn:



            cursor = conn.execute("SELECT * FROM tested_commands ORDER BY tested_at DESC")



            return [dict(row) for row in cursor.fetchall()]



