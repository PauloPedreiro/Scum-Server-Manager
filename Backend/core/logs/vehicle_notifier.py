"""
Sistema de Notificações Discord para Veículos
Envia notificações quando veículos são trancados ou transferidos
"""

import os
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
from .vehicle_processor import VehicleProcessor
from utils.logger import StructuredLogger

class VehicleNotifier:
    def __init__(
        self,
        webhook_config: Dict[str, str] = None,
        vehicle_processor: VehicleProcessor = None,
        config: Dict[str, Any] = None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.webhook_config = webhook_config or {}
        self.vehicle_processor = vehicle_processor
        self.images_path = "data/imagens/vehicle"
        self.logger = logger
        
        # Configurações padrão
        self.webhook_url = self.webhook_config.get('vehicle_registration')
        
        # Carregar configuração de exibição de localização
        vehicle_config = (config or {}).get('vehicle_registration', {})
        self.show_location = vehicle_config.get('show_location', True)  # Padrão: True (retrocompatível)
        
        if not self.webhook_url:
            print("AVISO: Webhook de veículos não configurado")
        try:
            if self.logger:
                self.logger.info(
                    "[VEHICLE_REGISTRATION] Webhook configured",
                    {"configured": bool(self.webhook_url)},
                )
        except Exception:
            pass
    
    def _get_scum_map_link(self, x: float, y: float, zoom: int = 4) -> str:
        """Gerar link do SCUM Maps"""
        return f"https://scum-map.com/en/shared/scum/island/{x:.4f},{y:.4f},{zoom}"
    
    def send_vehicle_notification(self, vehicle_data: Dict[str, Any]) -> bool:
        """Enviar notificação Discord para evento de veículo"""
        try:
            if not self.webhook_url:
                print("AVISO: Webhook de veículos não configurado")
                try:
                    if self.logger:
                        self.logger.warn(
                            "[VEHICLE_REGISTRATION] Webhook not configured",
                            {"configured": False},
                        )
                except Exception:
                    pass
                return False
            
            # Determinar tipo de evento e emoji
            if vehicle_data['ownership_type'] == 'claimed':
                event_emoji = "🚗"
                event_title = "Vehicle Registered"
                color = 0xff6b35  # Laranja
            elif vehicle_data['ownership_type'] == 'changed':
                event_emoji = "🔄"
                event_title = "Ownership Transferred"
                color = 0x3498db  # Azul
            else:
                event_emoji = "🚗"
                event_title = "Vehicle Event"
                color = 0x95a5a6  # Cinza
            
            # Obter dados do veículo
            vehicle_class = vehicle_data.get('vehicle_class', 'Unknown')
            vehicle_name = self.vehicle_processor.get_vehicle_display_name(vehicle_class) if self.vehicle_processor else vehicle_class
            vehicle_image = self.vehicle_processor.get_vehicle_image_mapping(vehicle_class) if self.vehicle_processor else 'dirtbike_es.png'
            
            # Criar campos base do embed
            fields = [
                {
                    "name": "Vehicle",
                    "value": f"{vehicle_name}",
                    "inline": True
                },
                {
                    "name": "Player",
                    "value": f"{vehicle_data['player_name']}",
                    "inline": True
                }
            ]
            
            # Adicionar campo de localização apenas se show_location estiver habilitado
            if self.show_location:
                location_x = vehicle_data.get('location_x', 0)
                location_y = vehicle_data.get('location_y', 0)
                map_link = self._get_scum_map_link(location_x, location_y)
                fields.append({
                    "name": "Location",
                    "value": f"[View on Map]({map_link})",
                    "inline": True
                })
            
            # Criar embed
            embed = {
                "title": f"{event_emoji} {event_title}",
                "color": color,
                "fields": fields,
                "footer": {
                    "text": f"Container ID: {vehicle_data['entity_id']} • Vehicle ID: {vehicle_data.get('vehicle_entity_id', 'N/A')} • Steam ID: {vehicle_data['steam_id']}"
                }
            }
            
            # Adicionar campo específico para transferência
            if vehicle_data['ownership_type'] == 'changed':
                embed["fields"].append({
                    "name": "Transfer",
                    "value": f"From: {vehicle_data.get('previous_owner_name', 'Unknown')}\nTo: {vehicle_data['player_name']}",
                    "inline": False
                })
            
            # Preparar payload
            payload = {
                "embeds": [embed]
            }
            
            # Enviar com miniatura se disponível
            image_path = os.path.join(self.images_path, vehicle_image)
            if os.path.exists(image_path):
                return self._send_with_image(payload, image_path, vehicle_image)
            else:
                return self._send_without_image(payload)
            
        except Exception as e:
            print(f"ERRO: Erro ao enviar notificação de veículo: {e}")
            try:
                if self.logger:
                    self.logger.error(
                        f"[VEHICLE_REGISTRATION] Unexpected send error: {e}",
                        {
                            "entity_id": int(vehicle_data.get("entity_id") or 0),
                            "ownership_type": str(vehicle_data.get("ownership_type") or ""),
                            "steam_id": str(vehicle_data.get("steam_id") or ""),
                        },
                    )
            except Exception:
                pass
            return False
    
    def _send_with_image(self, payload: Dict[str, Any], image_path: str, image_filename: str) -> bool:
        """Enviar notificação com miniatura"""
        try:
            # Atualizar embed com miniatura
            if payload.get('embeds'):
                payload['embeds'][0]['thumbnail'] = {
                    "url": f"attachment://{image_filename}"
                }
            
            # Preparar arquivo
            files = {
                'file': (image_filename, open(image_path, 'rb'), 'image/png')
            }
            
            # Enviar webhook
            response = requests.post(
                self.webhook_url,
                data={'payload_json': json.dumps(payload)},
                files=files,
                timeout=10
            )
            
            files['file'][1].close()  # Fechar arquivo
            
            if response.status_code in [200, 204]:
                print(f"OK: Notificação de veículo enviada com miniatura: {image_filename}")
                try:
                    if self.logger:
                        self.logger.info(
                            "[VEHICLE_REGISTRATION] Discord webhook sent (with image)",
                            {"status_code": int(response.status_code)},
                        )
                except Exception:
                    pass
                return True
            else:
                print(f"ERRO: Falha ao enviar notificação com miniatura. Status: {response.status_code}")
                try:
                    if self.logger:
                        self.logger.warn(
                            "[VEHICLE_REGISTRATION] Discord webhook failed (with image)",
                            {"status_code": int(response.status_code), "body": str(response.text or "")[:500]},
                        )
                except Exception:
                    pass
                return False
                
        except Exception as e:
            print(f"ERRO: Erro ao enviar notificação com miniatura: {e}")
            try:
                if self.logger:
                    self.logger.error(
                        f"[VEHICLE_REGISTRATION] Discord webhook exception (with image): {e}",
                        {"image": str(image_filename)},
                    )
            except Exception:
                pass
            return False
    
    def _send_without_image(self, payload: Dict[str, Any]) -> bool:
        """Enviar notificação sem miniatura"""
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                print(f"OK: Notificação de veículo enviada sem miniatura")
                try:
                    if self.logger:
                        self.logger.info(
                            "[VEHICLE_REGISTRATION] Discord webhook sent",
                            {"status_code": int(response.status_code)},
                        )
                except Exception:
                    pass
                return True
            else:
                print(f"ERRO: Falha ao enviar notificação sem miniatura. Status: {response.status_code}")
                try:
                    if self.logger:
                        self.logger.warn(
                            "[VEHICLE_REGISTRATION] Discord webhook failed",
                            {"status_code": int(response.status_code), "body": str(response.text or "")[:500]},
                        )
                except Exception:
                    pass
                return False
                
        except Exception as e:
            print(f"ERRO: Erro ao enviar notificação sem miniatura: {e}")
            try:
                if self.logger:
                    self.logger.error(
                        f"[VEHICLE_REGISTRATION] Discord webhook exception: {e}",
                        {},
                    )
            except Exception:
                pass
            return False
    
    def send_test_notification(self) -> bool:
        """Enviar notificação de teste"""
        try:
            if not self.webhook_url:
                print("AVISO: Webhook de veículos não configurado")
                return False
            
            # Dados de teste
            test_data = {
                'ownership_type': 'claimed',
                'entity_id': 12345678,
                'steam_id': '76561198000000000',
                'player_id': 999,
                'player_name': 'Teste Player',
                'location_x': 100000.0,
                'location_y': 200000.0,
                'location_z': 30000.0,
                'vehicle_class': 'wolfswagen',
                'timestamp': datetime.now()
            }
            
            return self.send_vehicle_notification(test_data)
            
        except Exception as e:
            print(f"ERRO: Erro ao enviar notificação de teste: {e}")
            return False
    
    def get_notifier_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do notificador"""
        return {
            'webhook_configured': bool(self.webhook_url),
            'images_path': self.images_path,
            'images_path_exists': os.path.exists(self.images_path),
            'available_images': len(os.listdir(self.images_path)) if os.path.exists(self.images_path) else 0
        }
