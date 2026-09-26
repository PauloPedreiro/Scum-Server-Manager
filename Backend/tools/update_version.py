"""
Script para atualizar a versão do SSM Backend automaticamente
"""

import re
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Discord webhook URL for version notifications (developer control)
VERSION_WEBHOOK_URL = "https://discord.com/api/webhooks/1448066449624010933/tsaf57RyXapYAi708JSttA5u_BkuuQ-7IFQyEzjraJkzbNkSwzW_XI7hc8ezMgnd4wft"

# Caminho do arquivo de versão
VERSION_FILE = Path(__file__).parent.parent / "version.py"

# Check if requests is available
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def get_current_version():
    """Obter versão atual do arquivo"""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Erro ao ler versão: {e}")
    return None


def update_version(new_version: str):
    """Atualizar versão no arquivo"""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Substituir versão
        content = re.sub(
            r'__version__\s*=\s*["\'][^"\']+["\']',
            f'__version__ = "{new_version}"',
            content,
        )

        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[+] Versao atualizada para: {new_version}")
        return True
    except Exception as e:
        print(f"[-] Erro ao atualizar versao: {e}")
        return False


def increment_version(
    current_version: str, increment_type: str = "patch", increment_value: int = 1
):
    """
    Incrementar versão automaticamente

    Args:
        current_version: Versão atual (ex: "3.0.1" ou "3.0.100")
        increment_type: Tipo de incremento ('major', 'minor', 'patch')
        increment_value: Valor a incrementar (padrão: 1, pode ser maior para números grandes)

    Returns:
        Nova versão (ex: "3.0.2" ou "3.0.101")
    """
    parts = current_version.split(".")
    if len(parts) != 3:
        print(f"[-] Formato de versao invalido: {current_version}")
        print("   Formato esperado: X.Y.Z (ex: 3.0.1 ou 3.0.100)")
        return None

    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2])

        if increment_type == "major":
            major += increment_value
            minor = 0
            patch = 0
        elif increment_type == "minor":
            minor += increment_value
            patch = 0
        elif increment_type == "patch":
            patch += increment_value
        else:
            print(f"[-] Tipo de incremento invalido: {increment_type}")
            print("   Tipos válidos: 'major', 'minor', 'patch'")
            return None

        return f"{major}.{minor}.{patch}"
    except ValueError:
        print(f"[-] Erro ao processar versao: {current_version}")
        return None


def get_build_number():
    """
    Gerar número de build baseado em timestamp ou sequencial
    Retorna um número grande para suportar muitas versões
    """
    timestamp = int(datetime.now().timestamp())
    # Usar timestamp completo dividido por 100 (muda a cada ~27 horas)
    build_number = (timestamp // 100) % 1000000  # Número entre 0 e 999999
    return build_number


def get_changelog_from_args(args):
    """
    Get changelog from command line arguments

    Args:
        args: List of command line arguments

    Returns:
        Changelog string or None if not provided
    """
    changelog = None

    # Check for -m or --message
    for i, arg in enumerate(args):
        if arg in ["-m", "--message"]:
            if i + 1 < len(args):
                changelog = args[i + 1]
                # If changelog starts with quotes, handle multi-line
                if changelog and (
                    changelog.startswith('"') or changelog.startswith("'")
                ):
                    # Try to get full multi-line string
                    quote_char = changelog[0]
                    if changelog.endswith(quote_char) and len(changelog) > 2:
                        changelog = changelog[1:-1]  # Remove quotes
                    else:
                        # Multi-line: collect until closing quote
                        parts = [changelog[1:]]  # Remove opening quote
                        for j in range(i + 2, len(args)):
                            parts.append(args[j])
                            if args[j].endswith(quote_char):
                                parts[-1] = parts[-1][:-1]  # Remove closing quote
                                changelog = " ".join(parts)
                                break
            break

    if changelog:
        changelog = changelog.strip()
        return changelog if changelog else None
    return None


def prompt_for_changelog():
    """
    Prompt user for changelog interactively

    Returns:
        Changelog string or None if user cancels
    """
    # Avoid Unicode/emoji to prevent Windows cp1252 console errors
    print("\nWhat was implemented in this version?")
    print("   (Enter your changes, press Enter twice to finish, or 'skip' to skip)")
    print("   " + "-" * 60)

    lines = []
    empty_count = 0

    try:
        while True:
            line = input()
            if line.strip().lower() == "skip":
                return None
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)
    except (EOFError, KeyboardInterrupt):
        print("\n[!] Changelog input cancelled")
        return None

    if not lines:
        return None

    changelog = "\n".join(lines).strip()
    return changelog if changelog else None


