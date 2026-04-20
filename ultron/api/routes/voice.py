"""Voice API routes — Endpoints for controlling the voice module."""
import os
import subprocess
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/voice", tags=["voice"])

@router.post("/launch")
async def launch_voice_mode():
    """Launch the standalone voice mode (start-voice.bat)."""
    try:
        # Resolve path to start-voice.bat
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        bat_path = os.path.join(base_dir, "start-voice.bat")
        
        if not os.path.exists(bat_path):
            raise HTTPException(status_code=404, detail=f"start-voice.bat not found at {bat_path}")
        
        # Launch in a new process without blocking the API
        # On Windows, use 'start' to open a new terminal window
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/c", bat_path], cwd=base_dir)
        
        return {"status": "success", "message": "Voice mode launched in a new window"}
    except Exception as e:
        logger.error(f"Failed to launch voice mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

