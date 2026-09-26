"""
Processador de logs economy_*.log para extrair transações bancárias e comerciais
"""

import os
import re
import sqlite3
import threading
import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
from core.database.connector import DatabaseConnector

from utils.logger import StructuredLogger
from core.banking.bank_transaction_tables import (
    ensure_bank_transaction_tables,
    get_or_create_location,
    get_or_create_item,
    get_transaction_type_id
)


class BankTransactionProcessor:
    """Processa logs economy_*.log e extrai transações bancárias"""
    
    def __init__(
        self,
        ssm_db_path: str,
        logs_directory: str,
        logger: Optional[StructuredLogger] = None,
        discord_webhook = None
    ):
        self.ssm_db_path = ssm_db_path
        self.logs_directory = logs_directory
        self.logger = logger or StructuredLogger()
        self.discord_webhook = discord_webhook  # Referência opcional ao DiscordWebhook

        # Padrões regex para parsing
        self.patterns = {
            # Timestamp: 2025.12.06-00.41.27
            'timestamp': re.compile(r'(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2})'),

            # Player: TutiCats(76561199617993331) ou player TutiCats(76561199617993331)
            'player': re.compile(r'(?:player\s+)?([A-Za-z0-9_]+)\((\d+)\)'),

            # Local: B_4_Armory, B_4_Trader, etc.
            'location': re.compile(r'([A-Z]_\d+)_([A-Za-z]+)'),

            # Item: Tradeable (ItemName (health: X, uses: Y)) ou Tradeable (ItemName (x2))
            'item': re.compile(r'Tradeable\s+\(([^)]+)\)'),

            # Valores monetários
            'money_value': re.compile(r'(\d+(?:\.\d+)?)\s+money'),
            'gold_value': re.compile(r'(\d+(?:\.\d+)?)\s+gold'),
            'credits_value': re.compile(r'(\d+(?:\.\d+)?)\s+credits'),

            # Saldos: "had 0 cash, 26019 account balance and 68 gold" ou "has 0 cash, 26019 bank account balance and 68 gold"
            'balance_before': re.compile(r'had\s+(\d+(?:\.\d+)?)\s+cash[,\s]+(\d+(?:\.\d+)?)\s+(?:bank\s+)?account\s+balance[,\s]+and\s+(\d+(?:\.\d+)?)\s+gold'),
            'balance_after': re.compile(r'has\s+(\d+(?:\.\d+)?)\s+cash[,\s]+(\d+(?:\.\d+)?)\s+(?:bank\s+)?account\s+balance[,\s]+and\s+(\d+(?:\.\d+)?)\s+gold'),

            # Valor de transação: "for 3278 (2870 + 408 worth of contained items)"
            'transaction_value': re.compile(r'for\s+(\d+(?:\.\d+)?)\s*(?:\((\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)\s+worth\s+of\s+contained\s+items\))?'),

            # Account Number: Account Number:718705046343
            'account_number': re.compile(r'Account\s+Number[:\s]+(\d+)'),
        }

        try:
            ensure_bank_transaction_tables(self.ssm_db_path, self.logger)
        except Exception as e:
            try:
                self.logger.warn(f"Falha ao garantir tabelas de transações bancárias: {e}")
            except Exception:
                pass

        # OPÇÃO 5: Controle robusto de parada
        self.running = True  # Flag de controle
        self.stop_event = threading.Event()  # Event para shutdown rápido

        # Retry/Backoff para reduzir falhas por concorrência no startup
        self.max_db_retries = 5
        self.base_backoff_seconds = 0.5

    def _sleep_backoff(self, attempt: int) -> None:
        try:
            delay = float(self.base_backoff_seconds) * (2**int(attempt))
        except Exception:
            delay = 1.0
        time.sleep(min(delay, 8.0))

    def _connect_db(
        self, timeout: float = 30.0, write_mode: bool = False
    ):
        """Usa o DatabaseConnector centralizado."""
        return DatabaseConnector.get_connection(self.ssm_db_path, timeout=float(timeout), write_mode=write_mode)
    
    def set_running(self, running: bool) -> None:
        """OPÇÃO 5: Definir flag de execução (para comunicação externa)"""
        self.running = running
        if not running:
            self.stop_event.set()
    
    def set_stop_event(self, stop_event: threading.Event) -> None:
        """OPÇÃO 5: Definir Event de parada (para comunicação com LogProcessor)"""
        self.stop_event = stop_event
    
    def clean_item_name(self, item_str: str) -> str:
        """
        Limpar nome do item removendo health, quantidade, uses, etc.
        
        Args:
            item_str: String do item completo (ex: "Weapon_MK18 (health: 99.94, uses: 1)")
            
        Returns:
            Nome base limpo (ex: "Weapon_MK18")
        """
        # Limpeza completa e definitiva
        
        # 1. Remover health com qualquer conteúdo (incluindo quantidades aninhadas)
        item_str = re.sub(r'\(health:\s*[^)]*\)', '', item_str, flags=re.IGNORECASE)
        
        # 2. Remover uses
        item_str = re.sub(r'\(uses:\s*\d+\)', '', item_str, flags=re.IGNORECASE)
        item_str = re.sub(r',\s*uses:\s*\d+', '', item_str, flags=re.IGNORECASE)
        
        # 3. Remover TODAS as quantidades (x1), (x2), etc. - loop até não sobrar nenhuma
        max_iterations = 10
        iteration = 0
        while re.search(r'\(x\d+\)', item_str, re.IGNORECASE) and iteration < max_iterations:
            item_str = re.sub(r'\(x\d+\)', '', item_str, flags=re.IGNORECASE)
            iteration += 1
        
        # 4. Remover contained items
        item_str = re.sub(r'\(contained\s+items:.*?\)', '', item_str, flags=re.IGNORECASE)
        
        # 5. Remover qualquer parêntese restante
        item_str = re.sub(r'\([^)]*\)', '', item_str)
        
        # 6. Remover vírgulas, espaços extras e limpar
        item_str = re.sub(r'[,;]\s*', '', item_str)
        item_str = re.sub(r'\s+', ' ', item_str)
        item_str = item_str.strip().rstrip(',')
        
        return item_str.strip()
    
    def extract_quantity(self, item_str: str) -> int:
        """
        Extrair quantidade do item.
        
        Args:
            item_str: String do item completo
            
        Returns:
            Quantidade (padrão: 1)
        """
        match = re.search(r'\(x(\d+)\)', item_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 1
    
    def parse_trade_sale(self, line: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """
        Parse de linha de venda: [Trade] Tradeable (...) sold by PLAYER(...) for VALOR to trader LOCAL
        
        Args:
            line: Linha do log
            timestamp: Timestamp da transação
            
        Returns:
            Dicionário com dados da transação ou None se não for válida
        """
        # Verificar se é uma linha de venda
        if 'sold by' not in line or 'to trader' not in line:
            return None

        try:
            # Extrair player
            player_match = self.patterns['player'].search(line)
            if not player_match:
                return None

            player_name = player_match.group(1)
            steam_id = player_match.group(2)

            # Verificar se player existe no banco
            if not self._player_exists(steam_id):
                return None

            # Extrair local
            location_match = self.patterns['location'].search(line)
            if not location_match:
                return None

            quadrant = location_match.group(1)
            location_type = location_match.group(2)

            # Extrair item
            item_match = self.patterns['item'].search(line)
            if not item_match:
                return None

            item_full = item_match.group(1)
            item_name = self.clean_item_name(item_full)
            item_quantity = self.extract_quantity(item_full)

            # Extrair valores
            value_match = self.patterns['transaction_value'].search(line)
            if not value_match:
                return None

            transaction_value = float(value_match.group(1))
            value_base = float(value_match.group(2)) if value_match.group(2) else transaction_value
            value_contained = float(value_match.group(3)) if value_match.group(3) else 0.0

            # Extrair informações adicionais
            players_online_match = re.search(r'effective users online:\s*(\d+)', line)
            players_online = int(players_online_match.group(1)) if players_online_match else None

            store_qty_match = re.search(r'old amount in store is\s+(-?\d+)', line)
            store_quantity_before = int(store_qty_match.group(1)) if store_qty_match else None

            return {
                'type': 'trade_sale',
                'timestamp': timestamp,
                'steam_id': steam_id,
                'player_name': player_name,
                'quadrant': quadrant,
                'location_type': location_type,
                'item_name': item_name,
                'item_quantity': item_quantity,
                'transaction_value': transaction_value,
                'value_base': value_base,
                'value_contained_items': value_contained,
                'players_online': players_online,
                'store_quantity_before': store_quantity_before,
                'store_quantity_after': store_quantity_before,  # Geralmente não muda
            }
        except Exception as e:
            self.logger.error(f"Erro ao parsear linha de venda: {e}", {'line': line[:200]})
            return None
    
    def parse_trade_purchase(self, line: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """
        Parse de linha de compra: [Trade] Tradeable (...) purchased by PLAYER(...) for VALOR money from trader LOCAL
        """
        if 'purchased by' not in line or 'from trader' not in line:
            return None
        
        try:
            player_match = self.patterns['player'].search(line)
            if not player_match:
                return None
            
            player_name = player_match.group(1)
            steam_id = player_match.group(2)
            
            if not self._player_exists(steam_id):
                return None
            
            location_match = self.patterns['location'].search(line)
            if not location_match:
                return None
            
            quadrant = location_match.group(1)
            location_type = location_match.group(2)
            
            item_match = self.patterns['item'].search(line)
            if not item_match:
                return None
            
            item_full = item_match.group(1)
            item_name = self.clean_item_name(item_full)
            item_quantity = self.extract_quantity(item_full)
            
            money_match = self.patterns['money_value'].search(line)
            if not money_match:
                return None
            
            transaction_value = float(money_match.group(1))
            
            players_online_match = re.search(r'effective users online:\s*(\d+)', line)
            players_online = int(players_online_match.group(1)) if players_online_match else None
            
            store_qty_match = re.search(r'old amount in store was\s+(-?\d+)', line)
            store_quantity_before = int(store_qty_match.group(1)) if store_qty_match else None
            
            return {
                'type': 'trade_purchase',
                'timestamp': timestamp,
                'steam_id': steam_id,
                'player_name': player_name,
                'quadrant': quadrant,
                'location_type': location_type,
                'item_name': item_name,
                'item_quantity': item_quantity,
                'transaction_value': transaction_value,
                'value_base': transaction_value,
                'value_contained_items': 0.0,
                'players_online': players_online,
                'store_quantity_before': store_quantity_before,
                'store_quantity_after': store_quantity_before,
            }
        except Exception as e:
            self.logger.error(f"Erro ao parsear linha de compra: {e}", {'line': line[:200]})
            return None
    
    def parse_bank_deposit(self, line: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """
        Parse de depósito bancário: [Bank] PLAYER(ID:STEAM_ID)(Account Number:ACCOUNT) deposited AMOUNT(ACTUAL_ADDED was added)...
        """
        if '[Bank]' not in line or 'deposited' not in line:
            return None
        
        try:
            # Extrair player: PLAYER(ID:STEAM_ID)
            player_match = re.search(r'([A-Za-z0-9_]+)\(ID:(\d+)\)', line)
            if not player_match:
                return None
            
            player_name = player_match.group(1)
            steam_id = player_match.group(2)
            
            if not self._player_exists(steam_id):
                return None
            
            # Extrair account number
            account_match = self.patterns['account_number'].search(line)
            account_number = account_match.group(1) if account_match else None
            
            # Extrair valores: deposited AMOUNT(ACTUAL_ADDED was added)
            deposit_match = re.search(r'deposited\s+(\d+(?:\.\d+)?)\((\d+(?:\.\d+)?)\s+was\s+added\)', line)
            if not deposit_match:
                return None
            
            transaction_value = float(deposit_match.group(1))
            value_base = float(deposit_match.group(2))  # Valor efetivamente adicionado
            
            return {
                'type': 'bank_deposit',
                'timestamp': timestamp,
                'steam_id': steam_id,
                'player_name': player_name,
                'account_number': account_number,
                'transaction_value': transaction_value,
                'value_base': value_base,
                'value_contained_items': 0.0,
            }
        except Exception as e:
            self.logger.error(f"Erro ao parsear depósito bancário: {e}", {'line': line[:200]})
            return None

    def parse_bank_withdrawal(self, line: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """
        Parse de saque bancário: [Bank] PLAYER(ID:STEAM_ID)(Account Number:ACCOUNT) withdrew AMOUNT(ACTUAL_REMOVED was removed)...
        """
        if '[Bank]' not in line or 'withdrew' not in line:
            return None

        try:
            player_match = re.search(r'([A-Za-z0-9_]+)\(ID:(\d+)\)', line)
            if not player_match:
                return None

            player_name = player_match.group(1)
            steam_id = player_match.group(2)

            if not self._player_exists(steam_id):
                return None

            account_match = self.patterns['account_number'].search(line)
            account_number = account_match.group(1) if account_match else None

            withdraw_match = re.search(
                r'withdrew\s+(\d+(?:\.\d+)?)\((\d+(?:\.\d+)?)\s+was\s+removed\)',
                line,
            )
            if not withdraw_match:
                return None

            transaction_value = float(withdraw_match.group(1))
            value_base = float(withdraw_match.group(2))

            return {
                'type': 'bank_withdrawal',
                'timestamp': timestamp,
                'steam_id': steam_id,
                'player_name': player_name,
                'account_number': account_number,
                'transaction_value': transaction_value,
                'value_base': value_base,
                'value_contained_items': 0.0,
            }
        except Exception as e:
            self.logger.error(f"Erro ao parsear saque bancário: {e}", {'line': line[:200]})
            return None
    
    def parse_currency_conversion(self, line: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """
        Parse de conversão de moeda: [Currency Conversion] PLAYER(ID:STEAM_ID)(Account Number:ACCOUNT) purchased GOLD gold for CREDITS credits...
        """
        if '[Currency Conversion]' not in line:
            return None
        
        try:
            player_match = re.search(r'([A-Za-z0-9_]+)\(ID:(\d+)\)', line)
            if not player_match:
                return None
            
            player_name = player_match.group(1)
            steam_id = player_match.group(2)
            
            if not self._player_exists(steam_id):
                return None
            
            # Extrair: purchased GOLD gold for CREDITS credits
            conversion_match = re.search(r'purchased\s+(\d+(?:\.\d+)?)\s+gold\s+for\s+(\d+(?:\.\d+)?)\s+credits', line)
            if not conversion_match:
                return None
            
            gold_amount = float(conversion_match.group(1))
            credits_spent = float(conversion_match.group(2))
            
            # Extrair novo saldo: (new account balance is GOLD gold/CREDITS credits)
            balance_match = re.search(r'new account balance is\s+(\d+(?:\.\d+)?)\s+gold/(\d+(?:\.\d+)?)\s+credits', line)
            balance_after_gold = float(balance_match.group(1)) if balance_match else None
            balance_after_account = float(balance_match.group(2)) if balance_match else None
            
            return {
                'type': 'currency_conversion',
                'timestamp': timestamp,
                'steam_id': steam_id,
                'player_name': player_name,
                'transaction_value': credits_spent,
                'value_base': credits_spent,
                'value_contained_items': 0.0,
                'gold_amount': gold_amount,
                'balance_after_gold': balance_after_gold,
                'balance_after_account': balance_after_account,
            }
        except Exception as e:
            self.logger.error(f"Erro ao parsear conversão de moeda: {e}", {'line': line[:200]})
            return None
    
    def parse_service_repair(self, line: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """
        Parse de serviço de reparo: [Trade-Mechanic] Service (Repair attachment ITEM) purchased by PLAYER(...) for VALOR money from trader LOCAL
        """
        if '[Trade-Mechanic]' not in line or 'Service' not in line:
            return None
        
        try:
            player_match = self.patterns['player'].search(line)
            if not player_match:
                return None
            
            player_name = player_match.group(1)
            steam_id = player_match.group(2)
            
            if not self._player_exists(steam_id):
                return None
            
            location_match = self.patterns['location'].search(line)
            if not location_match:
                return None
            
            quadrant = location_match.group(1)
            location_type = location_match.group(2)
            
            money_match = self.patterns['money_value'].search(line)
            if not money_match:
                return None
            
            transaction_value = float(money_match.group(1))
            
            # Extrair descrição do serviço
            service_match = re.search(r'Service\s+\(([^)]+)\)', line)
            service_description = service_match.group(1) if service_match else None
            
            players_online_match = re.search(r'effective users online:\s*(\d+)', line)
            players_online = int(players_online_match.group(1)) if players_online_match else None
            
            return {
                'type': 'service_repair',
                'timestamp': timestamp,
                'steam_id': steam_id,
                'player_name': player_name,
                'quadrant': quadrant,
                'location_type': location_type,
                'transaction_value': transaction_value,
                'value_base': transaction_value,
                'value_contained_items': 0.0,
                'service_description': service_description,
                'players_online': players_online,
            }
        except Exception as e:
            self.logger.error(f"Erro ao parsear serviço de reparo: {e}", {'line': line[:200]})
            return None
    
    def parse_balance_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse de linha de saldo (Before/After): player PLAYER(...) had/has X cash, Y account balance and Z gold
        """
        is_before = 'Before' in line or 'had' in line
        is_after = 'After' in line or 'has' in line
        
        if not (is_before or is_after):
            return None
        
        try:
            player_match = self.patterns['player'].search(line)
            if not player_match:
                return None
            
            steam_id = player_match.group(2)
            
            # Tentar padrão completo primeiro
            balance_match = self.patterns['balance_before' if is_before else 'balance_after'].search(line)
            if balance_match:
                return {
                    'steam_id': steam_id,
                    'is_before': is_before,
                    'money': float(balance_match.group(1)),
                    'account': float(balance_match.group(2)),
                    'gold': float(balance_match.group(3)),
                }
            
            # Fallback: padrão mais flexível
            money_match = re.search(r'(\d+(?:\.\d+)?)\s+cash', line)
            account_match = re.search(r'(\d+(?:\.\d+)?)\s+(?:bank\s+)?account\s+balance', line)
            gold_match = re.search(r'(\d+(?:\.\d+)?)\s+gold', line)
            
            return {
                'steam_id': steam_id,
                'is_before': is_before,
                'money': float(money_match.group(1)) if money_match else 0.0,
                'account': float(account_match.group(1)) if account_match else 0.0,
                'gold': float(gold_match.group(1)) if gold_match else 0.0,
            }
        except Exception as e:
            return None
    
    def _player_exists(self, steam_id: str) -> bool:
        """Verificar se player existe na tabela players"""
        for attempt in range(int(self.max_db_retries)):
            try:
                with self._connect_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT 1 FROM players WHERE steam_id = ? LIMIT 1",
                        (steam_id,),
                    )
                    return cursor.fetchone() is not None
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_db_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                return False
            except Exception:
                return False
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Processar um arquivo economy_*.log - OPÇÃO 5: Verifica stop_event antes de processar
        
        Args:
            file_path: Caminho do arquivo de log
            
        Returns:
            Estatísticas do processamento
        """
        # OPÇÃO 5: Verificar stop_event ANTES de iniciar processamento
        if not self.running or self.stop_event.is_set():
            return {
                'file': os.path.basename(file_path),
                'lines_processed': 0,
                'transactions_found': 0,
                'transactions_inserted': 0,
                'errors': 0,
                'stopped': True
            }
        
        stats = {
            'file': os.path.basename(file_path),
            'lines_processed': 0,
            'transactions_found': 0,
            'transactions_inserted': 0,
            'errors': 0,
        }

        for attempt in range(int(self.max_db_retries)):
            try:
                if not os.path.exists(file_path):
                    self.logger.error(f"Arquivo não encontrado: {file_path}")
                    stats['errors'] += 1
                    return stats

                # 1. Ler arquivo primeiro (sem segurar lock de banco)
                try:
                    with open(file_path, "r", encoding="utf-16le") as f:
                        lines = f.readlines()
                except Exception:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                if not lines:
                    return stats

                # 2. Obter cursor atual (leitura rápida)
                last_line = 0
                current_size = int(os.path.getsize(file_path))
                current_mtime = float(os.path.getmtime(file_path))

                with self._connect_db(timeout=10.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT last_line, last_size FROM log_cursors WHERE file_path = ?",
                        (file_path,),
                    )
                    row = cursor.fetchone()
                    if row:
                        last_line, last_size = int(row[0] or 0), int(row[1] or 0)
                        if current_size < last_size: # Rotação
                            last_line = 0
                    else:
                        cursor.execute(
                            "INSERT OR IGNORE INTO log_cursors(file_path, last_line, last_size, last_mtime) VALUES (?, 0, 0, 0)",
                            (file_path,),
                        )
                        conn.commit()

                if last_line >= len(lines):
                    return stats

                # 3. Processar linhas em memória
                transaction_groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
                balance_before: Dict[Tuple[str, str], Dict[str, float]] = {}
                balance_after: Dict[Tuple[str, str], Dict[str, float]] = {}
                
                # Filtrar apenas linhas relevantes para processamento
                new_lines = lines[last_line:]
                processed_count = 0

                for line in new_lines:
                    if not self.running or self.stop_event.is_set():
                        break
                    
                    line = line.strip()
                    if not line:
                        processed_count += 1
                        continue

                    timestamp_match = self.patterns['timestamp'].search(line)
                    if not timestamp_match:
                        processed_count += 1
                        continue
                    
                    timestamp = timestamp_match.group(1)
                    transaction = None

                    if '[Trade]' in line:
                        if 'sold by' in line:
                            transaction = self.parse_trade_sale(line, timestamp)
                        elif 'purchased by' in line:
                            transaction = self.parse_trade_purchase(line, timestamp)
                        elif 'Before' in line or 'After' in line:
                            balance_data = self.parse_balance_line(line)
                            if balance_data:
                                steam_id = balance_data['steam_id']
                                key = (steam_id, timestamp)
                                if balance_data['is_before']:
                                    balance_before[key] = balance_data
                                else:
                                    balance_after[key] = balance_data
                    elif '[Bank]' in line:
                        transaction = self.parse_bank_deposit(line, timestamp)
                        if not transaction:
                            transaction = self.parse_bank_withdrawal(line, timestamp)
                    elif '[Currency Conversion]' in line:
                        transaction = self.parse_currency_conversion(line, timestamp)
                    elif '[Trade-Mechanic]' in line:
                        transaction = self.parse_service_repair(line, timestamp)

                    if transaction:
                        steam_id = transaction.get('steam_id')
                        key = (steam_id, timestamp)
                        if key not in transaction_groups:
                            transaction_groups[key] = []
                        transaction_groups[key].append(transaction)
                    
                    processed_count += 1

                # 4. Gravar resultados em lote (lock de banco apenas aqui)
                to_notify = []
                if transaction_groups:
                    with self._connect_db(timeout=60.0, write_mode=True) as conn:
                        cursor = conn.cursor()
                        for key, txns in transaction_groups.items():
                            for txn in txns:
                                # Correlacionar balances se existirem
                                if key in balance_before:
                                    txn['balance_before'] = {
                                        'money': balance_before[key]['money'],
                                        'account': balance_before[key]['account'],
                                        'gold': balance_before[key]['gold']
                                    }
                                if key in balance_after:
                                    txn['balance_after'] = {
                                        'money': balance_after[key]['money'],
                                        'account': balance_after[key]['account'],
                                        'gold': balance_after[key]['gold']
                                    }

                                inserted_id = self._insert_transaction(conn, cursor, txn)
                                if inserted_id:
                                    stats['transactions_inserted'] += 1
                                    to_notify.append((txn, inserted_id))
                        
                        # Atualizar cursor dentro da mesma transação
                        cursor.execute(
                            "UPDATE log_cursors SET last_line = ?, last_size = ?, last_mtime = ?, updated_at = CURRENT_TIMESTAMP WHERE file_path = ?",
                            (last_line + processed_count, current_size, current_mtime, file_path),
                        )
                        conn.commit()
                    
                    # 5. Notificar Discord FORA da transação de banco (evita segurar lock durante I/O de rede)
                    for txn, inserted_id in to_notify:
                        try:
                            self.notify_transaction(txn, inserted_id)
                        except Exception as e:
                            self.logger.warn(f"Falha ao agendar notificação: {e}")
                else:
                    # Apenas atualizar cursor
                    with self._connect_db(timeout=10.0, write_mode=True) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE log_cursors SET last_line = ?, last_size = ?, last_mtime = ?, updated_at = CURRENT_TIMESTAMP WHERE file_path = ?",
                            (last_line + processed_count, current_size, current_mtime, file_path),
                        )
                        conn.commit()

                stats['lines_processed'] = processed_count
                stats['transactions_found'] = stats['transactions_inserted']
                return stats

                self.logger.info(
                    f"Arquivo processado: {stats['file']}",
                    {
                        'lines_processed': stats['lines_processed'],
                        'transactions_found': stats['transactions_found'],
                        'transactions_inserted': stats['transactions_inserted'],
                        'errors': stats['errors'],
                    },
                )
                return stats

            except sqlite3.OperationalError as e:
                if (
                    'database is locked' in str(e).lower()
                    and attempt < self.max_db_retries - 1
                ):
                    self.logger.warn(
                        f"Banco bloqueado ao processar arquivo {file_path}: {e} - retry {attempt + 1}/{self.max_db_retries}"
                    )
                    self._sleep_backoff(attempt)
                    continue
                if 'database is locked' in str(e).lower():
                    self.logger.warn(
                        f"Banco bloqueado ao processar arquivo {file_path}: {e} - tentando novamente mais tarde"
                    )
                else:
                    self.logger.error(f"Erro de banco ao processar arquivo {file_path}: {e}")
                stats['errors'] += 1
                return stats
            except Exception as e:
                self.logger.error(
                    f"Erro ao processar arquivo {file_path}: {e}",
                    {'error_type': type(e).__name__, 'error_message': str(e)},
                )
                import traceback

                self.logger.error(f"Traceback: {traceback.format_exc()}")
                stats['errors'] += 1
                return stats

        return stats

    def _insert_transaction(
        self,
        conn: sqlite3.Connection,
        cursor: sqlite3.Cursor,
        transaction: Dict[str, Any],
    ) -> Optional[int]:
        """Inserir transação no banco de dados."""
        try:
            type_id = get_transaction_type_id(conn, transaction['type'])
            if not type_id:
                return None

            location_id = None
            if 'quadrant' in transaction and 'location_type' in transaction:
                location_id = get_or_create_location(
                    conn,
                    transaction['quadrant'],
                    transaction['location_type'],
                    self.logger,
                )

            item_id = None
            item_quantity = 1
            if 'item_name' in transaction:
                item_id = get_or_create_item(conn, transaction['item_name'], self.logger)
                item_quantity = transaction.get('item_quantity', 1)

            balance_before = transaction.get('balance_before', {})
            balance_after = transaction.get('balance_after', {})

            def _norm_num(val: Any) -> Optional[str]:
                if val is None:
                    return None
                try:
                    return f"{float(val):.6f}"
                except Exception:
                    return str(val)

            hash_payload = {
                "type": transaction.get("type"),
                "timestamp": transaction.get("timestamp"),
                "steam_id": transaction.get("steam_id"),
                "quadrant": transaction.get("quadrant"),
                "location_type": transaction.get("location_type"),
                "item_name": transaction.get("item_name"),
                "item_quantity": transaction.get("item_quantity", item_quantity),
                "transaction_value": _norm_num(transaction.get("transaction_value")),
                "currency_type": transaction.get("currency_type", "money"),
                "value_base": _norm_num(transaction.get("value_base")),
                "value_contained_items": _norm_num(transaction.get("value_contained_items")),
                "gold_amount": _norm_num(transaction.get("gold_amount")),
                "account_number": transaction.get("account_number"),
            }
            transaction_hash = hashlib.sha256(
                json.dumps(
                    hash_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()

            transaction_id: Optional[int] = None
            try:
                cursor.execute(
                    """
                    INSERT INTO bank_transactions (
                        transaction_hash,
                        steam_id, transaction_type_id, location_id, item_id, item_quantity,
                        transaction_value, currency_type, value_base, value_contained_items,
                        balance_before_money, balance_before_gold, balance_before_account,
                        balance_after_money, balance_after_gold, balance_after_account,
                        trader_funds_before, trader_funds_after,
                        store_quantity_before, store_quantity_after,
                        players_online, timestamp,
                        discord_sent, discord_attempts, discord_last_attempt_at, discord_last_error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, NULL)
                    """,
                    (
                        transaction_hash,
                        transaction.get('steam_id'),
                        type_id,
                        location_id,
                        item_id,
                        item_quantity,
                        transaction.get('transaction_value'),
                        transaction.get('currency_type', 'money'),
                        transaction.get('value_base', transaction.get('transaction_value')),
                        transaction.get('value_contained_items', 0.0),
                        balance_before.get('money', 0.0),
                        balance_before.get('gold', 0.0),
                        balance_before.get('account', 0.0),
                        balance_after.get('money', 0.0),
                        balance_after.get('gold', 0.0),
                        balance_after.get('account', 0.0),
                        transaction.get('trader_funds_before'),
                        transaction.get('trader_funds_after'),
                        transaction.get('store_quantity_before'),
                        transaction.get('store_quantity_after'),
                        transaction.get('players_online'),
                        transaction.get('timestamp'),
                    ),
                )
                transaction_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                transaction_id = None

            return transaction_id
        except Exception as e:
            self.logger.error(
                f"Erro ao inserir transação: {e}",
                {
                    'type': transaction.get('type'),
                    'steam_id': transaction.get('steam_id'),
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                },
            )
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def mark_transaction_as_sent(self, transaction_id: int) -> bool:
        """
        Marcar transação como enviada para Discord
        
        Args:
            transaction_id: ID da transação no banco
            
        Returns:
            True se marcado com sucesso
        """
        try:
            with self._connect_db(timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bank_transactions 
                    SET discord_sent = 1, discord_last_attempt_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (transaction_id,))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Erro ao marcar transação como enviada: {e}", {
                'transaction_id': transaction_id,
                'error': str(e)
            })
            return False

    def increment_discord_attempts(
        self, transaction_id: int, error_msg: str = ""
    ) -> bool:
        """Incrementar tentativas de envio e registrar último erro (não interrompe fluxo)."""
        try:
            with self._connect_db(timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE bank_transactions
                    SET discord_attempts = COALESCE(discord_attempts, 0) + 1,
                        discord_last_error = ?,
                        discord_last_attempt_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (str(error_msg or "")[:500], int(transaction_id)),
                )
                conn.commit()
                return True
        except Exception:
            return False
    
    def notify_transaction(self, transaction: Dict[str, Any], transaction_id: int) -> None:
        """
        Notificar transação via Discord webhook - OPÇÃO 5: Verifica stop_event antes de enviar
        
        Args:
            transaction: Dicionário com dados da transação
            transaction_id: ID da transação inserida no banco
        """
        # OPÇÃO 5: Verificar stop_event ANTES de enviar webhook
        if not self.running or self.stop_event.is_set():
            self.logger.debug(f"Processamento parado - não enviando webhook para transação {transaction_id}")
            return
        
        if not self.discord_webhook:
            return
        
        try:
            # Verificar se já foi enviado (segurança extra)
            with self._connect_db(timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT discord_sent FROM bank_transactions WHERE id = ?", (transaction_id,))
                result = cursor.fetchone()
                if result and int(result[0] or 0) == 1:
                    # Já foi enviado, pular
                    self.logger.debug(f"Transação {transaction_id} já foi enviada, pulando")
                    return
            
            # Enviar notificação Discord
            success = self.discord_webhook.send_bank_transaction_notification(transaction)
            
            if success:
                # Marcar como enviado no banco
                self.mark_transaction_as_sent(transaction_id)
                self.logger.debug(f"Webhook enviado para transação {transaction_id}")
            else:
                # Deixar discord_sent = 0 para retry depois
                # Log apenas em debug para não poluir logs (erros detalhados já são logados no DiscordWebhook)
                self.logger.debug(f"Falha ao enviar webhook para transação {transaction_id} - será retentado automaticamente")
                self.increment_discord_attempts(transaction_id)
        except Exception as e:
            # Log mas não interromper processamento
            self.logger.warn(f"Erro ao enviar notificação Discord: {e}", {
                'transaction_id': transaction_id,
                'error': str(e)
            })
            self.increment_discord_attempts(transaction_id, str(e)[:200])
    
    def process_logs(self) -> Dict[str, Any]:
        """
        Processar todos os arquivos economy_*.log no diretório de logs
        
        Returns:
            Estatísticas gerais do processamento
        """
        total_stats = {
            'files_processed': 0,
            'total_lines': 0,
            'total_transactions_found': 0,
            'total_transactions_inserted': 0,
            'total_errors': 0,
        }
        
        try:
            logs_dir = Path(self.logs_directory)
            if not logs_dir.exists():
                self.logger.warn(f"Diretório de logs não encontrado: {self.logs_directory}")
                return total_stats
            
            # Encontrar todos os arquivos economy_*.log
            economy_logs = list(logs_dir.glob('economy_*.log'))
            
            if not economy_logs:
                self.logger.info("Nenhum arquivo economy_*.log encontrado")
                return total_stats
            
            # Processar cada arquivo
            for log_file in sorted(economy_logs, key=lambda x: x.stat().st_mtime, reverse=True):
                stats = self.process_file(str(log_file))
                
                total_stats['files_processed'] += 1
                total_stats['total_lines'] += stats['lines_processed']
                total_stats['total_transactions_found'] += stats['transactions_found']
                total_stats['total_transactions_inserted'] += stats['transactions_inserted']
                total_stats['total_errors'] += stats['errors']
            
            self.logger.info("Processamento de logs economy concluído", total_stats)
            return total_stats
            
        except Exception as e:
            self.logger.error(f"Erro ao processar logs economy: {e}")
            total_stats['total_errors'] += 1
            return total_stats

