"""
Blueprint: server
"""
from typing import Dict, Any, List, Optional, Tuple

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin
from datetime import datetime, timedelta, timezone
import sqlite3, threading
from core.server_settings.manager import ServerSettingsManager
from .helpers import _get_ssm_database_path, _get_scum_database_path

server_bp = Blueprint('server', __name__)

@server_bp.route("/api/server/status", methods=["GET"])
def get_server_status():
    """Obter status do servidor"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    try:
        # Log reduzido para evitar poluição do console

        if not server_manager:
            return (
                jsonify({"success": False, "error": "ServerManager não inicializado"}),
                500,
            )

        # Obter status detalhado
        status = server_manager.get_status()

        response = {"success": True, "data": status, "timestamp": time.time()}

        # Log reduzido para evitar poluição do console
        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server_bp.route("/api/server/start", methods=["POST"])
def start_server():
    """Iniciar servidor"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    try:
        # Tentar fazer parse do JSON (silent=True retorna None em caso de erro, não lança exceção)
        data = request.get_json(force=True, silent=True) or {}

        # Se get_json retornou None e há dados no body, pode ser JSON inválido
        if data is None and request.data:
            try:
                # Tentar fazer parse manual para obter mensagem de erro mais específica
                import json as json_lib

                json_lib.loads(request.data.decode("utf-8"))
            except json_lib.JSONDecodeError as json_error:
                if logger:
                    logger.error(f"JSON inválido no start_server: {json_error}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"JSON inválido: {str(json_error)}",
                            "message": "Verifique se o JSON está bem formatado. Body pode ser vazio {} ou conter {force: true, wait_timeout: 30}",
                        }
                    ),
                    400,
                )
            except Exception as e:
                if logger:
                    logger.error(f"Erro ao processar body no start_server: {e}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Erro ao processar requisição: {str(e)}",
                            "message": "Verifique se o Content-Type é application/json e se o JSON está bem formatado",
                        }
                    ),
                    400,
                )

        force = data.get("force", False)
        wait_timeout = data.get("wait_timeout", 30)

        logger.info(f"Iniciando servidor (force: {force}, timeout: {wait_timeout})")

        if not server_manager:
            return (
                jsonify({"success": False, "error": "ServerManager não inicializado"}),
                500,
            )

        # Verificar se já está rodando
        if server_manager._is_service_running() and not force:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Servidor já está rodando",
                        "status": "already_running",
                    }
                ),
                400,
            )

        # Enviar notificação de início
        try:
            discord_webhook.send_server_status(
                "server_starting",
                {
                    "is_running": False,
                    "port": server_manager.port,
                    "max_players": server_manager.max_players,
                },
            )
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de início: {e}")

        # Iniciar servidor
        # Nota: A verificação e limpeza de WAL/SHM agora são feitas automaticamente pelo start_server()
        scum_db_path = path_helper.get_scum_db_path() if path_helper else None
        result = server_manager.start_server(scum_db_path=scum_db_path)

        # Aguardar confirmação se especificado
        if result["success"] and wait_timeout > 0:
            time.sleep(min(wait_timeout, 10))  # Máximo 10 segundos
            final_status = server_manager.get_status()
            result["final_status"] = final_status

        # Enviar notificação de resultado
        try:
            if result["success"]:
                discord_webhook.send_server_status(
                    "server_started",
                    {
                        "is_running": True,
                        "pid": result.get("data", {}).get("pid"),
                        "uptime": result.get("data", {}).get("uptime", 0),
                        "port": server_manager.port,
                        "max_players": server_manager.max_players,
                    },
                )
            else:
                discord_webhook.send_server_status(
                    "server_start_failed",
                    {
                        "error": result.get("message", "Erro desconhecido"),
                        "is_running": False,
                    },
                )
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de resultado: {e}")

        logger.info(f"Resultado do início: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao iniciar servidor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server_bp.route("/api/server/stop", methods=["POST"])
def stop_server():
    """Parar servidor"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    try:
        # Tentar fazer parse do JSON (silent=True retorna None em caso de erro, não lança exceção)
        data = request.get_json(force=True, silent=True) or {}

        # Se get_json retornou None e há dados no body, pode ser JSON inválido
        if data is None and request.data:
            try:
                import json as json_lib

                json_lib.loads(request.data.decode("utf-8"))
            except json_lib.JSONDecodeError as json_error:
                if logger:
                    logger.error(f"JSON inválido no stop_server: {json_error}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"JSON inválido: {str(json_error)}",
                            "message": "Verifique se o JSON está bem formatado. Body pode ser vazio {} ou conter {force: true, wait_timeout: 30}",
                        }
                    ),
                    400,
                )
            except Exception as e:
                if logger:
                    logger.error(f"Erro ao processar body no stop_server: {e}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Erro ao processar requisição: {str(e)}",
                            "message": "Verifique se o Content-Type é application/json e se o JSON está bem formatado",
                        }
                    ),
                    400,
                )

        force = data.get("force", False)
        wait_timeout = data.get("wait_timeout", 30)

        logger.info(f"Parando servidor (force: {force}, timeout: {wait_timeout})")

        if not server_manager:
            return (
                jsonify({"success": False, "error": "ServerManager não inicializado"}),
                500,
            )

        # Verificar se está rodando
        if not server_manager._is_service_running():
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Servidor não está rodando",
                        "status": "not_running",
                    }
                ),
                400,
            )

        # Parar servidor
        # Nota: A limpeza de WAL/SHM e sincronização de elevated users agora são feitas automaticamente pelo stop_server()
        scum_db_path = path_helper.get_scum_db_path() if path_helper else None
        result = server_manager.stop_server(
            scum_db_path=scum_db_path, elevated_users_manager=elevated_users_manager
        )

        # Aguardar confirmação se especificado
        if result["success"] and wait_timeout > 0:
            time.sleep(min(wait_timeout, 10))  # Máximo 10 segundos
            final_status = server_manager.get_status()
            result["final_status"] = final_status

        # Enviar notificação apenas em falha (server_stopped removida)
        try:
            if not result["success"]:
                discord_webhook.send_server_status(
                    "server_stop_failed",
                    {
                        "error": result.get("message", "Erro desconhecido"),
                        "is_running": False,
                    },
                )
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de resultado: {e}")

        logger.info(f"Resultado da parada: {result['success']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao parar servidor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server_bp.route("/api/server/nssm/apply_shutdown_preset", methods=["POST"])
def apply_nssm_shutdown_preset():
    """Aplicar preset recomendado de shutdown do NSSM (requer admin/UAC no Windows)."""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    try:
        data = request.get_json(force=True, silent=True) or {}

        if not server_manager:
            return (
                jsonify({"success": False, "error": "ServerManager não inicializado"}),
                500,
            )

        # Permitir override opcional de timeouts.
        console_timeout_ms = data.get("console_timeout_ms", 120000)
        enable_terminate = bool(data.get("enable_terminate", False))
        terminate_timeout_ms = data.get("terminate_timeout_ms", 300000)

        result = server_manager.apply_nssm_shutdown_preset(
            console_timeout_ms=int(console_timeout_ms),
            enable_terminate=enable_terminate,
            terminate_timeout_ms=int(terminate_timeout_ms),
        )

        status = 200 if result.get("success") else 400
        return jsonify(result), status

    except Exception as e:
        if logger:
            logger.error(f"Erro ao aplicar preset NSSM: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server_bp.route("/api/server/settings", methods=["GET"])
def get_server_settings():
    """Obter todas as configurações ou seção específica do ServerSettings.ini"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    try:
        section = request.args.get("section")

        if not path_helper:
            return (
                jsonify({"success": False, "error": "PathHelper não inicializado"}),
                500,
            )

        config_dir = path_helper.get_scum_server_path("config_directory")
        if not config_dir:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Diretório de configuração não encontrado",
                    }
                ),
                500,
            )

        manager = ServerSettingsManager(config_dir)

        if section:
            # Retornar apenas uma seção (preservando ordem)
            settings = manager.get_section(section)
            # Usar json.dumps com sort_keys=False para preservar ordem
            response_data = {
                "success": True,
                "data": {section: settings},
                "timestamp": time.time(),
            }
            return Response(
                json.dumps(response_data, sort_keys=False, ensure_ascii=False),
                mimetype="application/json",
            )
        else:
            # Retornar todas as seções (preservando ordem)
            settings = manager.load_all()
            response_data = {
                "success": True,
                "data": settings,
                "timestamp": time.time(),
            }
            return Response(
                json.dumps(response_data, sort_keys=False, ensure_ascii=False),
                mimetype="application/json",
            )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao carregar configurações do servidor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server_bp.route("/api/server/settings", methods=["PATCH"])
