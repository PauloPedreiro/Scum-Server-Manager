"""
Blueprint: config
"""

from flask import Blueprint, jsonify, request, send_file, Response
from app.extensions import get_services
import traceback, os, time, json, hmac
from functools import wraps
from core.auth.decorators import require_auth, require_admin, require_player_auth
from utils.scum_db_helper import scum_db_readonly_connection_strict
from utils.integration_helpers import require_integration_key
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from app.constants import IS_EXE, DATA_DIR, ROOT_DIR, EXE_DIR
from core.config.config_manager import ConfigManager
from core.webhooks.manager import WebhooksManager
from .helpers import _get_ssm_database_path

def sync_config_prices_to_db(prices_dict, logger=None):
    """Sincroniza os preços do config.json com a tabela attribute_upgrade_prices no SSM.db"""
    try:
        from app.routes.helpers import _get_ssm_database_path
        from core.database.connector import DatabaseConnector
        
        ssm_db_path, error = _get_ssm_database_path()
        if error:
            if logger:
                logger.error(f"[Sync Prices] Erro ao obter caminho do banco: {error}")
            return False

        if not isinstance(prices_dict, dict):
            return False

        # Mapeamento de atributos
        attr_mapping = {
            "strength": "strength", "forca": "strength", "força": "strength", "force": "strength",
            "constitution": "constitution", "constituiçao": "constitution", "constituição": "constitution",
            "dexterity": "dexterity", "destreza": "dexterity",
            "intelligence": "intelligence", "inteligencia": "intelligence", "inteligência": "intelligence"
        }

        insert_rows = []
        for attr, lvls in prices_dict.items():
            if not isinstance(attr, str):
                continue
            normalized_attr = attr_mapping.get(attr.lower().strip())
            if not normalized_attr:
                continue
            if not isinstance(lvls, dict):
                continue
            for lvl_str, pr_val in lvls.items():
                try:
                    lvl = int(lvl_str)
                    pr = int(pr_val)
                except (ValueError, TypeError):
                    continue
                
                max_level = 8 if normalized_attr == "strength" else 5
                if lvl < 1 or lvl > max_level:
                    continue
                if pr < 0:
                    continue
                insert_rows.append((normalized_attr, lvl, pr))

        with DatabaseConnector.get_connection(ssm_db_path, write_mode=True) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attribute_upgrade_prices")
            if insert_rows:
                cursor.executemany(
                    """
                    INSERT INTO attribute_upgrade_prices (attribute_name, level, price)
                    VALUES (?, ?, ?)
                    """,
                    insert_rows
                )
            conn.commit()
            if logger:
                logger.info(f"[Sync Prices] Sincronização com o banco executada com sucesso. Registros: {len(insert_rows)}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"[Sync Prices] Erro ao sincronizar preços com o banco: {e}")
        return False


def sync_services_config(manager, services):
    """Sincroniza o dicionário in-memory services.config com o config.json em disco."""
    try:
        if services and hasattr(services, "config") and isinstance(services.config, dict):
            new_config = manager.load()
            services.config.clear()
            services.config.update(new_config)
            if hasattr(services, "logger") and services.logger:
                services.logger.info("[Sync Config] Dicionário de configuração in-memory sincronizado com sucesso.")
    except Exception as e:
        if services and hasattr(services, "logger") and services.logger:
            services.logger.error(f"[Sync Config] Erro ao sincronizar configuração na memória: {e}")


config_bp = Blueprint('config', __name__)

@config_bp.route("/api/config", methods=["GET"])
def get_config():
    """Obter configuração completa ou seção específica do config.json"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        section = request.args.get("section")

        # Determinar caminho do config.json
        if IS_EXE:
            config_path = DATA_DIR / "config.json"
        else:
            config_path = ROOT_DIR / "data" / "config.json"

        manager = ConfigManager(str(config_path))

        if section:
            # Retornar apenas uma seção
            section_data = manager.get_section(section)
            if section_data is None:
                return (
                    jsonify(
                        {"success": False, "error": f'Seção "{section}" não encontrada'}
                    ),
                    404,
                )

            response_data = {
                "success": True,
                "data": {section: section_data},
                "timestamp": time.time(),
            }
            return Response(
                json.dumps(response_data, sort_keys=False, ensure_ascii=False),
                mimetype="application/json",
            )
        else:
            # Retornar configuração completa
            config_data = manager.load()
            response_data = {
                "success": True,
                "data": config_data,
                "timestamp": time.time(),
            }
            return Response(
                json.dumps(response_data, sort_keys=False, ensure_ascii=False),
                mimetype="application/json",
            )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao carregar configuração: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/config/sections", methods=["GET"])
def get_config_sections():
    """Listar todas as seções disponíveis no config.json"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        # Determinar caminho do config.json
        if IS_EXE:
            config_path = DATA_DIR / "config.json"
        else:
            config_path = ROOT_DIR / "data" / "config.json"

        manager = ConfigManager(str(config_path))
        # Incluir subseções aninhadas (ex: paths.scum_server)
        include_nested = request.args.get("include_nested", "true").lower() == "true"
        sections = manager.get_sections(include_nested=include_nested)

        return (
            jsonify(
                {
                    "success": True,
                    "data": {"sections": sections, "total": len(sections)},
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao listar seções: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/config", methods=["PATCH"])
def update_config():
    """Atualizar seção(s) específica(s) do config.json"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        # Verificar se há dados no body
        if not request.data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": 'Body vazio. É necessário enviar um JSON com o campo "sections"',
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
            except json_lib.JSONDecodeError as json_error:
                if logger:
                    logger.error(f"JSON inválido no update_config: {json_error}")
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
                    logger.error(f"Erro ao processar body no update_config: {e}")
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

        sections = data.get("sections")
        if not sections or not isinstance(sections, dict):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": 'Campo "sections" é obrigatório e deve ser um objeto',
                    }
                ),
                400,
            )

        create_backup = data.get("create_backup", True)

        # Determinar caminho do config.json
        if IS_EXE:
            config_path = DATA_DIR / "config.json"
        else:
            config_path = ROOT_DIR / "data" / "config.json"

        manager = ConfigManager(str(config_path))
        updated_sections = manager.update_sections(
            sections, create_backup=create_backup
        )

        # Sincronizar configuração em memória
        sync_services_config(manager, services)

        # Sincronizar preços com o banco de dados se a seção foi modificada
        if "attribute_upgrade_prices" in updated_sections:
            prices_dict = manager.get_section("attribute_upgrade_prices")
            if prices_dict:
                sync_config_prices_to_db(prices_dict, logger=logger)

        # Identificar seções que requerem restart (pode ser expandido)
        requires_restart = []
        restart_sections = [
            "server",
            "scheduler",
            "api",
            "squad_sync",
            "survival_sync",
            "rankings_sync",
            "chest_sync",
            "player_gps_sync",
            "player_skills_sync",
            "vehicle_verification",
        ]

        for section in updated_sections:
            if section in restart_sections:
                requires_restart.append(section)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Configuração atualizada com sucesso",
                    "data": {
                        "updated_sections": updated_sections,
                        "requires_restart": requires_restart,
                    },
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao atualizar configuração: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/config", methods=["PUT"])
def replace_config():
    """Substituir configuração completa do config.json"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        # Verificar se há dados no body
        if not request.data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": 'Body vazio. É necessário enviar um JSON com o campo "config"',
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
            except json_lib.JSONDecodeError as json_error:
                if logger:
                    logger.error(f"JSON inválido no replace_config: {json_error}")
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
                    logger.error(f"Erro ao processar body no replace_config: {e}")
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

        new_config = data.get("config")
        if not new_config or not isinstance(new_config, dict):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": 'Campo "config" é obrigatório e deve ser um objeto',
                    }
                ),
                400,
            )

        create_backup = data.get("create_backup", True)

        # Determinar caminho do config.json
        if IS_EXE:
            config_path = DATA_DIR / "config.json"
        else:
            config_path = ROOT_DIR / "data" / "config.json"

        manager = ConfigManager(str(config_path))
        manager.replace_all(new_config, create_backup=create_backup)

        # Sincronizar configuração em memória
        sync_services_config(manager, services)

        # Sincronizar preços com o banco de dados se a seção foi modificada
        if "attribute_upgrade_prices" in new_config:
            prices_dict = new_config.get("attribute_upgrade_prices")
            if prices_dict:
                sync_config_prices_to_db(prices_dict, logger=logger)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Configuração completa atualizada",
                    "data": {"requires_restart": True},
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao substituir configuração: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/config/<section>", methods=["PUT"])
def update_config_section(section: str):
    """Atualizar seção completa do config.json (aceita qualquer campo)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
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

        # Verificar create_backup (query param tem prioridade)
        create_backup = request.args.get("create_backup", "true").lower() == "true"
        # Também aceita no body (mas remove do data para não ser salvo na seção)
        if "create_backup" in data:
            create_backup = bool(data.pop("create_backup"))

        # Determinar caminho do config.json
        if IS_EXE:
            config_path = DATA_DIR / "config.json"
        else:
            config_path = ROOT_DIR / "data" / "config.json"

        manager = ConfigManager(str(config_path))
        manager.update_section(section, data, create_backup=create_backup)

        # Sincronizar configuração em memória
        sync_services_config(manager, services)

        # Sincronizar preços com o banco de dados se a seção foi modificada
        if section == "attribute_upgrade_prices":
            sync_config_prices_to_db(data, logger=logger)

        # Identificar se requer restart
        requires_restart = []
        restart_sections = [
            "server",
            "scheduler",
            "api",
            "squad_sync",
            "survival_sync",
            "rankings_sync",
            "chest_sync",
            "player_gps_sync",
            "player_skills_sync",
            "vehicle_verification",
        ]

        if section in restart_sections:
            requires_restart.append(section)

        return (
            jsonify(
                {
                    "success": True,
                    "message": f'Seção "{section}" atualizada com sucesso',
                    "data": {
                        "section": section,
                        "updated_fields": list(data.keys()),
                        "requires_restart": requires_restart,
                    },
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao atualizar seção {section}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/config/backup", methods=["GET"])
def list_config_backups():
    """Listar backups disponíveis do config.json"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        limit = request.args.get("limit", 10, type=int)

        # Determinar caminho do config.json
        if IS_EXE:
            config_path = DATA_DIR / "config.json"
        else:
            config_path = ROOT_DIR / "data" / "config.json"

        manager = ConfigManager(str(config_path))
        backups = manager.list_backups(limit=limit)

        return (
            jsonify(
                {
                    "success": True,
                    "data": {"backups": backups, "total": len(backups)},
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao listar backups: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/config/restore", methods=["POST"])
def restore_config():
    """Restaurar configuração de um backup"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "Body é obrigatório"}), 400

        backup_filename = data.get("backup_file")
        if not backup_filename:
            return (
                jsonify(
                    {"success": False, "error": 'Campo "backup_file" é obrigatório'}
                ),
                400,
            )

        create_backup = data.get("create_backup", True)

        # Determinar caminho do config.json
        if IS_EXE:
            config_path = DATA_DIR / "config.json"
        else:
            config_path = ROOT_DIR / "data" / "config.json"

        manager = ConfigManager(str(config_path))
        manager.restore_backup(backup_filename, create_backup=create_backup)

        # Sincronizar configuração em memória
        sync_services_config(manager, services)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Configuração restaurada com sucesso",
                    "data": {
                        "restored_from": backup_filename,
                        "requires_restart": True,
                    },
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except FileNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        if logger:
            logger.error(f"Erro ao restaurar backup: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks", methods=["GET"])
def get_webhooks():
    """Obter todos os webhooks ou um webhook específico"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        webhook_name = request.args.get("webhook")

        # Determinar caminho do webhooks.json
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))

        if webhook_name:
            # Retornar apenas um webhook específico
            url = manager.get_webhook(webhook_name)
            if url is None:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f'Webhook "{webhook_name}" não encontrado',
                        }
                    ),
                    404,
                )

            response_data = {
                "success": True,
                "data": {webhook_name: url},
                "timestamp": time.time(),
            }
            return Response(
                json.dumps(response_data, sort_keys=False, ensure_ascii=False),
                mimetype="application/json",
            )
        else:
            # Retornar todos os webhooks
            webhooks_data = manager.load()
            response_data = {
                "success": True,
                "data": webhooks_data,
                "timestamp": time.time(),
            }
            return Response(
                json.dumps(response_data, sort_keys=False, ensure_ascii=False),
                mimetype="application/json",
            )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao carregar webhooks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks/names", methods=["GET"])
