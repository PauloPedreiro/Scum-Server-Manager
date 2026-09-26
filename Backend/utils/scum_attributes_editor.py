import os
import sqlite3
import struct
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_ATTRS_MAP: Dict[str, bytes] = {
    "strength": b"BaseStrength",
    "constitution": b"BaseConstitution",
    "dexterity": b"BaseDexterity",
    "intelligence": b"BaseIntelligence",
}


def _read_double_at(data: bytes, offset: int) -> Optional[float]:
    if offset < 0 or offset + 8 > len(data):
        return None
    return struct.unpack("<d", data[offset : offset + 8])[0]


def _write_double_at(buf: bytearray, offset: int, value: float) -> bool:
    if offset < 0 or offset + 8 > len(buf):
        return False
    buf[offset : offset + 8] = struct.pack("<d", float(value))
    return True


def round_attribute_value(val: float) -> float:
    """
    Arredonda o valor do atributo para o inteiro mais próximo se estiver muito próximo dele
    (diferença menor que 0.15), caso contrário mantém a precisão com duas casas decimais.
    Isso evita que valores como 4.9 sejam lidos e salvos como 4.9 em vez do nível cheio 5.0.
    """
    nearest_int = round(val)
    if abs(val - nearest_int) < 0.15:
        return float(nearest_int)
    return round(val, 2)


def fetch_prisoners(cursor: sqlite3.Cursor) -> List[Dict[str, Any]]:
    try:
        cursor.execute(
            """
            SELECT p.id AS prisoner_id, u.user_id AS steam_id, u.name AS name
            FROM prisoner p
            LEFT JOIN user_profile u ON u.prisoner_id = p.id
            ORDER BY p.id ASC
            """
        )
        rows = cursor.fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            prisoner_id, steam_id, name = row[0], row[1], row[2]
            results.append(
                {
                    "prisoner_id": prisoner_id,
                    "steam_id": str(steam_id) if steam_id is not None else None,
                    "name": name,
                }
            )
        return results
    except sqlite3.Error:
        return []


def resolve_prisoner_identifier(
    cursor: sqlite3.Cursor, identifier: str
) -> Optional[Dict[str, Any]]:
    ident = (identifier or "").strip()
    if not ident:
        return None

    prisoner_id: Optional[int] = None
    steam_id: Optional[str] = None

    if ident.isdigit() and len(ident) >= 15:
        steam_id = ident
    else:
        try:
            prisoner_id = int(ident)
        except Exception:
            steam_id = ident

    if prisoner_id is not None:
        cursor.execute(
            """
            SELECT p.id AS prisoner_id, u.user_id AS steam_id, u.name AS name
            FROM prisoner p
            LEFT JOIN user_profile u ON u.prisoner_id = p.id
            WHERE p.id = ?
            """,
            (prisoner_id,),
        )
    else:
        cursor.execute(
            """
            SELECT p.id AS prisoner_id, u.user_id AS steam_id, u.name AS name
            FROM user_profile u
            INNER JOIN prisoner p ON u.prisoner_id = p.id
            WHERE CAST(u.user_id AS TEXT) = ?
            """,
            (steam_id,),
        )

    row = cursor.fetchone()
    if not row:
        return None

    return {
        "prisoner_id": row[0],
        "steam_id": str(row[1]) if row[1] is not None else None,
        "name": row[2],
    }


def get_prisoner_attributes(
    cursor: sqlite3.Cursor, prisoner_id: int
) -> Optional[Dict[str, float]]:
    cursor.execute(
        "SELECT body_simulation FROM prisoner WHERE id = ?", (int(prisoner_id),)
    )
    row = cursor.fetchone()
    if not row:
        return None

    data = bytes(row[0])

    values: Dict[str, float] = {}
    for slug, key in _ATTRS_MAP.items():
        pos = data.find(key)
        val = 0.0
        if pos != -1:
            prop = data.find(b"DoubleProperty", pos)
            # LIMIT THE SEARCH OF DoubleProperty TO 120 BYTES AFTER THE KEY!
            if prop != -1 and (prop - pos) < 120:
                offset = prop + 24
                read_val = _read_double_at(data, offset)
                if read_val is not None:
                    val = round_attribute_value(float(read_val))
        values[slug] = val

    return values


