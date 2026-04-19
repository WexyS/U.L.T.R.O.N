import psutil
import platform
import socket
from datetime import datetime

class SystemMonitor:
    """PC kaynaklarını, ağ bilgilerini ve pil durumunu izler."""
    
    @staticmethod
    def get_cpu_usage() -> float:
        return psutil.cpu_percent(interval=None)
        
    @staticmethod
    def get_ram_usage() -> tuple[float, str]:
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        return mem.percent, f"{total_gb:.1f} GB"

    @staticmethod
    def get_battery_status() -> str:
        if not hasattr(psutil, "sensors_battery"):
            return "Bilinmiyor"
        bat = psutil.sensors_battery()
        if bat is None:
            return "Masaüstü (Pil Yok)"
        plugged = "Takılı" if bat.power_plugged else "Pilde"
        return f"%{bat.percent:.0f} ({plugged})"

    @staticmethod
    def get_system_info() -> dict:
        return {
            "OS": platform.system(),
            "OS_Release": platform.release(),
            "Machine": platform.machine(),
            "Processor": platform.processor(),
            "Node": platform.node(),
            "Boot_Time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def get_ip_address() -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP
