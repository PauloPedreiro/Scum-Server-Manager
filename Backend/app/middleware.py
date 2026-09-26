"""
Middleware e error handlers do Flask.
Extraído do main.py durante refatoração modular.

Registra:
- before_request: verificação de licença
- errorhandler(BadRequest): JSON malformado
"""

from flask import request, jsonify  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
from werkzeug.exceptions import BadRequest  # pyright: ignore[reportMissingImports, reportMissingModuleSource]


def register_middleware(app):
    """
    Registrar todos os middlewares e error handlers no app Flask.

    Args:
        app: Instância do Flask
    """

    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        """Tratar erros de BadRequest (geralmente JSON malformado)"""
        from app.extensions import get_services
        services = get_services()
        if services.logger:
            services.logger.error(f"BadRequest error: {e}")

        # Verificar se é erro de JSON
        if "JSON" in str(e) or "json" in str(e).lower():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "JSON inválido ou malformado",
                        "message": "Verifique se o Content-Type é application/json e se o JSON está bem formatado",
                    }
                ),
                400,
            )

        return (
            jsonify({"success": False, "error": str(e), "message": "Requisição inválida"}),
            400,
        )

    @app.before_request
    def check_license_before_request():
        """Verificar se licença é válida antes de processar requisição"""
        from app.extensions import get_services
        services = get_services()

        # Rotas que não precisam de validação de licença
        exempt_paths = [
            "/api/health",
            "/api/licensing/hardware-fingerprint",
            "/api/auth/login",  # Permitir login mesmo com licença inválida
        ]

        # Verificar se a rota está isenta
        if request.path in exempt_paths:
            return None

        # SEGURANÇA: Verificar se license_validator está inicializado
        license_validator = services.license_validator
        if not license_validator:
            # Se LicenseValidator não está disponível, bloquear TODAS as requisições
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sistema de validação de licença não disponível",
                        "code": "LICENSE_VALIDATOR_MISSING",
                        "message": "O sistema de validação de licença não está disponível. A aplicação não pode funcionar sem ele.",
                    }
                ),
                503,
            )  # Service Unavailable

        # Verificar se license_validator está habilitado
        if license_validator.licensing_enabled:
            # Verificar se licença é válida
            if not license_validator.is_valid:
                # Licença inválida - bloquear requisição
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Backend bloqueado - Licença inválida",
                            "code": "LICENSE_INVALID",
                            "message": "O backend foi bloqueado devido a licença inválida. Verifique sua licença no painel administrativo.",
                        }
                    ),
                    503,
                )  # Service Unavailable

        return None
