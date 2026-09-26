"""
Processador de Veículos do SCUM
Integra dados de chest ownership com informações do banco SCUM.db
"""

import sqlite3
import os
import json
import re
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from .chest_ownership_parser import ChestOwnershipParser
from utils.scum_db_helper import scum_db_readonly_connection

class VehicleProcessor:
    def __init__(self, scum_db_path: str = None):
        # Determinar caminho do banco SCUM.db
        if scum_db_path is None:
            # Tentar caminhos comuns
            possible_paths = [
                "C:/Servers/scum/SCUM/Saved/SaveFiles/SCUM.db",
                "C:/Servers/Scum/SCUM/Saved/SaveFiles/SCUM.db",
                "SCUM.db"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    scum_db_path = path
                    break
            
            if not scum_db_path:
                raise FileNotFoundError("Banco SCUM.db não encontrado nos caminhos padrão")
        
        self.scum_db_path = scum_db_path
        self.parser = ChestOwnershipParser()
        
        # Cache para mapeamento de veículos
        self.vehicle_cache = {}
        
        # Caminhos para mapeamento de imagens (nova pasta dedicada vehicle/)
        self.images_path = "data/imagens/vehicle"
        self.mapping_path = os.path.join(self.images_path, "mapping.json")
        
        # Lock para thread-safety ao escrever no JSON
        self.mapping_lock = threading.Lock()
        
        # Carregar mapeamento de imagens
        self.vehicle_image_mapping = self._load_vehicle_image_mapping()
        
        # Log sanitizado (não expor caminho completo)
        print("VehicleProcessor inicializado")
    
    def map_containers_to_vehicles(self, container_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Mapear container IDs para dados de veículos usando SCUM.db"""
        if not container_ids:
            return {}
        
        result = {}
        batch_size = 400
        
        try:
            # Conectar ao banco SCUM.db usando helper read-only
            with scum_db_readonly_connection(self.scum_db_path) as conn:
                conn.execute("PRAGMA busy_timeout = 8000")
                cursor = conn.cursor()
                
                # Processar em lotes para evitar problemas de memória
                for i in range(0, len(container_ids), batch_size):
                    batch = container_ids[i:i + batch_size]
                    placeholders = ','.join(['?' for _ in batch])
                    
                    # Query em lote para mapear containers para veículos
                    # Buscar recursivamente o veículo real (que está em vehicle_spawner)
                    query = f"""
                    WITH RECURSIVE container_hierarchy AS (
                        -- Caso base: o próprio entity_id pode ser o veículo OU um container filho do veículo
                        SELECT
                            e.id AS container_id,
                            e.id AS current_entity_id,
                            e.parent_entity_id AS parent_id,
                            0 AS depth
                        FROM entity e
                        WHERE e.id IN ({placeholders})

                        UNION ALL

                        -- Subir na hierarquia: current_entity_id vira o parent atual
                        SELECT
                            ch.container_id AS container_id,
                            e.id AS current_entity_id,
                            e.parent_entity_id AS parent_id,
                            ch.depth + 1 AS depth
                        FROM entity e
                        INNER JOIN container_hierarchy ch ON ch.parent_id = e.id
                        WHERE ch.depth < 12  -- Limitar profundidade (veículos + expansões podem ter cadeia maior)
                    ),
                    vehicle_candidates AS (
                        -- Candidatos onde o current_entity_id é um veículo real (existe em vehicle_spawner)
                        SELECT
                            ch.container_id,
                            ch.current_entity_id AS vehicle_id,
                            ch.depth
                        FROM container_hierarchy ch
                        INNER JOIN vehicle_spawner vs ON vs.vehicle_entity_id = ch.current_entity_id
                    ),
                    min_depth_per_container AS (
                        SELECT container_id, MIN(depth) AS min_depth
                        FROM vehicle_candidates
                        GROUP BY container_id
                    ),
                    vehicle_containers AS (
                        SELECT vc.container_id, vc.vehicle_id, md.min_depth AS depth
                        FROM vehicle_candidates vc
                        INNER JOIN min_depth_per_container md
                            ON md.container_id = vc.container_id
                           AND md.min_depth = vc.depth
                    )
                    SELECT DISTINCT
                        e.id as container_id,
                        e.class as container_class,
                        vc.vehicle_id,
                        vc.depth as vehicle_container_depth,
                        v.class as vehicle_class,
                        vs.vehicle_asset_id,
                        vs.is_vehicle_functional
                    FROM entity e
                    INNER JOIN vehicle_containers vc ON vc.container_id = e.id
                    LEFT JOIN entity v ON v.id = vc.vehicle_id
                    LEFT JOIN vehicle_spawner vs ON vs.vehicle_entity_id = vc.vehicle_id
                    WHERE e.id IN ({placeholders})
                    """
                    
                    cursor.execute(query, batch + batch)
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        container_id, container_class, vehicle_id, vehicle_container_depth, vehicle_class, vehicle_asset_id, is_vehicle_functional = row
                        
                        result[container_id] = {
                            'container_class': container_class,
                            'vehicle_entity_id': vehicle_id,
                            'vehicle_container_depth': int(vehicle_container_depth) if vehicle_container_depth is not None else None,
                            'vehicle_class': vehicle_class,
                            'vehicle_asset_id': vehicle_asset_id,
                            'is_vehicle_functional': bool(is_vehicle_functional) if is_vehicle_functional is not None else None
                        }
                        
                        # Atualizar cache
                        self.vehicle_cache[container_id] = result[container_id]
                
                print(f"OK Mapeamento de veículos concluído: {len(result)} containers mapeados")
                
        except sqlite3.Error as e:
            print(f"ERRO Erro ao consultar banco SCUM.db: {e}")
        except Exception as e:
            print(f"ERRO Erro inesperado no mapeamento de veículos: {e}")
        
        return result
    
    def process_ownership_claims(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processar claims de ownership e enriquecer com dados de veículos"""
        if not claims:
            return []
        
        # Extrair container IDs únicos
        container_ids = list(set([claim['entity_id'] for claim in claims]))
        
        # Mapear containers para veículos
        vehicle_mapping = self.map_containers_to_vehicles(container_ids)
        
        # Enriquecer claims com dados de veículos
        enriched_claims = []
        
        for claim in claims:
            entity_id = claim['entity_id']
            ownership_type = claim.get('ownership_type', 'claimed')
            vehicle_data = vehicle_mapping.get(entity_id, {})
            
            # Log específico para transferências
            is_transfer = ownership_type == 'changed'
            if is_transfer:
                previous_owner = claim.get('previous_owner_name', 'Unknown')
                new_owner = claim.get('player_name', 'Unknown')
                print(f"TRANSFERÊNCIA Processando: Entity ID {entity_id}")
                print(f"   De: {previous_owner} -> Para: {new_owner}")
            
            # Criar claim enriquecida
            enriched_claim = claim.copy()
            enriched_claim.update({
                'container_class': vehicle_data.get('container_class'),
                'vehicle_entity_id': vehicle_data.get('vehicle_entity_id'),
                'vehicle_container_depth': vehicle_data.get('vehicle_container_depth'),
                'vehicle_class': vehicle_data.get('vehicle_class'),
                'vehicle_asset_id': vehicle_data.get('vehicle_asset_id'),
                'is_vehicle_functional': vehicle_data.get('is_vehicle_functional'),
                'is_vehicle': bool(vehicle_data.get('vehicle_entity_id')),  # Indica se é um veículo
                'processed_at': datetime.now()
            })
            
            # Log se vehicle_entity_id foi encontrado ou não
            if is_transfer:
                if enriched_claim.get('vehicle_entity_id'):
                    print(f"   OK Vehicle Entity ID encontrado: {enriched_claim['vehicle_entity_id']} ({enriched_claim.get('vehicle_class', 'Unknown')})")
                else:
                    print(f"   AVISO: Vehicle Entity ID NÃO encontrado para Entity ID {entity_id} - pode ser container não vinculado a veículo")
            
            enriched_claims.append(enriched_claim)
        
        # Filtrar apenas claims que são veículos
        # Ignorar containers secundários de veículos (inventário expandido)
        secondary_containers = [
            'Big_Inventory_Expansion_Item_Container_ES',
            'Small_Inventory_Expansion_Item_Container_ES',
            'Medium_Inventory_Expansion_Item_Container_ES',
            'Big_Vehicle_StorageRack_ES',
            'Small_Vehicle_StorageRack_ES', 
            'Medium_Vehicle_StorageRack_ES'
        ]
        
        vehicle_claims = [claim for claim in enriched_claims if claim['is_vehicle']]
        
        # Deduplicar por vehicle_entity_id (evitar múltiplos containers do mesmo veículo)
        # Preferir container não-secundário quando houver múltiplas opções.
        deduplicated_claims = []
        best_by_vehicle = {}
        
        def _is_secondary_container(container_class: Optional[str]) -> bool:
            return bool(container_class) and container_class in secondary_containers
        
        for claim in vehicle_claims:
            vehicle_id = claim.get('vehicle_entity_id')
            if not vehicle_id:
                continue
            existing = best_by_vehicle.get(vehicle_id)
            if not existing:
                best_by_vehicle[vehicle_id] = claim
                continue

            existing_ts = existing.get('timestamp')
            current_ts = claim.get('timestamp')
            if isinstance(existing_ts, datetime) and isinstance(current_ts, datetime):
                if current_ts > existing_ts:
                    best_by_vehicle[vehicle_id] = claim
                    continue
                if current_ts < existing_ts:
                    continue

            existing_depth = existing.get('vehicle_container_depth')
            current_depth = claim.get('vehicle_container_depth')
            if isinstance(existing_depth, int) and isinstance(current_depth, int):
                if current_depth < existing_depth:
                    best_by_vehicle[vehicle_id] = claim
                    continue
                if current_depth > existing_depth:
                    continue

            existing_secondary = _is_secondary_container(existing.get('container_class'))
            current_secondary = _is_secondary_container(claim.get('container_class'))
            if existing_secondary and not current_secondary:
                best_by_vehicle[vehicle_id] = claim
        
        for claim in best_by_vehicle.values():
            deduplicated_claims.append(claim)
        
        print(f"OK Claims processadas: {len(enriched_claims)} total, {len(vehicle_claims)} veículos, {len(deduplicated_claims)} deduplicados")
        
        return deduplicated_claims
    
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parsear arquivo e processar claims de veículos"""
        try:
            # Parsear arquivo
            claims = self.parser.parse_file(file_path)
            
            if not claims:
                return []
            
            # Processar claims
            vehicle_claims = self.process_ownership_claims(claims)
            
            return vehicle_claims
            
        except Exception as e:
            print(f"ERRO Erro ao processar arquivo de veículos: {e}")
            return []
    
    def parse_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Parsear linhas e processar claims de veículos"""
        try:
            # Parsear linhas
            claims = self.parser.parse_lines(lines)
            
            if not claims:
                return []
            
            # Processar claims
            vehicle_claims = self.process_ownership_claims(claims)
            
            return vehicle_claims
            
        except Exception as e:
            print(f"ERRO Erro ao processar linhas de veículos: {e}")
            return []
    
    def _load_vehicle_image_mapping(self) -> Dict[str, str]:
        """Carregar mapeamento de imagens de veículos do JSON"""
        try:
            if os.path.exists(self.mapping_path):
                with open(self.mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                    print(f"OK Mapeamento de imagens de veículos carregado: {len(mapping)} veículos")
                    return mapping
            else:
                # Criar arquivo vazio se não existir
                print("AVISO Arquivo mapping.json não encontrado, criando novo")
                empty_mapping = {}
                self._save_vehicle_image_mapping(empty_mapping)
                return empty_mapping
        except Exception as e:
            print(f"ERRO Erro ao carregar mapeamento de imagens de veículos: {e}")
            return {}
    
    def _save_vehicle_image_mapping(self, mapping: Dict[str, str]) -> bool:
        """Salvar mapeamento de imagens de veículos no JSON com ordenação alfabética"""
        try:
            # Ordenar alfabeticamente por chave
            sorted_mapping = dict(sorted(mapping.items()))
            
            # Garantir que o diretório existe
            os.makedirs(os.path.dirname(self.mapping_path), exist_ok=True)
            
            with open(self.mapping_path, 'w', encoding='utf-8') as f:
                json.dump(sorted_mapping, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"ERRO Erro ao salvar mapeamento de imagens de veículos: {e}")
            return False
    
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
    
    def _add_vehicle_to_mapping(self, normalized_name: str) -> None:
        """Adicionar novo veículo ao mapeamento com valor vazio (thread-safe)"""
        if not normalized_name:
            return
        
        with self.mapping_lock:
            # Verificar se já existe
            if normalized_name not in self.vehicle_image_mapping:
                # Adicionar com valor vazio
                self.vehicle_image_mapping[normalized_name] = ""
                self._save_vehicle_image_mapping(self.vehicle_image_mapping)
                print(f"INFO Novo veículo descoberto e adicionado ao mapping: {normalized_name}")
    
    def get_vehicle_image_mapping(self, vehicle_class: str) -> str:
        """Mapear classe do veículo para arquivo de imagem usando JSON"""
        if not vehicle_class:
            return 'BPC_Dirtbike.png'  # Imagem padrão
        
        # Normalizar nome do veículo usando normalização robusta
        normalized_name = self._normalize_vehicle_name(vehicle_class)
        
        # Primeiro, tentar correspondência exata
        image_filename = self.vehicle_image_mapping.get(normalized_name)
        
        if image_filename is not None:
            # Se está no mapeamento mas vazio, retornar padrão
            if not image_filename or image_filename.strip() == "":
                return 'BPC_Dirtbike.png'
            # Se tem valor, retornar o arquivo
            return image_filename
        
        # Se não está no mapeamento, tentar correspondência parcial
        for key, image in self.vehicle_image_mapping.items():
            if normalized_name.find(key) != -1 or key.find(normalized_name) != -1:
                if image and image.strip() != "":
                    print(f"DEBUG: Mapeamento encontrado: '{vehicle_class}' -> '{image}' (via '{key}')")
                    return image
        
        # Se não encontrar, adicionar ao mapeamento com valor vazio (auto-descoberta)
        self._add_vehicle_to_mapping(normalized_name)
        
        # Retornar padrão
        print(f"DEBUG: Nenhum mapeamento encontrado para '{vehicle_class}' (normalizado: '{normalized_name}') - adicionado ao mapping")
        return 'BPC_Dirtbike.png'
    
    def get_vehicle_display_name(self, vehicle_class: str) -> str:
        """Obter nome de exibição amigável para o veículo"""
        if not vehicle_class:
            return "Veículo Desconhecido"
        
        # Mapeamento de nomes amigáveis
        display_names = {
            'bpc_barba': 'Barba',
            'bpc_bigraft': 'Big Raft',
            'bpc_citybike': 'City Bike',
            'bpc_cruiser': 'Cruiser',
            'bpc_dirtbike': 'Dirtbike',
            'bpc_kinglet_duster': 'Kinglet Duster',
            'bpc_kinglet_mariner': 'Kinglet Mariner',
            'bpc_laika': 'Laika',
            'bpc_mountainbike': 'Mountain Bike',
            'bpc_rager': 'Rager',
            'bpc_ris': 'RIS',
            'bpc_smallraft': 'Small Raft',
            'bpc_sup': 'SUP',
            'bpc_tractor': 'Trator',
            'bpc_wolfswagen': 'Wolfswagen',
            'bp_wheelbarrow_imp': 'Carrinho de Mão Improvisado',
            'bp_wheelbarrow_met': 'Carrinho de Mão Metal',
            
            # Mapeamentos alternativos
            'wolfswagen': 'Wolfswagen',
            'wolfsvagen': 'Wolfswagen',
            'dirtbike': 'Dirtbike',
            'quad': 'Quad',
            'rager': 'Rager',
            'tractor': 'Trator',
            'laika': 'Laika',
            'cruiser': 'Cruiser',
            'citybike': 'City Bike',
            'mountainbike': 'Mountain Bike',
            'barba': 'Barba',
            'bigraft': 'Big Raft',
            'smallraft': 'Small Raft',
            'sup': 'SUP',
            'ris': 'RIS',
            'kinglet_duster': 'Kinglet Duster',
            'kinglet_mariner': 'Kinglet Mariner',
            'wheelbarrow_improvised': 'Carrinho de Mão Improvisado',
            'wheelbarrow_metal': 'Carrinho de Mão Metal'
        }
        
        # Normalizar nome
        normalized_name = vehicle_class.lower().replace('_', '_')
        
        # Procurar correspondência
        for key, display_name in display_names.items():
            if normalized_name.find(key) != -1 or key.find(normalized_name) != -1:
                return display_name
        
        # Retornar nome original formatado
        return vehicle_class.replace('_', ' ').title()
    
    def check_vehicle_exists(self, vehicle_entity_id: int) -> bool:
        """
        Verificar se um veículo ainda existe no SCUM.db
        
        Args:
            vehicle_entity_id: ID da entidade do veículo
            
        Returns:
            True se o veículo existe, False caso contrário
        """
        if not vehicle_entity_id:
            return False
        
        try:
            with scum_db_readonly_connection(self.scum_db_path) as conn:
                conn.execute("PRAGMA busy_timeout = 8000")
                cursor = conn.cursor()
                
                # Verificar se o veículo existe na tabela vehicle_spawner
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM vehicle_spawner 
                    WHERE vehicle_entity_id = ?
                ''', (vehicle_entity_id,))
                
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            print(f"ERRO: Erro ao verificar existência do veículo {vehicle_entity_id}: {e}")
            return False
    
    def check_vehicles_batch(self, vehicle_entity_ids: List[int]) -> Dict[int, bool]:
        """
        Verificar existência de múltiplos veículos em lote
        
        Args:
            vehicle_entity_ids: Lista de IDs de entidades de veículos
            
        Returns:
            Dicionário mapeando vehicle_entity_id -> True/False (existe/não existe)
        """
        if not vehicle_entity_ids:
            return {}
        
        result = {}
        batch_size = 500
        
        try:
            with scum_db_readonly_connection(self.scum_db_path) as conn:
                conn.execute("PRAGMA busy_timeout = 8000")
                cursor = conn.cursor()
                
                # Processar em lotes para melhor performance
                for i in range(0, len(vehicle_entity_ids), batch_size):
                    batch = vehicle_entity_ids[i:i + batch_size]
                    placeholders = ','.join(['?' for _ in batch])
                    
                    # Query em lote para verificar existência
                    query = f'''
                        SELECT vehicle_entity_id 
                        FROM vehicle_spawner 
                        WHERE vehicle_entity_id IN ({placeholders})
                    '''
                    
                    cursor.execute(query, batch)
                    existing_ids = {row[0] for row in cursor.fetchall()}
                    
                    # Mapear resultados
                    for vehicle_id in batch:
                        result[vehicle_id] = vehicle_id in existing_ids
                
                return result
                
        except Exception as e:
            print(f"ERRO: Erro ao verificar existência de veículos em lote: {e}")
            # Em caso de erro, retornar False para todos
            return {vid: False for vid in vehicle_entity_ids}
    
    def get_processor_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do processador"""
        return {
            'scum_db_path': self.scum_db_path,
            'vehicle_cache_size': len(self.vehicle_cache),
            'parser_stats': self.parser.get_parser_stats()
        }