def get_webhook_names():
    """Listar todos os nomes de webhooks disponíveis"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        # Determinar caminho do webhooks.json
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))
        webhook_names = manager.get_webhook_names()

        return (
            jsonify(
                {
                    "success": True,
                    "data": {"webhooks": webhook_names, "total": len(webhook_names)},
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao listar nomes de webhooks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks", methods=["PATCH"])
def update_webhooks():
    """Atualizar múltiplos webhooks (apenas webhooks existentes)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        if not request.data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Body vazio. É necessário enviar um JSON com webhooks e create_backup (opcional)",
                    }
                ),
                400,
            )

        data = request.get_json(force=True, silent=True)

        if data is None:
            try:
                import json as json_lib

                json_lib.loads(request.data.decode("utf-8"))
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

        webhooks_updates = data.get("webhooks")
        if not webhooks_updates or not isinstance(webhooks_updates, dict):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": 'Campo "webhooks" é obrigatório e deve ser um objeto {nome: url}',
                    }
                ),
                400,
            )

        create_backup = data.get("create_backup", True)

        # Determinar caminho do webhooks.json
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))
        updated_webhooks = manager.update_webhooks(
            webhooks_updates, create_backup=create_backup
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Webhooks atualizados com sucesso",
                    "data": {"updated_webhooks": updated_webhooks},
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except KeyError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        if logger:
            logger.error(f"Erro ao atualizar webhooks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks", methods=["PUT"])
def replace_webhooks():
    """Substituir todos os webhooks"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        if not request.data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Body vazio. É necessário enviar um JSON com webhooks e create_backup (opcional)",
                    }
                ),
                400,
            )

        data = request.get_json(force=True, silent=True)

        if data is None:
            try:
                import json as json_lib

                json_lib.loads(request.data.decode("utf-8"))
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

        new_webhooks = data.get("webhooks")
        if not new_webhooks or not isinstance(new_webhooks, dict):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": 'Campo "webhooks" é obrigatório e deve ser um objeto {nome: url}',
                    }
                ),
                400,
            )

        create_backup = data.get("create_backup", True)

        # Determinar caminho do webhooks.json
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))
        manager.replace_all(new_webhooks, create_backup=create_backup)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Webhooks completos atualizados",
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao substituir webhooks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks/<webhook_name>", methods=["GET"])
def get_webhook(webhook_name: str):
    """Obter um webhook específico"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        # Determinar caminho do webhooks.json
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))
        url = manager.get_webhook(webhook_name)

        if url is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Webhook "{webhook_name}" não encontrado',
                    }
                ),
                404,
            )

        return (
            jsonify(
                {"success": True, "data": {webhook_name: url}, "timestamp": time.time()}
            ),
            200,
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao obter webhook {webhook_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks/<webhook_name>", methods=["PUT"])
def update_webhook(webhook_name: str):
    """Atualizar um webhook específico (apenas webhooks existentes)"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        if not request.data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Body vazio. É necessário enviar um JSON com url e create_backup (opcional)",
                    }
                ),
                400,
            )

        data = request.get_json(force=True, silent=True)

        if data is None:
            try:
                import json as json_lib

                json_lib.loads(request.data.decode("utf-8"))
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

        url = data.get("url")
        if not url or not isinstance(url, str):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": 'Campo "url" é obrigatório e deve ser uma string',
                    }
                ),
                400,
            )

        # Verificar create_backup (query param tem prioridade)
        create_backup = request.args.get("create_backup", "true").lower() == "true"
        # Também aceita no body (mas remove do data para não ser salvo)
        if "create_backup" in data:
            create_backup = bool(data.pop("create_backup"))

        # Determinar caminho do webhooks.json
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))
        manager.update_webhook(webhook_name, url, create_backup=create_backup)

        return (
            jsonify(
                {
                    "success": True,
                    "message": f'Webhook "{webhook_name}" atualizado com sucesso',
                    "data": {"webhook_name": webhook_name, "url": url},
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except KeyError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        if logger:
            logger.error(f"Erro ao atualizar webhook {webhook_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks/<webhook_name>/test", methods=["POST"])
def test_webhook(webhook_name: str):
    """Testar um webhook enviando uma mensagem de teste"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        # Determinar caminho do webhooks.json
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))

        # Obter URL do webhook
        webhook_url = manager.get_webhook(webhook_name)
        if not webhook_url:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Webhook "{webhook_name}" não encontrado',
                    }
                ),
                404,
            )

        # Testar webhook
        result = manager.test_webhook(webhook_url)

        return jsonify(
            {
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "data": {
                    "webhook_name": webhook_name,
                    "webhook_url": (
                        webhook_url[:50] + "..."
                        if len(webhook_url) > 50
                        else webhook_url
                    ),
                    "status_code": result.get("status_code"),
                    "error": result.get("error"),
                },
                "timestamp": time.time(),
            }
        ), (200 if result.get("success") else 400)

    except Exception as e:
        if logger:
            logger.error(f"Erro ao testar webhook {webhook_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks/test", methods=["POST"])