def update_server_setting():
    """Atualizar uma configuração específica do ServerSettings.ini"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    try:
        # Verificar se há dados no body
        if not request.data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Body vazio. É necessário enviar um JSON com section, key e value",
                    }
                ),
                400,
            )

        # Tentar fazer parse do JSON (silent=True retorna None em caso de erro, não lança exceção)
        data = request.get_json(force=True, silent=True)

        if data is None:
            # Se get_json retornou None, pode ser JSON inválido ou Content-Type incorreto
            try:
                # Tentar fazer parse manual para obter mensagem de erro mais específica
                import json as json_lib

                json_lib.loads(request.data.decode("utf-8"))
                # Se chegou aqui, o JSON é válido mas get_json retornou None por outro motivo
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Erro ao processar JSON",
                            "message": "Verifique se o Content-Type é application/json",
                        }
                    ),
                    400,
                )
            except json_lib.JSONDecodeError as json_error:
                if logger:
                    logger.error(f"JSON inválido: {json_error}")
                    logger.error(
                        f"Body recebido: {request.data[:500] if request.data else 'None'}"
                    )
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"JSON inválido: {str(json_error)}",
                            "message": "Verifique se o JSON está bem formatado",
                        }
                    ),
                    400,
                )
            except Exception as e:
                if logger:
                    logger.error(f"Erro ao processar body: {e}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Erro ao processar requisição: {str(e)}",
                            "message": "Verifique se o Content-Type é application/json e se o JSON está bem formatado",
                        }
                    ),
                    400,
                )

        if not data:
            return jsonify({"success": False, "error": "Body é obrigatório"}), 400

        section = data.get("section")
        key = data.get("key")
        value = data.get("value")

        if not all([section, key, value is not None]):
            return (
                jsonify(
                    {"success": False, "error": "section, key e value são obrigatórios"}
                ),
                400,
            )

        if not path_helper:
            return (
                jsonify({"success": False, "error": "PathHelper não inicializado"}),
                500,
            )

        config_dir = path_helper.get_scum_server_path("config_directory")
        if not config_dir:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Diretório de configuração não encontrado",
                    }
                ),
                500,
            )

        manager = ServerSettingsManager(config_dir)
        result = manager.set_value(section, key, value)

        if result["success"]:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": result["message"],
                        "data": {
                            "section": result["section"],
                            "key": result["key"],
                            "value": result["value"],
                            "backup": result.get("backup"),
                        },
                        "timestamp": time.time(),
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Erro desconhecido"),
                    }
                ),
                400,
            )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao atualizar configuração do servidor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server_bp.route("/api/server/settings/<section>", methods=["PUT"])
def update_server_settings_section(section: str):
    """Atualizar seção completa do ServerSettings.ini (aceita qualquer campo)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "Body é obrigatório"}), 400

        if not isinstance(data, dict):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Body deve ser um objeto com chaves e valores",
                    }
                ),
                400,
            )

        if not path_helper:
            return (
                jsonify({"success": False, "error": "PathHelper não inicializado"}),
                500,
            )

        config_dir = path_helper.get_scum_server_path("config_directory")
        if not config_dir:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Diretório de configuração não encontrado",
                    }
                ),
                500,
            )

        manager = ServerSettingsManager(config_dir)
        result = manager.update_section(section, data)

        if result["success"]:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": result["message"],
                        "data": {
                            "section": result["section"],
                            "updated_fields": result["updated_fields"],
                            "backup": result.get("backup"),
                        },
                        "timestamp": time.time(),
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Erro desconhecido"),
                    }
                ),
                400,
            )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao atualizar seção {section}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server_bp.route("/api/server/restart", methods=["POST"])
