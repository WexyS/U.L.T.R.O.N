import threading
import time
import logging
from typing import Callable, List, Dict

logger = logging.getLogger("UltronDaemon")

class UltronDaemon:
    def __init__(self, name: str, interval: int, func: Callable):
        self.name = name
        self.interval = interval
        self.func = func
        self.active = False
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        logger.info(f"Daemon [{self.name}] active and patrolling.")
        while self.active:
            try:
                self.func()
            except Exception as e:
                logger.error(f"Daemon [{self.name}] encountered anomaly: {e}")
            time.sleep(self.interval)

    def start(self):
        self.active = True
        self.thread.start()

class DaemonManager:
    """Claude's 5 Parallel Research Loops Manager"""
    def __init__(self):
        self.daemons: Dict[str, UltronDaemon] = {}

    def register_daemon(self, name: str, interval: int, func: Callable):
        self.daemons[name] = UltronDaemon(name, interval, func)
        logger.info(f"Daemon [{name}] registered for {interval}s intervals.")

    def start_all(self):
        for daemon in self.daemons.values():
            daemon.start()

    def get_status(self):
        return {name: ("Active" if d.active else "Inactive") for name, d in self.daemons.items()}

# --- Global Access ---
daemon_manager = DaemonManager()
