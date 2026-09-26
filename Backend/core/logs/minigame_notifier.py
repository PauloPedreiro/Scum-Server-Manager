"""
Minigame Notifier - Envia notificações de eventos de minigame para Discord
Especializado em eventos de LockpickingMinigame_C (raids)
"""

import os
import json
import re
import requests
from datetime import datetime
from typing import Dict, Any, Optional

class MinigameNotifier:
    """Notificador de eventos de minigame para Discord"""
    
    def __init__(self, webhooks_path: str = "data/webhooks.json"):
        self.webhooks_path = webhooks_path
        self.webhook_url = None
        self._load_webhook_url()
        
        # Configurar caminhos de imagens de raid
        self.raid_images_path = "data/imagens/Raid"
        self.raid_mapping_path = os.path.join(self.raid_images_path, 'mapping.json')
        self.raid_mapping = self._load_raid_mapping()
    
    def _load_webhook_url(self) -> Optional[str]:
        """Carregar URL do webhook de lockpicking events"""
        try:
            if os.path.exists(self.webhooks_path):
                try:
                    from core.webhooks.manager import WebhooksManager

                    mgr = WebhooksManager(self.webhooks_path)
                    webhooks = mgr.load()
                    self.webhook_url = (webhooks or {}).get('lockpicking_events') if isinstance(webhooks, dict) else None
                except Exception:
                    with open(self.webhooks_path, 'r', encoding='utf-8') as f:
                        webhooks = json.load(f)
                        self.webhook_url = (webhooks or {}).get('lockpicking_events') if isinstance(webhooks, dict) else None

                if self.webhook_url:
                    # Verificar se não está vazio
                    if str(self.webhook_url).strip():
                        print(f"OK Webhook de lockpicking events carregado")
                    else:
                        print(f"AVISO Webhook 'lockpicking_events' está vazio em webhooks.json")
                        self.webhook_url = None
                else:
                    print(f"AVISO Webhook 'lockpicking_events' não encontrado em webhooks.json")
            else:
                print(f"AVISO Arquivo webhooks.json não encontrado em {self.webhooks_path}")
                self.webhook_url = None
        except Exception as e:
            print(f"ERRO ao carregar webhook config: {e}")
            import traceback
            traceback.print_exc()
            self.webhook_url = None
        return self.webhook_url
    
    def _load_raid_mapping(self) -> Dict[str, str]:
        """Carregar mapeamento de objetos de raid do JSON"""
        try:
            if os.path.exists(self.raid_mapping_path):
                with open(self.raid_mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                    print(f"OK Mapeamento de objetos de raid carregado: {len(mapping)} objetos")
                    return mapping
            else:
                # Criar arquivo vazio se não existir
                print(f"AVISO Arquivo mapping.json não encontrado em {self.raid_images_path}, criando novo")
                empty_mapping = {}
                self._save_raid_mapping(empty_mapping)
                return empty_mapping
        except Exception as e:
            print(f"ERRO ao carregar mapeamento de objetos de raid: {e}")
            return {}
    
    def _save_raid_mapping(self, mapping: Dict[str, str]) -> bool:
        """Salvar mapeamento de objetos de raid no JSON com ordenação alfabética"""
        try:
            # Ordenar alfabeticamente por chave
            sorted_mapping = dict(sorted(mapping.items()))
            
            # Garantir que o diretório existe
            os.makedirs(os.path.dirname(self.raid_mapping_path), exist_ok=True)
            
            with open(self.raid_mapping_path, 'w', encoding='utf-8') as f:
                json.dump(sorted_mapping, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"ERRO ao salvar mapeamento de objetos de raid: {e}")
            return False
    
    def _normalize_object_name(self, object_name: str) -> str:
        """Normalizar nome do objeto removendo prefixos, sufixos e IDs"""
        if not object_name:
            return object_name
        
        # Remover sufixo "_C" e qualquer número após (ex: _C_2147299856)
        normalized = re.sub(r'_C(?:_\d+)?$', '', object_name)
        
        return normalized.strip()
    
    def _get_raid_object_image_path(self, normalized_object: str) -> Optional[str]:
        """Obter caminho da imagem do objeto de raid usando o mapeamento JSON"""
        if not normalized_object or not os.path.exists(self.raid_images_path):
            return None
        
        # Verificar se o objeto está no mapeamento
        image_filename = self.raid_mapping.get(normalized_object)
        
        # Se não está no mapeamento, adicionar com valor vazio
        if image_filename is None:
            self._add_raid_object_to_mapping(normalized_object)
            return None
        
        # Se está no mapeamento mas vazio, não tem imagem
        if not image_filename or image_filename.strip() == "":
            return None
        
        # Se tem valor no mapeamento, verificar se o arquivo existe
        image_path = os.path.join(self.raid_images_path, image_filename)
        if os.path.exists(image_path):
            return image_path
        else:
            # Arquivo não existe, logar aviso
            print(f"AVISO Imagem mapeada não encontrada: {image_filename} para objeto {normalized_object}")
            return None
    
    def _add_raid_object_to_mapping(self, normalized_object: str) -> None:
        """Adicionar novo objeto de raid ao mapeamento com valor vazio"""
        if not normalized_object:
            return
        
        # Verificar se já existe
        if normalized_object not in self.raid_mapping:
            # Adicionar com valor vazio
            self.raid_mapping[normalized_object] = ""
            self._save_raid_mapping(self.raid_mapping)
            print(f"OK Novo objeto de raid descoberto e adicionado ao mapping: {normalized_object}")
    
    def format_discord_message(self, event_data: Dict[str, Any], target: str = "global") -> Dict[str, Any]:
        """
        Formatar mensagem Discord para evento de lockpicking
        
        Args:
            event_data: Dados do evento de minigame
            
        Returns:
            Dict formatado para envio ao Discord
        """
        player_name = event_data.get('player_name', 'Desconhecido')
        success = event_data.get('success', False)
        lock_type = event_data.get('lock_type', 'Desconhecido')
        target_object = event_data.get('target_object', 'Desconhecido')
        elapsed_time = event_data.get('elapsed_time')
        failed_attempts = event_data.get('failed_attempts', 0)
        
        # Informações do proprietário
        owner_name = event_data.get('owner_name')
        is_property_invasion = event_data.get('is_property_invasion', False)
        
        # Timestamp
        timestamp_str = event_data.get('timestamp')
        if isinstance(timestamp_str, datetime):
            timestamp = timestamp_str
        elif isinstance(timestamp_str, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()
        
        # Garantir que temos proprietário (já validado no send_notification)
        owner_id = event_data.get('owner_id')
        owner_steam_id = event_data.get('owner_steam_id')
        
        # Determinar cor baseado no resultado e invasão
        if is_property_invasion:
            if success:
                color = 0xff0000  # Vermelho (invasão bem-sucedida)
                success_emoji = "✅"
            else:
                color = 0xff6600  # Laranja escuro (tentativa de invasão)
                success_emoji = "❌"
        else:
            # Se não for invasão mas tem proprietário (mesma propriedade), usar cores mais suaves
            if success:
                color = 0x00aa00  # Verde mais escuro
                success_emoji = "✅"
            else:
                color = 0xff9900  # Laranja
                success_emoji = "❌"
        
        # Título fixo para RAID
        title = "⚠️ RAID ALERT!"
        
        # Construir descrição no formato solicitado
        description_lines = []
        
        # Campos simples e diretos (sem negrito)
        description_lines.append(f"Invader: {player_name}")
        description_lines.append(f"Property of: {owner_name}")
        description_lines.append(f"Success: {success_emoji}")
        
        # Adicionar tipo de lock se houver
        if lock_type:
            description_lines.append(f"Lock: {lock_type}")
        
        # Adicionar quantidade de tentativas falhadas se disponível
        if failed_attempts is not None and failed_attempts >= 0:
            description_lines.append(f"Failed: {failed_attempts}")
        
        # Adicionar objeto alvo (sem label, apenas o nome) com linha em branco antes
        if target_object:
            # Remover sufixo _C se houver para melhor legibilidade
            clean_object = target_object.replace('_C', '').replace('_', ' ')
            description_lines.append("")  # Linha em branco antes do objeto
            description_lines.append(clean_object)
        
        # Adicionar comando de teleport na descrição (clicável/copiável)
        location_x = event_data.get('location_x')
        location_y = event_data.get('location_y')
        location_z = event_data.get('location_z')
        
        if location_x is not None and location_y is not None:
            if (target or "").strip().lower() == "owner":
                map_link = f"https://scum-map.com/en/shared/scum/island/{float(location_x):.4f},{float(location_y):.4f},4"
                description_lines.append("")
                description_lines.append(f"[View on Map]({map_link})")
            else:
                # Formato do comando de teleport (em bloco de código para facilitar cópia)
                # Usar 4 casas decimais e sempre usar 0 para Z se não houver
                z_value = location_z if location_z is not None else 0
                teleport_command = f"#Teleport {location_x:.4f} {location_y:.4f} {z_value:.0f}"
                
                # Adicionar o comando de teleport no final da descrição (em bloco de código)
                # O bloco de código no Discord permite clicar e copiar facilmente
                description_lines.append("")  # Linha em branco
                description_lines.append(f"```{teleport_command}```")
        
        # Criar descrição final
        description = "\n".join(description_lines)
        
        # Normalizar nome do objeto para buscar imagem
        normalized_object = self._normalize_object_name(target_object) if target_object else None
        
        # Verificar se existe imagem do objeto
        object_image_path = self._get_raid_object_image_path(normalized_object) if normalized_object else None
        
        # Criar embed
        embed_data = {
            'title': title,
            'description': description,
            'color': color,
            'timestamp': timestamp.isoformat(),
            'footer': {
                'text': 'SCUM Server Manager'
            }
        }
        
        # Adicionar thumbnail do objeto se disponível
        if object_image_path:
            object_image_filename = os.path.basename(object_image_path)
            embed_data['thumbnail'] = {
                "url": f"attachment://{object_image_filename}"
            }
            return {
                'embeds': [embed_data],
                '_use_image': True,
                '_image_path': object_image_path,
                '_image_filename': object_image_filename
            }
        
        return {
            'embeds': [embed_data],
            '_use_image': False
        }
    
    def send_notification(self, event_data: Dict[str, Any]) -> bool:
        """
        Enviar notificação de evento de lockpicking para Discord
        
        IMPORTANTE: Só envia se houver proprietário identificado (owner_id, owner_steam_id, owner_name)
        
        Args:
            event_data: Dados do evento de minigame
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            # Só enviar para LockpickingMinigame_C
            minigame_type = event_data.get('minigame_type', '')
            if 'LockpickingMinigame_C' not in minigame_type:
                return False
            
            # Verificar se existe proprietário identificado (owner_id, owner_steam_id, owner_name)
            owner_id = event_data.get('owner_id')
            owner_steam_id = event_data.get('owner_steam_id')
            owner_name = event_data.get('owner_name')
            
            # Só enviar se houver proprietário completo
            if not owner_id or not owner_steam_id or not owner_name:
                return False  # Não enviar se não houver proprietário
            
            # Verificar se webhook está configurado
            if not self.webhook_url:
                print("AVISO Webhook de lockpicking events não configurado")
                return False

            return self.send_notification_to_webhook(event_data, self.webhook_url, target="global")

        except Exception as e:
            print(f"ERRO ao enviar notificação de lockpicking: {e}")
            import traceback
            traceback.print_exc()
            return False

    def send_notification_to_webhook(self, event_data: Dict[str, Any], webhook_url: str, target: str = "owner") -> bool:
        try:
            # Só enviar para LockpickingMinigame_C
            minigame_type = event_data.get('minigame_type', '')
            if 'LockpickingMinigame_C' not in minigame_type:
                return False

            owner_id = event_data.get('owner_id')
            owner_steam_id = event_data.get('owner_steam_id')
            owner_name = event_data.get('owner_name')

            if not owner_id or not owner_steam_id or not owner_name:
                return False

            if not webhook_url or not str(webhook_url).strip():
                return False
            
            # Formatar mensagem
            message = self.format_discord_message(event_data, target=target)
            
            # Verificar se tem imagem para enviar
            use_image = message.get('_use_image', False)
            if use_image:
                image_path = message.get('_image_path')
                image_filename = message.get('_image_filename')
                
                # Remover campos internos antes de enviar
                message_to_send = {k: v for k, v in message.items() if not k.startswith('_')}
                
                # Enviar com imagem
                return self._send_with_image(webhook_url, message_to_send, image_path, image_filename)
            else:
                # Remover campos internos antes de enviar
                message_to_send = {k: v for k, v in message.items() if not k.startswith('_')}
                
                # Enviar sem imagem
                response = requests.post(
                    webhook_url,
                    json=message_to_send,
                    timeout=10
                )
                
                if response.status_code in [200, 204]:
                    print(f"OK Notificação de lockpicking enviada: {event_data.get('player_name')}")
                    return True
                else:
                    print(f"ERRO Falha ao enviar notificação: {response.status_code}")
                    return False
                
        except Exception as e:
            print(f"ERRO ao enviar notificação de lockpicking: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _send_with_image(self, webhook_url: str, message: Dict, image_path: str, image_filename: str) -> bool:
        """Enviar notificação com miniatura (GIF, PNG ou WEBP)"""
        try:
            # Determinar tipo MIME baseado na extensão
            ext = os.path.splitext(image_filename)[1].lower()
            if ext == '.gif':
                mime_type = 'image/gif'
            elif ext == '.webp':
                mime_type = 'image/webp'
            else:
                mime_type = 'image/png'
            
            with open(image_path, 'rb') as f:
                files = {
                    'file': (image_filename, f, mime_type)
                }
                
                response = requests.post(
                    webhook_url,
                    data={'payload_json': json.dumps(message)},
                    files=files,
                    timeout=10
                )
            
            if response.status_code in [200, 204]:
                print(f"OK Notificação de lockpicking enviada com miniatura: {image_filename}")
                return True
            else:
                print(f"ERRO Falha ao enviar notificação com imagem. Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"ERRO ao enviar notificação com imagem: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_batch_notifications(self, events: list[Dict[str, Any]]) -> int:
        """
        Enviar múltiplas notificações
        
        Args:
            events: Lista de eventos de minigame
            
        Returns:
            Número de notificações enviadas com sucesso
        """
        success_count = 0
        
        for event in events:
            if self.send_notification(event):
                success_count += 1
        
        return success_count

