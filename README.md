<div align="center">

# 🎮 Scum Server Manager (SSM 3.0)

**A high-performance open-source management ecosystem, Discord Bot, and Web Dashboard for SCUM dedicated game servers.**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![React / Vite](https://img.shields.io/badge/Frontend-React%20%7C%20Vite%20%7C%20Tailwind-61DAFB?logo=react&logoColor=black)](Frontend/)
[![Discord Community](https://img.shields.io/badge/Discord-Join%20Community-5865F2?logo=discord&logoColor=white)](https://discord.gg/EHwQTKWAtv)
[![Contributing](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Overview](#-overview) • [Screenshots](#-screenshots--showcase) • [Key Features](#-key-features) • [Quick Start](#-quick-start) • [Contributing](#-contributing) • [License](#-license)

</div>

---

## 📖 Overview

**Scum Server Manager (SSM)** provides automated game server management, RCON integration, real-time log tracking, a modern Web Dashboard, an in-game shop, automated scheduled routines, and an interactive Discord Bot for server administration and player engagement.

The project is structured as a **Monorepo**:
* **`Backend/`**: Python/Flask core orchestrating RCON queue management, Discord Bot service, log parsing (chat, kills, logins), SQLite transactional state, and the REST API.
* **`Frontend/`**: Modern React/Vite web application providing the administrative dashboard, analytics, real-time server controls, and player shop.

---

## 📸 Screenshots & Showcase

### 🖥️ Modern Web Dashboard & Overview
> Comprehensive live server telemetry, active player counts, server health, weather, restart countdowns, and historical statistics.

<div align="center">
  <img src="Backend/docs/images/02_web_overview.jpeg" alt="Web Overview Dashboard" width="85%" />
</div>

<p align="center">
  <img src="Backend/docs/images/01_web_login.jpeg" alt="Web Login" width="42%" />
  &nbsp;
  <img src="Backend/docs/images/18_web_background_customizer.jpeg" alt="Background Selector" width="42%" />
</p>

---

### 🗺️ Interactive Live SCUM Map
> Real-time Canvas map calibrated to the SCUM island grid showing chest coordinates, squad flags, and in-vehicle inventory tracking.

<div align="center">
  <img src="Backend/docs/images/03_web_map.jpeg" alt="Interactive SCUM Map" width="85%" />
</div>

---

### 👥 Player & Squad Management
> Deep player inspection including granular permission toggles, vehicle tracking, survival & combat statistics, banking, and real-time online analytics.

<p align="center">
  <img src="Backend/docs/images/05_web_players.jpeg" alt="Player Permissions" width="48%" />
  &nbsp;
  <img src="Backend/docs/images/06_web_vehicles.jpeg" alt="Vehicle Tracking" width="48%" />
</p>

<p align="center">
  <img src="Backend/docs/images/07_web_player_stats.jpeg" alt="Survival Combat Stats" width="48%" />
  &nbsp;
  <img src="Backend/docs/images/08_web_player_analytics.jpeg" alt="Online Analytics Chart" width="48%" />
</p>

---

### 🛍️ In-Game Shop, Attributes & Economy
> Fully-featured catalog editor, virtual economy, customizable attribute pricing with automated expiration rollback, and PvP Wanted bounty hunter system.

<p align="center">
  <img src="Backend/docs/images/10_web_shop_catalog.jpeg" alt="Shop Catalog Management" width="48%" />
  &nbsp;
  <img src="Backend/docs/images/11_web_attributes.jpeg" alt="Attributes Shop" width="48%" />
</p>

<p align="center">
  <img src="Backend/docs/images/12_web_wanted_bounty.jpeg" alt="Wanted Bounty System" width="48%" />
  &nbsp;
  <img src="Backend/docs/images/13_web_shop_notifications.jpeg" alt="Shop In-game Notifications" width="48%" />
</p>

---

### ⚙️ Server Control, Anti-Abuse & Automation
> Automated server maintenance, scheduled restarts, outside-flag mine protection, Squad TK Jail punishment, and dynamic in-game Kill Feed with trash-talk.

<p align="center">
  <img src="Backend/docs/images/04_web_server_controls.jpeg" alt="Server Controls & Scheduler" width="48%" />
  &nbsp;
  <img src="Backend/docs/images/17_web_rcon_routines.jpeg" alt="RCON Routine Scheduler" width="48%" />
</p>

<p align="center">
  <img src="Backend/docs/images/14_web_mine_punishment.jpeg" alt="Mine & Trap Flag Protection" width="48%" />
  &nbsp;
  <img src="Backend/docs/images/15_web_squad_tk_jail.jpeg" alt="Squad TK Jail" width="48%" />
</p>

<div align="center">
  <img src="Backend/docs/images/16_web_kill_feed.jpeg" alt="In-Game Kill Feed Settings" width="85%" />
</div>

---

### 🪟 Desktop Management Interface (Panel SSM GUI)
> Native desktop GUI for rapid server administration, live logs streaming, RCON console tester, and maintenance resets.

<p align="center">
  <img src="Backend/docs/images/gui_settings_general.png" alt="GUI Settings" width="48%" />
  &nbsp;
  <img src="Backend/docs/images/gui_rcon_tab.png" alt="GUI RCON Tab" width="48%" />
</p>

<p align="center">
  <img src="Backend/docs/images/gui_logs_scum.png" alt="GUI SCUM Logs" width="48%" />
  &nbsp;
  <img src="Backend/docs/images/gui_logs_app.png" alt="GUI App Logs" width="48%" />
</p>

---

## 🌟 Key Features

* **⚡ Safe RCON Queue (`RconQueueManager`)**: Prioritized queue system preventing socket congestion and packet loss with automated coordinate parsing (`#ScheduleWorldEvent`, `#teleport`) and command injection prevention.
* **🤖 Smart Discord Bot Integration**:
  * Persistent Live Status Embed with dynamic restart countdowns.
  * Real-time online player count in bot presence and server nickname (`[X/Y] Name`).
  * In-game event teleport code generator (`/evento <code>`) eliminating interaction timeouts.
  * Automatic synchronization of dedicated announcement and log channels.
* **⏱️ Playtime Rewards System**: Resilient session tracking with configurable grace periods for temporary disconnects, unified UTC timestamps, and plaintext Discord audit logs.
* **🎯 Wanted Killstreak & Bounties**: Dynamic PvP bounty hunters system with anti-squad exploit cooldowns and persistent Discord ranking updates.
* **🔒 Squad TK Jail**: Automated punishment module with exact release coordinate fallbacks.
* **🧹 SCUM Log Cleaner**: Automatic and manual server log rotation and disk cleanup directly via desktop GUI and Discord reporting.
* **🛍️ In-Game Shop & Economy**: Integrated virtual wallet, custom attribute upgrade pricing, and automatic welcome kit delivery.

---

## 🏗️ Repository Architecture

```text
Scum-Server-Manager/
├── .gitignore
├── LICENSE                  # GNU General Public License v3.0
├── README.md                # Project documentation & showcase
├── CONTRIBUTING.md          # Contribution guidelines
├── CODE_OF_CONDUCT.md       # Contributor Covenant Code of Conduct
│
├── Backend/                 # Python 3 / Flask / RCON / Discord Bot / GUI
│   ├── app/                 # REST API blueprints & routes
│   ├── core/                # Core engines (RCON, Discord, Logs, Shop, Scheduler)
│   ├── gui/                 # Desktop management interface
│   ├── data/                # Configuration and database templates
│   ├── docs/images/         # Showcase screenshots
│   └── requirements.txt     # Python dependencies
│
└── Frontend/                # React / Vite Web Dashboard
    ├── src/                 # Application components, pages and services
    └── package.json         # Node dependencies
```

---

## 🚀 Quick Start

### Prerequisites
* **Python**: 3.10 or higher
* **Node.js**: 18.x or higher
* **SCUM Dedicated Server** with RCON enabled

---

### 1. Backend Setup

1. Open a terminal in the `Backend/` directory:
   ```bash
   cd Backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment:
   * Copy `data/config.example.json` to `data/config.json`.
   * Configure your server RCON host, port, password, and Discord Bot token.
5. Run the Backend:
   ```bash
   python main.py
   ```

---

### 2. Frontend Setup

1. Open a terminal in the `Frontend/` directory:
   ```bash
   cd Frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the local development server:
   ```bash
   npm run dev
   ```

---

## 🤝 Contributing

We love contributions! Please check our **[Contributing Guide](CONTRIBUTING.md)** and **[Code of Conduct](CODE_OF_CONDUCT.md)** before opening issues or submitting pull requests.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feat/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: add some amazing feature'`)
4. Push to the Branch (`git push origin feat/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

Distributed under the **GNU General Public License v3.0 (GPL-3.0)**. See **[LICENSE](LICENSE)** for full license details.

---

<div align="center">
Developed with ❤️ by <b>Paulo Pedreiro</b> & Community • Join our <a href="https://discord.gg/EHwQTKWAtv">Discord Community</a>
</div>
