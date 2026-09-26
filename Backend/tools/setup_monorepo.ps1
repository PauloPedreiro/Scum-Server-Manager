# ==============================================================================
# SSM 3.0 - Setup do Monorepo Open Source
# ==============================================================================

$RootPath = "C:\Dev\SSM\SSM 3.0"
Set-Location $RootPath

Write-Host "Iniciando configuracao do Monorepo..." -ForegroundColor Cyan

# 1. Gerar .gitignore na raiz
$GitIgnorePath = Join-Path $RootPath ".gitignore"
$GitIgnoreLines = @(
    "# ==========================================",
    "# SCUM Server Manager - Monorepo .gitignore",
    "# ==========================================",
    "",
    "# OS & Temp",
    ".DS_Store",
    "Thumbs.db",
    "ehthumbs.db",
    "*.bak",
    "*.backup",
    "*.tmp",
    "*.temp",
    "temp/",
    "tmp/",
    "scratch/",
    "**/.git_old/",
    "**/.git_old_root/",
    "",
    "# IDEs & Editors",
    ".vscode/",
    ".idea/",
    ".cursor/",
    ".windsurf/",
    "*.swp",
    "*.swo",
    "*~",
    "*.suo",
    "*.user",
    "*.workspace",
    "",
    "# BACKEND",
    "**/__pycache__/",
    "*.py[cod]",
    "*$py.class",
    "*.so",
    ".Python",
    "build/",
    "develop-eggs/",
    "downloads/",
    "eggs/",
    ".eggs/",
    "lib/",
    "lib64/",
    "parts/",
    "sdist/",
    "var/",
    "wheels/",
    "*.egg-info/",
    ".installed.cfg",
    "*.egg",
    "MANIFEST",
    "",
    "# Python Virtual Environments",
    "**/.venv/",
    "**/venv/",
    "**/env/",
    "**/ENV/",
    "**/env.bak/",
    "**/venv.bak/",
    "",
    "# Build Output",
    "**/dist/",
    "*.spec.bak",
    "",
    "# Sensitive Configuration & Secrets (NEVER COMMIT)",
    "Backend/config.json",
    "Backend/webhooks.json",
    "Backend/data/config.json",
    "Backend/data/webhooks.json",
    "Backend/data/identity.json",
    "Backend/data/license.json",
    "Backend/data/config.backup.*",
    "Backend/data/server_settings_presets/default.ini",
    "**/server_settings_presets/default.ini",
    "**/config.json",
    "**/webhooks.json",
    "",
    "# SSM Database & Runtime State (DO NOT COMMIT)",
    "*.db",
    "*.db-*",
    "**/*.db",
    "**/*.db-*",
    "!Backend/data/templates/*.db",
    "!Backend/Implementar/scum_base_template.db",
    "Backend/data/backups/",
    "Backend/data/event_teleport_codes.json",
    "Backend/data/playtime_sessions.json",
    "Backend/data/chat_processed.json",
    "Backend/data/chat_state.json",
    "Backend/data/processed_commands.json",
    "Backend/data/mines_alerts_state.json",
    "Backend/data/cargo_drop_state.json",
    "Backend/data/fishing_ranking_last_run.json",
    "Backend/data/scum_installer_status.json",
    "",
    "# Whitelist safe configuration examples",
    "!Backend/data/config.example.json",
    "!Backend/data/webhooks.example.json",
    "",
    "# Logs",
    "*.log",
    "Backend/data/logs/*",
    "!Backend/data/logs/.gitkeep",
    "",
    "# Large Binary Mod Pak Files",
    "*.pak",
    "*.pak.disabled",
    "Backend/data/mods/paks/*",
    "!Backend/data/mods/paks/.gitkeep",
    "",
    "# FRONTEND",
    "**/node_modules/",
    "Frontend/dist/",
    "Frontend/.env",
    "Frontend/.env.local",
    "Frontend/.env.development.local",
    "Frontend/.env.test.local",
    "Frontend/.env.production.local",
    "npm-debug.log*",
    "yarn-debug.log*",
    "yarn-error.log*",
    "pnpm-debug.log*"
)
$GitIgnoreLines | Out-File -FilePath $GitIgnorePath -Encoding utf8
Write-Host "[OK] .gitignore raiz gerado." -ForegroundColor Green

