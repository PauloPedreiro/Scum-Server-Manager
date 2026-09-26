import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from utils.scum_attributes_editor import create_scum_db_backup
from utils.logger import StructuredLogger


@dataclass
class ChestSpawnResult:
    spawned: int
    errors: List[str]


class ScumChestSpawner:
    def __init__(self, scum_db_path: str, logger: Optional[StructuredLogger] = None):
        self.scum_db_path = scum_db_path
        self.logger = logger or StructuredLogger()

    def spawn_into_chest(self, chest_id: int, item_setup: str, qty: int) -> ChestSpawnResult:
        if qty <= 0:
            return ChestSpawnResult(spawned=0, errors=[])

        try:
            from utils.restart_guard import should_block_scum_db_access

            if should_block_scum_db_access(
                component="ScumChestSpawner",
                operation="spawn_into_chest",
                scum_db_path=self.scum_db_path,
            ):
                return ChestSpawnResult(spawned=0, errors=["SCUM_DB_BLOCKED_RESTART_GUARD"])
        except Exception:
            pass

        backup_path = None
        try:
            backup_path = create_scum_db_backup(self.scum_db_path)
        except Exception:
            backup_path = None

        spawned = 0
        errors: List[str] = []
        conn = sqlite3.connect(self.scum_db_path, timeout=30.0)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT id, entity_system_id FROM entity WHERE id = ?", (int(chest_id),))
            chest = cur.fetchone()
            if not chest:
                return ChestSpawnResult(spawned=0, errors=["CHEST_NOT_FOUND_SCUMDB"])

            entity_system_id = int(chest["entity_system_id"])

            cur.execute(
                """
                SELECT id FROM entity_component
                WHERE entity_id = ? AND name = 'Inventory'
                LIMIT 1
                """,
                (int(chest_id),),
            )
            comp = cur.fetchone()
            if not comp:
                return ChestSpawnResult(spawned=0, errors=["CHEST_NO_INVENTORY"])
            comp_id = int(comp["id"])

            # occupied slots
            cur.execute(
                """
                SELECT data FROM entity_inventory_component_entry
                WHERE entity_component_id = ?
                """,
                (comp_id,),
            )
            occupied: Set[int] = {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}

            cur.execute("SELECT COALESCE(MAX(id), 0) FROM entity")
            next_entity_id = int(cur.fetchone()[0] or 0) + 1

            for _ in range(int(qty)):
                slot_index = 0
                while slot_index in occupied:
                    slot_index += 1
                occupied.add(slot_index)

                cur.execute(
                    """
                    INSERT INTO entity (
                        id, entity_system_id, class,
                        location_x, location_y, location_z,
                        rotation_x, rotation_y, rotation_z,
                        scale_x, scale_y, scale_z,
                        flags, owning_entity_id, parent_entity_id
                    ) VALUES (?, ?, ?, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 32, ?, ?)
                    """,
                    (int(next_entity_id), int(entity_system_id), str(item_setup), int(chest_id), int(chest_id)),
                )

                cur.execute(
                    """
                    INSERT INTO item_entity(entity_id, health, max_health, flags)
                    VALUES(?, 100.0, 100.0, 2)
                    """,
                    (int(next_entity_id),),
                )

                cur.execute(
                    """
                    INSERT INTO entity_inventory_component_entry(entity_component_id, entity_id, data)
                    VALUES(?, ?, ?)
                    """,
                    (int(comp_id), int(next_entity_id), int(slot_index)),
                )

                spawned += 1
                next_entity_id += 1

            conn.commit()
            return ChestSpawnResult(spawned=spawned, errors=[])

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            errors.append(f"SPAWN_FAILED:{e}")
            # No auto restore from backup here; keep behavior consistent with backend policy
            return ChestSpawnResult(spawned=spawned, errors=errors)
        finally:
            try:
                conn.close()
            except Exception:
                pass