def send_version_notification(
    old_version: str,
    new_version: str,
    increment_type: str,
    increment_value: int = None,
    changelog: str = None,
    webhook_url: str = None,
):
    """
    Send version update notification to Discord webhook

    Args:
        old_version: Previous version (e.g., "3.0.100")
        new_version: New version (e.g., "3.0.101")
        increment_type: Type of update ('patch', 'minor', 'major', 'set', 'build')
        increment_value: Increment value (if applicable)
        changelog: Description of what was implemented (optional)
        webhook_url: Discord webhook URL (optional, uses default if None)

    Returns:
        True if notification was sent successfully, False otherwise
    """
    if not HAS_REQUESTS:
        print("[!] Warning: 'requests' library not available - notification not sent")
        return False

    webhook_url = webhook_url or VERSION_WEBHOOK_URL

    # Determine update type description
    type_descriptions = {
        "patch": "Patch",
        "minor": "Minor",
        "major": "Major",
        "set": "Manual",
        "build": "Build",
    }
    type_desc = type_descriptions.get(increment_type, "Update")

    # Build increment description
    if increment_value and increment_value > 1:
        increment_desc = f"{type_desc} (+{increment_value})"
    elif increment_type == "set":
        increment_desc = "Manual Update"
    elif increment_type == "build":
        increment_desc = "Build Number"
    else:
        increment_desc = f"{type_desc} (+1)"

    # Prepare changelog field
    changelog_text = changelog if changelog else "No changelog provided"
    # Limit to 1024 characters (Discord field limit)
    if len(changelog_text) > 1024:
        changelog_text = changelog_text[:1021] + "..."

    # Create Discord embed payload
    embed = {
        "title": "📦 SSM Backend - Version Updated",
        "description": f"A new version has been released\n\n🔗 [Visit SSM Portal](https://scumsm.com/)",
        "color": 3066993,  # Green color
        "fields": [
            {"name": "Previous Version", "value": old_version, "inline": True},
            {"name": "New Version", "value": new_version, "inline": True},
            {"name": "Update Type", "value": increment_desc, "inline": True},
            {"name": "What's New", "value": changelog_text, "inline": False},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "footer": {"text": "SSM Backend Development Tools"},
    }

    payload = {"embeds": [embed]}

    # Send notification to Discord
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=5,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code in (200, 204):
            print("[+] Notification sent to Discord")
            return True
        else:
            print(
                f"[!] Warning: Failed to send notification (Status: {response.status_code})"
            )
            return False

    except requests.exceptions.Timeout:
        print("[!] Warning: Timeout while sending notification to Discord")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning: Failed to send notification: {e}")
        return False
    except Exception as e:
        print(f"[!] Warning: Unexpected error sending notification: {e}")
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("SSM Backend Version Updater")
        print()
        print("Usage:")
        print("  python tools/update_version.py <command> [options]")
        print()
        print("Commands:")
        print("  show                    - Show current version")
        print(
            "  set <version>          - Set version manually (e.g., 3.0.2 or 3.0.100)"
        )
        print(
            "  patch [number]          - Increment patch (3.0.1 -> 3.0.2 or 3.0.100 -> 3.0.101)"
        )
        print(
            "                           Use: patch 10 to increment by 10 (3.0.100 -> 3.0.110)"
        )
        print("  minor [number]          - Increment minor (3.0.1 -> 3.1.0)")
        print("  major [number]          - Increment major (3.0.1 -> 4.0.0)")
        print(
            "  build                   - Use timestamp-based build number (3.0.1 -> 3.0.XXXXX)"
        )
        print()
        print("Options:")
        print("  -m, --message <text>   - Changelog description (what was implemented)")
        print("  --no-notify            - Skip Discord notification")
        print()
        print("Examples:")
        print("  python tools/update_version.py show")
        print("  python tools/update_version.py set 3.0.100")
        print("  python tools/update_version.py patch")
        print("  python tools/update_version.py patch 10")
        print(
            '  python tools/update_version.py patch -m "Fixed license validation bug"'
        )
        print("  python tools/update_version.py patch --no-notify")
        print("  python tools/update_version.py build")
        print("  python tools/update_version.py minor")
        print("  python tools/update_version.py major")
        sys.exit(1)

    # Parse arguments
    args = sys.argv[1:]
    if not args:
        print("[-] No command specified")
        sys.exit(1)

    command = args[0].lower()

    # Check for --no-notify flag
    send_notification = "--no-notify" not in args
    if "--no-notify" in args:
        args.remove("--no-notify")

    # Get changelog from arguments (if provided)
    changelog = None
    if send_notification:
        changelog = get_changelog_from_args(args)
        # Remove -m/--message and its value from args for command parsing
        filtered_args = []
        skip_next = False
        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                continue
            if arg in ["-m", "--message"]:
                skip_next = True
                continue
            filtered_args.append(arg)
        args = filtered_args

    current_version = get_current_version()

    if not current_version:
        print("[-] Could not read current version")
        sys.exit(1)

    if command == "show":
        print(f"Current version: {current_version}")
        sys.exit(0)

    elif command == "set":
        if len(args) < 2:
            print("[-] Error: Specify version")
            print("   Example: python tools/update_version.py set 3.0.2")
            sys.exit(1)

        new_version = args[1]
        # Validate format (allows large numbers)
        if not re.match(r"^\d+\.\d+\.\d+$", new_version):
            print(f"[-] Invalid version format: {new_version}")
            print("   Expected format: X.Y.Z (e.g., 3.0.2 or 3.0.100)")
            sys.exit(1)

        if update_version(new_version):
            # Avoid Unicode/emoji to prevent Windows cp1252 console errors
            print(f"Version changed from {current_version} to {new_version}")

            # Send notification if enabled
            if send_notification:
                # Prompt for changelog if not provided
                if not changelog:
                    changelog = prompt_for_changelog()

                send_version_notification(
                    old_version=current_version,
                    new_version=new_version,
                    increment_type="set",
                    changelog=changelog,
                )
        else:
            sys.exit(1)

    elif command == "build":
        # Use timestamp-based build number
        build_number = get_build_number()
        parts = current_version.split(".")
        if len(parts) == 3:
            new_version = f"{parts[0]}.{parts[1]}.{build_number}"
            if update_version(new_version):
                # Avoid Unicode/emoji to prevent Windows cp1252 console errors
                print(f"Version updated to build: {new_version}")

                # Send notification if enabled
                if send_notification:
                    # Prompt for changelog if not provided
                    if not changelog:
                        changelog = prompt_for_changelog()

                    send_version_notification(
                        old_version=current_version,
                        new_version=new_version,
                        increment_type="build",
                        changelog=changelog,
                    )
        else:
            print(f"[-] Invalid version format: {current_version}")
            sys.exit(1)

    elif command in ["patch", "minor", "major"]:
        # Check if increment value is specified
        increment_value = 1
        if len(args) > 1:
            try:
                increment_value = int(args[1])
                if increment_value < 1:
                    print("[-] Increment value must be greater than 0")
                    sys.exit(1)
            except ValueError:
                # If not a number, use default 1
                pass

        new_version = increment_version(current_version, command, increment_value)
        if new_version:
            if update_version(new_version):
                if increment_value > 1:
                    print(
                        f"Version incremented from {current_version} to {new_version} (+{increment_value})"
                    )
                else:
                    print(
                        f"Version incremented from {current_version} to {new_version}"
                    )

                # Send notification if enabled
                if send_notification:
                    # Prompt for changelog if not provided
                    if not changelog:
                        changelog = prompt_for_changelog()

                    send_version_notification(
                        old_version=current_version,
                        new_version=new_version,
                        increment_type=command,
                        increment_value=increment_value,
                        changelog=changelog,
                    )
        else:
            sys.exit(1)

    else:
        print(f"[-] Unknown command: {command}")
        print("   Use 'show', 'set', 'patch', 'minor', 'major' or 'build'")
        sys.exit(1)


if __name__ == "__main__":
    main()
