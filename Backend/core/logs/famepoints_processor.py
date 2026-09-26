"""
Processador de logs famepoints_*.log
Responsável por manter o total de fama dos jogadores sincronizado no banco.
"""

import logging
import os
import re
from typing import List, Dict

logger = logging.getLogger(__name__)


class FamepointsProcessor:
    """Processa arquivos famepoints_* e atualiza o total de fama dos jogadores."""

    def __init__(self, db_manager, temp_manager=None):
        self.db_manager = db_manager
        self.temp_manager = temp_manager
        # Regex permite timestamp antes de "Player" (formato: 2025.11.25-12.43.35: Player ...)
        self.award_pattern = re.compile(
            r'Player\s+(?P<player_name>.+?)\((?P<steam_id>\d+)\)\s+was awarded\s+'
            r'(?P<awarded>[-\d.]+)\s+fame points.*?for a total of\s+(?P<total>[-\d.]+)',
            re.IGNORECASE
        )

    def process_file(self, file_path: str) -> int:
        """Processa um arquivo completo de famepoints."""
        temp_path = None
        try:
            read_path = file_path
            if self.temp_manager:
                temp_path = self.temp_manager.create_temp_copy(file_path)
                if temp_path:
                    read_path = temp_path

            lines = self._read_lines(read_path)
            if not lines:
                return 0

            return self.process_lines(os.path.basename(file_path), lines)
        finally:
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)

    def process_lines(self, source_name: str, lines: List[str]) -> int:
        """Processar um conjunto de linhas (útil para monitoramento em tempo real)."""
        entries = self._extract_entries(lines)
        if not entries:
            print(f"   AVISO Nenhuma entrada de fama encontrada em {source_name} ({len(lines)} linhas)")
            return 0

        updated = 0
        skipped = 0

        for entry in entries:
            success = self.db_manager.upsert_player_fame_total(
                entry['steam_id'],
                entry['player_name'],
                entry['total_fame']
            )
            if success:
                updated += 1
                print(f"   OK Fama atualizada: {entry['player_name']} ({entry['steam_id']}) = {entry['total_fame']}")
            else:
                skipped += 1
                print(f"   AVISO Fama ignorada: {entry['player_name']} ({entry['steam_id']}) não existe na tabela players")

        if updated:
            logger.info(
                "Famepoints atualizados (%s): %s jogadores",
                source_name,
                updated
            )
            print(f"   OK Totais de fama atualizados: {updated} jogadores")
        if skipped:
            logger.debug(
                "Famepoints ignorados (%s): %s jogadores fora da tabela players",
                source_name,
                skipped
            )
            print(f"   AVISO Fama ignorada: {skipped} jogadores não encontrados na tabela players")
        return updated

    def _extract_entries(self, lines: List[str]) -> List[Dict[str, str]]:
        """Extrai entradas válidas a partir das linhas fornecidas."""
        entries = []
        for raw_line in lines:
            line = raw_line.strip()
            # Pular linhas vazias ou que não são relevantes
            if not line or line.startswith("2025.") and "Player" not in line:
                continue
                
            # Verificar se a linha contém "Player" (pode ter timestamp antes)
            if "Player" not in line or "was awarded" not in line or "for a total of" not in line:
                continue

            match = self.award_pattern.search(line)
            if not match:
                logger.debug("Regex não encontrou match na linha: %s", line[:100])
                continue

            player_name = match.group('player_name').strip()
            steam_id = match.group('steam_id')

            try:
                total_fame = float(match.group('total'))
            except ValueError:
                logger.debug("Não foi possível converter total de fama: %s", line)
                continue

            entries.append({
                'player_name': player_name,
                'steam_id': steam_id,
                'total_fame': total_fame
            })

        return entries

    def _read_lines(self, file_path: str) -> List[str]:
        """Lê as linhas do arquivo respeitando o encoding padrão dos logs."""
        if not file_path or not os.path.exists(file_path):
            return []

        # Tentar UTF-16LE (formato padrão dos logs do SCUM) e cair para UTF-8
        encodings = ('utf-16le', 'utf-8', 'utf-8-sig')
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as file_obj:
                    return file_obj.readlines()
            except UnicodeError:
                continue

        logger.warning("Falha ao ler arquivo de fama: %s", file_path)
        return []