def test_webhook_by_url():
    """Testar um webhook enviando uma mensagem de teste usando URL diretamente"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "Body é obrigatório"}), 400

        webhook_url = data.get("url")
        if not webhook_url or not isinstance(webhook_url, str):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": 'Campo "url" é obrigatório e deve ser uma string',
                    }
                ),
                400,
            )

        # Determinar caminho do webhooks.json (apenas para criar manager)
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))

        # Testar webhook
        result = manager.test_webhook(webhook_url)

        return jsonify(
            {
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "data": {
                    "webhook_url": (
                        webhook_url[:50] + "..."
                        if len(webhook_url) > 50
                        else webhook_url
                    ),
                    "status_code": result.get("status_code"),
                    "error": result.get("error"),
                },
                "timestamp": time.time(),
            }
        ), (200 if result.get("success") else 400)

    except Exception as e:
        if logger:
            logger.error(f"Erro ao testar webhook por URL: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks/backup", methods=["GET"])
def list_webhooks_backups():
    """Listar backups disponíveis do webhooks.json"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        limit = request.args.get("limit", 10, type=int)

        # Determinar caminho do webhooks.json
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))
        backups = manager.list_backups(limit=limit)

        return (
            jsonify(
                {
                    "success": True,
                    "data": {"backups": backups, "total": len(backups)},
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except Exception as e:
        if logger:
            logger.error(f"Erro ao listar backups: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/webhooks/restore", methods=["POST"])
def restore_webhooks():
    """Restaurar webhooks de um backup"""
    services = get_services()
    logger = getattr(services, 'logger', None)
    auth_manager = getattr(services, 'auth_manager', None)
    config = getattr(services, 'config', {})
    path_helper = getattr(services, 'path_helper', None)
    server_manager = getattr(services, 'server_manager', None)
    discord_bot_service = getattr(services, 'discord_bot_service', None)
    notification_manager = getattr(services, 'notification_manager', None)
    restart_scheduler = getattr(services, 'restart_scheduler', None)
    weather_scheduler = getattr(services, 'weather_scheduler', None)
    permission_manager = getattr(services, 'permission_manager', None)
    ini_manager = getattr(services, 'ini_manager', None)
    elevated_users_manager = getattr(services, 'elevated_users_manager', None)
    shop_service = getattr(services, 'shop_service', None)
    wallet_service = getattr(services, 'wallet_service', None)
    squad_sync_service = getattr(services, 'squad_sync_service', None)
    survival_stats_sync_service = getattr(services, 'survival_stats_sync_service', None)
    chest_sync_service = getattr(services, 'chest_sync_service', None)
    rankings_update_service = getattr(services, 'rankings_update_service', None)
    vehicle_verification_service = getattr(services, 'vehicle_verification_service', None)
    player_gps_sync_service = getattr(services, 'player_gps_sync_service', None)
    lockpicking_ranking_service = getattr(services, 'lockpicking_ranking_service', None)
    kills_ranking_service = getattr(services, 'kills_ranking_service', None)
    snipers_ranking_service = getattr(services, 'snipers_ranking_service', None)
    chest_inventory_sync_service = getattr(services, 'chest_inventory_sync_service', None)
    log_processor = getattr(services, 'log_processor', None)
    chat_processor = getattr(services, 'chat_processor', None)
    bunker_processor = getattr(services, 'bunker_processor', None)
    online_monitor = getattr(services, 'online_monitor', None)
    fishing_ranking_manager = getattr(services, 'fishing_ranking_manager', None)
    chat_command_monitor = getattr(services, 'chat_command_monitor', None)
    license_validator = getattr(services, 'license_validator', None)
    owner_manager = getattr(services, 'owner_manager', None)
    remote_command_handler = getattr(services, 'remote_command_handler', None)
    backend_identity = getattr(services, 'backend_identity', None)
    scum_logs_cleanup_service = getattr(services, 'scum_logs_cleanup_service', None)
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "Body é obrigatório"}), 400

        backup_filename = data.get("backup_file")
        if not backup_filename:
            return (
                jsonify(
                    {"success": False, "error": 'Campo "backup_file" é obrigatório'}
                ),
                400,
            )

        create_backup = data.get("create_backup", True)

        # Determinar caminho do webhooks.json
        if IS_EXE:
            webhooks_path = EXE_DIR / "data" / "webhooks.json"
        else:
            webhooks_path = ROOT_DIR / "data" / "webhooks.json"

        manager = WebhooksManager(str(webhooks_path))
        manager.restore_backup(backup_filename, create_backup=create_backup)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Webhooks restaurados com sucesso",
                    "data": {"restored_from": backup_filename},
                    "timestamp": time.time(),
                }
            ),
            200,
        )

    except FileNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        if logger:
            logger.error(f"Erro ao restaurar backup: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/config/kill-feed-phrases", methods=["GET"])
