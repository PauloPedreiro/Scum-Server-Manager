"""
Processador de Jogadores
Gerencia detecção de jogadores novos, mudança de nomes e tempo de jogo
"""

import sqlite3
import json
import requests
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from ..webhooks.manager import WebhooksManager

class PlayerProcessor:
    """Processador de jogadores para detecção de novos players e mudança de nomes"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.active_sessions = {}  # {steam_id: {'login_time': datetime, 'player_name': str, 'player_id': int}}
        self.steam_api = None
        self.webhook_url = None
        self.ban_webhook_url = None
        self._load_webhook_config()
    
    def _load_webhook_config(self):
        """Carregar configuração do webhook"""
        try:
            webhook_path = "data/webhooks.json"
            manager = WebhooksManager(webhook_path)
            webhooks = manager.load()
            self.webhook_url = webhooks.get('new_player')
            self.ban_webhook_url = webhooks.get('ban-list')
            print(f"OK Webhook configurado: {self.webhook_url is not None}")
        except Exception as e:
            print(f"ERRO Erro ao carregar configuração do webhook: {e}")

    def _send_ban_alert(self, player_data: Dict[str, Any], steam_info: Dict[str, Any]) -> bool:
        """Enviar alerta de jogador com ban para Discord"""
        try:
            if not self.ban_webhook_url:
                print("AVISO Webhook não configurado para ban-list")
                return False

            steam_id = player_data['steam_id']
            player_name = player_data['player_name']
            steam_name = steam_info.get('persona_name', 'Unknown Player') if steam_info else 'Unknown Player'
            steam_profile_url = steam_info.get('profile_url', f'https://steamcommunity.com/profiles/{steam_id}') if steam_info else f'https://steamcommunity.com/profiles/{steam_id}'
            avatar_url = steam_info.get('avatar_url', '') if steam_info else ''
            country = steam_info.get('country', '🌍 Unknown') if steam_info else '🌍 Unknown'

            vac_banned = bool(steam_info.get('vac_banned', False)) if steam_info else False
            trade_ban_state = str(steam_info.get('trade_ban_state', 'None')) if steam_info else 'None'
            is_limited_account = bool(steam_info.get('is_limited_account', False)) if steam_info else False

            embed = {
                "title": "🚨 Banned Player Detected",
                "color": 0xE74C3C,
                "fields": [
                    {
                        "name": "In-Game Name",
                        "value": player_name,
                        "inline": True
                    },
                    {
                        "name": "Steam Name",
                        "value": steam_name,
                        "inline": True
                    },
                    {
                        "name": "Steam ID",
                        "value": f"`{steam_id}`",
                        "inline": True
                    },
                    {
                        "name": "Country",
                        "value": country,
                        "inline": True
                    },
                    {
                        "name": "VAC Banned",
                        "value": "Yes" if vac_banned else "No",
                        "inline": True
                    },
                    {
                        "name": "Trade Ban State",
                        "value": trade_ban_state,
                        "inline": True
                    },
                    {
                        "name": "Limited Account",
                        "value": "Yes" if is_limited_account else "No",
                        "inline": True
                    },
                    {
                        "name": "🔗 Steam Profile",
                        "value": f"[Click here]({steam_profile_url})",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "SCUM Server Manager"
                }
            }

            if avatar_url:
                embed["thumbnail"] = {"url": avatar_url}

            payload = {
                "embeds": [embed]
            }

            response = requests.post(
                self.ban_webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"OK Alerta de ban enviado: {player_name}")
                return True
            else:
                print(f"ERRO Falha ao enviar alerta de ban: {response.status_code} - {response.text}")
                print(f"   Webhook URL: {self.ban_webhook_url[:50]}...")
                return False

        except Exception as e:
            print(f"ERRO Erro ao enviar alerta de ban: {e}")
            return False
    
    def _send_new_player_notification(self, player_data: Dict[str, Any], steam_info: Dict[str, Any] = None) -> bool:
        """Enviar notificação de novo jogador para Discord"""
        try:
            if not self.webhook_url:
                print("AVISO Webhook não configurado para novos jogadores")
                return False
            
            # Preparar dados do jogador
            steam_id = player_data['steam_id']
            player_name = player_data['player_name']
            join_time = player_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            
            # Usar dados da Steam API se disponível (format_player_info já retorna country formatado)
            if steam_info:
                avatar_url = steam_info.get('avatar_url', '')
                country = steam_info.get('country', '🌍 Unknown')
            else:
                avatar_url = ''
                country = '🌍 Unknown'
            
            # Montar embed do Discord no formato elegante (primeiro print)
            steam_name = steam_info.get('persona_name', 'Unknown Player') if steam_info else 'Unknown Player'
            steam_profile_url = steam_info.get('profile_url', f'https://steamcommunity.com/profiles/{steam_id}') if steam_info else f'https://steamcommunity.com/profiles/{steam_id}'
            
            # Campos individuais - apenas dados essenciais
            embed = {
                "title": "🎉 New Player on Server!",
                "color": 0xFF6B35,  # Laranja
                "fields": [
                    {
                        "name": "In-Game Name",
                        "value": player_name,
                        "inline": True
                    },
                    {
                        "name": "Steam Name",
                        "value": steam_name,
                        "inline": True
                    },
                    {
                        "name": "Steam ID",
                        "value": f"`{steam_id}`",
                        "inline": True
                    },
                    {
                        "name": "Country",
                        "value": country,
                        "inline": True
                    },
                    {
                        "name": "🔗 Steam Profile",
                        "value": f"[Click here]({steam_profile_url})",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "SCUM Server Manager"
                }
            }
            
            # Adicionar thumbnail se tiver avatar
            if avatar_url:
                embed["thumbnail"] = {"url": avatar_url}
            
            # Montar payload do webhook (sem content redundante)
            payload = {
                "embeds": [embed]
            }
            
            # Enviar webhook
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Discord pode retornar 200 ou 204 para sucesso
            if response.status_code in [200, 204]:
                print(f"OK Notificação de novo jogador enviada: {player_name}")
                return True
            else:
                print(f"ERRO Falha ao enviar notificação: {response.status_code} - {response.text}")
                print(f"   Webhook URL: {self.webhook_url[:50]}...")
                return False
                
        except Exception as e:
            print(f"ERRO Erro ao enviar notificação de novo jogador: {e}")
            return False
    
    def _get_steam_player_info(self, steam_id: str) -> Dict[str, Any]:
        """Obter informações do jogador via Steam API"""
        try:
            if not self.steam_api:
                # Inicializar Steam API se não estiver configurada
                from .steam_api import SteamAPI
                self.steam_api = SteamAPI()
            
            player_info = self.steam_api.get_player_info(steam_id)
            return self.steam_api.format_player_info(player_info)
            
        except Exception as e:
            print(f"AVISO Erro ao obter dados da Steam API: {e}")
            return {}
    
    def process_login(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processar login de jogador"""
        try:
            # DEBUG removido para reduzir verbosidade do console
            # print(f"DEBUG PlayerProcessor: Processando login de {session_data.get('player_name', 'UNKNOWN')}")
            steam_id = session_data['steam_id']
            player_name = session_data['player_name']
            player_id = session_data['player_id']
            timestamp = session_data['timestamp']
            
            # DEBUG removido para reduzir verbosidade do console
            # print(f"DEBUG PlayerProcessor: Steam ID: {steam_id}, Nome: {player_name}, ID: {player_id}")
            
            # Verificar se é jogador novo ou existente
            existing_player = self.db_manager.get_player_by_steam_id(steam_id)
            # DEBUG removido para reduzir verbosidade do console
            # print(f"DEBUG PlayerProcessor: Jogador existente: {existing_player is not None}")
            
            if existing_player:
                # Jogador existente
                name_changed = existing_player['player_name'] != player_name
                
                # Atualizar atividade
                self.db_manager.update_player_activity(
                    steam_id, player_name, player_id, timestamp
                )
                
                # Registrar sessão ativa
                self.active_sessions[steam_id] = {
                    'login_time': timestamp,
                    'player_name': player_name,
                    'player_id': player_id
                }
                
                result = {
                    'is_new_player': False,
                    'name_changed': name_changed,
                    'old_name': existing_player['player_name'] if name_changed else None,
                    'new_name': player_name if name_changed else None,
                    'total_sessions': existing_player['total_sessions'] + 1,
                    'total_playtime': existing_player['total_playtime']
                }
                
                if name_changed:
                    print(f"MUDANCA {steam_id}: {existing_player['player_name']} -> {player_name}")
                else:
                    print(f"JOGADOR {steam_id}: {player_name} (retornando)")
                
            else:
                # Jogador novo
                self.db_manager.create_new_player(steam_id, player_name, player_id, timestamp)
                
                # Registrar sessão ativa
                self.active_sessions[steam_id] = {
                    'login_time': timestamp,
                    'player_name': player_name,
                    'player_id': player_id
                }
                
                result = {
                    'is_new_player': True,
                    'name_changed': False,
                    'old_name': None,
                    'new_name': player_name,
                    'total_sessions': 1,
                    'total_playtime': 0
                }
                
                print(f"NOVO {steam_id}: {player_name} (NOVO JOGADOR)")
                
                # Enviar notificação de novo jogador (só se ainda não foi enviada)
                try:
                    # Verificar se notificação já foi enviada
                    player = self.db_manager.get_player_by_steam_id(steam_id)
                    if player and player.get('notification_sent', 0) == 1:
                        print(f"INFO Notificação já enviada para {player_name}, pulando...")
                    else:
                        # Obter informações da Steam API (opcional)
                        steam_info = self._get_steam_player_info(steam_id)

                        # Se for um novo jogador com ban, alertar em canal separado
                        try:
                            vac_banned = bool(steam_info.get('vac_banned', False))
                            trade_ban_state = str(steam_info.get('trade_ban_state', 'None'))
                            has_trade_ban = trade_ban_state.lower() != 'none'
                            if vac_banned or has_trade_ban:
                                self._send_ban_alert(session_data, steam_info)
                        except Exception as e:
                            print(f"AVISO Erro ao processar alerta de ban: {e}")
                        
                        # Enviar notificação
                        success = self._send_new_player_notification(session_data, steam_info)
                        
                        # Marcar como enviada se sucesso
                        if success:
                            self.db_manager.mark_notification_sent(steam_id)
                            print(f"OK Notificação marcada como enviada para {player_name}")
                        else:
                            print(f"AVISO Falha ao enviar notificação para {player_name}")
                    
                except Exception as e:
                    print(f"AVISO Erro ao processar notificação de novo jogador: {e}")
                    # Continuar mesmo se a notificação falhar
            
            return result
            
        except Exception as e:
            print(f"ERRO Erro ao processar login: {e}")
            return {'error': str(e)}
    
    def process_logout(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processar logout de jogador"""
        try:
            steam_id = session_data['steam_id']
            player_name = session_data['player_name']
            timestamp = session_data['timestamp']
            
            # Verificar se há sessão ativa
            if steam_id in self.active_sessions:
                session_info = self.active_sessions[steam_id]
                login_time = session_info['login_time']
                
                # Calcular duração da sessão
                session_duration = int((timestamp - login_time).total_seconds())
                
                # Atualizar tempo de jogo do jogador
                self.db_manager.update_player_activity(
                    steam_id, player_name, session_info['player_id'], 
                    timestamp, session_duration
                )
                
                # Remover sessão ativa
                del self.active_sessions[steam_id]
                
                result = {
                    'session_duration': session_duration,
                    'login_time': login_time,
                    'logout_time': timestamp
                }
                
                print(f"LOGOUT {steam_id}: {player_name} - Sessão: {session_duration}s")
                
                return result
            else:
                print(f"AVISO Logout sem login correspondente: {steam_id}")
                return {'error': 'No active session found'}
                
        except Exception as e:
            print(f"ERRO Erro ao processar logout: {e}")
            return {'error': str(e)}
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """Obter sessões ativas"""
        return {
            'active_count': len(self.active_sessions),
            'sessions': [
                {
                    'steam_id': steam_id,
                    'player_name': info['player_name'],
                    'player_id': info['player_id'],
                    'login_time': info['login_time'],
                    'duration': int((datetime.now() - info['login_time']).total_seconds())
                }
                for steam_id, info in self.active_sessions.items()
            ]
        }
    
    def get_players_summary(self) -> Dict[str, Any]:
        """Obter resumo dos jogadores"""
        try:
            stats = self.db_manager.get_players_stats()
            active_sessions = self.get_active_sessions()
            
            return {
                'total_players': stats.get('total_players', 0),
                'new_players': stats.get('new_players', 0),
                'active_players': stats.get('active_players', 0),
                'online_now': active_sessions['active_count'],
                'top_players': stats.get('top_players', [])[:5],
                'active_sessions': active_sessions['sessions']
            }
            
        except Exception as e:
            print(f"ERRO Erro ao obter resumo dos jogadores: {e}")
            return {}
    
    def cleanup_inactive_sessions(self, timeout_hours: int = 24) -> int:
        """Limpar sessões inativas (timeout)"""
        try:
            current_time = datetime.now()
            timeout_seconds = timeout_hours * 3600
            cleaned_count = 0
            
            inactive_sessions = []
            for steam_id, session_info in self.active_sessions.items():
                session_age = (current_time - session_info['login_time']).total_seconds()
                if session_age > timeout_seconds:
                    inactive_sessions.append(steam_id)
            
            for steam_id in inactive_sessions:
                session_info = self.active_sessions[steam_id]
                print(f"LIMPEZA Limpando sessão inativa: {steam_id} ({session_info['player_name']})")
                del self.active_sessions[steam_id]
                cleaned_count += 1
            
            return cleaned_count
            
        except Exception as e:
            print(f"ERRO Erro ao limpar sessões inativas: {e}")
            return 0
