import json
import os
import sqlite3
import time
import uuid
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.shop.db import ssm_tx
from utils.logger import StructuredLogger
from utils.scum_attributes_editor import create_scum_db_backup


@dataclass
class BaseMaterialDryRunResult:
    flag_id: int
    internal_base_id: int
    target_level: int
    stats: Dict[str, int]
    changes_sample: List[Dict[str, Any]]
    debug: Dict[str, Any]


@dataclass
class BaseMaterialRunOnceResult:
    claimed: int
    updated: int
    no_changes: int
    failed: int
    job_ids: List[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


_LEVELS = {
    "Twig": 1,
    "Wood": 2,
    "Metal": 3,
    "Brick": 4,
    "Cement": 5,
}


_MATERIAL_TOKEN_RE = re.compile(r"_(Twig|Wood|Metal|Brick|Cement)(?:_|$)", re.IGNORECASE)


def _short_name(asset_path: str) -> str:
    last = str(asset_path).split("/")[-1]
    if "." in last:
        parts = last.split(".")
        if len(parts) >= 2:
            return parts[-2]
    return last


def _parse_asset_for_template(asset_path: str) -> Tuple[str, str, Optional[str], Optional[int]]:
    short = _short_name(asset_path)

    material: Optional[str] = None
    level: Optional[int] = None
    family_key = short

    m = None
    for m2 in _MATERIAL_TOKEN_RE.finditer(short):
        m = m2
    if m:
        material = str(m.group(1))
        material_norm = material[:1].upper() + material[1:].lower()
        level = _LEVELS.get(material_norm)
        family_key = short[: m.start()]

    return short, family_key, material, level


class BaseMaterialJobService:
    DEFAULT_LOCK_TTL_SECONDS = 2 * 60
    DEFAULT_MAX_ATTEMPTS = 5

    _UPGR_TO_BASIC_RE = re.compile(r"_Upgr(_\d+)?_", re.IGNORECASE)

    def __init__(
        self,
        *,
        ssm_db_path: str,
        scum_db_path: str,
        template_db_path: str = "data/templates/scum_base_template.db",
        logger: Optional[StructuredLogger] = None,
    ):
        self.ssm_db_path = str(ssm_db_path)
        self.scum_db_path = str(scum_db_path)
        self.template_db_path = str(template_db_path)
        self.logger = logger or StructuredLogger()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS base_material_job (
                    job_id TEXT PRIMARY KEY,
                    flag_id INTEGER NOT NULL,
                    target_level INTEGER NOT NULL,
                    fallback_lowest INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TEXT,
                    locked_by TEXT,
                    locked_at TEXT,
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_base_material_job_pick
                ON base_material_job(status, next_attempt_at, created_at)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS base_material_flag_policy (
                    flag_id INTEGER PRIMARY KEY,
                    twig_locked INTEGER NOT NULL DEFAULT 0,
                    min_allowed_level INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )

    def _is_twig_locked(self, flag_id: int) -> Tuple[bool, int]:
        try:
            with ssm_tx(self.ssm_db_path) as conn:
                cur = conn.execute(
                    "SELECT twig_locked, min_allowed_level FROM base_material_flag_policy WHERE flag_id=?",
                    (int(flag_id),),
                )
                row = cur.fetchone()
                if not row:
                    return False, 1
                twig_locked = bool(int(row[0] or 0))
                min_allowed = int(row[1] or 1)
                return twig_locked, min_allowed
        except Exception:
            return False, 1

    def _set_twig_locked(self, flag_id: int, min_allowed_level: int = 2) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                """
                INSERT INTO base_material_flag_policy(flag_id, twig_locked, min_allowed_level, updated_at)
                VALUES(?, 1, ?, datetime('now'))
                ON CONFLICT(flag_id) DO UPDATE
                SET twig_locked=1,
                    min_allowed_level=MAX(excluded.min_allowed_level, base_material_flag_policy.min_allowed_level),
                    updated_at=datetime('now')
                """,
                (int(flag_id), int(min_allowed_level)),
            )

    def _resolve_internal_base_id(self, cur: sqlite3.Cursor, flag_id: int) -> int:
        cur.execute("SELECT base_id FROM base_element WHERE element_id = ? LIMIT 1", (int(flag_id),))
        row = cur.fetchone()
        if not row:
            raise RuntimeError("FLAG_NOT_FOUND")
        return int(row[0])

    def _open_scum_ro(self) -> sqlite3.Connection:
        # Using URI read-only + immutable prevents sqlite from creating WAL/SHM.
        uri = f"file:{Path(self.scum_db_path).resolve().as_posix()}?mode=ro&immutable=1"
        con = sqlite3.connect(uri, uri=True, timeout=10.0)
        con.row_factory = sqlite3.Row
        return con

    def _open_tpl(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.template_db_path), timeout=10.0)
        con.row_factory = sqlite3.Row
        return con

    def _compute_changes(
        self,
        *,
        flag_id: int,
        target_level: int,
        fallback_lowest: bool,
        auto_enrich_whitelist: bool = True,
    ) -> Tuple[int, List[Tuple[int, str, str, str]], Dict[str, int], Dict[str, Any]]:
        if not os.path.exists(self.scum_db_path):
            raise RuntimeError("SCUM_DB_NOT_FOUND")
        if not os.path.exists(self.template_db_path):
            raise RuntimeError("TEMPLATE_DB_NOT_FOUND")

        tpl = self._open_tpl()
        scum = self._open_scum_ro()
        try:
            sc = scum.cursor()
            tp = tpl.cursor()

            internal_base_id = self._resolve_internal_base_id(sc, int(flag_id))

            stats: Dict[str, int] = {
                "total": 0,
                "not_whitelisted": 0,
                "no_family": 0,
                "no_mapping": 0,
                "fallback_lowest_used": 0,
                "already_target": 0,
                "to_change": 0,
            }

            debug: Dict[str, Any] = {
                "not_whitelisted_assets": [],
                "no_mapping_family_keys": [],
                "auto_whitelisted": 0,
                "auto_whitelisted_assets": [],
            }

            sc.execute(
                """
                SELECT be.element_id, be.asset
                FROM base_element be
                WHERE be.base_id = ? AND be.asset IS NOT NULL
                """,
                (int(internal_base_id),),
            )

            rows = sc.fetchall() or []
            if auto_enrich_whitelist and rows:
                inserted = 0
                inserted_assets_sample: List[str] = []
                try:
                    tp.execute("BEGIN")
                    for row in rows:
                        asset = str(row["asset"] or "").strip()
                        if not asset:
                            continue
                        tp.execute(
                            "SELECT 1 FROM asset_whitelist WHERE asset = ? LIMIT 1",
                            (asset,),
                        )
                        if tp.fetchone():
                            continue

                        short, family_key, material, level = _parse_asset_for_template(asset)
                        tp.execute(
                            """
                            INSERT OR IGNORE INTO asset_whitelist(asset, short_name, family_key, material, level)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (asset, short, family_key, material, level),
                        )
                        if tp.rowcount and tp.rowcount > 0:
                            inserted += 1
                            if len(inserted_assets_sample) < 25:
                                inserted_assets_sample.append(asset)
                    tpl.commit()
                except Exception as e:
                    try:
                        tpl.rollback()
                    except Exception:
                        pass
                    try:
                        self.logger.warn(f"[BASE_MATERIAL] Failed to auto-enrich asset_whitelist: {e}")
                    except Exception:
                        pass

                debug["auto_whitelisted"] = int(inserted)
                debug["auto_whitelisted_assets"] = list(dict.fromkeys(inserted_assets_sample))

            changes: List[Tuple[int, str, str, str]] = []
            exclude_ids = {int(flag_id)}

            def _alt_family_keys(fk: str) -> List[str]:
                fk = str(fk)
                if fk.startswith("BP_"):
                    return ["BPC_" + fk[3:]]
                if fk.startswith("BPC_"):
                    return ["BP_" + fk[4:]]
                return []

            def _candidate_family_keys(fk: str) -> List[str]:
                fk = str(fk).strip()
                if not fk:
                    return []

                out: List[str] = []

                def _add(x: str) -> None:
                    x = str(x).strip()
                    if x and x not in out:
                        out.append(x)

                _add(fk)
                for x in _alt_family_keys(fk):
                    _add(x)

                # If the whitelist family_key came from an upgraded asset name, normalize it back
                # to the Basic variant so it can match the capture/template mapping keys.
                basic_fk = self._UPGR_TO_BASIC_RE.sub("_Basic_", fk)
                if basic_fk != fk:
                    _add(basic_fk)
                    for x in _alt_family_keys(basic_fk):
                        _add(x)

                return out

            for row in rows:
                stats["total"] += 1
                element_id = int(row["element_id"])
                if element_id in exclude_ids:
                    continue

                asset = str(row["asset"] or "").strip()
                if not asset:
                    continue

                tp.execute(
                    "SELECT family_key FROM asset_whitelist WHERE asset = ? LIMIT 1",
                    (asset,),
                )
                r_wh = tp.fetchone()
                if not r_wh:
                    stats["not_whitelisted"] += 1
                    if len(debug["not_whitelisted_assets"]) < 25:
                        debug["not_whitelisted_assets"].append(asset)
                    continue

                family_key = str(r_wh["family_key"] or "").strip()
                if not family_key:
                    stats["no_family"] += 1
                    continue

                r = None
                resolved_fk = family_key
                for fk2 in _candidate_family_keys(family_key):
                    tp.execute(
                        "SELECT asset FROM family_level_asset WHERE family_key = ? AND level = ? LIMIT 1",
                        (fk2, int(target_level)),
                    )
                    r = tp.fetchone()
                    if r:
                        resolved_fk = fk2
                        break

                if not r:
                    if not fallback_lowest:
                        stats["no_mapping"] += 1
                        if len(debug["no_mapping_family_keys"]) < 25:
                            debug["no_mapping_family_keys"].append(resolved_fk)
                        continue

                    r = None
                    for fk2 in _candidate_family_keys(family_key):
                        tp.execute(
                            """SELECT level, asset FROM family_level_asset WHERE family_key = ? AND level <= ? ORDER BY level DESC LIMIT 1""",
                            (fk2, int(target_level)),
                        )
                        r = tp.fetchone()
                        if r:
                            resolved_fk = fk2
                            break

                    # If there's no mapping <= target (rare), fall back to absolute lowest available.
                    if not r:
                        for fk2 in _candidate_family_keys(family_key):
                            tp.execute(
                                """SELECT level, asset FROM family_level_asset WHERE family_key = ? ORDER BY level ASC LIMIT 1""",
                                (fk2,),
                            )
                            r = tp.fetchone()
                            if r:
                                resolved_fk = fk2
                                break

                    if not r:
                        stats["no_mapping"] += 1
                        if len(debug["no_mapping_family_keys"]) < 25:
                            debug["no_mapping_family_keys"].append(resolved_fk)
                        continue

                    stats["fallback_lowest_used"] += 1

                new_asset = str(r["asset"] if isinstance(r, sqlite3.Row) else r[0])
                if new_asset == asset:
                    stats["already_target"] += 1
                    continue

                changes.append((element_id, asset, new_asset, family_key))

            stats["to_change"] = len(changes)
            debug_samples: Dict[str, Any] = {
                "not_whitelisted_assets": list(dict.fromkeys(debug["not_whitelisted_assets"])),
                "no_mapping_family_keys": list(dict.fromkeys(debug["no_mapping_family_keys"])),
                "auto_whitelisted": int(debug.get("auto_whitelisted") or 0),
                "auto_whitelisted_assets": list(dict.fromkeys(debug.get("auto_whitelisted_assets") or [])),
            }

            return internal_base_id, changes, stats, debug_samples
        finally:
            try:
                scum.close()
            except Exception:
                pass
            try:
                tpl.close()
            except Exception:
                pass

    def dry_run(
        self,
        *,
        flag_id: int,
        target_level: int,
        fallback_lowest: bool,
        auto_enrich_whitelist: bool = True,
    ) -> BaseMaterialDryRunResult:
        twig_locked, min_allowed = self._is_twig_locked(int(flag_id))
        if int(target_level) < int(min_allowed):
            raise RuntimeError("TARGET_LEVEL_FORBIDDEN")
        if twig_locked and int(target_level) == 1:
            raise RuntimeError("TARGET_LEVEL_FORBIDDEN")

        internal_base_id, changes, stats, debug_samples = self._compute_changes(
            flag_id=int(flag_id),
            target_level=int(target_level),
            fallback_lowest=bool(fallback_lowest),
            auto_enrich_whitelist=bool(auto_enrich_whitelist),
        )

        sample = [
            {
                "element_id": int(c[0]),
                "old_asset": str(c[1]),
                "new_asset": str(c[2]),
                "from_asset": str(c[1]),
                "to_asset": str(c[2]),
                "family_key": str(c[3]),
            }
            for c in changes[:200]
        ]

        return BaseMaterialDryRunResult(
            flag_id=int(flag_id),
            internal_base_id=int(internal_base_id),
            target_level=int(target_level),
            stats=stats,
            changes_sample=sample,
            debug=debug_samples,
        )

    def enqueue_dedup(
        self,
        *,
        flag_id: int,
        target_level: int,
        fallback_lowest: bool,
    ) -> Tuple[bool, str, bool]:
        twig_locked, min_allowed = self._is_twig_locked(int(flag_id))
        if int(target_level) < int(min_allowed):
            return False, "TARGET_LEVEL_FORBIDDEN", False
        if twig_locked and int(target_level) == 1:
            return False, "TARGET_LEVEL_FORBIDDEN", False

        job_id = f"base-material-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}-{uuid.uuid4().hex[:8]}"
        with ssm_tx(self.ssm_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT job_id
                FROM base_material_job
                WHERE flag_id=?
                  AND target_level=?
                  AND fallback_lowest=?
                  AND status IN ('pending','processing')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (int(flag_id), int(target_level), 1 if fallback_lowest else 0),
            )
            row = cur.fetchone()
            if row and row["job_id"]:
                return True, str(row["job_id"]), True

            conn.execute(
                """
                INSERT INTO base_material_job(job_id, flag_id, target_level, fallback_lowest, status, attempt_count, created_at, updated_at)
                VALUES(?, ?, ?, ?, 'pending', 0, datetime('now'), datetime('now'))
                """,
                (str(job_id), int(flag_id), int(target_level), 1 if fallback_lowest else 0),
            )
        return True, job_id, False

    def enqueue(
        self,
        *,
        flag_id: int,
        target_level: int,
        fallback_lowest: bool,
    ) -> Tuple[bool, str]:
        ok, job_or_code, _dedup = self.enqueue_dedup(
            flag_id=flag_id,
            target_level=target_level,
            fallback_lowest=fallback_lowest,
        )
        return ok, job_or_code

    def _claim_pending(self, restart_cycle_id: str, limit: int) -> List[Dict[str, Any]]:
        now_iso = _utc_now_iso()
        claimed: List[Dict[str, Any]] = []
        with ssm_tx(self.ssm_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM base_material_job
                WHERE status = 'pending'
                  AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (now_iso, int(limit)),
            )
            rows = cur.fetchall() or []
            for row in rows:
                job_id = str(row["job_id"])
                cur.execute(
                    """
                    UPDATE base_material_job
                    SET status='processing',
                        attempt_count=attempt_count+1,
                        locked_by=?,
                        locked_at=?,
                        updated_at=datetime('now')
                    WHERE job_id=? AND status='pending'
                    """,
                    (restart_cycle_id, now_iso, job_id),
                )
                if cur.rowcount:
                    claimed.append(dict(row))
        return claimed

    def _mark_done(self, job_id: str, payload: Dict[str, Any]) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                """
                UPDATE base_material_job
                SET status='done',
                    result_json=?,
                    error_code=NULL,
                    error_message=NULL,
                    locked_by=NULL,
                    locked_at=NULL,
                    updated_at=datetime('now')
                WHERE job_id=?
                """,
                (json.dumps(payload, ensure_ascii=False), str(job_id)),
            )

    def _mark_failed(self, job_id: str, error_code: str, error_message: str) -> None:
        with ssm_tx(self.ssm_db_path) as conn:
            conn.execute(
                """
                UPDATE base_material_job
                SET status='failed',
                    error_code=?,
                    error_message=?,
                    locked_by=NULL,
                    locked_at=NULL,
                    updated_at=datetime('now')
                WHERE job_id=?
                """,
                (str(error_code), str(error_message)[:2000], str(job_id)),
            )

    def _recover_stale_processing(
        self,
        *,
        lock_ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> int:
        """Move jobs stuck in 'processing' back to 'pending' (or fail after max attempts)."""

        now = datetime.now(timezone.utc)
        now_iso = now.replace(microsecond=0).isoformat()
        recovered = 0

        with ssm_tx(self.ssm_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT job_id, locked_at, attempt_count
                FROM base_material_job
                WHERE status='processing' AND locked_at IS NOT NULL
                """
            )
            rows = cur.fetchall() or []

            for r in rows:
                job_id = str(r["job_id"])
                locked_at = str(r["locked_at"] or "").strip()
                attempt_count = int(r["attempt_count"] or 0)
                if not locked_at:
                    continue

                try:
                    locked_dt = datetime.fromisoformat(locked_at)
                    if locked_dt.tzinfo is None:
                        locked_dt = locked_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue

                age_seconds = int((now - locked_dt).total_seconds())
                if age_seconds <= int(lock_ttl_seconds):
                    continue

                if attempt_count >= int(max_attempts):
                    cur.execute(
                        """
                        UPDATE base_material_job
                        SET status='failed',
                            error_code='MAX_ATTEMPTS',
                            error_message='Job exceeded max retry attempts (stuck processing)',
                            locked_by=NULL,
                            locked_at=NULL,
                            updated_at=datetime('now')
                        WHERE job_id=?
                        """,
                        (job_id,),
                    )
                    recovered += int(cur.rowcount or 0)
                    continue

                next_attempt_at = (now + timedelta(seconds=60)).replace(microsecond=0).isoformat()
                cur.execute(
                    """
                    UPDATE base_material_job
                    SET status='pending',
                        next_attempt_at=?,
                        locked_by=NULL,
                        locked_at=NULL,
                        error_code=NULL,
                        error_message=NULL,
                        updated_at=datetime('now')
                    WHERE job_id=? AND status='processing'
                    """,
                    (next_attempt_at, job_id),
                )
                recovered += int(cur.rowcount or 0)

        if recovered:
            try:
                self.logger.warn(
                    "[BASE_MATERIAL] Recovered stale processing jobs",
                    {"recovered": recovered, "now": now_iso},
                )
            except Exception:
                pass

        return recovered

    def _apply_changes(self, changes: List[Tuple[int, str, str, str]]) -> int:
        con = sqlite3.connect(str(self.scum_db_path), timeout=30.0)
        try:
            cur = con.cursor()
            con.execute("BEGIN")
            cur.executemany(
                "UPDATE base_element SET asset = ? WHERE element_id = ?",
                [(str(c[2]), int(c[0])) for c in changes],
            )
            updated = int(cur.rowcount or 0)
            con.commit()
            return updated
        finally:
            try:
                con.close()
            except Exception:
                pass

    def run_once(self, *, restart_cycle_id: str, limit: int = 10) -> BaseMaterialRunOnceResult:
        if not os.path.exists(self.scum_db_path):
            self.logger.warn(f"[BASE_MATERIAL] SCUM.db not found: {self.scum_db_path}")
            return BaseMaterialRunOnceResult(claimed=0, updated=0, no_changes=0, failed=0, job_ids=[])

        if not os.path.exists(self.template_db_path):
            self.logger.error(f"[BASE_MATERIAL] Template DB not found: {self.template_db_path}")
            return BaseMaterialRunOnceResult(claimed=0, updated=0, no_changes=0, failed=0, job_ids=[])

        # Recover jobs that got stuck in processing (e.g. process crash during restart window)
        try:
            self._recover_stale_processing(
                lock_ttl_seconds=self.DEFAULT_LOCK_TTL_SECONDS,
                max_attempts=self.DEFAULT_MAX_ATTEMPTS,
            )
        except Exception as e:
            try:
                self.logger.warn(f"[BASE_MATERIAL] Failed to recover stale processing jobs: {e}")
            except Exception:
                pass

        claimed = self._claim_pending(str(restart_cycle_id), int(limit))
        if not claimed:
            return BaseMaterialRunOnceResult(claimed=0, updated=0, no_changes=0, failed=0, job_ids=[])

        job_ids: List[str] = []
        updated_count = 0
        no_changes_count = 0
        failed_count = 0

        backup_path = None
        try:
            backup_path = create_scum_db_backup(self.scum_db_path)
            if backup_path:
                self.logger.info(f"[BASE_MATERIAL] SCUM.db backup created: {backup_path}")
        except Exception as e:
            self.logger.warn(f"[BASE_MATERIAL] Failed to create SCUM.db backup: {e}")

        for job in claimed:
            job_id = str(job.get("job_id"))
            job_ids.append(job_id)
            try:
                flag_id = int(job.get("flag_id"))
                target_level = int(job.get("target_level"))
                fallback_lowest = bool(int(job.get("fallback_lowest") or 0))

                twig_locked, min_allowed = self._is_twig_locked(flag_id)
                if int(target_level) < int(min_allowed) or (twig_locked and int(target_level) == 1):
                    raise RuntimeError("TARGET_LEVEL_FORBIDDEN")

                internal_base_id, changes, stats, debug_samples = self._compute_changes(
                    flag_id=flag_id,
                    target_level=target_level,
                    fallback_lowest=fallback_lowest,
                )

                if not changes:
                    no_changes_count += 1
                    payload = {
                        "job_id": job_id,
                        "flag_id": flag_id,
                        "internal_base_id": internal_base_id,
                        "target_level": target_level,
                        "result": "no_changes",
                        "stats": stats,
                        "debug_samples": debug_samples,
                        "backup_path": backup_path,
                        "updated_rows": 0,
                    }
                    self._mark_done(job_id, payload)
                    continue

                updated_rows = self._apply_changes(changes)
                updated_count += 1

                if int(target_level) >= 2:
                    self._set_twig_locked(flag_id, min_allowed_level=2)

                payload = {
                    "job_id": job_id,
                    "flag_id": flag_id,
                    "internal_base_id": internal_base_id,
                    "target_level": target_level,
                    "result": "updated",
                    "stats": stats,
                    "debug_samples": debug_samples,
                    "backup_path": backup_path,
                    "updated_rows": int(updated_rows),
                }
                self._mark_done(job_id, payload)

                self.logger.info(
                    "[BASE_MATERIAL] Applied base material job",
                    {
                        "job_id": job_id,
                        "flag_id": flag_id,
                        "internal_base_id": internal_base_id,
                        "target_level": target_level,
                        "updated_rows": int(updated_rows),
                    },
                )

            except Exception as e:
                failed_count += 1
                self._mark_failed(job_id, "ERROR", str(e))
                self.logger.warn(f"[BASE_MATERIAL] Job failed job_id={job_id}: {e}")

        return BaseMaterialRunOnceResult(
            claimed=len(claimed),
            updated=updated_count,
            no_changes=no_changes_count,
            failed=failed_count,
            job_ids=job_ids,
        )
