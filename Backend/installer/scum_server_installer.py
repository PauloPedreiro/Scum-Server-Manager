import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from collections import deque
from pathlib import Path


def run_scum_server_installer(base_dir: str, installer_state_dir: str = "") -> int:
    if installer_state_dir:
        state_dir = Path(installer_state_dir)
    else:
        program_data = os.environ.get("PROGRAMDATA") or "C:\\ProgramData"
        state_dir = Path(program_data) / "SSM" / "installer"

    logs_dir = state_dir / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    log_path = logs_dir / "scum_installer.log"
    status_path = state_dir / "scum_installer_status.json"

    def write_status(state: str, message: str, progress: int = 0):
        payload = {
            "state": state,
            "message": message,
            "progress": progress,
            "updated_at": int(time.time()),
        }
        try:
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def log_line(text: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {text}"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        try:
            print(line)
        except Exception:
            pass

    try:
        base = Path(base_dir)
        steamcmd_dir = base / "steamcmd"
        scum_install_dir = base / "scum"
        steamcmd_exe = steamcmd_dir / "steamcmd.exe"
        steamcmd_zip_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
        steamcmd_zip_path = steamcmd_dir / "steamcmd.zip"

        write_status("running", "Preparing folders", 5)
        log_line("[1/4] Preparing folders...")
        steamcmd_dir.mkdir(parents=True, exist_ok=True)
        scum_install_dir.mkdir(parents=True, exist_ok=True)

        if not steamcmd_exe.exists():
            write_status("running", "Downloading SteamCMD", 15)
            log_line("[2/4] Downloading SteamCMD...")
            try:
                if steamcmd_zip_path.exists():
                    steamcmd_zip_path.unlink()
            except Exception:
                pass

            urllib.request.urlretrieve(steamcmd_zip_url, str(steamcmd_zip_path))

            write_status("running", "Extracting SteamCMD", 25)
            log_line("Extracting SteamCMD...")
            with zipfile.ZipFile(str(steamcmd_zip_path), "r") as z:
                z.extractall(str(steamcmd_dir))

        if not steamcmd_exe.exists():
            msg = f"SteamCMD not found after extraction: {steamcmd_exe}"
            write_status("error", msg, 0)
            log_line(f"ERROR: {msg}")
            return 1

        write_status("running", "Initializing SteamCMD", 35)
        log_line("[3/4] Initializing SteamCMD...")

        def _run_steamcmd_stream(
            args_list,
            timeout_seconds: int,
            heartbeat_message: str = "",
            heartbeat_progress_range: tuple = None,
        ) -> tuple:
            last_lines = deque(maxlen=200)
            start = time.time()
            last_activity = time.time()
            last_heartbeat = 0.0
            last_heartbeat_log = 0.0
            heartbeat_progress = None
            if heartbeat_progress_range and len(heartbeat_progress_range) == 2:
                heartbeat_progress = heartbeat_progress_range[0]

            p = subprocess.Popen(
                [str(steamcmd_exe)] + args_list,
                cwd=str(steamcmd_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                bufsize=0,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            try:
                assert p.stdout is not None
                q: "queue.Queue[bytes | None]" = queue.Queue()

                def _reader():
                    try:
                        while True:
                            data = p.stdout.read(1024)
                            if not data:
                                break
                            q.put(data)
                    except Exception:
                        pass
                    finally:
                        try:
                            q.put(None)
                        except Exception:
                            pass

                reader_t = threading.Thread(target=_reader, daemon=True)
                reader_t.start()

                buffer = ""
                saw_eof = False
                while True:
                    if timeout_seconds and (time.time() - start) > timeout_seconds:
                        try:
                            p.kill()
                        except Exception:
                            pass
                        break

                    now = time.time()
                    if (
                        heartbeat_progress is not None
                        and heartbeat_message
                        and (now - last_activity) > 8
                        and (now - last_heartbeat) > 8
                    ):
                        last_heartbeat = now
                        try:
                            lo, hi = heartbeat_progress_range
                            heartbeat_progress = min(
                                int(heartbeat_progress + 1), int(hi)
                            )
                            write_status(
                                "running",
                                heartbeat_message,
                                int(heartbeat_progress),
                            )
                        except Exception:
                            pass

                        if (now - last_heartbeat_log) > 15:
                            last_heartbeat_log = now
                            try:
                                log_line(
                                    f"{heartbeat_message}... ({int(heartbeat_progress)}%)"
                                )
                            except Exception:
                                pass

                    try:
                        item = q.get(timeout=0.1)
                    except queue.Empty:
                        if p.poll() is not None and saw_eof:
                            break
                        continue

                    if item is None:
                        saw_eof = True
                        if p.poll() is not None:
                            break
                        continue

                    try:
                        text = item.decode("utf-8", errors="replace")
                    except Exception:
                        text = str(item)

                    buffer += text

                    while True:
                        idx_r = buffer.find("\r")
                        idx_n = buffer.find("\n")
                        if idx_r == -1 and idx_n == -1:
                            break

                        if idx_r != -1 and idx_n != -1:
                            idx = min(idx_r, idx_n)
                        elif idx_r != -1:
                            idx = idx_r
                        else:
                            idx = idx_n

                        line = buffer[:idx].strip()
                        buffer = buffer[idx + 1 :]
                        if line:
                            last_lines.append(line)
                            log_line(line)
                            last_activity = time.time()

                try:
                    reader_t.join(timeout=1)
                except Exception:
                    pass

                try:
                    p.wait(timeout=5)
                except Exception:
                    pass
            finally:
                try:
                    if p.stdout:
                        p.stdout.close()
                except Exception:
                    pass

            return int(p.returncode or 0), "\n".join(list(last_lines))

        init_ok = False
        last_init_output = ""
        for attempt in range(1, 4):
            try:
                log_line(f"SteamCMD init attempt {attempt}/3...")
                rc, combined = _run_steamcmd_stream(
                    ["+quit"],
                    timeout_seconds=600,
                    heartbeat_message="Initializing SteamCMD",
                    heartbeat_progress_range=(35, 54),
                )
                combined = (combined or "").strip()
                last_init_output = combined

                if rc == 0:
                    init_ok = True
                    break

                lowered = combined.lower()
                if (
                    "update complete" in lowered
                    or "atualiza" in lowered
                    or "applying update" in lowered
                    or "downloading update" in lowered
                    or "checking for available update" in lowered
                ):
                    time.sleep(8)
                    continue

                time.sleep(5)
            except subprocess.TimeoutExpired:
                last_init_output = "SteamCMD init timeout"
                log_line("SteamCMD init timeout, retrying...")
                time.sleep(5)

        if not init_ok:
            msg = last_init_output or "SteamCMD init failed"
            write_status("error", msg, 0)
            log_line(f"ERROR: SteamCMD init failed after retries: {msg}")
            return 1

        write_status("running", "Installing/Updating SCUM Server", 55)
        log_line("[4/4] Installing/Updating SCUM Server...")

        install_ok = False
        last_install_output = ""
        for attempt in range(1, 4):
            log_line(f"SCUM install attempt {attempt}/3...")
            rc, combined = _run_steamcmd_stream(
                [
                    "+force_install_dir",
                    str(scum_install_dir),
                    "+login",
                    "anonymous",
                    "+app_update",
                    "3792580",
                    "+quit",
                ],
                timeout_seconds=3600,
                heartbeat_message="Installing/Updating SCUM Server",
                heartbeat_progress_range=(55, 84),
            )

            combined = (combined or "").strip()
            last_install_output = combined

            if rc == 0:
                install_ok = True
                break

            lowered = combined.lower()
            if "missing configuration" in lowered:
                log_line(
                    "SteamCMD reported 'Missing configuration' - reinitializing and retrying..."
                )
                try:
                    _run_steamcmd_stream(
                        ["+quit"],
                        timeout_seconds=600,
                        heartbeat_message="Initializing SteamCMD",
                        heartbeat_progress_range=(35, 54),
                    )
                except Exception:
                    pass
                time.sleep(10)
                continue

            time.sleep(8)

        if not install_ok:
            msg = last_install_output or "SteamCMD app_update failed"
            write_status("error", msg, 0)
            log_line(f"ERROR: SCUM install/update failed after retries: {msg}")
            return 1

        try:
            (scum_install_dir / "SCUM" / "Saved" / "SaveFiles").mkdir(
                parents=True, exist_ok=True
            )
            (scum_install_dir / "SCUM" / "Saved" / "SaveFiles" / "Logs").mkdir(
                parents=True, exist_ok=True
            )
            (scum_install_dir / "SCUM" / "Saved" / "Config" / "WindowsServer").mkdir(
                parents=True, exist_ok=True
            )
        except Exception:
            pass

        write_status("running", "Updating configuration", 85)
        log_line("Updating config.json paths...")

        if getattr(sys, "frozen", False):
            app_dir = Path(sys.executable).parent
        else:
            app_dir = Path(__file__).resolve().parent.parent

        data_dir = app_dir / "data"
        config_path = data_dir / "config.json"
        if not config_path.exists():
            msg = f"config.json not found: {config_path}"
            write_status("error", msg, 0)
            log_line(f"ERROR: {msg}")
            return 1

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f) or {}

        config.setdefault("server", {})
        config["server"]["steamcmd_path"] = str(steamcmd_dir)

        config.setdefault("paths", {})
        config["paths"].setdefault("scum_server", {})
        scum_paths = config["paths"]["scum_server"]
        scum_paths["root_directory"] = str(scum_install_dir)
        scum_paths["binaries_directory"] = str(
            scum_install_dir / "SCUM" / "Binaries" / "Win64"
        )
        scum_paths["logs_directory"] = str(
            scum_install_dir / "SCUM" / "Saved" / "SaveFiles" / "Logs"
        )
        scum_paths["server_logs_directory"] = str(
            scum_install_dir / "SCUM" / "Saved" / "Logs"
        )
        scum_paths["config_directory"] = str(
            scum_install_dir / "SCUM" / "Saved" / "Config" / "WindowsServer"
        )
        scum_paths["database"] = str(
            scum_install_dir / "SCUM" / "Saved" / "SaveFiles" / "SCUM.db"
        )
        scum_paths["savefiles_directory"] = str(
            scum_install_dir / "SCUM" / "Saved" / "SaveFiles"
        )

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        write_status("success", "SCUM Server installed/updated successfully", 100)
        log_line("SUCCESS: Installation completed.")
        return 0

    except Exception as e:
        write_status("error", str(e), 0)
        try:
            log_line(f"ERROR: {e}")
        except Exception:
            pass
        return 1
