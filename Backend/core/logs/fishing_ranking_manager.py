#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Ranking de Pescadores - SCUM Server Manager
Extrai dados de pesca do SCUM.db e gera rankings para Discord
"""

import sqlite3
import os
import json
import requests
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from core.database.connector import DatabaseConnector
import logging

logger = logging.getLogger(__name__)

class FishingDataExtractor:
    """Extrator de dados de pesca do banco SCUM.db"""
    
    def __init__(self, scum_db_path: str, ssm_db_path: Optional[str] = None):
        self.scum_db_path = scum_db_path
        self.ssm_db_path = ssm_db_path
        
    def extract_fishing_data(self) -> Dict:
        """Extrai todos os dados de pesca do SCUM.db"""
        
        if not os.path.exists(self.scum_db_path):
            raise FileNotFoundError(f"Banco SCUM.db não encontrado: {self.scum_db_path}")
        
        try:
            from utils.scum_db_helper import scum_db_readonly_connection_strict

            with scum_db_readonly_connection_strict(self.scum_db_path) as conn:
                cursor = conn.cursor()
                
                # 1. Estatísticas gerais
                stats = self._get_general_stats(cursor)
                
                # 2. Todos os pescadores (para salvar no banco)
                all_fishers = self._get_all_fishers(cursor)
                
                # 3. Top pescadores (para exibição no Discord)
                top_fishers = self._get_top_fishers(cursor)
                
                # 4. Ranking por espécie
                species_rankings = self._get_species_rankings(cursor)
                
                # 5. Recordes especiais
                records = self._get_special_records(cursor)
                
                # 6. Análise de dados
                analysis = self._get_data_analysis(cursor, stats, top_fishers)
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'general_stats': stats,
                    'all_fishers': all_fishers,  # Todos os jogadores para salvar no banco
                    'top_fishers': top_fishers,  # Top 20 para exibição
                    'species_rankings': species_rankings,
                    'special_records': records,
                    'data_analysis': analysis
                }
                
        except Exception as e:
            logger.error(f"Erro ao extrair dados de pesca: {e}")
            raise
    
    def _get_general_stats(self, cursor) -> Dict:
        """Obtém estatísticas gerais do servidor"""
        
        # Total de jogadores
        cursor.execute("SELECT COUNT(*) FROM user_profile")
        total_players = cursor.fetchone()[0]
        
        # Jogadores que pescaram
        cursor.execute("""
            SELECT COUNT(DISTINCT user_profile_id) 
            FROM fishing_stats 
            WHERE fish_caught > 0
        """)
        active_fishers = cursor.fetchone()[0]
        
        # Total de peixes capturados
        cursor.execute("SELECT SUM(fish_caught) FROM fishing_stats")
        total_fish = cursor.fetchone()[0] or 0
        
        # Temperatura da água (consultada do SSM.db se disponível)
        water_temp = 24.4
        try:
            if self.ssm_db_path and os.path.exists(self.ssm_db_path):
                with DatabaseConnector.get_connection(self.ssm_db_path, timeout=5.0) as ssm_conn:
                    ssm_cur = ssm_conn.cursor()
                    ssm_cur.execute("SELECT water_temperature FROM weather_parameters ORDER BY sync_timestamp DESC LIMIT 1")
                    row = ssm_cur.fetchone()
                    if row and row[0] is not None:
                        water_temp = float(row[0])
        except Exception:
            water_temp = 24.4
        
        fishing_percentage = round((active_fishers / total_players) * 100, 1) if total_players > 0 else 0
        
        return {
            'total_players': total_players,
            'active_fishers': active_fishers,
            'never_fished': total_players - active_fishers,
            'total_fish_caught': total_fish,
            'water_temperature': water_temp,
            'fishing_percentage': fishing_percentage
        }

    
    def _get_top_fishers(self, cursor) -> List[Dict]:
        """Obtém top pescadores"""
        
        cursor.execute("""
            SELECT up.user_id, up.name, fs.fish_caught, fs.fish_kept, fs.fish_released, 
                   fs.lines_broken, fs.heaviest_fish_caught, fs.longest_fish_caught
            FROM user_profile up
            JOIN fishing_stats fs ON up.id = fs.user_profile_id
            WHERE fs.fish_caught > 0
            ORDER BY fs.fish_caught DESC
            LIMIT 20
        """)
        
        results = cursor.fetchall()
        top_fishers = []
        
        for i, row in enumerate(results, 1):
            top_fishers.append({
                'position': i,
                'steam_id': str(row[0]) if row[0] else None,
                'name': row[1],
                'fish_caught': row[2],
                'fish_kept': row[3],
                'fish_released': row[4],
                'lines_broken': row[5],
                'heaviest_fish': row[6] or 0,
                'longest_fish': row[7] or 0
            })
        
        return top_fishers
    
    def _get_all_fishers(self, cursor) -> List[Dict]:
        """Obtém todos os pescadores com dados completos para salvar no banco (todos os campos da fishing_stats)"""
        
        try:
            # Verificar se as tabelas existem
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profile'")
            if not cursor.fetchone():
                logger.error("Tabela user_profile não encontrada no SCUM.db")
                return []
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fishing_stats'")
            if not cursor.fetchone():
                logger.error("Tabela fishing_stats não encontrada no SCUM.db")
                return []
            
            # Verificar quantos registros existem na fishing_stats
            cursor.execute("SELECT COUNT(*) FROM fishing_stats WHERE fish_caught > 0")
            count = cursor.fetchone()[0]
            logger.info(f"Encontrados {count} registros na fishing_stats com fish_caught > 0")
            
            cursor.execute("""
                SELECT up.user_id, up.name, 
                       fs.fish_caught, fs.fish_kept, fs.fish_released, 
                       fs.lines_broken, fs.heaviest_fish_caught, fs.longest_fish_caught,
                       fs.bass_caught, fs.catfish_caught, fs.pike_caught, 
                       fs.carp_caught, fs.amur_caught, fs.bleak_caught,
                       fs.chub_caught, fs.ruffe_caught, fs.prussian_carp_caught,
                       fs.crucian_carp_caught, fs.sardine_caught, fs.dentex_caught,
                       fs.orata_caught, fs.tuna_caught
                FROM user_profile up
                JOIN fishing_stats fs ON up.id = fs.user_profile_id
                WHERE fs.fish_caught > 0
                ORDER BY fs.fish_caught DESC
            """)
            
            results = cursor.fetchall()
            all_fishers = []
            
            logger.info(f"Query retornou {len(results)} linhas")
            
            for row in results:
                all_fishers.append({
                    'steam_id': str(row[0]) if row[0] else None,
                    'player_name': row[1],
                    'fish_caught': row[2],
                    'fish_kept': row[3],
                    'fish_released': row[4],
                    'lines_broken': row[5],
                    'heaviest_fish_caught': row[6] or 0,
                    'longest_fish_caught': row[7] or 0,
                    'bass_caught': row[8] or 0,
                    'catfish_caught': row[9] or 0,
                    'pike_caught': row[10] or 0,
                    'carp_caught': row[11] or 0,
                    'amur_caught': row[12] or 0,
                    'bleak_caught': row[13] or 0,
                    'chub_caught': row[14] or 0,
                    'ruffe_caught': row[15] or 0,
                    'prussian_carp_caught': row[16] or 0,
                    'crucian_carp_caught': row[17] or 0,
                    'sardine_caught': row[18] or 0,
                    'dentex_caught': row[19] or 0,
                    'orata_caught': row[20] or 0,
                    'tuna_caught': row[21] or 0
                })
            
            logger.info(f"Processados {len(all_fishers)} pescadores para salvar no banco")
            return all_fishers
            
        except Exception as e:
            logger.error(f"Erro ao obter pescadores do SCUM.db: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _get_species_rankings(self, cursor) -> Dict:
        """Obtém rankings por espécie"""
        
        species_data = {}
        species_columns = ['bass_caught', 'catfish_caught', 'pike_caught', 'carp_caught', 'tuna_caught']
        species_names = ['Bass', 'Catfish', 'Pike', 'Carp', 'Tuna']
        
        for col, name in zip(species_columns, species_names):
            cursor.execute(f"""
                SELECT up.user_id, up.name, fs.{col}, fs.heaviest_fish_caught, fs.longest_fish_caught
                FROM user_profile up
                JOIN fishing_stats fs ON up.id = fs.user_profile_id
                WHERE fs.{col} > 0
                ORDER BY fs.{col} DESC
                LIMIT 3
            """)
            
            results = cursor.fetchall()
            species_data[name] = []
            
            for i, row in enumerate(results, 1):
                species_data[name].append({
                    'position': i,
                    'steam_id': str(row[0]) if row[0] else None,
                    'name': row[1],
                    'count': row[2],
                    'heaviest': row[3] or 0,
                    'longest': row[4] or 0
                })
        
        return species_data
    
    def _get_special_records(self, cursor) -> Dict:
        """Obtém recordes especiais"""
        
        # Peixe mais pesado
        cursor.execute("""
            SELECT up.name, fs.heaviest_fish_caught, fs.longest_fish_caught
            FROM user_profile up
            JOIN fishing_stats fs ON up.id = fs.user_profile_id
            WHERE fs.heaviest_fish_caught > 0
            ORDER BY fs.heaviest_fish_caught DESC
            LIMIT 1
        """)
        heaviest_result = cursor.fetchone()
        
        # Peixe mais longo
        cursor.execute("""
            SELECT up.name, fs.longest_fish_caught, fs.heaviest_fish_caught
            FROM user_profile up
            JOIN fishing_stats fs ON up.id = fs.user_profile_id
            WHERE fs.longest_fish_caught > 0
            ORDER BY fs.longest_fish_caught DESC
            LIMIT 1
        """)
        longest_result = cursor.fetchone()
        
        # Pescador mais eficiente
        cursor.execute("""
            SELECT up.name, fs.fish_caught, fs.lines_broken
            FROM user_profile up
            JOIN fishing_stats fs ON up.id = fs.user_profile_id
            WHERE fs.fish_caught > 0
            ORDER BY fs.lines_broken ASC, fs.fish_caught DESC
            LIMIT 1
        """)
        efficient_result = cursor.fetchone()
        
        # Pescador mais ativo
        cursor.execute("""
            SELECT up.name, fs.fish_caught, fs.fish_kept, fs.fish_released
            FROM user_profile up
            JOIN fishing_stats fs ON up.id = fs.user_profile_id
            ORDER BY fs.fish_caught DESC
            LIMIT 1
        """)
        active_result = cursor.fetchone()
        
        records = {}
        
        if heaviest_result:
            records['heaviest_fish'] = {
                'player': heaviest_result[0],
                'weight': heaviest_result[1],
                'length': heaviest_result[2]
            }
        
        if longest_result:
            records['longest_fish'] = {
                'player': longest_result[0],
                'length': longest_result[1],
                'weight': longest_result[2]
            }
        
        if efficient_result:
            records['most_efficient'] = {
                'player': efficient_result[0],
                'fish_caught': efficient_result[1],
                'lines_broken': efficient_result[2],
                'efficiency_rate': 100.0 if efficient_result[2] == 0 else round((efficient_result[1] / (efficient_result[2] + 1)) * 100, 1)
            }
        
        if active_result:
            records['most_active'] = {
                'player': active_result[0],
                'fish_caught': active_result[1],
                'fish_kept': active_result[2],
                'fish_released': active_result[3],
                'keep_rate': round((active_result[2] / active_result[1]) * 100, 1) if active_result[1] > 0 else 0
            }
        
        return records
    
    def _get_data_analysis(self, cursor, stats: Dict, top_fishers: List[Dict]) -> Dict:
        """Gera análise dos dados"""
        
        # Distribuição por espécie
        species_distribution = {}
        species_totals = {}
        
        species_columns = ['bass_caught', 'catfish_caught', 'pike_caught', 'carp_caught', 'tuna_caught']
        species_names = ['Bass', 'Catfish', 'Pike', 'Carp', 'Tuna']
        
        for col, name in zip(species_columns, species_names):
            cursor.execute(f"SELECT SUM({col}) FROM fishing_stats")
            total = cursor.fetchone()[0] or 0
            species_totals[name] = total
        
        total_species_fish = sum(species_totals.values())
        
        for name, total in species_totals.items():
            percentage = round((total / total_species_fish) * 100, 1) if total_species_fish > 0 else 0
            species_distribution[name] = {
                'count': total,
                'percentage': percentage
            }
        
        # Padrões de comportamento
        behavior_patterns = []
        
        if top_fishers:
            # Analisar padrões dos top pescadores
            for fisher in top_fishers[:5]:
                pattern = f"{fisher['name']}: "
                if fisher['lines_broken'] == 0:
                    pattern += "Perfect (0 broken lines)"
                elif fisher['lines_broken'] < fisher['fish_caught'] * 0.1:
                    pattern += "Very efficient"
                elif fisher['lines_broken'] > fisher['fish_caught'] * 0.5:
                    pattern += "Aggressive fishing (many broken lines)"
                else:
                    pattern += "Balanced fishing"
                
                behavior_patterns.append(pattern)
        
        # Estatísticas de eficiência
        if top_fishers:
            avg_lines_broken = sum(f['lines_broken'] for f in top_fishers) / len(top_fishers)
            avg_keep_rate = sum(f['fish_kept'] / f['fish_caught'] * 100 for f in top_fishers if f['fish_caught'] > 0) / len(top_fishers)
            
            efficiency_stats = {
                'avg_lines_broken_per_fish': round(avg_lines_broken / stats['total_fish_caught'], 2) if stats['total_fish_caught'] > 0 else 0,
                'avg_keep_rate': round(avg_keep_rate, 1),
                'most_efficient_player': min(top_fishers, key=lambda x: x['lines_broken'])['name'] if top_fishers else "N/A"
            }
        else:
            efficiency_stats = {
                'avg_lines_broken_per_fish': 0,
                'avg_keep_rate': 0,
                'most_efficient_player': "N/A"
            }
        
        return {
            'species_distribution': species_distribution,
            'behavior_patterns': behavior_patterns,
            'efficiency_stats': efficiency_stats
        }

class FishingRankingGenerator:
    """Gerador de rankings de pesca"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.timestamp = datetime.fromisoformat(data['timestamp'])
    
    def generate_ranking_embeds(self) -> List[Dict]:
        """Gera os embeds do ranking para envio ao Discord"""
        
        embeds = []
        
        # Embed 1: TOP 10 PESCADORES MAIS ATIVOS
        embeds.append(self._generate_top10_embed())
        
        # Embed 2: RANKING POR ESPÉCIE DE PEIXE
        embeds.append(self._generate_species_embed())
        
        return embeds
    
    def _generate_top10_embed(self) -> Dict:
        """Gera embed do TOP 10 PESCADORES MAIS ATIVOS"""
        
        top_fishers = self.data['top_fishers'][:10]  # Top 10 apenas
        stats = self.data['general_stats']
        
        # Construir tabela de ranking
        if not top_fishers:
            description = "🎣 *No fishing records yet. Cast your line and claim the #1 spot!*"
        else:
            lines = []
            lines.append("```")
            # Largura compacta para Discord (máximo ~50 caracteres para evitar quebra em mobile)
            header = f"{'Rank':<4} | {'Player':<18} | {'Fish':>5} | {'Weight':>7} | {'Length':>7}"
            lines.append(header)
            lines.append("-" * 50)
            
            # Linhas de dados
            for fisher in top_fishers:
                player_name = fisher['name'][:18].strip()
                fish_caught = fisher['fish_caught']
                heaviest = fisher['heaviest_fish']
                longest = fisher['longest_fish']
                
                pos_str = f"#{fisher['position']}"
                row = f"{pos_str:<4} | {player_name:<18} | {fish_caught:>5} | {heaviest:>5.1f}kg | {longest:>5.1f}cm"
                lines.append(row)
            
            lines.append("```")
            description = "\n".join(lines)
        
        # Criar embed
        embed = {
            "title": "🎣 TOP 10 MOST ACTIVE FISHERMEN",
            "description": description,
            "color": 0x3498db,  # Azul (cor temática de pesca)
            "fields": [
                {
                    "name": "📊 General Statistics",
                    "value": f"• **Total Fish Caught:** {stats['total_fish_caught']}\n"
                            f"• **Active Fishermen:** {stats['active_fishers']} ({stats['fishing_percentage']}%)\n"
                            f"• **Water Temperature:** 🌊 {stats['water_temperature']:.1f}°C",
                    "inline": False
                }
            ],
            "footer": {
                "text": "🔄 Updated every 15m • SSM Fishing Records"
            }
        }
        
        return embed
    
    def _generate_species_embed(self) -> Dict:
        """Gera embed do RANKING POR ESPÉCIE DE PEIXE (TOP 3 por espécie)"""
        
        species_rankings = self.data['species_rankings']
        
        has_any_species = any(bool(rankings) for rankings in (species_rankings or {}).values())
        
        # Construir descrição com rankings por espécie
        if not has_any_species:
            description = "🐟 *No species catches recorded yet.*"
        else:
            lines = []
            lines.append("```")
            
            for species_name, rankings in species_rankings.items():
                if rankings:
                    lines.append(f"\n[{species_name.upper()}]")
                    lines.append(f"{'Pos':<4} | {'Player':<18} | {'Qty':>4} | {'Weight':>7} | {'Length':>7}")
                    lines.append("-" * 50)
                    
                    for ranking in rankings[:3]:  # TOP 3 por espécie
                        player_name = ranking['name'][:18].strip()
                        pos_str = f"#{ranking['position']}"
                        row = f"{pos_str:<4} | {player_name:<18} | {ranking['count']:>4} | {ranking['heaviest']:>5.1f}kg | {ranking['longest']:>5.1f}cm"
                        lines.append(row)
            
            lines.append("```")
            description = "\n".join(lines)
        
        # Criar embed
        embed = {
            "title": "🐟 SPECIES RECORD HOLDERS (TOP 3)",
            "description": description,
            "color": 0x1abc9c,  # Verde-água (cor temática de peixe)
            "footer": {
                "text": "Top 3 per species • SSM Backend"
            }
        }
        
        return embed


