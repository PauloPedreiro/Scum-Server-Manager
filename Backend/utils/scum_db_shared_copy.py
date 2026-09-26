"""
Gerenciador de cópia compartilhada do SCUM.db para leituras.

Cria uma única cópia temporária do SCUM.db que pode ser reutilizada por múltiplos serviços,
reduzindo a carga no disco e melhorando a performance. A cópia é recriada quando:
- Atinge a idade máxima configurada (max_copy_age_seconds)
- Não há mais referências ativas (reference counting)

Implementação singleton para garantir uma única instância global.
"""

import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

from utils.logger import StructuredLogger


class ScumDbSharedCopyManager:
    """
    Gerenciador singleton para cópia compartilhada do SCUM.db.

    Mantém uma única cópia temporária do SCUM.db que pode ser reutilizada por
    múltiplos serviços. Usa reference counting para gerenciar o ciclo de vida
    da cópia.
    """

    _instance: Optional["ScumDbSharedCopyManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Implementação singleton thread-safe."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Inicializar o gerenciador (chamado apenas uma vez)."""
        if self._initialized:
            return

        self._initialized = True
        self.logger = StructuredLogger()

        # Estado da cópia
        self._copy_path: Optional[str] = None
        self._copy_created_at: Optional[float] = None
        self._reference_count: int = 0
        self._copy_lock = threading.RLock()  # Reentrant lock para nested calls

        # Pausa (maintenance window) para bloquear leituras durante restart.
        # Objetivo: evitar que o backend segure handles no SCUM.db enquanto o serviço para/inicia.
        self._pause_until_ts: float = 0.0
        self._pause_cond = threading.Condition()

        # Configuração padrão (será sobrescrita por configure())
        self.enabled: bool = True
        self.temp_dir: str = "data/temp"
        self.max_copy_age_seconds: int = 120  # 2 minutos
        self.restart_pause_seconds: int = 120  # pausa durante restart (segundos)
        self.cleanup_orphaned_copies: bool = True
        self.max_orphan_age_hours: int = 1
        self.scum_db_path: Optional[str] = None

        # Estatísticas
        self.stats: Dict[str, Any] = {
            "copies_created": 0,
            "copies_reused": 0,
            "copies_refreshed": 0,
            "errors": 0,
        }

    def configure(
        self, config: Dict[str, Any], scum_db_path: Optional[str] = None
    ) -> None:
        """
        Configurar o gerenciador com parâmetros do config.json.

        Args:
            config: Dicionário com configurações de scum_db_shared_copy
            scum_db_path: Caminho para o SCUM.db original
        """
        copy_config = config.get("scum_db_shared_copy", {})

        self.enabled = copy_config.get("enabled", True)
        self.temp_dir = copy_config.get("temp_dir", "data/temp")
        self.max_copy_age_seconds = copy_config.get("max_copy_age_seconds", 120)
        self.restart_pause_seconds = int(copy_config.get("restart_pause_seconds", 120) or 120)
        self.cleanup_orphaned_copies = copy_config.get("cleanup_orphaned_copies", True)
        self.max_orphan_age_hours = copy_config.get("max_orphan_age_hours", 1)

        if scum_db_path:
            self.scum_db_path = scum_db_path

        # Garantir que o diretório temporário existe
        os.makedirs(self.temp_dir, exist_ok=True)

        # Limpar cópias órfãs na inicialização
        if self.cleanup_orphaned_copies:
            self._cleanup_orphaned_copies()

        self.logger.info(
            "ScumDbSharedCopyManager configurado",
            {
                "enabled": self.enabled,
                "temp_dir": self.temp_dir,
                "max_copy_age_seconds": self.max_copy_age_seconds,
                "restart_pause_seconds": self.restart_pause_seconds,
                "scum_db_path": self.scum_db_path,
            },
        )

    def _get_copy_path(self) -> str:
        """Obter caminho para a cópia temporária."""
        return os.path.join(self.temp_dir, "SCUM.db.temp")

    def pause_for(self, seconds: float, *, reason: str = "") -> None:
        """Pausar o acesso à cópia compartilhada por um período.

        Durante a pausa, `get_copy_connection()` irá aguardar até o fim da janela.
        """
        until_ts = time.time() + max(0.0, float(seconds))
        with self._pause_cond:
            # Se já existe uma pausa maior, não encurtar.
            if until_ts > self._pause_until_ts:
                self._pause_until_ts = until_ts
            try:
                self.logger.warn(
                    "ScumDbSharedCopyManager pausado",
                    {
                        "seconds": float(seconds),
                        "reason": reason,
                        "pause_until": self._pause_until_ts,
                    },
                )
            except Exception:
                pass
            self._pause_cond.notify_all()

    def resume(self) -> None:
        """Retomar imediatamente o acesso à cópia compartilhada."""
        with self._pause_cond:
            self._pause_until_ts = 0.0
            try:
                self.logger.info("ScumDbSharedCopyManager retomado")
            except Exception:
                pass
            self._pause_cond.notify_all()

    def _wait_if_paused(self) -> None:
        """Bloquear enquanto estiver em janela de pausa."""
        while True:
            with self._pause_cond:
                now = time.time()
                remaining = self._pause_until_ts - now
                if remaining <= 0:
                    return
                # Esperar no máximo 5s por iteração para permitir logs/notify.
                wait_s = min(remaining, 5.0)
            # Esperar fora do lock de pausa para não segurar o condition.
            # (o Condition.wait precisa ser feito com o lock; então reentramos)
            with self._pause_cond:
                self._pause_cond.wait(timeout=wait_s)

    def _is_copy_valid(self) -> bool:
        """Verificar se a cópia atual é válida (existe e não está expirada)."""
        if not self._copy_path or not os.path.exists(self._copy_path):
            return False

        if self._copy_created_at is None:
            return False

        age_seconds = time.time() - self._copy_created_at
        return age_seconds < self.max_copy_age_seconds

    def _create_copy(self) -> bool:
        """
        Criar uma nova cópia do SCUM.db.

        Returns:
            True se a cópia foi criada com sucesso, False caso contrário
        """
        if not self.scum_db_path or not os.path.exists(self.scum_db_path):
            self.logger.error(
                "SCUM.db não encontrado para criar cópia",
                {"scum_db_path": self.scum_db_path},
            )
            return False

        copy_path = self._get_copy_path()

        try:
            # Remover cópia antiga se existir
            if os.path.exists(copy_path):
                try:
                    os.remove(copy_path)
                except Exception as e:
                    self.logger.warning(
                        "Erro ao remover cópia antiga",
                        {"error": str(e), "copy_path": copy_path},
                    )

            # Criar nova cópia
            start_time = time.time()
            shutil.copy2(self.scum_db_path, copy_path)
            copy_time = time.time() - start_time

            self._copy_path = copy_path
            self._copy_created_at = time.time()
            self.stats["copies_created"] += 1

            file_size_mb = os.path.getsize(copy_path) / (1024 * 1024)

            self.logger.info(
                "Cópia do SCUM.db criada",
                {
                    "copy_path": copy_path,
                    "size_mb": round(file_size_mb, 2),
                    "copy_time_seconds": round(copy_time, 2),
                },
            )

            return True

        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(
                "Erro ao criar cópia do SCUM.db",
                {"error": str(e), "scum_db_path": self.scum_db_path},
            )
            return False

    def _cleanup_orphaned_copies(self) -> None:
        """Limpar cópias órfãs no diretório temporário."""
        if not os.path.exists(self.temp_dir):
            return

        try:
            max_age_seconds = self.max_orphan_age_hours * 3600
            current_time = time.time()

            for filename in os.listdir(self.temp_dir):
                if filename.startswith("SCUM.db") and filename.endswith(".temp"):
                    filepath = os.path.join(self.temp_dir, filename)

                    try:
                        file_age = current_time - os.path.getmtime(filepath)

                        # Remover se:
                        # 1. Não é a cópia atual E está muito antigo (cópia órfã)
                        # 2. É a cópia atual MAS está muito antigo (> max_orphan_age_hours) E não há referências
                        should_remove = False
                        reason = ""

                        if filepath != self._copy_path:
                            # Cópia órfã (não é a atual)
                            if file_age > max_age_seconds:
                                should_remove = True
                                reason = "cópia órfã"
                        elif filepath == self._copy_path:
                            # É a cópia atual, mas está muito antiga e sem referências
                            if (
                                file_age > max_age_seconds
                                and self._reference_count == 0
                            ):
                                should_remove = True
                                reason = "cópia atual expirada sem referências"
                                # Limpar estado interno também
                                self._copy_path = None
                                self._copy_created_at = None

                        if should_remove:
                            os.remove(filepath)
                            self.logger.info(
                                f"Cópia removida ({reason})",
                                {
                                    "filepath": filepath,
                                    "age_hours": round(file_age / 3600, 2),
                                },
                            )
                    except Exception as e:
                        self.logger.warning(
                            "Erro ao processar arquivo temporário",
                            {"filepath": filepath, "error": str(e)},
                        )

        except Exception as e:
            self.logger.warning(
                "Erro ao limpar cópias órfãs",
                {"error": str(e), "temp_dir": self.temp_dir},
            )

    def _acquire_copy(self) -> Optional[str]:
        """
        Adquirir acesso à cópia (incrementa reference count).

        Returns:
            Caminho para a cópia se disponível, None caso contrário

        Raises:
            RuntimeError: Se não está habilitado ou falhou ao criar cópia
        """
        with self._copy_lock:
            # Se não está habilitado, lançar erro (sem fallback)
            if not self.enabled:
                raise RuntimeError(
                    "ScumDbSharedCopyManager não está habilitado. "
                    "Configure 'scum_db_shared_copy.enabled = true' no config.json"
                )

            # Verificar se precisa criar/recriar cópia
            if not self._is_copy_valid():
                # Se há referências ativas, marcar para refresh após liberação
                if self._reference_count > 0:
                    # Não pode recriar agora, mas a cópia está expirada
                    # Retornar a cópia atual mesmo expirada (melhor que nada)
                    if self._copy_path and os.path.exists(self._copy_path):
                        self.stats["copies_reused"] += 1
                        self._reference_count += 1
                        return self._copy_path

                # Criar nova cópia
                if not self._create_copy():
                    # Sem fallback - sempre falhar se não conseguir criar cópia
                    raise RuntimeError(
                        "Falha ao criar cópia do SCUM.db. "
                        "Verifique se o SCUM.db existe e se há permissões de leitura/escrita."
                    )

            # Incrementar reference count
            self._reference_count += 1

            # Se reutilizou cópia válida, incrementar estatística
            if self._reference_count > 1:
                self.stats["copies_reused"] += 1

            return self._copy_path

    def _release_copy(self) -> None:
        """Liberar acesso à cópia (decrementa reference count)."""
        with self._copy_lock:
            if self._reference_count > 0:
                self._reference_count -= 1

                # Se não há mais referências e a cópia está expirada, remover
                if self._reference_count == 0:
                    if self._copy_path and os.path.exists(self._copy_path):
                        # Verificar se está expirada
                        if not self._is_copy_valid():
                            try:
                                os.remove(self._copy_path)
                                self.logger.debug(
                                    "Cópia expirada removida",
                                    {"copy_path": self._copy_path},
                                )
                            except Exception as e:
                                self.logger.warning(
                                    "Erro ao remover cópia expirada",
                                    {"error": str(e), "copy_path": self._copy_path},
                                )

                            self._copy_path = None
                            self._copy_created_at = None

    @contextmanager
    def get_copy_connection(self, scum_db_path: Optional[str] = None):
        """
        Context manager para obter conexão à cópia compartilhada.

        Args:
            scum_db_path: Caminho para o SCUM.db (usado apenas se manager não foi configurado)

        Yields:
            sqlite3.Connection: Conexão à cópia compartilhada

        Raises:
            RuntimeError: Se não conseguir criar ou acessar a cópia compartilhada
        """
        # Se estiver pausado (janela de restart/manutenção), aguardar.
        self._wait_if_paused()

        # Adquirir cópia (lança erro se falhar - sem fallback)
        copy_path = self._acquire_copy()

        if copy_path is None:
            raise RuntimeError(
                "Falha ao adquirir cópia compartilhada do SCUM.db. "
                "Verifique se o ScumDbSharedCopyManager está configurado corretamente."
            )

        # Usar cópia compartilhada (única opção)
        conn = None
        try:
            try:
                self.logger.info(
                    "Usando copia compartilhada do SCUM.db (conexao aberta)",
                    {"copy_path": copy_path},
                )
            except Exception:
                pass
            conn = sqlite3.connect(copy_path, timeout=5.0)
            conn.execute("PRAGMA read_uncommitted=1")
            yield conn
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            self._release_copy()

    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do gerenciador."""
        with self._copy_lock:
            return {
                **self.stats,
                "current_copy_path": self._copy_path,
                "copy_age_seconds": (
                    round(time.time() - self._copy_created_at, 2)
                    if self._copy_created_at
                    else None
                ),
                "reference_count": self._reference_count,
                "copy_valid": self._is_copy_valid(),
            }


# Instância global singleton
_shared_copy_manager = ScumDbSharedCopyManager()


def get_shared_copy_manager() -> ScumDbSharedCopyManager:
    """Obter instância singleton do gerenciador."""
    return _shared_copy_manager
