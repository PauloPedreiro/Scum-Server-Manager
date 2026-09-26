"""
Integração com Steam API para obter informações de jogadores
Usa Steam Community XML API (pública, sem API key) como método principal
"""

import requests
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
from datetime import datetime

# Constantes de segurança (hardcoded para prevenir injeção de URL)
STEAM_COMMUNITY_XML_BASE_URL = "http://steamcommunity.com/profiles"
STEAM_COMMUNITY_XML_SUFFIX = "/?xml=1"
STEAM_PROFILE_BASE_URL = "https://steamcommunity.com/profiles"

class SteamAPI:
    def __init__(self, api_key: str = None):
        # API key não é mais necessária (usamos Steam Community XML API pública)
        # Parâmetro mantido para compatibilidade, mas não é usado
        self.api_key = None  # Não usado mais
        self.timeout = 10
        self.cache = {}
        self.cache_timeout = 300  # 5 minutos
        
    def _validate_steam_id(self, steam_id: str) -> bool:
        """
        Validar formato do Steam ID (segurança)
        
        Args:
            steam_id: Steam ID a validar
            
        Returns:
            True se válido, False caso contrário
        """
        if not steam_id:
            return False
        # Steam ID deve conter apenas números
        if not steam_id.isdigit():
            return False
        # Steam ID64 tem entre 17 e 19 dígitos
        if len(steam_id) < 17 or len(steam_id) > 19:
            return False
        return True
    
    def _get_steam_community_info(self, steam_id: str) -> Dict[str, Any]:
        """
        Obter informações do jogador via Steam Community XML API (sem API key)
        
        Retorna apenas dados essenciais:
        - Nome (steamID)
        - Avatar (avatarFull)
        - País (countryCode ou location)
        - Link do perfil (construído)
        
        Args:
            steam_id: Steam ID do jogador (64-bit)
            
        Returns:
            Dict com informações essenciais do jogador
        """
        # VALIDAÇÃO DE SEGURANÇA: Validar Steam ID antes de usar
        if not self._validate_steam_id(steam_id):
            print(f"ERRO: Steam ID inválido: {steam_id}")
            return self._get_fallback_info(steam_id)
        
        try:
            # CONSTRUÇÃO SEGURA: Usar constantes hardcoded + steam_id validado
            xml_url = f"{STEAM_COMMUNITY_XML_BASE_URL}/{steam_id}{STEAM_COMMUNITY_XML_SUFFIX}"
            
            print(f"OK: Consultando Steam Community XML API para {steam_id}")
            response = requests.get(xml_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parsear XML
            root = ET.fromstring(response.content)
            
            # Extrair apenas campos essenciais
            persona_name = root.findtext('steamID', 'Unknown Player')
            avatar_full = root.findtext('avatarFull', '')
            avatar_medium = root.findtext('avatarMedium', '')
            avatar_icon = root.findtext('avatarIcon', '')
            country_code = root.findtext('countryCode', '')
            location = root.findtext('location', '')
            vac_banned = root.findtext('vacBanned', '0')
            trade_ban_state = root.findtext('tradeBanState', 'None')
            is_limited_account = root.findtext('isLimitedAccount', '0')
            
            # Construir URL do perfil de forma segura
            profile_url = f"{STEAM_PROFILE_BASE_URL}/{steam_id}"
            
            # Usar avatar full se disponível, senão medium, senão icon
            avatar_url = avatar_full or avatar_medium or avatar_icon
            
            player_info = {
                'steam_id': steam_id,
                'persona_name': persona_name,
                'avatar_url': avatar_icon,  # Avatar pequeno (padrão)
                'avatar_medium_url': avatar_medium,
                'avatar_full_url': avatar_full,
                'country_code': country_code,
                'location': location,  # Localização completa (fallback)
                'profile_url': profile_url,
                'vac_banned': str(vac_banned).strip() == '1',
                'trade_ban_state': str(trade_ban_state).strip() or 'None',
                'is_limited_account': str(is_limited_account).strip() == '1',
                'persona_state': 0,
                'community_visibility': 0,
                'last_logoff': 0,
                'real_name': '',
                'time_created': 0
            }
            
            # Salvar no cache
            cache_key = f"player_{steam_id}"
            self.cache[cache_key] = (player_info, datetime.now().timestamp())
            
            # Log seguro (evita erro de encoding com caracteres especiais)
            try:
                print(f"OK: Dados obtidos do Steam Community XML para {steam_id}: {persona_name}")
            except UnicodeEncodeError:
                # Se houver erro de encoding, usar apenas Steam ID
                print(f"OK: Dados obtidos do Steam Community XML para {steam_id}")
            
            return player_info
            
        except ET.ParseError as e:
            print(f"ERRO: Erro ao parsear XML do Steam Community: {e}")
            return self._get_fallback_info(steam_id)
        except requests.exceptions.RequestException as e:
            print(f"ERRO: Erro de rede ao consultar Steam Community: {e}")
            return self._get_fallback_info(steam_id)
        except Exception as e:
            print(f"ERRO: Erro inesperado ao obter dados do Steam Community: {e}")
            return self._get_fallback_info(steam_id)
    
    def get_player_info(self, steam_id: str) -> Dict[str, Any]:
        """
        Obter informações do jogador via Steam Community XML API
        
        Sempre usa Steam Community XML API (pública, sem API key) como método principal.
        
        Args:
            steam_id: Steam ID do jogador
            
        Returns:
            Dict com informações do jogador ou dados padrão se falhar
        """
        try:
            # Verificar cache primeiro
            cache_key = f"player_{steam_id}"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now().timestamp() - timestamp < self.cache_timeout:
                    print(f"OK: Dados do cache para {steam_id}")
                    return cached_data
            
            # SEMPRE usar Steam Community XML API (não requer API key)
            player_info = self._get_steam_community_info(steam_id)
            
            return player_info
                
        except Exception as e:
            print(f"ERRO: Erro ao obter dados do jogador: {e}")
            return self._get_fallback_info(steam_id)
    
    def _parse_player_data(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parsear dados da Steam API"""
        return {
            'steam_id': player_data.get('steamid', ''),
            'persona_name': player_data.get('personaname', 'Unknown'),
            'avatar_url': player_data.get('avatar', ''),
            'avatar_medium_url': player_data.get('avatarmedium', ''),
            'avatar_full_url': player_data.get('avatarfull', ''),
            'country_code': player_data.get('loccountrycode', ''),
            'profile_url': player_data.get('profileurl', ''),
            'persona_state': player_data.get('personastate', 0),
            'community_visibility': player_data.get('communityvisibilitystate', 0),
            'last_logoff': player_data.get('lastlogoff', 0),
            'real_name': player_data.get('realname', ''),
            'time_created': player_data.get('timecreated', 0)
        }
    
    def _get_fallback_info(self, steam_id: str) -> Dict[str, Any]:
        """Dados padrão quando Steam Community XML API não está disponível"""
        # Construir URL do perfil de forma segura
        profile_url = f"{STEAM_PROFILE_BASE_URL}/{steam_id}" if steam_id else ""
        
        return {
            'steam_id': steam_id,
            'persona_name': 'Unknown Player',
            'avatar_url': '',
            'avatar_medium_url': '',
            'avatar_full_url': '',
            'country_code': '',
            'location': '',
            'profile_url': profile_url,
            'persona_state': 0,
            'community_visibility': 0,
            'last_logoff': 0,
            'real_name': '',
            'time_created': 0
        }
    
    def get_country_flag(self, country_code: str) -> str:
        """Obter emoji da bandeira do país"""
        if not country_code:
            return "🌍"
        
        # Mapeamento básico de códigos de país para emojis
        country_flags = {
            'BR': '🇧🇷', 'US': '🇺🇸', 'CA': '🇨🇦', 'GB': '🇬🇧', 'DE': '🇩🇪',
            'FR': '🇫🇷', 'ES': '🇪🇸', 'IT': '🇮🇹', 'RU': '🇷🇺', 'JP': '🇯🇵',
            'CN': '🇨🇳', 'KR': '🇰🇷', 'AU': '🇦🇺', 'MX': '🇲🇽', 'AR': '🇦🇷',
            'CL': '🇨🇱', 'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'UY': '🇺🇾',
            'PY': '🇵🇾', 'BO': '🇧🇴', 'EC': '🇪🇨', 'GY': '🇬🇾', 'SR': '🇸🇷',
            'GF': '🇬🇫', 'FK': '🇫🇰', 'NL': '🇳🇱', 'BE': '🇧🇪', 'CH': '🇨🇭',
            'AT': '🇦🇹', 'SE': '🇸🇪', 'NO': '🇳🇴', 'DK': '🇩🇰', 'FI': '🇫🇮',
            'PL': '🇵🇱', 'CZ': '🇨🇿', 'SK': '🇸🇰', 'HU': '🇭🇺', 'RO': '🇷🇴',
            'BG': '🇧🇬', 'HR': '🇭🇷', 'SI': '🇸🇮', 'EE': '🇪🇪', 'LV': '🇱🇻',
            'LT': '🇱🇹', 'IE': '🇮🇪', 'PT': '🇵🇹', 'GR': '🇬🇷', 'CY': '🇨🇾',
            'MT': '🇲🇹', 'LU': '🇱🇺', 'IS': '🇮🇸', 'LI': '🇱🇮', 'MC': '🇲🇨',
            'SM': '🇸🇲', 'VA': '🇻🇦', 'AD': '🇦🇩', 'BY': '🇧🇾', 'UA': '🇺🇦',
            'MD': '🇲🇩', 'RS': '🇷🇸', 'ME': '🇲🇪', 'BA': '🇧🇦', 'MK': '🇲🇰',
            'AL': '🇦🇱', 'XK': '🇽🇰', 'TR': '🇹🇷', 'IL': '🇮🇱', 'SA': '🇸🇦',
            'AE': '🇦🇪', 'EG': '🇪🇬', 'ZA': '🇿🇦', 'NG': '🇳🇬', 'KE': '🇰🇪',
            'GH': '🇬🇭', 'MA': '🇲🇦', 'TN': '🇹🇳', 'DZ': '🇩🇿', 'LY': '🇱🇾',
            'SD': '🇸🇩', 'ET': '🇪🇹', 'UG': '🇺🇬', 'TZ': '🇹🇿', 'ZW': '🇿🇼',
            'BW': '🇧🇼', 'NA': '🇳🇦', 'SZ': '🇸🇿', 'LS': '🇱🇸', 'MW': '🇲🇼',
            'ZM': '🇿🇲', 'MZ': '🇲🇿', 'MG': '🇲🇬', 'MU': '🇲🇺', 'SC': '🇸🇨',
            'KM': '🇰🇲', 'DJ': '🇩🇯', 'SO': '🇸🇴', 'ER': '🇪🇷', 'SS': '🇸🇸',
            'CF': '🇨🇫', 'TD': '🇹🇩', 'NE': '🇳🇪', 'ML': '🇲🇱', 'BF': '🇧🇫',
            'CI': '🇨🇮', 'LR': '🇱🇷', 'SL': '🇸🇱', 'GN': '🇬🇳', 'GW': '🇬🇼',
            'GM': '🇬🇲', 'SN': '🇸🇳', 'CV': '🇨🇻', 'ST': '🇸🇹', 'GQ': '🇬🇶',
            'GA': '🇬🇦', 'CG': '🇨🇬', 'CD': '🇨🇩', 'AO': '🇦🇴', 'CM': '🇨🇲',
            'TG': '🇹🇬', 'BJ': '🇧🇯', 'NE': '🇳🇪', 'NG': '🇳🇬', 'TD': '🇹🇩',
            'CF': '🇨🇫', 'CM': '🇨🇲', 'GQ': '🇬🇶', 'GA': '🇬🇦', 'CG': '🇨🇬',
            'CD': '🇨🇩', 'AO': '🇦🇴', 'ZM': '🇿🇲', 'ZW': '🇿🇼', 'BW': '🇧🇼',
            'NA': '🇳🇦', 'SZ': '🇸🇿', 'LS': '🇱🇸', 'MW': '🇲🇼', 'MZ': '🇲🇿',
            'MG': '🇲🇬', 'MU': '🇲🇺', 'SC': '🇸🇨', 'KM': '🇰🇲', 'DJ': '🇩🇯',
            'SO': '🇸🇴', 'ER': '🇪🇷', 'SS': '🇸🇸', 'CF': '🇨🇫', 'TD': '🇹🇩',
            'NE': '🇳🇪', 'ML': '🇲🇱', 'BF': '🇧🇫', 'CI': '🇨🇮', 'LR': '🇱🇷',
            'SL': '🇸🇱', 'GN': '🇬🇳', 'GW': '🇬🇼', 'GM': '🇬🇲', 'SN': '🇸🇳',
            'CV': '🇨🇻', 'ST': '🇸🇹', 'GQ': '🇬🇶', 'GA': '🇬🇦', 'CG': '🇨🇬',
            'CD': '🇨🇩', 'AO': '🇦🇴', 'CM': '🇨🇲', 'TG': '🇹🇬', 'BJ': '🇧🇯'
        }
        
        return country_flags.get(country_code.upper(), f"🌍 {country_code}")
    
    def format_player_info(self, player_info: Dict[str, Any]) -> Dict[str, str]:
        """
        Formatar informações do jogador para exibição no Discord
        
        Retorna apenas dados essenciais:
        - persona_name (nome)
        - avatar_url (avatar completo)
        - country (país formatado)
        - profile_url (link do perfil)
        """
        # Obter país (priorizar countryCode, fallback para location)
        country_code = player_info.get('country_code', '')
        location = player_info.get('location', '')
        
        # Formatar país
        if country_code:
            country_flag = self.get_country_flag(country_code)
            country_name = self._get_country_name(country_code)
            country = f"{country_flag} {country_name}"
        elif location:
            country = f"🌍 {location}"
        else:
            country = "🌍 Unknown"
        
        # Garantir avatar (usar fallback se vazio)
        avatar_url = player_info.get('avatar_full_url', '')
        if not avatar_url:
            # Tentar avatar médio como fallback
            avatar_url = player_info.get('avatar_medium_url', '')
        if not avatar_url:
            # Tentar avatar pequeno como último fallback
            avatar_url = player_info.get('avatar_url', '')
        
        return {
            'steam_id': player_info.get('steam_id', ''),
            'persona_name': player_info.get('persona_name', 'Unknown Player'),
            'avatar_url': avatar_url,
            'country': country,
            'profile_url': player_info.get('profile_url', ''),
            'vac_banned': bool(player_info.get('vac_banned', False)),
            'trade_ban_state': player_info.get('trade_ban_state', 'None'),
            'is_limited_account': bool(player_info.get('is_limited_account', False))
        }
    
    def _get_country_name(self, country_code: str) -> str:
        """Obter nome do país pelo código"""
        if not country_code:
            return ""
        
        country_names = {
            'BR': 'Brazil', 'US': 'United States', 'CA': 'Canada', 'GB': 'United Kingdom',
            'DE': 'Germany', 'FR': 'France', 'ES': 'Spain', 'IT': 'Italy', 'RU': 'Russia',
            'JP': 'Japan', 'CN': 'China', 'KR': 'South Korea', 'AU': 'Australia',
            'MX': 'Mexico', 'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia',
            'PE': 'Peru', 'VE': 'Venezuela', 'UY': 'Uruguay', 'PY': 'Paraguay',
            'BO': 'Bolivia', 'EC': 'Ecuador', 'GY': 'Guyana', 'SR': 'Suriname',
            'GF': 'French Guiana', 'FK': 'Falkland Islands', 'NL': 'Netherlands',
            'BE': 'Belgium', 'CH': 'Switzerland', 'AT': 'Austria', 'SE': 'Sweden',
            'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland', 'PL': 'Poland',
            'CZ': 'Czech Republic', 'SK': 'Slovakia', 'HU': 'Hungary', 'RO': 'Romania',
            'BG': 'Bulgaria', 'HR': 'Croatia', 'SI': 'Slovenia', 'EE': 'Estonia',
            'LV': 'Latvia', 'LT': 'Lithuania', 'IE': 'Ireland', 'PT': 'Portugal',
            'GR': 'Greece', 'CY': 'Cyprus', 'MT': 'Malta', 'LU': 'Luxembourg',
            'IS': 'Iceland', 'LI': 'Liechtenstein', 'MC': 'Monaco', 'SM': 'San Marino',
            'VA': 'Vatican City', 'AD': 'Andorra', 'BY': 'Belarus', 'UA': 'Ukraine',
            'MD': 'Moldova', 'RS': 'Serbia', 'ME': 'Montenegro', 'BA': 'Bosnia and Herzegovina',
            'MK': 'North Macedonia', 'AL': 'Albania', 'XK': 'Kosovo', 'TR': 'Turkey',
            'IL': 'Israel', 'SA': 'Saudi Arabia', 'AE': 'United Arab Emirates',
            'EG': 'Egypt', 'ZA': 'South Africa', 'NG': 'Nigeria', 'KE': 'Kenya',
            'GH': 'Ghana', 'MA': 'Morocco', 'TN': 'Tunisia', 'DZ': 'Algeria',
            'LY': 'Libya', 'SD': 'Sudan', 'ET': 'Ethiopia', 'UG': 'Uganda',
            'TZ': 'Tanzania', 'ZW': 'Zimbabwe', 'BW': 'Botswana', 'NA': 'Namibia',
            'SZ': 'Eswatini', 'LS': 'Lesotho', 'MW': 'Malawi', 'ZM': 'Zambia',
            'MZ': 'Mozambique', 'MG': 'Madagascar', 'MU': 'Mauritius', 'SC': 'Seychelles',
            'KM': 'Comoros', 'DJ': 'Djibouti', 'SO': 'Somalia', 'ER': 'Eritrea',
            'SS': 'South Sudan', 'CF': 'Central African Republic', 'TD': 'Chad',
            'NE': 'Niger', 'ML': 'Mali', 'BF': 'Burkina Faso', 'CI': 'Ivory Coast',
            'LR': 'Liberia', 'SL': 'Sierra Leone', 'GN': 'Guinea', 'GW': 'Guinea-Bissau',
            'GM': 'Gambia', 'SN': 'Senegal', 'CV': 'Cape Verde', 'ST': 'Sao Tome and Principe',
            'GQ': 'Equatorial Guinea', 'GA': 'Gabon', 'CG': 'Republic of the Congo',
            'CD': 'Democratic Republic of the Congo', 'AO': 'Angola', 'CM': 'Cameroon',
            'TG': 'Togo', 'BJ': 'Benin'
        }
        
        return country_names.get(country_code.upper(), country_code)
