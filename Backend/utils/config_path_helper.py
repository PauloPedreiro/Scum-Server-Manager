#!/usr/bin/env python3
"""
Config Path Helper - Função helper para carregar caminhos do config.json
com compatibilidade retroativa para a nova estrutura de paths
"""

import os
import json
import sys
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigPathHelper:
    """Helper para carregar caminhos do config.json com compatibilidade retroativa"""

    def __init__(self, config: Dict[str, Any]):
        """Inicializar com configuração carregada"""
        self.config = config
        self.paths = config.get("paths", {})
        self.application_paths = self.paths.get("application", {})
        self.scum_server_paths = self.paths.get("scum_server", {})

        # Detectar se está rodando como executável
        if getattr(sys, "frozen", False):
            # Rodando como executável - usar diretório do .exe como base
            self.base_dir = Path(sys.executable).parent
        else:
            # Rodando como script - usar diretório atual
            self.base_dir = Path.cwd()

    def get_application_path(self, key: str, fallback: Optional[str] = None) -> str:
        """Obter caminho da aplicação com fallback"""
        # Tentar nova estrutura primeiro
        if key in self.application_paths:
            path = self.application_paths[key]
            # Se for caminho relativo e estivermos em executável, tornar absoluto
            if not os.path.isabs(path) and getattr(sys, "frozen", False):
                return str(self.base_dir / path)
            return path

        # Fallbacks para estrutura antiga
        fallbacks = {
            "logs_directory": self.config.get("logging", {}).get(
                "log_dir", "data/logs"
            ),
            "database": "data/SSM.db",
            "data_directory": "data",
        }

        fallback_path = fallbacks.get(key, fallback or "")
        # Se for caminho relativo e estivermos em executável, tornar absoluto
        if (
            fallback_path
            and not os.path.isabs(fallback_path)
            and getattr(sys, "frozen", False)
        ):
            return str(self.base_dir / fallback_path)
        return fallback_path

    def get_scum_server_path(self, key: str, fallback: Optional[str] = None) -> str:
        """Obter caminho do servidor SCUM com fallback"""
        # Tentar nova estrutura primeiro
        if key in self.scum_server_paths:
            return self.scum_server_paths[key]

        # Fallbacks para estrutura antiga (compatibilidade retroativa)
        # Primeiro tenta seção 'server' (estrutura antiga), depois valores padrão
        server_config = self.config.get("server", {})
        fallbacks = {
            "root_directory": server_config.get("install_path", "C:\\Servers\\Scum"),
            "binaries_directory": server_config.get(
                "server_path", "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64"
            ),
            "logs_directory": server_config.get(
                "logs_directory", "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs"
            ),
            "config_directory": self.config.get("notifications", {}).get(
                "scum_config_path",
                "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer",
            ),
            "database": self.config.get("weather_scheduler", {}).get(
                "scum_db_path", "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"
            ),
        }

        return fallbacks.get(key, fallback or "")

    def get_scum_db_path(self) -> str:
        """Obter caminho do banco SCUM.db com múltiplos fallbacks"""
        # Tentar nova estrutura
        if "database" in self.scum_server_paths:
            return self.scum_server_paths["database"]

        # Fallbacks para estrutura antiga
        fallbacks = [
            self.config.get("weather_scheduler", {}).get("scum_db_path"),
            self.config.get("fishing_ranking", {}).get("scum_db_path"),
            "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
        ]

        for fallback in fallbacks:
            if fallback:
                return fallback

        return "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db"

    def get_ssm_db_path(self) -> str:
        """Obter caminho do banco SSM.db"""
        return self.get_application_path("database", "data/SSM.db")

    def get_logs_directory(self) -> str:
        """Obter diretório de logs da aplicação"""
        return self.get_application_path("logs_directory", "data/logs")

    def get_scum_logs_directory(self) -> str:
        """Obter diretório de logs do SCUM"""
        return self.get_scum_server_path(
            "logs_directory", "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs"
        )

    def validate_paths(self) -> Dict[str, bool]:
        """Validar se os caminhos existem"""
        validation = {}

        # Validar caminhos da aplicação
        app_paths = {
            "data_directory": self.get_application_path("data_directory"),
            "logs_directory": self.get_logs_directory(),
            "database": self.get_ssm_db_path(),
        }

        for key, path in app_paths.items():
            validation[f"application_{key}"] = os.path.exists(path)

        # Validar caminhos do servidor SCUM
        scum_paths = {
            "root_directory": self.get_scum_server_path("root_directory"),
            "binaries_directory": self.get_scum_server_path("binaries_directory"),
            "logs_directory": self.get_scum_logs_directory(),
            "database": self.get_scum_db_path(),
        }

        for key, path in scum_paths.items():
            validation[f"scum_{key}"] = os.path.exists(path)

        return validation


def load_config_with_paths(
    config_file: str = "data/config.json",
) -> tuple[Dict[str, Any], ConfigPathHelper]:
    """Carregar config.json e retornar config + helper de paths"""
    import sys
    from pathlib import Path

    try:
        # Se o caminho é relativo e estamos em um executável, ajustar
        if not Path(config_file).is_absolute():
            if getattr(sys, "frozen", False):
                # Rodando como executável - usar diretório do .exe
                exe_dir = Path(sys.executable).parent
                config_path = exe_dir / config_file
            else:
                # Rodando como script - usar caminho relativo normal
                config_path = Path(config_file)
        else:
            config_path = Path(config_file)

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Garantir chaves padrão para squad_tk_jail
        if "squad_tk_jail" not in config:
            config["squad_tk_jail"] = {
                "enabled": False,
                "jail_coordinates": "-271417.281 314246.875 84056.023",
                "jail_radius_meters": 20.0,
                "jail_duration_minutes": 30,
                "warning_color": "2",
                "use_colors": True,
                "announcement_message": "{killer} matou o companheiro de squad {victim} e foi enviado para a prisão por {minutes} minutos!",
                "escape_message": "{player}, você tentou escapar! Retornando para a cela.",
                "release_message": "{player} cumpriu sua pena e foi libertado!"
            }
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        path_helper = ConfigPathHelper(config)
        return config, path_helper

    except Exception as e:
        raise Exception(f"Erro ao carregar configuração: {e}")


# Exemplo de uso:
if __name__ == "__main__":
    try:
        config, paths = load_config_with_paths()

        print("=== Configuração Carregada ===")
        print(f"SCUM DB: {paths.get_scum_db_path()}")
        print(f"SSM DB: {paths.get_ssm_db_path()}")
        print(f"Logs App: {paths.get_logs_directory()}")
        print(f"Logs SCUM: {paths.get_scum_logs_directory()}")

        print("\n=== Validacao de Caminhos ===")
        validation = paths.validate_paths()
        for path, exists in validation.items():
            status = "OK" if exists else "ERRO"
            print(f"{status} {path}: {exists}")

    except Exception as e:
        print(f"Erro: {e}")
