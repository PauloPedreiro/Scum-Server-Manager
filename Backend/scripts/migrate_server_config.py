#!/usr/bin/env python3
"""
Script de migração para remover campos redundantes da seção 'server' no config.json

Este script:
1. Remove campos redundantes de 'server' que já existem em 'paths.scum_server'
2. Mantém apenas campos específicos do servidor
3. Cria backup antes de modificar
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def migrate_config(config_path: str = "data/config.json"):
    """
    Migrar config.json removendo campos redundantes da seção 'server'

    Args:
        config_path: Caminho para o arquivo config.json
    """
    config_file = Path(config_path)

    if not config_file.exists():
        print(f"❌ Arquivo não encontrado: {config_path}")
        return False

    # Criar backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_file.parent / f"config.backup.{timestamp}.json"
    shutil.copy2(config_file, backup_path)
    print(f"✅ Backup criado: {backup_path}")

    # Carregar config
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao carregar config.json: {e}")
        return False

    # Verificar se já foi migrado
    server_section = config.get("server", {})
    paths_section = config.get("paths", {}).get("scum_server", {})

    # Campos redundantes a remover
    redundant_fields = ["server_path", "install_path", "logs_directory"]

    # Verificar se há campos redundantes
    has_redundant = any(field in server_section for field in redundant_fields)

    if not has_redundant:
        print("✅ Config já está migrado (sem campos redundantes)")
        return True

    # Remover campos redundantes
    removed_fields = []
    for field in redundant_fields:
        if field in server_section:
            removed_fields.append(field)
            del server_section[field]
            print(f"  🗑️  Removido campo redundante: {field}")

    # Verificar se paths.scum_server existe
    if not paths_section:
        print("⚠️  Aviso: Seção 'paths.scum_server' não encontrada!")
        print(
            "   Os campos foram removidos, mas você precisa configurar 'paths.scum_server'"
        )

    # Salvar config atualizado
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Config migrado com sucesso!")
        print(f"   Campos removidos: {', '.join(removed_fields)}")
        print(f"   Backup salvo em: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar config.json: {e}")
        print(f"   Restaure o backup: {backup_path}")
        return False


if __name__ == "__main__":
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else "data/config.json"

    print("=" * 60)
    print("Migração de Config - Remover Campos Redundantes")
    print("=" * 60)
    print()

    success = migrate_config(config_path)

    if success:
        print()
        print("=" * 60)
        print("✅ Migração concluída com sucesso!")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ Migração falhou!")
        print("=" * 60)
        sys.exit(1)
