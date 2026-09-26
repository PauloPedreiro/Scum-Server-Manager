import tkinter
import tkinter.ttk as ttk
import customtkinter as ctk
import sqlite3
import configparser
import os
import threading
from datetime import datetime
from tkinter import filedialog, messagebox

# Importa módulos
from modules.database import fetch_prisoners, get_prisoner_attributes, update_prisoner_attributes
from modules.utils import create_local_backup, check_db_lock
from modules.sftp_handler import run_sftp_mode, PARAMIKO_AVAILABLE

try:
    import paramiko
except ImportError:
    pass

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# =============================================================================
# TRANSLATION DICTIONARY
# =============================================================================
TRANSLATIONS = {
    "app_title": {"en": "SetAttributes Editor v0.9 beta", "pt": "SetAttributes Editor v0.9 beta"},
    "nav_database": {"en": " DATABASE", "pt": " BANCO DADOS"},
    "nav_settings": {"en": " SETTINGS", "pt": " CONFIGURAR"},
    "nav_credits": {"en": " CREDITS", "pt": " CRÉDITOS"},
    "nav_terms": {"en": " TERMS OF USE", "pt": " TERMOS DE USO"},
    "source_label": {"en": "SOURCE:", "pt": "ORIGEM:"},
    "btn_local": {"en": "LOCAL DB", "pt": "DB LOCAL"},
    "btn_remote": {"en": "REMOTE (SFTP)", "pt": "REMOTO (SFTP)"},
    "status_waiting": {"en": "WAITING CONNECTION", "pt": "AGUARDANDO CONEXÃO"},
    "search_placeholder": {"en": "Search Player (Name/SteamID)...", "pt": "Buscar Jogador (Nome/SteamID)..."},
    "items_found": {"en": "Items found", "pt": "Itens encontrados"},
    "col_name": {"en": "PLAYER NAME", "pt": "NOME JOGADOR"},
    "col_steam": {"en": "STEAM ID", "pt": "STEAM ID"},
    "inspector_empty": {"en": "SELECT A PLAYER\nTO EDIT", "pt": "SELECIONE UM JOGADOR\nPARA EDITAR"},
    "inspector_details": {"en": "PLAYER DETAILS", "pt": "DETALHES DO JOGADOR"},
    "inspector_attrs": {"en": "ATTRIBUTES", "pt": "ATRIBUTOS"},
    "attr_str": {"en": "Strength (STR)", "pt": "Força (STR)"},
    "attr_con": {"en": "Constitution (CON)", "pt": "Constituição (CON)"},
    "attr_dex": {"en": "Dexterity (DEX)", "pt": "Destreza (DEX)"},
    "attr_int": {"en": "Intelligence (INT)", "pt": "Inteligência (INT)"},
    "pending_changes": {"en": "PENDING CHANGES:", "pt": "PENDÊNCIAS:"},
    "btn_revert": {"en": "Revert All", "pt": "Reverter"},
    "btn_save_disk": {"en": "SAVE TO DISK", "pt": "SALVAR (DISCO)"},
    "btn_upload": {"en": "UPLOAD (SFTP)", "pt": "ENVIAR (SFTP)"},
    "msg_confirm": {"en": "Confirm", "pt": "Confirmar"},
    "msg_discard": {"en": "Discard ALL pending changes?", "pt": "Descartar TODAS as alterações?"},
    "msg_success": {"en": "Success", "pt": "Sucesso"},
    "msg_saved": {"en": "Saved {count} players to {dest}.", "pt": "Salvo {count} jogadores em {dest}."},
    "msg_limit": {"en": "{key} must be between 1.0 and {max}", "pt": "{key} deve ser entre 1.0 e {max}"},
    "msg_upload_ask": {"en": "Send changes to server?\nServer restart required.", "pt": "Enviar para o servidor?\nReinício necessário."},
    "msg_upload_done": {"en": "Upload Complete!", "pt": "Envio Concluído!"},
    "settings_title": {"en": "Application Settings", "pt": "Configurações"},
    "settings_sftp": {"en": "SFTP Connection Details", "pt": "Detalhes de Conexão SFTP"},
    "btn_save_cfg": {"en": "Save Configuration", "pt": "Salvar Configuração"},
    "lbl_lang": {"en": "Language / Idioma", "pt": "Idioma / Language"},
    "status_connecting": {"en": "Connecting...", "pt": "Conectando..."},
    "status_connected": {"en": "Connected", "pt": "Conectado"},
    "status_downloading": {"en": "Downloading...", "pt": "Baixando..."},
    "status_uploading": {"en": "Uploading...", "pt": "Enviando..."},
    "error_paramiko": {"en": "Paramiko missing", "pt": "Paramiko ausente"},
    "locked_alert": {"en": "Database is in use. Read Only Mode.", "pt": "Banco de dados em uso. Modo Leitura."},
    "remote_locked": {"en": "Remote DB locked (.wal/.shm found). Read Only.", "pt": "DB Remoto bloqueado (.wal/.shm). Modo Leitura."},
    "terms_title": {"en": "Terms & Disclaimer", "pt": "Termos e Aviso Legal"},
    "credits_dev": {"en": "Developed by:", "pt": "Desenvolvido por:"},
    "credits_thank_title": {"en": "Special Thanks", "pt": "Agradecimentos Especiais"},
    "credits_thank_msg": {
        "en": "To Admins Sabugador & Mewtwo from server\n'Oblivion[BR] - PvP/PvE - 5x Loot - 10x Skill'\nAnd to Emiza for the mediation.",
        "pt": "Aos Admins Sabugador e Mewtwo do servidor\n'Oblivion[BR] - PvP/PvE - 5x Loot - 10x Skill'\nE ao Emiza pela intermediação."
    },
    "c_admins": {"en": "To Admins", "pt": "Aos Admins"},
    "c_and": {"en": "&", "pt": "e"},
    "c_server": {"en": "from server", "pt": "do servidor"},
    "c_emiza": {"en": "And to", "pt": "E ao"},
    "c_mediation": {"en": "for the mediation", "pt": "pela intermediação"},
    "terms_text": {
        "en": ("SetAttributes Editor – Version 0.9 Beta\nTerms and Disclaimer\n\n"
               "1. Tool Nature and Open Source\n"
               "SetAttributes Editor is an unofficial and Open Source utility developed for administering private SCUM servers.\n"
               "The source code is publicly available for transparency and auditing at: https://github.com/nereuvjr-br/SetAttributes\n"
               "This software is not affiliated with, endorsed, or approved by Gamepires or Jagex.\n\n"
               "2. Beta Version Warning\n"
               "This is version 0.9 Beta. The software is still in active development and may contain bugs, instability, or incomplete features. "
               "By using this version, you accept the risk of encountering unexpected behavior and are strongly encouraged to report issues to the official repository.\n\n"
               "3. Game EULA Compliance\n"
               "By using SetAttributes Editor, you acknowledge that:\n"
               "- Direct modification of game files as 'SCUM.db' may violate Gamepires' Terms of Service (ToS) and EULA.\n"
               "- This tool is intended exclusively for administrative purposes on private servers.\n"
               "- Using this tool to gain unfair advantages (cheating) or on official servers is sole responsibility of the user and may result in a permanent ban of your Steam account.\n\n"
               "4. Disclaimer of Liability\n"
               "The software is provided 'as-is'. The developer is NOT responsible for:\n"
               "- Database corruption or loss of player progress.\n"
               "- Server technical instability after uploading modifications.\n"
               "- Any sanctions applied by the game developer resulting from the use of this tool.\n\n"
               "5. Security Protocols (Mandatory)\n"
               "To ensure the integrity of your data, the system requires:\n"
               "- Automatic Backup: A local backup copy is generated when opening the database. Keep these backups until you confirm that the server has started correctly.\n"
               "- Offline Server: The server MUST be completely stopped before any Upload. Sending changes while the server is running will result in file corruption.\n"
               "- Lock Verification: Although the system attempts to detect if the database is in use, the ultimate responsibility for ensuring the game process is not accessing the file lies with the administrator.\n\n"
               "By proceeding and using SetAttributes Editor v0.9 Beta, you confirm that you have read, understood, and agreed to all the terms described above."), 

        "pt": ("SetAttributes Editor – Versão 0.9 Beta\nTermos e Aviso Legal\n\n"
               "1. Natureza da Ferramenta e Código Aberto\n"
               "O SetAttributes Editor é um utilitário não oficial e de código aberto (Open Source) desenvolvido para a administração de servidores privados de SCUM.\n"
               "O código-fonte está disponível publicamente para transparência e auditoria em: https://github.com/nereuvjr-br/SetAttributes\n"
               "Este software não é afiliado, endossado ou aprovado pela Gamepires ou Jagex.\n\n"
               "2. Aviso de Versão Beta\n"
               "Esta é uma versão 0.9 Beta. Isso significa que o software ainda está em desenvolvimento ativo e pode conter bugs, instabilidades ou funcionalidades incompletas. "
               "Ao utilizar esta versão, você aceita o risco de encontrar comportamentos inesperados e é fortemente encorajado a reportar problemas no repositório oficial.\n\n"
               "3. Conformidade com a EULA do Jogo\n"
               "Ao utilizar o SetAttributes Editor, você declara estar ciente de que:\n"
               "- A modificação direta de arquivos do jogo (como o SCUM.db) pode violar os Termos de Serviço (ToS) e a EULA da Gamepires.\n"
               "- Esta ferramenta destina-se exclusivamente a fins administrativos em servidores privados.\n"
               "- O uso desta ferramenta para obter vantagens injustas (cheating) ou em servidores oficiais é de total responsabilidade do usuário e pode resultar em banimento permanente da sua conta Steam.\n\n"
               "4. Isenção de Responsabilidade\n"
               "O software é fornecido 'no estado em que se encontra' (As-Is). O desenvolvedor NÃO se responsabiliza por:\n"
               "- Corrupção de bancos de dados ou perda de progresso de jogadores.\n"
               "- Instabilidade técnica no servidor após o upload de modificações.\n"
               "- Quaisquer sanções aplicadas pela desenvolvedora do jogo decorrentes do uso desta ferramenta.\n\n"
               "5. Protocolos de Segurança (Obrigatórios)\n"
               "Para garantir a integridade dos seus dados, o sistema exige:\n"
               "- Backup Automático: Uma cópia de segurança local é gerada ao abrir o banco. Mantenha esses backups até confirmar que o servidor iniciou corretamente.\n"
               "- Servidor Offline: O servidor DEVE estar completamente desligado (Stop) antes de qualquer Upload. Enviar alterações com o servidor rodando resultará em corrupção de arquivos.\n"
               "- Verificação de Lock: Embora o sistema tente detectar se o banco está em uso, a responsabilidade final de garantir que o processo do jogo não está acessando o arquivo é do administrador.\n\n"
               "Ao prosseguir e utilizar o SetAttributes Editor v0.9 Beta, você confirma que leu, compreendeu e concorda com todos os termos acima descritos.")
    }
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Config Inicial
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        # Load Language
        self.lang = self.config.get('GENERAL', 'Language', fallback='en')
        if self.lang not in ['en', 'pt']: self.lang = 'en'

        self.title(self.tr("app_title"))
        self.geometry("1200x800")

        # --- VARIÁVEIS DE ESTADO ---
        self.db_path = None
        self.conn = None
        self.current_cursor = None
        self.prisoners_list = [] 
        self.selected_pid = None
        self.is_sftp = False
        self.temp_folder = os.path.join(os.getcwd(), "Temp")
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        self.sftp_temp_path = None
        self.is_read_only = False
        self.is_remote_locked = False
        
        # --- LAYOUT PRINCIPAL (Grid 1x2) ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Container References
        self.sidebar = None
        self.frame_editor = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_settings = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_credits = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_terms = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        # Build UI
        self.rebuild_ui()
        
        # Check Terms of Agreement
        self.after(100, self.check_terms_acceptance)
        
    def check_terms_acceptance(self):
        accepted = self.config.getboolean('GENERAL', 'TermsAccepted', fallback=False)
        if not accepted:
            self.show_terms_modal()

    def show_terms_modal(self):
        # Block interaction with main window
        self.attributes('-disabled', True)
        
        top = ctk.CTkToplevel(self)
        top.title("Terms of Use / Termos de Uso")
        top.geometry("600x700")
        top.resizable(False, False)
        top.attributes('-topmost', True)
        
        # Protocol to close app if closed without accepting
        def on_close():
            self.destroy()
        top.protocol("WM_DELETE_WINDOW", on_close)

        # Content
        f_content = ctk.CTkFrame(top, fg_color="transparent")
        f_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.populate_terms_content(f_content)

        # Buttons
        f_btns = ctk.CTkFrame(top, height=80, fg_color="#181818")
        f_btns.pack(fill="x", side="bottom")
        
        btn_exit = ctk.CTkButton(f_btns, text="Exit / Sair", fg_color="#C0392B", width=120, command=on_close)
        btn_exit.pack(side="left", padx=20, pady=20)
        
        def on_accept():
            if not self.config.has_section('GENERAL'):
                self.config.add_section('GENERAL')
            self.config.set('GENERAL', 'TermsAccepted', 'true')
            try:
                with open('config.ini', 'w') as f: self.config.write(f)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save config.ini:\n{e}")
                return
            self.attributes('-disabled', False)
            top.destroy()
            
        btn_accept = ctk.CTkButton(f_btns, text="I Agree / Concordo", fg_color="#27AE60", width=120, command=on_accept)
        btn_accept.pack(side="right", padx=20, pady=20)
        
        # Force focus
        top.focus_force()
        top.grab_set()

    def populate_terms_content(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        full_text = self.tr("terms_text")
        lines = full_text.split('\n')
        
        font_title = ctk.CTkFont(size=18, weight="bold")
        font_h2 = ctk.CTkFont(size=14, weight="bold")
        font_body = ctk.CTkFont(size=12)
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if "SetAttributes Editor" in line and "Version" in line: # Main Title
                ctk.CTkLabel(scroll, text=line, font=font_title, text_color="#3498DB", wraplength=520).pack(pady=(0, 20), anchor="w")
            elif "Termos e Aviso Legal" in line or "Terms and Disclaimer" in line: # Subtitle
                ctk.CTkLabel(scroll, text=line, font=font_h2, text_color="gray", wraplength=520).pack(pady=(0, 20), anchor="w")
            elif line[0].isdigit() and "." in line[:3]: # Numbered sections like "1. ..."
                ctk.CTkLabel(scroll, text=line, font=font_h2, text_color="#E67E22", wraplength=520, justify="left").pack(pady=(15, 5), anchor="w")
            elif line.startswith("-"): # Bullet points
                 ctk.CTkLabel(scroll, text=line, font=font_body, text_color="#BDC3C7", wraplength=500, justify="left").pack(pady=(2, 2), padx=(20, 0), anchor="w")
            else: # Normal text
                ctk.CTkLabel(scroll, text=line, font=font_body, text_color="silver", wraplength=520, justify="left").pack(pady=(2, 2), anchor="w")

    def tr(self, key, **kwargs):
        """ Translate helper """
        dic = TRANSLATIONS.get(key, {})
        txt = dic.get(self.lang, key) # fallback to key if missing
        if kwargs:
            try: txt = txt.format(**kwargs)
            except: pass
        return txt

    def rebuild_ui(self):
        # Limpa Sidebar anterior
        if self.sidebar: self.sidebar.destroy()
        
        # Limpa Frames
        for w in self.frame_editor.winfo_children(): w.destroy()
        for w in self.frame_settings.winfo_children(): w.destroy()
        for w in self.frame_credits.winfo_children(): w.destroy()
        for w in self.frame_terms.winfo_children(): w.destroy()

        self.setup_sidebar()
        self.setup_editor_view()
        self.setup_settings_view()
        self.setup_credits_view()
        self.setup_terms_view()
        
        self.show_view("editor")
        self.title(self.tr("app_title"))

    def set_language(self, lang_code):
        self.lang = lang_code
        # Salva na config
        if not self.config.has_section('GENERAL'): self.config.add_section('GENERAL')
        self.config.set('GENERAL', 'Language', lang_code)
        with open('config.ini', 'w') as f: self.config.write(f)
        
        # Rebuild
        self.rebuild_ui()

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        # Logo / Title
        title_lbl = ctk.CTkLabel(self.sidebar, text="SetAttributes\nEDITOR", font=ctk.CTkFont(size=24, weight="bold"))
        title_lbl.grid(row=0, column=0, padx=20, pady=(30, 20))

        # Nav Buttons
        self.btn_nav_editor = ctk.CTkButton(self.sidebar, text=self.tr("nav_database"), command=lambda: self.show_view("editor"),
                                            fg_color="transparent", border_spacing=10, font=ctk.CTkFont(size=14, weight="bold"),
                                            anchor="w")
        self.btn_nav_editor.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.btn_nav_settings = ctk.CTkButton(self.sidebar, text=self.tr("nav_settings"), command=lambda: self.show_view("settings"),
                                              fg_color="transparent", border_spacing=10, font=ctk.CTkFont(size=14, weight="bold"),
                                              anchor="w")
        self.btn_nav_settings.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.btn_nav_credits = ctk.CTkButton(self.sidebar, text=self.tr("nav_credits"), command=lambda: self.show_view("credits"),
                                              fg_color="transparent", border_spacing=10, font=ctk.CTkFont(size=14, weight="bold"),
                                              anchor="w")
        self.btn_nav_credits.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.btn_nav_terms = ctk.CTkButton(self.sidebar, text=self.tr("nav_terms"), command=lambda: self.show_view("terms"),
                                              fg_color="transparent", border_spacing=10, font=ctk.CTkFont(size=14, weight="bold"),
                                              anchor="w")
        self.btn_nav_terms.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        # Footer
        ctk.CTkLabel(self.sidebar, text="v0.9 beta | Nereu Jr", text_color="gray50").grid(row=7, column=0, pady=20)

    def show_view(self, name):
        self.frame_editor.grid_forget()
        self.frame_settings.grid_forget()
        self.frame_credits.grid_forget()
        self.frame_terms.grid_forget()
        
        # Highlight Button
        color_active = ("gray75", "gray25")
        self.btn_nav_editor.configure(fg_color=color_active if name == "editor" else "transparent")
        self.btn_nav_settings.configure(fg_color=color_active if name == "settings" else "transparent")
        self.btn_nav_credits.configure(fg_color=color_active if name == "credits" else "transparent")
        self.btn_nav_terms.configure(fg_color=color_active if name == "terms" else "transparent")

        if name == "editor":
            self.frame_editor.grid(row=0, column=1, sticky="nsew")
        elif name == "settings":
            self.frame_settings.grid(row=0, column=1, sticky="nsew")
        elif name == "credits":
            self.frame_credits.grid(row=0, column=1, sticky="nsew")
        elif name == "terms":
            self.frame_terms.grid(row=0, column=1, sticky="nsew")

    # =========================================================================
    # VIEW: EDITOR (DASHBOARD)
    # =========================================================================
    def setup_editor_view(self):
        self.frame_editor.grid_rowconfigure(2, weight=0) # Log fixed height
        self.frame_editor.grid_rowconfigure(1, weight=1) # Main content flexible
        self.frame_editor.grid_columnconfigure(0, weight=1)

        # --- HEADER ---
        header = ctk.CTkFrame(self.frame_editor, height=60, fg_color="#1F1F1F", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.pack_propagate(False)

        # Source Controls
        f_src = ctk.CTkFrame(header, fg_color="transparent")
        f_src.pack(side="left", padx=20, pady=10)
        
        ctk.CTkLabel(f_src, text=self.tr("source_label"), font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").pack(side="left", padx=(0,10))
        
        self.btn_src_local = ctk.CTkButton(f_src, text=self.tr("btn_local"), width=100, border_width=1, fg_color="transparent", 
                                           command=self.setup_local_mode)
        self.btn_src_local.pack(side="left", padx=5)
        
        self.btn_src_sftp = ctk.CTkButton(f_src, text=self.tr("btn_remote"), width=120, border_width=1, fg_color="transparent", 
                                          command=self.start_sftp_flow)
        self.btn_src_sftp.pack(side="left", padx=5)

        # Global Status
        self.lbl_status_main = ctk.CTkLabel(header, text=self.tr("status_waiting"), font=ctk.CTkFont(size=14, weight="bold"), text_color="gray")
        self.lbl_status_main.pack(side="right", padx=20)
        
        self.lbl_sub_status = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=12), text_color="#3498DB")
        self.lbl_sub_status.pack(side="right", padx=10)


        # --- MAIN CONTENT ---
        split_container = ctk.CTkFrame(self.frame_editor, fg_color="transparent")
        split_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(20, 10))
        split_container.grid_columnconfigure(0, weight=3) # Lista
        split_container.grid_columnconfigure(1, weight=2) # Inspector
        split_container.grid_rowconfigure(0, weight=1)

        # >>> LISTA
        panel_list = ctk.CTkFrame(split_container, fg_color="#2B2B2B")
        panel_list.grid(row=0, column=0, sticky="nsew", padx=(0,10))
        
        # Toolbar Busca
        f_tool = ctk.CTkFrame(panel_list, height=50, fg_color="transparent")
        f_tool.pack(fill="x", padx=10, pady=5)
        
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filter_player_list)
        entry_search = ctk.CTkEntry(f_tool, placeholder_text=self.tr("search_placeholder"), textvariable=self.search_var, width=300)
        entry_search.pack(side="left", pady=5)
        
        self.lbl_count = ctk.CTkLabel(f_tool, text=f"0 {self.tr('items_found')}", text_color="gray")
        self.lbl_count.pack(side="right", padx=10)

        # Treeview Wrapper
        f_tree = ctk.CTkFrame(panel_list, fg_color="transparent")
        f_tree.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.create_treeview(f_tree)

        # >>> INSPECTOR
        self.panel_inspector = ctk.CTkFrame(split_container, fg_color="#242424", border_width=1, border_color="#3A3A3A")
        self.panel_inspector.grid(row=0, column=1, sticky="nsew")
        self.panel_inspector.pack_propagate(False)
        
        self.setup_inspector_ui()
        self.init_staging_db()

        # --- CONSOLE LOG ---
        log_frame = ctk.CTkFrame(self.frame_editor, height=100, fg_color="transparent")
        log_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.log_box = ctk.CTkTextbox(log_frame, height=100, font=ctk.CTkFont(size=12, family="Consolas"))
        self.log_box.pack(fill="both", expand=True)

    def log(self, t):
        print(f"[LOG] {t}")
        if hasattr(self, 'log_box'):
            self.log_box.insert("end", f"{t}\n")
            self.log_box.see("end")

    def setup_inspector_ui(self):
        for w in self.panel_inspector.winfo_children(): w.destroy()

        if not self.selected_pid:
            ctk.CTkLabel(self.panel_inspector, text=self.tr("inspector_empty"), 
                         font=ctk.CTkFont(size=16, weight="bold"), text_color="gray40").place(relx=0.5, rely=0.5, anchor="center")
            return

        p = next((x for x in self.all_prisoners_data if x['id'] == self.selected_pid), None)
        if not p: return
        
        scroll = ctk.CTkScrollableFrame(self.panel_inspector, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=15)

        # Header
        ctk.CTkLabel(scroll, text=self.tr("inspector_details"), font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").pack(anchor="w")
        ctk.CTkLabel(scroll, text=p['name'], font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(scroll, text=f"ID: {p['id']} | Steam: {p['steam_id']}", font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", pady=(0, 20))
        
        ctk.CTkFrame(scroll, height=2, fg_color="gray30").pack(fill="x", pady=(0, 20)) 

        # Atributos
        ctk.CTkLabel(scroll, text=self.tr("inspector_attrs"), font=ctk.CTkFont(size=14, weight="bold"), text_color="#3498DB").pack(anchor="w", pady=(0, 15))

        staged = self.get_staged_changes().get(self.selected_pid, {})
        self.inspector_entries = {}
        
        def add_field(label, attr_key, max_val):
            if attr_key in staged: val = staged[attr_key]
            else: 
                raw = get_prisoner_attributes(self.current_cursor, self.selected_pid)
                val = raw.get(attr_key, 0.0) if raw else 0.0

            f_row = ctk.CTkFrame(scroll, fg_color="transparent")
            f_row.pack(fill="x", pady=8)
            ctk.CTkLabel(f_row, text=label, width=150, anchor="w", font=ctk.CTkFont(size=13)).pack(side="left")
            
            ent = ctk.CTkEntry(f_row, width=80, justify="center")
            ent.pack(side="right")
            ent.insert(0, f"{val:.1f}")
            
            if attr_key in staged:
                ent.configure(border_color="#F39C12", text_color="#F39C12")
                ctk.CTkLabel(f_row, text="*", text_color="#F39C12").pack(side="right", padx=5)

            ent.bind("<Return>", lambda e: self.do_stage_change(attr_key, ent, max_val))
            ent.bind("<FocusOut>", lambda e: self.do_stage_change(attr_key, ent, max_val))
            self.inspector_entries[attr_key] = ent

        add_field(self.tr("attr_str"), "strength", 8.0)
        add_field(self.tr("attr_con"), "constitution", 5.0)
        add_field(self.tr("attr_dex"), "dexterity", 5.0)
        add_field(self.tr("attr_int"), "intelligence", 5.0)
        
        # Footer
        footer = ctk.CTkFrame(self.panel_inspector, height=100, fg_color="#181818")
        footer.pack(side="bottom", fill="x", padx=0, pady=0)
        
        cur = self.stage_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM changes")
        pending_count = cur.fetchone()[0]
        
        f_info = ctk.CTkFrame(footer, fg_color="transparent")
        f_info.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_info, text=f"{self.tr('pending_changes')} {pending_count}", font=ctk.CTkFont(weight="bold"), 
                     text_color="#F39C12" if pending_count > 0 else "gray").pack(side="left")
        
        if pending_count > 0:
            ctk.CTkButton(f_info, text=self.tr("btn_revert"), width=60, height=20, fg_color="#C0392B", 
                          command=self.discard_all_changes).pack(side="right")

        f_btns = ctk.CTkFrame(footer, fg_color="transparent")
        f_btns.pack(fill="x", padx=15, pady=(0,15))
        
        self.btn_save = ctk.CTkButton(f_btns, text=self.tr("btn_save_disk"), height=40, width=120, fg_color="#27AE60",
                                      state="normal" if not self.is_read_only else "disabled",
                                      command=self.save_batch_changes)
        self.btn_save.pack(side="left", fill="x", expand=True, padx=(0,5))
        
        self.btn_upload = ctk.CTkButton(f_btns, text=self.tr("btn_upload"), height=40, width=120, fg_color="#D35400",
                                        state="normal" if (self.is_sftp and not self.is_read_only) else "disabled",
                                        command=self.trigger_manual_upload)
        self.btn_upload.pack(side="left", fill="x", expand=True, padx=(5,0))

    def do_stage_change(self, key, widget, max_val):
        try:
            val_str = widget.get().replace(',', '.')
            val = float(val_str)
            if not (1.0 <= val <= max_val):
                messagebox.showerror(self.tr("msg_confirm"), self.tr("msg_limit", key=key, max=max_val))
                return
            self.stage_value(self.selected_pid, key, val)
            widget.configure(border_color="#F39C12", text_color="#F39C12")
            self.update_row_visuals(self.selected_pid)
            self.setup_inspector_ui()
        except: pass

    def create_treeview(self, parent):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#212121", foreground="#E0E0E0", fieldbackground="#212121", rowheight=35, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#181818", foreground="#AAAAAA", borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map('Treeview', background=[('selected', '#3498DB')])

        cols = ("id", "name", "steam", "str", "con", "dex", "int")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse")
        
        self.tree.heading("id", text="ID"); self.tree.column("id", width=40, anchor="center")
        self.tree.heading("name", text=self.tr("col_name")); self.tree.column("name", width=180, anchor="w")
        self.tree.heading("steam", text=self.tr("col_steam")); self.tree.column("steam", width=120, anchor="center")
        self.tree.heading("str", text="STR"); self.tree.column("str", width=50, anchor="center")
        self.tree.heading("con", text="CON"); self.tree.column("con", width=50, anchor="center")
        self.tree.heading("dex", text="DEX"); self.tree.column("dex", width=50, anchor="center")
        self.tree.heading("int", text="INT"); self.tree.column("int", width=50, anchor="center")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        try:
            self.selected_pid = int(sel[0])
            self.setup_inspector_ui()
        except: pass

    # =========================================================================
    # LOGIC (Staging, DB)
    # =========================================================================
    def setup_local_mode(self):
        self.is_sftp = False
        default_path = self.config.get('LOCAL', 'DbPath', fallback='')
        f = filedialog.askopenfilename(initialdir=os.path.dirname(default_path), filetypes=[("DB", "*.db")])
        if f:
            self.db_path = f
            self.btn_src_local.configure(fg_color="#3498DB", text_color="white")
            self.btn_src_sftp.configure(fg_color="transparent", text_color="gray")
            self.connect_db_generic()

    def connect_db_generic(self):
        try:
            if self.conn: self.conn.close()
            
            self.log(f"Opening database: {self.db_path}")
            if check_db_lock(self.db_path):
                self.is_read_only = True
                self.log(" -> [LOCKED] Database is in use by another process.")
                messagebox.showwarning("Locked", self.tr("locked_alert"))
            else:
                self.is_read_only = self.is_remote_locked if self.is_sftp else False
                if self.is_read_only: self.log(" -> [READ-ONLY] Remote lock detected.")

            self.conn = sqlite3.connect(self.db_path)
            self.current_cursor = self.conn.cursor()
            self.load_prisoners()
            self.log("Database connected successfully.")
            
        except Exception as e:
            self.log(f"Error connecting to DB: {e}")
            messagebox.showerror("Error", str(e))

    def init_staging_db(self):
        try:
            if self.conn: self.conn.close()
            # Reconnection logic handled else where or staging db is separate?
            # Creating staging in memory or local file
            self.stage_conn = sqlite3.connect("staging.db", check_same_thread=False)
            self.stage_conn.execute("CREATE TABLE IF NOT EXISTS changes (player_id INTEGER, attr TEXT, value REAL, PRIMARY KEY(player_id, attr))")
            self.stage_conn.commit()
        except: pass

    def get_staged_changes(self):
        cur = self.stage_conn.cursor()
        cur.execute("SELECT player_id, attr, value FROM changes")
        res = {}
        for pid, attr, val in cur.fetchall():
            if pid not in res: res[pid] = {}
            res[pid][attr] = val
        return res

    def stage_value(self, pid, attr, val):
        self.stage_conn.execute("INSERT OR REPLACE INTO changes (player_id, attr, value) VALUES (?,?,?)", (pid, attr, val))
        self.stage_conn.commit()
    
    def clear_staging_db(self):
        self.stage_conn.execute("DELETE FROM changes")
        self.stage_conn.commit()
        self.setup_inspector_ui()

    def discard_all_changes(self):
        if messagebox.askyesno(self.tr("msg_confirm"), self.tr("msg_discard")):
            self.clear_staging_db()
            self.filter_player_list() 
            self.setup_inspector_ui()

    def load_prisoners(self):
        if not self.current_cursor: return
        lst = fetch_prisoners(self.current_cursor)
        if not lst: return
        self.all_prisoners_data = lst
        self.filter_player_list()
        
        mode = "SFTP" if self.is_sftp else "LOCAL"
        if self.is_read_only: mode += " [READ ONLY]"
        self.lbl_status_main.configure(text=mode, text_color="#E74C3C" if self.is_read_only else "gray")
        self.setup_inspector_ui() 

    def filter_player_list(self, *args):
        for i in self.tree.get_children(): self.tree.delete(i)
        query = self.search_var.get().lower()
        staged = self.get_staged_changes() 
        count = 0
        for p in self.all_prisoners_data:
            dname = f"{p['name']} {p['steam_id']}".lower()
            if query in dname or query in str(p['id']):
                attrs = get_prisoner_attributes(self.current_cursor, p['id'])
                pend = staged.get(p['id'], {})
                vals = [p['id'], p['name'], p['steam_id']]
                for k in ['strength', 'constitution', 'dexterity', 'intelligence']:
                    if k in pend: vals.append(f"{pend[k]:.1f} *")
                    else: vals.append(f"{attrs.get(k, 0.0):.1f}" if attrs else "-")
                self.tree.insert("", "end", iid=p['id'], values=vals)
                count += 1
        self.lbl_count.configure(text=f"{count} {self.tr('items_found')}")
        if self.selected_pid and self.tree.exists(self.selected_pid):
            self.tree.selection_set(self.selected_pid)

    def update_row_visuals(self, pid):
        p = next((x for x in self.all_prisoners_data if x['id'] == pid), None)
        if not p: return
        attrs = get_prisoner_attributes(self.current_cursor, pid)
        pend = self.get_staged_changes().get(pid, {})
        vals = [p['id'], p['name'], p['steam_id']]
        for k in ['strength', 'constitution', 'dexterity', 'intelligence']:
            if k in pend: vals.append(f"{pend[k]:.1f} *")
            else: vals.append(f"{attrs.get(k, 0.0):.1f}" if attrs else "-")
        if self.tree.exists(pid): self.tree.item(pid, values=vals)

    def save_batch_changes(self):
        if self.is_read_only: return
        changes = self.get_staged_changes()
        if not changes: return
        count = 0
        for pid, p_changes in changes.items():
            success, _ = update_prisoner_attributes(self.current_cursor, pid, p_changes)
            if success: count += 1
        if count > 0:
            self.conn.commit()
            self.clear_staging_db()
            self.load_prisoners()
            messagebox.showinfo(self.tr("msg_success"), self.tr("msg_saved", count=count, dest='SFTP Temp' if self.is_sftp else 'Disk'))

    # =========================================================================
    # SFTP LOGIC
    # =========================================================================
    def start_sftp_flow(self):
        if not PARAMIKO_AVAILABLE: 
            self.log("Error: Paramiko library not found.")
            return messagebox.showerror("Error", self.tr("error_paramiko"))
            
        self.lbl_sub_status.configure(text=self.tr("status_connecting"), text_color="orange")
        self.log("Initiating SFTP connection...")
        threading.Thread(target=self._thread_sftp_list, daemon=True).start()

    def _thread_sftp_list(self):
        try:
            self.config.read('config.ini')
            h = self.config.get('SFTP', 'Host')
            self.after(0, lambda: self.log(f"Connecting to {h}..."))
            
            p = int(self.config.get('SFTP', 'Port'))
            u = self.config.get('SFTP', 'User')
            pw = self.config.get('SFTP', 'Password')
            rem = self.config.get('SFTP', 'RemoteDbPath')
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(h, port=p, username=u, password=pw)
            sftp = ssh.open_sftp()
            
            base = os.path.dirname(rem) if rem.endswith('.db') else rem
            if not base or base == ".": base = "."
            
            self.after(0, lambda: self.log(f"Listing files in: {base}"))
            files = sftp.listdir(base)
            db_files = [x for x in files if x.endswith('.db')]
            
            self.after(0, lambda: self.log(f"Found {len(db_files)} database files."))
            sftp.close(); ssh.close()
            
            self.after(0, lambda: self.show_sftp_selector(db_files, files, base))
        except Exception as e:
             self.after(0, lambda: self.log(f"[SFTP ERROR] {e}"))
             self.after(0, lambda: messagebox.showerror("SFTP Error", str(e)))
             self.after(0, lambda: self.lbl_sub_status.configure(text="Connection Failed", text_color="red"))

    def show_sftp_selector(self, dbs, all_files, base):
        self.lbl_sub_status.configure(text="Select DB", text_color="white")
        top = ctk.CTkToplevel(self)
        top.title("Select Database")
        top.geometry("400x400")
        ctk.CTkLabel(top, text="Available Databases", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True)
        for f in dbs:
            locked = (f"{f}-wal" in all_files) or (f"{f}-shm" in all_files)
            btn = ctk.CTkButton(scroll, text=f"{f} {'[LOCKED]' if locked else ''}", 
                                fg_color="#C0392B" if locked else "#2980B9",
                                command=lambda fn=f, lk=locked: self.confirm_sftp_dl(top, base, fn, lk))
            btn.pack(fill="x", pady=2)

    def confirm_sftp_dl(self, win, base, fname, locked):
        win.destroy()
        full = f"{base}/{fname}".replace("//", "/")
        self.config.set('SFTP', 'RemoteDbPath', full)
        self.is_remote_locked = locked
        if locked: 
            self.log(f"Warning: {fname} appears to be locked (WAL/SHM present).")
            messagebox.showwarning("Locked", self.tr("remote_locked"))
        
        self.lbl_sub_status.configure(text=self.tr("status_downloading"), text_color="#3498DB")
        self.log(f"Starting download: {full}")
        threading.Thread(target=self._thread_sftp_dl, args=(full,), daemon=True).start()

    def _thread_sftp_dl(self, remote_path):
        try:
            h = self.config.get('SFTP', 'Host')
            p = int(self.config.get('SFTP', 'Port'))
            u = self.config.get('SFTP', 'User')
            pw = self.config.get('SFTP', 'Password')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.sftp_temp_path = os.path.join(self.temp_folder, f"SFTP_{timestamp}.db")

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(h, port=p, username=u, password=pw)
            sftp = ssh.open_sftp()
            
            self.after(0, lambda: self.log(f"Downloading to: {self.sftp_temp_path}"))
            sftp.get(remote_path, self.sftp_temp_path)
            sftp.close(); ssh.close()
            
            self.after(0, lambda: self.log("Download complete."))
            self.after(0, self.finalize_sftp_dl)
        except Exception as e:
            self.after(0, lambda: self.log(f"[DOWNLOAD ERROR] {e}"))
            self.after(0, lambda: messagebox.showerror("DL Error", str(e)))

    def finalize_sftp_dl(self):
        self.is_sftp = True
        self.db_path = self.sftp_temp_path
        self.btn_src_sftp.configure(fg_color="#D35400", text_color="white")
        self.btn_src_local.configure(fg_color="transparent", text_color="gray")
        self.lbl_sub_status.configure(text=self.tr("status_connected"), text_color="#2ECC71")
        create_local_backup(self.db_path, custom_name="SFTP_Download.db")
        self.connect_db_generic()

    def trigger_manual_upload(self):
        if not self.is_sftp: return
        if not messagebox.askyesno(self.tr("msg_confirm"), self.tr("msg_upload_ask")): return
        self.lbl_sub_status.configure(text=self.tr("status_uploading"), text_color="orange")
        self.log("Starting upload process...")
        threading.Thread(target=self._thread_sftp_up, daemon=True).start()

    def _thread_sftp_up(self):
        try:
            rem = self.config.get('SFTP', 'RemoteDbPath')
            h = self.config.get('SFTP', 'Host')
            p = int(self.config.get('SFTP', 'Port'))
            
            self.after(0, lambda: self.log(f"Connecting to {h} for upload..."))
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(h, port=p, username=self.config.get('SFTP', 'User'), password=self.config.get('SFTP', 'Password'))
            sftp = ssh.open_sftp()
            
            try: 
                sftp.rename(rem, f"{rem}.bak")
                self.after(0, lambda: self.log("Remote backup created (.bak)."))
            except: pass
            
            self.after(0, lambda: self.log(f"Uploading {self.sftp_temp_path} -> {rem}"))
            sftp.put(self.sftp_temp_path, rem)
            sftp.close(); ssh.close()
            
            self.after(0, lambda: self.log("Upload successful."))
            self.after(0, lambda: messagebox.showinfo(self.tr("msg_success"), self.tr("msg_upload_done")))
            self.after(0, lambda: self.lbl_sub_status.configure(text="Upload OK", text_color="#2ECC71"))
        except Exception as e:
            self.after(0, lambda: self.log(f"[UPLOAD ERROR] {e}"))
            self.after(0, lambda: messagebox.showerror("Up Error", str(e)))

    # =========================================================================
    # SETTINGS VIEW
    # =========================================================================
    def setup_settings_view(self):
        ctk.CTkLabel(self.frame_settings, text=self.tr("settings_title"), font=ctk.CTkFont(size=24, weight="bold")).pack(pady=30)
        form = ctk.CTkFrame(self.frame_settings)
        form.pack(pady=20, padx=50, fill="both", expand=True)

        # Language Selector
        row_lang = ctk.CTkFrame(form, fg_color="transparent")
        row_lang.pack(fill="x", pady=10, padx=20)
        ctk.CTkLabel(row_lang, text=self.tr("lbl_lang"), width=150, anchor="w").pack(side="left")
        
        seg_lang = ctk.CTkSegmentedButton(row_lang, values=["en", "pt"], command=self.set_language)
        seg_lang.pack(side="right")
        seg_lang.set(self.lang)

        # Config fields
        self.ents_cfg = {}
        def add_cfg(label, sec, key, is_pass=False):
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", pady=10, padx=20)
            ctk.CTkLabel(row, text=label, width=150, anchor="w").pack(side="left")
            e = ctk.CTkEntry(row)
            if is_pass: e.configure(show="*")
            e.pack(side="right", fill="x", expand=True)
            e.insert(0, self.config.get(sec, key, fallback=''))
            self.ents_cfg[f"{sec}.{key}"] = e

        ctk.CTkLabel(form, text=self.tr("settings_sftp"), text_color="#3498DB", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        add_cfg("Host", "SFTP", "Host")
        add_cfg("Port", "SFTP", "Port")
        add_cfg("User", "SFTP", "User")
        add_cfg("Password", "SFTP", "Password", is_pass=True)
        add_cfg("Remote Path", "SFTP", "RemoteDbPath")

        ctk.CTkButton(self.frame_settings, text=self.tr("btn_save_cfg"), command=self.save_cfg, height=50).pack(pady=20, fill="x", padx=100)

    def save_cfg(self):
        for k, e in self.ents_cfg.items():
            sec, key = k.split('.')
            if not self.config.has_section(sec): self.config.add_section(sec)
            self.config.set(sec, key, e.get())
        
        with open('config.ini', 'w') as f: self.config.write(f)
        messagebox.showinfo(self.tr("msg_success"), "Configuration updated.")

    # =========================================================================
    # VIEW: CREDITS
    # =========================================================================
    def setup_credits_view(self):
        self.frame_credits.grid_rowconfigure(0, weight=1)
        self.frame_credits.grid_columnconfigure(0, weight=1)
        
        container = ctk.CTkFrame(self.frame_credits, fg_color="#2B2B2B", corner_radius=20)
        container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.6, relheight=0.85)
        
        ctk.CTkLabel(container, text="SetAttributes EDITOR", font=ctk.CTkFont(size=30, weight="bold"), text_color="#3498DB").pack(pady=(40, 10))
        ctk.CTkLabel(container, text="v0.9 beta", font=ctk.CTkFont(size=16), text_color="gray").pack()
        
        ctk.CTkLabel(container, text="Desenvolvido por:", font=ctk.CTkFont(size=14)).pack(pady=(40, 5))
        ctk.CTkLabel(container, text="Nereu Jr", font=ctk.CTkFont(size=22, weight="bold"), text_color="white").pack()
        
        ctk.CTkLabel(container, text="Tecnologias:", font=ctk.CTkFont(size=14)).pack(pady=(30, 5))
        ctk.CTkLabel(container, text="Python | CustomTkinter | SQLite | Paramiko", text_color="gray").pack()
        
        ctk.CTkLabel(container, text="© 2025 Todos os direitos reservados.", font=ctk.CTkFont(size=10), text_color="gray30").pack(side="bottom", pady=20)
        
        # Additional Credits Display
        ctk.CTkLabel(container, text=self.tr("credits_thank_title"), font=ctk.CTkFont(size=16, weight="bold"), text_color="#F39C12").pack(pady=(20, 10))
        # Custom Credits Flow with Bold Names
        font_norm = ctk.CTkFont(size=12)
        font_bold = ctk.CTkFont(size=12, weight="bold")
        
        # Row 1: Admins
        f_r1 = ctk.CTkFrame(container, fg_color="transparent")
        f_r1.pack(pady=(5,0))
        ctk.CTkLabel(f_r1, text=self.tr("c_admins"), font=font_norm).pack(side="left")
        ctk.CTkLabel(f_r1, text=" Sabugador ", font=font_bold, text_color="white").pack(side="left")
        ctk.CTkLabel(f_r1, text=self.tr("c_and"), font=font_norm).pack(side="left")
        ctk.CTkLabel(f_r1, text=" Mewtwo ", font=font_bold, text_color="white").pack(side="left")
        
        # Row 2: Server
        ctk.CTkLabel(container, text=self.tr("c_server"), font=font_norm).pack(pady=0)
        ctk.CTkLabel(container, text="'Oblivion[BR] - PvP/PvE - 5x Loot - 10x Skill'", font=ctk.CTkFont(size=11, slant="italic"), text_color="silver").pack(pady=0)
        
        # Row 3: Emiza
        f_r3 = ctk.CTkFrame(container, fg_color="transparent")
        f_r3.pack(pady=(5,0))
        ctk.CTkLabel(f_r3, text=self.tr("c_emiza"), font=font_norm).pack(side="left")
        ctk.CTkLabel(f_r3, text=" Emiza ", font=font_bold, text_color="white").pack(side="left")
        ctk.CTkLabel(f_r3, text=self.tr("c_mediation"), font=font_norm).pack(side="left")

    # =========================================================================
    # VIEW: TERMS
    # =========================================================================
    def setup_terms_view(self):
        self.frame_terms.grid_rowconfigure(0, weight=1)
        self.frame_terms.grid_columnconfigure(0, weight=1)
        
        container = ctk.CTkFrame(self.frame_terms, fg_color="#2B2B2B", corner_radius=20)
        container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.85)

        # Reuse parsing logic
        inner_frame = ctk.CTkFrame(container, fg_color="transparent")
        inner_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.populate_terms_content(inner_frame)

if __name__ == "__main__":
    app = App()
    app.mainloop()
