"""
Sistema de Identificação Única do Backend
Gera e gerencia Backend ID único para escalabilidade
"""

import uuid
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from utils.app_data_dir import get_runtime_data_dir, migrate_legacy_data_dir


class BackendIdentity:
    def __init__(self):
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            legacy_data_dir = exe_dir / "data"
            data_dir = get_runtime_data_dir(is_exe=True)
            migrate_legacy_data_dir(legacy_data_dir, data_dir, filenames=["identity.json"])
            self.identity_file = str(data_dir / "identity.json")
        else:
            self.identity_file = "data/identity.json"
        self.identity = {}
        self.load_or_create_identity()

    def load_or_create_identity(self):
        """Carregar identidade existente ou criar nova"""
        if os.path.exists(self.identity_file):
            try:
                with open(self.identity_file, "r", encoding="utf-8") as f:
                    self.identity = json.load(f)
                # Identidade carregada (não logar ID completo por segurança)
            except Exception as e:
                print(f"⚠️ Erro ao carregar identidade: {e}")
                self.create_new_identity()
        else:
            self.create_new_identity()

    def create_new_identity(self):
        """Criar nova identidade única"""
        self.identity = {
            "backend_id": f"SCUM-BACKEND-{str(uuid.uuid4()).replace('-', '').upper()[:12]}",
            "owner_id": None,  # Será definido no registro
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0.0",
            "region": "america_south",
            "status": "unregistered",
            "capabilities": [
                "server_control",
                "scheduler",
                "notifications",
                "discord_webhooks",
            ],
        }
        self.save_identity()
        # Nova identidade criada (não logar ID completo por segurança)

    def save_identity(self):
        """Salvar identidade no arquivo"""
        try:
            os.makedirs(os.path.dirname(self.identity_file), exist_ok=True)
            with open(self.identity_file, "w", encoding="utf-8") as f:
                json.dump(self.identity, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro ao salvar identidade: {e}")

    def update_identity(self, updates: Dict[str, Any]):
        """Atualizar campos da identidade"""
        self.identity.update(updates)
        self.identity["last_updated"] = datetime.now().isoformat()
        self.save_identity()
        # Identidade atualizada (não logar dados completos por segurança)

    def get_identity(self) -> Dict[str, Any]:
        """Obter identidade completa"""
        return self.identity.copy()

    def get_backend_id(self) -> str:
        """Obter Backend ID"""
        return self.identity.get("backend_id", "")

    def get_owner_id(self) -> Optional[str]:
        """Obter Owner ID"""
        return self.identity.get("owner_id")

    def set_owner_id(self, owner_id: str):
        """Definir Owner ID"""
        self.update_identity({"owner_id": owner_id, "status": "registered"})

    def set_region(self, region: str):
        """Definir região"""
        self.update_identity({"region": region})

    def is_registered(self) -> bool:
        """Verificar se está registrado"""
        return self.identity.get("status") == "registered"

    def get_identity_summary(self) -> Dict[str, Any]:
        """Obter resumo da identidade para logs"""
        return {
            "backend_id": self.identity.get("backend_id"),
            "owner_id": self.identity.get("owner_id"),
            "status": self.identity.get("status"),
            "region": self.identity.get("region"),
            "version": self.identity.get("version"),
            "created_at": self.identity.get("created_at"),
        }