def update_prisoner_attributes(
    cursor: sqlite3.Cursor,
    prisoner_id: int,
    new_values: Dict[str, float],
) -> Tuple[bool, List[str]]:
    cursor.execute(
        "SELECT body_simulation FROM prisoner WHERE id = ?", (int(prisoner_id),)
    )
    row = cursor.fetchone()
    if not row:
        return False, []

    buf = bytearray(row[0])
    changes = 0
    logs: List[str] = []

    for slug, value in new_values.items():
        key = _ATTRS_MAP.get(slug)
        if not key:
            continue

        pos = buf.find(key)
        if pos == -1:
            continue

        prop = buf.find(b"DoubleProperty", pos)
        # Limitar busca a 120 bytes após a chave para evitar cruzamento de atributos
        if prop == -1 or (prop - pos) >= 120:
            continue

        offset = prop + 24
        old_val = _read_double_at(buf, offset)
        if old_val is None:
            continue

        if float(old_val) != float(value):
            if _write_double_at(buf, offset, float(value)):
                changes += 1
                logs.append(f"{slug}: {old_val:.2f} -> {float(value):.2f}")

    if changes <= 0:
        return False, []

    cursor.execute(
        "UPDATE prisoner SET body_simulation = ? WHERE id = ?", (buf, int(prisoner_id))
    )
    return True, logs


