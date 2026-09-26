"""
Registro centralizado de todos os Blueprints da API.

Cada Blueprint é um módulo independente que agrupa rotas por domínio.
Novos Blueprints devem ser importados e adicionados à lista aqui.
"""


def register_all_blueprints(app):
    """
    Registrar todos os Blueprints no app Flask.

    Args:
        app: Instância do Flask

    NOTA PARA O DESENVOLVEDOR:
    À medida que as rotas forem migradas do main.py para seus respectivos
    Blueprints, basta importá-las aqui e registrá-las.
    As rotas que ainda estiverem no main.py continuarão funcionando
    normalmente (o main.py registra elas diretamente no app).
    """
    # ---- Blueprints já migrados ----
    from app.routes.system import system_bp
    app.register_blueprint(system_bp)

    # ---- Blueprints pendentes de migração ----
    # Descomente cada linha à medida que as rotas forem migradas:
    
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.routes.server import server_bp
    app.register_blueprint(server_bp)
    #
    from app.routes.players import players_bp
    app.register_blueprint(players_bp)
    
    from app.routes.shop import shop_bp
    app.register_blueprint(shop_bp)
    #
    from app.routes.rankings import rankings_bp
    app.register_blueprint(rankings_bp)
    
    from app.routes.vehicles import vehicles_bp
    app.register_blueprint(vehicles_bp)
    
    from app.routes.squads import squads_bp
    app.register_blueprint(squads_bp)
    
    from app.routes.survival import survival_bp
    app.register_blueprint(survival_bp)
    
    from app.routes.chests import chests_bp
    app.register_blueprint(chests_bp)
    
    from app.routes.gps import gps_bp
    app.register_blueprint(gps_bp)
    #
    from app.routes.scheduler_routes import scheduler_bp
    app.register_blueprint(scheduler_bp)
    
    from app.routes.config_routes import config_bp
    app.register_blueprint(config_bp)
    
    from app.routes.logs import logs_bp
    app.register_blueprint(logs_bp)
    
    from app.routes.reports import reports_bp
    app.register_blueprint(reports_bp)
    
    from app.routes.integrations import integrations_bp
    app.register_blueprint(integrations_bp)
    
    from app.routes.player_app import player_app_bp
    app.register_blueprint(player_app_bp)
    
    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)
    
    from app.routes.chat import chat_bp
    app.register_blueprint(chat_bp)
    
    from app.routes.notifications import notifications_bp
    app.register_blueprint(notifications_bp)
    
    from app.routes.permissions import permissions_bp
    app.register_blueprint(permissions_bp)
    
    from app.routes.elevated_users import elevated_users_bp
    app.register_blueprint(elevated_users_bp)

    from app.routes.events import events_bp
    app.register_blueprint(events_bp)

    from app.routes.rcon_routine_routes import rcon_routine_bp
    app.register_blueprint(rcon_routine_bp)
