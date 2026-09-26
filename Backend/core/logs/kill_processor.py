"""
Kill Log Processor - Processa logs de mortes/kills do SCUM
Monitora kill_*.log e armazena eventos de morte no banco de dados
"""

import os
import json
import re
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from core.database.connector import DatabaseConnector
import logging
import requests

logger = logging.getLogger(__name__)

class KillProcessor:
    """Processador de logs de mortes/kills do SCUM"""
    
    def __init__(self, db_manager=None, webhooks_path: str = "data/webhooks.json", config: Dict = None, config_path: str = "data/config.json"):
        self.db_manager = db_manager
        self.webhooks_path = webhooks_path
        self.config = config or {}
        self.config_path = config_path
        self.noob_gif_path = "data/imagens/SCUM GIF/Noob.gif"
        self.weapons_images_path = "data/imagens/Weapons"
        self.weapons_mapping_path = os.path.join(self.weapons_images_path, "mapping.json")
        
        # Lock para thread-safety ao escrever no JSON
        self.mapping_lock = threading.Lock()
        
        # Carregar mapeamento de armas
        self.weapons_mapping = self._load_weapons_mapping()
        
        # Padrões de regex para parsing
        # Padrão para morte: "2025.11.01-20.37.54: Died: PLAYER (STEAM_ID), Killer: KILLER (NPC/JOGADOR) Weapon: ARMA [TYPE] S:[...]"
        self.kill_pattern = re.compile(
            r'^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*Died:\s*([^(]+)\s*\((\d+)\)\s*,\s*Killer:\s*([^(]+)\s*\(([^)]+)\)\s*Weapon:\s*([^\s]+)\s*\[([^\]]+)\]'
        )
        
        # Padrão para suicídio: "2025.11.01-20.43.50: Comitted suicide. User: PLAYER (ID, STEAM_ID), [PLAYER]. Location: X=... Y=... Z=..."
        self.suicide_pattern = re.compile(
            r'^(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\s*Comitted suicide\.\s*User:\s*([^(]+)\s*\((\d+),\s*(\d+)\)\s*,\s*\[([^\]]+)\]\.\s*Location:\s*X=([-\d.]+)\s*Y=([-\d.]+)\s*Z=([-\d.]+)\.'
        )
        
        # Padrão para extrair localizações da linha resumida
        self.location_pattern = re.compile(
            r'KillerLoc\s*:\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\s+VictimLoc:\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*Distance:\s*([\d.]+)\s*m'
        )
    
    def _normalize_weapon_name(self, weapon: str) -> str:
        """Normalizar nome da arma removendo prefixos, sufixos e IDs"""
        if not weapon:
            return weapon
        
        # Remover tipo entre colchetes se existir: [Melee] ou [Projectile]
        weapon = re.sub(r'\s*\[.*?\]', '', weapon).strip()
        
        # Remover prefixo "Weapon_" se existir
        if weapon.startswith('Weapon_'):
            weapon = weapon[7:]  # Remove "Weapon_"
        
        # Remover sufixo "_C" e qualquer número após (ex: _C_2147299856)
        weapon = re.sub(r'_C(?:_\d+)?$', '', weapon)
        
        return weapon.strip()
    
    def _load_weapons_mapping(self) -> Dict[str, str]:
        """Carregar mapeamento de armas do JSON"""
        try:
            if os.path.exists(self.weapons_mapping_path):
                with open(self.weapons_mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                    logger.info(f"Mapeamento de armas carregado: {len(mapping)} armas")
                    return mapping
            else:
                # Criar arquivo vazio se não existir
                logger.info("Arquivo mapping.json não encontrado, criando novo")
                empty_mapping = {}
                self._save_weapons_mapping(empty_mapping)
                return empty_mapping
        except Exception as e:
            logger.error(f"Erro ao carregar mapeamento de armas: {e}")
            return {}
    
    def _save_weapons_mapping(self, mapping: Dict[str, str]) -> bool:
        """Salvar mapeamento de armas no JSON com ordenação alfabética"""
        try:
            # Ordenar alfabeticamente por chave
            sorted_mapping = dict(sorted(mapping.items()))
            
            # Garantir que o diretório existe
            os.makedirs(os.path.dirname(self.weapons_mapping_path), exist_ok=True)
            
            with open(self.weapons_mapping_path, 'w', encoding='utf-8') as f:
                json.dump(sorted_mapping, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar mapeamento de armas: {e}")
            return False
    
    def _add_weapon_to_mapping(self, normalized_weapon: str) -> None:
        """Adicionar nova arma ao mapeamento com valor vazio (thread-safe)"""
        if not normalized_weapon:
            return
        
        with self.mapping_lock:
            # Verificar se já existe
            if normalized_weapon not in self.weapons_mapping:
                # Adicionar com valor vazio
                self.weapons_mapping[normalized_weapon] = ""
                self._save_weapons_mapping(self.weapons_mapping)
                logger.info(f"Nova arma descoberta e adicionada ao mapping: {normalized_weapon}")
    
    def _get_weapon_image_path(self, normalized_weapon: str) -> Optional[str]:
        """Obter caminho da imagem da arma usando o mapeamento JSON"""
        if not normalized_weapon or not os.path.exists(self.weapons_images_path):
            return None
        
        # Verificar se a arma está no mapeamento
        image_filename = self.weapons_mapping.get(normalized_weapon)
        
        # Se não está no mapeamento, adicionar com valor vazio
        if image_filename is None:
            self._add_weapon_to_mapping(normalized_weapon)
            return None
        
        # Se está no mapeamento mas vazio, não tem imagem
        if not image_filename or image_filename.strip() == "":
            return None
        
        # Se tem valor no mapeamento, verificar se o arquivo existe
        image_path = os.path.join(self.weapons_images_path, image_filename)
        if os.path.exists(image_path):
            return image_path
        else:
            # Arquivo não existe, logar aviso
            logger.warning(f"Imagem mapeada não encontrada: {image_filename} para arma {normalized_weapon}")
            return None
    
    def _get_kill_webhook_url(self) -> Optional[str]:
        """Obtém URL do webhook kill_log"""
        try:
            if not os.path.exists(self.webhooks_path):
                logger.warning("Arquivo webhooks.json não encontrado")
                return None

            from core.webhooks.manager import WebhooksManager

            mgr = WebhooksManager(str(self.webhooks_path))
            webhooks = mgr.load()
            if not isinstance(webhooks, dict):
                return None
            return webhooks.get('kill_log')
        except Exception as e:
            logger.error(f"Erro ao ler webhooks.json: {e}")
            return None
    
    def _format_discord_message(self, kill_data: Dict) -> Dict:
        """Formata mensagem de kill para Discord"""
        event_type = kill_data.get('event_type', 'kill')
        victim_name = kill_data.get('victim_name', 'Desconhecido')
        timestamp = kill_data.get('timestamp')
        
        # Converter timestamp para datetime se for string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()
        
        # Determinar título, cor e emoji baseado no tipo de evento
        if event_type == 'suicide':
            title = f"💀 Suicídio - {victim_name}"
            color = 0x95a5a6  # Cinza
            description = f"Vítima: {victim_name}"
            
            # Usar imagem Suicide.png para eventos de suicídio
            suicide_image_path = os.path.join(self.weapons_images_path, "Suicide.png")
            
            embed_data = {
                'title': title,
                'description': description,
                'color': color,
                'timestamp': timestamp.isoformat(),
                'footer': {
                    'text': 'SCUM Server Manager'
                }
            }
            
            # Adicionar thumbnail da imagem de suicídio se disponível
            if os.path.exists(suicide_image_path):
                suicide_image_filename = os.path.basename(suicide_image_path)
                embed_data['thumbnail'] = {
                    "url": f"attachment://{suicide_image_filename}"
                }
                return {
                    'embeds': [embed_data],
                    '_use_image': True,
                    '_image_path': suicide_image_path,
                    '_image_filename': suicide_image_filename
                }
            
            return {
                'embeds': [embed_data],
                '_use_image': False
            }
        else:
            killer_name = kill_data.get('killer_profile_name', 'Desconhecido')
            killer_is_npc = kill_data.get('killer_is_npc', False)
            weapon = kill_data.get('weapon', 'Desconhecida')
            weapon_type = kill_data.get('weapon_type', '')
            distance = kill_data.get('distance')
            
            if killer_is_npc:
                # NPC Kill: título com vítima, descrição com killer, arma e distância
                title = f"🤖 Morto por NPC - {victim_name}"
                color = 0xe67e22  # Laranja
                
                description_lines = [f"Killer: NPC Pro Player"]
                
                # Arma (normalizada)
                normalized_weapon = self._normalize_weapon_name(weapon)
                description_lines.append(f"Arma: {normalized_weapon}")
                
                # Distância (apenas se disponível)
                if distance is not None:
                    description_lines.append(f"Distância: {distance:.2f} m")
                
                description = "\n".join(description_lines)
                
                # Verificar se existe imagem da arma (mesmo padrão do PvP)
                weapon_image_path = self._get_weapon_image_path(normalized_weapon)
                
                embed_data = {
                    'title': title,
                    'description': description,
                    'color': color,
                    'timestamp': timestamp.isoformat(),
                    'footer': {
                        'text': 'SCUM Server Manager'
                    }
                }
                
                # Adicionar thumbnail da arma se disponível
                if weapon_image_path:
                    weapon_image_filename = os.path.basename(weapon_image_path)
                    embed_data['thumbnail'] = {
                        "url": f"attachment://{weapon_image_filename}"
                    }
                    return {
                        'embeds': [embed_data],
                        '_use_image': True,
                        '_image_path': weapon_image_path,
                        '_image_filename': weapon_image_filename
                    }
                
                return {
                    'embeds': [embed_data],
                    '_use_image': False
                }
            else:
                # PvP Kill: título sem vítima, descrição com vítima, killer, arma e distância
                title = "⚔️ PvP Kill"
                color = 0xe74c3c  # Vermelho
                
                description_lines = [
                    f"Vítima: {victim_name}",
                    f"Killer: {killer_name}"
                ]
                
                # Arma (normalizada)
                normalized_weapon = self._normalize_weapon_name(weapon)
                description_lines.append(f"Arma: {normalized_weapon}")
                
                # Distância (apenas se disponível)
                if distance is not None:
                    description_lines.append(f"Distância: {distance:.2f} m")
                
                description = "\n".join(description_lines)
                
                # Verificar se existe imagem da arma
                weapon_image_path = self._get_weapon_image_path(normalized_weapon)
                
                embed_data = {
                    'title': title,
                    'description': description,
                    'color': color,
                    'timestamp': timestamp.isoformat(),
                    'footer': {
                        'text': 'SCUM Server Manager'
                    }
                }
                
                # Adicionar thumbnail da arma se disponível
                if weapon_image_path:
                    weapon_image_filename = os.path.basename(weapon_image_path)
                    embed_data['thumbnail'] = {
                        "url": f"attachment://{weapon_image_filename}"
                    }
                    return {
                        'embeds': [embed_data],
                        '_use_image': True,
                        '_image_path': weapon_image_path,
                        '_image_filename': weapon_image_filename
                    }
        
        return {
            'embeds': [{
                'title': title,
                'description': description,
                'color': color,
                'timestamp': timestamp.isoformat(),
                'footer': {
                    'text': 'SCUM Server Manager'
                }
            }],
            '_use_image': False
        }
    
    def _send_to_discord(self, kill_data: Dict) -> bool:
        """Enviar evento de kill para Discord"""
        try:
            webhook_url = self._get_kill_webhook_url()
            if not webhook_url:
                logger.warning("Webhook kill_log não configurado")
                return False
            
            message = self._format_discord_message(kill_data)
            
            # Verificar se deve enviar com imagem
            use_image = message.pop('_use_image', False)
            image_path = message.pop('_image_path', None)
            image_filename = message.pop('_image_filename', None)
            
            # Se tem imagem configurada, enviar com ela
            if use_image and image_path and image_filename and os.path.exists(image_path):
                return self._send_with_image(webhook_url, message, image_path, image_filename)
            else:
                return self._send_without_image(webhook_url, message, kill_data)
                
        except Exception as e:
            logger.error(f"Erro ao enviar kill para Discord: {e}")
            return False
    
    def _send_with_image(self, webhook_url: str, message: Dict, image_path: str, image_filename: str) -> bool:
        """Enviar notificação com miniatura (GIF ou PNG)"""
        try:
            # Determinar tipo MIME baseado na extensão
            if image_filename.lower().endswith('.gif'):
                mime_type = 'image/gif'
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
                logger.info(f"Evento de kill enviado para Discord com miniatura: {image_filename}")
                return True
            else:
                logger.error(f"Falha ao enviar kill com imagem. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar kill com imagem: {e}")
            return False
    
    def _send_without_image(self, webhook_url: str, message: Dict, kill_data: Dict) -> bool:
        """Enviar notificação sem imagem"""
        try:
            response = requests.post(
                webhook_url,
                json=message,
                timeout=10
            )
            
            if response.status_code == 204:
                logger.info(f"Evento de kill enviado para Discord: {kill_data.get('victim_name')}")
                return True
            else:
                logger.error(f"Falha ao enviar kill para Discord: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar kill para Discord: {e}")
            return False
    
    def _parse_scum_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Converter timestamp SCUM para datetime"""
        try:
            # Formato: 2025.11.01-20.37.54
            timestamp_parts = timestamp_str.split('-')
            date_part = timestamp_parts[0].replace('.', '-')
            time_part = timestamp_parts[1].replace('.', ':')
            iso_string = f"{date_part}T{time_part}"
            return datetime.fromisoformat(iso_string)
        except Exception as e:
            logger.error(f"Erro ao converter timestamp: {timestamp_str}, {e}")
            return datetime.now()
    
    def _parse_kill_line(self, line: str) -> Optional[Dict]:
        """Parse uma linha de morte"""
        match = self.kill_pattern.match(line.strip())
        if not match:
            return None
        
        timestamp_str, victim_name, victim_steam_id, killer_name, killer_type, weapon, weapon_type = match.groups()
        
        # Converter timestamp
        timestamp = self._parse_scum_timestamp(timestamp_str)
        
        # Extrair localizações e distância
        location_match = self.location_pattern.search(line)
        killer_x = killer_y = killer_z = victim_x = victim_y = victim_z = distance = None
        
        if location_match:
            killer_x = float(location_match.group(1))
            killer_y = float(location_match.group(2))
            killer_z = float(location_match.group(3))
            victim_x = float(location_match.group(4))
            victim_y = float(location_match.group(5))
            victim_z = float(location_match.group(6))
            distance = float(location_match.group(7))
        
        # Verificar se é NPC
        is_npc = killer_type.strip().upper() == 'NPC'
        
        return {
            'event_type': 'kill',
            'timestamp': timestamp.isoformat(),
            'victim_name': victim_name.strip(),
            'victim_steam_id': victim_steam_id,
            'killer_profile_name': killer_name.strip(),
            'killer_user_id': killer_type.strip(),
            'killer_is_npc': is_npc,
            'weapon': weapon.strip(),
            'weapon_type': weapon_type.strip(),
            'killer_location_x': killer_x,
            'killer_location_y': killer_y,
            'killer_location_z': killer_z,
            'victim_location_x': victim_x,
            'victim_location_y': victim_y,
            'victim_location_z': victim_z,
            'distance': distance,
            'raw_line': line.strip()
        }
    
    def _parse_suicide_line(self, line: str) -> Optional[Dict]:
        """Parse uma linha de suicídio"""
        match = self.suicide_pattern.match(line.strip())
        if not match:
            return None
        
        timestamp_str, player_name, player_id, steam_id, player_name_bracket, x, y, z = match.groups()
        
        # Converter timestamp
        timestamp = self._parse_scum_timestamp(timestamp_str)
        
        return {
            'event_type': 'suicide',
            'timestamp': timestamp.isoformat(),
            'victim_name': player_name.strip(),
            'victim_steam_id': steam_id,
            'victim_player_id': int(player_id),
            'victim_location_x': float(x),
            'victim_location_y': float(y),
            'victim_location_z': float(z),
            'killer_profile_name': None,
            'killer_user_id': None,
            'killer_is_npc': False,
            'weapon': None,
            'weapon_type': None,
            'distance': None,
            'raw_line': line.strip()
        }
    
    def _parse_json_line(self, line: str) -> Optional[Dict]:
        """Parse linha JSON com dados detalhados"""
        try:
            # Remover timestamp do início se houver
            if ':' in line and line.count(':') > 1:
                json_start = line.find('{')
                if json_start > 0:
                    line = line[json_start:]
            
            data = json.loads(line)
            return data
        except Exception as e:
            logger.debug(f"Erro ao parsear JSON: {e}")
            return None
    
    def _enrich_kill_data(self, kill_data: Dict, json_data: Dict = None) -> Dict:
        """Enriquecer dados de kill com informações do JSON"""
        if json_data:
            # Dados do Killer
            killer_data = json_data.get('Killer', {})
            if killer_data:
                server_loc = killer_data.get('ServerLocation', {})
                kill_data['killer_location_x'] = server_loc.get('X')
                kill_data['killer_location_y'] = server_loc.get('Y')
                kill_data['killer_location_z'] = server_loc.get('Z')
                kill_data['killer_has_immortality'] = killer_data.get('HasImmortality', False)
                kill_data['killer_is_npc'] = killer_data.get('UserId', '').upper() == 'NPC'
                kill_data['is_in_game_event'] = killer_data.get('IsInGameEvent', False)
                
                # Se não tem killer_steam_id e não é NPC, tentar extrair do UserId
                if not kill_data.get('killer_steam_id') and not kill_data['killer_is_npc']:
                    user_id = killer_data.get('UserId', '')
                    if user_id.isdigit():
                        kill_data['killer_steam_id'] = user_id
            
            # Dados da Vítima
            victim_data = json_data.get('Victim', {})
            if victim_data:
                server_loc = victim_data.get('ServerLocation', {})
                kill_data['victim_location_x'] = server_loc.get('X')
                kill_data['victim_location_y'] = server_loc.get('Y')
                kill_data['victim_location_z'] = server_loc.get('Z')
                kill_data['is_in_game_event'] = victim_data.get('IsInGameEvent', False) or kill_data.get('is_in_game_event', False)
            
            # Arma e hora do jogo
            weapon = json_data.get('Weapon', '')
            if weapon:
                # Separar arma e tipo: "Weapon_DT11B_C [Projectile]"
                weapon_match = re.match(r'^(.+?)\s*\[([^\]]+)\]$', weapon)
                if weapon_match:
                    kill_data['weapon'] = weapon_match.group(1).strip()
                    kill_data['weapon_type'] = weapon_match.group(2).strip()
                else:
                    kill_data['weapon'] = weapon.strip()
            
            kill_data['game_time'] = json_data.get('TimeOfDay', '')
            kill_data['raw_json'] = json.dumps(json_data)
        
        return kill_data
    
    def _kill_event_exists(self, kill_data: Dict) -> bool:
        """Verificar se o evento já existe no banco"""
        if not self.db_manager:
            return False
        
        try:
            with DatabaseConnector.get_connection(self.db_manager.db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                
                # Para suicídio, verificar apenas timestamp + victim_steam_id
                if kill_data.get('event_type') == 'suicide':
                    cursor.execute('''
                        SELECT COUNT(*) FROM kill_events 
                        WHERE timestamp = ? AND victim_steam_id = ? AND event_type = 'suicide'
                    ''', (
                        kill_data.get('timestamp'),
                        kill_data.get('victim_steam_id')
                    ))
                else:
                    # Para kills, verificar timestamp + victim_steam_id + killer_profile_name
                    cursor.execute('''
                        SELECT COUNT(*) FROM kill_events 
                        WHERE timestamp = ? AND victim_steam_id = ? AND killer_profile_name = ?
                    ''', (
                        kill_data.get('timestamp'),
                        kill_data.get('victim_steam_id'),
                        kill_data.get('killer_profile_name')
                    ))
                
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"Erro ao verificar se kill event existe: {e}")
            return False
    
    def process_kill_log(self, log_file_path: str) -> Dict[str, Any]:
        """
        Processa arquivo de kill log
        
        Args:
            log_file_path: Caminho para o arquivo kill_*.log
            
        Returns:
            Dict com resultado do processamento
        """
        try:
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
                    return {'success': False, 'error': str(e), 'processed': 0}
            
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            if not lines:
                logger.info("Nenhuma linha encontrada no kill log")
                return {'success': True, 'processed': 0}
            
            kill_events = []
            json_data = None
            last_kill_data = None
            
            logger.info(f"Processando {len(lines)} linhas do kill log")
            
            for i, line in enumerate(lines):
                # Ignorar linha de versão
                if 'Game version:' in line:
                    continue
                
                # Tentar parsear como JSON primeiro
                json_parsed = self._parse_json_line(line)
                if json_parsed:
                    json_data = json_parsed
                    # Se temos um kill_data pendente, enriquecer com JSON e adicionar
                    if last_kill_data:
                        enriched_kill = self._enrich_kill_data(last_kill_data, json_data)
                        kill_events.append(enriched_kill)
                        last_kill_data = None
                        json_data = None
                    continue
                
                # Tentar parsear como morte
                kill_data = self._parse_kill_line(line)
                if kill_data:
                    # Se há JSON já parseado (da linha anterior), enriquecer agora
                    if json_data:
                        kill_data = self._enrich_kill_data(kill_data, json_data)
                        json_data = None
                        kill_events.append(kill_data)
                    else:
                        # Guardar para enriquecer com JSON da próxima linha
                        last_kill_data = kill_data
                    continue
                
                # Tentar parsear como suicídio
                suicide_data = self._parse_suicide_line(line)
                if suicide_data:
                    kill_events.append(suicide_data)
                    continue
            
            # Se sobrou um kill_data pendente sem JSON, adicionar mesmo assim
            if last_kill_data:
                kill_events.append(last_kill_data)
                last_kill_data = None
            
            if not kill_events:
                logger.info("Nenhum evento de kill encontrado no arquivo")
                return {'success': True, 'processed': 0}
            
            # Verificar duplicatas e filtrar
            unique_events = []
            for event in kill_events:
                if not self._kill_event_exists(event):
                    unique_events.append(event)
            
            if not unique_events:
                logger.info(f"Todos os {len(kill_events)} eventos já foram processados")
                return {'success': True, 'processed': 0, 'skipped': len(kill_events)}
            
            # Preparar dados para inserção e enviar ao Discord
            events_to_insert = []
            for event in unique_events:
                # Adicionar nome do arquivo
                event['log_file'] = os.path.basename(log_file_path)
                
                # Enviar para Discord
                discord_sent = self._send_to_discord(event)
                
                # Enviar para o chat do jogo (Kill Feed)
                try:
                    self._send_in_game_feed(event)
                except Exception as e:
                    logger.error(f"Erro ao disparar kill feed no chat do jogo: {e}")
                
                # Verificar e punir Team Kill de Squad
                if event.get('event_type') == 'kill' and not event.get('killer_is_npc', False):
                    killer_steam_id = event.get('killer_steam_id') or event.get('killer_user_id')
                    victim_steam_id = event.get('victim_steam_id')
                    if killer_steam_id and victim_steam_id and killer_steam_id != victim_steam_id:
                        try:
                            from app.extensions import get_services
                            svc = get_services()
                            if getattr(svc, 'squad_tk_jail_service', None):
                                svc.squad_tk_jail_service.check_and_punish_tk(
                                    killer_steam_id=killer_steam_id,
                                    killer_name=event.get('killer_profile_name') or 'Desconhecido',
                                    victim_steam_id=victim_steam_id,
                                    victim_name=event.get('victim_name') or 'Desconhecido'
                                )
                        except Exception as tk_err:
                            logger.error(f"Erro ao processar verificação de Team Kill: {tk_err}")
                        
                        try:
                            from app.extensions import get_services
                            from uuid import uuid4
                            svc = get_services()
                            if getattr(svc, 'bounty_service', None):
                                svc.bounty_service.process_pvp_kill(
                                    killer_steam_id=killer_steam_id,
                                    killer_name=event.get('killer_profile_name') or 'Desconhecido',
                                    victim_steam_id=victim_steam_id,
                                    victim_name=event.get('victim_name') or 'Desconhecido',
                                    kill_event_id=uuid4().hex
                                )
                        except Exception as bounty_err:
                            logger.error(f"Erro ao processar Bounty Hunter Killstreak: {bounty_err}")
                
                # Preparar estrutura para o banco
                event_data = {
                    'event_type': event.get('event_type', 'kill'),
                    'timestamp': event.get('timestamp'),
                    'game_time': event.get('game_time'),
                    'victim_steam_id': event.get('victim_steam_id'),
                    'victim_player_id': event.get('victim_player_id'),
                    'victim_name': event.get('victim_name'),
                    'victim_location_x': event.get('victim_location_x'),
                    'victim_location_y': event.get('victim_location_y'),
                    'victim_location_z': event.get('victim_location_z'),
                    'killer_steam_id': event.get('killer_steam_id'),
                    'killer_user_id': event.get('killer_user_id'),
                    'killer_profile_name': event.get('killer_profile_name'),
                    'killer_is_npc': event.get('killer_is_npc', False),
                    'killer_location_x': event.get('killer_location_x'),
                    'killer_location_y': event.get('killer_location_y'),
                    'killer_location_z': event.get('killer_location_z'),
                    'killer_has_immortality': event.get('killer_has_immortality', False),
                    'weapon': event.get('weapon'),
                    'weapon_type': event.get('weapon_type'),
                    'distance': event.get('distance'),
                    'is_in_game_event': event.get('is_in_game_event', False),
                    'log_file': event.get('log_file'),
                    'raw_json': event.get('raw_json'),
                    'discord_sent': discord_sent
                }
                
                events_to_insert.append(event_data)
            
            # Inserir no banco
            if self.db_manager:
                inserted_count = self.db_manager.insert_batch_kill_events(events_to_insert)
                logger.info(f"Kill log processado: {inserted_count} eventos inseridos")
                
                # Verificar detonações de minas
                try:
                    self._check_mine_detonations(events_to_insert)
                except Exception as e:
                    logger.error(f"Erro ao verificar detonacoes de minas: {e}")
                
                return {
                    'success': True,
                    'processed': inserted_count,
                    'skipped': len(kill_events) - len(unique_events),
                    'total_found': len(kill_events)
                }
            else:
                logger.warning("DatabaseManager não disponível, eventos não foram salvos")
                return {
                    'success': False,
                    'error': 'DatabaseManager não disponível',
                    'processed': 0
                }
            
        except Exception as e:
            logger.error(f"Erro ao processar kill log: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e), 'processed': 0}

    def _check_mine_detonations(self, kill_events: List[Dict[str, Any]]) -> None:
        """Verificar se os eventos de kill correspondem a detonações de minas"""
        for event in kill_events:
            try:
                weapon = event.get('weapon') or ""
                event_type = event.get('event_type') or 'kill'
                is_mine_weapon = any(x in weapon.lower() for x in ["mine", "claymore", "pipebomb", "trap", "explosive", "bombspinner"])
                
                vx = event.get('victim_location_x')
                vy = event.get('victim_location_y')
                
                if (is_mine_weapon or event_type == 'suicide') and vx is not None and vy is not None:
                    # Usar tolerância de 500 unidades (5 metros) para detecção de explosão
                    owner_steam_id = self.db_manager.mark_mine_detonated_by_coords(float(vx), float(vy), tolerance=500.0)
                    if owner_steam_id:
                        logger.info(f"KillProcessor: Mina do jogador {owner_steam_id} detonada e atualizada no banco. Vitima: {event.get('victim_name')} ({vx}, {vy})")
            except Exception as e:
                logger.error(f"Erro ao verificar detonacao para evento: {e}")

    def _get_random_kill_phrase(self) -> str:
        """Retorna uma frase aleatória do arquivo de frases do kill feed"""
        try:
            kill_feed_cfg = self.config.get("kill_feed", {})
            phrases_path = kill_feed_cfg.get("phrases_path", "data/kill_feed_phrases.json")
            if os.path.exists(phrases_path):
                with open(phrases_path, 'r', encoding='utf-8') as f:
                    phrases = json.load(f)
                if isinstance(phrases, list) and phrases:
                    import random
                    return random.choice(phrases)
        except Exception as e:
            logger.error(f"Erro ao carregar frases do kill feed: {e}")
        return "Deitou sem sono!"

    def _send_in_game_feed(self, event: Dict) -> None:
        """Envia evento de PvP kill para o chat global/feed do jogo (Announce ou SendChat)"""
        try:
            # Apenas PvP kills (exclui suicídios e NPC kills)
            if event.get('event_type') != 'kill' or event.get('killer_is_npc', False):
                return
                
            kill_feed_cfg = self.config.get("kill_feed", {})
            if not kill_feed_cfg.get("enabled", True):
                return
                
            mode = kill_feed_cfg.get("mode", "chat").lower()
            priority = kill_feed_cfg.get("priority", 15)
            
            # Sanitizar entradas de texto para evitar quebra de comandos RCON e newlines
            def sanitize_input(text: str) -> str:
                if not text:
                    return ""
                # Remover quebras de linha e retornos de carro (evita injeção de múltiplos comandos RCON)
                text = text.replace("\r", "").replace("\n", "")
                # Substituir aspas duplas por aspas simples (evita quebrar a aspa de fechamento do comando SendChat)
                text = text.replace('"', "'")
                # Limpar caracteres de controle
                text = "".join(ch for ch in text if ord(ch) >= 32)
                return text.strip()
            
            killer = sanitize_input(event.get('killer_profile_name') or 'Desconhecido')
            victim = sanitize_input(event.get('victim_name') or 'Desconhecido')
            weapon = sanitize_input(self._normalize_weapon_name(event.get('weapon') or 'Desconhecida'))
            distance = event.get('distance')
            
            dist_str = f"{distance:.1f}" if distance is not None else "0"
            phrase = sanitize_input(self._get_random_kill_phrase())
            
            default_template = "{killer} matou {victim} ({weapon} - {distance}m) | {phrase}"
            template = kill_feed_cfg.get("message_template", default_template)
            
            try:
                msg = template.format(killer=killer, victim=victim, weapon=weapon, distance=dist_str, phrase=phrase)
            except Exception as e:
                logger.error(f"Erro ao formatar mensagem do kill feed: {e}")
                msg = f"{killer} matou {victim} ({weapon} - {dist_str}m) | {phrase}"
                
            # Garantir sanitização completa da mensagem final gerada pelo template customizado
            msg = sanitize_input(msg)
                
            from core.rcon_queue_manager import RconQueueManager
            rcon_q = RconQueueManager.get_instance(self.config_path)
            
            if mode == "announce":
                logger.info(f"Enviando kill feed via Announce: {msg}")
                rcon_q.enqueue_command(f'Announce {msg}', priority=priority)
            elif mode == "chat":
                # Obter todos os jogadores online do banco
                online_steam_ids = []
                try:
                    with DatabaseConnector.get_connection(self.db_manager.db_path, write_mode=False) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT steam_id FROM players_online WHERE status = 'online'")
                        online_steam_ids = [row[0] for row in cursor.fetchall() if row[0]]
                except Exception as e:
                    logger.error(f"Erro ao buscar jogadores online para kill feed: {e}")
                
                if online_steam_ids:
                    chat_type = kill_feed_cfg.get("chat_type", 2)
                    logger.info(f"Enviando kill feed via SendChat ({chat_type}) para {len(online_steam_ids)} jogadores")
                    for steam_id in online_steam_ids:
                        rcon_q.enqueue_command(f'SendChat {chat_type} "{msg}" {steam_id}', delay_after=0.05, priority=priority)
        except Exception as e:
            logger.error(f"Erro ao processar envio do kill feed in-game: {e}")