def restart_server():
    """Reiniciar servidor (executa em background para evitar timeout)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    try:
        # SEGURANÇA: Verificar se restart já está em andamento
        if server_manager and hasattr(server_manager, '_restart_in_progress'):
            if server_manager._restart_in_progress:
                return jsonify({
                    "success": False,
                    "error": "Restart já está em andamento",
                    "message": "Aguarde o restart atual terminar antes de tentar novamente",
                    "status": "restart_in_progress"
                }), 409  # 409 Conflict
        # Tentar fazer parse do JSON (silent=True retorna None em caso de erro, não lança exceção)
        data = request.get_json(force=True, silent=True) or {}

        # Se get_json retornou None e há dados no body, pode ser JSON inválido
        if data is None and request.data:
            try:
                import json as json_lib

                json_lib.loads(request.data.decode("utf-8"))
            except json_lib.JSONDecodeError as json_error:
                if logger:
                    logger.error(f"JSON inválido no restart_server: {json_error}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"JSON inválido: {str(json_error)}",
                            "message": "Verifique se o JSON está bem formatado. Body pode ser vazio {} ou conter {force: true, wait_timeout: 0}",
                        }
                    ),
                    400,
                )
            except Exception as e:
                if logger:
                    logger.error(f"Erro ao processar body no restart_server: {e}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Erro ao processar requisição: {str(e)}",
                            "message": "Verifique se o Content-Type é application/json e se o JSON está bem formatado",
                        }
                    ),
                    400,
                )

        force = data.get("force", False)
        wait_timeout = data.get("wait_timeout", 0)  # Não aguardar por padrão

        logger.info(f"Reiniciando servidor (force: {force}, timeout: {wait_timeout})")

        if not server_manager:
            return (
                jsonify({"success": False, "error": "ServerManager não inicializado"}),
                500,
            )

        # Verificar se está rodando
        if not server_manager._is_service_running():
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Servidor não está rodando",
                        "status": "not_running",
                    }
                ),
                400,
            )

        # Enviar notificação de reinicialização
        try:
            discord_webhook.send_server_status(
                "server_restarting",
                {
                    "is_running": True,
                    "port": server_manager.port,
                    "max_players": server_manager.max_players,
                },
            )
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de reinicialização: {e}")

        # Executar restart em thread separada para evitar timeout
        def execute_restart():
            try:
                scum_db_path = path_helper.get_scum_db_path() if path_helper else None

                gps_was_running = False
                try:
                    if (
                        player_gps_sync_service is not None
                        and getattr(player_gps_sync_service, "is_running", False)
                    ):
                        gps_was_running = True
                        try:
                            if logger:
                                logger.info(
                                    "Parando PlayerGpsSyncService temporariamente para janela de restart"
                                )
                        except Exception:
                            pass
                        try:
                            player_gps_sync_service.stop()
                        except Exception as e:
                            try:
                                if logger:
                                    logger.warn(
                                        f"Falha ao parar PlayerGpsSyncService antes do restart: {e}"
                                    )
                            except Exception:
                                pass
                except Exception:
                    gps_was_running = False

                # IMPORTANTE: NÃO executar entregas aqui.
                # A entrega escreve no SCUM.db e deve acontecer SOMENTE na janela offline,
                # depois do serviço SCUM parar, dentro do ServerManager.restart_server().

                result = server_manager.restart_server(
                    scum_db_path=scum_db_path,
                    elevated_users_manager=elevated_users_manager,
                )

                try:
                    server_ready = False
                    try:
                        server_ready = bool(result.get("success")) and bool(
                            result.get("server_ready")
                        )
                    except Exception:
                        server_ready = False

                    if gps_was_running and server_ready and (
                        player_gps_sync_service is not None
                    ):
                        try:
                            if logger:
                                logger.info(
                                    "Reiniciando PlayerGpsSyncService apos janela de restart"
                                )
                        except Exception:
                            pass
                        try:
                            player_gps_sync_service.start()
                        except Exception as e:
                            try:
                                if logger:
                                    logger.warn(
                                        f"Falha ao reiniciar PlayerGpsSyncService apos restart: {e}"
                                    )
                            except Exception:
                                pass
                    elif gps_was_running and not server_ready:
                        try:
                            if logger:
                                logger.warn(
                                    "PlayerGpsSyncService permanecerá parado: SCUMServer ainda não está pronto (server_ready=False)"
                                )
                        except Exception:
                            pass
                except Exception:
                    pass

                # Enviar notificação apenas em falha (server_restarted removida)
                try:
                    if not result["success"]:
                        discord_webhook.send_server_status(
                            "server_restart_failed",
                            {
                                "error": result.get("message", "Erro desconhecido"),
                                "is_running": False,
                            },
                        )
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação de resultado: {e}")

                logger.info(f"Resultado do reinício (background): {result['success']}")
            except Exception as e:
                logger.error(f"Erro ao executar restart em background: {e}")
                try:
                    discord_webhook.send_server_status(
                        "server_restart_failed", {"error": str(e), "is_running": False}
                    )
                except:
                    pass

        # Iniciar thread em background
        restart_thread = threading.Thread(target=execute_restart, daemon=True)
        restart_thread.start()

        # Retornar imediatamente informando que o restart foi iniciado
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Reinicialização iniciada. O processo pode levar vários minutos, especialmente se houver Elevated Users para sincronizar.",
                    "status": "restarting",
                    "note": "Use o endpoint /api/server/status para verificar o progresso do restart",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Erro ao iniciar reinicialização: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server_bp.route("/api/server/cleanup-wal", methods=["POST"])
def cleanup_wal_files():
    """Limpar arquivos WAL/SHM do SCUM.db manualmente"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    try:
        if not server_manager:
            return (
                jsonify({"success": False, "error": "ServerManager não inicializado"}),
                500,
            )

        # Verificar se servidor está parado
        if server_manager._is_service_running():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Servidor está rodando - não é seguro limpar arquivos WAL/SHM",
                        "message": "Pare o servidor antes de limpar os arquivos",
                    }
                ),
                400,
            )

        # Obter caminho do SCUM.db
        scum_db_path = path_helper.get_scum_db_path()

        # Limpar arquivos
        from utils.scum_db_cleanup import (
            cleanup_scum_db_wal_files,
            set_shared_copy_manager,
        )
        from utils.scum_db_shared_copy import get_shared_copy_manager

        # Registrar ScumDbSharedCopyManager para fechar conexões antes de limpar
        try:
            shared_copy_mgr = get_shared_copy_manager()
            if shared_copy_mgr:
                set_shared_copy_manager(shared_copy_mgr)
        except Exception as e:
            logger.warn(f"Erro ao registrar ScumDbSharedCopyManager para limpeza: {e}")

        cleanup_result = cleanup_scum_db_wal_files(server_manager, scum_db_path, logger)

        if cleanup_result.get("success"):
            return (
                jsonify(
                    {
                        "success": True,
                        "message": cleanup_result.get("message"),
                        "files_removed": cleanup_result.get("files_removed", []),
                        "files_found": cleanup_result.get("files_found", []),
                        "checkpoint_success": cleanup_result.get(
                            "checkpoint_success", False
                        ),
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": cleanup_result.get("message"),
                        "errors": cleanup_result.get("errors", []),
                        "files_found": cleanup_result.get("files_found", []),
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Erro ao limpar arquivos WAL/SHM: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server_bp.route("/api/server/logs", methods=["GET"])
def get_server_logs():
    """Obter logs do servidor"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    password_reset_manager = getattr(services, 'password_reset_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    server_manager = getattr(services, 'server_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    ini_manager = getattr(services, 'ini_manager', None)
    discord_webhook = getattr(services, 'discord_webhook', None)
    path_helper = getattr(services, 'path_helper', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    try:
        # Obter parâmetros da query
        limit = int(request.args.get("limit", 100))
        level = request.args.get("level")
        since = request.args.get("since")

        logger.info(f"Requisição de logs (limit: {limit}, level: {level})")

        # Obter logs do arquivo
        log_file = logger.get_log_file_path()
        logs = []

        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Processar logs (últimas linhas)
            recent_lines = lines[-limit:] if limit > 0 else lines

            for line in recent_lines:
                try:
                    # Tentar parsear como JSON estruturado
                    log_entry = json.loads(line.strip())
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    # Se não for JSON, tratar como log simples
                    logs.append(
                        {
                            "timestamp": time.time(),
                            "level": "info",
                            "message": line.strip(),
                        }
                    )

        response = {
            "success": True,
            "data": {"logs": logs, "count": len(logs), "limit": limit},
            "timestamp": time.time(),
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro ao obter logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


