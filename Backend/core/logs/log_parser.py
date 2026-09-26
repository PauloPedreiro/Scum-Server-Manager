"""
Parser de Logs do SCUM
Extrai dados estruturados dos logs de login/logout
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

class LogParser:
    def __init__(self):
        # Regex para extrair dados de login/logout
        self.login_pattern = re.compile(
            r"(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}): "  # Timestamp
            r"'(\d+\.\d+\.\d+\.\d+) "                      # IP Address
            r"(\d+):"                                      # Steam ID
            r"([^(]+)\((\d+)\)' "                          # Player Name e ID
            r"logged (in|out) at: "                       # Action
            r"X=([\d.-]+) Y=([\d.-]+) Z=([\d.-]+)"        # Coordinates
        )
        
        # Regex para linha de versão do jogo (ignorar)
        self.version_pattern = re.compile(r"Game version:")
        
        # Regex para linhas vazias ou inválidas
        self.empty_pattern = re.compile(r"^\s*$")
    
    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parsear uma linha de log e extrair dados"""
        try:
            line = line.strip()
            
            # Ignorar linhas vazias
            if self.empty_pattern.match(line):
                return None
            
            # Ignorar linhas de versão do jogo
            if self.version_pattern.search(line):
                return None
            
            # Ignorar linhas de transações bancárias (processadas por BankTransactionProcessor)
            if '[Trade]' in line or '[Bank]' in line or '[Currency Conversion]' in line or '[Trade-Mechanic]' in line:
                return None
            
            # Tentar fazer match com padrão de login/logout
            match = self.login_pattern.match(line)
            if match:
                return self._extract_session_data(match)
            
            # Log de linha não reconhecida (silencioso - comentado para reduzir ruído)
            # logger.debug(f"Linha não reconhecida: {line[:100]}...")
            return None
            
        except Exception as e:
            print(f"ERRO Erro ao parsear linha: {e}")
            print(f"   Linha: {line[:100]}...")
            return None
    
    def _extract_session_data(self, match) -> Dict[str, Any]:
        """Extrair dados estruturados do match do regex"""
        try:
            # Extrair grupos do regex
            timestamp_str = match.group(1)
            ip_address = match.group(2)
            steam_id = match.group(3)
            player_name = match.group(4)
            player_id = int(match.group(5))
            action = match.group(6)
            coordinates_x = float(match.group(7))
            coordinates_y = float(match.group(8))
            coordinates_z = float(match.group(9))
            
            # Converter timestamp
            timestamp = self._parse_timestamp(timestamp_str)
            
            # Mapear ação para o formato esperado pelo PlayerProcessor
            action_mapping = {
                'in': 'login',
                'out': 'logout'
            }
            mapped_action = action_mapping.get(action, action)
            
            return {
                'steam_id': steam_id,
                'player_name': player_name,
                'player_id': player_id,
                'ip_address': ip_address,
                'action': mapped_action,
                'coordinates_x': coordinates_x,
                'coordinates_y': coordinates_y,
                'coordinates_z': coordinates_z,
                'timestamp': timestamp
            }
            
        except Exception as e:
            print(f"ERRO Erro ao extrair dados da sessão: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Converter timestamp do log para datetime"""
        try:
            # Formato: 2025.10.18-00.03.38
            # Converter para: 2025-10-18 00:03:38
            
            # Dividir em data e hora
            date_part, time_part = timestamp_str.split('-')
            
            # Converter data: 2025.10.18 -> 2025-10-18
            formatted_date = date_part.replace('.', '-')
            
            # Converter hora: 00.03.38 -> 00:03:38
            formatted_time = time_part.replace('.', ':')
            
            # Combinar: 2025-10-18 00:03:38
            formatted_timestamp = f"{formatted_date} {formatted_time}"
            
            return datetime.strptime(formatted_timestamp, "%Y-%m-%d %H:%M:%S")
            
        except Exception as e:
            print(f"ERRO Erro ao converter timestamp: {e}")
            print(f"Timestamp original: {timestamp_str}")
            print(f"Timestamp formatado: {formatted_timestamp}")
            # Retornar timestamp atual como fallback
            return datetime.now()
    
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parsear arquivo completo e retornar todas as sessões"""
        sessions = []
        
        try:
            # Tentar UTF-16LE primeiro (padrão do SCUM)
            try:
                with open(file_path, 'r', encoding='utf-16le') as f:
                    for line_num, line in enumerate(f, 1):
                        session_data = self.parse_line(line)
                        if session_data:
                            sessions.append(session_data)
            except UnicodeDecodeError:
                # Fallback para UTF-8 se UTF-16LE falhar
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        session_data = self.parse_line(line)
                        if session_data:
                            sessions.append(session_data)
            
            # logger.debug(f"Arquivo parseado: {os.path.basename(file_path)}")
            # logger.debug(f"Sessões encontradas: {len(sessions)}")
            
        except Exception as e:
            print(f"ERRO Erro ao parsear arquivo: {e}")
        
        return sessions
    
    def parse_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Parsear lista de linhas e retornar sessões"""
        sessions = []
        
        for line_num, line in enumerate(lines, 1):
            session_data = self.parse_line(line)
            if session_data:
                sessions.append(session_data)
        
        return sessions
    
    def validate_session_data(self, session_data: Dict[str, Any]) -> bool:
        """Validar dados extraídos da sessão"""
        required_fields = ['steam_id', 'player_name', 'player_id', 'action', 'timestamp']
        
        for field in required_fields:
            if field not in session_data or session_data[field] is None:
                print(f"⚠️ Campo obrigatório ausente: {field}")
                return False
        
        # Validar Steam ID (deve ser numérico)
        if not session_data['steam_id'].isdigit():
            print(f"⚠️ Steam ID inválido: {session_data['steam_id']}")
            return False
        
        # Validar Player ID (deve ser numérico)
        if not isinstance(session_data['player_id'], int):
            print(f"⚠️ Player ID inválido: {session_data['player_id']}")
            return False
        
        # Validar Action (deve ser 'in' ou 'out')
        if session_data['action'] not in ['in', 'out']:
            print(f"⚠️ Action inválida: {session_data['action']}")
            return False
        
        return True
    
    def get_parser_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do parser"""
        return {
            'login_pattern': self.login_pattern.pattern,
            'version_pattern': self.version_pattern.pattern,
            'empty_pattern': self.empty_pattern.pattern
        }
