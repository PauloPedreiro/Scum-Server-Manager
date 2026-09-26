#!/usr/bin/env python3
"""
Script auxiliar para copiar arquivos de dados para o diretório do executável
Usado após o build do PyInstaller
Copia todos os arquivos necessários para executar o SSM Backend
"""

import shutil
import sys
import os
from pathlib import Path


def copy_data_files():
    """Copiar todos os arquivos de dados necessários para o diretório dist"""
    root_dir = Path(__file__).parent.parent
    dist_base = root_dir / "dist"

    # Verificar onde os executáveis foram criados
    # PyInstaller onedir gera em dist/Panel SSM/, onefile gera em dist/
    if (dist_base / "Panel SSM" / "Panel SSM.exe").exists():
        # onedir: Executáveis estão em dist/Panel SSM/
        dist_dir = dist_base / "Panel SSM"
        print(f"[OK] Detectado (onedir): Executaveis em {dist_dir}")
    elif (dist_base / "Panel SSM.exe").exists():
        # onefile: Executáveis estão em dist/ diretamente
        dist_dir = dist_base
        print(f"[OK] Detectado (onefile): Executaveis em {dist_dir}")
    elif (dist_base / "ssm_backend" / "ssm_backend.exe").exists():
        # Legacy: dist/ssm_backend/
        dist_dir = dist_base / "ssm_backend"
        print(f"[OK] Detectado (legacy): Executaveis em {dist_dir}")
    else:
        # Fallback: usar dist/ como padrão
        dist_dir = dist_base
        if not dist_dir.exists():
            print(f"[AVISO] Diretorio dist nao encontrado! Criando...")
            dist_dir.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Usando diretorio: {dist_dir}")

    print("=" * 60)
    print("Copiando arquivos necessários para dist...")
    print("=" * 60)

    # Lista de arquivos e diretórios a copiar
    items_to_copy = [
        # Arquivos de configuração reais
        # Distribuicao: usar template limpo como config.json (evita dados sensiveis)
        ("data/config.example.json", "data/config.json"),
        # Distribuicao: usar template limpo como webhooks.json (evita tokens/ids)
        ("data/webhooks.example.json", "data/webhooks.json"),
        # Arquivos de configuração exemplo (backup)
        ("data/config.example.json", "data/config.example.json"),
        ("data/webhooks.example.json", "data/webhooks.example.json"),
        # Diretório de imagens completo
        ("data/imagens", "data/imagens"),
        # Frases de kill feed
        ("data/kill_feed_phrases.json", "data/kill_feed_phrases.json"),
        # Arquivos de dados JSON necessários
        ("base_coordinates.csv", "base_coordinates.csv"),
        ("base_coordinates.json", "base_coordinates.json"),
        # Diretório nssm
        ("nssm-2.24", "nssm-2.24"),
        # Diretórios de notificações (templates)
        ("data/notifications", "data/notifications"),
        # Templates / banco de templates (SCUM_TEMPLATES.db)
        ("data/templates", "data/templates"),
        # Mods directory (RCON engines, UE4SS core, Pak mods library)
        ("data/mods", "data/mods"),
        # Criar diretórios necessários
        ("data/logs", "data/logs"),  # Diretório de logs (vazio)
        ("data/logs/rcon", "data/logs/rcon"),  # Diretório de logs RCON (vazio)
        ("data/temp", "data/temp"),  # Diretório temp (vazio)
        ("data/admin", "data/admin"),  # Diretório admin (vazio)
    ]


    copied_count = 0
    skipped_count = 0
    error_count = 0

    for source, dest in items_to_copy:
        source_path = root_dir / source
        dest_path = dist_dir / dest

        try:
            if source_path.exists():
                # Se for diretório, copiar recursivamente
                if source_path.is_dir():
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    print(f"[OK] Copiado diretorio: {dest}")
                    copied_count += 1
                else:
                    # Se for arquivo, garantir que o diretório pai existe
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    print(f"[OK] Copiado arquivo: {dest}")
                    copied_count += 1
            else:
                # Se não existir mas for um diretório que precisa ser criado
                if (
                    dest.endswith(("logs", "temp", "admin"))
                    and not source_path.exists()
                ):
                    dest_path.mkdir(parents=True, exist_ok=True)
                    print(f"[OK] Criado diretorio: {dest}")
                    copied_count += 1
                else:
                    print(f"[AVISO] Nao encontrado: {source}")
                    skipped_count += 1
        except Exception as e:
            print(f"[ERRO] Erro ao copiar {source}: {e}")
            error_count += 1

    print("\n" + "=" * 60)
    print(f"Resumo:")
    print(f"  [OK] Copiados: {copied_count}")
    print(f"  [AVISO] Ignorados: {skipped_count}")
    print(f"  [ERRO] Erros: {error_count}")
    print("=" * 60)

    if error_count == 0:
        print("\n[OK] Todos os arquivos necessarios foram copiados com sucesso!")
        return True
    else:
        print(
            f"\n[AVISO] Alguns arquivos nao foram copiados. Verifique os erros acima."
        )
        return False


if __name__ == "__main__":
    success = copy_data_files()
    sys.exit(0 if success else 1)
