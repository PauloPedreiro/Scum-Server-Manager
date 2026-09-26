# Scum Server Manager (SSM 3.0)

A complete, high-performance management ecosystem, bot, and web portal for SCUM dedicated game servers.

## Overview

Scum Server Manager (SSM) provides automated game server management, RCON integration, real-time log tracking, a modern Web Dashboard, an in-game shop, automated scheduled routines, and an interactive Discord Bot for server administration and player engagement.

The project is structured as a **Monorepo**:
- **Backend/**: Python/Flask core orchestrating RCON queue management, Discord Bot service, log parsing (chat, kills, logins), SQLite transactional state, and the REST API.
- **Frontend/**: Modern React/Vite web application providing the administrative dashboard, analytics, real-time server controls, and player shop.

## Key Features

- Safe RCON Queue (RconQueueManager) with prioritized queues and coordinate parsing
- Smart Discord Bot Integration (Live Status Embed, online player count, in-game teleport codes)
- Playtime Rewards System with disconnect grace period and UTC timestamps
- Wanted Killstreak and dynamic PvP bounty system
- Squad TK Jail automated punishment and coordinate fallback
- SCUM Server Log Cleaner and disk manager
- In-Game Shop, Virtual Economy, and Attribute Upgrade Management

## Quick Start

### 1. Backend Setup
`ash
cd Backend
python -m venv venv
# Windows: .\\venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
`",
    ",
    
`ash
cd Frontend
npm install
npm run dev
`",
    ",
    

Distributed under the MIT License. See LICENSE for more information.

---
Developed by **Paulo Pedreiro** & Community.
