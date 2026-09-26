from flask import Blueprint, jsonify, request
from app.extensions import get_services
from core.auth.decorators import require_auth, require_admin
from datetime import datetime
import re

events_bp = Blueprint('events', __name__)

def parse_raw_coordinates(coord_str: str):
    if not coord_str:
        return None
    coord_str = coord_str.strip()
    match = re.search(r'X=([\d\.\-]+)[,\s]+Y=([\d\.\-]+)[,\s]+Z=([\d\.\-]+)', coord_str, re.IGNORECASE)
    if match:
        return float(match.group(1)), float(match.group(2)), float(match.group(3))
    match = re.search(r'#ScheduleWorldEvent\s+\S+\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)', coord_str, re.IGNORECASE)
    if match:
        return float(match.group(1)), float(match.group(2)), float(match.group(3))
    # General fallback
    cleaned = coord_str.replace(',', ' ').replace('{', ' ').replace('}', ' ').replace('|', ' ')
    parts = []
    for part in cleaned.split():
        p_clean = re.sub(r'[^\d\.\-]', '', part)
        if p_clean:
            try:
                parts.append(float(p_clean))
            except ValueError:
                pass
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    return None

@events_bp.route("/api/events", methods=["GET"])
@require_auth
def list_events():
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        events = event_mgr.list_events()
        for event in events:
            coordinates = event_mgr.list_coordinates(event["event_id"])
            if coordinates:
                first_coord = coordinates[0]
                event["coordinates_raw"] = f"{{X={first_coord['x']:.3f} Y={first_coord['y']:.3f} Z={first_coord['z']:.3f}}}"
            else:
                event["coordinates_raw"] = ""
        return jsonify({"success": True, "data": events})
    except Exception as e:
        logger.error(f"Erro ao listar eventos: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events", methods=["POST"])
@require_auth
@require_admin
def create_event():
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"success": False, "error": "Nome do evento é obrigatório"}), 400
            
        description = data.get("description", "")
        webhook_url = data.get("webhook_url")
        duration_minutes = int(data.get("duration_minutes", 60))
        recurrence_interval_minutes = data.get("recurrence_interval_minutes")
        if recurrence_interval_minutes is not None:
            recurrence_interval_minutes = int(recurrence_interval_minutes)
            
        schedule_type = data.get("schedule_type", "manual")
        schedule_value = data.get("schedule_value")
        
        event_id = event_mgr.create_event(
            name=name,
            description=description,
            webhook_url=webhook_url,
            duration_minutes=duration_minutes,
            recurrence_interval_minutes=recurrence_interval_minutes,
            schedule_type=schedule_type,
            schedule_value=schedule_value
        )
        
        # Process and add coordinates if provided
        coordinates_raw = data.get("coordinates_raw") or data.get("location") or data.get("location_raw")
        parsed_coords = parse_raw_coordinates(coordinates_raw) if coordinates_raw else None
        
        if parsed_coords:
            x, y, z = parsed_coords
            event_mgr.add_coordinate(event_id, "Local do Evento", x, y, z)
        elif "x" in data and "y" in data and "z" in data:
            try:
                x = float(data["x"])
                y = float(data["y"])
                z = float(data["z"])
                event_mgr.add_coordinate(event_id, "Local do Evento", x, y, z)
            except (ValueError, TypeError):
                pass
        
        return jsonify({"success": True, "data": {"event_id": event_id}})
    except Exception as e:
        logger.error(f"Erro ao criar evento: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/<int:event_id>", methods=["GET"])
