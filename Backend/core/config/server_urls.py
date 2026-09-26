#!/usr/bin/env python3
"""
Configuração Centralizada de URLs de Servidores
ÚNICO LOCAL onde as URLs são definidas - todas as outras partes do sistema importam daqui
"""

# ============================================================================
# CONFIGURAÇÃO DE SERVIDORES DE LICENCIAMENTO
# ============================================================================
# SEGURANÇA: URLs hardcoded para prevenir manipulação via config.json
# Para desenvolvimento/teste local, altere estas constantes:
LICENSE_SERVER_URL = "http://localhost:8000"  # Dev: localhost
GESTAO_SERVER_URL = "http://localhost:8000"   # Dev: localhost
# ============================================================================


def get_license_server_url() -> str:
    """
    Obter URL do servidor de licenciamento

    Returns:
        str: URL do servidor de licenciamento
    """
    return LICENSE_SERVER_URL


def get_gestao_server_url() -> str:
    """
    Obter URL do servidor de Gestão

    Returns:
        str: URL do servidor de Gestão
    """
    return GESTAO_SERVER_URL
