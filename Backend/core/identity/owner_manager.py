"""
Gerenciador de Proprietário
Gerencia informações e configurações do proprietário do servidor
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from utils.app_data_dir import get_runtime_data_dir, migrate_legacy_data_dir


class OwnerManager:
    def __init__(self, identity_file: str = "data/identity.json"):
        if identity_file == "data/identity.json" and getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            legacy_data_dir = exe_dir / "data"
            data_dir = get_runtime_data_dir(is_exe=True)
            migrate_legacy_data_dir(legacy_data_dir, data_dir, filenames=["identity.json"])
            self.identity_file = str(data_dir / "identity.json")
        else:
            self.identity_file = identity_file
        self.owner_data = {}
        self.load_owner_data()

    def load_owner_data(self):
        """Carregar dados do proprietário"""
        if os.path.exists(self.identity_file):
            try:
                with open(self.identity_file, "r", encoding="utf-8") as f:
                    identity_data = json.load(f)
                    self.owner_data = identity_data.get("owner_data", {})
            except Exception as e:
                print(f"⚠️ Erro ao carregar dados do proprietário: {e}")
                self.owner_data = {}

    def set_owner_info(
        self,
        owner_id: str,
        owner_name: str,
        email: str = None,
        region: str = "america_south",
    ):
        """Definir informações do proprietário"""
        self.owner_data = {
            "owner_id": owner_id,
            "owner_name": owner_name,
            "email": email,
            "region": region,
            "server_name": f"Servidor de {owner_name}",
            "license_type": "individual",  # individual, premium, enterprise
            "max_servers": 1,
            "features": [
                "server_control",
                "scheduler",
                "notifications",
                "discord_webhooks",
            ],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
        self.save_owner_data()
        print(f"👤 Proprietário definido: {owner_name} ({owner_id})")

    def save_owner_data(self):
        """Salvar dados do proprietário"""
        try:
            if os.path.exists(self.identity_file):
                with open(self.identity_file, "r", encoding="utf-8") as f:
                    identity_data = json.load(f)
            else:
                identity_data = {}

            identity_data["owner_data"] = self.owner_data

            with open(self.identity_file, "w", encoding="utf-8") as f:
                json.dump(identity_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro ao salvar dados do proprietário: {e}")

    def get_owner_info(self) -> Dict[str, Any]:
        """Obter informações do proprietário"""
        return self.owner_data.copy()

    def get_owner_id(self) -> Optional[str]:
        """Obter Owner ID"""
        return self.owner_data.get("owner_id")

    def get_server_name(self) -> str:
        """Obter nome do servidor"""
        return self.owner_data.get("server_name", "Meu Servidor SCUM")

    def get_region(self) -> str:
        """Obter região"""
        return self.owner_data.get("region", "america_south")

    def get_license_type(self) -> str:
        """Obter tipo de licença"""
        return self.owner_data.get("license_type", "individual")

    def get_max_servers(self) -> int:
        """Obter número máximo de servidores"""
        return self.owner_data.get("max_servers", 1)

    def get_features(self) -> list:
        """Obter funcionalidades disponíveis"""
        return self.owner_data.get("features", [])

    def has_feature(self, feature: str) -> bool:
        """Verificar se tem funcionalidade específica"""
        return feature in self.get_features()

    def update_server_name(self, server_name: str):
        """Atualizar nome do servidor"""
        self.owner_data["server_name"] = server_name
        self.owner_data["last_updated"] = datetime.now().isoformat()
        self.save_owner_data()
        print(f"🔄 Nome do servidor atualizado: {server_name}")

    def is_owner_configured(self) -> bool:
        """Verificar se proprietário está configurado"""
        return bool(self.owner_data.get("owner_id"))