@require_auth
def get_event_details(event_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        event = event_mgr.get_event(event_id)
        if not event:
            return jsonify({"success": False, "error": "Evento não encontrado"}), 404
            
        coordinates = event_mgr.list_coordinates(event_id)
        commands = event_mgr.list_startup_commands(event_id)
        
        event["coordinates"] = coordinates
        event["commands"] = commands
        
        if coordinates:
            first_coord = coordinates[0]
            event["coordinates_raw"] = f"{{X={first_coord['x']:.3f} Y={first_coord['y']:.3f} Z={first_coord['z']:.3f}}}"
        else:
            event["coordinates_raw"] = ""
            
        return jsonify({"success": True, "data": event})
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do evento: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/<int:event_id>", methods=["PUT"])
@require_auth
@require_admin
def update_event(event_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"success": False, "error": "Nome do evento é obrigatório"}), 400
            
        description = data.get("description", "")
        webhook_url = data.get("webhook_url")
        duration_minutes = int(data.get("duration_minutes", 60))
        recurrence_interval_minutes = data.get("recurrence_interval_minutes")
        if recurrence_interval_minutes is not None:
            recurrence_interval_minutes = int(recurrence_interval_minutes)
            
        schedule_type = data.get("schedule_type", "manual")
        schedule_value = data.get("schedule_value")
        
        success = event_mgr.update_event(
            event_id=event_id,
            name=name,
            description=description,
            webhook_url=webhook_url,
            duration_minutes=duration_minutes,
            recurrence_interval_minutes=recurrence_interval_minutes,
            schedule_type=schedule_type,
            schedule_value=schedule_value
        )
        
        # Process and update coordinates if provided
        coordinates_raw = data.get("coordinates_raw") or data.get("location") or data.get("location_raw")
        parsed_coords = parse_raw_coordinates(coordinates_raw) if coordinates_raw else None
        
        if parsed_coords or ("x" in data and "y" in data and "z" in data):
            # Remove existing coords
            coords = event_mgr.list_coordinates(event_id)
            for c in coords:
                event_mgr.remove_coordinate(c["coord_id"])
                
            if parsed_coords:
                x, y, z = parsed_coords
                event_mgr.add_coordinate(event_id, "Local do Evento", x, y, z)
            else:
                try:
                    x = float(data["x"])
                    y = float(data["y"])
                    z = float(data["z"])
                    event_mgr.add_coordinate(event_id, "Local do Evento", x, y, z)
                except (ValueError, TypeError):
                    pass
        
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Erro ao atualizar evento: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/<int:event_id>", methods=["DELETE"])
@require_auth
@require_admin
def delete_event(event_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        success = event_mgr.delete_event(event_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Erro ao deletar evento: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/<int:event_id>/start", methods=["POST"])
@require_auth
@require_admin
def start_event(event_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        success = event_mgr.start_event(event_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Erro ao iniciar evento: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/<int:event_id>/stop", methods=["POST"])
@require_auth
@require_admin
def stop_event(event_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        success = event_mgr.stop_event(event_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Erro ao finalizar evento: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Coordenadas
@events_bp.route("/api/events/<int:event_id>/coordinates", methods=["POST"])
@require_auth
@require_admin
def add_coordinate(event_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        data = request.get_json() or {}
        name = data.get("name")
        x = float(data.get("x", 0.0))
        y = float(data.get("y", 0.0))
        z = float(data.get("z", 0.0))
        
        if not name:
            return jsonify({"success": False, "error": "Nome da coordenada é obrigatório"}), 400
            
        coord_id = event_mgr.add_coordinate(event_id, name, x, y, z)
        return jsonify({"success": True, "data": {"coord_id": coord_id}})
    except Exception as e:
        logger.error(f"Erro ao adicionar coordenada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/coordinates/<int:coord_id>", methods=["DELETE"])
@require_auth
@require_admin
def remove_coordinate(coord_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        success = event_mgr.remove_coordinate(coord_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Erro ao remover coordenada: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Comandos
@events_bp.route("/api/events/<int:event_id>/commands", methods=["POST"])
@require_auth
@require_admin
def add_startup_command(event_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        data = request.get_json() or {}
        command_string = data.get("command_string")
        order_index = int(data.get("order_index", 0))
        recurrence_interval_minutes = data.get("recurrence_interval_minutes")
        if recurrence_interval_minutes is not None:
            recurrence_interval_minutes = int(recurrence_interval_minutes)
        
        if not command_string:
            return jsonify({"success": False, "error": "Comando RCON é obrigatório"}), 400
            
        startup_id = event_mgr.add_startup_command(
            event_id=event_id, 
            command_string=command_string, 
            order_index=order_index, 
            recurrence_interval_minutes=recurrence_interval_minutes
        )
        return jsonify({"success": True, "data": {"startup_id": startup_id}})
    except Exception as e:
        logger.error(f"Erro ao adicionar comando inicial: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/commands/<int:startup_id>", methods=["DELETE"])
@require_auth
@require_admin
def remove_startup_command(startup_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        success = event_mgr.remove_startup_command(startup_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Erro ao remover comando inicial: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/commands/<int:startup_id>", methods=["PUT"])
@require_auth
@require_admin
def update_startup_command(startup_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        data = request.get_json() or {}
        recurrence = data.get("recurrence_interval_minutes")
        if recurrence is not None and recurrence != "":
            recurrence = int(recurrence)
        else:
            recurrence = None
            
        success = event_mgr.update_startup_command(startup_id, recurrence)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Erro ao atualizar comando inicial: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/<int:event_id>/commands/sync", methods=["PUT"])
@require_auth
@require_admin
def sync_startup_commands(event_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        data = request.get_json() or {}
        commands = data.get("commands", [])
        
        # Deletar todos os comandos atuais do evento
        current_commands = event_mgr.list_startup_commands(event_id)
        for cmd in current_commands:
            event_mgr.remove_startup_command(cmd["startup_id"])
            
        # Adicionar os novos
        for idx, cmd in enumerate(commands):
            event_mgr.add_startup_command(
                event_id=event_id,
                command_string=cmd.get("command_string"),
                order_index=idx,
                recurrence_interval_minutes=cmd.get("recurrence_interval_minutes")
            )
            
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Erro ao sincronizar comandos iniciais: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/<int:event_id>/coordinates/sync", methods=["PUT"])
@require_auth
@require_admin
def sync_coordinates(event_id):
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        data = request.get_json() or {}
        coordinates = data.get("coordinates", [])
        
        # Deletar todas as coordenadas atuais do evento
        current_coords = event_mgr.list_coordinates(event_id)
        for coord in current_coords:
            event_mgr.remove_coordinate(coord["coord_id"])
            
        # Adicionar as novas
        for coord in coordinates:
            event_mgr.add_coordinate(
                event_id=event_id,
                name=coord.get("name"),
                x=float(coord.get("x", 0.0)),
                y=float(coord.get("y", 0.0)),
                z=float(coord.get("z", 0.0))
            )
            
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Erro ao sincronizar coordenadas: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Teste & Homologação
@events_bp.route("/api/events/test-command", methods=["POST"])
@require_auth
@require_admin
def test_command():
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        data = request.get_json() or {}
        command = data.get("command")
        if not command:
            return jsonify({"success": False, "error": "Comando RCON é obrigatório"}), 400
            
        result = event_mgr.test_command(command)
        return jsonify({"success": result["success"], "data": {"response": result["response"]}})
    except Exception as e:
        logger.error(f"Erro ao testar comando RCON: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/tested-commands", methods=["POST"])
@require_auth
@require_admin
def register_tested_command():
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        data = request.get_json() or {}
        command = data.get("command")
        requires_coordinates = data.get("requires_coordinates", 0)
        
        if not command:
            return jsonify({"success": False, "error": "Comando é obrigatório"}), 400
            
        event_mgr._register_tested_command(command, "success", requires_coordinates)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Erro ao registrar comando testado: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@events_bp.route("/api/events/tested-commands", methods=["GET"])
@require_auth
def list_tested_commands():
    services = get_services()
    logger = services.logger
    event_mgr = getattr(services, 'event_manager', None)
    
    if not event_mgr:
        return jsonify({"success": False, "error": "EventManager não inicializado"}), 500
        
    try:
        tested_cmds = event_mgr.list_tested_commands()
        return jsonify({"success": True, "data": tested_cmds})
    except Exception as e:
        logger.error(f"Erro ao listar comandos testados: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
