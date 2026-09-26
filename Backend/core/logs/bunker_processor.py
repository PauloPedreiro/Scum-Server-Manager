"""
Processador de Logs de Bunkers do SCUM
Processa eventos de bunkers dos logs gameplay_*.log
"""

import re
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from core.database.connector import DatabaseConnector
import threading
import time
import json
import requests

from .database_manager import DatabaseManager
from .temp_file_manager import TempFileManager

class BunkerProcessor:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.temp_manager = TempFileManager()

        self._logger = logging.getLogger("scum_backend")
        self._bunker_debug = str(os.environ.get("SSM_BUNKER_DEBUG") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        self._http = requests.Session()
        self._status_updater_thread = None
        self._status_updater_running = False
        self._status_updater_interval_seconds = 10 * 60
        try:
            v = (os.environ.get("SSM_BUNKER_UPDATE_INTERVAL_SECONDS") or "").strip()
            if v:
                self._status_updater_interval_seconds = max(10, int(v))
        except Exception:
            pass
        self._status_updater_lock = threading.Lock()
        self._last_sent_signature = ""
        self._last_sent_at = 0.0
        
        # Padrões regex para eventos de bunkers
        self.bunker_patterns = {
            'bunker_activated': re.compile(
                r'Bunker\s+(\w+)\s+activated',
                re.IGNORECASE
            ),
            'bunker_locked': re.compile(
                r'Bunker\s+(\w+)\s+locked',
                re.IGNORECASE
            ),
            'bunker_access': re.compile(
                r'Player\s+(\w+)\s+accessed\s+bunker\s+(\w+)',
                re.IGNORECASE
            ),
            'bunker_abandoned': re.compile(
                r'Bunker\s+(\w+)\s+abandoned',
                re.IGNORECASE
            )
        }
        
        # Mapeamento de bunkers conhecidos
        self.known_bunkers = {
            'A1': 'A1 Bunker',
            'A3': 'A3 Bunker', 
            'C4': 'C4 Bunker',
            'D1': 'D1 Bunker'
        }
        
        # Coordenadas dos bunkers (se disponíveis)
        self.bunker_coordinates = {
            'A1': {'x': 1234.5, 'y': 5678.9, 'z': 100.0},
            'A3': {'x': 2345.6, 'y': 6789.0, 'z': 100.0},
            'C4': {'x': 3456.7, 'y': 7890.1, 'z': 100.0},
            'D1': {'x': 4567.8, 'y': 8901.2, 'z': 100.0}
        }

        self._start_status_updater()

    def _start_status_updater(self) -> None:
        try:
            if self._status_updater_running:
                return
            self._status_updater_running = True

            def _loop():
                while self._status_updater_running:
                    try:
                        if self._bunker_debug:
                            try:
                                self._logger.info("BunkerStatusUpdater: tick")
                            except Exception:
                                pass
                        self.send_or_edit_bunker_status_message(force=False)
                    except Exception:
                        pass
                    time.sleep(int(self._status_updater_interval_seconds))

            self._status_updater_thread = threading.Thread(
                target=_loop, daemon=True, name="BunkerStatusUpdater"
            )
            self._status_updater_thread.start()
        except Exception:
            try:
                self._logger.exception("BunkerStatusUpdater: failed to start")
            except Exception:
                pass
            self._status_updater_running = False

    def stop_status_updater(self) -> None:
        try:
            self._status_updater_running = False
        except Exception:
            pass
    
    def process_bunker_logs(self, log_file_path: str) -> Dict[str, Any]:
        """Processar logs de bunkers de um arquivo com a lógica correta"""
        try:
            # 1. Verificar se o arquivo já foi processado
            file_name = os.path.basename(log_file_path)
            if self._is_file_already_processed(file_name):
                print(f"INFO: Arquivo {file_name} já foi processado, pulando...")
                return {"success": True, "skipped": True, "reason": "Arquivo já processado"}
            
            # Copiar arquivo para temp
            temp_file = self.temp_manager.create_temp_copy(log_file_path)
            if not temp_file:
                return {'success': False, 'error': 'Falha ao copiar arquivo para temp'}
            
            try:
                # 2. Processar arquivo e gravar no banco
                results = self._process_file(temp_file)
                
                # 3. Marcar arquivo como processado
                if results.get("success"):
                    self._mark_file_as_processed(file_name, log_file_path)
                
                return results
            finally:
                # Limpar arquivo temporário
                self.temp_manager.cleanup_temp_file(temp_file)
            
        except Exception as e:
            print(f"ERRO: Erro ao processar logs de bunkers: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_bunker_logs_from_temp(self, temp_file_path: str, original_file_path: str) -> Dict[str, Any]:
        """Processar logs de bunkers usando arquivo temporário já copiado"""
        try:
            # 1. Verificar se o arquivo já foi processado
            file_name = os.path.basename(original_file_path)
            if self._is_file_already_processed(file_name):
                print(f"INFO: Arquivo {file_name} já foi processado, pulando...")
                return {"success": True, "skipped": True, "reason": "Arquivo já processado"}
            
            # 2. Processar arquivo temporário diretamente (sem copiar novamente)
            results = self._process_file(temp_file_path)
            
            # 3. Marcar arquivo como processado
            if results.get("success"):
                self._mark_file_as_processed(file_name, original_file_path)
            
            return results
            
        except Exception as e:
            print(f"ERRO: Erro ao processar logs de bunkers: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_file(self, file_path: str) -> Dict[str, Any]:
        """Processar arquivo de log de bunkers"""
        bunker_events = []
        processed_lines = 0
        
        try:
            with open(file_path, 'r', encoding='utf-16le', errors='ignore') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Extrair timestamp da linha
                    timestamp = self._extract_timestamp(line)
                    if not timestamp:
                        continue
                    
                    # Verificar padrões de bunker
                    event = self._parse_bunker_event(line, timestamp)
                    if event:
                        bunker_events.append(event)
                    
                    processed_lines += 1
            
            # Processar eventos encontrados
            if bunker_events:
                self._process_bunker_events(bunker_events)
            
            return {
                'success': True,
                'events_found': len(bunker_events),
                'lines_processed': processed_lines,
                'bunker_events': bunker_events
            }
            
        except Exception as e:
            print(f"ERRO: Erro ao processar arquivo {file_path}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extrair timestamp da linha do log"""
        # Padrão de timestamp nos logs do SCUM: 2025.10.21-20.00.48
        timestamp_pattern = re.compile(r'(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2})')
        match = timestamp_pattern.search(line)
        
        if match:
            try:
                # Converter formato 2025.10.21-20.00.48 para datetime
                timestamp_str = match.group(1)
                # Dividir em data e hora
                parts = timestamp_str.split('-')
                date_part = parts[0].replace('.', '-')  # 2025.10.21 -> 2025-10-21
                time_part = parts[1].replace('.', ':')  # 20.02.33 -> 20:02:33
                formatted_str = f"{date_part} {time_part}"
                return datetime.strptime(formatted_str, '%Y-%m-%d %H:%M:%S')
            except ValueError as e:
                # Tentar formato alternativo
                try:
                    timestamp_str = match.group(1)
                    # Formato direto: 2025.10.21-20.02.33
                    formatted_str = timestamp_str.replace('.', '-', 2).replace('-', ' ', 1).replace('.', ':')
                    return datetime.strptime(formatted_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # Formato mais simples
                    try:
                        timestamp_str = match.group(1)
                        # 2025.10.21-20.02.33 -> 2025-10-21 20:02:33
                        formatted_str = timestamp_str.replace('.', '-', 2).replace('-', ' ', 1).replace('.', ':')
                        return datetime.strptime(formatted_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass
        
        return None
    
    def _parse_bunker_event(self, line: str, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Extrair evento de bunker da linha"""
        # Verificar se é linha de bunker
        if '[LogBunkerLock]' not in line:
            return None
        
        # Padrão para eventos de ativação/bloqueio
        # [LogBunkerLock] A1 Bunker Activated 12h 35m 29s ago
        activation_pattern = re.compile(r'\[LogBunkerLock\]\s+(\w+)\s+Bunker\s+(Activated|Locked)')
        match = activation_pattern.search(line)
        if match:
            bunker_id = match.group(1)
            action = match.group(2).lower()
            return {
                'event_type': 'bunker_activation',
                'bunker_id': bunker_id,
                'bunker_name': f"{bunker_id} Bunker",
                'action': action,
                'timestamp': timestamp,
                'raw_line': line
            }
        
        # Padrão para status de bunker ativo
        # [LogBunkerLock] A1 Bunker is Active. Activated 00h 00m 00s ago. X=-348529.312 Y=-469201.781 Z=4247.645
        active_pattern = re.compile(r'\[LogBunkerLock\]\s+(\w+)\s+Bunker\s+is\s+Active\.\s+Activated\s+(\d{2})h\s+(\d{2})m\s+(\d{2})s\s+ago\.\s+X=([-\d.]+)\s+Y=([-\d.]+)\s+Z=([-\d.]+)')
        match = active_pattern.search(line)
        if match:
            bunker_id = match.group(1)
            hours = int(match.group(2))
            minutes = int(match.group(3))
            seconds = int(match.group(4))
            x = float(match.group(5))
            y = float(match.group(6))
            z = float(match.group(7))
            
            # Calcular tempo de ativação
            activation_time = timestamp - timedelta(hours=hours, minutes=minutes, seconds=seconds)
            
            return {
                'event_type': 'bunker_status',
                'bunker_id': bunker_id,
                'bunker_name': f"{bunker_id} Bunker",
                'status': 'active',
                'timestamp': timestamp,
                'activation_time': activation_time,
                'coordinates': {'x': x, 'y': y, 'z': z},
                'raw_line': line
            }
        
        # Padrão para status de bunker bloqueado
        # [LogBunkerLock] D1 Bunker is Locked. Locked 00h 00m 00s ago, next Activation in 11h 24m 29s. X=-537889.562 Y=540004.312 Z=81279.648
        locked_pattern = re.compile(r'\[LogBunkerLock\]\s+(\w+)\s+Bunker\s+is\s+Locked\.\s+Locked\s+(\d{2})h\s+(\d{2})m\s+(\d{2})s\s+ago,\s+next\s+Activation\s+in\s+(\d{2})h\s+(\d{2})m\s+(\d{2})s\.\s+X=([-\d.]+)\s+Y=([-\d.]+)\s+Z=([-\d.]+)')
        match = locked_pattern.search(line)
        if match:
            bunker_id = match.group(1)
            locked_hours = int(match.group(2))
            locked_minutes = int(match.group(3))
            locked_seconds = int(match.group(4))
            next_hours = int(match.group(5))
            next_minutes = int(match.group(6))
            next_seconds = int(match.group(7))
            x = float(match.group(8))
            y = float(match.group(9))
            z = float(match.group(10))
            
            # Calcular tempo de bloqueio
            lock_time = timestamp - timedelta(hours=locked_hours, minutes=locked_minutes, seconds=locked_seconds)
            
            # Calcular próxima ativação
            next_activation = timestamp + timedelta(hours=next_hours, minutes=next_minutes, seconds=next_seconds)
            
            return {
                'event_type': 'bunker_status',
                'bunker_id': bunker_id,
                'bunker_name': f"{bunker_id} Bunker",
                'status': 'locked',
                'timestamp': timestamp,
                'lock_time': lock_time,
                'next_activation': next_activation,
                'coordinates': {'x': x, 'y': y, 'z': z},
                'raw_line': line
            }
        
        return None
    
    def _create_bunker_event(self, event_type: str, match: re.Match, 
                           timestamp: datetime, line: str) -> Dict[str, Any]:
        """Criar evento de bunker"""
        bunker_id = match.group(1) if len(match.groups()) >= 1 else None
        
        # Determinar status baseado no tipo de evento
        if event_type == 'bunker_activated':
            status = 'active'
            next_activation = None
            duration_minutes = 180  # Duração padrão de 3 horas
        elif event_type == 'bunker_locked':
            status = 'locked'
            next_activation = timestamp + timedelta(hours=3)  # Próxima ativação em 3 horas
            duration_minutes = None
        else:
            status = 'unknown'
            next_activation = None
            duration_minutes = None
        
        # Obter coordenadas se disponíveis
        coordinates = self.bunker_coordinates.get(bunker_id, {})
        
        return {
            'bunker_id': bunker_id,
            'bunker_name': self.known_bunkers.get(bunker_id, f"{bunker_id} Bunker"),
            'event_type': event_type,
            'status': status,
            'timestamp': timestamp,
            'coordinates_x': coordinates.get('x'),
            'coordinates_y': coordinates.get('y'),
            'coordinates_z': coordinates.get('z'),
            'last_activity': timestamp,
            'next_activation': next_activation,
            'duration_minutes': duration_minutes,
            'source_line': line
        }
    
    def _process_bunker_events(self, events: List[Dict[str, Any]]) -> None:
        """Processar eventos de bunkers e atualizar banco com lógica correta"""
        # Armazenar estado anterior dos bunkers
        previous_bunker_states = self._get_previous_bunker_states()
        
        # Processar todos os eventos primeiro
        for event in events:
            try:
                event_type = event.get('event_type')
                bunker_id = event.get('bunker_id')
                
                if event_type == 'bunker_activation':
                    # Processar ativação/bloqueio
                    action = event.get('action')
                    status = 'active' if action == 'activated' else 'locked'
                    
                    bunker_data = {
                        'bunker_id': bunker_id,
                        'bunker_name': event.get('bunker_name'),
                        'status': status,
                        'timestamp': event.get('timestamp'),
                        'last_activity': event.get('timestamp')
                    }
                    
                    success = self.db_manager.update_bunker_status(bunker_data)
                    if success:
                        print(f"OK: Bunker {bunker_id} {action}")
                    else:
                        print(f"ERRO: Falha ao atualizar bunker {bunker_id}")
                
                elif event_type == 'bunker_status':
                    # Processar status atual
                    status = event.get('status')
                    coordinates = event.get('coordinates', {})
                    activation_time = event.get('activation_time')
                    lock_time = event.get('lock_time')
                    next_activation = event.get('next_activation')
                    
                    # Determinar last_activity baseado no status
                    if status == 'active' and activation_time:
                        last_activity = activation_time
                    elif status == 'locked' and lock_time:
                        last_activity = lock_time
                    else:
                        last_activity = event.get('timestamp')
                    
                    bunker_data = {
                        'bunker_id': bunker_id,
                        'bunker_name': event.get('bunker_name'),
                        'status': status,
                        'timestamp': event.get('timestamp'),
                        'last_activity': last_activity,
                        'next_activation': next_activation,
                        'coordinates_x': coordinates.get('x'),
                        'coordinates_y': coordinates.get('y'),
                        'coordinates_z': coordinates.get('z')
                    }
                    
                    success = self.db_manager.update_bunker_status(bunker_data)
                    if success:
                        print(f"OK: Status do bunker {bunker_id} atualizado: {status}")
                    else:
                        print(f"ERRO: Falha ao atualizar bunker {bunker_id}")
                    
            except Exception as e:
                print(f"ERRO: Erro ao processar evento de bunker: {e}")
        
        # Após processar todos os eventos, verificar se houve mudanças
        if events:
            self._check_and_send_bunker_changes(previous_bunker_states)

        # Sempre garantir que o painel fixo existe/atualize (sem spam)
        try:
            self.send_or_edit_bunker_status_message(force=False)
        except Exception:
            pass
    
    def _send_bunker_notification(self, bunker_data: Dict[str, Any], action: str) -> None:
        """Enviar notificação de bunker para Discord"""
        try:
            self.send_or_edit_bunker_status_message(force=True)
        except Exception as e:
            print(f"ERRO: Falha ao enviar notificação de bunker: {e}")
    
    def _get_bunker_status_summary(self) -> Dict[str, Any]:
        """Obter resumo do status dos bunkers"""
        try:
            stats = self.db_manager.get_bunker_stats()
            return stats
        except Exception as e:
            print(f"ERRO: Erro ao obter status dos bunkers: {e}")
            return {}
    
    def format_bunker_status_message(self) -> str:
        """Formatar mensagem de status dos bunkers para Discord"""
        try:
            stats = self.db_manager.get_bunker_stats()
            if not stats:
                return "No bunker data available"
            
            message = "**🏗️ BUNKER STATUS - SCUM**\n\n"
            
            for bunker in stats.get('bunker_details', []):
                bunker_id = bunker['bunker_id']
                bunker_name = bunker['bunker_name']
                status = bunker['status']
                last_activity = bunker['last_activity']
                next_activation = bunker['next_activation']
                
                # Determinar emoji e texto baseado no status
                if status == 'active':
                    emoji = "🟢"
                    time_text = f"{self._get_time_ago(last_activity)} ago" if last_activity else "unknown"
                else:
                    emoji = "🔴"
                    time_text = f"Next Activation: in {self._get_time_until(next_activation)}" if next_activation else "unknown"
                
                message += f"{emoji} **{bunker_name}**\n"
                message += f"Status: {status.upper()}\n"
                message += f"Time: {time_text}\n\n"
            
            return message
            
        except Exception as e:
            print(f"ERRO: Erro ao formatar mensagem de bunkers: {e}")
            return "Failed to get bunker status"
    
    def _get_time_ago(self, timestamp: str) -> str:
        """Calcular tempo decorrido desde timestamp"""
        try:
            if not timestamp:
                return "unknown"
            
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            now = datetime.now()
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days} day" if diff.days == 1 else f"{diff.days} days"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour" if hours == 1 else f"{hours} hours"
            else:
                minutes = diff.seconds // 60
                return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
                
        except Exception:
            return "unknown"
    
    def _get_time_until(self, timestamp: str) -> str:
        """Calcular tempo até timestamp"""
        try:
            if not timestamp:
                return "unknown"
            
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            now = datetime.now()
            diff = dt - now

            if diff.total_seconds() < 0:
                diff = timedelta(seconds=0)
            
            if diff.days > 0:
                return f"{diff.days} day" if diff.days == 1 else f"{diff.days} days"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour" if hours == 1 else f"{hours} hours"
            else:
                minutes = diff.seconds // 60
                return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
                
        except Exception:
            return "unknown"
    
    def _is_file_already_processed(self, file_name: str) -> bool:
        """Verificar se arquivo já foi processado"""
        try:
            import sqlite3
            with DatabaseConnector.get_connection(self.db_manager.db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT file_name FROM log_files_processed WHERE file_name = ?",
                    (file_name,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"ERRO: Erro ao verificar arquivo processado: {e}")
            return False
    
    def _mark_file_as_processed(self, file_name: str, file_path: str) -> None:
        """Marcar arquivo como processado"""
        try:
            import sqlite3
            with DatabaseConnector.get_connection(self.db_manager.db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO log_files_processed 
                       (file_name, file_path, last_modified, status, updated_at) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (file_name, file_path, datetime.now(), 'processed', datetime.now())
                )
                print(f"OK: Arquivo {file_name} marcado como processado")
        except Exception as e:
            print(f"ERRO: Erro ao marcar arquivo como processado: {e}")
    
    def _get_previous_bunker_states(self) -> Dict[str, Dict[str, Any]]:
        """Obter estado anterior dos bunkers do banco"""
        try:
            import sqlite3
            bunker_states = {}
            with DatabaseConnector.get_connection(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bunker_status")
                rows = cursor.fetchall()
                
                for row in rows:
                    bunker_id = row[0]  # bunker_id é a primeira coluna
                    bunker_states[bunker_id] = {
                        'status': row[2],  # status
                        'last_activity': row[5],  # last_activity
                        'next_activation': row[6]  # next_activation
                    }
            
            return bunker_states
        except Exception as e:
            print(f"ERRO: Erro ao obter estado anterior dos bunkers: {e}")
            return {}
    
    def _check_and_send_bunker_changes(self, previous_states: Dict[str, Dict[str, Any]]) -> None:
        """Verificar mudanças nos bunkers e enviar notificação se necessário"""
        try:
            # Obter estado atual dos bunkers
            current_states = self._get_previous_bunker_states()
            
            # Verificar se houve mudanças
            changes_detected = False
            
            for bunker_id, current_state in current_states.items():
                previous_state = previous_states.get(bunker_id, {})
                
                # Verificar mudanças de status
                if (previous_state.get('status') != current_state.get('status') or
                    previous_state.get('last_activity') != current_state.get('last_activity')):
                    changes_detected = True
                    break
            
            # Se houve mudanças, enviar notificação
            if changes_detected:
                print("INFO: Mudanças detectadas nos bunkers, enviando notificação...")
                self.send_or_edit_bunker_status_message(force=True)
            else:
                print("INFO: Nenhuma mudança detectada nos bunkers, não enviando notificação")
                
        except Exception as e:
            print(f"ERRO: Erro ao verificar mudanças nos bunkers: {e}")

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

            mgr = WebhooksManager(str(self._get_webhooks_file_path()))
            return mgr.load_v2()
        except Exception:
            return None

    def _save_webhooks_v2(self, v2_data: Dict[str, Any]) -> bool:
        try:
            from core.webhooks.manager import WebhooksManager

            mgr = WebhooksManager(str(self._get_webhooks_file_path()))
            mgr.replace_all_v2(v2_data, create_backup=True)
            return True
        except Exception:
            return False

    def _get_webhooks_file_path(self) -> "Path":
        try:
            from pathlib import Path

            if getattr(sys, "frozen", False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).resolve().parents[2]
            return base_dir / "data" / "webhooks.json"
        except Exception:
            from pathlib import Path

            return Path("data") / "webhooks.json"

    def _get_bunkers_event_v2(self) -> Optional[Dict[str, Any]]:
        try:
            v2 = self._load_webhooks_v2()
            if not isinstance(v2, dict):
                return None
            events = v2.get("events")
            if not isinstance(events, dict):
                return None
            ev = events.get("bunkers_status")
            if not isinstance(ev, dict):
                return None
            return ev
        except Exception:
            return None

    def _load_bunkers_state(self) -> Dict[str, Any]:
        try:
            ev = self._get_bunkers_event_v2() or {}
            st = ev.get("state")
            if isinstance(st, dict):
                return dict(st)
        except Exception:
            pass
        return {}

    def _update_bunkers_state(self, patch: Dict[str, Any]) -> None:
        try:
            v2 = self._load_webhooks_v2()
            if not isinstance(v2, dict):
                return
            events = v2.get("events")
            if not isinstance(events, dict):
                return
            ev = events.get("bunkers_status")
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

    def _load_bunkers_webhook_url(self) -> str:
        try:
            # Prefer v2 schema (events.*.target.webhook.url)
            ev = self._get_bunkers_event_v2() or {}
            target = ev.get("target") if isinstance(ev, dict) else None
            if isinstance(target, dict):
                webhook = target.get("webhook")
                if isinstance(webhook, dict):
                    url = str(webhook.get("url") or "").strip()
                    if url:
                        return url

            # Fallback: legacy/v1 flat keys
            webhooks_path = self._get_webhooks_file_path()
            if os.path.exists(str(webhooks_path)):
                try:
                    from core.webhooks.manager import WebhooksManager

                    mgr = WebhooksManager(str(webhooks_path))
                    hooks = mgr.load()
                    if isinstance(hooks, dict):
                        return str(hooks.get("bunkers_status") or "").strip()
                except Exception:
                    with open(webhooks_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        if isinstance(raw, dict):
                            return str(raw.get("bunkers_status") or "").strip()
        except Exception:
            pass
        return ""

    def _build_bunkers_signature(self, stats: Dict[str, Any]) -> str:
        try:
            details = stats.get("bunker_details") if isinstance(stats, dict) else None
            if not isinstance(details, list):
                return ""
            parts = []
            for b in details:
                if not isinstance(b, dict):
                    continue
                bid = str(b.get("bunker_id") or "")
                st = str(b.get("status") or "")
                parts.append(f"{bid}:{st}")
            parts.sort()
            payload = "|".join(parts)
            import hashlib

            return hashlib.sha1(payload.encode("utf-8", errors="ignore")).hexdigest()
        except Exception:
            return ""

    def _build_bunkers_embed(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        embed = {
            "title": "BUNKER STATUS",
            "description": "",
            "color": 0x57F287,
            "fields": [],
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": f"Scum Server - https://scumsm.com/ | Updated: {updated_at}"},
        }

        details = stats.get("bunker_details") if isinstance(stats, dict) else None
        if not isinstance(details, list):
            return embed

        rows = []
        for bunker in details:
            if not isinstance(bunker, dict):
                continue

            bunker_name = str(bunker.get("bunker_name") or bunker.get("bunker_id") or "Bunker")
            status = str(bunker.get("status") or "").lower()
            last_activity = bunker.get("last_activity")
            next_activation = bunker.get("next_activation")

            if status == "active":
                status_label = "Active"
                time_text = f"{self._get_time_ago(last_activity)} ago" if last_activity else "unknown"
            elif status == "locked":
                status_label = "Locked"
                time_text = f"in {self._get_time_until(next_activation)}" if next_activation else "unknown"
            else:
                status_label = status.title() if status else "Unknown"
                time_text = "unknown"

            rows.append((bunker_name, status_label, time_text))

        if rows:
            header_1 = "Bunker Sector"
            header_2 = "Status"
            header_3 = "Time"
            name_w = max(len(header_1), max(len(r[0]) for r in rows))
            status_w = max(len(header_2), max(len(r[1]) for r in rows))

            blocks = []
            for name, st, t in rows:
                blocks.append(
                    "\n".join(
                        [
                            f"{header_1:<{name_w}}  {header_2:<{status_w}}  {header_3}",
                            f"{name:<{name_w}}  {st:<{status_w}}  {t}",
                        ]
                    )
                )

            embed["description"] = "```\n" + "\n\n".join(blocks) + "\n```"

        return embed

    def send_or_edit_bunker_status_message(self, force: bool = False) -> bool:
        with self._status_updater_lock:
            stats = self.db_manager.get_bunker_stats()
            if not isinstance(stats, dict) or not stats:
                return False

            now = time.time()
            signature = self._build_bunkers_signature(stats)

            should_send = force
            if not should_send:
                # Atualizar a cada 10 min para o tempo ficar atualizado, mesmo sem mudar status
                if (now - float(self._last_sent_at or 0.0)) >= float(self._status_updater_interval_seconds):
                    should_send = True
                # Se status mudou, também enviar
                elif signature and signature != self._last_sent_signature:
                    should_send = True

            if not should_send:
                return True

            webhook_url = self._load_bunkers_webhook_url()
            if not webhook_url:
                try:
                    self._logger.warning("BunkerStatusUpdater: webhook url not configured")
                except Exception:
                    pass
                return False

            parsed = self._parse_discord_webhook_url(webhook_url)
            if not parsed:
                try:
                    self._logger.warning("BunkerStatusUpdater: webhook url invalid")
                except Exception:
                    pass
                return False

            if self._bunker_debug:
                try:
                    self._logger.info(
                        "BunkerStatusUpdater: sending update",
                        extra={
                            "data": {
                                "force": bool(force),
                                "webhook_id": str(parsed.get("id") or ""),
                                "has_token": bool(parsed.get("token")),
                            }
                        },
                    )
                except Exception:
                    pass

            embed = self._build_bunkers_embed(stats)
            payload = {"embeds": [embed]}

            state = self._load_bunkers_state()
            message_id = state.get("last_message_id")
            message_id = str(message_id).strip() if message_id else ""

            if not message_id:
                if self._bunker_debug:
                    try:
                        self._logger.info(
                            "BunkerStatusUpdater: no last_message_id, creating fixed message"
                        )
                    except Exception:
                        pass

            # Tentar editar mensagem fixa existente
            if message_id:
                r = None
                try:
                    r = self._http.patch(
                        f"https://discord.com/api/webhooks/{parsed['id']}/{parsed['token']}/messages/{message_id}",
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=15,
                    )
                    if int(getattr(r, "status_code", 0)) in (200, 204):
                        self._last_sent_signature = signature
                        self._last_sent_at = now
                        self._update_bunkers_state({"last_updated_at": datetime.now().isoformat()})
                        return True
                    else:
                        try:
                            sc = int(getattr(r, "status_code", 0))
                        except Exception:
                            sc = 0
                        try:
                            self._logger.warning(
                                "BunkerStatusUpdater: patch failed",
                                extra={"data": {"status": sc}},
                            )
                        except Exception:
                            pass
                except Exception:
                    try:
                        self._logger.exception(
                            "BunkerStatusUpdater: patch failed (exception)"
                        )
                    except Exception:
                        pass
                    pass
                finally:
                    try:
                        if r is not None:
                            r.close()
                    except Exception:
                        pass

            # Criar nova mensagem fixa
            r2 = None
            try:
                r2 = self._http.post(
                    f"https://discord.com/api/webhooks/{parsed['id']}/{parsed['token']}?wait=true",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=15,
                )
                if int(getattr(r2, "status_code", 0)) in (200, 201):
                    try:
                        data = r2.json()
                    except Exception:
                        data = None
                    mid = None
                    if isinstance(data, dict):
                        mid = data.get("id")
                    if mid is not None:
                        self._update_bunkers_state(
                            {
                                "last_message_id": str(mid),
                                "last_updated_at": datetime.now().isoformat(),
                            }
                        )
                    self._last_sent_signature = signature
                    self._last_sent_at = now
                    return True
                else:
                    try:
                        sc2 = int(getattr(r2, "status_code", 0))
                    except Exception:
                        sc2 = 0
                    try:
                        self._logger.warning(
                            "BunkerStatusUpdater: post failed",
                            extra={"data": {"status": sc2}},
                        )
                    except Exception:
                        pass
            except Exception:
                try:
                    self._logger.exception("BunkerStatusUpdater: post failed (exception)")
                except Exception:
                    pass
                pass
            finally:
                try:
                    if r2 is not None:
                        r2.close()
                except Exception:
                    pass
            return False
    
    def get_bunker_status_summary(self) -> Dict[str, Any]:
        """Obter resumo do status dos bunkers para notificações"""
        try:
            return self.db_manager.get_bunker_stats()
        except Exception as e:
            print(f"ERRO: Erro ao obter status dos bunkers: {e}")
            return {}
    
    def _send_bunker_status_notification(self) -> None:
        """Enviar notificação de status dos bunkers para Discord"""
        try:
            self.send_or_edit_bunker_status_message(force=True)
        except Exception as e:
            print(f"ERRO: Falha ao enviar notificação de status de bunkers: {e}")
