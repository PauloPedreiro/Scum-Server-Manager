"""
Sistema de Hardware Fingerprint
Coleta MAC addresses e outros identificadores únicos de hardware
Gera hash SHA-256 único da máquina
"""

import hashlib
import platform
import json
import os
import socket
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Tentar importar psutil para informações de rede e sistema
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Tentar importar bibliotecas Windows
try:
    import wmi

    WMI_AVAILABLE = True
except ImportError as e:
    WMI_AVAILABLE = False
    WMI_IMPORT_ERROR = str(e)

try:
    import winreg

    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False

try:
    import win32api

    WIN32API_AVAILABLE = True
except ImportError:
    WIN32API_AVAILABLE = False

try:
    import pythoncom

    PYTHONCOM_AVAILABLE = True
except ImportError:
    PYTHONCOM_AVAILABLE = False


class HardwareFingerprint:
    """Gera fingerprint único da máquina combinando múltiplos componentes de hardware"""

    def __init__(self, logger=None):
        """
        Inicializa o coletor de hardware fingerprint

        Args:
            logger: Logger opcional para logs
        """
        self.logger = logger
        self.is_windows = platform.system() == "Windows"

        if not self.is_windows:
            if self.logger:
                self.logger.warn("Hardware fingerprint is supported only on Windows")

        # Inicializar WMI se disponível
        self.wmi_conn = None
        self.wmi_available = False

        if not self.is_windows:
            if self.logger:
                self.logger.warn("Hardware fingerprint is supported only on Windows")
            return

        if not WMI_AVAILABLE:
            if self.logger:
                self.logger.warn(
                    "'wmi' library is not installed. Run: pip install wmi"
                )
            return

        # Tentar inicializar WMI
        try:
            # Inicializar COM para uso em threads (necessário para Flask)
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    # Já inicializado, continuar
                    pass

            self.wmi_conn = wmi.WMI()
            self.wmi_available = True
            if self.logger:
                self.logger.debug("WMI initialized successfully")
        except Exception as e:
            self.wmi_available = False
            if self.logger:
                self.logger.warn(f"Failed to initialize WMI: {e}")
                self.logger.warn(f"Error type: {type(e).__name__}")

    def generate(self) -> Tuple[str, Dict[str, Any]]:
        """
        Gera hash SHA-256 único da máquina

        Returns:
            Tupla (hash_string, componentes_dict)
        """
        components = self._collect_all_components()
        hash_value = self._generate_hash(components)

        return hash_value, components

    def _collect_all_components(self) -> Dict[str, Any]:
        """Coleta todos os componentes de hardware disponíveis"""
        components = {
            "network_macs": [],
            "cpu_id": None,
            "cpu_name": None,
            "cpu_cores": None,
            "disk_serials": [],
            "disks_detailed": [],  # Lista com capacidade e serial
            "motherboard_serial": None,
            "motherboard_name": None,
            "bios_serial": None,
            "windows_guid": None,
            "system_uuid": None,
            "hostname": None,
            "ram_serials": [],
            "ram_detailed": [],  # Lista com capacidade e serial
            "gpu_name": None,
            "gpu_serial": None,
            "fingerprint_status": None,
            "fingerprint_message": None,
        }

        if not self.is_windows:
            return components

        # Coletar componentes
        try:
            components["network_macs"] = self._get_network_macs()
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect network MACs: {e}")

        try:
            cpu_info = self._get_cpu_info()
            components["cpu_id"] = cpu_info.get("id")
            components["cpu_name"] = cpu_info.get("name")
            components["cpu_cores"] = cpu_info.get("cores")
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect CPU information: {e}")

        try:
            disk_info = self._get_disk_info()
            components["disk_serials"] = disk_info.get("serials", [])
            components["disks_detailed"] = disk_info.get("detailed", [])
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect disk information: {e}")

        try:
            mb_info = self._get_motherboard_info()
            components["motherboard_serial"] = mb_info.get("serial")
            components["motherboard_name"] = mb_info.get("name")
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect motherboard information: {e}")

        try:
            components["bios_serial"] = self._get_bios_serial()
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect BIOS serial: {e}")

        try:
            components["windows_guid"] = self._get_windows_guid()
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect Windows GUID: {e}")

        try:
            components["system_uuid"] = self._get_system_uuid()
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect System UUID: {e}")

        try:
            components["hostname"] = socket.gethostname()
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect hostname: {e}")

        try:
            ram_info = self._get_ram_info()
            components["ram_serials"] = ram_info.get("serials", [])
            components["ram_detailed"] = ram_info.get("detailed", [])
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect RAM information: {e}")

        try:
            gpu_info = self._get_gpu_info()
            components["gpu_name"] = gpu_info.get("name")
            components["gpu_serial"] = gpu_info.get("serial")
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to collect GPU information: {e}")

        # Validate minimum identifiers and attach status/message for UI
        critical_components = [
            components["windows_guid"],
            components["system_uuid"],
            components["cpu_id"],
            len(components["network_macs"]) > 0,
            len(components["disk_serials"]) > 0,
        ]

        present_count = sum(1 for c in critical_components if c)
        if present_count == 0:
            components["fingerprint_status"] = "unavailable"
            components["fingerprint_message"] = (
                "Virtualized environment without available identifiers"
            )
        elif present_count < 2:
            components["fingerprint_status"] = "weak"
            components["fingerprint_message"] = "Insufficient identifiers for a reliable fingerprint"
        else:
            components["fingerprint_status"] = "ok"

        if present_count < 2:
            if self.logger:
                self.logger.error(
                    "Not enough identifiers collected for a reliable fingerprint"
                )
                self.logger.error(
                    f"Identifiers collected: WIN_GUID={'OK' if components.get('windows_guid') else 'NONE'}, SYS_UUID={'OK' if components.get('system_uuid') else 'NONE'}, CPU_ID={'OK' if components.get('cpu_id') else 'NONE'}, MACS={len(components.get('network_macs') or [])}, DISKS={len(components.get('disk_serials') or [])}"
                )

        return components

    def _get_system_uuid(self) -> Optional[str]:
        """Obtém UUID do sistema via WMI (útil em VMs/KVM)"""
        if not self.wmi_conn:
            return None

        try:
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            products = self.wmi_conn.Win32_ComputerSystemProduct()
            if products and hasattr(products[0], "UUID") and products[0].UUID:
                uuid_value = str(products[0].UUID).strip().upper()
                invalid_values = [
                    "N/A",
                    "NONE",
                    "DEFAULT",
                    "00000000-0000-0000-0000-000000000000",
                    "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
                ]
                if uuid_value and uuid_value not in invalid_values:
                    return uuid_value
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read System UUID via WMI: {e}")

        return None

    def _get_network_macs(self) -> List[str]:
        """Obtém MAC addresses de todos os adaptadores de rede físicos"""
        macs = []

        if not self.wmi_conn:
            return macs

        try:
            # Garantir que COM está inicializado para threads
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            adapters = self.wmi_conn.Win32_NetworkAdapter(PhysicalAdapter=True)

            for adapter in adapters:
                if adapter.MACAddress and adapter.MACAddress != "00:00:00:00:00:00":
                    # Filtrar adaptadores virtuais
                    adapter_name = adapter.Name.lower() if adapter.Name else ""
                    virtual_keywords = [
                        "vmware",
                        "virtualbox",
                        "hyper-v",
                        "loopback",
                        "virtual",
                    ]

                    if not any(keyword in adapter_name for keyword in virtual_keywords):
                        mac = adapter.MACAddress.upper().replace("-", ":")
                        if mac not in macs:
                            macs.append(mac)
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read MACs via WMI: {e}")

        # Ordenar para garantir ordem determinística
        return sorted(macs)

    def _get_cpu_info(self) -> Dict[str, Any]:
        """Obtém informações detalhadas da CPU"""
        info = {"id": None, "name": None, "cores": None}

        if not self.wmi_conn:
            return info

        try:
            # Garantir que COM está inicializado para threads
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            processors = self.wmi_conn.Win32_Processor()
            if processors:
                proc = processors[0]

                # CPU ID
                if proc.ProcessorId:
                    info["id"] = proc.ProcessorId.strip().upper()
                elif hasattr(proc, "UniqueId") and proc.UniqueId:
                    info["id"] = proc.UniqueId.strip().upper()

                # Nome da CPU
                if proc.Name:
                    info["name"] = proc.Name.strip()

                # Número de cores
                if proc.NumberOfCores:
                    info["cores"] = int(proc.NumberOfCores)
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read CPU info via WMI: {e}")

        return info

    def _get_disk_info(self) -> Dict[str, Any]:
        """Obtém informações detalhadas de todos os discos"""
        serials = []
        detailed = []

        if not self.wmi_conn:
            return {"serials": serials, "detailed": detailed}

        try:
            # Garantir que COM está inicializado para threads
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            disks = self.wmi_conn.Win32_DiskDrive()
            for disk in disks:
                disk_info = {
                    "index": disk.Index if hasattr(disk, "Index") else None,
                    "model": disk.Model.strip() if disk.Model else "Unknown",
                    "serial": None,
                    "size_gb": None,
                    "size_bytes": None,
                }

                # Serial
                if disk.SerialNumber:
                    serial = disk.SerialNumber.strip().upper()
                    if serial:
                        disk_info["serial"] = serial
                        if serial not in serials:
                            serials.append(serial)

                # Tamanho
                if disk.Size:
                    try:
                        size_bytes = int(disk.Size)
                        size_gb = round(size_bytes / (1024**3), 2)
                        disk_info["size_bytes"] = size_bytes
                        disk_info["size_gb"] = size_gb
                    except:
                        pass

                detailed.append(disk_info)
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read disk info via WMI: {e}")

        # Fallback: Volume Serial Number
        if not serials and WIN32API_AVAILABLE:
            try:
                volumes = win32api.GetLogicalDriveStrings().split("\x00")
                for vol in volumes:
                    if vol:
                        try:
                            vol_info = win32api.GetVolumeInformation(vol)
                            if vol_info[1]:  # Serial number
                                serial = str(vol_info[1])
                                if serial not in serials:
                                    serials.append(serial)
                        except:
                            pass
            except Exception as e:
                if self.logger:
                    self.logger.warn(f"Failed to read volume serial: {e}")

        return {"serials": sorted(serials), "detailed": detailed}

    def _get_motherboard_info(self) -> Dict[str, Any]:
        """Obtém informações detalhadas da placa-mãe"""
        info = {"serial": None, "name": None}

        if not self.wmi_conn:
            return info

        try:
            # Garantir que COM está inicializado para threads
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            boards = self.wmi_conn.Win32_BaseBoard()
            if boards:
                board = boards[0]

                # Serial
                if board.SerialNumber:
                    serial = board.SerialNumber.strip().upper()
                    invalid_values = [
                        "N/A",
                        "NONE",
                        "DEFAULT",
                        "TO BE FILLED BY O.E.M.",
                        "OEM",
                    ]
                    if serial and serial not in invalid_values:
                        info["serial"] = serial

                # Nome/Modelo
                if board.Product:
                    info["name"] = board.Product.strip()
                elif board.Manufacturer:
                    manufacturer = board.Manufacturer.strip()
                    product = board.Product.strip() if board.Product else ""
                    info["name"] = f"{manufacturer} {product}".strip()
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read motherboard info via WMI: {e}")

        return info

    def _get_bios_serial(self) -> Optional[str]:
        """Obtém serial do BIOS"""
        if not self.wmi_conn:
            return None

        try:
            # Garantir que COM está inicializado para threads
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            bios_list = self.wmi_conn.Win32_BIOS()
            if bios_list and bios_list[0].SerialNumber:
                serial = bios_list[0].SerialNumber.strip().upper()
                # Filtrar valores inválidos comuns
                invalid_values = [
                    "N/A",
                    "NONE",
                    "DEFAULT STRING",
                    "DEFAULT",
                    "TO BE FILLED BY O.E.M.",
                    "OEM",
                ]
                if serial and serial not in invalid_values:
                    return serial
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read BIOS serial via WMI: {e}")

        return None

    def _get_gpu_info(self) -> Dict[str, Any]:
        """Obtém informações da GPU"""
        info = {"name": None, "serial": None}

        if not self.wmi_conn:
            return info

        try:
            # Garantir que COM está inicializado para threads
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            # Tentar Win32_VideoController
            video_controllers = self.wmi_conn.Win32_VideoController()
            if video_controllers:
                gpu = video_controllers[0]

                # Nome da GPU
                if gpu.Name:
                    info["name"] = gpu.Name.strip()

                # Serial (pode não estar disponível)
                if hasattr(gpu, "PNPDeviceID") and gpu.PNPDeviceID:
                    info["serial"] = gpu.PNPDeviceID.strip()
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read GPU info via WMI: {e}")

        return info

    def _get_windows_guid(self) -> Optional[str]:
        """Obtém Windows Machine GUID do Registry"""
        if not REGISTRY_AVAILABLE:
            return None

        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
            )
            guid = winreg.QueryValueEx(key, "MachineGuid")[0]
            winreg.CloseKey(key)

            if guid:
                return guid.strip().upper()
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read Windows GUID from registry: {e}")

        return None

    def _get_ram_info(self) -> Dict[str, Any]:
        """Obtém informações detalhadas da RAM"""
        serials = []
        detailed = []

        if not self.wmi_conn:
            return {"serials": serials, "detailed": detailed}

        try:
            # Garantir que COM está inicializado para threads
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            memory_modules = self.wmi_conn.Win32_PhysicalMemory()
            for module in memory_modules:
                ram_info = {
                    "capacity_gb": None,
                    "capacity_bytes": None,
                    "serial": None,
                    "speed_mhz": None,
                    "manufacturer": None,
                    "part_number": None,
                }

                # Capacidade
                if module.Capacity:
                    try:
                        capacity_bytes = int(module.Capacity)
                        capacity_gb = round(capacity_bytes / (1024**3), 2)
                        ram_info["capacity_bytes"] = capacity_bytes
                        ram_info["capacity_gb"] = capacity_gb
                    except:
                        pass

                # Serial
                if hasattr(module, "SerialNumber") and module.SerialNumber:
                    serial = module.SerialNumber.strip().upper()
                    invalid_values = ["N/A", "NONE", "00000000", "FFFFFFFF"]
                    if serial and serial not in invalid_values:
                        ram_info["serial"] = serial
                        if serial not in serials:
                            serials.append(serial)

                # Velocidade
                if hasattr(module, "Speed") and module.Speed:
                    try:
                        ram_info["speed_mhz"] = int(module.Speed)
                    except:
                        pass

                # Fabricante
                if hasattr(module, "Manufacturer") and module.Manufacturer:
                    ram_info["manufacturer"] = module.Manufacturer.strip()

                # Part Number
                if hasattr(module, "PartNumber") and module.PartNumber:
                    ram_info["part_number"] = module.PartNumber.strip()

                detailed.append(ram_info)
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read RAM info via WMI: {e}")

        return {"serials": sorted(serials), "detailed": detailed}

    def _generate_hash(self, components: Dict[str, Any]) -> str:
        """
        Gera hash SHA-256 dos componentes

        Args:
            components: Dicionário com componentes coletados

        Returns:
            Hash SHA-256 em hexadecimal
        """
        def _safe_strip_upper(value: Any) -> str:
            if value is None:
                return ""
            try:
                return str(value).strip().upper()
            except Exception:
                return ""

        # Normalizar e ordenar componentes
        network_macs = sorted(
            [
                mac.upper().replace("-", ":")
                for mac in components.get("network_macs", [])
            ]
        )
        disk_serials = sorted(
            [_safe_strip_upper(serial) for serial in components.get("disk_serials", [])]
        )
        ram_serials = sorted(
            [_safe_strip_upper(serial) for serial in components.get("ram_serials", [])]
        )

        cpu_id = _safe_strip_upper(components.get("cpu_id"))
        motherboard_serial = (
            _safe_strip_upper(components.get("motherboard_serial"))
        )
        bios_serial = _safe_strip_upper(components.get("bios_serial"))
        windows_guid = _safe_strip_upper(components.get("windows_guid"))
        system_uuid = _safe_strip_upper(components.get("system_uuid"))
        hostname = _safe_strip_upper(components.get("hostname"))

        # Incluir informações adicionais no hash para maior robustez
        # Discos detalhados (serial + tamanho)
        disk_details = []
        for disk in components.get("disks_detailed", []):
            if disk.get("serial"):
                size = disk.get("size_gb", 0)
                disk_details.append(f"{disk['serial']}:{size}")
        disk_details_str = ",".join(sorted(disk_details))

        # RAM detalhada - incluir TODOS os módulos (mesmo sem serial)
        # Usar: serial (se disponível) ou capacidade+part_number+speed como identificador
        ram_details = []
        for ram in components.get("ram_detailed", []):
            capacity = ram.get("capacity_gb", 0)
            speed = ram.get("speed_mhz", 0)
            part_number = _safe_strip_upper(ram.get("part_number")) or "NONE"

            if ram.get("serial"):
                # Se tem serial, usar serial:capacidade
                ram_details.append(f"S:{ram['serial']}:{capacity}")
            else:
                # Se não tem serial, usar capacidade+part_number+speed
                ram_details.append(f"C:{capacity}:{speed}:{part_number}")
        ram_details_str = ",".join(sorted(ram_details))

        # GPU (incluir no hash)
        gpu_name = _safe_strip_upper(components.get("gpu_name"))
        gpu_serial = _safe_strip_upper(components.get("gpu_serial"))
        gpu_str = f"{gpu_name}:{gpu_serial}" if gpu_name or gpu_serial else ""

        # CPU name e cores (incluir para maior robustez)
        cpu_name = _safe_strip_upper(components.get("cpu_name"))
        cpu_cores = components.get("cpu_cores")
        cpu_extended = f"{cpu_id}:{cpu_name}:{cpu_cores}" if cpu_id else ""

        # Motherboard name (incluir)
        mb_name = _safe_strip_upper(components.get("motherboard_name"))
        mb_str = (
            f"{motherboard_serial}:{mb_name}" if motherboard_serial or mb_name else ""
        )

        # Concatenar de forma determinística
        fingerprint_string = "|".join(
            [
                f"NET:{','.join(network_macs)}",
                f"CPU:{cpu_extended}",
                f"DISK:{','.join(disk_serials)}",
                f"DISKD:{disk_details_str}",
                f"MB:{mb_str}",
                f"BIOS:{bios_serial}",
                f"WIN:{windows_guid}",
                f"SYSUUID:{system_uuid}",
                f"HOST:{hostname}",
                f"RAM:{','.join(ram_serials)}",
                f"RAMD:{ram_details_str}",
                f"GPU:{gpu_str}",
            ]
        )

        # Gerar hash SHA-256
        hash_value = hashlib.sha256(fingerprint_string.encode("utf-8")).hexdigest()

        return hash_value

    def verify(
        self, stored_hash: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Verifica se hardware mudou comparando com hash armazenado

        Args:
            stored_hash: Hash armazenado anteriormente (opcional)

        Returns:
            Tupla (mudou: bool, hash_atual: str, hash_armazenado: str)
        """
        current_hash, components = self.generate()

        if stored_hash is None:
            return False, current_hash, None

        changed = current_hash != stored_hash

        return changed, current_hash, stored_hash

    def get_hardware_list(self) -> Dict[str, Any]:
        """
        Retorna lista completa de hardware no formato da documentação da API

        Returns:
            Dicionário com estrutura:
            {
                "network_interfaces": [...],
                "cpu": {...},
                "disks": [...],
                "motherboard": {...},
                "memory": {...},
                "system": {...}
            }
        """
        hardware_list = {
            "network_interfaces": [],
            "cpu": {},
            "disks": [],
            "motherboard": {},
            "memory": {},
            "system": {},
        }

        if not self.is_windows:
            return hardware_list

        # Coletar todos os componentes
        components = self._collect_all_components()

        # Network Interfaces
        hardware_list["network_interfaces"] = self._get_network_interfaces_detailed(
            components
        )

        # CPU
        hardware_list["cpu"] = self._get_cpu_detailed(components)

        # Disks
        hardware_list["disks"] = self._get_disks_detailed(components)

        # Motherboard
        hardware_list["motherboard"] = self._get_motherboard_detailed(components)

        # Memory
        hardware_list["memory"] = self._get_memory_detailed(components)

        # System
        hardware_list["system"] = self._get_system_info()

        return hardware_list

    def _get_network_interfaces_detailed(
        self, components: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Obtém informações detalhadas de interfaces de rede"""
        interfaces = []

        if not self.wmi_conn:
            return interfaces

        try:
            # Garantir que COM está inicializado
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            # Obter IPs das interfaces usando psutil se disponível
            interface_ips = {}
            if PSUTIL_AVAILABLE:
                try:
                    net_if_addrs = psutil.net_if_addrs()
                    for interface_name, addrs in net_if_addrs.items():
                        for addr in addrs:
                            if addr.family == socket.AF_INET:  # IPv4
                                if interface_name not in interface_ips:
                                    interface_ips[interface_name] = []
                                interface_ips[interface_name].append(addr.address)
                except Exception as e:
                    if self.logger:
                        self.logger.warn(f"Failed to read interface IPs: {e}")

            # Obter adaptadores via WMI
            adapters = self.wmi_conn.Win32_NetworkAdapter(PhysicalAdapter=True)

            for adapter in adapters:
                if adapter.MACAddress and adapter.MACAddress != "00:00:00:00:00:00":
                    # Filtrar adaptadores virtuais
                    adapter_name = adapter.Name.lower() if adapter.Name else ""
                    virtual_keywords = [
                        "vmware",
                        "virtualbox",
                        "hyper-v",
                        "loopback",
                        "virtual",
                    ]

                    if not any(keyword in adapter_name for keyword in virtual_keywords):
                        mac = adapter.MACAddress.upper().replace("-", ":")

                        # Determinar tipo (ethernet ou wireless)
                        interface_type = "ethernet"
                        adapter_name_lower = adapter_name
                        if any(
                            keyword in adapter_name_lower
                            for keyword in ["wifi", "wireless", "wlan", "802.11"]
                        ):
                            interface_type = "wireless"

                        # Obter IP da interface
                        ip_address = None
                        interface_name = (
                            adapter.Name if adapter.Name else f"Adapter_{mac}"
                        )
                        if (
                            interface_name in interface_ips
                            and interface_ips[interface_name]
                        ):
                            ip_address = interface_ips[interface_name][
                                0
                            ]  # Pegar primeiro IP

                        interfaces.append(
                            {
                                "name": interface_name,
                                "mac_address": mac,
                                "ip_address": ip_address or "N/A",
                                "type": interface_type,
                            }
                        )
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read detailed network interfaces: {e}")

        return interfaces

    def _get_cpu_detailed(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Obtém informações detalhadas da CPU no formato da documentação"""
        cpu_info = {
            "manufacturer": None,
            "model": None,
            "serial": None,
            "cores": None,
            "threads": None,
        }

        if not self.wmi_conn:
            return cpu_info

        try:
            # Garantir que COM está inicializado
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            processors = self.wmi_conn.Win32_Processor()
            if processors:
                proc = processors[0]

                # Manufacturer
                if proc.Manufacturer:
                    cpu_info["manufacturer"] = proc.Manufacturer.strip()

                # Model (Name)
                if proc.Name:
                    cpu_info["model"] = proc.Name.strip()

                # Serial (ProcessorId)
                if proc.ProcessorId:
                    cpu_info["serial"] = proc.ProcessorId.strip().upper()
                elif hasattr(proc, "UniqueId") and proc.UniqueId:
                    cpu_info["serial"] = proc.UniqueId.strip().upper()

                # Cores
                if proc.NumberOfCores:
                    cpu_info["cores"] = int(proc.NumberOfCores)

                # Threads (Logical Processors)
                if proc.NumberOfLogicalProcessors:
                    cpu_info["threads"] = int(proc.NumberOfLogicalProcessors)
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read detailed CPU information: {e}")

        return cpu_info

    def _get_disks_detailed(self, components: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Obtém informações detalhadas de discos no formato da documentação"""
        disks = []

        for disk_detail in components.get("disks_detailed", []):
            disk_info = {
                "device": None,
                "model": disk_detail.get("model", "Unknown"),
                "serial": disk_detail.get("serial"),
                "size_gb": disk_detail.get("size_gb"),
                "type": None,
            }

            # Device (usar index ou model como identificador)
            if disk_detail.get("index") is not None:
                disk_info["device"] = f"\\\\.\\PHYSICALDRIVE{disk_detail['index']}"
            else:
                disk_info["device"] = disk_detail.get("model", "Unknown")

            # Type (SSD ou HDD) - tentar determinar pelo model
            model_lower = disk_info["model"].lower()
            if any(
                keyword in model_lower
                for keyword in ["ssd", "solid state", "nvme", "m.2"]
            ):
                disk_info["type"] = "SSD"
            else:
                disk_info["type"] = "HDD"

            # Apenas adicionar se tiver serial ou size
            if disk_info["serial"] or disk_info["size_gb"]:
                disks.append(disk_info)

        return disks

    def _get_motherboard_detailed(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Obtém informações detalhadas da placa-mãe no formato da documentação"""
        mb_info = {
            "manufacturer": None,
            "model": None,
            "serial": components.get("motherboard_serial"),
        }

        if not self.wmi_conn:
            return mb_info

        try:
            # Garantir que COM está inicializado
            if PYTHONCOM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                except:
                    pass

            boards = self.wmi_conn.Win32_BaseBoard()
            if boards:
                board = boards[0]

                # Manufacturer
                if board.Manufacturer:
                    mb_info["manufacturer"] = board.Manufacturer.strip()

                # Model (Product)
                if board.Product:
                    mb_info["model"] = board.Product.strip()
        except Exception as e:
            if self.logger:
                self.logger.warn(
                    f"Failed to read detailed motherboard information: {e}"
                )

        return mb_info

    def _get_memory_detailed(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Obtém informações detalhadas de memória no formato da documentação"""
        memory_info = {"total_gb": None, "modules": []}

        # Calcular total de RAM
        total_bytes = 0
        for ram_detail in components.get("ram_detailed", []):
            if ram_detail.get("capacity_bytes"):
                total_bytes += ram_detail["capacity_bytes"]

        if total_bytes > 0:
            memory_info["total_gb"] = round(total_bytes / (1024**3), 2)

        # Módulos de memória
        for ram_detail in components.get("ram_detailed", []):
            module = {
                "size_gb": ram_detail.get("capacity_gb"),
                "speed": None,
                "type": None,
            }

            # Speed
            if ram_detail.get("speed_mhz"):
                module["speed"] = f"{ram_detail['speed_mhz']}MHz"

            # Type (tentar determinar)
            # Por padrão, assumir DDR4 (pode ser melhorado)
            module["type"] = "DDR4"

            # Apenas adicionar se tiver size
            if module["size_gb"]:
                memory_info["modules"].append(module)

        return memory_info

    def _get_system_info(self) -> Dict[str, Any]:
        """Obtém informações do sistema no formato da documentação"""
        system_info = {
            "hostname": None,
            "architecture": None,
            "os": None,
            "os_version": None,
        }

        try:
            # Hostname
            system_info["hostname"] = socket.gethostname()

            # Architecture
            machine = platform.machine()
            if machine:
                system_info["architecture"] = machine

            # OS
            system_info["os"] = platform.system()

            # OS Version
            if platform.system() == "Windows":
                # Windows version
                version = platform.version()
                release = platform.release()
                system_info["os_version"] = f"Windows {release} {version}"
            else:
                system_info["os_version"] = platform.platform()
        except Exception as e:
            if self.logger:
                self.logger.warn(f"Failed to read system information: {e}")

        return system_info
