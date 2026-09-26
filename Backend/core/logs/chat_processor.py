#!/usr/bin/env python3
"""
Processador de logs de chat do SCUM
Monitora mensagens do chat global e envia para Discord
"""

import os
import json
import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from pathlib import Path

from core.logs.temp_file_manager import TempFileManager
from core.logs.chat_notifier import ChatNotifier
from utils.logger import StructuredLogger


class ChatProcessor:
    """Processador de logs de chat do SCUM"""
    
    def __init__(self, webhook_config: Dict = None, logger: StructuredLogger = None, chat_config: Dict = None):
        """
        Inicializar processador de chat
        
        Args:
            webhook_config: Configuração dos webhooks Discord
            logger: Logger estruturado
        """
        self.logger = logger or StructuredLogger()
        self.webhook_config = webhook_config or {}
        self.chat_config = chat_config or {}
        
        # Configurações
        self.data_dir = Path("data")
        self.processed_file = self.data_dir / "chat_processed.json"
        self.webhook_name = "chat_in_game"

        channels = self.chat_config.get("channels")
        self.allowed_channels = None
        if isinstance(channels, list) and channels:
            self.allowed_channels = set(str(c).strip().lower() for c in channels if str(c).strip())
        
        # Inicializar componentes
        self.temp_manager = TempFileManager(str(self.data_dir / "temp"))
        self.notifier = ChatNotifier(self.webhook_config, logger=self.logger)
        
        # Cache de mensagens processadas
        self.processed_messages: Set[str] = set()
        self.load_processed_messages()
        
        self.logger.info("ChatProcessor inicializado")
    
    def load_processed_messages(self):
        """Carregar mensagens já processadas"""
        try:
            if self.processed_file.exists():
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_messages = set(data.get('processed_messages', []))
                
                self.logger.debug(f"Carregadas {len(self.processed_messages)} mensagens processadas")
            else:
                self.logger.debug("Arquivo de mensagens processadas não encontrado, iniciando vazio")
        except Exception as e:
            self.logger.error(f"Erro ao carregar mensagens processadas: {e}")
            self.processed_messages = set()
    
    def save_processed_messages(self):
        """Salvar mensagens processadas"""
        try:
            # Criar diretório se não existir
            self.data_dir.mkdir(exist_ok=True)
            
            data = {
                'processed_messages': list(self.processed_messages),
                'last_update': datetime.now().isoformat()
            }
            
            with open(self.processed_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Salvas {len(self.processed_messages)} mensagens processadas")
        except Exception as e:
            self.logger.error(f"Erro ao salvar mensagens processadas: {e}")
    
    def generate_message_hash(self, timestamp: str, steam_id: str, message: str) -> str:
        """
        Gerar hash único para uma mensagem
        
        Args:
            timestamp: Timestamp da mensagem
            steam_id: Steam ID do jogador
            message: Conteúdo da mensagem
            
        Returns:
            Hash MD5 da mensagem
        """
        # Combinar timestamp + steam_id + mensagem para criar hash único
        combined = f"{timestamp}|{steam_id}|{message}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()

    def generate_message_hash_with_channel(self, timestamp: str, steam_id: str, channel: str, message: str) -> str:
        combined = f"{timestamp}|{steam_id}|{channel}|{message}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()

    def should_send_channel(self, channel: Optional[str]) -> bool:
        if self.allowed_channels is None:
            return True
        if not channel:
            return False
        return str(channel).strip().lower() in self.allowed_channels
    
    def parse_chat_line(self, line: str) -> Optional[Dict]:
        """
        Parsear linha do log de chat
        
        Args:
            line: Linha do log
            
        Returns:
            Dicionário com dados da mensagem ou None se não for chat global
        """
        try:
            # Tentar padrão com canal (Global)
            pattern_channel = r"(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}): '(\d+):([^']+)\((\d+)\)' '(Global|Globaal|Gloobal|Local|Squad|Admin)[:]*\s*(.+)'"
            match = re.match(pattern_channel, line)
            
            # Fallback: sem exigir canal (alguns servidores logam sem a palavra 'Global')
            if not match:
                pattern_generic = r"(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}): '(\d+):([^']+)\((\d+)\)'.*?:\s*(.+)"
                match = re.match(pattern_generic, line)
            
            if not match:
                self.logger.debug(f"Linha de chat não pôde ser parseada: {line[:120]}...")
                return None
            
            groups = match.groups()
            if len(groups) == 6:
                timestamp, steam_id, player_name, player_id, channel, message = groups
                channel_norm = channel.strip()
                if channel_norm.lower() in ("globaal", "gloobal"):
                    channel_norm = "Global"
            else:
                timestamp, steam_id, player_name, player_id, message = groups
                channel_norm = None
            
            return {
                'timestamp': timestamp,
                'steam_id': steam_id,
                'player_name': player_name.strip(),
                'player_id': int(player_id),
                'channel': channel_norm,
                'message': message.strip()
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao parsear linha de chat: {e}")
            return None
    
    def process_file(self, file_path: str) -> Dict:
        """
        Processar arquivo de chat
        
        Args:
            file_path: Caminho do arquivo de log
            
        Returns:
            Estatísticas do processamento
        """
        stats = {
            'file_path': file_path,
            'lines_processed': 0,
            'messages_found': 0,
            'messages_sent': 0,
            'errors': 0
        }
        
        try:
            self.logger.info(f"Processando arquivo de chat: {file_path}")
            
            # Copiar arquivo para temp se necessário
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                temp_path = file_path
            
            # Processar arquivo (tentar UTF-16LE primeiro, depois UTF-8)
            try:
                with open(temp_path, 'r', encoding='utf-16le') as f:
                    for line_num, line in enumerate(f, 1):
                        stats['lines_processed'] += 1
                        
                        try:
                            # Parsear linha
                            chat_data = self.parse_chat_line(line.strip())
                            if not chat_data:
                                continue
                            
                            stats['messages_found'] += 1

                            if not self.should_send_channel(chat_data.get('channel')):
                                continue
                            
                            # Gerar hash da mensagem
                            channel_value = chat_data.get('channel') or ""
                            if channel_value:
                                message_hash = self.generate_message_hash_with_channel(
                                    chat_data['timestamp'],
                                    chat_data['steam_id'],
                                    channel_value,
                                    chat_data['message']
                                )
                                legacy_hash = self.generate_message_hash(
                                    chat_data['timestamp'],
                                    chat_data['steam_id'],
                                    chat_data['message']
                                )
                            else:
                                message_hash = self.generate_message_hash(
                                    chat_data['timestamp'],
                                    chat_data['steam_id'],
                                    chat_data['message']
                                )
                                legacy_hash = None
                            
                            # Verificar se já foi processada
                            if (message_hash in self.processed_messages) or (legacy_hash and legacy_hash in self.processed_messages):
                                self.logger.debug(f"Mensagem já processada: {chat_data['player_name']}: {chat_data['message'][:50]}...")
                                continue
                            
                            # Enviar para Discord
                            success = self.notifier.send_chat_message(
                                chat_data['player_name'],
                                chat_data['message'],
                                channel=chat_data.get('channel')
                            )
                            
                            if success:
                                # Marcar como processada
                                self.processed_messages.add(message_hash)
                                stats['messages_sent'] += 1
                                
                                self.logger.debug(f"Mensagem enviada: {chat_data['player_name']}: {chat_data['message'][:50]}...")
                            else:
                                self.logger.warn(f"Falha ao enviar mensagem: {chat_data['player_name']}: {chat_data['message'][:50]}...")
                        
                        except Exception as e:
                            stats['errors'] += 1
                            self.logger.error(f"Erro ao processar linha {line_num}: {e}")
            except UnicodeDecodeError:
                # Fallback para UTF-8 se UTF-16LE falhar
                with open(temp_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        stats['lines_processed'] += 1
                        
                        try:
                            # Parsear linha
                            chat_data = self.parse_chat_line(line.strip())
                            if not chat_data:
                                continue
                            
                            stats['messages_found'] += 1

                            if not self.should_send_channel(chat_data.get('channel')):
                                continue
                            
                            # Gerar hash da mensagem
                            channel_value = chat_data.get('channel') or ""
                            if channel_value:
                                message_hash = self.generate_message_hash_with_channel(
                                    chat_data['timestamp'],
                                    chat_data['steam_id'],
                                    channel_value,
                                    chat_data['message']
                                )
                                legacy_hash = self.generate_message_hash(
                                    chat_data['timestamp'],
                                    chat_data['steam_id'],
                                    chat_data['message']
                                )
                            else:
                                message_hash = self.generate_message_hash(
                                    chat_data['timestamp'],
                                    chat_data['steam_id'],
                                    chat_data['message']
                                )
                                legacy_hash = None
                            
                            # Verificar se já foi processada
                            if (message_hash in self.processed_messages) or (legacy_hash and legacy_hash in self.processed_messages):
                                self.logger.debug(f"Mensagem já processada: {chat_data['player_name']}: {chat_data['message'][:50]}...")
                                continue
                            
                            # Enviar para Discord
                            success = self.notifier.send_chat_message(
                                chat_data['player_name'],
                                chat_data['message'],
                                channel=chat_data.get('channel')
                            )
                            
                            if success:
                                # Marcar como processada
                                self.processed_messages.add(message_hash)
                                stats['messages_sent'] += 1
                                
                                self.logger.debug(f"Mensagem enviada: {chat_data['player_name']}: {chat_data['message'][:50]}...")
                            else:
                                self.logger.warn(f"Falha ao enviar mensagem: {chat_data['player_name']}: {chat_data['message'][:50]}...")
                        
                        except Exception as e:
                            stats['errors'] += 1
                            self.logger.error(f"Erro ao processar linha {line_num}: {e}")
            
            # Salvar mensagens processadas
            if stats['messages_sent'] > 0:
                self.save_processed_messages()
            
            # Limpar arquivo temporário se foi criado
            if temp_path != file_path:
                self.temp_manager.cleanup_temp_file(temp_path)
            
            self.logger.info(f"Processamento concluído: {stats['messages_sent']} mensagens enviadas de {stats['messages_found']} encontradas")
            
        except Exception as e:
            stats['errors'] += 1
            self.logger.error(f"Erro ao processar arquivo {file_path}: {e}")
        
        return stats
    
    def cleanup_old_hashes(self, days: int = 7):
        """
        Limpar hashes antigos para evitar arquivo muito grande
        
        Args:
            days: Número de dias para manter hashes
        """
        try:
            # Por simplicidade, vamos manter apenas os últimos 1000 hashes
            # Em uma implementação mais sofisticada, poderíamos usar timestamps
            if len(self.processed_messages) > 1000:
                # Converter para lista, pegar os últimos 1000, converter de volta para set
                messages_list = list(self.processed_messages)
                self.processed_messages = set(messages_list[-1000:])
                
                self.save_processed_messages()
                self.logger.info(f"Limpeza de hashes: mantidos últimos 1000 de {len(messages_list)}")
        
        except Exception as e:
            self.logger.error(f"Erro na limpeza de hashes: {e}")
    
    def get_stats(self) -> Dict:
        """
        Obter estatísticas do processador
        
        Returns:
            Estatísticas atuais
        """
        return {
            'processed_messages_count': len(self.processed_messages),
            'processed_file_exists': self.processed_file.exists(),
            'webhook_name': self.webhook_name,
            'temp_manager_active': self.temp_manager is not None
        }
