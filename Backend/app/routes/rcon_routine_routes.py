from flask import Blueprint, jsonify, request, Response
import json
import time
from app.extensions import get_services
from core.auth.decorators import require_auth, require_admin
from utils.sanitize import sanitize_rcon_command_coords

rcon_routine_bp = Blueprint('rcon_routine', __name__)

@rcon_routine_bp.route("/api/rcon-routines", methods=["GET"])
@require_auth
@require_admin
def get_routines():
    """Retorna todas as rotinas RCON cadastradas."""
    services = get_services()
    manager = getattr(services, 'rcon_routine_manager', None)
    if not manager:
        return jsonify({"success": False, "error": "RconRoutineManager não inicializado"}), 500
    
    routines = manager.get_routines()
    return Response(
        json.dumps({"success": True, "data": routines}, sort_keys=False, ensure_ascii=False),
        mimetype="application/json"
    )

@rcon_routine_bp.route("/api/rcon-routines", methods=["POST"])
@require_auth
@require_admin
def create_routine():
    """Cria uma nova rotina de comandos RCON."""
    services = get_services()
    manager = getattr(services, 'rcon_routine_manager', None)
    if not manager:
        return jsonify({"success": False, "error": "RconRoutineManager não inicializado"}), 500
    
    try:
        data = request.json or {}
        name = data.get("name")
        interval_minutes = data.get("interval_minutes")
        commands = data.get("commands")
        enabled = data.get("enabled", True)
        
        warning_enabled = data.get("warning_enabled", False)
        warning_message = data.get("warning_message", "")
        warning_color = data.get("warning_color", "")
        warning_minutes_before = data.get("warning_minutes_before", 5)
        
        if not name or not isinstance(name, str) or not name.strip():
            return jsonify({"success": False, "error": "Nome da rotina é obrigatório"}), 400
        
        try:
            interval_minutes = int(interval_minutes)
            if interval_minutes <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Intervalo (em minutos) deve ser um número inteiro maior que 0"}), 400
            
        if "warning_minutes_before" in data:
            try:
                val = int(data["warning_minutes_before"])
                if val <= 0:
                    raise ValueError()
                warning_minutes_before = val
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Tempo de aviso prévio deve ser um número inteiro maior que 0"}), 400
            
        if not isinstance(commands, list):
            return jsonify({"success": False, "error": "Comandos devem ser uma lista de strings"}), 400
            
        new_routine = manager.add_routine(
            name=name.strip(),
            interval_minutes=interval_minutes,
            commands=commands,
            enabled=enabled,
            warning_enabled=warning_enabled,
            warning_message=warning_message,
            warning_color=warning_color,
            warning_minutes_before=warning_minutes_before
        )
        return jsonify({"success": True, "data": new_routine})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@rcon_routine_bp.route("/api/rcon-routines/<routine_id>", methods=["PUT"])
