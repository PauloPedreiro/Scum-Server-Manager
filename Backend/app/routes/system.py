"""
Blueprint: System Routes
Rotas de saúde, licenciamento e diagnóstico do sistema.

Endpoints:
    GET  /api/health                              - Health check
    GET  /api/licensing/hardware-fingerprint       - Hardware fingerprint (debug)
    GET  /api/discord/webhooks/test                - Listar eventos para teste
    POST /api/discord/webhooks/test/<event_key>    - Testar webhook do Discord
"""

import time
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request  # pyright: ignore[reportMissingImports, reportMissingModuleSource]

from app.extensions import get_services

system_bp = Blueprint("system", __name__)


@system_bp.route("/api/health", methods=["GET"])
def health_check():
    """Verificar saúde da aplicação"""
    try:
        services = get_services()

        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {
                "server_manager": services.server_manager is not None,
                "restart_scheduler": services.restart_scheduler is not None,
                "weather_scheduler": services.weather_scheduler is not None,
                "notification_manager": services.notification_manager is not None,
                "discord_webhook": services.discord_webhook is not None,
                "chat_command_monitor": services.chat_command_monitor is not None,
                "logger": services.logger is not None,
                "config": services.config is not None,
            },
        }

        return jsonify(health_status)

    except Exception as e:
        services = get_services()
        if services.logger:
            services.logger.error(f"Erro no health check: {e}")
        return (
            jsonify({"status": "unhealthy", "error": str(e), "timestamp": time.time()}),
            500,
        )


@system_bp.route("/api/licensing/hardware-fingerprint", methods=["GET"])
def get_hardware_fingerprint():
    """Obter hardware fingerprint para debug"""
    try:
        from core.licensing.hardware_fingerprint import HardwareFingerprint
        services = get_services()

        hardware_fp = HardwareFingerprint(logger=services.logger)
        equipment_hash, components = hardware_fp.generate()

        return jsonify(
            {
                "success": True,
                "data": {
                    "equipment_hash": equipment_hash,
                    "components": {
                        "cpu_id": components.get("cpu_id", "N/A"),
                        "network_macs_count": len(components.get("network_macs", [])),
                        "disk_serials_count": len(components.get("disk_serials", [])),
                        "windows_guid": components.get("windows_guid", "N/A"),
                    },
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@system_bp.route("/api/discord/webhooks/test", methods=["GET"])
def discord_webhooks_test_list():
    """Listar eventos disponíveis para teste de webhook no Discord."""
    try:
        return jsonify(
            {
                "success": True,
                "data": {
                    "events": [
                        "players_online",
                        "vehicle_registration",
                        "chat_in_game",
                        "timer",
                        "commands",
                        "kill_log",
                        "cargo_drop",
                        "lockpicking_events",
                        "chest_events",
                        "chest_vehicle_alerts",
                    ]
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@system_bp.route("/api/discord/webhooks/test/<event_key>", methods=["POST", "GET"])
def discord_webhooks_test_send(event_key: str):
    """Enviar uma mensagem de teste para um webhook do Discord (por event_key)."""
    try:
        services = get_services()
        discord_webhook = getattr(services, 'discord_webhook', None)
        config = getattr(services, 'config', {})
        path_helper = getattr(services, 'path_helper', None)
        logger = getattr(services, 'logger', None)

        key = str(event_key or "").strip()
        if not key:
            return jsonify({"success": False, "error": "event_key vazio"}), 400

        if not discord_webhook:
            return (
                jsonify({"success": False, "error": "DiscordWebhook não inicializado"}),
                500,
            )

        # Recarregar webhooks do arquivo (evita depender de restart quando webhooks.json foi editado)
        # Para TESTE: enviar mesmo se enabled=false (apenas precisa ter URL)
        test_url = None
        try:
            from core.webhooks.manager import WebhooksManager

            webhooks_path = None
            try:
                if path_helper is not None:
                    webhooks_path = path_helper.get_application_path(
                        "webhooks_file", "data/webhooks.json"
                    )
            except Exception:
                webhooks_path = None
            if not webhooks_path:
                import sys
                from pathlib import Path
                if getattr(sys, "frozen", False):
                    root_dir = Path(sys._MEIPASS)
                else:
                    root_dir = Path(__file__).parent.parent
                webhooks_path = str(root_dir / "data" / "webhooks.json")

            hooks_manager = WebhooksManager(str(webhooks_path))

            # atualizar mapa enabled-only (envios reais)
            refreshed = hooks_manager.load()
            if isinstance(refreshed, dict):
                try:
                    config["webhooks"] = refreshed
                except Exception:
                    pass
                try:
                    discord_webhook.webhooks = refreshed
                except Exception:
                    pass

            # URL para teste (inclui disabled)
            meta = hooks_manager.list_events_meta()
            if isinstance(meta, dict) and isinstance(meta.get(key), dict):
                test_url = (meta.get(key) or {}).get("url")

            # forçar recarregar display_name no DiscordWebhook
            try:
                setattr(discord_webhook, "_display_name_map", None)
            except Exception:
                pass
        except Exception:
            test_url = None

        title = f"SSM Test: {key}"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        description = f"Mensagem de teste do webhook '{key}' em {ts}."

        # Erro mais claro quando não existe URL no arquivo
        current_url = None
        try:
            current_url = (test_url or "").strip() if isinstance(test_url, str) else ""
        except Exception:
            current_url = ""
        if not current_url:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Webhook '{key}' não configurado (URL vazia no webhooks.json)",
                        "data": {
                            "event_key": key,
                            "known_keys": sorted(list((getattr(discord_webhook, 'webhooks', {}) or {}).keys())),
                        },
                    }
                ),
                400,
            )

        # Garantir que o send_webhook use a URL deste evento mesmo se ele estiver disabled
        try:
            if hasattr(discord_webhook, "webhooks") and isinstance(discord_webhook.webhooks, dict):
                discord_webhook.webhooks[key] = current_url
        except Exception:
            pass

        ok = discord_webhook.send_webhook(
            webhook_name=key,
            title=title,
            description=description,
            color=0x3498DB,
            fields=[{"name": "event_key", "value": key, "inline": True}],
        )

        if not ok:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Falha ao enviar. Verifique se o evento está enabled e com URL no webhooks.json (v2).",
                        "data": {"event_key": key},
                    }
                ),
                400,
            )

        return jsonify({"success": True, "data": {"event_key": key, "sent": True}})
    except Exception as e:
        try:
            services = get_services()
            if services.logger:
                services.logger.error(f"Erro ao testar webhook Discord ({event_key}): {e}")
        except Exception:
            pass
        return jsonify({"success": False, "error": str(e)}), 500
