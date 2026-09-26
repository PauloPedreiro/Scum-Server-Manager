# SCUM SetAttributes Editor v0.9 Beta - Release Notes

**Date:** 2025-12-22  
**Developer:** Nereu Jr  
**Status:** Open Beta  

---

## 🇺🇸 English Version

### 🚀 Introduction

We are excited to announce the **v0.9 Beta** release of the SCUM SetAttributes Editor! This update brings a massive overhaul to the entire application, transitioning from a command-line script to a fully-featured Graphical User Interface (GUI) with enhanced safety features and remote management capabilities.

### ✨ Key Features in v0.9

#### 🖥️ Brand New GUI
- **Modern Interface**: Built with `CustomTkinter`, offering a dark-mode, user-friendly experience.
- **Visual Inspector**: Select players from a list and edit their attributes (Strength, Constitution, Dexterity, Intelligence) with a clean sidebar inspector.
- **Search & Filter**: Easily find players by Name or Steam ID.

#### 🌐 Remote Management (SFTP)
- **Direct Server Connection**: Connect directly to your game server via SFTP.
- **Remote DB Browser**: Browse and select the correct `SCUM.db` file from the remote server.
- **Safe Editing**: The tool downloads the DB to a temporary folder, performs edits locally, and requests confirmation before uploading the changes back to the server.
- **Lock Detection**: Warns if the remote database is locked (server running) to prevent corruption.

#### 🛡️ Safety & Reliability
- **Staging System (Pending Changes)**: Changes are not applied immediately. You can make multiple edits to different players and review them in a "Pending" state before saving.
- **Automatic Backups**: A local backup is automatically created every time you load a database.
- **Read-Only Mode**: If the database is detected as "in-use" (locked), the application automatically switches to Read-Only mode to prevent accidental corruption.

#### 🌍 Localization
- **Multi-language Support**: Fully translated into **English** and **Portuguese (PT-BR)**.
- **Switch on the Fly**: Change languages instantly via the Settings menu.

#### 📦 Portable Distribution
- **No Installation Required**: The application is compiled into a single `.exe` file.
- **Zip Package**: Includes the executable and a template configuration file (`config.ini.example`).

---

### 🛠️ How to Install & Use

1. **Download**: Get the `SCUM_Attribute_Editor_Portable.zip`.
2. **Extract**: Unzip the folder to a location of your choice.
3. **Configure (Optional)**: Rename `config.ini.example` to `config.ini` to save your default paths and SFTP credentials.
4. **Run**: Double-click `SCUM_Attribute_Editor.exe`.

---

### ⚠️ Important Warnings

- **Server Shutdown Required**: ALWAYS stop your SCUM server before uploading changes via SFTP.
- **Beta Software**: This is a beta release. While we have implemented many safety checks, always ensure you have external backups of your server data.
- **VAC/Ban Risk**: This tool is for **Private Server Administration ONLY**. Using this on official servers or to gain unfair advantages is strictly prohibited and can lead to bans.

### 🙏 Credits

- **Developer**: Nereu Jr
- **Special Thanks**:
    - Admins **Sabugador** & **Mewtwo** from *'Oblivion[BR] - PvP/PvE - 5x Loot - 10x Skill'*
    - **Emiza** for the mediation and support.

<br>
<br>

---

## 🇧🇷 Versão em Português

### 🚀 Introdução

Temos o prazer de anunciar o lançamento da versão **v0.9 Beta** do SCUM SetAttributes Editor! Esta atualização traz uma reformulação completa para o aplicativo, migrando de um script de linha de comando para uma Interface Gráfica (GUI) completa, com recursos de segurança aprimorados e capacidades de gerenciamento remoto.

### ✨ Principais Novidades na v0.9

#### 🖥️ Nova Interface Gráfica (GUI)
- **Visual Moderno**: Construído com `CustomTkinter`, oferecendo um modo escuro amigável e intuitivo.
- **Inspetor Visual**: Selecione jogadores de uma lista e edite seus atributos (Força, Constituição, Destreza, Inteligência) com um inspetor lateral limpo.
- **Busca e Filtro**: Encontre jogadores facilmente por Nome ou Steam ID.

#### 🌐 Gerenciamento Remoto (SFTP)
- **Conexão Direta**: Conecte-se diretamente ao servidor do jogo via SFTP.
- **Navegador de DB Remoto**: Navegue e selecione o arquivo `SCUM.db` correto no servidor remoto.
- **Edição Segura**: A ferramenta baixa o DB para uma pasta temporária, realiza as edições localmente e solicita confirmação antes de enviar as alterações de volta para o servidor.
- **Detecção de Bloqueio**: Avisa se o banco de dados remoto estiver bloqueado (servidor rodando) para evitar corrupção.

#### 🛡️ Segurança e Confiabilidade
- **Sistema de Pendências (Staging)**: As alterações não são aplicadas imediatamente. Você pode fazer várias edições em diferentes jogadores e revisá-las em um estado de "Pendente" antes de salvar.
- **Backups Automáticos**: Um backup local é criado automaticamente toda vez que você carrega um banco de dados.
- **Modo Somente Leitura**: Se o banco de dados for detectado como "em uso" (bloqueado), o aplicativo muda automaticamente para o modo Somente Leitura para evitar corrupção acidental.

#### 🌍 Localização
- **Suporte Multi-idioma**: Totalmente traduzido para **Inglês** e **Português (PT-BR)**.
- **Troca Rápida**: Mude o idioma instantaneamente através do menu de Configurações.

#### 📦 Distribuição Portátil
- **Sem Instalação**: O aplicativo é compilado em um único arquivo `.exe`.
- **Pacote Zip**: Inclui o executável e um modelo de arquivo de configuração (`config.ini.example`).

---

### 🛠️ Como Instalar e Usar

1. **Baixar**: Obtenha o arquivo `SCUM_Attribute_Editor_Portable.zip`.
2. **Extrair**: Descompacte a pasta em um local de sua escolha.
3. **Configurar (Opcional)**: Renomeie o `config.ini.example` para `config.ini` para salvar seus caminhos padrão e credenciais SFTP.
4. **Executar**: Clique duas vezes em `SCUM_Attribute_Editor.exe`.

---

### ⚠️ Avisos Importantes

- **Parada do Servidor Necessária**: SEMPRE pare o seu servidor SCUM antes de fazer upload de alterações via SFTP.
- **Software Beta**: Esta é uma versão beta. Embora tenhamos implementado muitas verificações de segurança, sempre garanta que você tenha backups externos dos dados do seu servidor.
- **Risco de VAC/Ban**: Esta ferramenta é APENAS para **Administração de Servidores Privados**. Usá-la em servidores oficiais ou para obter vantagens injustas é estritamente proibido e pode levar a banimentos.

### 🙏 Créditos

- **Desenvolvedor**: Nereu Jr
- **Agradecimentos Especiais**:
    - Admins **Sabugador** & **Mewtwo** do servidor *'Oblivion[BR] - PvP/PvE - 5x Loot - 10x Skill'*
    - **Emiza** pela intermediação e suporte.

---

*Reporte bugs e feedback no repositório oficial.*
