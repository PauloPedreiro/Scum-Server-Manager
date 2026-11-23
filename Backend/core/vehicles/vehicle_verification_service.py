"""
Serviço de Verificação Periódica de Veículos
Verifica se os veículos registrados no SSM.db ainda existem no SCUM.db
"""

import threading
import time
import schedule
from datetime import datetime
from typing import Dict, Any, Optional
from utils.logger import StructuredLogger


class VehicleVerificationService:
    """Serviço para verificação periódica de existência e sincronização de localização de veículos"""

    def __init__(
        self,
        log_processor,
        enabled: bool = True,
        verification_interval_hours: int = 24,
        location_sync_interval_minutes: int = 5,
        logger: Optional[StructuredLogger] = None,
    ):
        """
        Inicializar serviço de verificação de veículos

        Args:
            log_processor: Instância do LogProcessor (deve ter vehicle_processor e db_manager)
            enabled: Se o serviço está habilitado
            verification_interval_hours: Intervalo entre verificações em horas (padrão: 24)
            location_sync_interval_minutes: Intervalo de sincronização das coordenadas atuais em minutos (padrão: 5)
            logger: Logger estruturado (opcional)
        """
        self.log_processor = log_processor
        self.enabled = enabled
        self.verification_interval_hours = verification_interval_hours
        self.location_sync_interval_minutes = max(1, int(location_sync_interval_minutes or 5))
        self.logger = logger or StructuredLogger()

        self.scheduler = schedule.Scheduler()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False
        self.last_verification: Optional[datetime] = None
        self.last_location_sync: Optional[datetime] = None
        self.last_result: Optional[Dict[str, Any]] = None

    def sync_active_vehicle_locations(self) -> Dict[str, Any]:
        """Sincronizar coordenadas atuais (table entity do SCUM.db) dos veículos ativos."""
        try:
            if not self.log_processor or not self.log_processor.vehicle_processor:
                return {
                    "success": False,
                    "error": "VehicleProcessor não inicializado",
                    "timestamp": datetime.now().isoformat(),
                }

            active_ids = self.log_processor.db_manager.get_active_vehicle_entity_ids()
            if not active_ids:
                self.last_location_sync = datetime.now()
                return {
                    "success": True,
                    "total_active": 0,
                    "updated": 0,
                    "timestamp": self.last_location_sync.isoformat(),
                }

            live_locations = (
                self.log_processor.vehicle_processor.get_vehicles_live_locations_batch(
                    active_ids
                )
            )
            updated_count = 0
            if live_locations:
                updated_count = (
                    self.log_processor.db_manager.update_vehicles_locations_batch(
                        live_locations
                    )
                )

            self.last_location_sync = datetime.now()
            return {
                "success": True,
                "total_active": len(active_ids),
                "found_in_scum_db": len(live_locations),
                "updated": updated_count,
                "timestamp": self.last_location_sync.isoformat(),
            }
        except Exception as e:
            self.logger.error(
                f"Erro na sincronização de localização dos veículos: {e}",
                {"error": str(e)},
            )
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def verify_vehicles(self) -> Dict[str, Any]:
        """
        Executar verificação de todos os veículos

        Returns:
            Dicionário com resultado da verificação
        """
        try:
            if not self.log_processor or not self.log_processor.vehicle_processor:
                return {
                    "success": False,
                    "error": "VehicleProcessor não inicializado",
                    "timestamp": datetime.now().isoformat(),
                }

            self.logger.info("Iniciando verificação periódica de veículos...")

            # Obter todos os vehicle_entity_ids do banco
            vehicle_ids = self.log_processor.db_manager.get_all_vehicle_entity_ids()

            if not vehicle_ids:
                result = {
                    "success": True,
                    "message": "Nenhum veículo encontrado para verificar",
                    "total_checked": 0,
                    "existing": 0,
                    "not_found": 0,
                    "updated": 0,
                    "timestamp": datetime.now().isoformat(),
                }
                self.last_result = result
                self.last_verification = datetime.now()
                self.logger.info("Verificação concluída: nenhum veículo para verificar")
                return result

            self.logger.info(
                f"Iniciando verificação de {len(vehicle_ids)} veículos...",
                {"total_vehicles": len(vehicle_ids)},
            )

            # Verificar existência em lote
            existence_map = self.log_processor.vehicle_processor.check_vehicles_batch(
                vehicle_ids
            )

            # Separar veículos que não existem e os que existem (para atualizar coordenadas atuais)
            existing_ids = [int(vid) for vid, exists in existence_map.items() if exists]
            not_found_vehicles = {
                vid: 2  # Status 2 = Desaparecido (não encontrado no SCUM.db)
                for vid, exists in existence_map.items()
                if not exists
            }

            # Atualizar status dos veículos que não existem
            updated_count = 0
            if not_found_vehicles:
                updated_count = (
                    self.log_processor.db_manager.update_vehicles_status_batch(
                        not_found_vehicles
                    )
                )

            # Aproveitar verificação para sincronizar coordenadas atuais dos veículos existentes
            locations_updated_count = 0
            if existing_ids and hasattr(
                self.log_processor.vehicle_processor, "get_vehicles_live_locations_batch"
            ):
                live_locations = (
                    self.log_processor.vehicle_processor.get_vehicles_live_locations_batch(
                        existing_ids
                    )
                )
                if live_locations:
                    locations_updated_count = (
                        self.log_processor.db_manager.update_vehicles_locations_batch(
                            live_locations
                        )
                    )
                    self.last_location_sync = datetime.now()

            existing_count = len(existing_ids)
            not_found_count = len(not_found_vehicles)

            result = {
                "success": True,
                "message": f"Verificação concluída: {existing_count} veículos existem, {not_found_count} não encontrados",
                "total_checked": len(vehicle_ids),
                "existing": existing_count,
                "not_found": not_found_count,
                "updated": updated_count,
                "locations_updated": locations_updated_count,
                "not_found_vehicle_ids": list(not_found_vehicles.keys()),
                "timestamp": datetime.now().isoformat(),
            }

            self.last_result = result
            self.last_verification = datetime.now()

            self.logger.info(
                "Verificação periódica de veículos concluída",
                {
                    "total_checked": len(vehicle_ids),
                    "existing": existing_count,
                    "not_found": not_found_count,
                    "updated": updated_count,
                },
            )

            return result

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            self.logger.error(
                f"Erro na verificação periódica de veículos: {e}", {"error": str(e)}
            )
            return error_result

    def start(self) -> Dict[str, Any]:
        """
        Iniciar serviço de verificação periódica

        Returns:
            Dicionário com resultado da inicialização
        """
        if not self.enabled:
            return {
                "success": False,
                "message": "Serviço de verificação de veículos desabilitado",
                "status": "disabled",
            }

        if self.is_running:
            return {
                "success": False,
                "message": "Serviço de verificação de veículos já está em execução",
                "status": "already_running",
            }

        try:
            # Executar primeira verificação imediatamente
            self.logger.info("Executando verificação inicial de veículos...")
            self.verify_vehicles()

            # Agendar próximas execuções
            self.scheduler.clear()
            self.scheduler.every(self.verification_interval_hours).hours.do(
                self.verify_vehicles
            )
            self.scheduler.every(self.location_sync_interval_minutes).minutes.do(
                self.sync_active_vehicle_locations
            )

            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()
            self.is_running = True

            self.logger.info(
                "VehicleVerificationService iniciado",
                {
                    "verification_interval_hours": self.verification_interval_hours,
                    "location_sync_interval_minutes": self.location_sync_interval_minutes,
                    "next_verification_in_hours": self.verification_interval_hours,
                },
            )

            return {
                "success": True,
                "message": "Serviço de verificação de veículos iniciado",
                "status": "started",
                "verification_interval_hours": self.verification_interval_hours,
                "location_sync_interval_minutes": self.location_sync_interval_minutes,
            }

        except Exception as e:
            self.logger.error(
                "Erro ao iniciar VehicleVerificationService", {"error": str(e)}
            )
            return {
                "success": False,
                "message": f"Erro ao iniciar serviço: {e}",
                "status": "error",
            }

    def stop(self) -> Dict[str, Any]:
        """
        Parar serviço de verificação periódica

        Returns:
            Dicionário com resultado da parada
        """
        if not self.is_running:
            return {
                "success": False,
                "message": "Serviço de verificação de veículos não está em execução",
                "status": "not_running",
            }

        self.stop_event.set()
        self.scheduler.clear()

        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.is_running = False

        self.logger.info("VehicleVerificationService parado")

        return {
            "success": True,
            "message": "Serviço de verificação de veículos parado",
            "status": "stopped",
        }

    def _scheduler_loop(self):
        """Loop do agendador"""
        while not self.stop_event.is_set():
            try:
                self.scheduler.run_pending()
                self.stop_event.wait(timeout=60)  # Verificar a cada minuto (acorda no stop)
            except Exception as e:
                self.logger.error(
                    f"Erro no loop do scheduler de verificação de veículos: {e}",
                    {"error": str(e)},
                )
                self.stop_event.wait(timeout=60)

    def get_status(self) -> Dict[str, Any]:
        """
        Obter status do serviço

        Returns:
            Dicionário com status atual
        """
        return {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "verification_interval_hours": self.verification_interval_hours,
            "location_sync_interval_minutes": self.location_sync_interval_minutes,
            "last_verification": (
                self.last_verification.isoformat() if self.last_verification else None
            ),
            "last_location_sync": (
                self.last_location_sync.isoformat() if self.last_location_sync else None
            ),
            "last_result": self.last_result,
        }

    def run_verification_now(self) -> Dict[str, Any]:
        """
        Executar verificação manualmente (fora do agendamento)

        Returns:
            Dicionário com resultado da verificação
        """
        return self.verify_vehicles()
