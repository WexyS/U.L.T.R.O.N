"""Auto Launchers - Ensures required external processes (Voicebox, OpenGuider) are running."""
import logging
import asyncio
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

async def check_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=1.0)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False

async def ensure_voicebox_running():
    # 1. Check if port is active
    if await check_port_in_use(17493):
        logger.info("VoiceBox API detected on port 17493.")
        return

    logger.info("VoiceBox not detected. Attempting to locate and launch...")
    
    # Common installation paths
    localappdata = os.environ.get("LOCALAPPDATA", "")
    progfiles = os.environ.get("PROGRAMFILES", "")
    
    paths_to_check = [
        Path(localappdata) / "Programs" / "voicebox" / "Voicebox.exe",
        Path(progfiles) / "voicebox" / "Voicebox.exe",
        Path(localappdata) / "voicebox" / "Voicebox.exe"
    ]
    
    found_path = None
    for p in paths_to_check:
        if p.exists():
            found_path = p
            break
            
    if found_path:
        logger.info(f"Launching VoiceBox from {found_path}...")
        try:
            # Launch without hiding completely so tray icon appears, or detached
            subprocess.Popen([str(found_path)], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            logger.info("VoiceBox launched automatically. Booting up AI models (may take a few seconds).")
        except Exception as e:
            logger.warning(f"Failed to auto-launch VoiceBox: {e}")
    else:
        logger.warning("Voicebox executable not found on disk. Please download Voicebox_x64-setup.exe from https://github.com/jamiepine/voicebox/releases and install it once. Ultron will then auto-launch it forever.")

async def start_all_auto_launchers():
    """Starts all external dependencies for Ultron ecosystem."""
    logger.info("Running auto-launch checks for external tools...")
    await asyncio.gather(
        ensure_voicebox_running()
    )