@require_auth
@require_admin
def get_kill_feed_phrases():
    """Obter lista de frases do kill feed"""
    try:
        if IS_EXE:
            phrases_path = DATA_DIR / "kill_feed_phrases.json"
        else:
            phrases_path = ROOT_DIR / "data" / "kill_feed_phrases.json"

        # Se o arquivo não existir, retorna array vazio ou o arquivo padrão
        if not os.path.exists(phrases_path):
            return jsonify({"success": True, "data": []})

        with open(phrases_path, "r", encoding="utf-8") as f:
            phrases = json.load(f)

        return jsonify({"success": True, "data": phrases})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/api/config/kill-feed-phrases", methods=["POST"])
@require_auth
@require_admin
def update_kill_feed_phrases():
    """Atualizar lista de frases do kill feed"""
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"success": False, "error": "Os dados enviados devem ser uma lista de frases (array de strings)"}), 400

        # Validar que todos os elementos são strings
        if not all(isinstance(x, str) for x in data):
            return jsonify({"success": False, "error": "Todas as frases enviadas devem ser do tipo texto (string)"}), 400

        if IS_EXE:
            phrases_path = DATA_DIR / "kill_feed_phrases.json"
        else:
            phrases_path = ROOT_DIR / "data" / "kill_feed_phrases.json"

        # Escrever arquivo
        with open(phrases_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({"success": True, "message": "Lista de frases atualizada com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



