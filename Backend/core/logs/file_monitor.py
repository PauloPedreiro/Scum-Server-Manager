"""
Monitor de Arquivos de Log do SCUM
Sistema de monitoramento em tempo real para detectar mudanças nos logs
"""

import os
import time
import threading
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from core.logs.temp_file_manager import TempFileManager
from core.database.connector import DatabaseConnector
from utils.logger import StructuredLogger

class LogFileHandler(FileSystemEventHandler):
    """Handler para eventos de arquivo do sistema"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        super().__init__()
    
    def on_modified(self, event):
        """Arquivo foi modificado"""
        if not event.is_directory and self._is_login_log(event.src_path):
            print(f"DEBUG: Arquivo modificado detectado: {os.path.basename(event.src_path)}")
            self.monitor._process_file_changes(event.src_path)
    
    def on_created(self, event):
        """Novo arquivo foi criado"""
        if not event.is_directory and self._is_login_log(event.src_path):
            self.monitor._process_file_changes(event.src_path)
    
    def _is_login_log(self, file_path: str) -> bool:
        """Verificar se é arquivo de log de login, chat, admin, vehicle destruction, gameplay, kill ou famepoints"""
        # NOTA: chest_ownership_*.log e economy_*.log NÃO são monitorados pelo watchdog - usam cópia periódica apenas
        filename = os.path.basename(file_path)
        return (filename.startswith('login_') or 
                filename.startswith('chat_') or filename.startswith('admin_') or 
                filename.startswith('vehicle_destruction_') or filename.startswith('gameplay_') or
                filename.startswith('kill_') or filename.startswith('famepoints_')) and filename.endswith('.log')

class LogFileMonitor:
    """Monitor de arquivos de log em tempo real"""
    
    def __init__(
        self,
        log_directory: str,
        callback: Callable[[str, List[str]], None],
        db_path: str = "data/SSM.db",
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.log_directory = log_directory
        self.callback = callback
        self.db_path = db_path  # Caminho do banco para acessar log_files_processed
        self.logger = logger
        self.observer = None
        self.running = False
        self.stop_event = threading.Event()
        self.file_positions = {}  # Controle de posição em cada arquivo
        self.lock = threading.Lock()
        self.polling_thread = None
        self.polling_interval = 5  # Verificar a cada 5 segundos
        self.chest_ownership_copy_interval = 30  # Copiar chest_ownership a cada 30 segundos
        self.chest_ownership_copy_thread = None
        self.chest_ownership_last_line_count = {}  # Última quantidade de linhas processadas por arquivo
        self.gameplay_copy_interval = 5  # Copiar gameplay_*.log a cada 5 segundos (reduz latência de alertas)
        self.gameplay_copy_thread = None
        self.current_active_gameplay_file = None  # Arquivo gameplay ativo atual
        self.economy_copy_interval = 30  # Copiar economy_*.log a cada 30 segundos
        self.economy_copy_thread = None
        self.economy_last_line_count = {}  # Última quantidade de linhas processadas por arquivo
        self.temp_manager = TempFileManager("data/temp")  # Gerenciador de arquivos temporários
        self.max_retries = 5
        self.busy_timeout_ms = 5000

        try:
            fm_cfg = (config or {}).get("file_monitor")
            if isinstance(fm_cfg, dict):
                pi = fm_cfg.get("polling_interval_seconds")
                gi = fm_cfg.get("gameplay_copy_interval_seconds")
                ci = fm_cfg.get("chest_ownership_copy_interval_seconds")
                ei = fm_cfg.get("economy_copy_interval_seconds")

                if pi is not None:
                    self.polling_interval = max(1, int(float(pi)))
                if gi is not None:
                    self.gameplay_copy_interval = max(1, int(float(gi)))
                if ci is not None:
                    self.chest_ownership_copy_interval = max(1, int(float(ci)))
                if ei is not None:
                    self.economy_copy_interval = max(1, int(float(ei)))
        except Exception:
            pass
        # Log do caminho da pasta temp
        temp_path = os.path.abspath("data/temp")
        print(f"INFO Pasta temp para chest_ownership: {temp_path}")
        print(f"INFO Pasta temp para gameplay: {temp_path}")
        print(f"INFO Pasta temp para economy: {temp_path}")
        
        # Verificar se diretório existe
        if not os.path.exists(log_directory):
            try:
                os.makedirs(log_directory, exist_ok=True)
                print(f"AVISO Pasta de logs não encontrada; criando automaticamente: {log_directory}")
            except Exception:
                raise FileNotFoundError(f"Diretório de logs não encontrado: {log_directory}")

    def _connect_db(self) -> sqlite3.Connection:
        """Usa o DatabaseConnector centralizado."""
        return DatabaseConnector.get_connection(self.db_path, timeout=5.0)

    def _sleep_backoff(self, attempt: int) -> None:
        time.sleep(0.2 * (2**attempt))
    
    def start_monitoring(self):
        """Iniciar monitoramento de arquivos"""
        try:
            # Configurar observer (watchdog)
            event_handler = LogFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, self.log_directory, recursive=False)
            
            # Iniciar observer
            self.observer.start()

            try:
                if self.logger:
                    self.logger.info(
                        "[FILE_MONITOR] Started watchdog observer",
                        {"log_directory": str(self.log_directory)},
                    )
            except Exception:
                pass

            # IMPORTANTE: definir running antes de iniciar threads de loop
            self.running = True
            try:
                self.stop_event.clear()
            except Exception:
                pass
            
            # Iniciar polling thread para arquivos que podem estar em uso
            self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
            self.polling_thread.start()

            try:
                if self.logger:
                    self.logger.info("[FILE_MONITOR] Polling thread started", {})
            except Exception:
                pass
            
            # Iniciar thread para copiar chest_ownership periodicamente
            self.chest_ownership_copy_thread = threading.Thread(target=self._chest_ownership_copy_loop, daemon=True)
            self.chest_ownership_copy_thread.start()
            print("OK Thread de cópia de chest_ownership iniciada")

            try:
                if self.logger:
                    self.logger.info(
                        "[FILE_MONITOR] Chest ownership copy thread started",
                        {"interval_seconds": int(self.chest_ownership_copy_interval)},
                    )
            except Exception:
                pass
            
            # Iniciar thread para copiar gameplay_*.log periodicamente
            self.gameplay_copy_thread = threading.Thread(target=self._gameplay_copy_loop, daemon=True)
            self.gameplay_copy_thread.start()
            print("OK Thread de cópia de gameplay iniciada")

            try:
                if self.logger:
                    self.logger.info(
                        "[FILE_MONITOR] Gameplay copy thread started",
                        {"interval_seconds": int(self.gameplay_copy_interval)},
                    )
            except Exception:
                pass
            
            # Iniciar thread para copiar economy_*.log periodicamente
            self.economy_copy_thread = threading.Thread(target=self._economy_copy_loop, daemon=True)
            self.economy_copy_thread.start()
            print("OK Thread de cópia de economy iniciada")

            try:
                if self.logger:
                    self.logger.info(
                        "[FILE_MONITOR] Economy copy thread started",
                        {"interval_seconds": int(self.economy_copy_interval)},
                    )
            except Exception:
                pass
            
            # logger.debug("Monitor de arquivos iniciado")
            # logger.debug("Aguardando mudanças nos arquivos de log...")
            
        except Exception as e:
            print(f"ERRO Erro ao iniciar monitor de arquivos: {e}")
            try:
                if self.logger:
                    self.logger.error(f"[FILE_MONITOR] Failed to start: {e}", {})
            except Exception:
                pass
            raise
    
    def stop_monitoring(self):
        """Parar monitoramento de arquivos"""
        try:
            self.running = False
            try:
                self.stop_event.set()
            except Exception:
                pass

            try:
                if self.logger:
                    self.logger.info("[FILE_MONITOR] Stopping", {})
            except Exception:
                pass
            
            if self.observer:
                self.observer.stop()
                self.observer.join()
            
            if self.polling_thread:
                self.polling_thread.join(timeout=5)
            
            if self.chest_ownership_copy_thread:
                self.chest_ownership_copy_thread.join(timeout=5)
            
            if self.gameplay_copy_thread:
                self.gameplay_copy_thread.join(timeout=5)
            
            if self.economy_copy_thread:
                self.economy_copy_thread.join(timeout=5)
                
            print("OK Monitor de arquivos parado")

            try:
                if self.logger:
                    self.logger.info("[FILE_MONITOR] Stopped", {})
            except Exception:
                pass
                
        except Exception as e:
            print(f"ERRO Erro ao parar monitor de arquivos: {e}")
            try:
                if self.logger:
                    self.logger.error(f"[FILE_MONITOR] Failed to stop: {e}", {})
            except Exception:
                pass

    def _read_all_lines_from_temp(self, temp_path: str) -> List[str]:
        """Ler todas as linhas de um arquivo de log temporário com fallback de encoding"""
        if not temp_path:
            return []
        if not os.path.exists(temp_path):
            return []

        encodings_to_try = ["utf-16le", "utf-16", "utf-8", "utf-8-sig", "latin-1", "cp1252"]
        last_error = None
        for encoding in encodings_to_try:
            try:
                with open(temp_path, "r", encoding=encoding, errors="replace") as f:
                    lines = [line.rstrip("\n").rstrip("\r") for line in f.readlines()]
                cleaned = [line for line in lines if line is not None]
                try:
                    null_count = 0
                    sample_chars = 0
                    for line in cleaned[:5]:
                        if not line:
                            continue
                        sample_chars += len(line)
                        null_count += line.count("\x00")
                    if sample_chars > 0 and null_count > (sample_chars * 0.2):
                        raise UnicodeError("null-byte heavy decoded text")
                except UnicodeError:
                    raise
                except Exception:
                    pass
                return cleaned
            except Exception as e:
                last_error = e
                continue

        try:
            with open(temp_path, "rb") as f:
                raw = f.read()
            text = raw.decode("utf-16le", errors="replace")
            return [line.rstrip("\r") for line in text.split("\n")]
        except Exception as e:
            last_error = e

        try:
            print(f"ERRO Falha ao ler arquivo temp {temp_path}: {last_error}")
        except Exception:
            pass
        return []
    
    def _polling_loop(self):
        """Loop de polling para detectar mudanças em arquivos"""
        # logger.debug("Polling loop iniciado")
        while self.running:
            try:
                # 1) Monitorar apenas o login_*.log mais recente
                login_files = [f for f in os.listdir(self.log_directory) if f.startswith('login_') and f.endswith('.log')]
                if login_files:
                    def file_key(name: str) -> str:
                        try:
                            base = name.split('login_')[1].split('.log')[0]
                        except Exception:
                            base = name
                        return ''.join(ch for ch in base if ch.isdigit())
                    latest_login_name = max(login_files, key=file_key)
                    file_path = os.path.join(self.log_directory, latest_login_name)
                    self._check_file_changes(file_path)

                # 2) Continuar monitorando chat_*.log (todos, pois podem existir dois ativos em janelas
                #    diferentes durante reinício)
                for filename in os.listdir(self.log_directory):
                    if filename.startswith('chat_') and filename.endswith('.log'):
                        self._check_file_changes(os.path.join(self.log_directory, filename))

                # 3) chest_ownership_*.log agora é processado em thread separada (cópia periódica)
                
                # 4) Monitorar admin_*.log (todos)
                for filename in os.listdir(self.log_directory):
                    if filename.startswith('admin_') and filename.endswith('.log'):
                        self._check_file_changes(os.path.join(self.log_directory, filename))
                
                # 5) Monitorar vehicle_destruction_*.log (todos)
                for filename in os.listdir(self.log_directory):
                    if filename.startswith('vehicle_destruction_') and filename.endswith('.log'):
                        self._check_file_changes(os.path.join(self.log_directory, filename))
                
                # 6) Monitorar kill_*.log (todos)
                for filename in os.listdir(self.log_directory):
                    if filename.startswith('kill_') and filename.endswith('.log'):
                        self._check_file_changes(os.path.join(self.log_directory, filename))
                
                # 7) Monitorar famepoints_*.log (todos)
                for filename in os.listdir(self.log_directory):
                    if filename.startswith('famepoints_') and filename.endswith('.log'):
                        self._check_file_changes(os.path.join(self.log_directory, filename))
                
                # 8) economy_*.log agora é processado em thread separada (cópia periódica)
                
                if self.stop_event.wait(self.polling_interval):
                    break
                
            except Exception as e:
                print(f"ERRO Erro no polling loop: {e}")
                if self.stop_event.wait(self.polling_interval):
                    break
    
    def _chest_ownership_copy_loop(self):
        """Loop para copiar chest_ownership periodicamente para temp, processar e deletar"""
        print(f"INFO Loop de cópia de chest_ownership iniciado (intervalo: {self.chest_ownership_copy_interval}s)")
        try:
            if self.logger:
                self.logger.info(
                    "[CHEST_OWNERSHIP] Copy loop started",
                    {"interval_seconds": int(self.chest_ownership_copy_interval)},
                )
        except Exception:
            pass
        while self.running:
            try:
                # Encontrar todos os arquivos chest_ownership_*.log
                chest_ownership_files = []
                try:
                    for filename in os.listdir(self.log_directory):
                        if filename.startswith('chest_ownership_') and filename.endswith('.log'):
                            file_path = os.path.join(self.log_directory, filename)
                            if os.path.exists(file_path):
                                chest_ownership_files.append(file_path)
                except Exception as e:
                    print(f"ERRO Erro ao listar arquivos chest_ownership: {e}")
                    if self.stop_event.wait(self.chest_ownership_copy_interval):
                        break
                    continue
                
                if chest_ownership_files:
                    print(f"CHEST_OWNERSHIP Copiando {len(chest_ownership_files)} arquivo(s) para temp...")
                    try:
                        if self.logger:
                            self.logger.info(
                                "[CHEST_OWNERSHIP] Files found",
                                {"count": int(len(chest_ownership_files))},
                            )
                    except Exception:
                        pass
                    # Processar cada arquivo
                    for file_path in chest_ownership_files:
                        self._process_chest_ownership_copy(file_path)
                else:
                    print("CHEST_OWNERSHIP Nenhum arquivo encontrado")
                
                if self.stop_event.wait(self.chest_ownership_copy_interval):
                    break
                
            except Exception as e:
                print(f"ERRO Erro no loop de cópia de chest_ownership: {e}")
                if self.stop_event.wait(self.chest_ownership_copy_interval):
                    break
                import traceback
                traceback.print_exc()
    
    def _process_chest_ownership_copy(self, file_path: str):
        """Copiar chest_ownership para temp, verificar novas linhas, processar e deletar"""
        temp_path = None
        try:
            filename = os.path.basename(file_path)
            
            # 1. Copiar arquivo para temp (SEMPRE copiar, independente de mudanças)
            print(f"CHEST_OWNERSHIP Copiando {filename} para temp...")
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                print(f"ERRO Falha ao copiar {filename} para temp")
                return
            
            print(f"OK {filename} copiado para temp")
            
            # 2. Ler todas as linhas da cópia
            all_lines = self._read_all_lines_from_temp(temp_path)
            if not all_lines:
                print(f"AVISO {filename} sem linhas válidas")
                # Deletar cópia mesmo sem linhas
                self.temp_manager.cleanup_temp_file(temp_path)
                return
            
            # 3. Obter quantidade de linhas já processadas
            last_line_count = self.chest_ownership_last_line_count.get(file_path, 0)
            current_line_count = len(all_lines)
            
            print(f"CHEST_OWNERSHIP {filename}: {current_line_count} linhas totais, {last_line_count} já processadas")
            try:
                if self.logger:
                    self.logger.info(
                        "[CHEST_OWNERSHIP] File stats",
                        {
                            "file": str(filename),
                            "total_lines": int(current_line_count),
                            "previous_lines": int(last_line_count),
                        },
                    )
            except Exception:
                pass
            
            # DEBUG: Verificar se há discrepância (contador diz que processou tudo mas arquivo tem mais linhas)
            # Se o contador está igual ao total mas o veículo não foi registrado, pode ser que o processamento falhou
            # Neste caso, vamos forçar reprocessamento da última linha para garantir
            if current_line_count == last_line_count and current_line_count > 0:
                print(f"CHEST_OWNERSHIP {filename}: AVISO - Contador igual ao total ({current_line_count}), verificando última linha...")
                if all_lines:
                    last_line = all_lines[-1]
                    print(f"CHEST_OWNERSHIP {filename}: Última linha do arquivo: {last_line[:100] if len(last_line) > 100 else last_line}")
                    # Verificar se a última linha parece ser um veículo (contém "ownership claimed" ou "ownership changed")
                    if "ownership" in last_line.lower():
                        print(f"CHEST_OWNERSHIP {filename}: Última linha parece ser um veículo, forçando reprocessamento...")
                        # Reprocessar apenas a última linha para garantir
                        new_lines = [last_line]
                        print(f"CHEST_OWNERSHIP Chamando callback para reprocessar última linha de {filename}")
                        try:
                            self.callback(file_path, new_lines)
                            print(f"CHEST_OWNERSHIP {filename}: Reprocessamento da última linha concluído")
                        except Exception as e:
                            print(f"ERRO Erro ao reprocessar última linha de {filename}: {e}")
                            import traceback
                            traceback.print_exc()
            
            # 4. Se há novas linhas, processar
            if current_line_count > last_line_count:
                # Extrair apenas linhas novas
                new_lines = all_lines[last_line_count:]
                
                print(f"CHEST_OWNERSHIP {filename}: {len(new_lines)} novas linhas detectadas")
                print(f"CHEST_OWNERSHIP {filename}: Primeiras 3 linhas novas: {new_lines[:3] if len(new_lines) >= 3 else new_lines}")
                try:
                    if self.logger:
                        self.logger.info(
                            "[CHEST_OWNERSHIP] New lines detected",
                            {"file": str(filename), "new_lines": int(len(new_lines))},
                        )
                except Exception:
                    pass
                
                if new_lines:
                    # Chamar callback para processar
                    print(f"CHEST_OWNERSHIP Chamando callback para processar {len(new_lines)} novas linhas de {filename}")
                    callback_success = False
                    try:
                        self.callback(file_path, new_lines)
                        callback_success = True
                        print(f"CHEST_OWNERSHIP {filename}: Callback executado com sucesso")
                        try:
                            if self.logger:
                                self.logger.info(
                                    "[CHEST_OWNERSHIP] Callback processed",
                                    {"file": str(filename), "lines": int(len(new_lines))},
                                )
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"ERRO Erro no callback de {filename}: {e}")
                        import traceback
                        traceback.print_exc()
                        callback_success = False
                        try:
                            if self.logger:
                                self.logger.error(
                                    f"[CHEST_OWNERSHIP] Callback error: {e}",
                                    {"file": str(filename)},
                                )
                        except Exception:
                            pass
                    
                    # IMPORTANTE: Só atualizar contador se o callback foi executado sem exceção
                    # Mas isso não garante que o processamento interno foi bem-sucedido
                    # O callback pode ter executado mas não processado (ex: vehicle_processor None)
                    if callback_success:
                        self.chest_ownership_last_line_count[file_path] = current_line_count
                        print(f"CHEST_OWNERSHIP {filename}: Contador atualizado para {current_line_count} linhas processadas")
                    else:
                        print(f"CHEST_OWNERSHIP {filename}: Contador NÃO atualizado devido a erro no callback")
            else:
                print(f"CHEST_OWNERSHIP {filename}: sem novas linhas (já processou todas)")
            
            # 5. Deletar cópia temporária (SEMPRE deletar após processar)
            self.temp_manager.cleanup_temp_file(temp_path)
            temp_path = None
            print(f"OK {filename}: cópia deletada")
            
        except Exception as e:
            print(f"ERRO Erro ao processar cópia de chest_ownership: {e}")
            import traceback
            traceback.print_exc()
            try:
                if self.logger:
                    self.logger.error(
                        f"[CHEST_OWNERSHIP] Copy processing error: {e}",
                        {"file": str(os.path.basename(file_path))},
                    )
            except Exception:
                pass
        finally:
            # Garantir limpeza da cópia
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _find_latest_gameplay_log(self) -> Optional[str]:
        """Encontrar o arquivo gameplay_*.log mais recente pelo timestamp no nome"""
        try:
            if not os.path.exists(self.log_directory):
                return None
            
            gameplay_files = []
            for filename in os.listdir(self.log_directory):
                if filename.startswith('gameplay_') and filename.endswith('.log'):
                    file_path = os.path.join(self.log_directory, filename)
                    if os.path.exists(file_path):
                        gameplay_files.append(file_path)
            
            if not gameplay_files:
                return None
            
            # Extrair timestamp do nome do arquivo
            # Formato: gameplay_YYYYMMDDHHMMSS.log
            def file_key(path: str) -> str:
                name = os.path.basename(path)
                try:
                    # gameplay_20260108043248.log → 20260108043248
                    base = name.split('gameplay_')[1].split('.log')[0]
                    # Remover caracteres não numéricos
                    return ''.join(ch for ch in base if ch.isdigit())
                except Exception:
                    return '0'
            
            latest_file = max(gameplay_files, key=file_key)
            return latest_file
            
        except Exception as e:
            print(f"ERRO Erro ao encontrar arquivo gameplay mais recente: {e}")
            return None
    
    def _get_gameplay_file_status(self, filename: str) -> Optional[Dict[str, Any]]:
        """Obter status do arquivo gameplay na tabela log_files_processed"""
        for attempt in range(self.max_retries):
            try:
                with self._connect_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT file_name, file_path, last_position, last_modified, 
                               lines_processed, status, created_at, updated_at
                        FROM log_files_processed 
                        WHERE file_name = ?
                    ''', (filename,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'file_name': row[0],
                            'file_path': row[1],
                            'last_position': row[2],
                            'last_modified': row[3],
                            'lines_processed': row[4],
                            'status': row[5],
                            'created_at': row[6],
                            'updated_at': row[7]
                        }
                    return None
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO Erro ao obter status do arquivo gameplay: {e}")
                return None
            except Exception as e:
                print(f"ERRO Erro ao obter status do arquivo gameplay: {e}")
                return None
    
    def _update_gameplay_file_status(self, filename: str, file_path: str, 
                                    lines_processed: int, status: str = 'active') -> bool:
        """Atualizar status do arquivo gameplay na tabela log_files_processed"""
        for attempt in range(self.max_retries):
            try:
                with self._connect_db() as conn:
                    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    conn.execute('''
                        INSERT OR REPLACE INTO log_files_processed 
                        (file_name, file_path, last_position, last_modified, 
                         lines_processed, status, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        filename, file_path, file_size, 
                        datetime.now().isoformat(), lines_processed, status
                    ))
                    conn.commit()
                    return True
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO Erro ao atualizar status do arquivo gameplay: {e}")
                return False
            except Exception as e:
                print(f"ERRO Erro ao atualizar status do arquivo gameplay: {e}")
                return False
    
    def _mark_old_gameplay_files_inactive(self, active_filename: str) -> None:
        """Marcar todos os arquivos gameplay_*.log como inactive exceto o ativo"""
        for attempt in range(self.max_retries):
            try:
                with self._connect_db() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT file_name FROM log_files_processed 
                        WHERE file_name LIKE 'gameplay_%' 
                          AND status = 'active'
                          AND file_name != ?
                    """, (active_filename,))
                    
                    old_files = cursor.fetchall()
                
                for (old_filename,) in old_files:
                    old_file_path = os.path.join(self.log_directory, old_filename)
                    old_status = self._get_gameplay_file_status(old_filename)
                    old_lines = old_status['lines_processed'] if old_status else 0
                    
                    self._update_gameplay_file_status(
                        old_filename, old_file_path, old_lines, 'inactive'
                    )
                    print(f"   [INFO] Arquivo gameplay antigo marcado como inactive: {old_filename}")
                return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries - 1:
                    self._sleep_backoff(attempt)
                    continue
                print(f"ERRO Erro ao marcar arquivos gameplay antigos como inactive: {e}")
                import traceback
                traceback.print_exc()
                return
            except Exception as e:
                print(f"ERRO Erro ao marcar arquivos gameplay antigos como inactive: {e}")
                import traceback
                traceback.print_exc()
                return
    
    def _gameplay_copy_loop(self):
        """Loop para copiar gameplay_*.log periodicamente para temp, processar e deletar"""
        print(f"INFO Loop de cópia de gameplay iniciado (intervalo: {self.gameplay_copy_interval}s)")
        while self.running:
            try:
                # 1. Identificar arquivo ativo (mais recente pelo timestamp)
                active_file = self._find_latest_gameplay_log()
                
                if not active_file:
                    print("GAMEPLAY Nenhum arquivo gameplay_*.log encontrado")
                    if self.stop_event.wait(self.gameplay_copy_interval):
                        break
                    continue
                
                active_filename = os.path.basename(active_file)
                
                # 2. Verificar se arquivo ativo mudou
                if active_file != self.current_active_gameplay_file:
                    print(f"GAMEPLAY Arquivo ativo mudou: {active_filename}")
                    
                    # Marcar arquivo anterior como inactive (se existir)
                    if self.current_active_gameplay_file:
                        previous_filename = os.path.basename(self.current_active_gameplay_file)
                        self._mark_old_gameplay_files_inactive(active_filename)
                    
                    # Atualizar referência
                    self.current_active_gameplay_file = active_file
                    
                    # Verificar/criar registro na tabela para novo arquivo
                    file_status = self._get_gameplay_file_status(active_filename)
                    if not file_status:
                        # Criar registro inicial
                        self._update_gameplay_file_status(active_filename, active_file, 0, 'active')
                        print(f"GAMEPLAY Novo arquivo registrado na tabela: {active_filename}")
                    elif file_status['status'] == 'inactive':
                        # Reativar arquivo (pode ter sido reaberto pelo servidor)
                        old_lines = file_status['lines_processed']
                        self._update_gameplay_file_status(active_filename, active_file, old_lines, 'active')
                        print(f"GAMEPLAY Arquivo reativado: {active_filename} (já tinha {old_lines} linhas processadas)")
                
                # 3. Processar apenas arquivo ativo
                self._process_gameplay_copy(active_file)
                
                if self.stop_event.wait(self.gameplay_copy_interval):
                    break
                
            except Exception as e:
                print(f"ERRO Erro no loop de cópia de gameplay: {e}")
                if self.stop_event.wait(self.gameplay_copy_interval):
                    break
                import traceback
                traceback.print_exc()
    
    def _process_gameplay_copy(self, file_path: str):
        """Copiar gameplay para temp, verificar novas linhas, processar e deletar"""
        temp_path = None
        try:
            filename = os.path.basename(file_path)
            
            # 1. Verificar status na tabela
            file_status = self._get_gameplay_file_status(filename)
            if not file_status:
                # Criar registro se não existe
                self._update_gameplay_file_status(filename, file_path, 0, 'active')
                file_status = {'lines_processed': 0, 'status': 'active'}

            # 2. Se arquivo está 'inactive', ainda assim verificar se cresceu.
            # Se houver linhas novas, reativar e processar normalmente.
            is_inactive = file_status.get('status') != 'active'
            
            # 3. Copiar arquivo para temp (SEMPRE copiar, independente de mudanças)
            print(f"GAMEPLAY Copiando {filename} para temp...")
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                print(f"ERRO Falha ao copiar {filename} para temp")
                return
            
            print(f"OK {filename} copiado para temp")
            
            # 4. Ler todas as linhas da cópia
            all_lines = self._read_all_lines_from_temp(temp_path)
            if not all_lines:
                print(f"AVISO {filename} sem linhas válidas")
                # Deletar cópia mesmo sem linhas
                self.temp_manager.cleanup_temp_file(temp_path)
                return
            
            # 5. Obter quantidade de linhas já processadas da tabela
            last_line_count = file_status.get('lines_processed', 0)
            current_line_count = len(all_lines)

            if not is_inactive:
                print(f"GAMEPLAY {filename}: {current_line_count} linhas totais, {last_line_count} já processadas")
            
            # 6. Se há novas linhas, processar
            if current_line_count > last_line_count:
                if is_inactive:
                    try:
                        self._update_gameplay_file_status(filename, file_path, last_line_count, 'active')
                        file_status['status'] = 'active'
                        is_inactive = False
                        print(f"GAMEPLAY Arquivo reativado automaticamente: {filename} (novas linhas detectadas)")
                    except Exception:
                        pass
                # Extrair apenas linhas novas
                new_lines = all_lines[last_line_count:]
                
                print(f"GAMEPLAY {filename}: {len(new_lines)} novas linhas detectadas")
                if len(new_lines) <= 3:
                    print(f"GAMEPLAY {filename}: Primeiras linhas novas: {new_lines}")
                else:
                    print(f"GAMEPLAY {filename}: Primeiras 3 linhas novas: {new_lines[:3]}")
                
                if new_lines:
                    # Chamar callback para processar
                    print(f"GAMEPLAY Chamando callback para processar {len(new_lines)} novas linhas de {filename}")
                    callback_success = False
                    try:
                        self.callback(file_path, new_lines)
                        callback_success = True
                        print(f"GAMEPLAY {filename}: Callback executado com sucesso")
                    except Exception as e:
                        print(f"ERRO Erro no callback de {filename}: {e}")
                        import traceback
                        traceback.print_exc()
                        callback_success = False
                    
                    # IMPORTANTE: Só atualizar contador na tabela se o callback foi executado sem exceção
                    if callback_success:
                        # Atualizar tabela com novo contador
                        self._update_gameplay_file_status(filename, file_path, current_line_count, 'active')
                        print(f"GAMEPLAY {filename}: Contador atualizado na tabela para {current_line_count} linhas processadas")
                    else:
                        print(f"GAMEPLAY {filename}: Contador NÃO atualizado devido a erro no callback")
            else:
                if not is_inactive:
                    print(f"GAMEPLAY {filename}: sem novas linhas (já processou todas)")
            
            # 7. Deletar cópia temporária (SEMPRE deletar após processar)
            self.temp_manager.cleanup_temp_file(temp_path)
            temp_path = None
            print(f"OK {filename}: cópia deletada")
            
        except Exception as e:
            print(f"ERRO Erro ao processar cópia de gameplay: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Garantir limpeza da cópia
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _economy_copy_loop(self):
        """Loop para copiar economy_*.log periodicamente para temp, processar e deletar"""
        print(f"INFO Loop de cópia de economy iniciado (intervalo: {self.economy_copy_interval}s)")
        while self.running:
            try:
                # Encontrar todos os arquivos economy_*.log
                economy_files = []
                try:
                    for filename in os.listdir(self.log_directory):
                        if filename.startswith('economy_') and filename.endswith('.log'):
                            file_path = os.path.join(self.log_directory, filename)
                            if os.path.exists(file_path):
                                economy_files.append(file_path)
                except Exception as e:
                    print(f"ERRO Erro ao listar arquivos economy: {e}")
                    if self.stop_event.wait(self.economy_copy_interval):
                        break
                    continue
                
                if economy_files:
                    print(f"ECONOMY Copiando {len(economy_files)} arquivo(s) para temp...")
                    # Processar cada arquivo
                    for file_path in economy_files:
                        self._process_economy_copy(file_path)
                else:
                    print("ECONOMY Nenhum arquivo encontrado")
                
                if self.stop_event.wait(self.economy_copy_interval):
                    break
                
            except Exception as e:
                print(f"ERRO Erro no loop de cópia de economy: {e}")
                if self.stop_event.wait(self.economy_copy_interval):
                    break
                import traceback
                traceback.print_exc()
    
    def _process_economy_copy(self, file_path: str):
        """Copiar economy para temp, processar arquivo completo e deletar"""
        temp_path = None
        try:
            filename = os.path.basename(file_path)
            
            # 1. Copiar arquivo para temp (SEMPRE copiar, independente de mudanças)
            print(f"ECONOMY Copiando {filename} para temp...")
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                print(f"ERRO Falha ao copiar {filename} para temp")
                return
            
            print(f"OK {filename} copiado para temp")
            
            # 2. Ler todas as linhas da cópia para verificar se há novas linhas
            all_lines = self._read_all_lines_from_temp(temp_path)
            if not all_lines:
                print(f"AVISO {filename} sem linhas válidas")
                # Deletar cópia mesmo sem linhas
                self.temp_manager.cleanup_temp_file(temp_path)
                return
            
            # 3. Obter quantidade de linhas já processadas
            last_line_count = self.economy_last_line_count.get(file_path, 0)
            current_line_count = len(all_lines)
            
            print(f"ECONOMY {filename}: {current_line_count} linhas totais, {last_line_count} já processadas")
            
            # 4. Se há novas linhas, processar arquivo completo (economy precisa de contexto completo)
            if current_line_count > last_line_count:
                # Para economy, processamos o arquivo completo via callback
                # O callback para economy chama _process_economy_file que espera o file_path
                # Como já copiamos para temp, passamos o temp_path para evitar cópia duplicada
                print(f"ECONOMY {filename}: {current_line_count - last_line_count} novas linhas detectadas, processando arquivo completo...")
                
                # Chamar callback com o temp_path (já é uma cópia temporária)
                # O _process_economy_file vai processar diretamente sem copiar novamente
                callback_success = False
                try:
                    # Passar temp_path como file_path e lista vazia (o processador lê o arquivo completo)
                    self.callback(temp_path, [])
                    callback_success = True
                    print(f"ECONOMY {filename}: Callback executado com sucesso")
                except Exception as e:
                    print(f"ERRO Erro no callback de {filename}: {e}")
                    import traceback
                    traceback.print_exc()
                    callback_success = False
                
                # IMPORTANTE: Só atualizar contador se o callback foi executado sem exceção
                if callback_success:
                    self.economy_last_line_count[file_path] = current_line_count
                    print(f"ECONOMY {filename}: Contador atualizado para {current_line_count} linhas processadas")
                else:
                    print(f"ECONOMY {filename}: Contador NÃO atualizado devido a erro no callback")
            else:
                print(f"ECONOMY {filename}: sem novas linhas (já processou todas)")
            
            # 5. Deletar cópia temporária (SEMPRE deletar após processar)
            self.temp_manager.cleanup_temp_file(temp_path)
            temp_path = None
            print(f"OK {filename}: cópia deletada")
            
        except Exception as e:
            print(f"ERRO Erro ao processar cópia de economy: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Garantir limpeza da cópia
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def _check_file_changes(self, file_path: str):
        """Verificar mudanças em arquivo específico"""
        try:
            if not os.path.exists(file_path):
                return
            
            current_size = os.path.getsize(file_path)
            last_position = self.file_positions.get(file_path, 0)
            
            if current_size > last_position:
                # Arquivo foi modificado
                print(f"DEBUG: Polling detectou mudança em: {os.path.basename(file_path)}")
                self._process_file_changes(file_path)
            elif current_size > 0 and last_position == 0:
                # Arquivo existe mas não foi processado ainda
                # logger.debug(f"Polling detectou arquivo não processado: {os.path.basename(file_path)}")
                self._process_file_changes(file_path)
                
        except Exception as e:
                print(f"ERRO Erro ao verificar mudanças no arquivo: {e}")
    
    def _process_file_changes(self, file_path: str):
        """Processar mudanças em arquivo"""
        try:
            with self.lock:
                filename = os.path.basename(file_path)
                current_position = self.file_positions.get(file_path, 0)

                # Se um NOVO arquivo login_*.log foi criado, priorizar ele e resetar posição
                if filename.startswith('login_') and filename.endswith('.log'):
                    # Descobrir qual é o login_*.log mais recente pelo nome (timestamp)
                    login_files = [
                        os.path.join(self.log_directory, f)
                        for f in os.listdir(self.log_directory)
                        if f.startswith('login_') and f.endswith('.log')
                    ]
                    if login_files:
                        def file_key(path: str) -> str:
                            name = os.path.basename(path)
                            try:
                                base = name.split('login_')[1].split('.log')[0]
                            except Exception:
                                base = name
                            return ''.join(ch for ch in base if ch.isdigit())
                        latest_login = max(login_files, key=file_key)
                        # Se o arquivo atual não é o mais recente, não processar este e resetar posição do novo
                        if os.path.abspath(file_path) != os.path.abspath(latest_login):
                            # Garante que sempre seguimos o arquivo mais novo
                            file_path = latest_login
                            filename = os.path.basename(file_path)
                            current_position = self.file_positions.get(file_path, 0)
                
                # Verificar se arquivo existe e tem conteúdo
                if not os.path.exists(file_path):
                    return
                
                file_size = os.path.getsize(file_path)
                if file_size <= current_position:
                    return
                
                # Ler apenas linhas novas
                new_lines, new_position = self._read_new_lines(file_path, current_position)
                if new_lines:
                    # Atualizar posição com base no que realmente foi lido
                    self.file_positions[file_path] = new_position
                    
                    # Chamar callback com dados
                    self.callback(file_path, new_lines)
                    
        except Exception as e:
            print(f"ERRO Erro ao processar mudanças no arquivo: {e}")
    
    def _read_new_lines(self, file_path: str, start_position: int) -> tuple[List[str], int]:
        """Ler apenas linhas novas do arquivo usando arquivo temporário para evitar bloqueios"""
        temp_path = None
        try:
            # Criar cópia temporária para evitar bloqueio quando SCUM está escrevendo
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                return [], int(start_position)

            # Leitura robusta: offset em bytes (binário) + decode
            try:
                with open(temp_path, 'rb') as f:
                    temp_size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                    safe_start = min(max(0, int(start_position)), int(temp_size))
                    f.seek(safe_start)
                    data = f.read()
            except Exception:
                return [], int(start_position)

            if not data:
                return [], int(start_position)

            # Atualizar posição pelo que foi realmente lido do snapshot
            new_position = int(start_position) + len(data)

            text = None
            try:
                # UTF-8 com BOM
                if data.startswith(b"\xef\xbb\xbf"):
                    text = data.decode('utf-8-sig', errors='ignore')
                # UTF-16 BOMs
                elif data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
                    text = data.decode('utf-16', errors='ignore')
                else:
                    # Heurística: muitos NULs sugere UTF-16LE
                    sample = data[:512]
                    if sample and (sample.count(b"\x00") / max(1, len(sample))) > 0.10:
                        if len(data) % 2 == 1:
                            data = data[:-1]
                        text = data.decode('utf-16le', errors='ignore')
                    else:
                        text = data.decode('utf-8', errors='ignore')
            except Exception:
                text = None

            if not text:
                return [], int(start_position)

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return lines, int(new_position)
                
        except PermissionError:
            # Arquivo está bloqueado - silenciosamente ignorar (não é erro crítico)
            return [], int(start_position)
        except Exception as e:
            # Apenas logar se não for erro de permissão (para não poluir console)
            if "Permission denied" not in str(e) and "Errno 13" not in str(e):
                print(f"ERRO Erro ao ler linhas do arquivo: {e}")
            return [], int(start_position)
        finally:
            # Limpar arquivo temporário
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
    
    def get_file_position(self, file_path: str) -> int:
        """Obter posição atual no arquivo"""
        with self.lock:
            return self.file_positions.get(file_path, 0)
    
    def set_file_position(self, file_path: str, position: int):
        """Definir posição no arquivo"""
        with self.lock:
            self.file_positions[file_path] = position
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Obter status do monitoramento"""
        return {
            'running': self.running,
            'log_directory': self.log_directory,
            'files_tracked': len(self.file_positions),
            'file_positions': dict(self.file_positions)
        }

class LogFileScanner:
    """Scanner para processar arquivos existentes"""
    
    def __init__(self, log_directory: str):
        self.log_directory = log_directory
    
    def scan_existing_files(self) -> List[str]:
        """Escanear arquivos de log existentes"""
        log_files = []
        
        try:
            for filename in os.listdir(self.log_directory):
                if (filename.startswith('login_') or filename.startswith('chest_ownership_') or 
                    filename.startswith('chat_') or filename.startswith('gameplay_') or 
                    filename.startswith('admin_') or filename.startswith('vehicle_destruction_') or 
                    filename.startswith('kill_') or filename.startswith('famepoints_') or
                    filename.startswith('economy_')) and filename.endswith('.log'):
                    file_path = os.path.join(self.log_directory, filename)
                    log_files.append(file_path)
            
            # logger.debug(f"Arquivos de log encontrados: {len(log_files)}")
            for file_path in log_files:
                print(f"   - {os.path.basename(file_path)}")
                
        except Exception as e:
            print(f"ERRO Erro ao escanear arquivos: {e}")
        
        return log_files
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Obter informações do arquivo"""
        try:
            stat = os.stat(file_path)
            return {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_size': stat.st_size,
                'last_modified': datetime.fromtimestamp(stat.st_mtime),
                'created_at': datetime.fromtimestamp(stat.st_ctime)
            }
        except Exception as e:
            print(f"ERRO Erro ao obter informações do arquivo: {e}")
            return {}
    
    def read_file_lines(self, file_path: str, start_line: int = 0, max_lines: int = None) -> List[str]:
        """Ler linhas do arquivo usando arquivo temporário para evitar bloqueios"""
        temp_path = None
        try:
            # Criar cópia temporária para evitar bloqueio quando SCUM está escrevendo
            temp_path = self.temp_manager.create_temp_copy(file_path)
            if not temp_path:
                return []
            
            # Tentar UTF-16LE primeiro (padrão do SCUM)
            try:
                with open(temp_path, 'r', encoding='utf-16le') as f:
                    lines = f.readlines()
                    
                    # Aplicar filtros
                    if start_line > 0:
                        lines = lines[start_line:]
                    
                    if max_lines:
                        lines = lines[:max_lines]
                    
                    return [line.strip() for line in lines if line.strip()]
            except UnicodeDecodeError:
                # Fallback para UTF-8 se UTF-16LE falhar
                with open(temp_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                    # Aplicar filtros
                    if start_line > 0:
                        lines = lines[start_line:]
                    
                    if max_lines:
                        lines = lines[:max_lines]
                    
                    return [line.strip() for line in lines if line.strip()]
                
        except PermissionError:
            # Arquivo está bloqueado - silenciosamente ignorar (não é erro crítico)
            return []
        except Exception as e:
            # Apenas logar se não for erro de permissão (para não poluir console)
            if "Permission denied" not in str(e) and "Errno 13" not in str(e):
                print(f"ERRO Erro ao ler linhas do arquivo: {e}")
            return []
        finally:
            # Limpar arquivo temporário
            if temp_path:
                self.temp_manager.cleanup_temp_file(temp_path)