def create_scum_db_backup(
    scum_db_path: str, backup_root_dir: str = "data/backups/scum_db", keep_last_n: int = 20
) -> str:
    src = Path(scum_db_path)
    if not src.exists():
        raise FileNotFoundError(f"SCUM.db não encontrado: {scum_db_path}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst_dir = Path(backup_root_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"SCUM.db.{ts}.bak"

    import shutil

    shutil.copy2(str(src), str(dst))

    try:
        n = int(keep_last_n or 0)
    except Exception:
        n = 0
    if n > 0:
        try:
            backups = list(dst_dir.glob("SCUM.db.*.bak"))
            # Ordenar por mtime (mais novo primeiro)
            backups.sort(key=lambda p: float(p.stat().st_mtime), reverse=True)
            for old in backups[n:]:
                try:
                    old.unlink(missing_ok=True)
                except Exception:
                    try:
                        os.remove(str(old))
                    except Exception:
                        pass
        except Exception:
            pass

    return str(dst)


SKILL_GROUPS = {
    "strength": [
        "BoxingSkill",        # Briga
        "MeleeWeaponsSkill",  # Armas brancas
        "ArcherySkill",       # Arquearia
        "RiflesSkill",        # Fuzis
        "HandgunSkill",       # Pistola
    ],
    "constitution": [
        "RunningSkill",
        "EnduranceSkill",
    ],
    "dexterity": [
        "ThieverySkill",
        "DemolitionSkill",
        "StealthSkill",
        "DrivingSkill",
        "MotorcycleSkill",
        "AviationSkill",
    ],
    "intelligence": [
        "AwarenessSkill",
        "CamouflageSkill",
        "CookingSkill",
        "MedicalSkill",
        "SnipingSkill",
        "SurvivalSkill",
        "EngineeringSkill",
        "FarmingSkill",
    ],
}

SKILL_RCON_NAMES = {
    "BoxingSkill": "Brawling",
    "MeleeWeaponsSkill": "Melee Weapons",
    "ArcherySkill": "Archery",
    "RiflesSkill": "Rifles",
    "HandgunSkill": "Handgun",
    "RunningSkill": "Running",
    "EnduranceSkill": "Endurance",
    "ThieverySkill": "Thievery",
    "DemolitionSkill": "Demolition",
    "StealthSkill": "Stealth",
    "DrivingSkill": "Driving",
    "MotorcycleSkill": "Motorcycling",
    "AviationSkill": "Aviation",
    "AwarenessSkill": "Awareness",
    "CamouflageSkill": "Camouflage",
    "CookingSkill": "Cooking",
    "MedicalSkill": "Medical",
    "SnipingSkill": "Sniping",
    "SurvivalSkill": "Survival",
    "EngineeringSkill": "Engineering",
    "FarmingSkill": "Farming",
}


def _format_attr_value(val: float) -> str:
    """
    Formata valor de atributo para envio RCON.
    Se o valor for um inteiro exato (ex: 5.0), envia como '5.00' (duas casas decimais
    mantidas para compatibilidade RCON), mas normaliza para evitar que 4.9 seja enviado
    quando o alvo é 5.
    """
    # Normaliza valores próximos de inteiro antes de formatar
    normalized = round_attribute_value(val)
    return f"{normalized:.2f}"


def apply_attribute_and_skills_via_rcon(
    rcon_client,
    steam_id: str,
    attribute_name: str,
    target_level: float,
    current_attrs: Dict[str, float],
) -> Tuple[bool, str]:
    """
    Executa os comandos RCON SetAttributes e SetSkillLevel para o jogador online.
    Normaliza os valores antes de enviar para evitar que 4.9 seja enviado quando
    o alvo é 5.0 (causado por imprecisão float no banco SCUM.db).
    """
    import logging
    logger = logging.getLogger("scum_attributes_editor")

    # Normalizar todos os valores antes de enviar
    s_raw = target_level if attribute_name == "strength" else current_attrs.get("strength", 3.0)
    c_raw = target_level if attribute_name == "constitution" else current_attrs.get("constitution", 3.0)
    d_raw = target_level if attribute_name == "dexterity" else current_attrs.get("dexterity", 3.0)
    i_raw = target_level if attribute_name == "intelligence" else current_attrs.get("intelligence", 3.0)

    s = round_attribute_value(float(s_raw))
    c = round_attribute_value(float(c_raw))
    d = round_attribute_value(float(d_raw))
    i = round_attribute_value(float(i_raw))

    # Formatar o comando RCON com valores normalizados
    cmd_attr = f"SetAttributes {s:.2f} {c:.2f} {d:.2f} {i:.2f} {steam_id}"
    logger.debug(
        f"[RCON-ATTR] Enviando SetAttributes para {steam_id}: "
        f"STR={s:.2f} CON={c:.2f} DEX={d:.2f} INT={i:.2f} "
        f"(atributo alvo: {attribute_name}={target_level})"
    )
    res_attr = rcon_client.send_command(cmd_attr)
    logger.debug(f"[RCON-ATTR] Resposta do servidor: {res_attr!r}")

    if not res_attr or "is not online" in res_attr.lower() or "not found" in res_attr.lower():
        return False, f"Jogador {steam_id} não está online no servidor para atualizar via RCON."

    # Atualizar as skills do grupo correspondente
    skills = SKILL_GROUPS.get(attribute_name, [])
    skill_level = int(round(target_level))  # Garantir int exato (ex: 5, não 4)
    for db_skill in skills:
        rcon_skill = SKILL_RCON_NAMES.get(db_skill, db_skill.replace("Skill", ""))
        if " " in rcon_skill and not (rcon_skill.startswith('"') and rcon_skill.endswith('"')):
            rcon_skill = f'"{rcon_skill}"'
        cmd_skill = f"SetSkillLevel {rcon_skill} {skill_level} {steam_id}"
        logger.debug(f"[RCON-SKILL] Enviando: {cmd_skill}")
        rcon_client.send_command(cmd_skill)

    logger.debug(
        f"[RCON-ATTR] Concluído para {steam_id}: {attribute_name}={target_level} "
        f"-> enviado={round_attribute_value(float(target_level)):.2f}"
    )
    return True, "Atributos e skills atualizados com sucesso via RCON."


def update_prisoner_skills_db(
    cursor: sqlite3.Cursor,
    prisoner_id: int,
    attribute_name: str,
    target_level: float,
) -> None:
    """
    Atualiza as skills do grupo do atributo diretamente no banco SCUM.db.
    """
    skills = SKILL_GROUPS.get(attribute_name, [])
    skill_level = int(target_level)

    exp_map = {
        0: 0.0,
        1: 10000.0,
        2: 100000.0,
        3: 1000000.0,
        4: 10000000.0,
        5: 10000000.0,
        6: 10000000.0,
        7: 10000000.0,
        8: 10000000.0,
    }
    exp = exp_map.get(skill_level, 10000.0)

    for skill in skills:
        cursor.execute(
            "SELECT 1 FROM prisoner_skill WHERE prisoner_id = ? AND name = ?",
            (int(prisoner_id), skill),
        )
        if cursor.fetchone():
            cursor.execute(
                "UPDATE prisoner_skill SET level = ?, experience = ? WHERE prisoner_id = ? AND name = ?",
                (skill_level, exp, int(prisoner_id), skill),
            )
        else:
            cursor.execute(
                "INSERT INTO prisoner_skill (prisoner_id, name, level, experience, xml) VALUES (?, ?, ?, ?, NULL)",
                (int(prisoner_id), skill, skill_level, exp),
            )

