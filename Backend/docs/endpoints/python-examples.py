#!/usr/bin/env python3
"""
Exemplos Python para SCUM Backend API
Coleção de exemplos práticos usando requests para testar todos os endpoints
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional


class SCUMBackendAPI:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "SCUM-Backend-Python/1.0", "Accept": "application/json"}
        )

    def health_check(self) -> Dict[str, Any]:
        """Verificar saúde da aplicação"""
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "error"}

    def get_server_status(self) -> Dict[str, Any]:
        """Obter status do servidor"""
        try:
            response = self.session.get(f"{self.base_url}/api/server/status")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "error"}

    def start_server(
        self, force: bool = False, wait_timeout: int = 30
    ) -> Dict[str, Any]:
        """Iniciar servidor"""
        try:
            data = {"force": force, "wait_timeout": wait_timeout}
            response = self.session.post(
                f"{self.base_url}/api/server/start",
                json=data,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "error"}

    def stop_server(
        self, force: bool = False, wait_timeout: int = 30
    ) -> Dict[str, Any]:
        """Parar servidor"""
        try:
            data = {"force": force, "wait_timeout": wait_timeout}
            response = self.session.post(
                f"{self.base_url}/api/server/stop",
                json=data,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "error"}

    def restart_server(
        self, force: bool = False, wait_timeout: int = 30
    ) -> Dict[str, Any]:
        """Reiniciar servidor (envia notificações para Discord)"""
        try:
            data = {"force": force, "wait_timeout": wait_timeout}
            response = self.session.post(
                f"{self.base_url}/api/server/restart",
                json=data,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "error"}

    def get_logs(
        self,
        limit: int = 100,
        level: Optional[str] = None,
        since: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Obter logs do servidor"""
        try:
            params = {"limit": limit}
            if level:
                params["level"] = level
            if since:
                params["since"] = since

            response = self.session.get(
                f"{self.base_url}/api/server/logs", params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "error"}


# ============================================================================
# EXEMPLOS DE USO
# ============================================================================


def exemplo_basico():
    """Exemplo básico de uso da API"""
    print("🔍 Exemplo Básico - SCUM Backend API")
    print("=" * 50)

    api = SCUMBackendAPI()

    # 1. Health check
    print("1. Verificando saúde da API...")
    health = api.health_check()
    print(f"   Status: {health.get('status', 'unknown')}")
    print(f"   Componentes: {health.get('components', {})}")
    print()

    # 2. Status do servidor
    print("2. Verificando status do servidor...")
    status = api.get_server_status()
    if status.get("success"):
        is_running = status["data"]["is_running"]
        service_name = status["data"]["service_name"]
        print(f"   Servidor: {service_name}")
        print(f"   Rodando: {is_running}")
        print(f"   Porta: {status['data']['port']}")
        print(f"   Max Players: {status['data']['max_players']}")
    else:
        print(f"   Erro: {status.get('error', 'Desconhecido')}")
    print()


def exemplo_controle_servidor():
    """Exemplo de controle do servidor"""
    print("🚀 Exemplo de Controle do Servidor")
    print("=" * 50)

    api = SCUMBackendAPI()

    # Verificar status atual
    print("1. Status atual...")
    status = api.get_server_status()
    if status.get("success"):
        is_running = status["data"]["is_running"]
        print(f"   Servidor rodando: {is_running}")

        if not is_running:
            # Iniciar servidor
            print("2. Iniciando servidor...")
            start_result = api.start_server(force=False, wait_timeout=30)
            if start_result.get("success"):
                print(f"   ✅ {start_result['message']}")

                # Aguardar e verificar
                print("3. Aguardando 10 segundos...")
                time.sleep(10)

                # Verificar se iniciou
                print("4. Verificando se iniciou...")
                new_status = api.get_server_status()
                if new_status.get("success"):
                    print(f"   Servidor rodando: {new_status['data']['is_running']}")
            else:
                print(f"   ❌ Erro: {start_result.get('message', 'Desconhecido')}")
        else:
            print("2. Servidor já está rodando!")
    else:
        print(f"   ❌ Erro ao obter status: {status.get('error', 'Desconhecido')}")
    print()


