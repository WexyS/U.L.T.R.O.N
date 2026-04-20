import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ConnectivityManager:
    """Manages internet connectivity status and offline mode transitions."""
    
    _is_online: Optional[bool] = None

    @staticmethod
    def check_connection(host="8.8.8.8", port=53, timeout=3) -> bool:
        """Check if internet is accessible."""
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            ConnectivityManager._is_online = True
            return True
        except socket.error:
            ConnectivityManager._is_online = False
            return False

    @classmethod
    def is_online(cls, force_check: bool = False) -> bool:
        """Return cached or fresh connectivity status."""
        if cls._is_online is None or force_check:
            return cls.check_connection()
        return cls._is_online

    @staticmethod
    def get_offline_recommendation(task_type: str) -> str:
        """Provide recommendations for tasks when offline."""
        recommendations = {
            "research": "Internet is unavailable. Using local memory and knowledge base for research. Results may be limited to previously learned data.",
            "code": "Offline mode active. Using local Ultron Native Core (Ollama) for code generation and analysis.",
            "vision": "Vision system is fully operational offline using local screen capture and neural engines.",
            "voice": "Voice interaction is operational via local Whisper/VoiceBox modules.",
            "general": "Ultron is running in local-first mode. All data remains on this machine."
        }
        return recommendations.get(task_type, "System is offline. Some features may be limited.")
