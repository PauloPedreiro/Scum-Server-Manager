import json
import uuid
import os
import threading
from typing import List, Dict, Any, Optional
from utils.logger import StructuredLogger

class RconRoutineManager:
    """
    Gerencia o arquivo de configuração de rotinas RCON (data/rcon_routines.json).
    Lida com o CRUD das rotinas de comando com concorrência segura.
    """
    def __init__(self, file_path: str, logger: Optional[Any] = None):
        self.file_path = file_path
        self.logger = logger or StructuredLogger()
        self._lock = threading.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Garante que o arquivo JSON existe no disco e inicializa com rotinas padrão se estiver vazio."""
        with self._lock:
            exists = os.path.exists(self.file_path)
            is_empty = False
            if exists:
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if not content or content == "[]":
                            is_empty = True
                except Exception:
                    is_empty = True

            if not exists or is_empty:
                try:
                    os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                    default_routines = [
                        {
                            "id": "e605d8f6-df30-4e14-9b2f-2d645fc11b43",
                            "name": "Limpeza e Manutenção do Servidor (Itens/Corpos)",
                            "interval_minutes": 180,
                            "enabled": False,
                            "last_run": None,
                            "commands": [
                                "#DestroyAllItemsWithinRadius LuisMoncada_Boots_01 25420000",
                                "#DestroyAllItemsWithinRadius LuisMoncada_Glove_01 25420000",
                                "#DestroyAllItemsWithinRadius Danny_Trejo_Glove_01 25420000",
                                "#DestroyAllItemsWithinRadius Danny_Trejo_Boots_01 25420000",
                                "#DestroyAllItemsWithinRadius 1H_DannyMachete 25420000",
                                "#DestroyAllItemsWithinRadius Inmate_pants 25420000",
                                "#DestroyAllItemsWithinRadius HighTop_Shoes 25420000",
                                "#DestroyAllItemsWithinRadius Underpants_01 25420000",
                                "#DestroyAllItemsWithinRadius F_Undershirt_Bra_01 25420000",
                                "#DestroyAllItemsWithinRadius Sock_01 25420000",
                                "#DestroyAllItemsWithinRadius F_Bra_Supporter_01 25420000",
                                "#DestroyAllItemsWithinRadius Undershirt_01 25420000",
                                "#DestroyAllItemsWithinRadius Scum_Shirt_Supporter_Pack_Black_01 25420000",
                                "#DestroyAllItemsWithinRadius Improvised_Bag_Small_01 25420000",
                                "#DestroyAllItemsWithinRadius PenisWarmer_01 25420000",
                                "#DestroyAllItemsWithinRadius 1H_Hatchet 25420000",
                                "#DestroyAllItemsWithinRadius Prisoner_Head 25420000",
                                "#DestroyAllItemsWithinRadius Danny_Trejo_Vest 25420000",
                                "#DestroyAllItemsWithinRadius Danny_Trejo_Pants 25420000",
                                "#DestroyAllItemsWithinRadius Boxer_Briefs_01 25420000",
                                "#DestroyAllItemsWithinRadius Socks_02 25420000",
                                "#DestroyAllItemsWithinRadius Classic_Shirt_02 25420000",
                                "#DestroyAllItemsWithinRadius Raymond_Cruz_Boots 25420000",
                                "#DestroyAllItemsWithinRadius Raymond_Cruz_Hat 25420000",
                                "#DestroyAllItemsWithinRadius LuisMoncada_Jacket 25420000",
                                "#DestroyAllItemsWithinRadius Raymond_Cruz_Shirt 25420000",
                                "#DestroyAllItemsWithinRadius LuisMoncada_Pants 25420000",
                                "#DestroyAllItemsWithinRadius Raymond_Cruz_Pants 25420000",
                                "#DestroyAllItemsWithinRadius 1H_RaymondCruz_Knife 25420000",
                                "#DestroyAllItemsWithinRadius Inmate_shirt_01 25420000",
                                "#DestroyAllItemsWithinRadius Inmate_Pants_01_Forest_DigitalDeluxe 25420000",
                                "#DestroyAllItemsWithinRadius Inmate_Pants_01_Snow_DigitalDeluxe 25420000",
                                "#DestroyAllItemsWithinRadius Inmate_Shirt_01_South_DigitalDeluxe 25420000",
                                "#DestroyAllItemsWithinRadius TwD_EnlistedMilitary_Cap_01 25420000",
                                "#DestroyAllItemsWithinRadius TwD_EnlistedMilitary_Jacket_01 25420000",
                                "#DestroyAllItemsWithinRadius TwD_EnlistedMilitary_Pants_01 25420000",
                                "Backpack_DigitalDeluxe 25420000",
                                "LuisMoncada_Boots 25420000",
                                "DestroyCorpsesWithinRadius 25420000"
                            ],
                            "warning_enabled": False,
                            "warning_message": "AVISO - LIMPEZA DO MAPA EM {minutes} MINUTOS!",
                            "warning_color": "#FF0000",
                            "warning_minutes_before": 5,
                            "last_warning_run": None
                        }
                    ]
                    with open(self.file_path, "w", encoding="utf-8") as f:
                        json.dump(default_routines, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"Criado arquivo de rotinas RCON com regras padrão em: {self.file_path}")
                except Exception as e:
                    self.logger.error(f"Erro ao criar arquivo de rotinas RCON em {self.file_path}: {e}")

    def load_routines(self) -> List[Dict[str, Any]]:
        """Carrega e retorna todas as rotinas."""
        with self._lock:
            if not os.path.exists(self.file_path):
                return []
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    return []
            except Exception as e:
                self.logger.error(f"Erro ao ler rotinas RCON de {self.file_path}: {e}")
                return []

    def save_routines(self, routines: List[Dict[str, Any]]) -> bool:
        """Salva a lista completa de rotinas no disco."""
        with self._lock:
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(routines, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                self.logger.error(f"Erro ao salvar rotinas RCON em {self.file_path}: {e}")
                return False

    def get_routines(self) -> List[Dict[str, Any]]:
        """Retorna todas as rotinas (alias seguro)."""
        return self.load_routines()

    def get_routine(self, routine_id: str) -> Optional[Dict[str, Any]]:
        """Retorna uma rotina específica pelo ID."""
        routines = self.load_routines()
        for r in routines:
            if r.get("id") == routine_id:
                return r
        return None

    def add_routine(self, name: str, interval_minutes: int, commands: List[str], enabled: bool = True,
                    warning_enabled: bool = False, warning_message: str = "", warning_color: str = "",
                    warning_minutes_before: int = 5) -> Dict[str, Any]:
        """Cria e adiciona uma nova rotina RCON."""
        routines = self.load_routines()
        new_routine = {
            "id": str(uuid.uuid4()),
            "name": name,
            "interval_minutes": max(1, int(interval_minutes)),
            "enabled": bool(enabled),
            "last_run": None,
            "commands": [cmd.strip() for cmd in commands if cmd.strip()],
            "warning_enabled": bool(warning_enabled),
            "warning_message": str(warning_message),
            "warning_color": str(warning_color),
            "warning_minutes_before": max(1, int(warning_minutes_before)),
            "last_warning_run": None
        }
        routines.append(new_routine)
        self.save_routines(routines)
        self.logger.info(f"Nova rotina RCON adicionada: '{name}' (ID: {new_routine['id']})")
        return new_routine

    def update_routine(self, routine_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualiza campos específicos de uma rotina."""
        routines = self.load_routines()
        for r in routines:
            if r.get("id") == routine_id:
                if "name" in data:
                    r["name"] = str(data["name"])
                if "interval_minutes" in data:
                    r["interval_minutes"] = max(1, int(data["interval_minutes"]))
                if "enabled" in data:
                    r["enabled"] = bool(data["enabled"])
                if "commands" in data:
                    r["commands"] = [cmd.strip() for cmd in data["commands"] if cmd.strip()]
                if "last_run" in data:
                    r["last_run"] = data["last_run"]
                if "warning_enabled" in data:
                    r["warning_enabled"] = bool(data["warning_enabled"])
                if "warning_message" in data:
                    r["warning_message"] = str(data["warning_message"])
                if "warning_color" in data:
                    r["warning_color"] = str(data["warning_color"])
                if "warning_minutes_before" in data:
                    r["warning_minutes_before"] = max(1, int(data["warning_minutes_before"]))
                if "last_warning_run" in data:
                    r["last_warning_run"] = data["last_warning_run"]
                
                self.save_routines(routines)
                self.logger.info(f"Rotina RCON atualizada: '{r['name']}' (ID: {routine_id})")
                return r
        return None

    def delete_routine(self, routine_id: str) -> bool:
        """Remove uma rotina pelo ID."""
        routines = self.load_routines()
        original_len = len(routines)
        routines = [r for r in routines if r.get("id") != routine_id]
        if len(routines) < original_len:
            self.save_routines(routines)
            self.logger.info(f"Rotina RCON deletada: ID {routine_id}")
            return True
        return False

    def update_last_run(self, routine_id: str, timestamp: float) -> bool:
        """Atualiza a data da última execução da rotina."""
        routines = self.load_routines()
        for r in routines:
            if r.get("id") == routine_id:
                r["last_run"] = timestamp
                self.save_routines(routines)
                return True
        return False

    def update_last_warning_run(self, routine_id: str, timestamp: float) -> bool:
        """Atualiza a data do último envio do aviso da rotina."""
        routines = self.load_routines()
        for r in routines:
            if r.get("id") == routine_id:
                r["last_warning_run"] = timestamp
                self.save_routines(routines)
                return True
        return False
