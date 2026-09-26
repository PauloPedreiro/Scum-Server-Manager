"""
SSM Backend - App Factory

Este módulo contém a função create_app() que cria e configura a instância
Flask da aplicação. Implementa o padrão App Factory do Flask.

A transição do monolito (main.py) é incremental:
- Blueprints migrados são registrados aqui via register_all_blueprints()
- Rotas ainda no main.py continuam funcionando normalmente
- O ServiceRegistry (extensions.py) substitui as variáveis globais
"""

from flask import Flask  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
from flask_cors import CORS  # pyright: ignore[reportMissingImports, reportMissingModuleSource]


def create_app(config: dict = None) -> Flask:
    """
    Factory function para criar e configurar o app Flask.

    Args:
        config: Configuração opcional para override

    Returns:
        Instância Flask configurada com Blueprints e middleware
    """
    app = Flask(__name__)

    # Configurar CORS para permitir requisições do frontend
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:8000",
                    "http://127.0.0.1:8000",
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                ]
            }
        },
        supports_credentials=True,
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Server-Hash",
        ],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # Registrar middleware (error handlers, before_request)
    from app.middleware import register_middleware
    register_middleware(app)

    # Registrar Blueprints
    from app.routes import register_all_blueprints
    register_all_blueprints(app)

    return app
