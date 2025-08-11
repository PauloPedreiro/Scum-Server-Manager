const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let serverProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        },
        icon: path.join(__dirname, 'icon.ico'),
        title: 'Scum Server Manager'
    });

    // Criar HTML simples
    const htmlContent = `
<!DOCTYPE html>
<html>
<head>
    <title>Scum Server Manager</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            color: white;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            color: #fff;
        }
        .status {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
        }
        .endpoint {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            font-family: monospace;
        }
        .btn {
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
        }
        .btn:hover {
            background: #45a049;
        }
        .btn-danger {
            background: #f44336;
        }
        .btn-danger:hover {
            background: #da190b;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Scum Server Manager</h1>
        
        <div class="status">
            <h3>📊 Status do Servidor</h3>
            <p id="serverStatus">Iniciando...</p>
        </div>

        <div class="status">
            <h3>🔗 Endpoints Disponíveis</h3>
            <div class="endpoint">API Principal: <a href="http://localhost:3000" target="_blank">http://localhost:3000</a></div>
            <div class="endpoint">Health Check: <a href="http://localhost:3000/health" target="_blank">http://localhost:3000/health</a></div>
            <div class="endpoint">Estatísticas: <a href="http://localhost:3000/funny-stats" target="_blank">http://localhost:3000/funny-stats</a></div>
            <div class="endpoint">Jogadores: <a href="http://localhost:3000/players" target="_blank">http://localhost:3000/players</a></div>
            <div class="endpoint">Configurações: <a href="http://localhost:3000/config" target="_blank">http://localhost:3000/config</a></div>
        </div>

        <div style="text-align: center; margin-top: 20px;">
            <button class="btn" onclick="testServer()">🧪 Testar Servidor</button>
            <button class="btn btn-danger" onclick="stopServer()">⏹️ Parar Servidor</button>
        </div>

        <div class="status">
            <h3>📝 Logs do Servidor</h3>
            <div id="logs" style="background: rgba(0,0,0,0.5); padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto;"></div>
        </div>
    </div>

    <script>
        function testServer() {
            fetch('http://localhost:3000')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('serverStatus').innerHTML = '✅ Servidor funcionando!';
                    addLog('✅ Teste de conexão bem-sucedido');
                })
                .catch(error => {
                    document.getElementById('serverStatus').innerHTML = '❌ Servidor não responde';
                    addLog('❌ Erro no teste: ' + error.message);
                });
        }

        function stopServer() {
            if (confirm('Deseja parar o servidor?')) {
                window.close();
            }
        }

        function addLog(message) {
            const logs = document.getElementById('logs');
            const timestamp = new Date().toLocaleTimeString();
            logs.innerHTML += \`[${timestamp}] ${message}\\n\`;
            logs.scrollTop = logs.scrollHeight;
        }

        // Testar servidor automaticamente
        setTimeout(testServer, 2000);
    </script>
</body>
</html>`;

    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(htmlContent));

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startServer() {
    const serverPath = path.join(__dirname, 'server.js');
    
    if (fs.existsSync(serverPath)) {
        serverProcess = spawn('node', [serverPath], {
            stdio: ['pipe', 'pipe', 'pipe']
        });

        serverProcess.stdout.on('data', (data) => {
            console.log('Servidor:', data.toString());
        });

        serverProcess.stderr.on('data', (data) => {
            console.error('Erro do servidor:', data.toString());
        });

        serverProcess.on('close', (code) => {
            console.log('Servidor encerrado com código:', code);
        });
    } else {
        console.error('Arquivo server.js não encontrado!');
    }
}

app.whenReady().then(() => {
    startServer();
    createWindow();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        if (serverProcess) {
            serverProcess.kill();
        }
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

app.on('before-quit', () => {
    if (serverProcess) {
        serverProcess.kill();
    }
});