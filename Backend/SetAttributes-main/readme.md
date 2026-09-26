# SCUM SetAttributes Editor v0.9 Beta

**Developed by Nereu Jr**

A powerful and user-friendly GUI tool to edit SCUM prisoner attributes (`Strength`, `Constitution`, `Dexterity`, `Intelligence`) directly in the `SCUM.db` database.

This tool performs surgical binary editing on the SQLite database, ensuring game integrity while allowing precise customization of player stats.

## 🚀 Key Features

- **🖥️ Modern GUI**: Brand new graphical interface built with `CustomTkinter`. No more command-line complexity.
- **✨ Visual Inspector**: Select players from a list, search by Name or SteamID, and edit attributes in a clean sidebar.
- **🌐 Remote Management (SFTP)**: Connect directly to your Linux/Docker server, download the database safely, and upload changes after editing.
- **🛡️ Smart Safety**:
  - **Lock Detection**: Warns if the database is in use (server running) to prevent corruption.
  - **Staging System**: Queue multiple changes (Pending) and review them before committing to disk.
  - **Automatic Backups**: Creates local backups every time a database is opened.
- **🌍 Multi-Language**: Fully localized in **English** and **Portuguese (PT-BR)**.

## 📥 Installation

There is no complex installation required. This application is distributed as a **Portable** package.

1. Download the latest `SCUM_Attribute_Editor_Portable.zip` from the Releases page.
2. Extract the `.zip` file to a folder.
3. Run `SCUM_Attribute_Editor.exe`.

## ⚙️ Configuration

The application uses a `config.ini` file for storing preferences and connection details.

1. Inside the folder, you will find a `config.ini.example`.
2. Rename it to `config.ini`.
3. Open it with any text editor to set up your defaults (optional):

```ini
[LOCAL]
DbPath = C:\Servers\scum\SCUM\Saved\SaveFiles\SCUM.db

[SFTP]
Host = 192.168.1.100
Port = 22
User = steam
Password = your_password
RemoteDbPath = /home/steam/SCUM/Saved/SaveFiles/SCUM.db

[GENERAL]
Language = en
# Options: en, pt
```

## ⚠️ Important Warnings

> **🔴 SERVER MUST BE OFFLINE**: Always **STOP** your SCUM server before uploading any changes via SFTP or saving to the local file. Editing the database while the server is running **will** result in file corruption and data loss.

> **🔵 Beta Software**: This is a beta version (v0.9). While extensive testing has been done, unexpected bugs may occur. Always keep your own backups.

> **🚫 Private Use Only**: This tool is intended for **Private Server Administration**. Using this on Official servers is impossible/illegal and trying to use it for cheating may result in a ban.

## 🤝 Credits

- **Developer**: Nereu Jr
- **Special Thanks**:
    - Admins **Sabugador** & **Mewtwo** from *'Oblivion[BR] - PvP/PvE - 5x Loot - 10x Skill'*
    - **Emiza** for the mediation and support.