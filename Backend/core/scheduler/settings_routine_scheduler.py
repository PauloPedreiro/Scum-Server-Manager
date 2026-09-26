#!/usr/bin/env python3
"""
Settings Routine Scheduler - Agendador programado para troca de ServerSettings.ini
"""

import os
import json
import time
import shutil
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from utils.logger import StructuredLogger

class SettingsRoutineScheduler:
    """Agendador de arquivos de configuração ServerSettings.ini"""

    def __init__(self, config: Dict[str, Any], path_helper: Any, logger: Optional[StructuredLogger] = None):
        self.config = config
        self.path_helper = path_helper
        self.logger = logger or StructuredLogger()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # Estado em memória do ID da rotina ativa
        self.active_routine_id: Optional[str] = None
        self.last_check_time: float = 0.0

        # Diretórios e caminhos
        self.data_dir = self._get_data_dir()
        self.presets_dir = self.data_dir / "server_settings_presets"
        self.routines_file = self.data_dir / "settings_routines.json"

        # Executar auto-setup
        self._ensure_setup()

    def _get_data_dir(self) -> Path:
        """Obter diretório de dados"""
        # Tentar obter do path_helper
        if self.path_helper:
            try:
                return Path(self.path_helper.get_application_path("data_directory", "data"))
            except Exception:
                pass
        return Path("data")

    def _get_scum_settings_file(self) -> Optional[Path]:
        """Obter o caminho do ServerSettings.ini oficial do SCUM"""
        if self.path_helper:
            try:
                config_dir = self.path_helper.get_scum_server_path("config_directory")
                if config_dir:
                    return Path(config_dir) / "ServerSettings.ini"
            except Exception as e:
                self.logger.error(f"Erro ao obter caminho do ServerSettings.ini do SCUM: {e}")
        return None

    def _ensure_setup(self):
        """Auto-setup silencioso: criar diretórios e arquivos necessários"""
        try:
            # 1. Garantir pasta de presets
            self.presets_dir.mkdir(parents=True, exist_ok=True)

            # 2. Garantir default.ini a partir do ServerSettings.ini atual do SCUM
            default_preset = self.presets_dir / "default.ini"
            scum_settings = self._get_scum_settings_file()
            
            if not default_preset.exists() and scum_settings and scum_settings.exists():
                try:
                    shutil.copy2(scum_settings, default_preset)
                    self.logger.info(f"Preset padrão inicial criado com sucesso a partir de: {scum_settings}")
                except Exception as e:
                    self.logger.warning(f"Não foi possível copiar ServerSettings.ini original para default.ini: {e}")

            # 3. Garantir arquivo de rotinas vazio
            if not self.routines_file.exists():
                try:
                    with open(self.routines_file, "w", encoding="utf-8") as f:
                        json.dump([], f, indent=2, ensure_ascii=False)
                    self.logger.info(f"Arquivo de rotinas de configurações criado: {self.routines_file}")
                except Exception as e:
                    self.logger.error(f"Erro ao criar arquivo de rotinas: {e}")

            # 4. Garantir chave no config.json
            if "settings_scheduler" not in self.config:
                self.config["settings_scheduler"] = {"enabled": False}
                self._save_config_file()

        except Exception as e:
            self.logger.error(f"Erro no auto-setup do SettingsRoutineScheduler: {e}")

    def _save_config_file(self):
        """Salvar configuração global no config.json"""
        try:
            config_path = self.data_dir / "config.json"
            # Fazer cópia limpa para salvar
            config_to_save = {}
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_to_save = json.load(f)
                except Exception:
                    config_to_save = self.config.copy()
            
            config_to_save["settings_scheduler"] = self.config.get("settings_scheduler", {"enabled": False})
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao salvar config.json: {e}")

    def load_routines(self) -> List[Dict[str, Any]]:
        """Carregar rotinas do arquivo JSON"""
        with self.lock:
            if not self.routines_file.exists():
                return []
            try:
                with open(self.routines_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Erro ao ler rotinas do arquivo JSON: {e}")
                return []

    def save_routines(self, routines: List[Dict[str, Any]]) -> bool:
        """Salvar rotinas no arquivo JSON"""
        with self.lock:
            try:
                with open(self.routines_file, "w", encoding="utf-8") as f:
                    json.dump(routines, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                self.logger.error(f"Erro ao salvar rotinas no arquivo JSON: {e}")
                return False

    def is_enabled(self) -> bool:
        """Verificar se o agendador está habilitado globalmente"""
        return self.config.get("settings_scheduler", {}).get("enabled", False)

    def set_enabled(self, enabled: bool):
        """Habilitar ou desabilitar o agendador globalmente"""
        if "settings_scheduler" not in self.config:
            self.config["settings_scheduler"] = {}
        self.config["settings_scheduler"]["enabled"] = enabled
        self._save_config_file()
        
        self.logger.info(f"Agendador de configurações global {'HABILITADO' if enabled else 'DESABILITADO'}")
        
        if enabled:
            self.reconcile()

    def start(self):
        """Iniciar a thread do agendador"""
        with self.lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, name="SettingsSchedulerThread", daemon=True)
            self.thread.start()
            self.logger.info("Agendador de ServerSettings iniciado com sucesso")

        # Reconciliar o estado atual imediatamente no startup
        self.reconcile()

    def stop(self):
        """Parar a thread do agendador"""
        with self.lock:
            if not self.running:
                return
            self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.logger.info("Agendador de ServerSettings parado")

    def _run_loop(self):
        """Loop principal de verificação"""
        while self.running:
            try:
                if self.is_enabled():
                    self.reconcile()
            except Exception as e:
                self.logger.error(f"Erro no loop de reconciliação do agendador de config: {e}")
            
            # Aguardar 60 segundos antes de verificar novamente
            time.sleep(60)

    def is_time_in_routine(self, now: datetime, routine: Dict[str, Any]) -> bool:
        """
        Verifica se a data/hora fornecida está dentro da janela da rotina
        Suporta eventos que cruzam a meia-noite (overnight)
        """
        if not routine.get("enabled", True):
            return False

        days = routine.get("days_of_week", [])
        if not days:
            return False

        start_str = routine.get("start_time", "")
        end_str = routine.get("end_time", "")
        if not start_str or not end_str:
            return False

        try:
            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))
        except ValueError:
            return False

        today_weekday = now.weekday()

        # Caso 1: Verifica se começou HOJE
        if today_weekday in days:
            today_start = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            if sh <= eh:
                today_end = now.replace(hour=eh, minute=em, second=0, microsecond=0)
                if today_start <= now < today_end:
                    return True
            else:
                # Cruza a meia-noite (overnight)
                today_end = (now + timedelta(days=1)).replace(hour=eh, minute=em, second=0, microsecond=0)
                if today_start <= now < today_end:
                    return True

        # Caso 2: Verifica se começou ONTEM (para eventos que cruzam a meia-noite)
        yesterday_weekday = (today_weekday - 1) % 7
        if yesterday_weekday in days:
            if sh > eh:  # Apenas se cruzar a meia-noite
                yesterday_start = (now - timedelta(days=1)).replace(hour=sh, minute=sm, second=0, microsecond=0)
                yesterday_end = now.replace(hour=eh, minute=em, second=0, microsecond=0)
                if yesterday_start <= now < yesterday_end:
                    return True

        return False

    def reconcile(self):
        """Avaliar a hora atual e garantir que o arquivo correto esteja aplicado"""
        if not self.is_enabled():
            return

        now = datetime.now()
        routines = self.load_routines()
        
        active_routine: Optional[Dict[str, Any]] = None
        
        # Encontrar a primeira rotina ativa
        for r in routines:
            if self.is_time_in_routine(now, r):
                active_routine = r
                break

        # Ações baseadas no estado da rotina ativa detectada
        if active_routine:
            routine_id = active_routine["id"]
            preset_file = active_routine.get("preset_file", "")
            
            # Se for uma nova rotina detectada
            if self.active_routine_id != routine_id:
                self.logger.info(f"Ativando rotina de configuração '{active_routine.get('name')}' (Preset: {preset_file})")
                success = self.apply_preset(preset_file)
                if success:
                    self.active_routine_id = routine_id
                else:
                    self.logger.error(f"Falha ao aplicar preset '{preset_file}' para a rotina '{active_routine.get('name')}'")
        else:
            # Nenhuma rotina ativa. Se antes tínhamos uma rotina ativa, restauramos o default
            # Também forçamos a primeira reconciliação no startup a validar o default se active_routine_id for None
            if self.active_routine_id is not None:
                self.logger.info("Nenhuma rotina ativa detectada. Restaurando ServerSettings.ini padrão (default.ini)")
                success = self.apply_preset("default.ini")
                if success:
                    self.active_routine_id = None
            elif not self._is_file_synced_with_preset("default.ini"):
                # Garante que o arquivo do jogo seja sincronizado com o default.ini caso estejam desalinhados no startup
                self.logger.info("Restaurando ServerSettings.ini para default.ini devido a desalinhamento de startup")
                self.apply_preset("default.ini")

    def _is_file_synced_with_preset(self, preset_name: str) -> bool:
        """Verifica se o ServerSettings.ini oficial do jogo tem o mesmo tamanho/data que o preset (evita escrita redundante)"""
        scum_settings = self._get_scum_settings_file()
        preset_path = self.presets_dir / preset_name
        
        if not scum_settings or not scum_settings.exists() or not preset_path.exists():
            return False
            
        try:
            # Um check rápido de tamanho de arquivo é muito eficiente para arquivos INI
            return scum_settings.stat().st_size == preset_path.stat().st_size
        except Exception:
            return False

    def apply_preset(self, preset_name: str) -> bool:
        """Copiar fisicamente um preset para o caminho oficial do ServerSettings.ini"""
        scum_settings = self._get_scum_settings_file()
        if not scum_settings:
            self.logger.error("Caminho do ServerSettings.ini do SCUM não configurado no SSM")
            return False

        preset_path = self.presets_dir / preset_name
        if not preset_path.exists():
            self.logger.error(f"Preset de configuração não encontrado: {preset_path}")
            return False

        try:
            # Garantir pasta de destino
            scum_settings.parent.mkdir(parents=True, exist_ok=True)
            
            # Copiar arquivo sobrescrevendo
            shutil.copy2(preset_path, scum_settings)
            self.logger.info(f"Preset '{preset_name}' aplicado com sucesso em: {scum_settings}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao copiar preset '{preset_name}' para '{scum_settings}': {e}")
            return False

    def get_presets(self) -> List[Dict[str, Any]]:
        """Listar todos os presets de configuração na pasta de presets"""
        presets = []
        try:
            for item in self.presets_dir.glob("*.ini"):
                stat = item.stat()
                presets.append({
                    "name": item.name,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        except Exception as e:
            self.logger.error(f"Erro ao listar presets: {e}")
        return presets

    def upload_preset(self, file_content: bytes, name: str) -> Dict[str, Any]:
        """Salvar um novo preset enviado pelo usuário"""
        # Sanitizar nome
        name = name.strip()
        if not name.endswith(".ini"):
            name += ".ini"
        
        # Impedir caracteres ilegais para segurança de arquivos
        name = "".join(c for c in name if c.isalnum() or c in (".", "-", "_"))
        if name in ("", ".ini"):
            return {"success": False, "error": "Nome de preset inválido"}

        preset_path = self.presets_dir / name
        try:
            with open(preset_path, "wb") as f:
                f.write(file_content)
            self.logger.info(f"Novo preset '{name}' salvo via upload")
            return {"success": True, "name": name}
        except Exception as e:
            self.logger.error(f"Erro ao salvar preset '{name}' via upload: {e}")
            return {"success": False, "error": str(e)}

    def delete_preset(self, name: str) -> Dict[str, Any]:
        """Remover um preset físico da pasta"""
        name = os.path.basename(name)
        if name == "default.ini":
            return {"success": False, "error": "O preset padrão (default.ini) não pode ser excluído"}

        preset_path = self.presets_dir / name
        if not preset_path.exists():
            return {"success": False, "error": "Preset não encontrado"}

        try:
            preset_path.unlink()
            self.logger.info(f"Preset '{name}' excluído com sucesso")
            return {"success": True}
        except Exception as e:
            self.logger.error(f"Erro ao excluir preset '{name}': {e}")
            return {"success": False, "error": str(e)}

    def clone_current_as_preset(self, name: str) -> Dict[str, Any]:
        """Clonar o ServerSettings.ini oficial atual do jogo como um preset"""
        scum_settings = self._get_scum_settings_file()
        if not scum_settings or not scum_settings.exists():
            return {"success": False, "error": "ServerSettings.ini oficial do jogo não encontrado para clonar"}

        name = name.strip()
        if not name.endswith(".ini"):
            name += ".ini"
        name = "".join(c for c in name if c.isalnum() or c in (".", "-", "_"))
        if name in ("", ".ini"):
            return {"success": False, "error": "Nome de preset inválido"}

        preset_path = self.presets_dir / name
        try:
            shutil.copy2(scum_settings, preset_path)
            self.logger.info(f"ServerSettings.ini oficial clonado como preset: {name}")
            return {"success": True, "name": name}
        except Exception as e:
            self.logger.error(f"Erro ao clonar ServerSettings.ini atual para preset '{name}': {e}")
            return {"success": False, "error": str(e)}
