"""
Processador de eventos de destruição de veículos
Monitora vehicle_destruction_*.log e envia notificações para Discord
"""

import os
import json
import re
import threading
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, List
from core.database.connector import DatabaseConnector

logger = logging.getLogger(__name__)

class VehicleDestructionProcessor:
    """Processador de eventos de destruição de veículos"""
    
    def __init__(self, webhooks_path: str = "data/webhooks.json", db_manager=None):
        self.webhooks_path = webhooks_path
        self.db_manager = db_manager
        self.images_path = "data/imagens/vehicle"
        self.mapping_file = os.path.join(self.images_path, "mapping.json")
        
        # Thread-safety
        self.mapping_lock = threading.Lock()
        
        # Carregar mapping no init
        self.vehicle_image_mapping = self._load_vehicle_mapping()
        
        # Regex para parsear linhas de destruição de veículos
        self.destruction_pattern = re.compile(
            r'(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}): \[(\w+)\] (.+?)\. VehicleId: (\d+)\. Owner: (?:(\d+) \((\d+), (.+?)\)|N/A)\. Location: X=([-\d.]+) Y=([-\d.]+) Z=([-\d.]+)'
        )
        
        # Categorização de eventos
        self.event_categories = {
            'VehicleInactiveTimerReached': {
                'emoji': '🟡',
                'color': 0xf39c12,  # Amarelo
                'name': 'Vehicle Inactive'
            },
            'Sold': {
                'emoji': '💰',
                'color': 0x2ecc71,  # Verde
                'name': 'Vehicle Sold'
            },
            'ForbiddenZoneTimerExpired': {
                'emoji': '🟠',
                'color': 0xe67e22,  # Laranja
                'name': 'Vehicle Removed (Forbidden Zone)'
            },
            'Disappeared': {
                'emoji': '🔴',
                'color': 0xe74c3c,  # Vermelho
                'name': 'Vehicle Disappeared'
            },
            'Destroyed': {
                'emoji': '⚫',
                'color': 0x2c3e50,  # Preto
                'name': 'Vehicle Destroyed'
            }
        }
        
        # Mapeamento de status para banco de dados
        self.status_mapping = {
            'VehicleInactiveTimerReached': 1,
            'Sold': 0,
            'ForbiddenZoneTimerExpired': 2,
            'Disappeared': 2,
            'Destroyed': 3
        }
    
    def _normalize_vehicle_name(self, vehicle_name: str) -> str:
        """Normalizar nome do veículo (padrão kill_log)"""
        if not vehicle_name:
            return vehicle_name
        
        # Remover prefixos comuns
        normalized = vehicle_name
        for prefix in ['BPC_', 'BP_', 'bpc_', 'bp_']:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        
        # Remover sufixos (_ES, _C, IDs numéricos)
        normalized = re.sub(r'_ES(_\d+)?$', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'_C(_\d+)?$', '', normalized)
        normalized = re.sub(r'_\d+$', '', normalized)  # IDs numéricos
        
        # Normalizar formato (lowercase, substituir espaços/hífens)
        normalized = normalized.lower().strip()
        normalized = normalized.replace(' ', '_').replace('-', '_')
        
        return normalized
    
    def _load_vehicle_mapping(self) -> Dict[str, str]:
        """Carregar mapeamento de veículos do arquivo JSON"""
        try:
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                    logger.info(f"Mapeamento de veículos carregado: {len(mapping)} veículos")
                    return mapping
            else:
                # Criar arquivo vazio se não existir
                logger.info("Arquivo mapping.json não encontrado, criando novo")
                empty_mapping = {}
                self._save_vehicle_mapping(empty_mapping)
                return empty_mapping
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear arquivo de mapeamento: {e}")
            return {}
        except Exception as e:
            logger.error(f"Erro ao carregar mapeamento de veículos: {e}")
            return {}
    
    def _save_vehicle_mapping(self, mapping: Dict[str, str]) -> bool:
        """Salvar mapeamento ordenado alfabeticamente (thread-safe)"""
        try:
            # Ordenar alfabeticamente
            sorted_mapping = dict(sorted(mapping.items()))
            
            # Garantir que o diretório existe
            os.makedirs(os.path.dirname(self.mapping_file), exist_ok=True)
            
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(sorted_mapping, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar mapeamento: {e}")
            return False
    
    def _add_vehicle_to_mapping(self, normalized_name: str) -> None:
        """Adicionar novo veículo ao mapeamento (thread-safe)"""
        if not normalized_name:
            return
        
        with self.mapping_lock:
            if normalized_name not in self.vehicle_image_mapping:
                self.vehicle_image_mapping[normalized_name] = ""
                self._save_vehicle_mapping(self.vehicle_image_mapping)
                logger.info(f"Novo veículo descoberto: {normalized_name}")
    
    def _get_vehicle_image_mapping(self, vehicle_name: str) -> Optional[str]:
        """Mapear nome do veículo para arquivo de imagem"""
        if not vehicle_name:
            return None
        
        # Normalizar nome
        normalized_name = self._normalize_vehicle_name(vehicle_name)
        
        # Buscar no mapping
        image_filename = self.vehicle_image_mapping.get(normalized_name)
        
        # Se não existe, adicionar (auto-descoberta)
        if image_filename is None:
            self._add_vehicle_to_mapping(normalized_name)
            return None
        
        # Se existe mas está vazio, retornar None
        if not image_filename or image_filename.strip() == "":
            return None
        
        # Verificar se arquivo existe
        image_path = os.path.join(self.images_path, image_filename)
        if os.path.exists(image_path):
            return image_filename
        
        logger.warning(f"Imagem mapeada não encontrada: {image_filename}")
        return None
    
    def _get_vehicle_webhook_url(self) -> Optional[str]:
        """Obtém URL do webhook para veículos"""
        try:
            if not os.path.exists(self.webhooks_path):
                logger.error(f"Arquivo webhooks.json não encontrado: {self.webhooks_path}")
                return None

            from core.webhooks.manager import WebhooksManager

            mgr = WebhooksManager(str(self.webhooks_path))
            webhooks = mgr.load()
            if not isinstance(webhooks, dict):
                return None
            return webhooks.get('vehicle-log')
        except Exception as e:
            logger.error(f"Erro ao ler webhooks.json: {e}")
            return None
    
    def _categorize_event(self, event_type: str) -> Dict:
        """Categoriza o tipo de evento"""
        return self.event_categories.get(event_type, {
            'emoji': '❓',
            'color': 0x95a5a6,  # Cinza
            'name': 'Unknown Event'
        })
    
    def _parse_destruction_line(self, line: str) -> Optional[Dict]:
        """Parse uma linha de destruição de veículo"""
        match = self.destruction_pattern.match(line.strip())
        if not match:
            return None
            
        groups = match.groups()
        timestamp_str, event_type, vehicle_name, vehicle_id = groups[0], groups[1], groups[2], groups[3]
        
        # Verificar se Owner é N/A ou tem dados
        if groups[4] is None:  # Owner: N/A
            owner_steam_id = None
            owner_id = None
            owner_name = "N/A"
        else:  # Owner: steam_id (id, name)
            owner_steam_id = groups[4]
            owner_id = int(groups[5])
            owner_name = groups[6]
        
        # Converter timestamp SCUM para datetime
        try:
            # Formato: 2025.10.20-18.51.10
            timestamp_parts = timestamp_str.split('-')
            date_part = timestamp_parts[0].replace('.', '-')
            time_part = timestamp_parts[1].replace('.', ':')
            iso_string = f"{date_part}T{time_part}"
            timestamp = datetime.fromisoformat(iso_string)
        except Exception:
            timestamp = datetime.now()
        
        # Categorizar evento
        category_info = self._categorize_event(event_type)
        
        # Gerar ID único do evento (timestamp + vehicle_id)
        event_id = f"{timestamp_str}:{vehicle_id}"
        
        return {
            'timestamp': timestamp,
            'event_type': event_type,
            'vehicle_name': vehicle_name,
            'vehicle_id': int(vehicle_id),
            'owner_steam_id': owner_steam_id,
            'owner_id': owner_id,
            'owner_name': owner_name,
            'location': {
                'x': float(groups[-3]),
                'y': float(groups[-2]),
                'z': float(groups[-1])
            },
            'category': category_info,
            'event_id': event_id,
            'status': self.status_mapping.get(event_type, 0)
        }
    
    def _get_scum_map_link(self, x: float, y: float, zoom: int = 4) -> str:
        """Gerar link do SCUM Maps"""
        return f"https://scum-map.com/en/shared/scum/island/{x:.4f},{y:.4f},{zoom}"
    
    def _format_discord_message(self, parsed_data: Dict) -> Dict:
        """Formata mensagem para Discord"""
        category = parsed_data['category']
        
        # Gerar link do SCUM Maps
        location_x = parsed_data['location']['x']
        location_y = parsed_data['location']['y']
        location_z = parsed_data['location']['z']
        map_link = self._get_scum_map_link(location_x, location_y)
        
        # Construir footer com IDs
        footer_parts = [f"Vehicle ID: {parsed_data['vehicle_id']}"]
        if parsed_data.get('owner_steam_id'):
            footer_parts.append(f"Steam ID: {parsed_data['owner_steam_id']}")
        footer_text = " • ".join(footer_parts)
        
        embed = {
            "title": f"{category['emoji']} {category['name']}",
            "color": category['color'],
            "fields": [
                {
                    "name": "Vehicle",
                    "value": parsed_data['vehicle_name'],
                    "inline": True
                },
                {
                    "name": "Owner",
                    "value": parsed_data['owner_name'],
                    "inline": True
                },
                {
                    "name": "Location",
                    "value": f"[View on Map]({map_link})",
                    "inline": True
                },
                {
                    "name": "🌐 Global Rankings",
                    "value": "[View all rankings](https://scumsm.com/rankings)",
                    "inline": False
                }
            ],
            "footer": {
                "text": footer_text
            }
        }
        
        # Adicionar miniatura do veículo se disponível
        vehicle_image = self._get_vehicle_image_mapping(parsed_data['vehicle_name'])
        if vehicle_image:
            embed["thumbnail"] = {
                "url": f"attachment://{vehicle_image}"
            }
        
        return {"embeds": [embed]}
    
    def _event_exists_in_database(self, event_id: str, parsed_data: Dict) -> bool:
        """Verifica se o evento já existe no banco de dados"""
        try:
            if not self.db_manager:
                return False

            with DatabaseConnector.get_connection(self.db_manager.db_path, write_mode=False) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM vehicle_destruction_events WHERE vehicle_id = ? AND event_type = ? AND timestamp = ?",
                    (
                        parsed_data['vehicle_id'],
                        parsed_data['event_type'],
                        parsed_data['timestamp'].isoformat(),
                    ),
                )
                row = cursor.fetchone()
                return bool(row and row[0] > 0)
            
        except Exception as e:
            logger.error(f"Erro ao verificar evento no banco: {e}")
            return False
    
    def _save_to_database(self, parsed_data: Dict, discord_sent: int = 1):
        """Salvar evento de destruição no banco de dados"""
        try:
            if not self.db_manager:
                return

            with DatabaseConnector.get_connection(self.db_manager.db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO vehicle_destruction_events (vehicle_id, vehicle_name, owner_steam_id, owner_id, owner_name, event_type, location_x, location_y, location_z, timestamp, discord_sent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        parsed_data['vehicle_id'],
                        parsed_data['vehicle_name'],
                        parsed_data['owner_steam_id'] or "N/A",
                        parsed_data['owner_id'] or 0,
                        parsed_data['owner_name'],
                        parsed_data['event_type'],
                        parsed_data['location']['x'],
                        parsed_data['location']['y'],
                        parsed_data['location']['z'],
                        parsed_data['timestamp'].isoformat(),
                        int(discord_sent or 0),
                    ),
                )
                cursor.execute(
                    "UPDATE vehicle_current_ownership SET status = ? WHERE vehicle_entity_id = ?",
                    (parsed_data['status'], parsed_data['vehicle_id']),
                )

            logger.info(f"Evento salvo no banco: {parsed_data['event_type']} - {parsed_data['vehicle_name']}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar no banco de dados: {e}")
            import traceback
            traceback.print_exc()
    
    def process_vehicle_destruction_log(self, log_file_path: str) -> bool:
        """Processa arquivo de log de destruição de veículos"""
        try:
            # Verificar se arquivo existe
            if not os.path.exists(log_file_path):
                logger.warning(f"Arquivo de log não encontrado: {log_file_path}")
                return False
            
            # Obter URL do webhook
            webhook_url = self._get_vehicle_webhook_url()
            if not webhook_url or not str(webhook_url).strip():
                logger.warning("Webhook vehicle-log não configurado")
                webhook_url = None
            
            # Ler arquivo (SCUM usa UTF-16LE)
            try:
                with open(log_file_path, 'r', encoding='utf-16le') as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Erro ao ler arquivo: {e}")
                    return False
            
            # Dividir em linhas
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            if not lines:
                logger.info("Nenhuma linha encontrada no arquivo")
                return True
            
            processed_events = 0
            
            logger.info(f"Processando {len(lines)} linhas do vehicle destruction log")
            
            # Processar cada linha
            for line in lines:
                if not line:
                    continue
                    
                # Parse da linha
                parsed_data = self._parse_destruction_line(line)
                if not parsed_data:
                    logger.debug(f"Linha não parseada: {line}")
                    continue
                
                # Ignorar eventos com Owner N/A
                if parsed_data.get('owner_name') == 'N/A':
                    logger.debug(f"Evento ignorado (Owner N/A): {parsed_data['vehicle_name']} (ID: {parsed_data['vehicle_id']})")
                    continue
                
                event_id = parsed_data['event_id']
                
                # Verificar se o evento já existe no banco de dados
                if self._event_exists_in_database(event_id, parsed_data):
                    logger.info(f"Evento {event_id} já existe no banco, pulando.")
                    continue

                # Formatar mensagem Discord
                discord_message = self._format_discord_message(parsed_data)
                
                # Obter imagem do veículo
                vehicle_image = self._get_vehicle_image_mapping(parsed_data['vehicle_name'])
                
                # Enviar para Discord (opcional) + sempre salvar no banco
                discord_sent = 0
                try:
                    if webhook_url:
                        if vehicle_image:
                            # Enviar com miniatura
                            image_path = os.path.join(self.images_path, vehicle_image)
                            if os.path.exists(image_path):
                                discord_sent = 1 if self._send_with_image(discord_message, image_path, vehicle_image, webhook_url) else 0
                            else:
                                logger.warning(f"Imagem não encontrada: {image_path}")
                                discord_sent = 1 if self._send_without_image(discord_message, webhook_url) else 0
                        else:
                            # Enviar sem miniatura
                            discord_sent = 1 if self._send_without_image(discord_message, webhook_url) else 0
                except Exception as e:
                    logger.error(f"Erro ao enviar webhook: {e}")

                if discord_sent:
                    logger.info(f"Evento de destruição enviado: {parsed_data['event_type']} - {parsed_data['vehicle_name']}")
                    processed_events += 1

                # Salvar no banco de dados (mesmo se não enviou)
                self._save_to_database(parsed_data, discord_sent=discord_sent)
            
            logger.info(f"Vehicle destruction log processado: {processed_events} eventos enviados")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar vehicle destruction log: {e}")
            return False
    
    def _send_with_image(self, discord_message: Dict, image_path: str, image_filename: str, webhook_url: str) -> bool:
        """Enviar notificação com miniatura"""
        try:
            # Preparar arquivo
            with open(image_path, 'rb') as f:
                files = {
                    'file': (image_filename, f, 'image/png')
                }
                
                # Enviar webhook
                response = requests.post(
                    webhook_url,
                    data={'payload_json': json.dumps(discord_message)},
                    files=files,
                    timeout=10
                )
                
                if response.status_code in [200, 204]:
                    logger.info(f"Evento de destruição enviado com miniatura: {image_filename}")
                    return True
                else:
                    logger.error(f"Falha ao enviar com miniatura. Status: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao enviar com miniatura: {e}")
            return False
    
    def _send_without_image(self, discord_message: Dict, webhook_url: str) -> bool:
        """Enviar notificação sem miniatura"""
        try:
            response = requests.post(
                webhook_url,
                json=discord_message,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info("Evento de destruição enviado sem miniatura")
                return True
            else:
                logger.error(f"Falha ao enviar sem miniatura. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar sem miniatura: {e}")
            return False
