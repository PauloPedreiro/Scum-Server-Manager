"""
Script para gerar payload do Postman para teste de validação de licença
Uso: python tools/generate_postman_payload.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Adicionar raiz do projeto ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from core.licensing.hardware_fingerprint import HardwareFingerprint
    from core.licensing.license_cache import LicenseCache
    from utils.logger import StructuredLogger
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Certifique-se de estar executando do diretório raiz do projeto")
    sys.exit(1)


def generate_payload():
    """Gera payload completo para teste no Postman"""

    print("🔍 Coletando informações de hardware...")

    # Inicializar logger
    logger = StructuredLogger(name="postman_payload_generator")

    # Inicializar HardwareFingerprint
    hardware_fp = HardwareFingerprint(logger=logger)

    # Gerar equipment_hash
    # SEGURANÇA: Hash sempre gerado em memória, nunca armazenado
    equipment_hash, components = hardware_fp.generate()
    print(f"✓ Equipment Hash gerado: {equipment_hash}")

    # Coletar hardware_list completo
    hardware_list = hardware_fp.get_hardware_list()
    print("✓ Hardware list coletado")

    # Gerar timestamp ISO 8601 UTC
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Montar payload
    payload = {
        "equipment_hash": equipment_hash,
        "hardware_list": hardware_list,
        "timestamp": timestamp,
        "version": "3.0.1",
    }

    # Opcional: adicionar backend_id se necessário
    # payload["backend_id"] = "SCUM-BACKEND-TEST"

    return payload


def main():
    """Função principal"""
    try:
        payload = generate_payload()

        print("\n" + "=" * 60)
        print("📋 PAYLOAD PARA POSTMAN")
        print("=" * 60)
        print("\nURL: http://localhost:8000/api/v1/validate")
        print("Method: POST")
        print("Headers:")
        print("  Content-Type: application/json")
        print("  User-Agent: SSM-Backend/1.0")
        print("\nBody (JSON):")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("💾 Salvando em arquivo...")

        # Salvar em arquivo
        output_file = ROOT_DIR / "data" / "postman_payload.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        print(f"✓ Payload salvo em: {output_file}")
        print("\n💡 Dica: Copie o JSON acima e cole no Body do Postman (raw, JSON)")

    except Exception as e:
        print(f"\n❌ Erro ao gerar payload: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
