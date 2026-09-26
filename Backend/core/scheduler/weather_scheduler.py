"""
Sistema de Agendamento de Sincronização Climática
Gerencia sincronização automática dos dados climáticos do SCUM
"""
from core.database.connector import DatabaseConnector

import threading
import time
import schedule
import configparser
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Callable, Tuple
from utils.logger import StructuredLogger
import sqlite3
import requests
import json
import os
import math
import hashlib



class WeatherScheduler:
    def __init__(
        self,
        config: Dict[str, Any],
        logger: StructuredLogger = None,
        scum_db_path: str = None,
        ssm_db_path: str = None,
    ):
        self.config = config
        self.logger = logger or StructuredLogger()

        # Configurações do agendador climático
        self.scheduler_config = config.get("weather_scheduler", {})
        self.enabled = self.scheduler_config.get("enabled", True)
        self.sync_interval_minutes = self.scheduler_config.get(
            "sync_interval_minutes", 30
        )
        self.auto_start = self.scheduler_config.get("auto_start", True)
        self._scheduler = schedule.Scheduler()

        # Caminhos dos bancos de dados
        self.scum_db_path = (
            scum_db_path or "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
        )
        self.ssm_db_path = ssm_db_path or "data/SSM.db"

        # Estado do agendador
        self.is_running = False
        self.scheduler_thread = None
        self.stop_event = threading.Event()

        # Callbacks para notificações
        self.notification_callbacks: List[Callable] = []

        # Logs de agendamento
        self.schedule_logs = []

        self.logger.info(
            "WeatherScheduler inicializado",
            {
                "enabled": self.enabled,
                "sync_interval_minutes": self.sync_interval_minutes,
            },
        )

    def add_notification_callback(self, callback: Callable):
        """Adicionar callback para notificações"""
        self.notification_callbacks.append(callback)
        self.logger.info(
            f"Callback de notificação climática adicionado: {callback.__name__}"
        )

    def _notify(self, message: str, data: Dict[str, Any] = None):
        """Enviar notificação para todos os callbacks"""
        for callback in self.notification_callbacks:
            try:
                callback(message, data)
            except Exception as e:
                self.logger.error(f"Erro no callback de notificação climática: {e}")

    def _log_schedule_event(self, event: str, data: Dict[str, Any] = None):
        """Registrar evento no log de agendamento"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data or {},
        }
        self.schedule_logs.append(log_entry)

        # Manter apenas os últimos 100 logs
        if len(self.schedule_logs) > 100:
            self.schedule_logs = self.schedule_logs[-100:]

    def _sync_weather_data(self):
        """Sincronizar dados climáticos"""
        try:
            self.logger.info("Iniciando sincronização climática")
            self._log_schedule_event("sync_started")

            # Verificar se o banco SCUM existe
            if not os.path.exists(self.scum_db_path):
                self.logger.error(f"Banco SCUM não encontrado: {self.scum_db_path}")
                self._notify(
                    "❌ Erro: Banco SCUM não encontrado",
                    {"notification_type": "weather_error"},
                )
                return False

            # Conectar ao banco SCUM
            from utils.scum_db_helper import scum_db_readonly_connection

            with scum_db_readonly_connection(self.scum_db_path) as conn:
                cursor = conn.cursor()

                # Buscar dados da tabela weather_parameters
                cursor.execute(
                    """
                    SELECT map_id, user_profile_id, time_of_day, moon_rotation, 
                           base_air_temperature, water_temperature, 
                           should_cumulonimbus_cause_fog, fog_density, data
                    FROM weather_parameters
                    ORDER BY map_id DESC
                    LIMIT 1
                """
                )

                weather_data = cursor.fetchone()

                if not weather_data:
                    self.logger.warn("Nenhum dado climático encontrado no SCUM.db")
                    return False

                # Converter time_of_day para formato legível
                time_of_day = weather_data[2]
                hours = int(time_of_day)
                minutes = int((time_of_day - hours) * 60)
                formatted_time = f"{hours:02d}:{minutes:02d}"

                self.logger.info(f"Dados climáticos obtidos - Hora: {formatted_time}")

                # Sincronizar para SSM.db
                success = self._sync_to_ssm_db(weather_data)

                if success:
                    try:
                        self._update_server_time_state_from_read(time_of_day)
                    except Exception:
                        pass

                    # Enviar notificação para Discord
                    self._send_discord_notification(formatted_time)
                    self._log_schedule_event(
                        "sync_completed",
                        {"time": formatted_time, "temperature": weather_data[4]},
                    )
                    return True

                self._log_schedule_event("sync_failed")
                return False

        except Exception as e:
            self.logger.error(f"Erro na sincronização climática: {e}")
            self._notify(
                f"❌ Erro na sincronização climática: {e}",
                {"notification_type": "weather_error"},
            )
            self._log_schedule_event("sync_error", {"error": str(e)})
            return False

    def _get_last_synced_time_of_day_from_ssm(self) -> Optional[float]:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT time_of_day
                    FROM weather_parameters
                    ORDER BY map_id DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if not row:
                    return None
                return float(row[0])
        except Exception:
            return None

    def _get_latest_weather_snapshot_from_ssm(self) -> Dict[str, Any]:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT time_of_day, moon_rotation, base_air_temperature, water_temperature,
                           should_cumulonimbus_cause_fog, fog_density, sync_timestamp
                    FROM weather_parameters
                    ORDER BY sync_timestamp DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                return dict(row) if row else {}
        except Exception:
            return {}

    def _format_moon_phase(self, moon_rotation: Optional[float]) -> str:
        try:
            if moon_rotation is None:
                return ""
            r = float(moon_rotation)
            if not math.isfinite(r):
                return ""

            # Heurística: o SCUM expõe um valor que cresce com o ciclo lunar.
            # Para exibição amigável, classificamos em 8 fases usando quartis.
            # (Ajuste fino pode ser feito se necessário, mas 9.44 costuma cair em First Quarter.)
            cycle = 37.6
            x = r % cycle
            phase_index = int((x / cycle) * 8.0) % 8
            phases = [
                "New Moon",
                "Waxing Crescent",
                "First Quarter",
                "Waxing Gibbous",
                "Full Moon",
                "Waning Gibbous",
                "Last Quarter",
                "Waning Crescent",
            ]
            return phases[phase_index]
        except Exception:
            return ""

    def _format_fog_label(self, fog_density: Any, cumulonimbus_causes_fog: Any) -> str:
        try:
            dens = 0.0
            try:
                dens = float(fog_density) if fog_density is not None else 0.0
            except Exception:
                dens = 0.0

            causes = False
            try:
                causes = bool(int(cumulonimbus_causes_fog))
            except Exception:
                causes = bool(cumulonimbus_causes_fog)

            if dens >= 0.7:
                return "Heavy Fog"
            if dens >= 0.4:
                return "Medium Fog"
            if dens >= 0.1:
                return "Light Fog"
            if causes:
                return "Fog"
            return "Clear"
        except Exception:
            return ""

    def _timer_tick(self) -> bool:
        """Atualiza o canal timer a cada 60s sem consultar o SCUM.db."""
        try:
            predicted = None
            try:
                predicted = self._predict_server_time_hhmm()
            except Exception:
                predicted = None

            if predicted:
                return bool(self._send_discord_notification(predicted))

            tod = self._get_last_synced_time_of_day_from_ssm()
            if tod is None:
                return True
            h = int(tod)
            m = int((tod - h) * 60)
            return bool(self._send_discord_notification(f"{h:02d}:{m:02d}"))
        except Exception:
            return False

    def _get_server_time_state(self) -> Dict[str, Any]:
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT baseline_time_of_day, baseline_real_ts_utc, time_scale,
                           last_verified_ts_utc, last_real_time_of_day, last_drift_seconds
                    FROM server_time_state
                    WHERE id = 1
                    """
                )
                row = cur.fetchone()
                return dict(row) if row else {}
        except Exception:
            return {}

    def _set_server_time_state(self, patch: Dict[str, Any]) -> None:
        with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0, write_mode=True) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO server_time_state (id, time_scale)
                VALUES (1, 1.0)
                """
            )

            cols = []
            vals = []
            for k, v in (patch or {}).items():
                cols.append(f"{k} = ?")
                vals.append(v)

            cols.append("updated_at = CURRENT_TIMESTAMP")
            sql = "UPDATE server_time_state SET " + ", ".join(cols) + " WHERE id = 1"
            cur.execute(sql, tuple(vals))
            conn.commit()

    def _update_server_time_state_from_read(self, time_of_day: float) -> None:
        now_utc = datetime.utcnow().isoformat()
        state = self._get_server_time_state()

        try:
            prev_baseline_tod = state.get("baseline_time_of_day")
            prev_baseline_ts = state.get("baseline_real_ts_utc")
            prev_real_tod = state.get("last_real_time_of_day")
            prev_verified_ts = state.get("last_verified_ts_utc")

            prev_scale = state.get("time_scale")
            try:
                prev_scale = float(prev_scale) if prev_scale is not None else 1.0
            except Exception:
                prev_scale = 1.0

            if prev_real_tod is not None and prev_verified_ts:
                try:
                    t0 = datetime.fromisoformat(str(prev_verified_ts))
                    t1 = datetime.utcnow()
                    delta_real_s = max(1.0, (t1 - t0).total_seconds())

                    tod0 = float(prev_real_tod)
                    tod1 = float(time_of_day)
                    delta_game_h = tod1 - tod0
                    if delta_game_h < -12.0:
                        delta_game_h += 24.0
                    elif delta_game_h > 12.0:
                        delta_game_h -= 24.0

                    measured_scale = (delta_game_h * 3600.0) / float(delta_real_s)
                    if measured_scale > 0.05 and measured_scale < 50.0:
                        prev_scale = (prev_scale * 0.7) + (measured_scale * 0.3)
                except Exception:
                    pass

            # Drift: comparar previsão atual com leitura real
            drift_s = None
            if prev_baseline_tod is not None and prev_baseline_ts:
                try:
                    bt = datetime.fromisoformat(str(prev_baseline_ts))
                    now_dt = datetime.utcnow()
                    delta_s = (now_dt - bt).total_seconds()
                    predicted = float(prev_baseline_tod) + (delta_s / 3600.0) * float(prev_scale)
                    predicted = predicted % 24.0

                    real = float(time_of_day) % 24.0
                    diff_h = real - predicted
                    if diff_h < -12.0:
                        diff_h += 24.0
                    elif diff_h > 12.0:
                        diff_h -= 24.0
                    drift_s = diff_h * 3600.0
                except Exception:
                    drift_s = None

            self._set_server_time_state(
                {
                    "baseline_time_of_day": float(time_of_day),
                    "baseline_real_ts_utc": now_utc,
                    "time_scale": float(prev_scale),
                    "last_verified_ts_utc": now_utc,
                    "last_real_time_of_day": float(time_of_day),
                    "last_drift_seconds": float(drift_s) if drift_s is not None else None,
                }
            )
        except Exception:
            self._set_server_time_state(
                {
                    "baseline_time_of_day": float(time_of_day),
                    "baseline_real_ts_utc": now_utc,
                    "last_verified_ts_utc": now_utc,
                    "last_real_time_of_day": float(time_of_day),
                }
            )

    def _predict_server_time_hhmm(self) -> Optional[str]:
        state = self._get_server_time_state()
        try:
            baseline_tod = state.get("baseline_time_of_day")
            baseline_ts = state.get("baseline_real_ts_utc")
            if baseline_tod is None or not baseline_ts:
                return None

            scale = state.get("time_scale")
            try:
                scale = float(scale) if scale is not None else 1.0
            except Exception:
                scale = 1.0

            bt = datetime.fromisoformat(str(baseline_ts))
            now_dt = datetime.utcnow()
            delta_s = (now_dt - bt).total_seconds()

            tod = float(baseline_tod) + (delta_s / 3600.0) * float(scale)
            tod = tod % 24.0
            h = int(tod)
            m = int((tod - h) * 60)
            return f"{h:02d}:{m:02d}"
        except Exception:
            return None

    def _sync_to_ssm_db(self, weather_data):
        """Sincronizar dados para o SSM.db"""
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                # Verificar se já existe registro
                cursor.execute("SELECT COUNT(*) FROM weather_parameters")
                count = cursor.fetchone()[0]

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if count > 0:
                    # Atualizar registro existente
                    update_sql = """
                    UPDATE weather_parameters SET 
                        map_id = ?, user_profile_id = ?, time_of_day = ?, moon_rotation = ?, 
                        base_air_temperature = ?, water_temperature = ?, should_cumulonimbus_cause_fog = ?, 
                        fog_density = ?, data = ?, sync_timestamp = ?
                    WHERE map_id = ?
                    """
                    cursor.execute(
                        update_sql, (*weather_data, timestamp, weather_data[0])
                    )
                    self.logger.info(
                        f"Dados climáticos atualizados no SSM.db - {timestamp}"
                    )
                else:
                    # Inserir primeiro registro
                    insert_sql = """
                    INSERT INTO weather_parameters 
                    (map_id, user_profile_id, time_of_day, moon_rotation, base_air_temperature, 
                     water_temperature, should_cumulonimbus_cause_fog, fog_density, data, sync_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    cursor.execute(insert_sql, (*weather_data, timestamp))
                    self.logger.info(
                        f"Primeiro registro climático inserido no SSM.db - {timestamp}"
                    )

                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"ERRO ao sincronizar para SSM.db: {e}")
            return False

    def _read_server_settings_ini(self) -> Dict[str, Any]:
        """Lê parâmetros principais do ServerSettings.ini"""
        try:
            config_dir = (
                self.config.get("paths", {})
                .get("scum_server", {})
                .get("config_directory")
                or "C:\\Servers\\scum\\SCUM\\Saved\\Config\\WindowsServer"
            )
            ini_path = os.path.join(config_dir, "ServerSettings.ini")
            if os.path.exists(ini_path):
                cp = configparser.ConfigParser(strict=False)
                cp.read(ini_path, encoding="utf-8-sig")

                server_name = cp.get("General", "scum.ServerName", fallback="SCUM Server").strip()
                max_players = cp.getint("General", "scum.MaxPlayers", fallback=64)
                time_speed = cp.getfloat("World", "scum.TimeOfDaySpeed", fallback=1.0)
                sunrise = cp.get("World", "scum.SunriseTime", fallback="04:00:00").strip()
                sunset = cp.get("World", "scum.SunsetTime", fallback="23:59:50").strip()

                return {
                    "server_name": server_name or "SCUM Server",
                    "max_players": max(1, max_players),
                    "time_speed": time_speed,
                    "sunrise_time": sunrise,
                    "sunset_time": sunset,
                }
        except Exception as e:
            self.logger.debug(f"Erro ao ler ServerSettings.ini: {e}")

        server_cfg = self.config.get("server", {})
        comm_cfg = self.config.get("communication", {})
        return {
            "server_name": str(comm_cfg.get("server_name") or "SCUM Server"),
            "max_players": int(server_cfg.get("max_players", 64)),
            "time_speed": 1.0,
            "sunrise_time": "04:00:00",
            "sunset_time": "23:59:50",
        }

    def _get_online_players_count(self) -> int:
        """Obtém a contagem de jogadores atualmente online no SSM.db ou no OnlinePlayersMonitor"""
        # 1. Tentar obter direto do serviço OnlinePlayersMonitor em memória (tempo real)
        try:
            from app.extensions import get_services
            services = get_services()
            online_monitor = getattr(services, "online_monitor", None)
            if online_monitor and hasattr(online_monitor, "online_players"):
                return len(online_monitor.online_players)
        except Exception:
            pass

        # 2. Se o monitor não estiver em memória, consultar banco de dados
        try:
            with DatabaseConnector.get_connection(self.ssm_db_path, timeout=10.0) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM players_online WHERE status = 'online'")
                row = cur.fetchone()
                return int(row[0]) if row else 0
        except Exception:
            return 0

    def _is_scum_server_running(self) -> bool:
        """Verifica se o servidor SCUM está ativo via múltiplos métodos (Serviço Windows, Processos, API)"""
        # 1. Verificar via serviço Windows (sc query e PowerShell)
        service_name = str(
            self.config.get("server", {}).get("service_name") or "SCUMServer"
        ).strip()
        try:
            import subprocess, sys

            creation_flags = (
                subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            r = subprocess.run(
                ["sc", "query", service_name],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=creation_flags,
            )
            if "RUNNING" in (r.stdout or "").upper():
                return True
        except Exception:
            pass

        try:
            import subprocess, sys

            creation_flags = (
                subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            ps_cmd = (
                f"Get-Service -Name '{service_name}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status"
            )
            r2 = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=4,
                creationflags=creation_flags,
            )
            if (r2.stdout or "").strip().upper() == "RUNNING":
                return True
        except Exception:
            pass

        # 2. Verificar via processos do sistema (psutil)
        try:
            import psutil

            for proc in psutil.process_iter(["name", "cmdline"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                    if name in (
                        "scumserver.exe",
                        "scum.exe",
                        "scum-win64-shipping.exe",
                        "scum-win64-test.exe",
                    ):
                        return True
                    if "nssm.exe" in name and (
                        "scum" in cmdline or service_name.lower() in cmdline
                    ):
                        return True
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    pass
        except Exception:
            pass

        # 3. Tentar via API interna se estiver ativa
        try:
            api_port = self.config.get("api", {}).get("port", 3000)
            res = requests.get(
                f"http://127.0.0.1:{api_port}/api/server/status", timeout=1.5
            )
            if res.status_code == 200:
                data = res.json()
                if (
                    isinstance(data, dict)
                    and data.get("data", {}).get("is_running") is True
                ):
                    return True
        except Exception:
            pass

        return False


    def _format_moon_phase(self, rotation: Optional[float]) -> str:
        """Retorna a fase da lua formatada em inglês"""
        if rotation is None:
            return "🌓 Waxing Crescent"
        try:
            rot = float(rotation) % 360.0
            if rot < 22.5 or rot >= 337.5:
                return "🌑 New Moon"
            elif rot < 67.5:
                return "🌒 Waxing Crescent"
            elif rot < 112.5:
                return "🌓 First Quarter"
            elif rot < 157.5:
                return "🌔 Waxing Gibbous"
            elif rot < 202.5:
                return "🌕 Full Moon"
            elif rot < 247.5:
                return "🌖 Waning Gibbous"
            elif rot < 292.5:
                return "🌗 Last Quarter"
            else:
                return "🌘 Waning Crescent"
        except Exception:
            return "🌓 Waxing Crescent"

    def _format_fog_label(
        self,
        fog_density: Optional[float],
        cumulonimbus_fog: Optional[bool] = None,
    ) -> str:
        """Retorna descrição de neblina/clima em inglês"""
        try:
            if fog_density is None:
                return "🌤️ Clear Sky"
            fd = float(fog_density)
            if fd <= 0.05:
                return "🌤️ Clear Sky"
            elif fd <= 0.30:
                return "🌫️ Light Fog"
            elif fd <= 0.60:
                return "🌫️ Medium Fog"
            elif fd <= 0.85:
                return "🌫️ Heavy Fog"
            else:
                return "🌫️ Dense Fog"
        except Exception:
            return "🌤️ Clear Sky"

    def trigger_immediate_refresh(self):
        """Força a sincronização e atualização imediata do Live Dashboard no Discord"""
        try:
            threading.Thread(target=self._timer_tick, daemon=True, name="ImmediateWeatherSync").start()
        except Exception as e:
            self.logger.error(f"Erro ao disparar refresh imediato do WeatherScheduler: {e}")

    def _get_next_restart_info(self) -> Tuple[str, str, Optional[int]]:
        """Calcula o próximo restart programado e retorna (next_restart_str, restart_times_formatted, minutes_remaining) em inglês"""
        restart_times = self.config.get("scheduler", {}).get("restart_times", [])
        if not restart_times:
            return "Not scheduled", "-", None

        now = datetime.now()
        candidates = []
        for rt in restart_times:
            try:
                parts = [int(x) for x in str(rt).split(":")[:2]]
                dt = now.replace(hour=parts[0], minute=parts[1], second=0, microsecond=0)
                if dt <= now:
                    dt += timedelta(days=1)
                candidates.append(dt)
            except Exception:
                pass

        next_str = "Not scheduled"
        minutes_remaining = None
        if candidates:
            candidates.sort()
            next_dt = candidates[0]
            diff = next_dt - now
            total_sec = max(0, int(diff.total_seconds()))
            h = total_sec // 3600
            m = (total_sec % 3600) // 60
            minutes_remaining = total_sec // 60

            if total_sec <= 60:
                next_str = f"🚨 **RESTART IN LESS THAN 1 MINUTE!** ({next_dt.strftime('%H:%M')})"
            elif minutes_remaining <= 3:
                next_str = f"🔴 **RESTART IMMINENT IN {minutes_remaining} MINUTE(S)!** ({next_dt.strftime('%H:%M')})"
            elif minutes_remaining <= 10:
                next_str = f"⚠️ **RESTART IN {minutes_remaining} MINUTE(S)!** ({next_dt.strftime('%H:%M')})"
            else:
                next_str = f"📅 **{next_dt.strftime('%H:%M')}** (in {h}h {m:02d}m)"

        restarts_formatted = " • ".join(str(x) for x in restart_times)
        return next_str, restarts_formatted, minutes_remaining

    def _build_live_dashboard_payload(self, display_time: str) -> Dict[str, Any]:
        """Constrói o payload JSON do Live Dashboard para o Discord em inglês com detecção online/offline e alertas de restart"""
        ini_data = self._read_server_settings_ini()
        server_name = ini_data.get("server_name", "SCUM Server")
        max_players = ini_data.get("max_players", 64)
        time_speed = ini_data.get("time_speed", 1.0)
        sunrise = ini_data.get("sunrise_time", "04:00:00")
        sunset = ini_data.get("sunset_time", "23:59:50")

        # Próximo Restart e Alerta Dinâmico
        next_restart_str, restarts_list_str, minutes_until_restart = self._get_next_restart_info()

        # Status do servidor (Online vs Offline vs Alerta de Restart)
        is_online = self._is_scum_server_running()
        if not is_online:
            title = f"🔄 SERVER RESTARTING / OFFLINE — {server_name}"
            color = 0xE67E22  # Laranja / Offline
        elif minutes_until_restart is not None and minutes_until_restart <= 3:
            title = f"🔴 RESTART IMMINENT — {server_name}"
            color = 0xE74C3C  # Vermelho Alerta Máximo
        elif minutes_until_restart is not None and minutes_until_restart <= 10:
            title = f"🟡 RESTART WARNING — {server_name}"
            color = 0xF1C40F  # Amarelo Alerta
        else:
            title = f"🟢 SERVER ONLINE — {server_name}"
            color = 0x2ECC71  # Verde Normal

        # Conexão
        server_cfg = self.config.get("server", {})
        ext_ip = str(server_cfg.get("external_ip") or "").strip()
        port = server_cfg.get("port", 7777)
        if ext_ip:
            conn_str = f"{ext_ip}:{port}"
        else:
            conn_str = f"Port {port}"

        # Lotação
        online_count = self._get_online_players_count() if is_online else 0
        pct = (online_count / max_players) * 100 if max_players > 0 else 0
        filled = max(0, min(10, int(round(pct / 10))))
        bar = "█" * filled + "░" * (10 - filled)

        # Dia / Noite
        is_day = True
        try:
            gt_parts = [int(x) for x in display_time.split(":")[:2]]
            sr_parts = [int(x) for x in sunrise.split(":")[:2]]
            ss_parts = [int(x) for x in sunset.split(":")[:2]]
            gt_min = gt_parts[0] * 60 + gt_parts[1]
            sr_min = sr_parts[0] * 60 + sr_parts[1]
            ss_min = ss_parts[0] * 60 + ss_parts[1]
            if sr_min <= ss_min:
                is_day = sr_min <= gt_min <= ss_min
            else:
                is_day = gt_min >= sr_min or gt_min <= ss_min
        except Exception:
            is_day = True

        day_icon = "🌞" if is_day else "🌙"
        day_label = "Day" if is_day else "Night"

        # Clima e Temperaturas
        weather = self._get_latest_weather_snapshot_from_ssm()
        air_temp = weather.get("base_air_temperature")
        water_temp = weather.get("water_temperature")
        moon_rot = weather.get("moon_rotation")
        fog_dense = weather.get("fog_density")
        cumul_fog = weather.get("should_cumulonimbus_cause_fog")

        at_str = f"{float(air_temp):.1f}°C" if air_temp is not None else "-"
        wt_str = f"{float(water_temp):.1f}°C" if water_temp is not None else "-"
        fog_txt = self._format_fog_label(fog_dense, cumul_fog)
        moon_phase = self._format_moon_phase(moon_rot)

        capacity_value = (
            f"• **Players:** {online_count} / {max_players} `[{bar}]` ({pct:.0f}%)\n• **Connection:** {conn_str}"
            if is_online
            else f"• **Status:** Server is currently restarting / offline. Awaiting connection..."
        )

        embed = {
            "title": title,
            "color": color,
            "fields": [
                {
                    "name": "📊 Status & Capacity",
                    "value": capacity_value,
                    "inline": False,
                },
                {
                    "name": "⏱️ In-Game Time & Weather",
                    "value": f"• **SCUM Time:** {day_icon} **{display_time}** ({day_label})\n• **Time Scale:** x{time_speed:.2f}\n• **Temperature:** 🌡️ Air: {at_str} | 🌊 Water: {wt_str}\n• **Weather:** {fog_txt}\n• **Moon Phase:** {moon_phase}",
                    "inline": False,
                },
                {
                    "name": "⏳ Scheduled Restarts",
                    "value": f"• **Next Restart:** {next_restart_str}\n• **Daily Schedule:** {restarts_list_str}",
                    "inline": False,
                },
            ],
            "footer": {
                "text": "🔄 Updated every 60s • SSM Backend Monitoring System"
            },
        }

        return {"embeds": [embed]}

    def _send_discord_notification(self, server_time):
        """Enviar notificação do Live Dashboard para Discord (canal serverstatus)"""
        try:
            # Carregar webhooks
            webhooks_path = "data/webhooks.json"
            if not os.path.exists(webhooks_path):
                self.logger.error("Arquivo webhooks.json não encontrado")
                return False

            target_webhook = ""
            target_event = "serverstatus"
            event_state = {}
            mgr = None

            try:
                from core.webhooks.manager import WebhooksManager

                mgr = WebhooksManager(webhooks_path)
                webhooks = mgr.load()

                # Prioridade 1: serverstatus, Prioridade 2: timer (retrocompatibilidade)
                target_webhook = (webhooks or {}).get("serverstatus")
                if not target_webhook:
                    target_webhook = (webhooks or {}).get("timer")
                    target_event = "timer" if target_webhook else "serverstatus"

                try:
                    v2 = mgr.load_v2()
                    event_state = (
                        ((v2 or {}).get("events") or {})
                        .get(target_event, {})
                        .get("state", {})
                    )
                    if not isinstance(event_state, dict):
                        event_state = {}
                except Exception:
                    event_state = {}
            except Exception:
                with open(webhooks_path, "r", encoding="utf-8") as f:
                    webhooks = json.load(f)
                target_webhook = (webhooks or {}).get("serverstatus") or (
                    webhooks or {}
                ).get("timer")
                target_event = (
                    "serverstatus"
                    if (webhooks or {}).get("serverstatus")
                    else "timer"
                )

            if not target_webhook:
                self.logger.debug("Webhook 'serverstatus' / 'timer' não configurado")
                return True

            predicted = None
            try:
                predicted = self._predict_server_time_hhmm()
            except Exception:
                predicted = None
            display_time = predicted or server_time

            payload = self._build_live_dashboard_payload(display_time)

            signature = hashlib.sha1(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()

            try:
                last_sig = str(event_state.get("last_signature") or "")
                if last_sig and last_sig == signature:
                    return True
            except Exception:
                pass

            parsed = None
            try:
                parts = str(target_webhook).split("/api/webhooks/")
                if len(parts) == 2:
                    tail = parts[1].strip("/")
                    segs = tail.split("/")
                    if len(segs) >= 2:
                        parsed = {"id": segs[0], "token": segs[1]}
            except Exception:
                parsed = None

            message_id = None
            try:
                message_id = event_state.get("last_message_id")
                message_id = str(message_id).strip() if message_id else ""
            except Exception:
                message_id = ""

            # PATCH se existir mensagem fixa
            if parsed and message_id:
                r = None
                try:
                    r = requests.patch(
                        f"https://discord.com/api/webhooks/{parsed['id']}/{parsed['token']}/messages/{message_id}",
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=15,
                    )
                    if int(getattr(r, "status_code", 0)) in (200, 204):
                        if mgr:
                            try:
                                mgr.patch_event_state(
                                    target_event,
                                    {
                                        "last_updated_at": datetime.now().isoformat(),
                                        "last_signature": signature,
                                    },
                                    create_backup=False,
                                )
                            except Exception:
                                pass
                        self.logger.info(
                            f"Live Dashboard atualizado no Discord: {display_time}"
                        )
                        return True
                    elif int(getattr(r, "status_code", 0)) == 404:
                        # Mensagem antiga foi apagada no Discord, resetar ID para recriar
                        message_id = ""
                except Exception as e:
                    self.logger.debug(f"Erro ao editar mensagem no Discord: {e}")
                finally:
                    try:
                        if r is not None:
                            r.close()
                    except Exception:
                        pass

            # Criar nova mensagem fixa (wait=true para obter id)
            r2 = None
            try:
                if parsed:
                    url = f"https://discord.com/api/webhooks/{parsed['id']}/{parsed['token']}?wait=true"
                else:
                    url = str(target_webhook)
                    if "?wait=true" not in url:
                        sep = "&" if "?" in url else "?"
                        url = url + f"{sep}wait=true"

                r2 = requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=15,
                )
                if int(getattr(r2, "status_code", 0)) in (200, 201, 204):
                    mid = None
                    try:
                        data = r2.json()
                        if isinstance(data, dict):
                            mid = data.get("id")
                    except Exception:
                        mid = None

                    if mid is not None and mgr:
                        try:
                            mgr.patch_event_state(
                                target_event,
                                {
                                    "last_message_id": str(mid),
                                    "last_updated_at": datetime.now().isoformat(),
                                    "last_signature": signature,
                                },
                                create_backup=False,
                            )
                        except Exception:
                            pass

                    self.logger.info(
                        f"Live Dashboard criado no Discord: {display_time}"
                    )
                    return True

            except Exception as e:
                self.logger.error(f"Erro ao enviar Live Dashboard para Discord: {e}")
            finally:
                try:
                    if r2 is not None:
                        r2.close()
                except Exception:
                    pass

            return False

        except Exception as e:
            self.logger.error(f"Erro ao processar Live Dashboard: {e}")
            return False


    def _scheduler_loop(self):
        """Loop principal do agendador climático"""
        self.logger.info("Loop do agendador climático iniciado")

        while not self.stop_event.is_set():
            try:
                self._scheduler.run_pending()
                time.sleep(60)  # Verificar a cada minuto
            except Exception as e:
                self.logger.error(f"Erro no loop do agendador climático: {e}")
                time.sleep(5)  # Aguardar mais tempo em caso de erro

        self.logger.info("Loop do agendador climático encerrado")

    def start(self) -> Dict[str, Any]:
        """Iniciar agendador climático"""
        try:
            if not self.enabled:
                return {
                    "success": False,
                    "message": "Agendador climático está desabilitado",
                    "status": "disabled",
                }

            if self.is_running:
                return {
                    "success": False,
                    "message": "Agendador climático já está rodando",
                    "status": "already_running",
                }

            # Limpar agendamentos anteriores
            self._scheduler.clear()

            # Agendar sincronização a cada X minutos
            self._scheduler.every(self.sync_interval_minutes).minutes.do(
                self._sync_weather_data
            )

            # Atualizar canal timer a cada 60s (sem consultar SCUM.db)
            self._scheduler.every(1).minutes.do(self._timer_tick)

            # Executar primeira sincronização imediatamente
            self.logger.info("Executando primeira sincronização climática...")
            self._sync_weather_data()

            # Executar primeira atualização do timer imediatamente
            try:
                self._timer_tick()
            except Exception:
                pass

            # Iniciar thread do agendador
            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()

            self.is_running = True

            self.logger.info(
                f"Agendador climático iniciado - Sincronização a cada {self.sync_interval_minutes} minutos"
            )
            self._log_schedule_event(
                "scheduler_started",
                {"sync_interval_minutes": self.sync_interval_minutes},
            )

            return {
                "success": True,
                "message": f"Agendador climático iniciado com sucesso",
                "status": "started",
                "sync_interval_minutes": self.sync_interval_minutes,
            }

        except Exception as e:
            self.logger.error(f"Erro ao iniciar agendador climático: {e}")
            return {
                "success": False,
                "message": f"Erro ao iniciar agendador climático: {e}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        """Parar agendador climático"""
        try:
            if not self.is_running:
                return {
                    "success": False,
                    "message": "Agendador climático não está rodando",
                    "status": "not_running",
                }

            # Parar thread
            self.stop_event.set()
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)

            # Limpar agendamentos
            self._scheduler.clear()

            self.is_running = False

            self.logger.info("Agendador climático parado")
            self._log_schedule_event("scheduler_stopped")

            return {
                "success": True,
                "message": "Agendador climático parado com sucesso",
                "status": "stopped",
            }

        except Exception as e:
            self.logger.error(f"Erro ao parar agendador climático: {e}")
            return {
                "success": False,
                "message": f"Erro ao parar agendador climático: {e}",
                "status": "error",
            }

    def get_status(self) -> Dict[str, Any]:
        """Obter status do agendador climático"""
        try:
            return {
                "success": True,
                "data": {
                    "enabled": self.enabled,
                    "is_running": self.is_running,
                    "sync_interval_minutes": self.sync_interval_minutes,
                    "auto_start": self.auto_start,
                    "logs_count": len(self.schedule_logs),
                    "next_sync": f"A cada {self.sync_interval_minutes} minutos",
                },
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter status do agendador climático: {e}")
            return {"success": False, "error": str(e)}

    def get_logs(self, limit: int = 50) -> Dict[str, Any]:
        """Obter logs do agendador climático"""
        try:
            recent_logs = (
                self.schedule_logs[-limit:] if limit > 0 else self.schedule_logs
            )

            return {
                "success": True,
                "data": {
                    "logs": recent_logs,
                    "count": len(recent_logs),
                    "total": len(self.schedule_logs),
                },
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter logs do agendador climático: {e}")
            return {"success": False, "error": str(e)}

    def force_sync_now(self) -> Dict[str, Any]:
        """Forçar sincronização imediata"""
        try:
            self.logger.info("Sincronização climática forçada solicitada")
            self._log_schedule_event("force_sync_requested")

            success = self._sync_weather_data()

            if success:
                self.logger.info(
                    "Sincronização climática forçada concluída com sucesso"
                )
                return {
                    "success": True,
                    "message": "Sincronização climática executada com sucesso",
                    "status": "completed",
                }
            else:
                return {
                    "success": False,
                    "message": "Falha na sincronização climática",
                    "status": "failed",
                }

        except Exception as e:
            self.logger.error(f"Erro na sincronização forçada: {e}")
            return {
                "success": False,
                "message": f"Erro na sincronização forçada: {e}",
                "status": "error",
            }