def exemplo_logs():
    """Exemplo de obtenção de logs"""
    print("📝 Exemplo de Logs")
    print("=" * 50)

    api = SCUMBackendAPI()

    # Últimos 10 logs
    print("1. Últimos 10 logs...")
    logs = api.get_logs(limit=10)
    if logs.get("success"):
        log_entries = logs["data"]["logs"]
        print(f"   Total de logs: {len(log_entries)}")

        for i, log in enumerate(log_entries[:5], 1):  # Mostrar apenas 5
            timestamp = log.get("timestamp", "N/A")
            level = log.get("level", "N/A")
            message = log.get("message", "N/A")
            print(f"   {i}. [{level}] {message}")
    else:
        print(f"   ❌ Erro: {logs.get('error', 'Desconhecido')}")
    print()

    # Logs de erro
    print("2. Logs de erro...")
    error_logs = api.get_logs(limit=5, level="error")
    if error_logs.get("success"):
        error_entries = error_logs["data"]["logs"]
        if error_entries:
            print(f"   Encontrados {len(error_entries)} logs de erro:")
            for log in error_entries:
                timestamp = log.get("timestamp", "N/A")
                message = log.get("message", "N/A")
                print(f"   - {timestamp}: {message}")
        else:
            print("   ✅ Nenhum log de erro encontrado!")
    else:
        print(f"   ❌ Erro: {error_logs.get('error', 'Desconhecido')}")
    print()


def exemplo_monitoramento():
    """Exemplo de monitoramento contínuo"""
    print("📊 Exemplo de Monitoramento")
    print("=" * 50)

    api = SCUMBackendAPI()

    print("Monitorando por 30 segundos (atualizações a cada 5s)...")
    print("Pressione Ctrl+C para parar")
    print()

    try:
        for i in range(6):  # 6 iterações de 5 segundos = 30 segundos
            print(f"=== Iteração {i+1}/6 - {datetime.now().strftime('%H:%M:%S')} ===")

            # Health check
            health = api.health_check()
            print(f"API Health: {health.get('status', 'unknown')}")

            # Server status
            status = api.get_server_status()
            if status.get("success"):
                is_running = status["data"]["is_running"]
                print(f"Server Running: {is_running}")
            else:
                print(f"Server Status: Erro - {status.get('error', 'Desconhecido')}")

            # Último log
            logs = api.get_logs(limit=1)
            if logs.get("success") and logs["data"]["logs"]:
                last_log = logs["data"]["logs"][0]
                level = last_log.get("level", "N/A")
                message = (
                    last_log.get("message", "N/A")[:50] + "..."
                    if len(last_log.get("message", "")) > 50
                    else last_log.get("message", "N/A")
                )
                print(f"Last Log: [{level}] {message}")

            print("---")

            if i < 5:  # Não aguardar na última iteração
                time.sleep(5)

    except KeyboardInterrupt:
        print("\n✅ Monitoramento interrompido pelo usuário")
    print()


