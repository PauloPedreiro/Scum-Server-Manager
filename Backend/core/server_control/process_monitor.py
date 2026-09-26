"""
Monitor de Processos para SCUM Backend
"""

import psutil
import time
from typing import Dict, Any, Optional, List
from utils.logger import StructuredLogger


class ProcessMonitor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = StructuredLogger()
        self.service_name = config.get("service_name", "SCUMServer")
        self.server_path = config.get("server_path", "")

    def get_process_info(self) -> Dict[str, Any]:
        """Obter informações detalhadas do processo SCUM"""
        try:
            # Procurar por processos SCUM
            scum_processes = []

            for proc in psutil.process_iter(
                ["pid", "name", "exe", "cpu_percent", "memory_info", "create_time"]
            ):
                try:
                    if proc.info["name"] and "scum" in proc.info["name"].lower():
                        scum_processes.append(proc.info)
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    continue

            if not scum_processes:
                return {
                    "found": False,
                    "processes": [],
                    "message": "Nenhum processo SCUM encontrado",
                }

            # Processar informações dos processos
            process_info = []
            for proc in scum_processes:
                try:
                    process = psutil.Process(proc["pid"])

                    # Calcular uptime
                    uptime = time.time() - proc["create_time"]

                    # Obter uso de CPU e memória
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()

                    process_info.append(
                        {
                            "pid": proc["pid"],
                            "name": proc["name"],
                            "exe": proc["exe"],
                            "cpu_percent": cpu_percent,
                            "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                            "uptime_seconds": round(uptime, 2),
                            "uptime_formatted": self._format_uptime(uptime),
                            "status": "running",
                        }
                    )

                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    continue

            return {
                "found": True,
                "processes": process_info,
                "count": len(process_info),
                "message": f"Encontrados {len(process_info)} processo(s) SCUM",
            }

        except Exception as e:
            self.logger.error(f"Erro ao obter informações do processo: {e}")
            return {
                "found": False,
                "processes": [],
                "error": str(e),
                "message": "Erro ao monitorar processos",
            }

    def get_system_info(self) -> Dict[str, Any]:
        """Obter informações do sistema"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # Memória
            memory = psutil.virtual_memory()
            memory_total_gb = round(memory.total / 1024 / 1024 / 1024, 2)
            memory_used_gb = round(memory.used / 1024 / 1024 / 1024, 2)
            memory_percent = memory.percent

            # Disco
            disk = psutil.disk_usage("/")
            disk_total_gb = round(disk.total / 1024 / 1024 / 1024, 2)
            disk_used_gb = round(disk.used / 1024 / 1024 / 1024, 2)
            disk_percent = round((disk.used / disk.total) * 100, 2)

            # Boot time
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time

            return {
                "cpu": {"percent": cpu_percent, "count": cpu_count},
                "memory": {
                    "total_gb": memory_total_gb,
                    "used_gb": memory_used_gb,
                    "percent": memory_percent,
                },
                "disk": {
                    "total_gb": disk_total_gb,
                    "used_gb": disk_used_gb,
                    "percent": disk_percent,
                },
                "system": {
                    "uptime_seconds": round(uptime_seconds, 2),
                    "uptime_formatted": self._format_uptime(uptime_seconds),
                    "boot_time": boot_time,
                },
            }

        except Exception as e:
            self.logger.error(f"Erro ao obter informações do sistema: {e}")
            return {"error": str(e), "message": "Erro ao obter informações do sistema"}

    def get_network_info(self) -> Dict[str, Any]:
        """Obter informações de rede"""
        try:
            # Estatísticas de rede
            net_io = psutil.net_io_counters()

            # Conexões de rede
            connections = psutil.net_connections()

            # Interfaces de rede
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()

            network_info = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "connections_count": len(connections),
                "interfaces": {},
            }

            # Informações das interfaces
            for interface, addrs in net_if_addrs.items():
                if interface in net_if_stats:
                    stats = net_if_stats[interface]
                    network_info["interfaces"][interface] = {
                        "is_up": stats.isup,
                        "speed": stats.speed,
                        "mtu": stats.mtu,
                        "addresses": [
                            addr.address
                            for addr in addrs
                            if addr.family.name == "AF_INET"
                        ],
                    }

            return network_info

        except Exception as e:
            self.logger.error(f"Erro ao obter informações de rede: {e}")
            return {"error": str(e), "message": "Erro ao obter informações de rede"}

    def monitor_process(self, pid: int, duration: int = 60) -> Dict[str, Any]:
        """Monitorar um processo específico por um período"""
        try:
            process = psutil.Process(pid)
            start_time = time.time()

            samples = []
            sample_interval = 5  # segundos

            while time.time() - start_time < duration:
                try:
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()

                    sample = {
                        "timestamp": time.time(),
                        "cpu_percent": cpu_percent,
                        "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                        "status": "running",
                    }

                    samples.append(sample)

                    time.sleep(sample_interval)

                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    break

            # Calcular estatísticas
            if samples:
                cpu_values = [s["cpu_percent"] for s in samples]
                memory_values = [s["memory_mb"] for s in samples]

                stats = {
                    "duration_seconds": duration,
                    "samples_count": len(samples),
                    "cpu": {
                        "min": min(cpu_values),
                        "max": max(cpu_values),
                        "avg": round(sum(cpu_values) / len(cpu_values), 2),
                    },
                    "memory": {
                        "min": min(memory_values),
                        "max": max(memory_values),
                        "avg": round(sum(memory_values) / len(memory_values), 2),
                    },
                    "samples": samples,
                }
            else:
                stats = {
                    "duration_seconds": duration,
                    "samples_count": 0,
                    "error": "Processo não encontrado ou acesso negado",
                }

            return stats

        except Exception as e:
            self.logger.error(f"Erro ao monitorar processo {pid}: {e}")
            return {"error": str(e), "message": f"Erro ao monitorar processo {pid}"}

    def _format_uptime(self, seconds: float) -> str:
        """Formatar uptime em formato legível"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d {hours}h"

    def get_all_info(self) -> Dict[str, Any]:
        """Obter todas as informações de monitoramento"""
        return {
            "process": self.get_process_info(),
            "system": self.get_system_info(),
            "network": self.get_network_info(),
            "timestamp": time.time(),
        }
