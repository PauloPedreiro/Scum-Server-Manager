"""
Admin Log Processor - Processa logs de administradores do SCUM
Monitora admin_*.log e envia comandos para Discord com categorização
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
import requests

logger = logging.getLogger(__name__)

class AdminLogProcessor:
    """Processador de logs de administradores do SCUM"""
    
    def __init__(self, webhooks_path: str = "data/webhooks.json", db_path: Optional[str] = None):
        import sys
        from pathlib import Path
        if getattr(sys, "frozen", False):
            self.data_dir = Path(sys.executable).parent / "data"
        else:
            self.data_dir = Path("data")
        self.webhooks_path = webhooks_path if os.path.isabs(webhooks_path) else str(self.data_dir / "webhooks.json")
        self.db_path = db_path or str(self.data_dir / "SSM.db")
        
        # Padrões de regex para parsing
        self.admin_log_pattern = re.compile(
            r'^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*\'(\d+):([^\']+)\'\s+Command:\s*\'(.*)\'$'
        )

        self.admin_map_teleport_pattern = re.compile(
            r"^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*\'(\d+):([^\']+)\'\s+Used map click teleport to (player|vehicle):\s*\'([^\']+)\'\s+Location:\s*(.*)$"
        )
        
        # Categorização de comandos
        self.command_categories = {
            "teleport": {"emoji": "🚀", "color": 0x9B59B6, "name": "Teleport"},
            "spawn": {"emoji": "🎁", "color": 0xF1C40F, "name": "Spawn"},
            "godmode": {"emoji": "🛡️", "color": 0xE74C3C, "name": "God Mode"},
            "info": {"emoji": "👁️", "color": 0x3498DB, "name": "Game Info"},
            "punishments": {"emoji": "⚖️", "color": 0xE67E22, "name": "Server Punishments"},
            "other": {"emoji": "📋", "color": 0x2ECC71, "name": "Other"},
        }

        self._legacy_category_name_to_key = {
            "teleport": "teleport",
            "spawn": "spawn",
            "spawn item": "spawn",
            "god mode": "godmode",
            "player info": "info",
            "command": "other",
            "default": "other",
            "other": "other",
            "server punishments": "punishments",
        }
    
    def _get_admin_webhook_url(self) -> Optional[str]:
        """Obtém URL do webhook adminlog"""
        try:
            if not os.path.exists(self.webhooks_path):
                logger.warning("Arquivo webhooks.json não encontrado")
                return None

            from core.webhooks.manager import WebhooksManager

            mgr = WebhooksManager(str(self.webhooks_path))
            webhooks = mgr.load()
            if not isinstance(webhooks, dict):
                return None
            return webhooks.get('adminlog')
        except Exception as e:
            logger.error(f"Erro ao ler webhooks.json: {e}")
            return None
    
    def _get_category_config(self, category: str) -> Dict:
        category_key = (category or "").strip().lower()
        if category_key in self.command_categories:
            config = self.command_categories[category_key]
            return {
                "category": category_key,
                "emoji": config.get("emoji", "📋"),
                "color": config.get("color", 0x2ECC71),
                "name": config.get("name", "Other"),
            }

        legacy_key = self._legacy_category_name_to_key.get(category_key)
        if legacy_key and legacy_key in self.command_categories:
            config = self.command_categories[legacy_key]
            return {
                "category": legacy_key,
                "emoji": config.get("emoji", "📋"),
                "color": config.get("color", 0x2ECC71),
                "name": config.get("name", "Other"),
            }

        config = self.command_categories["other"]
        return {
            "category": "other",
            "emoji": config.get("emoji", "📋"),
            "color": config.get("color", 0x2ECC71),
            "name": config.get("name", "Other"),
        }

    def _extract_command_verb(self, action: str) -> str:
        action = (action or "").strip()
        if not action:
            return ""
        return action.split()[0].strip().lower()

    def _categorize_command(self, action: str, event_type: str = "command") -> Dict:
        action_lower = (action or "").lower()

        if "used map click teleport" in action_lower:
            return self._get_category_config("teleport")

        verb = self._extract_command_verb(action)

        if verb in {"ban", "unban", "kick", "mute", "unmute"}:
            return self._get_category_config("punishments")

        if verb.startswith("teleport") or verb == "goto":
            return self._get_category_config("teleport")

        if verb in {"spawnitem", "spawnvehicle", "spawnzombie", "destroyvehicle"}:
            return self._get_category_config("spawn")

        if verb in {"setgodmode", "setimmortality", "setinfiniteammo"}:
            return self._get_category_config("godmode")

        if verb.startswith("show") or verb.startswith("list"):
            return self._get_category_config("info")

        return self._get_category_config("other")
    
    def _parse_admin_line(self, line: str) -> Optional[Dict]:
        """Parse uma linha do admin log"""
        match = self.admin_log_pattern.match(line.strip())
        if match:
            timestamp_str, steam_id, player_name, action = match.groups()
            event_type = "command"
        else:
            match = self.admin_map_teleport_pattern.match(line.strip())
            if not match:
                return None
            timestamp_str, steam_id, player_name, target_type, target, location_part = match.groups()
            if target_type == "player":
                event_type = "map_teleport_player"
            else:
                event_type = "map_teleport_vehicle"
            action = f"Used map click teleport to {target_type}: '{target}' Location: {location_part}".strip()
        
        # Converter timestamp SCUM para datetime
        try:
            # Formato: 2025.01.20-13.00.01
            timestamp_parts = timestamp_str.split('-')
            date_part = timestamp_parts[0].replace('.', '-')
            time_part = timestamp_parts[1].replace('.', ':')
            iso_string = f"{date_part}T{time_part}"
            timestamp = datetime.fromisoformat(iso_string)
        except Exception:
            timestamp = datetime.now()
        
        # Categorizar comando
        category_info = self._categorize_command(action, event_type=event_type)
        
        # Gerar ID único do comando (timestamp + steam_id)
        command_id = f"{timestamp_str}:{steam_id}"
        
        return {
            'timestamp': timestamp,
            'steam_id': steam_id,
            'player_name': player_name,
            'action': action,
            'category': category_info,
            'command_id': command_id,
            'event_type': event_type,
        }
    
    def _format_discord_message(self, parsed_data: Dict) -> Dict:
        """Formata mensagem para Discord"""
        timestamp = parsed_data['timestamp']
        steam_id = parsed_data['steam_id']
        player_name = parsed_data['player_name']
        action = parsed_data['action']
        category = parsed_data['category']
        
        # Formatar timestamp em português
        formatted_time = timestamp.strftime('%d/%m/%Y %H:%M:%S')
        
        return {
            'embeds': [{
                'title': f"{category['emoji']} {category['name']}",
                'description': (
                    f"**Admin:** {player_name}\n"
                    f"**Steam ID:** `{steam_id}`\n"
                    f"**Comando:** {action}\n"
                    f"**Horário:** {formatted_time}"
                ),
                'color': category['color'],
                'timestamp': timestamp.isoformat(),
                'footer': {
                    'text': 'SCUM Server Manager - Admin Log'
                }
            }]
        }
    
    def _command_exists_in_database(self, command_id: str, parsed_data: Dict) -> bool:
        """Verifica se o comando já existe no banco de dados"""
        try:
            import sqlite3
            
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                
                # Verificar se o comando já existe na tabela admin_commands_processed
                cursor.execute('''
                    SELECT COUNT(*) FROM admin_commands_processed 
                    WHERE command_id = ?
                ''', (command_id,))
                
                count = cursor.fetchone()[0]
                
                return count > 0
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                logger.warning(f"Banco de dados bloqueado ao verificar comando, tentando novamente: {e}")
                # Retry simples
                import time
                time.sleep(0.1)
                try:
                    with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT COUNT(*) FROM admin_commands_processed 
                            WHERE command_id = ?
                        ''', (command_id,))
                        count = cursor.fetchone()[0]
                        return count > 0
                except Exception as retry_e:
                    logger.error(f"Erro ao verificar comando no banco (retry): {retry_e}")
                    return False
            else:
                logger.error(f"Erro ao verificar comando no banco: {e}")
                return False
        except Exception as e:
            logger.error(f"Erro ao verificar comando no banco: {e}")
            return False
    
    def _save_command_to_database(self, parsed_data: Dict, discord_sent: int = 1):
        """Salva comando processado no banco de dados"""
        import sqlite3
        import time
        
        max_retries = 3
        retry_delay = 0.2
        
        for attempt in range(max_retries):
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    cursor = conn.cursor()

                    # Criar tabela se não existir (schema base)
                    cursor.execute(
                        '''
                        CREATE TABLE IF NOT EXISTS admin_commands_processed (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            command_id TEXT UNIQUE NOT NULL,
                            steam_id TEXT NOT NULL,
                            player_name TEXT NOT NULL,
                            action TEXT NOT NULL,
                            timestamp TEXT NOT NULL,
                            category TEXT NOT NULL,
                            discord_sent INTEGER DEFAULT 1,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    '''
                    )

                    # Migração leve (compatível): adicionar colunas novas se não existirem
                    for ddl in (
                        "ALTER TABLE admin_commands_processed ADD COLUMN category_key TEXT",
                        "ALTER TABLE admin_commands_processed ADD COLUMN category_name TEXT",
                        "ALTER TABLE admin_commands_processed ADD COLUMN event_type TEXT",
                    ):
                        try:
                            cursor.execute(ddl)
                        except Exception:
                            pass

                    category_info = parsed_data.get("category") or {}
                    category_key = (category_info.get("category") or "other").strip().lower() or "other"
                    category_name = category_info.get("name") or self.command_categories.get(category_key, {}).get("name") or "Other"
                    event_type = parsed_data.get("event_type") or "command"

                    # Inserir comando na tabela
                    cursor.execute(
                        '''
                        INSERT OR IGNORE INTO admin_commands_processed (
                            command_id, steam_id, player_name, action, timestamp,
                            category, category_key, category_name, event_type, discord_sent
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                        (
                            parsed_data["command_id"],
                            parsed_data["steam_id"],
                            parsed_data["player_name"],
                            parsed_data["action"],
                            parsed_data["timestamp"].isoformat(),
                            category_key,
                            category_key,
                            category_name,
                            event_type,
                            int(discord_sent or 0),
                        ),
                    )

                    conn.commit()
                    logger.info(f"Comando salvo no banco: {parsed_data['action'][:50]}...")
                    return

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower():
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Banco de dados bloqueado (tentativa {attempt + 1}/{max_retries}), aguardando..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    logger.error(
                        f"Erro ao salvar comando no banco após {max_retries} tentativas: {e}"
                    )
                    import traceback

                    traceback.print_exc()
                    return

                logger.error(f"Erro ao salvar comando no banco: {e}")
                import traceback

                traceback.print_exc()
                return
            except Exception as e:
                logger.error(f"Erro ao salvar comando no banco: {e}")
                import traceback

                traceback.print_exc()
                return
    
    def _find_latest_admin_log(self, log_directory: str) -> Optional[str]:
        """Encontrar o arquivo admin_*.log mais recente"""
        try:
            if not os.path.exists(log_directory):
                return None
            
            admin_files = []
            for file in os.listdir(log_directory):
                if file.startswith('admin_') and file.endswith('.log'):
                    file_path = os.path.join(log_directory, file)
                    mtime = os.path.getmtime(file_path)
                    admin_files.append((file_path, mtime))
            
            if not admin_files:
                return None
            
            # Retornar o arquivo mais recente
            latest_file = max(admin_files, key=lambda x: x[1])
            return latest_file[0]
            
        except Exception as e:
            logger.error(f"Erro ao encontrar arquivo admin mais recente: {e}")
            return None
    
    def process_latest_admin_log(self, log_directory: str) -> bool:
        """Processar o arquivo admin_*.log mais recente"""
        try:
            latest_file = self._find_latest_admin_log(log_directory)
            if not latest_file:
                logger.info("Nenhum arquivo admin_*.log encontrado")
                return False
            
            logger.info(f"Processando arquivo admin mais recente: {os.path.basename(latest_file)}")
            return self.process_admin_log(latest_file)
            
        except Exception as e:
            logger.error(f"Erro ao processar admin log mais recente: {e}")
            return False
    
    def process_admin_log(self, log_file_path: str) -> bool:
        """
        Processa arquivo de admin log e envia para Discord
        
        Args:
            log_file_path: Caminho para o arquivo admin_*.log
            
        Returns:
            bool: True se processado com sucesso
        """
        try:
            # Obter webhook URL
            webhook_url = self._get_admin_webhook_url()
            if not webhook_url or not str(webhook_url).strip():
                logger.warning("Webhook adminlog não configurado")
                webhook_url = None
            
            # Ler arquivo
            try:
                with open(log_file_path, 'r', encoding='utf-16le') as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Erro ao ler arquivo {log_file_path}: {e}")
                    return False
            
            # Processar linhas
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            if not lines:
                logger.info("Nenhuma linha encontrada no admin log")
                return True
            
            processed_commands = 0
            
            logger.info(f"Processando {len(lines)} linhas do admin log")
            
            # Processar cada linha
            for line in lines:
                if not line:
                    continue
                    
                # Parse da linha
                parsed_data = self._parse_admin_line(line)
                if not parsed_data:
                    logger.debug(f"Linha não parseada: {line}")
                    continue
                
                command_id = parsed_data['command_id']
                
                # Verificar se o comando já existe no banco de dados
                if self._command_exists_in_database(command_id, parsed_data):
                    logger.info(f"Comando {command_id} já existe no banco, pulando.")
                    continue
                
                # Formatar mensagem Discord
                discord_message = self._format_discord_message(parsed_data)
                
                # Enviar para Discord
                try:
                    if webhook_url:
                        response = requests.post(
                            webhook_url,
                            json=discord_message,
                            timeout=10
                        )
                        
                        if response.status_code == 204:
                            logger.info(f"Comando admin enviado: {parsed_data['action'][:50]}...")
                            processed_commands += 1
                            
                            # Salvar comando no banco de dados
                            self._save_command_to_database(parsed_data, discord_sent=1)
                            
                        else:
                            logger.error(f"Falha ao enviar comando admin: {response.status_code}")
                            self._save_command_to_database(parsed_data, discord_sent=0)
                    else:
                        self._save_command_to_database(parsed_data, discord_sent=0)
                        
                except Exception as e:
                    logger.error(f"Erro ao enviar webhook: {e}")
                    self._save_command_to_database(parsed_data, discord_sent=0)
            
            logger.info(f"Admin log processado: {processed_commands} comandos enviados")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar admin log: {e}")
            return False
    
    def _get_last_processed_command(self) -> Optional[str]:
        """Obtém o último comando processado do banco de dados"""
        try:
            import sqlite3
            
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                
                # Criar tabela se não existir
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS admin_commands_processed (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        command_id TEXT UNIQUE NOT NULL,
                        steam_id TEXT NOT NULL,
                        player_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        category TEXT NOT NULL,
                        discord_sent INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Obter último comando processado
                cursor.execute('''
                    SELECT command_id 
                    FROM admin_commands_processed 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Erro ao obter último comando processado: {e}")
            return None

    def get_processing_stats(self) -> Dict:
        """Obtém estatísticas do processamento"""
        try:
            import sqlite3
            
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                
                # Criar tabela se não existir
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS admin_commands_processed (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        command_id TEXT UNIQUE NOT NULL,
                        steam_id TEXT NOT NULL,
                        player_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        category TEXT NOT NULL,
                        discord_sent INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Contar comandos processados
                cursor.execute('SELECT COUNT(*) FROM admin_commands_processed')
                total_commands = cursor.fetchone()[0]
                
                # Último comando processado
                cursor.execute('''
                    SELECT command_id, timestamp, created_at 
                    FROM admin_commands_processed 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''')
                last_command = cursor.fetchone()
                
                if last_command:
                    return {
                        'total_commands': total_commands,
                        'last_command_id': last_command[0],
                        'last_timestamp': last_command[1],
                        'last_processed': last_command[2],
                        'status': 'Ativo'
                    }
                else:
                    return {
                        'total_commands': 0,
                        'status': 'Nenhum comando processado'
                    }
                
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {'status': 'Erro ao obter estatísticas'}