# 2. Gerar LICENSE (MIT)
$LicensePath = Join-Path $RootPath "LICENSE"
$LicenseLines = @(
    "MIT License",
    "",
    "Copyright (c) 2026 Paulo Pedreiro",
    "",
    "Permission is hereby granted, free of charge, to any person obtaining a copy",
    "of this software and associated documentation files (the ""Software""), to deal",
    "in the Software without restriction, including without limitation the rights",
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell",
    "copies of the Software, and to permit persons to whom the Software is",
    "furnished to do so, subject to the following conditions:",
    "",
    "The above copyright notice and this permission notice shall be included in all",
    "copies or substantial portions of the Software.",
    "",
    "THE SOFTWARE IS PROVIDED ""AS IS"", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR",
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,",
    "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE",
    "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER",
    "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,",
    "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE",
    "SOFTWARE."
)
$LicenseLines | Out-File -FilePath $LicensePath -Encoding utf8
Write-Host "[OK] LICENSE gerada." -ForegroundColor Green

# 3. Gerar README.md na raiz
$ReadmePath = Join-Path $RootPath "README.md"
$ReadmeLines = @(
    "# Scum Server Manager (SSM 3.0)",
    "",
    "A complete, high-performance management ecosystem, bot, and web portal for SCUM dedicated game servers.",
    "",
    "## Overview",
    "",
    "Scum Server Manager (SSM) provides automated game server management, RCON integration, real-time log tracking, a modern Web Dashboard, an in-game shop, automated scheduled routines, and an interactive Discord Bot for server administration and player engagement.",
    "",
    "The project is structured as a **Monorepo**:",
    "- **Backend/**: Python/Flask core orchestrating RCON queue management, Discord Bot service, log parsing (chat, kills, logins), SQLite transactional state, and the REST API.",
    "- **Frontend/**: Modern React/Vite web application providing the administrative dashboard, analytics, real-time server controls, and player shop.",
    "",
    "## Key Features",
    "",
    "- Safe RCON Queue (RconQueueManager) with prioritized queues and coordinate parsing",
    "- Smart Discord Bot Integration (Live Status Embed, online player count, in-game teleport codes)",
    "- Playtime Rewards System with disconnect grace period and UTC timestamps",
    "- Wanted Killstreak and dynamic PvP bounty system",
    "- Squad TK Jail automated punishment and coordinate fallback",
    "- SCUM Server Log Cleaner and disk manager",
    "- In-Game Shop, Virtual Economy, and Attribute Upgrade Management",
    "",
    "## Quick Start",
    "",
    "### 1. Backend Setup",
    "```bash",
    "cd Backend",
    "python -m venv venv",
    "# Windows: .\\venv\\Scripts\\activate",
    "pip install -r requirements.txt",
    "python main.py",
    "```",
    "",
    "### 2. Frontend Setup",
    "```bash",
    "cd Frontend",
    "npm install",
    "npm run dev",
    "```",
    "",
    "## License",
    "",
    "Distributed under the MIT License. See LICENSE for more information.",
    "",
    "---",
    "Developed by **Paulo Pedreiro** & Community."
)
$ReadmeLines | Out-File -FilePath $ReadmePath -Encoding utf8
Write-Host "[OK] README.md raiz gerado." -ForegroundColor Green

# 4. Desativar .git interno do Backend (para nao virar submodulo)
$BackendGit = Join-Path $RootPath "Backend\.git"
$BackendGitOld = Join-Path $RootPath "Backend\.git_old"
if (Test-Path $BackendGit) {
    if (Test-Path $BackendGitOld) {
        Remove-Item -Recurse -Force $BackendGitOld
    }
    Move-Item -Path $BackendGit -Destination $BackendGitOld -Force
    Write-Host "[OK] Backend/.git renomeado para Backend/.git_old (backup seguro)." -ForegroundColor Green
}

# 5. Desativar .git interno do Frontend (se existir)
$FrontendGit = Join-Path $RootPath "Frontend\.git"
$FrontendGitOld = Join-Path $RootPath "Frontend\.git_old"
if (Test-Path $FrontendGit) {
    if (Test-Path $FrontendGitOld) {
        Remove-Item -Recurse -Force $FrontendGitOld
    }
    Move-Item -Path $FrontendGit -Destination $FrontendGitOld -Force
    Write-Host "[OK] Frontend/.git renomeado para Frontend/.git_old (backup seguro)." -ForegroundColor Green
}

# 6. Garantir novo Git Monorepo limpo na raiz (backup de .git antigo se houver)
Set-Location $RootPath
$RootGit = Join-Path $RootPath ".git"
$RootGitOld = Join-Path $RootPath ".git_old_root"
if (Test-Path $RootGit) {
    if (Test-Path $RootGitOld) {
        Remove-Item -Recurse -Force $RootGitOld
    }
    Move-Item -Path $RootGit -Destination $RootGitOld -Force
    Write-Host "[OK] .git antigo da raiz movido para .git_old_root." -ForegroundColor Yellow
}

git init -b main
git remote add origin "https://github.com/PauloPedreiro/Scum-Server-Manager.git"
Write-Host "[OK] Novo Git limpo inicializado na raiz e remoto configurado." -ForegroundColor Green