@require_auth
@require_admin
def update_routine(routine_id):
    """Edita campos de uma rotina RCON existente."""
    services = get_services()
    manager = getattr(services, 'rcon_routine_manager', None)
    if not manager:
        return jsonify({"success": False, "error": "RconRoutineManager não inicializado"}), 500
    
    try:
        data = request.json or {}
        
        # Validação do intervalo
        if "interval_minutes" in data:
            try:
                val = int(data["interval_minutes"])
                if val <= 0:
                    raise ValueError()
                data["interval_minutes"] = val
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Intervalo (em minutos) deve ser um número inteiro maior que 0"}), 400
                
        # Validação do tempo de aviso prévio
        if "warning_minutes_before" in data:
            try:
                val = int(data["warning_minutes_before"])
                if val <= 0:
                    raise ValueError()
                data["warning_minutes_before"] = val
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Tempo de aviso prévio deve ser um número inteiro maior que 0"}), 400
                
        # Validação de comandos
        if "commands" in data and not isinstance(data["commands"], list):
            return jsonify({"success": False, "error": "Comandos devem ser uma lista de strings"}), 400
            
        updated = manager.update_routine(routine_id, data)
        if not updated:
            return jsonify({"success": False, "error": "Rotina não encontrada"}), 404
            
        return jsonify({"success": True, "data": updated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@rcon_routine_bp.route("/api/rcon-routines/<routine_id>", methods=["DELETE"])
@require_auth
@require_admin
def delete_routine(routine_id):
    """Exclui uma rotina RCON cadastrada."""
    services = get_services()
    manager = getattr(services, 'rcon_routine_manager', None)
    if not manager:
        return jsonify({"success": False, "error": "RconRoutineManager não inicializado"}), 500
    
    try:
        deleted = manager.delete_routine(routine_id)
        if not deleted:
            return jsonify({"success": False, "error": "Rotina não encontrada"}), 404
        return jsonify({"success": True, "message": "Rotina deletada com sucesso"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@rcon_routine_bp.route("/api/rcon-routines/<routine_id>/test", methods=["POST"])
@require_auth
@require_admin
def test_routine(routine_id):
    """
    Botão de Teste: executa e aguarda o retorno da RCON para cada comando da rotina,
    retornando as respostas em tempo real com um limite seguro para evitar timeout HTTP.
    """
    services = get_services()
    manager = getattr(services, 'rcon_routine_manager', None)
    rcon_queue_manager = getattr(services, 'rcon_queue_manager', None)
    if not manager or not rcon_queue_manager:
        return jsonify({"success": False, "error": "Serviços RconRoutine ou RconQueueManager não inicializados"}), 500
        
    try:
        routine = manager.get_routine(routine_id)
        if not routine:
            return jsonify({"success": False, "error": "Rotina não encontrada"}), 404
            
        commands = routine.get("commands", [])
        
        # Constrói a lista de comandos a testar
        test_commands = []
        
        # 1. Inclui o aviso prévio se estiver habilitado
        warning_enabled = routine.get("warning_enabled", False)
        warning_message = routine.get("warning_message", "")
        if warning_enabled and warning_message:
            interval_minutes = int(routine.get("interval_minutes", 60))
            warning_minutes_before = int(routine.get("warning_minutes_before", 5))
            warning_minutes_before = min(warning_minutes_before, max(1, interval_minutes - 1))
            formatted_msg = warning_message.replace("{minutes}", str(warning_minutes_before))
            
            # Sanitização (mesmo padrão do Kill Feed)
            formatted_msg = formatted_msg.replace("\r", "").replace("\n", "").replace('"', "'")
            formatted_msg = "".join(ch for ch in formatted_msg if ord(ch) >= 32).strip()

            # Tipo de chat numérico (mesmo padrão do Kill Feed): 7 = vermelho por padrão
            warning_color = routine.get("warning_color", "").strip()
            try:
                chat_type = int(warning_color) if warning_color.isdigit() else 7
            except (ValueError, AttributeError):
                chat_type = 7

            # Busca jogadores online (mesmo padrão do Kill Feed)
            online_steam_ids = []
            try:
                rcon_routine_manager_svc = getattr(services, 'rcon_routine_manager', None)
                # Acessa o db_manager via serviços do app
                app_services = services
                raw_db = getattr(app_services, 'db_manager', None) or getattr(app_services, 'log_processor', None)
                db_ref = getattr(raw_db, 'db_manager', raw_db) if raw_db else None
                if db_ref and hasattr(db_ref, 'db_path'):
                    from core.database.connector import DatabaseConnector
                    with DatabaseConnector.get_connection(db_ref.db_path, write_mode=False) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT steam_id FROM players_online WHERE status = 'online'")
                        online_steam_ids = [row[0] for row in cursor.fetchall() if row[0]]
            except Exception as e:
                pass  # Fallback para Announce

            if online_steam_ids:
                for steam_id in online_steam_ids:
                    test_commands.append(f'SendChat {chat_type} "{formatted_msg}" {steam_id}')
            else:
                # Fallback: Announce broadcast (sem cor)
                test_commands.append(f"Announce {formatted_msg}")
            
        # 2. Adiciona os comandos da rotina principal
        for cmd in commands:
            if cmd.strip():
                test_commands.append(sanitize_rcon_command_coords(cmd.strip()))
                
        if not test_commands:
            return jsonify({"success": False, "error": "Rotina não possui comandos ou aviso habilitado para testar"}), 400
            
        # Enfileira todos os comandos no RconQueueManager e guarda os Futures
        # Usamos prioridade 5 (alta prioridade de teste manual) e delay de 0.5s para rodar mais rápido
        futures = []
        for cmd in test_commands:
            fut = rcon_queue_manager.enqueue_command(
                command=cmd,
                delay_after=0.5,
                priority=5
            )
            futures.append((cmd, fut))
            
        # Aguarda a resposta de cada comando com um limite de tempo total de 25s
        import time
        start_time = time.time()
        max_wait_seconds = 25.0
        results = []
        
        for cmd, fut in futures:
            elapsed = time.time() - start_time
            if elapsed >= max_wait_seconds:
                # Se estourar o limite da requisição HTTP, o restante roda em background
                results.append({
                    "command": cmd,
                    "success": True,
                    "response": "Enfileirado (executando em background para evitar timeout HTTP)"
                })
                continue
                
            try:
                remaining = max_wait_seconds - elapsed
                # Garante pelo menos 1s de timeout se restar pouco tempo
                cmd_timeout = max(1.0, remaining)
                response = fut.result(timeout=cmd_timeout)
                results.append({
                    "command": cmd,
                    "success": True,
                    "response": response or "Sem resposta do servidor (OK)"
                })
            except Exception as e:
                results.append({
                    "command": cmd,
                    "success": False,
                    "response": f"Erro: {str(e)}"
                })
                
        # Atualiza a data da última execução, pois foi executada
        manager.update_last_run(routine_id, time.time())
        
        return jsonify({
            "success": True,
            "routine_name": routine.get("name"),
            "results": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
