import re
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from .temp_file_manager import TempFileManager

class GameplayLogParser:
    """
    Parser para logs de gameplay do SCUM
    Extrai atividades de jogadores em tempo real
    """
    
    def __init__(self, temp_manager: TempFileManager):
        self.temp_manager = temp_manager
        # Regex de número robusta:
        # - aceita inteiros e floats (com sinal)
        # - aceita pontuação extra no final (ex: "3170.810." ou "3170.810,")
        _num = r"-?\d+(?:\.\d+)?"
        _num_tailed = rf"({_num})(?:[.,])?"
        # Regex para extrair dados das atividades
        self.activity_patterns = {
            'minigame': re.compile(
                rf'\[LogMinigame\]\s+\[.*?\]\s+User:\s+([^(]+)\s+\((\d+),\s+(\d+)\)\.\s+.*?Location:\s+X={_num_tailed}\s+Y={_num_tailed}\s+Z={_num_tailed}'
            ),
            'kill': re.compile(
                rf'\[LogKill\]\s+User:\s+([^(]+)\s+\((\d+),\s+(\d+)\)\.\s+.*?Location:\s+X={_num_tailed}\s+Y={_num_tailed}\s+Z={_num_tailed}'
            ),
            'damage': re.compile(
                rf'\[LogDamage\]\s+User:\s+([^(]+)\s+\((\d+),\s+(\d+)\)\.\s+.*?Location:\s+X={_num_tailed}\s+Y={_num_tailed}\s+Z={_num_tailed}'
            ),
            'inventory': re.compile(
                rf'\[LogInventory\]\s+User:\s+([^(]+)\s+\((\d+),\s+(\d+)\)\.\s+.*?Location:\s+X={_num_tailed}\s+Y={_num_tailed}\s+Z={_num_tailed}'
            ),
            'vehicle': re.compile(
                rf'\[LogVehicle\]\s+User:\s+([^(]+)\s+\((\d+),\s+(\d+)\)\.\s+.*?Location:\s+X={_num_tailed}\s+Y={_num_tailed}\s+Z={_num_tailed}'
            ),
            'building': re.compile(
                rf'\[LogBuilding\]\s+User:\s+([^(]+)\s+\((\d+),\s+(\d+)\)\.\s+.*?Location:\s+X={_num_tailed}\s+Y={_num_tailed}\s+Z={_num_tailed}'
            )
        }
        
        # Regex para timestamp
        self.timestamp_pattern = re.compile(r'(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):')
        
        # Regex específica para LogMinigame (extrai campos básicos)
        self.minigame_pattern = re.compile(
            r'\[LogMinigame\]\s+\[([^\]]+)\]\s+User:\s+([^(]+)\s+\((\d+),\s*(\d+)\)'
        )
        self.location_pattern = re.compile(
            rf'Location:\s+X={_num_tailed}\s+Y={_num_tailed}\s+Z={_num_tailed}'
        )

        # Regex específica para LogTrap Armed
        # Exemplo:
        # 2026.04.18-04.24.27: [LogTrap] Armed. User: Pedreiro (1, 76561198040636105). Trap name: Small anti-personnel mine. Location: X=-321507.531 Y=4185.704 Z=35696.000
        self.trap_armed_pattern = re.compile(
            rf"\[LogTrap\]\s+Armed\.\s+User:\s+([^\(]+)\s+\((\d+),\s*(\d+)\)\.\s+Trap\s+name:\s+([^\.]+)\.\s+Location:\s+X={_num_tailed}\s+Y={_num_tailed}\s+Z={_num_tailed}"
        )
        # Regex para extrair informações do proprietário: "User owner: 84([76561198094354554] ARKANJO)"
        # Aceita também variações como "User owner: N/A" ou sem parênteses
        self.owner_pattern = re.compile(
            r'User owner:\s*(\d+)\s*\(\[(\d+)\]\s*([^)]+)\)'
        )
        # Padrão alternativo para casos onde o formato pode variar
        self.owner_pattern_alt = re.compile(
            r'User owner:\s*(\d+)\s*\[(\d+)\]\s*([^.\s]+)'
        )
        # Regex para extrair Success: Yes/No
        self.success_pattern = re.compile(r'Success:\s*(Yes|No)')
        # Regex para extrair Elapsed time: 77.53
        self.elapsed_time_pattern = re.compile(r'Elapsed time:\s*([\d.]+)')
        # Regex para extrair Failed attempts: 38
        self.failed_attempts_pattern = re.compile(r'Failed attempts:\s*(\d+)')
        # Regex para extrair Target object: BPC_ModularDoor_Loophole_Double_Wood_C(ID: N/A) ou Target object: WoodenWeaponRack_C(ID: 12941790)
        self.target_object_pattern = re.compile(r'Target object:\s*([^(]+)\s*\(ID:\s*([^)]+)\)')
        # Regex para extrair Lock type: Basic
        self.lock_type_pattern = re.compile(r'Lock type:\s*(\w+)')
        
        print("OK GameplayLogParser inicializado")

    def parse_trap_events_from_lines(self, lines: List[str], original_file_path: str) -> List[Dict[str, Any]]:
        """Extrair eventos de [LogTrap] Armed de uma lista de linhas (processamento incremental)."""
        events: List[Dict[str, Any]] = []

        try:
            log_file = os.path.basename(original_file_path)

            for line_num, raw in enumerate(lines, 1):
                line = (raw or "").strip()
                if not line:
                    continue

                if "[LogTrap]" not in line or "Armed" not in line:
                    continue

                timestamp = None
                timestamp_match = self.timestamp_pattern.match(line)
                if timestamp_match:
                    timestamp = self.parse_timestamp(timestamp_match.group(0))

                m = self.trap_armed_pattern.search(line)
                if not m:
                    continue

                try:
                    player_name = m.group(1).strip()
                    player_id = int(m.group(2))
                    steam_id = str(m.group(3)).strip()
                    trap_name = m.group(4).strip()
                    x = float(m.group(5))
                    y = float(m.group(6))
                    z = float(m.group(7))
                except (ValueError, IndexError) as e:
                    print(f"AVISO: Erro ao extrair evento LogTrap na linha {line_num}: {e}")
                    continue

                events.append(
                    {
                        "log_line": line,
                        "timestamp": timestamp,
                        "event_type": "trap_armed",
                        "steam_id": steam_id,
                        "player_id": player_id,
                        "player_name": player_name,
                        "trap_name": trap_name,
                        "location_x": x,
                        "location_y": y,
                        "location_z": z,
                        "log_file": log_file,
                    }
                )

            return events

        except Exception as e:
            print(f"ERRO ao processar linhas de LogTrap: {e}")
            import traceback

            traceback.print_exc()
            return events
    
    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Converter timestamp do log para datetime"""
        try:
            # Formato: 2025.10.18-04.26.50
            match = self.timestamp_pattern.match(timestamp_str)
            if match:
                date_part = match.group(1)  # 2025.10.18
                time_part = match.group(2)  # 04.26.50
                
                # Converter para formato padrão
                date_formatted = date_part.replace('.', '-')
                time_formatted = time_part.replace('.', ':')
                
                timestamp_str = f"{date_formatted} {time_formatted}"
                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"ERRO ao converter timestamp: {e}")
        return None
    
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Processar arquivo de gameplay e extrair atividades"""
        activities = []
        
        # Criar cópia temporária
        temp_path = self.temp_manager.create_temp_copy(file_path)
        if not temp_path:
            print(f"ERRO Falha ao criar cópia temporária: {file_path}")
            return activities
        
        try:
            # Ler arquivo temporário
            content = self.temp_manager.read_temp_file(temp_path)
            if not content:
                print(f"ERRO Falha ao ler arquivo temporário: {temp_path}")
                return activities
            
            lines = content.split('\n')
            print(f"OK Processando {len(lines)} linhas do arquivo gameplay")
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Extrair timestamp
                timestamp_match = self.timestamp_pattern.match(line)
                if not timestamp_match:
                    continue
                
                timestamp = self.parse_timestamp(timestamp_match.group(0))
                if not timestamp:
                    continue
                
                # Tentar extrair atividade de cada tipo
                for activity_type, pattern in self.activity_patterns.items():
                    match = pattern.search(line)
                    if match:
                        try:
                            activity = {
                                'timestamp': timestamp,
                                'activity_type': activity_type,
                                'player_name': match.group(1).strip(),
                                'player_id': int(match.group(2)),
                                'steam_id': match.group(3),
                                'coordinates': {
                                    'x': float(match.group(4)),
                                    'y': float(match.group(5)),
                                    'z': float(match.group(6))
                                },
                                'raw_line': line
                            }
                            activities.append(activity)
                            print(f"OK Atividade encontrada: {activity_type} - {activity['player_name']}")
                            break  # Encontrou uma atividade, não precisa verificar outros tipos
                        except (ValueError, IndexError) as e:
                            print(f"ERRO ao processar linha {line_num}: {e}")
                            continue
            
            print(f"OK Total de atividades extraídas: {len(activities)}")
            return activities
            
        except Exception as e:
            print(f"ERRO ao processar arquivo gameplay: {e}")
            return activities
        finally:
            # Limpar arquivo temporário
            self.temp_manager.cleanup_temp_file(temp_path)
    
    def get_recent_activities(self, activities: List[Dict[str, Any]], minutes: int = 30) -> List[Dict[str, Any]]:
        """Filtrar atividades recentes (últimos X minutos)"""
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        
        recent_activities = []
        for activity in activities:
            if activity['timestamp'].timestamp() > cutoff_time:
                recent_activities.append(activity)
        
        print(f"OK Atividades recentes (últimos {minutes} min): {len(recent_activities)}")
        return recent_activities
    
    def get_players_with_recent_activity(self, activities: List[Dict[str, Any]], minutes: int = 30) -> Dict[str, Dict[str, Any]]:
        """Obter jogadores com atividade recente"""
        recent_activities = self.get_recent_activities(activities, minutes)
        
        players_activity = {}
        for activity in recent_activities:
            steam_id = activity['steam_id']
            
            if steam_id not in players_activity:
                players_activity[steam_id] = {
                    'steam_id': steam_id,
                    'player_name': activity['player_name'],
                    'player_id': activity['player_id'],
                    'last_activity': activity['timestamp'],
                    'last_coordinates': activity['coordinates'],
                    'activity_types': set(),
                    'total_activities': 0
                }
            
            # Atualizar dados do jogador
            player_data = players_activity[steam_id]
            if activity['timestamp'] > player_data['last_activity']:
                player_data['last_activity'] = activity['timestamp']
                player_data['last_coordinates'] = activity['coordinates']
            
            player_data['activity_types'].add(activity['activity_type'])
            player_data['total_activities'] += 1
        
        # Converter sets para listas para serialização JSON
        for player_data in players_activity.values():
            player_data['activity_types'] = list(player_data['activity_types'])
        
        print(f"OK Jogadores com atividade recente: {len(players_activity)}")
        return players_activity
    
    def parse_minigame_events(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extrair eventos de LogMinigame de um arquivo de log
        Retorna lista de eventos formatados para inserção no banco
        """
        events = []
        
        # Criar cópia temporária
        temp_path = self.temp_manager.create_temp_copy(file_path)
        if not temp_path:
            print(f"ERRO Falha ao criar cópia temporária: {file_path}")
            return events
        
        try:
            # Processar usando arquivo temporário
            events = self._parse_minigame_events_from_file(temp_path, file_path)
            return events
        finally:
            # Limpar arquivo temporário
            self.temp_manager.cleanup_temp_file(temp_path)
    
    def parse_minigame_events_from_temp(self, temp_path: str, original_file_path: str) -> List[Dict[str, Any]]:
        """
        Extrair eventos de LogMinigame de um arquivo temporário já copiado
        Retorna lista de eventos formatados para inserção no banco
        """
        # Processar diretamente o arquivo temporário (sem copiar novamente)
        return self._parse_minigame_events_from_file(temp_path, original_file_path)
    
    def parse_minigame_events_from_lines(self, lines: List[str], original_file_path: str) -> List[Dict[str, Any]]:
        """
        Extrair eventos de LogMinigame de uma lista de linhas (processamento incremental)
        Retorna lista de eventos formatados para inserção no banco
        """
        events = []
        
        try:
            # Obter nome do arquivo original
            log_file = os.path.basename(original_file_path)
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Verificar se é um evento de LogMinigame
                if '[LogMinigame]' not in line:
                    continue
                
                # Extrair timestamp
                timestamp_match = self.timestamp_pattern.match(line)
                if not timestamp_match:
                    continue
                
                timestamp = self.parse_timestamp(timestamp_match.group(0))
                if not timestamp:
                    continue
                
                # Extrair tipo de minigame e dados do jogador
                minigame_match = self.minigame_pattern.search(line)
                if not minigame_match:
                    continue
                
                # Extrair coordenadas (não obrigatório - pode ser None)
                location_match = self.location_pattern.search(line)
                location_x = None
                location_y = None
                location_z = None
                
                if location_match:
                    try:
                        location_x = float(location_match.group(1))
                        location_y = float(location_match.group(2))
                        location_z = float(location_match.group(3))
                    except (ValueError, IndexError) as e:
                        print(f"AVISO: Erro ao extrair coordenadas na linha {line_num}: {e}")
                        location_x = None
                        location_y = None
                        location_z = None
                
                try:
                    minigame_type = minigame_match.group(1).strip()
                    player_name = minigame_match.group(2).strip()
                    player_id = int(minigame_match.group(3))
                    steam_id = minigame_match.group(4)
                    
                    # Extrair Success (Yes/No)
                    success = None
                    success_match = self.success_pattern.search(line)
                    if success_match:
                        success_value = success_match.group(1).strip().upper()
                        if success_value in ('YES', 'TRUE', '1'):
                            success = True
                        elif success_value in ('NO', 'FALSE', '0'):
                            success = False
                        else:
                            success = bool(success_value)
                    else:
                        if 'Failed attempts: 0' in line and 'Success:' not in line:
                            pass
                    
                    # Extrair Elapsed time
                    elapsed_time = None
                    elapsed_match = self.elapsed_time_pattern.search(line)
                    if elapsed_match:
                        try:
                            elapsed_time = float(elapsed_match.group(1))
                        except ValueError:
                            pass
                    
                    # Extrair Failed attempts
                    failed_attempts = None
                    failed_match = self.failed_attempts_pattern.search(line)
                    if failed_match:
                        try:
                            failed_attempts = int(failed_match.group(1))
                        except ValueError:
                            pass
                    
                    # Extrair Target object e ID
                    target_object = None
                    target_object_id = None
                    target_match = self.target_object_pattern.search(line)
                    if target_match:
                        target_object = target_match.group(1).strip()
                        target_id_str = target_match.group(2).strip()
                        if target_id_str.upper() == 'N/A':
                            target_object_id = 'N/A'
                        else:
                            try:
                                target_object_id = str(int(target_id_str))
                            except ValueError:
                                target_object_id = target_id_str
                    
                    # Extrair Lock type
                    lock_type = None
                    lock_match = self.lock_type_pattern.search(line)
                    if lock_match:
                        lock_type = lock_match.group(1).strip()
                    
                    # Extrair informações do proprietário (se houver)
                    owner_id = None
                    owner_steam_id = None
                    owner_name = None
                    is_property_invasion = False
                    
                    # Tentar primeiro padrão
                    owner_match = self.owner_pattern.search(line)
                    if not owner_match:
                        # Tentar padrão alternativo
                        owner_match = self.owner_pattern_alt.search(line)
                    
                    if owner_match:
                        try:
                            owner_id = int(owner_match.group(1))
                            owner_steam_id = owner_match.group(2)
                            owner_name = owner_match.group(3).strip()
                            
                            # Verificar se é invasão de propriedade (owner != lockpicker)
                            if owner_steam_id != steam_id:
                                is_property_invasion = True
                        except (ValueError, IndexError) as e:
                            print(f"AVISO: Erro ao extrair dados do proprietário: {e}")
                            owner_id = None
                            owner_steam_id = None
                            owner_name = None
                    
                    event = {
                        'log_line': line,
                        'timestamp': timestamp,
                        'minigame_type': minigame_type,
                        'steam_id': steam_id,
                        'player_id': player_id,
                        'player_name': player_name,
                        'success': success,
                        'elapsed_time': elapsed_time,
                        'failed_attempts': failed_attempts,
                        'target_object': target_object,
                        'target_object_id': target_object_id,
                        'lock_type': lock_type,
                        'owner_id': owner_id,
                        'owner_steam_id': owner_steam_id,
                        'owner_name': owner_name,
                        'is_property_invasion': is_property_invasion,
                        'location_x': location_x,
                        'location_y': location_y,
                        'location_z': location_z,
                        'log_file': log_file,
                        'discord_sent': False
                    }
                    
                    events.append(event)
                    
                except (ValueError, IndexError) as e:
                    print(f"ERRO ao processar linha {line_num}: {e}")
                    continue
            
            return events
            
        except Exception as e:
            print(f"ERRO ao processar linhas de minigame: {e}")
            import traceback
            traceback.print_exc()
            return events
    
    def _parse_minigame_events_from_file(self, file_path: str, original_file_path: str) -> List[Dict[str, Any]]:
        """
        Método auxiliar para processar eventos de minigame de um arquivo
        """
        events = []
        
        try:
            # Ler arquivo (pode ser temporário ou original)
            content = self.temp_manager.read_temp_file(file_path)
            if not content:
                # Tentar ler diretamente se não conseguir via temp_manager
                try:
                    with open(file_path, 'r', encoding='utf-16le', errors='ignore') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
            
            if not content:
                print(f"ERRO Falha ao ler arquivo: {file_path}")
                return events
            
            # Obter nome do arquivo original
            log_file = os.path.basename(original_file_path)
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Verificar se é um evento de LogMinigame
                if '[LogMinigame]' not in line:
                    continue
                
                # Extrair timestamp
                timestamp_match = self.timestamp_pattern.match(line)
                if not timestamp_match:
                    continue
                
                timestamp = self.parse_timestamp(timestamp_match.group(0))
                if not timestamp:
                    continue
                
                # Extrair tipo de minigame e dados do jogador
                minigame_match = self.minigame_pattern.search(line)
                if not minigame_match:
                    continue
                
                # Extrair coordenadas (não obrigatório - pode ser None)
                location_match = self.location_pattern.search(line)
                location_x = None
                location_y = None
                location_z = None
                
                if location_match:
                    try:
                        location_x = float(location_match.group(1))
                        location_y = float(location_match.group(2))
                        location_z = float(location_match.group(3))
                    except (ValueError, IndexError) as e:
                        print(f"AVISO: Erro ao extrair coordenadas na linha {line_num}: {e}")
                        location_x = None
                        location_y = None
                        location_z = None
                
                try:
                    minigame_type = minigame_match.group(1).strip()
                    player_name = minigame_match.group(2).strip()
                    player_id = int(minigame_match.group(3))
                    steam_id = minigame_match.group(4)
                    
                    # Extrair Success (Yes/No)
                    success = None
                    success_match = self.success_pattern.search(line)
                    if success_match:
                        success_value = success_match.group(1).strip().upper()
                        # Aceitar Yes, No, True, False, 1, 0
                        if success_value in ('YES', 'TRUE', '1'):
                            success = True
                        elif success_value in ('NO', 'FALSE', '0'):
                            success = False
                        else:
                            # Tentar converter como boolean
                            success = bool(success_value)
                    else:
                        # Se não encontrar "Success:", tentar inferir de outras pistas
                        # Por exemplo, se tem "Failed attempts: 0" e não tem "Success: No", pode ser sucesso
                        if 'Failed attempts: 0' in line and 'Success:' not in line:
                            # Não podemos inferir sem certeza, deixar como None
                            pass
                    
                    # Extrair Elapsed time
                    elapsed_time = None
                    elapsed_match = self.elapsed_time_pattern.search(line)
                    if elapsed_match:
                        try:
                            elapsed_time = float(elapsed_match.group(1))
                        except ValueError:
                            pass
                    
                    # Extrair Failed attempts
                    failed_attempts = None
                    failed_match = self.failed_attempts_pattern.search(line)
                    if failed_match:
                        try:
                            failed_attempts = int(failed_match.group(1))
                        except ValueError:
                            pass
                    
                    # Extrair Target object e ID
                    target_object = None
                    target_object_id = None
                    target_match = self.target_object_pattern.search(line)
                    if target_match:
                        target_object = target_match.group(1).strip()
                        target_id_str = target_match.group(2).strip()
                        # Salvar como string (pode ser "N/A" ou número)
                        if target_id_str.upper() == 'N/A':
                            target_object_id = 'N/A'
                        else:
                            # Tentar converter para inteiro, mas salvar como string para consistência
                            try:
                                target_object_id = str(int(target_id_str))
                            except ValueError:
                                target_object_id = target_id_str
                    
                    # Extrair Lock type
                    lock_type = None
                    lock_match = self.lock_type_pattern.search(line)
                    if lock_match:
                        lock_type = lock_match.group(1).strip()
                    
                    # Extrair informações do proprietário (se houver)
                    owner_id = None
                    owner_steam_id = None
                    owner_name = None
                    is_property_invasion = False
                    
                    # Tentar primeiro padrão
                    owner_match = self.owner_pattern.search(line)
                    if not owner_match:
                        # Tentar padrão alternativo
                        owner_match = self.owner_pattern_alt.search(line)
                    
                    if owner_match:
                        try:
                            owner_id = int(owner_match.group(1))
                            owner_steam_id = owner_match.group(2)
                            owner_name = owner_match.group(3).strip()
                            
                            # Verificar se é invasão de propriedade (owner != lockpicker)
                            if owner_steam_id != steam_id:
                                is_property_invasion = True
                        except (ValueError, IndexError) as e:
                            # Se falhar ao extrair, logar mas continuar
                            print(f"AVISO: Erro ao extrair dados do proprietário: {e}")
                            owner_id = None
                            owner_steam_id = None
                            owner_name = None
                    
                    event = {
                        'log_line': line,
                        'timestamp': timestamp,
                        'minigame_type': minigame_type,
                        'steam_id': steam_id,
                        'player_id': player_id,
                        'player_name': player_name,
                        'success': success,
                        'elapsed_time': elapsed_time,
                        'failed_attempts': failed_attempts,
                        'target_object': target_object,
                        'target_object_id': target_object_id,
                        'lock_type': lock_type,
                        'owner_id': owner_id,
                        'owner_steam_id': owner_steam_id,
                        'owner_name': owner_name,
                        'is_property_invasion': is_property_invasion,
                        'location_x': location_x,
                        'location_y': location_y,
                        'location_z': location_z,
                        'log_file': log_file,
                        'discord_sent': False  # Inicialmente não enviado
                    }
                    
                    events.append(event)
                    
                except (ValueError, IndexError) as e:
                    print(f"ERRO ao processar linha {line_num}: {e}")
                    continue
            
            # Estatísticas detalhadas
            lockpicking_count = sum(1 for e in events if e.get('minigame_type') == 'LockpickingMinigame_C')
            success_count = sum(1 for e in events if e.get('success') is True)
            fail_count = sum(1 for e in events if e.get('success') is False)
            with_owner_count = sum(1 for e in events if e.get('owner_id') is not None)
            
            print(f"OK Extraídos {len(events)} eventos de minigame do arquivo {log_file}")
            if lockpicking_count > 0:
                print(f"   └─ LockpickingMinigame_C: {lockpicking_count} eventos")
                print(f"      ├─ Sucessos: {success_count}")
                print(f"      ├─ Falhas: {fail_count}")
                print(f"      └─ Com proprietário: {with_owner_count}")
            
            return events
            
        except Exception as e:
            print(f"ERRO ao processar arquivo de minigame: {e}")
            import traceback
            traceback.print_exc()
            return events