class FishingRankingNotifier:
    """Notificador de rankings via Discord com suporte a PATCH (Live Dashboard sem spam)"""
    
    def __init__(self, webhook_url: str, webhooks_path: str = "data/webhooks.json"):
        self.webhook_url = webhook_url
        self.webhooks_path = webhooks_path
    
    def send_ranking_embeds(self, embeds: List[Dict]) -> bool:
        """Envia ou edita os embeds do ranking no Discord com suporte a PATCH"""
        try:
            if not embeds:
                logger.warning("Nenhum embed para enviar")
                return False
            
            payload = {
                "embeds": embeds
            }
            
            # Carregar WebhooksManager se disponível
            mgr = None
            event_state = {}
            target_event = "fishing_ranking"
            try:
                from core.webhooks.manager import WebhooksManager
                if os.path.exists(self.webhooks_path):
                    mgr = WebhooksManager(self.webhooks_path)
                    v2 = mgr.load_v2()
                    event_state = (
                        ((v2 or {}).get("events") or {})
                        .get(target_event, {})
                        .get("state", {})
                    )
                    if not isinstance(event_state, dict):
                        event_state = {}
            except Exception as e:
                logger.debug(f"Não foi possível carregar WebhooksManager: {e}")

            # Calcular assinatura SHA1 para evitar chamadas de rede sem alterações
            signature = hashlib.sha1(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()

            try:
                last_sig = str(event_state.get("last_signature") or "")
                if last_sig and last_sig == signature:
                    logger.debug("Nenhuma alteração nos dados do ranking de pesca (assinatura idêntica)")
                    return True
            except Exception:
                pass

            # Extrair id e token do webhook
            parsed = None
            try:
                parts = str(self.webhook_url).split("/api/webhooks/")
                if len(parts) == 2:
                    tail = parts[1].strip("/")
                    segs = tail.split("/")
                    if len(segs) >= 2:
                        parsed = {"id": segs[0], "token": segs[1]}
            except Exception:
                parsed = None

            message_id = ""
            try:
                mid = event_state.get("last_message_id")
                message_id = str(mid).strip() if mid else ""
            except Exception:
                message_id = ""

            # 1. Tentar PATCH se já houver mensagem salva
            if parsed and message_id:
                try:
                    patch_url = f"https://discord.com/api/webhooks/{parsed['id']}/{parsed['token']}/messages/{message_id}"
                    r = requests.patch(
                        patch_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=12,
                    )
                    if r.status_code in (200, 204):
                        if mgr:
                            try:
                                mgr.patch_event_state(
                                    target_event,
                                    {
                                        "last_updated_at": datetime.now().isoformat(),
                                        "last_signature": signature,
                                    },
                                    create_backup=False,
                                )
                            except Exception:
                                pass
                        logger.info(f"Fishing Ranking atualizado via PATCH no Discord (msg {message_id})")
                        return True
                    elif r.status_code == 404:
                        logger.info("Mensagem anterior do Fishing Ranking não encontrada (404). Criando nova mensagem fixa...")
                        message_id = ""
                    else:
                        logger.warning(f"Erro ao editar mensagem de fishing ranking (HTTP {r.status_code}): {r.text}")
                except Exception as e:
                    logger.warning(f"Exceção ao tentar PATCH de fishing ranking: {e}")

            # 2. Criar nova mensagem (POST ?wait=true)
            max_retries = 3
            retry_delay = 1
            for attempt in range(max_retries):
                try:
                    if parsed:
                        post_url = f"https://discord.com/api/webhooks/{parsed['id']}/{parsed['token']}?wait=true"
                    else:
                        post_url = str(self.webhook_url)
                        if "?wait=true" not in post_url:
                            sep = "&" if "?" in post_url else "?"
                            post_url = f"{post_url}{sep}wait=true"

                    response = requests.post(post_url, json=payload, timeout=12)
                    if response.status_code in (200, 204):
                        new_msg_id = ""
                        try:
                            data = response.json()
                            new_msg_id = str(data.get("id") or "").strip()
                        except Exception:
                            pass

                        if mgr and new_msg_id:
                            try:
                                mgr.patch_event_state(
                                    target_event,
                                    {
                                        "last_message_id": new_msg_id,
                                        "last_updated_at": datetime.now().isoformat(),
                                        "last_signature": signature,
                                    },
                                    create_backup=False,
                                )
                            except Exception:
                                pass
                        logger.info(f"Nova mensagem fixa de Fishing Ranking criada no Discord (msg {new_msg_id})")
                        return True
                    elif response.status_code == 429:
                        try:
                            error_data = response.json()
                            retry_after = error_data.get('retry_after', retry_delay)
                            logger.warning(f"Rate limit atingido, aguardando {retry_after:.2f}s...")
                            time.sleep(retry_after)
                            continue
                        except Exception:
                            time.sleep(retry_delay)
                            continue
                    else:
                        logger.error(f"Erro ao enviar ranking (HTTP {response.status_code}): {response.text}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        return False
                except requests.exceptions.Timeout:
                    logger.error("Timeout ao enviar ranking para Discord")
                    return False
                except requests.exceptions.RequestException as e:
                    logger.error(f"Erro de rede ao enviar ranking: {e}")
                    return False
                except Exception as e:
                    logger.error(f"Erro ao enviar ranking para Discord: {e}")
                    return False

            return False
        except Exception as e:
            logger.error(f"Erro inesperado no notificador de fishing ranking: {e}")
            return False


class FishingRankingManager:
    """Gerenciador principal do sistema de ranking de pesca"""
    
    def __init__(self, config: Dict, path_helper=None):
        self.config = config
        self.path_helper = path_helper
        
        # Obter caminho do SSM.db usando path_helper ou fallback
        if path_helper:
            self.ssm_db_path = path_helper.get_ssm_db_path()
            try:
                self.webhooks_path = path_helper.get_application_path(
                    "webhooks_file", "data/webhooks.json"
                )
            except Exception:
                self.webhooks_path = "data/webhooks.json"
        else:
            self.ssm_db_path = config.get('ssm_db_path', 'data/SSM.db')
            self.webhooks_path = "data/webhooks.json"

        self.extractor = FishingDataExtractor(config['scum_db_path'], self.ssm_db_path)
        self.webhook_url = config.get('webhook_url')
        
        if not self.webhook_url:
            raise ValueError("Webhook URL não configurado")
    
    def generate_daily_ranking(self) -> bool:
        """Gera e sincroniza o ranking de pesca (Live Dashboard)"""
        try:
            logger.info("Extraindo dados de pesca do SCUM.db...")
            data = self.extractor.extract_fishing_data()
            
            stats = data.get('general_stats', {})
            all_fishers = data.get('all_fishers', [])
            logger.info(f"Dados extraídos: {stats.get('total_players', 0)} jogadores, {stats.get('active_fishers', 0)} pescadores")
            
            generator = FishingRankingGenerator(data)
            embeds = generator.generate_ranking_embeds()
            
            logger.info("Sincronizando ranking de pesca no Discord...")
            notifier = FishingRankingNotifier(self.webhook_url, self.webhooks_path)
            success = notifier.send_ranking_embeds(embeds)
            
            if success:
                logger.info("Ranking de pesca sincronizado com sucesso!")
                # Salvar no banco SSM.db se houver registros
                if all_fishers:
                    self.save_ranking_to_db(data)
                return True
            else:
                logger.error("Erro ao sincronizar ranking de pesca para Discord")
                return False
                
        except FileNotFoundError as e:
            logger.error(f"Erro: Banco SCUM.db não encontrado: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro na sincronização do ranking de pesca: {e}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            return False

    
    def save_ranking_to_db(self, data: Dict) -> bool:
        """Salva o ranking no banco SSM.db (uma linha por jogador, INSERT OR REPLACE)"""
        
        try:
            db_path = self.ssm_db_path
            
            with DatabaseConnector.get_connection(db_path, write_mode=True) as conn:
                cursor = conn.cursor()
                
                # Garantir que a tabela existe (criar se necessário)
                self._ensure_table_exists(conn, cursor)
                
                # Obter todos os jogadores com dados de pesca
                all_fishers = data.get('all_fishers', [])
                
                logger.info(f"Preparando para salvar {len(all_fishers)} pescadores no banco SSM.db")
                
                if not all_fishers:
                    logger.warning("Nenhum jogador com dados de pesca para salvar (all_fishers está vazio)")
                    logger.warning("Isso pode acontecer se:")
                    logger.warning("  1. O SCUM.db não tem dados de pesca (nenhum jogador com fish_caught > 0)")
                    logger.warning("  2. A tabela fishing_stats está vazia no SCUM.db")
                    logger.warning("  3. O caminho do SCUM.db está incorreto")
                    return False
                
                # Inserir ou atualizar cada jogador
                processed = 0
                
                for fisher in all_fishers:
                    if not fisher.get('steam_id'):
                        logger.warning(f"Jogador {fisher.get('player_name')} sem steam_id, pulando...")
                        continue
                    
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO fishing_rankings (
                                steam_id, player_name,
                                fish_caught, fish_kept, fish_released, lines_broken,
                                heaviest_fish_caught, longest_fish_caught,
                                bass_caught, catfish_caught, pike_caught, carp_caught,
                                amur_caught, bleak_caught, chub_caught, ruffe_caught,
                                prussian_carp_caught, crucian_carp_caught, sardine_caught,
                                dentex_caught, orata_caught, tuna_caught,
                                last_updated
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            fisher['steam_id'],
                            fisher['player_name'],
                            fisher['fish_caught'],
                            fisher['fish_kept'],
                            fisher['fish_released'],
                            fisher['lines_broken'],
                            fisher['heaviest_fish_caught'],
                            fisher['longest_fish_caught'],
                            fisher['bass_caught'],
                            fisher['catfish_caught'],
                            fisher['pike_caught'],
                            fisher['carp_caught'],
                            fisher['amur_caught'],
                            fisher['bleak_caught'],
                            fisher['chub_caught'],
                            fisher['ruffe_caught'],
                            fisher['prussian_carp_caught'],
                            fisher['crucian_carp_caught'],
                            fisher['sardine_caught'],
                            fisher['dentex_caught'],
                            fisher['orata_caught'],
                            fisher['tuna_caught'],
                            datetime.now().isoformat()
                        ))
                        
                        # INSERT OR REPLACE sempre funciona
                        processed += 1
                            
                    except Exception as e:
                        logger.error(f"Erro ao salvar jogador {fisher.get('player_name')}: {e}")
                        continue
                
                conn.commit()
                logger.info(f"Ranking salvo no banco SSM.db: {processed} jogadores processados (INSERT OR REPLACE)")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao salvar ranking no banco: {e}")
            return False
    
    def _ensure_table_exists(self, conn, cursor):
        """Garante que a tabela fishing_rankings existe, criando se necessário"""
        try:
            # Verificar se a tabela já existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fishing_rankings'")
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                logger.info("Criando tabela fishing_rankings...")
            else:
                logger.debug("Tabela fishing_rankings já existe")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fishing_rankings (
                    steam_id TEXT PRIMARY KEY,
                    player_name TEXT NOT NULL,
                    
                    -- Estatísticas gerais
                    fish_caught INTEGER DEFAULT 0,
                    fish_kept INTEGER DEFAULT 0,
                    fish_released INTEGER DEFAULT 0,
                    lines_broken INTEGER DEFAULT 0,
                    
                    -- Recordes
                    heaviest_fish_caught REAL DEFAULT 0,
                    longest_fish_caught REAL DEFAULT 0,
                    
                    -- Por espécie (todos os campos da fishing_stats)
                    bass_caught INTEGER DEFAULT 0,
                    catfish_caught INTEGER DEFAULT 0,
                    pike_caught INTEGER DEFAULT 0,
                    carp_caught INTEGER DEFAULT 0,
                    amur_caught INTEGER DEFAULT 0,
                    bleak_caught INTEGER DEFAULT 0,
                    chub_caught INTEGER DEFAULT 0,
                    ruffe_caught INTEGER DEFAULT 0,
                    prussian_carp_caught INTEGER DEFAULT 0,
                    crucian_carp_caught INTEGER DEFAULT 0,
                    sardine_caught INTEGER DEFAULT 0,
                    dentex_caught INTEGER DEFAULT 0,
                    orata_caught INTEGER DEFAULT 0,
                    tuna_caught INTEGER DEFAULT 0,
                    
                    -- Metadata
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Criar índices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fishing_rankings_steam_id ON fishing_rankings(steam_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fishing_rankings_fish_caught ON fishing_rankings(fish_caught DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fishing_rankings_last_updated ON fishing_rankings(last_updated DESC)")
            
            conn.commit()
            if not table_exists:
                logger.info("Tabela fishing_rankings criada com sucesso")
            else:
                logger.debug("Tabela fishing_rankings verificada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao garantir existência da tabela fishing_rankings: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise