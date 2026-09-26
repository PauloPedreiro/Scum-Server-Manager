"""
Parser de Logs de Chest Ownership do SCUM
Extrai dados de propriedade de containers/veículos dos logs
"""

import re
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

class ChestOwnershipParser:
    def __init__(self):
        # Regex para extrair dados de chest ownership claimed
        # Formato: 2025.10.19-00.17.09: Chest (entity id: 13584383) ownership claimed. Owner: 76561198262392446 (325, BrwtusOff). Location: X=73966.914062 Y=77898.226562 Z=34886.937500
        self.ownership_claimed_pattern = re.compile(
            r"(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*Chest\s*\(entity id:\s*(\d+)\)\s*ownership\s+claimed\.\s*Owner:\s*(\d+)\s*\((\d+),\s*([^)]+)\)\.\s*Location:\s*X=([\d.-]+)\s*Y=([\d.-]+)\s*Z=([\d.-]+)",
            re.IGNORECASE
        )
        
        # Regex para extrair dados de chest ownership changed
        # Formato: 2025.10.19-00.23.49: Chest (entity id: 14262805) ownership changed. Old owner: 76561198352119687 (149, Marco Zero) -> New owner: 76561198140683162 (322, Jovigono). Location: X=-682827.562500 Y=-251619.140625 Z=12569.433594
        self.ownership_changed_pattern = re.compile(
            r"(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*Chest\s*\(entity id:\s*(\d+)\)\s*ownership\s+changed\.\s*Old owner:\s*(\d+)\s*\((\d+),\s*([^)]+)\)\s*->\s*New owner:\s*(\d+)\s*\((\d+),\s*([^)]+)\)\.\s*Location:\s*X=([\d.-]+)\s*Y=([\d.-]+)\s*Z=([\d.-]+)",
            re.IGNORECASE
        )
        
        # Padrões para ignorar
        self.ignore_patterns = [
            re.compile(r"^\s*$"),  # Linhas vazias
            re.compile(r"Game version:"),  # Linhas de versão
        ]
    
    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parsear uma linha de log de chest ownership"""
        try:
            line = line.strip()
            
            # Verificar se deve ignorar a linha
            for pattern in self.ignore_patterns:
                if pattern.search(line):
                    return None
            
            # Tentar fazer match com padrão de ownership claimed
            match = self.ownership_claimed_pattern.match(line)
            if match:
                return self._extract_ownership_claimed_data(match)
            
            # Tentar fazer match com padrão de ownership changed
            match = self.ownership_changed_pattern.match(line)
            if match:
                return self._extract_ownership_changed_data(match)
            
            return None
            
        except Exception as e:
            print(f"ERRO Erro ao parsear linha de chest ownership: {e}")
            print(f"   Linha: {line[:100]}...")
            return None
    
    def _extract_ownership_claimed_data(self, match) -> Dict[str, Any]:
        """Extrair dados estruturados do match do regex para ownership claimed"""
        try:
            # Extrair grupos do regex
            timestamp_str = match.group(1)
            entity_id = int(match.group(2))
            steam_id = match.group(3)
            player_id = int(match.group(4))
            player_name = match.group(5).strip()
            location_x = float(match.group(6))
            location_y = float(match.group(7))
            location_z = float(match.group(8))
            
            # Converter timestamp
            timestamp = self._parse_timestamp(timestamp_str)
            
            return {
                'timestamp': timestamp,
                'entity_id': entity_id,
                'steam_id': steam_id,
                'player_id': player_id,
                'player_name': player_name,
                'ownership_type': 'claimed',
                'previous_owner_steam_id': None,
                'previous_owner_name': None,
                'location_x': location_x,
                'location_y': location_y,
                'location_z': location_z,
                'raw_line': match.group(0)
            }
            
        except Exception as e:
            print(f"ERRO Erro ao extrair dados de ownership claimed: {e}")
            return None
    
    def _extract_ownership_changed_data(self, match) -> Dict[str, Any]:
        """Extrair dados estruturados do match do regex para ownership changed"""
        try:
            # Extrair grupos do regex
            timestamp_str = match.group(1)
            entity_id = int(match.group(2))
            old_steam_id = match.group(3)
            old_player_id = int(match.group(4))
            old_player_name = match.group(5).strip()
            new_steam_id = match.group(6)
            new_player_id = int(match.group(7))
            new_player_name = match.group(8).strip()
            location_x = float(match.group(9))
            location_y = float(match.group(10))
            location_z = float(match.group(11))
            
            # Converter timestamp
            timestamp = self._parse_timestamp(timestamp_str)
            
            return {
                'timestamp': timestamp,
                'entity_id': entity_id,
                'steam_id': new_steam_id,  # Novo proprietário
                'player_id': new_player_id,
                'player_name': new_player_name,
                'ownership_type': 'changed',
                'previous_owner_steam_id': old_steam_id,
                'previous_owner_name': old_player_name,
                'location_x': location_x,
                'location_y': location_y,
                'location_z': location_z,
                'raw_line': match.group(0)
            }
            
        except Exception as e:
            print(f"ERRO Erro ao extrair dados de ownership changed: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Converter timestamp do log para datetime"""
        try:
            # Formato: 2025.10.19-00.17.09
            # Converter para: 2025-10-19 00:17:09
            
            # Dividir em data e hora
            date_part, time_part = timestamp_str.split('-')
            
            # Converter data: 2025.10.19 -> 2025-10-19
            formatted_date = date_part.replace('.', '-')
            
            # Converter hora: 00.17.09 -> 00:17:09
            formatted_time = time_part.replace('.', ':')
            
            # Combinar: 2025-10-19 00:17:09
            formatted_timestamp = f"{formatted_date} {formatted_time}"
            
            return datetime.strptime(formatted_timestamp, "%Y-%m-%d %H:%M:%S")
            
        except Exception as e:
            print(f"ERRO Erro ao converter timestamp: {e}")
            print(f"Timestamp original: {timestamp_str}")
            # Retornar timestamp atual como fallback
            return datetime.now()
    
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parsear arquivo completo e retornar todas as claims de ownership"""
        claims = []
        
        try:
            # Tentar UTF-16LE primeiro (padrão do SCUM)
            try:
                with open(file_path, 'r', encoding='utf-16le') as f:
                    for line_num, line in enumerate(f, 1):
                        claim_data = self.parse_line(line)
                        if claim_data:
                            claim_data['line_number'] = line_num
                            claim_data['source_file'] = os.path.basename(file_path)
                            claims.append(claim_data)
            except UnicodeDecodeError:
                # Fallback para UTF-8 se UTF-16LE falhar
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        claim_data = self.parse_line(line)
                        if claim_data:
                            claim_data['line_number'] = line_num
                            claim_data['source_file'] = os.path.basename(file_path)
                            claims.append(claim_data)
            
            # logger.debug("Arquivo chest ownership parseado")
            # logger.debug(f"Claims encontradas: {len(claims)}")
            
        except Exception as e:
            print(f"ERRO Erro ao parsear arquivo chest ownership: {e}")
        
        return claims
    
    def parse_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Parsear lista de linhas e retornar claims"""
        claims = []
        
        for line_num, line in enumerate(lines, 1):
            claim_data = self.parse_line(line)
            if claim_data:
                claim_data['line_number'] = line_num
                claims.append(claim_data)
        
        return claims
    
    def validate_claim_data(self, claim_data: Dict[str, Any]) -> bool:
        """Validar dados extraídos da claim"""
        required_fields = ['timestamp', 'entity_id', 'steam_id', 'player_name', 'ownership_type']
        
        for field in required_fields:
            if field not in claim_data or claim_data[field] is None:
                print(f"⚠️ Campo obrigatório ausente: {field}")
                return False
        
        # Validar Steam ID (deve ser numérico)
        if not claim_data['steam_id'].isdigit():
            print(f"⚠️ Steam ID inválido: {claim_data['steam_id']}")
            return False
        
        # Validar Entity ID (deve ser numérico)
        if not isinstance(claim_data['entity_id'], int):
            print(f"⚠️ Entity ID inválido: {claim_data['entity_id']}")
            return False
        
        # Validar Ownership Type
        if claim_data['ownership_type'] not in ['claimed', 'changed']:
            print(f"⚠️ Ownership Type inválido: {claim_data['ownership_type']}")
            return False
        
        return True
    
    def get_parser_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do parser"""
        return {
            'ownership_claimed_pattern': self.ownership_claimed_pattern.pattern,
            'ownership_changed_pattern': self.ownership_changed_pattern.pattern,
            'ignore_patterns': [p.pattern for p in self.ignore_patterns]
        }
