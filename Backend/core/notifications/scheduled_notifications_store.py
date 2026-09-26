import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ScheduledNotification:
    id: str
    enabled: bool
    title: str
    message: str
    color: str
    duration: int
    schedule: Dict[str, Any]
    created_at: str
    updated_at: str


class ScheduledNotificationsStore:
    def __init__(self, base_path: Path, logger=None):
        self.base_path = base_path
        self.logger = logger
        self.config_path = self.base_path / "config"
        self.file_path = self.config_path / "scheduled_notifications.json"
        self._ensure_dirs()
        self._ensure_file()

    def _ensure_dirs(self):
        self.config_path.mkdir(parents=True, exist_ok=True)

    def _ensure_file(self):
        if self.file_path.exists():
            return
        data = {"version": 1, "items": []}
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"version": 1, "items": []}
            if "items" not in data or not isinstance(data.get("items"), list):
                data["items"] = []
            if "version" not in data:
                data["version"] = 1
            return data
        except Exception:
            return {"version": 1, "items": []}

    def save(self, data: Dict[str, Any]):
        tmp_path = str(self.file_path) + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.file_path)

    def list_items(self) -> List[Dict[str, Any]]:
        return list(self.load().get("items", []))

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        for item in self.list_items():
            if item.get("id") == item_id:
                return item
        return None

    def upsert_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        data = self.load()
        items = data.get("items", [])
        existing_idx = None
        for i, it in enumerate(items):
            if it.get("id") == item.get("id"):
                existing_idx = i
                break

        now_iso = datetime.now().isoformat()
        if existing_idx is None:
            item.setdefault("created_at", now_iso)
            item["updated_at"] = now_iso
            items.append(item)
        else:
            item.setdefault("created_at", items[existing_idx].get("created_at") or now_iso)
            item["updated_at"] = now_iso
            items[existing_idx] = item

        data["items"] = items
        self.save(data)
        return item

    def delete_item(self, item_id: str) -> bool:
        data = self.load()
        items = data.get("items", [])
        new_items = [it for it in items if it.get("id") != item_id]
        if len(new_items) == len(items):
            return False
        data["items"] = new_items
        self.save(data)
        return True
