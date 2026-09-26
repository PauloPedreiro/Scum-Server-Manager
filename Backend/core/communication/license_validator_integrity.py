"""
Sistema de Verificação de Integridade do LicenseValidator
Verifica se o módulo license_validator.py não foi modificado ou extraído do executável
"""

import hashlib
import sys
import os
from pathlib import Path
from typing import Tuple

# Hash SHA-256 do módulo license_validator.py (calculado no build)
# Este hash é gerado durante o build e hardcoded aqui
# Se o módulo for modificado, o hash não corresponderá
EXPECTED_MODULE_HASH = None  # Será definido durante o build

# Constantes e classes críticas que devem estar presentes no módulo
REQUIRED_MODULE_ATTRIBUTES = [
    "VALIDATION_INTERVAL_SECONDS",  # Constante
    "LicenseValidator",  # Classe
]

# Métodos críticos que devem estar na classe LicenseValidator
REQUIRED_CLASS_METHODS = ["validate_license", "should_validate_now"]

# Strings críticas que devem estar no código (proteção contra modificação)
# NOTA: A verificação de 'VALIDATION_INTERVAL_SECONDS = 14400' pode falhar em modo de teste
# pois permitimos valores menores em desenvolvimento
REQUIRED_CODE_SIGNATURES = [
    "VALIDATION_INTERVAL_SECONDS =",  # Verificar que existe, mas não o valor exato
    "def validate_license",
    "def should_validate_now",
    "SEGURANÇA: Validação sempre ativa",
    "Sem período de graça",
]


def calculate_module_hash(module_path: str) -> str:
    """Calcular hash SHA-256 de um módulo Python"""
    try:
        with open(module_path, "rb") as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()
    except Exception:
        return None


def verify_module_integrity() -> Tuple[bool, str]:
    """
    Verificar integridade do módulo license_validator

    Returns:
        (is_valid: bool, error_message: str)
    """
    try:
        # Tentar importar o módulo
        try:
            import core.communication.license_validator as lv_module
        except ImportError as e:
            return False, f"Módulo license_validator não pode ser importado: {e}"

        # Verificar se está rodando como executável
        is_frozen = getattr(sys, "frozen", False)

        if is_frozen:
            # Em executável, verificar se módulo existe no sys.modules
            if "core.communication.license_validator" not in sys.modules:
                return False, "Módulo license_validator não encontrado em sys.modules"

            # Verificar constantes e classes críticas do módulo
            for attr_name in REQUIRED_MODULE_ATTRIBUTES:
                if not hasattr(lv_module, attr_name):
                    return (
                        False,
                        f"Atributo crítico '{attr_name}' não encontrado no módulo",
                    )

            # Verificar VALIDATION_INTERVAL_SECONDS tem valor correto
            # Em executável, deve ser exatamente 14400 (produção)
            if hasattr(lv_module, "VALIDATION_INTERVAL_SECONDS"):
                interval = getattr(lv_module, "VALIDATION_INTERVAL_SECONDS")
                if interval != 14400:
                    return (
                        False,
                        f"VALIDATION_INTERVAL_SECONDS foi modificado: {interval} (esperado: 14400)",
                    )

            # Verificar se LicenseValidator existe e tem métodos críticos
            if not hasattr(lv_module, "LicenseValidator"):
                return False, "Classe LicenseValidator não encontrada"

            LicenseValidator = getattr(lv_module, "LicenseValidator")
            for method_name in REQUIRED_CLASS_METHODS:
                if not hasattr(LicenseValidator, method_name):
                    return (
                        False,
                        f"Método crítico '{method_name}' não encontrado em LicenseValidator",
                    )

            # Verificar código fonte (se disponível)
            try:
                module_file = getattr(lv_module, "__file__", None)
                if module_file:
                    # Tentar ler o arquivo e verificar assinaturas
                    with open(module_file, "r", encoding="utf-8", errors="ignore") as f:
                        source_code = f.read()

                    # Verificar se assinaturas críticas estão presentes
                    for signature in REQUIRED_CODE_SIGNATURES:
                        if signature not in source_code:
                            return (
                                False,
                                f"Assinatura crítica não encontrada no código: {signature[:50]}...",
                            )
            except Exception:
                # Se não conseguir ler o arquivo (normal em executável), continuar
                pass

            return True, "Integridade verificada com sucesso"
        else:
            # Em modo desenvolvimento, verificar arquivo físico
            module_file = getattr(lv_module, "__file__", None)
            if not module_file:
                return False, "Não foi possível determinar localização do módulo"

            if not os.path.exists(module_file):
                return False, f"Arquivo do módulo não existe: {module_file}"

            # Verificar constantes e classes do módulo
            for attr_name in REQUIRED_MODULE_ATTRIBUTES:
                if not hasattr(lv_module, attr_name):
                    return False, f"Atributo crítico '{attr_name}' não encontrado"

            # Verificar se LicenseValidator existe e tem métodos críticos
            if not hasattr(lv_module, "LicenseValidator"):
                return False, "Classe LicenseValidator não encontrada"

            LicenseValidator = getattr(lv_module, "LicenseValidator")
            for method_name in REQUIRED_CLASS_METHODS:
                if not hasattr(LicenseValidator, method_name):
                    return (
                        False,
                        f"Método crítico '{method_name}' não encontrado em LicenseValidator",
                    )

            # Verificar VALIDATION_INTERVAL_SECONDS
            # Em modo desenvolvimento, permitir valores menores para testes (ex: 120 segundos)
            # Em produção (executável), deve ser exatamente 14400
            if hasattr(lv_module, "VALIDATION_INTERVAL_SECONDS"):
                interval = getattr(lv_module, "VALIDATION_INTERVAL_SECONDS")
                # Permitir valores de teste em desenvolvimento (qualquer valor <= 14400)
                # Em executável, já foi verificado acima que deve ser exatamente 14400
                if interval > 14400:
                    return (
                        False,
                        f"VALIDATION_INTERVAL_SECONDS não pode ser maior que 14400: {interval}",
                    )
                # Em desenvolvimento, permitir qualquer valor <= 14400 (para testes)
                # Não bloquear valores menores que 14400 em modo desenvolvimento

            return True, "Integridade verificada com sucesso"

    except Exception as e:
        return False, f"Erro ao verificar integridade: {e}"


def verify_module_not_extracted() -> Tuple[bool, str]:
    """
    Verificar se o módulo não foi extraído do executável para fora

    Returns:
        (is_valid: bool, error_message: str)
    """
    try:
        is_frozen = getattr(sys, "frozen", False)

        if not is_frozen:
            # Em modo desenvolvimento, não há problema
            return True, "Modo desenvolvimento - verificação não aplicável"

        # Em executável, verificar se arquivo físico existe fora do executável
        # Se alguém extraiu o módulo, pode tentar modificá-lo
        exe_dir = Path(sys.executable).parent
        possible_extracted_path = (
            exe_dir / "core" / "communication" / "license_validator.py"
        )

        if possible_extracted_path.exists():
            return (
                False,
                f"Módulo license_validator.py encontrado fora do executável: {possible_extracted_path}",
            )

        # Verificar também em subdiretórios comuns
        for subdir in ["core", "lib", "modules"]:
            check_path = exe_dir / subdir / "communication" / "license_validator.py"
            if check_path.exists():
                return (
                    False,
                    f"Módulo license_validator.py encontrado em local suspeito: {check_path}",
                )

        return True, "Nenhum arquivo extraído detectado"

    except Exception as e:
        return False, f"Erro ao verificar extração: {e}"
