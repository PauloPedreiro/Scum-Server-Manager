import os
import sys
from pathlib import Path
from typing import Optional


def _default_roaming_appdata() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    return Path.home() / "AppData" / "Roaming"


def get_persistent_data_dir(app_name: str = "SSM Backend") -> Path:
    override = os.environ.get("SSM_DATA_DIR")
    if override and override.strip():
        return Path(override).expanduser()
    return _default_roaming_appdata() / app_name


def get_legacy_appdata_dir(app_name: str = "SSM Backend") -> Path:
    return _default_roaming_appdata() / app_name


def get_runtime_data_dir(
    *,
    is_exe: Optional[bool] = None,
    exe_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
    app_name: str = "SSM Backend",
) -> Path:
    if is_exe is None:
        is_exe = bool(getattr(sys, "frozen", False))

    if is_exe:
        override = os.environ.get("SSM_DATA_DIR")
        if override and override.strip():
            return Path(override).expanduser()
        if exe_dir is not None:
            return exe_dir / "data"
        return Path.cwd() / "data"

    if project_root is not None:
        return project_root / "data"

    if exe_dir is not None:
        return exe_dir / "data"

    return Path.cwd() / "data"


def migrate_legacy_data_dir(
    legacy_data_dir: Path,
    target_data_dir: Path,
    *,
    filenames: Optional[list[str]] = None,
) -> None:
    if filenames is None:
        filenames = [
            "config.json",
            "webhooks.json",
            "identity.json",
            "SSM.db",
            "license.json",
        ]

    try:
        if not legacy_data_dir.exists() or not legacy_data_dir.is_dir():
            return
        target_data_dir.mkdir(parents=True, exist_ok=True)

        for name in filenames:
            src = legacy_data_dir / name
            dst = target_data_dir / name
            if not src.exists() or not src.is_file():
                continue
            if dst.exists():
                continue
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
            except Exception:
                pass
    except Exception:
        return
