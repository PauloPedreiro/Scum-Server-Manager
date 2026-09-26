#!/usr/bin/env python3
"""
Editor de Configuração - Interface para editar config.json e webhooks.json
Interface web simples usando Flask
"""

import os
import json
import sys
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS

# Adicionar diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

app = Flask(__name__)
CORS(app)

# Caminhos dos arquivos de configuração
CONFIG_DIR = ROOT_DIR / "data"
CONFIG_FILE = CONFIG_DIR / "config.json"
WEBHOOKS_FILE = CONFIG_DIR / "webhooks.json"
CONFIG_EXAMPLE = CONFIG_DIR / "config.example.json"
WEBHOOKS_EXAMPLE = CONFIG_DIR / "webhooks.example.json"

# Template HTML para a interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configuração SSM Backend</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
        }
        .tabs {
            display: flex;
            background: #f5f5f5;
            border-bottom: 2px solid #ddd;
        }
        .tab {
            flex: 1;
            padding: 15px 20px;
            cursor: pointer;
            text-align: center;
            font-weight: 600;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }
        .tab:hover {
            background: #e8e8e8;
        }
        .tab.active {
            background: white;
            border-bottom-color: #667eea;
            color: #667eea;
        }
        .tab-content {
            display: none;
            padding: 30px;
        }
        .tab-content.active {
            display: block;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        .form-group textarea {
            min-height: 100px;
            font-family: 'Courier New', monospace;
            resize: vertical;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background: #5a6268;
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn-success:hover {
            background: #218838;
        }
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #eee;
        }
        .alert {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .webhook-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }
        .webhook-item label {
            display: block;
            margin-bottom: 5px;
            color: #667eea;
            font-weight: 600;
        }
        .json-viewer {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .help-text {
            font-size: 12px;
            color: #6c757d;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ Configuração SSM Backend</h1>
            <p>Configure os arquivos config.json e webhooks.json</p>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="switchTab('config')">Config.json</div>
            <div class="tab" onclick="switchTab('webhooks')">Webhooks.json</div>
        </div>
        
        <div id="alert-container"></div>
        
        <!-- Tab Config.json -->
        <div id="config-tab" class="tab-content active">
            <h2>Configurações Principais</h2>
            <form id="config-form">
                <div class="form-row">
                    <div class="form-group">
                        <label>Porta da API</label>
                        <input type="number" name="api_port" id="api_port" value="3000">
                    </div>
                    <div class="form-group">
                        <label>Host da API</label>
                        <input type="text" name="api_host" id="api_host" value="127.0.0.1">
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Caminho do Servidor SCUM</label>
                    <input type="text" name="scum_root" id="scum_root" placeholder="C:\\Servers\\Scum">
                    <div class="help-text">Caminho completo para o diretório raiz do servidor SCUM</div>
                </div>
                
                <div class="form-group">
                    <label>Caminho do Banco de Dados SCUM</label>
                    <input type="text" name="scum_db" id="scum_db" placeholder="C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db">
                </div>
                
                <div class="form-group">
                    <label>Configuração JSON Completa</label>
                    <textarea id="config-json" name="config_json" rows="15"></textarea>
                    <div class="help-text">Edite o JSON completo aqui. Use "Carregar do Arquivo" para ver a estrutura atual.</div>
                </div>
                
                <div class="actions">
                    <button type="button" class="btn btn-secondary" onclick="loadConfigFile()">Carregar do Arquivo</button>
                    <button type="button" class="btn btn-primary" onclick="saveConfig()">Salvar Configuração</button>
                </div>
            </form>
        </div>
        
        <!-- Tab Webhooks.json -->
        <div id="webhooks-tab" class="tab-content">
            <h2>Webhooks do Discord</h2>
            <form id="webhooks-form">
                <div id="webhooks-container"></div>
                
                <div class="form-group">
                    <label>JSON Completo dos Webhooks</label>
                    <textarea id="webhooks-json" name="webhooks_json" rows="15"></textarea>
                </div>
                
                <div class="actions">
                    <button type="button" class="btn btn-secondary" onclick="loadWebhooksFile()">Carregar do Arquivo</button>
                    <button type="button" class="btn btn-primary" onclick="saveWebhooks()">Salvar Webhooks</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        function switchTab(tab) {
            // Atualizar tabs
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tab + '-tab').classList.add('active');
        }
        
        function showAlert(message, type) {
            const container = document.getElementById('alert-container');
            container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
            setTimeout(() => {
                container.innerHTML = '';
            }, 5000);
        }
        
        async function loadConfigFile() {
            try {
                const response = await fetch('/api/config/load');
                const data = await response.json();
                if (data.success) {
                    document.getElementById('config-json').value = JSON.stringify(data.config, null, 2);
                    showAlert('Configuração carregada com sucesso!', 'success');
                } else {
                    showAlert('Erro ao carregar: ' + data.error, 'error');
                }
            } catch (error) {
                showAlert('Erro ao carregar configuração: ' + error.message, 'error');
            }
        }
        
        async function saveConfig() {
            try {
                const jsonText = document.getElementById('config-json').value;
                const config = JSON.parse(jsonText);
                
                const response = await fetch('/api/config/save', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({config})
                });
                
                const data = await response.json();
                if (data.success) {
                    showAlert('Configuração salva com sucesso!', 'success');
                } else {
                    showAlert('Erro ao salvar: ' + data.error, 'error');
                }
            } catch (error) {
                showAlert('Erro: JSON inválido - ' + error.message, 'error');
            }
        }
        
        async function loadWebhooksFile() {
            try {
                const response = await fetch('/api/webhooks/load');
                const data = await response.json();
                if (data.success) {
                    document.getElementById('webhooks-json').value = JSON.stringify(data.webhooks, null, 2);
                    showAlert('Webhooks carregados com sucesso!', 'success');
                } else {
                    showAlert('Erro ao carregar: ' + data.error, 'error');
                }
            } catch (error) {
                showAlert('Erro ao carregar webhooks: ' + error.message, 'error');
            }
        }
        
        async function saveWebhooks() {
            try {
                const jsonText = document.getElementById('webhooks-json').value;
                const webhooks = JSON.parse(jsonText);
                
                const response = await fetch('/api/webhooks/save', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({webhooks})
                });
                
                const data = await response.json();
                if (data.success) {
                    showAlert('Webhooks salvos com sucesso!', 'success');
                } else {
                    showAlert('Erro ao salvar: ' + data.error, 'error');
                }
            } catch (error) {
                showAlert('Erro: JSON inválido - ' + error.message, 'error');
            }
        }
        
        // Carregar configurações ao iniciar
        window.onload = function() {
            loadConfigFile();
            loadWebhooksFile();
        };
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Página principal"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/config/load", methods=["GET"])
def load_config():
    """Carregar config.json"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            return jsonify({"success": True, "config": config})
        elif CONFIG_EXAMPLE.exists():
            with open(CONFIG_EXAMPLE, "r", encoding="utf-8") as f:
                config = json.load(f)
            return jsonify({"success": True, "config": config, "from_example": True})
        else:
            return jsonify({"success": False, "error": "Arquivo não encontrado"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/config/save", methods=["POST"])
def save_config():
    """Salvar config.json"""
    try:
        data = request.json
        config = data.get("config")

        # Garantir que o diretório existe
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Salvar arquivo
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        return jsonify({"success": True, "message": "Configuração salva com sucesso"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/webhooks/load", methods=["GET"])
def load_webhooks():
    """Carregar webhooks.json"""
    try:
        if WEBHOOKS_FILE.exists():
            with open(WEBHOOKS_FILE, "r", encoding="utf-8") as f:
                webhooks = json.load(f)
            return jsonify({"success": True, "webhooks": webhooks})
        elif WEBHOOKS_EXAMPLE.exists():
            with open(WEBHOOKS_EXAMPLE, "r", encoding="utf-8") as f:
                webhooks = json.load(f)
            return jsonify(
                {"success": True, "webhooks": webhooks, "from_example": True}
            )
        else:
            return jsonify({"success": False, "error": "Arquivo não encontrado"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/webhooks/save", methods=["POST"])
def save_webhooks():
    """Salvar webhooks.json"""
    try:
        data = request.json
        webhooks = data.get("webhooks")

        # Garantir que o diretório existe
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Salvar arquivo
        with open(WEBHOOKS_FILE, "w", encoding="utf-8") as f:
            json.dump(webhooks, f, indent=2, ensure_ascii=False)

        return jsonify({"success": True, "message": "Webhooks salvos com sucesso"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def main():
    # SEGURANÇA: este editor expõe configuração sensível em uma interface web.
    # Ele só pode ser executado quando explicitamente habilitado.
    if str(os.environ.get("SSM_ENABLE_CONFIG_EDITOR") or "").strip() != "1":
        print(
            "Config editor is disabled by default. Set SSM_ENABLE_CONFIG_EDITOR=1 to enable.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    print("=" * 60)
    print("Editor de Configuração SSM Backend")
    print("=" * 60)
    print("\nAcesse: http://127.0.0.1:8888")
    print("\nPressione Ctrl+C para encerrar")

    app.run(host="127.0.0.1", port=8888, debug=False)


if __name__ == "__main__":
    main()
