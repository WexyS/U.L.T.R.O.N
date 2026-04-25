import subprocess
import requests
import logging
import asyncio
import time
from typing import Tuple, List, Dict
from ultron.core.event_bus import event_bus

logger = logging.getLogger("UltronVRAM")

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
LAST_LOG_TIME = 0.0
LOG_COOLDOWN = 60.0  # seconds

def get_vram_usage() -> Tuple[int, int]:
    """Returns (used_mb, total_mb). Defaults to (0,0) if nvidia-smi fails."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True
        )
        parts = result.stdout.strip().split("\n")[0].split(",")
        used_mb = int(parts[0].strip())
        total_mb = int(parts[1].strip())
        return used_mb, total_mb
    except Exception as e:
        logger.debug(f"Failed to read VRAM via nvidia-smi: {e}")
        return 0, 0

def get_loaded_models() -> List[Dict]:
    """Returns a list of currently loaded Ollama models."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/ps", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("models", [])
    except Exception as e:
        logger.debug(f"Failed to get loaded models: {e}")
    return []

def unload_model(model_name: str) -> bool:
    """Forces Ollama to unload a model by sending a generate request with keep_alive=0."""
    try:
        logger.warning(f"VRAM Hypervisor forcing unload of model: {model_name}")
        payload = {
            "model": model_name,
            "keep_alive": 0
        }
        resp = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Failed to unload model {model_name}: {e}")
        return False

def get_threshold_mb() -> int:
    """Calculate threshold dynamically based on total VRAM."""
    used_mb, total_mb = get_vram_usage()
    if total_mb == 0:
        return 10500 # Default fallback
    
    # Keep at least 1.5GB free or 10% of total, whichever is larger
    buffer = max(1500, int(total_mb * 0.1))
    return total_mb - buffer

def vram_hypervisor_tick():
    """Main function to be called periodically by the daemon manager."""
    used_mb, total_mb = get_vram_usage()
    if total_mb == 0:
        return  # Cannot read VRAM or not NVIDIA
    
    threshold_mb = get_threshold_mb()
    usage_percent = (used_mb / total_mb) * 100
    
    # Fire status event for UI
    event_bus.emit("VRAM_STATUS_UPDATE", "AgentBridge", {
        "used_mb": used_mb,
        "total_mb": total_mb,
        "threshold_mb": threshold_mb,
        "usage_percent": round(usage_percent, 1)
    })
    
    # If we exceed threshold, try to swap out models
    if used_mb > threshold_mb:
        global LAST_LOG_TIME
        current_time = time.time()
        if current_time - LAST_LOG_TIME > LOG_COOLDOWN:
            logger.warning(f"HIGH VRAM USAGE: {used_mb}MB / {total_mb}MB ({usage_percent:.1f}%). Threshold: {threshold_mb}MB")
            LAST_LOG_TIME = current_time
            
        loaded_models = get_loaded_models()
        
        if len(loaded_models) > 1:
            # Sort models by size (largest first) and unload the largest
            loaded_models.sort(key=lambda x: x.get("size", 0), reverse=True)
            model_to_unload = loaded_models[0]["name"]
            
            success = unload_model(model_to_unload)
            if success:
                logger.info(f"VRAM Optimization: Unloaded {model_to_unload} ({usage_percent:.1f}% used).")
                event_bus.emit("MODEL_UNLOADED", "AgentBridge", {
                    "model_name": model_to_unload,
                    "reason": "VRAM Limit Exceeded",
                    "usage_percent": usage_percent
                })
        elif len(loaded_models) == 1:
            if usage_percent > 95:
                logger.warning("VRAM critically low (>95%) with only one model loaded. System may become unstable.")