def exemplo_sequencia_completa():
    """Exemplo de sequência completa de operações"""
    print("🔄 Exemplo de Sequência Completa")
    print("=" * 50)

    api = SCUMBackendAPI()

    # 1. Health check
    print("1. Verificando saúde da API...")
    health = api.health_check()
    if health.get("status") != "healthy":
        print(f"   ❌ API não está saudável: {health}")
        return
    print("   ✅ API está saudável")

    # 2. Status inicial
    print("2. Verificando status inicial...")
    initial_status = api.get_server_status()
    if initial_status.get("success"):
        is_running = initial_status["data"]["is_running"]
        print(f"   Status inicial: {'Rodando' if is_running else 'Parado'}")
    else:
        print(f"   ❌ Erro ao obter status: {initial_status.get('error')}")
        return

    # 3. Parar servidor (se estiver rodando)
    if is_running:
        print("3. Parando servidor...")
        stop_result = api.stop_server(force=False, wait_timeout=30)
        if stop_result.get("success"):
            print(f"   ✅ {stop_result['message']}")
        else:
            print(f"   ❌ Erro ao parar: {stop_result.get('message')}")
            return

        # Aguardar
        print("   Aguardando 5 segundos...")
        time.sleep(5)

    # 4. Iniciar servidor
    print("4. Iniciando servidor...")
    start_result = api.start_server(force=False, wait_timeout=30)
    if start_result.get("success"):
        print(f"   ✅ {start_result['message']}")
    else:
        print(f"   ❌ Erro ao iniciar: {start_result.get('message')}")
        return

    # 5. Verificar se iniciou
    print("5. Verificando se iniciou...")
    time.sleep(10)
    final_status = api.get_server_status()
    if final_status.get("success"):
        is_running = final_status["data"]["is_running"]
        print(f"   Status final: {'Rodando' if is_running else 'Parado'}")

        if is_running:
            print("   ✅ Sequência concluída com sucesso!")
        else:
            print("   ❌ Servidor não iniciou corretamente")
    else:
        print(f"   ❌ Erro ao verificar status final: {final_status.get('error')}")

    # 6. Logs finais
    print("6. Últimos logs...")
    logs = api.get_logs(limit=5)
    if logs.get("success"):
        log_entries = logs["data"]["logs"]
        for log in log_entries:
            level = log.get("level", "N/A")
            message = log.get("message", "N/A")
            print(f"   [{level}] {message}")
    print()


def exemplo_tratamento_erros():
    """Exemplo de tratamento de erros"""
    print("⚠️ Exemplo de Tratamento de Erros")
    print("=" * 50)

    # API com URL inválida para testar erros
    api_invalida = SCUMBackendAPI("http://localhost:9999")

    print("1. Testando com URL inválida...")
    health = api_invalida.health_check()
    if "error" in health:
        print(f"   ❌ Erro capturado: {health['error']}")
    else:
        print(f"   ✅ Resposta inesperada: {health}")

    # API válida
    api_valida = SCUMBackendAPI()

    print("2. Testando operação inválida...")
    # Tentar parar servidor que não está rodando
    stop_result = api_valida.stop_server(force=False, wait_timeout=30)
    if stop_result.get("success"):
        print(f"   ✅ {stop_result['message']}")
    else:
        print(
            f"   ⚠️ Resposta esperada: {stop_result.get('message', 'Erro desconhecido')}"
        )

    print("3. Testando com parâmetros inválidos...")
    # Tentar iniciar com timeout muito baixo
    start_result = api_valida.start_server(force=False, wait_timeout=0)
    if start_result.get("success"):
        print(f"   ✅ {start_result['message']}")
    else:
        print(f"   ⚠️ Resposta: {start_result.get('message', 'Erro desconhecido')}")
    print()


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================


def main():
    """Função principal com menu de exemplos"""
    print("🎮 SCUM Backend API - Exemplos Python")
    print("=" * 50)
    print()

    exemplos = {
        "1": ("Exemplo Básico", exemplo_basico),
        "2": ("Controle do Servidor", exemplo_controle_servidor),
        "3": ("Logs", exemplo_logs),
        "4": ("Monitoramento", exemplo_monitoramento),
        "5": ("Sequência Completa", exemplo_sequencia_completa),
        "6": ("Tratamento de Erros", exemplo_tratamento_erros),
        "0": ("Todos os Exemplos", None),
    }

    while True:
        print("Escolha um exemplo:")
        for key, (name, _) in exemplos.items():
            print(f"  {key}. {name}")
        print("  q. Sair")
        print()

        escolha = input("Digite sua escolha: ").strip().lower()

        if escolha == "q":
            print("👋 Até logo!")
            break
        elif escolha == "0":
            # Executar todos os exemplos
            for key, (name, func) in exemplos.items():
                if func:
                    print(f"\n{'='*60}")
                    print(f"Executando: {name}")
                    print("=" * 60)
                    func()
                    input("\nPressione Enter para continuar...")
        elif escolha in exemplos and exemplos[escolha][1]:
            print(f"\n{'='*60}")
            print(f"Executando: {exemplos[escolha][0]}")
            print("=" * 60)
            exemplos[escolha][1]()
            input("\nPressione Enter para continuar...")
        else:
            print("❌ Escolha inválida!")

        print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    main()
