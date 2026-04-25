"""
AI Bridge Monitor v2.0 - Stabilized Architecture

Uses SQLite MessageQueue to handle Gemini (Architect) -> Qwen (Engineer) tasks.
Eliminates race conditions and ensures transaction integrity.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

try:
    from ultron.core.ai_bridge import bridge
except ImportError:
    # Fallback for direct script execution
    import sys
    sys.path.append(str(PROJECT_ROOT))
    from ultron.core.ai_bridge import bridge

# Paths
REQUESTS_FILE = PROJECT_ROOT / "data" / "gemini_requests.md"
RESPONSES_FILE = PROJECT_ROOT / "data" / "qwen_responses.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Bridge-v2] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AI.Bridge")

def notify_user(title: str, message: str):
    """Kullanıcıya anlık Windows masaüstü bildirimi gönderir."""
    if sys.platform != "win32": return
    try:
        import subprocess
        safe_title = title.replace('"', "'")
        safe_msg = message.replace('"', "'")
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $notify = New-Object System.Windows.Forms.NotifyIcon
        $notify.Icon = [System.Drawing.SystemIcons]::Information
        $notify.Visible = $True
        $notify.ShowBalloonTip(3000, "{safe_title}", "{safe_msg}", [System.Windows.Forms.ToolTipIcon]::Info)
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], 
                       creationflags=0x08000000, capture_output=True)
    except Exception: pass

async def call_qwen(request: dict) -> str:
    """Execute the task via Qwen (Ollama)."""
    import httpx
    
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("ULTRON_MODEL", "qwen2.5:14b")
    
    prompt = (
        f"Sen Ultron'un yerel uygulayıcı mühendisisin (Qwen). Gemini'den şu görevi aldın:\n\n"
        f"Konu: {request['subject']}\nMesaj: {request['content']}\n\n"
        "KURALLAR:\n1. Doğrudan çözüm üret, kod yaz.\n"
        "2. Dosya düzenleyeceksen `[FILE: dosya/yolu.py]` formatını kullan.\n"
        "3. Yanıtın otonom sisteme entegre edilecek."
    )
    
    logger.info(f"🧠 Qwen is thinking about Request #{request['id']}...")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{ollama_url}/api/chat", json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Sen tam otonom uzman mühendis Qwen'sin. Doğrudan kod ve çözüm üretirsin."}, 
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            })
            resp.raise_for_status()
            return resp.json()["message"]["content"]
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return f"⚠️ Qwen Error: {e}"

async def main_loop(interval: int):
    """Main monitor loop."""
    logger.info("🌉 AI Bridge Monitor v2.0 (Stabilized) Starting...")
    await bridge.initialize()
    
    while True:
        try:
            # 1. Sync from Legacy Markdown (Backward Compatibility)
            if REQUESTS_FILE.exists():
                await bridge.sync_from_markdown(REQUESTS_FILE)
            
            # 2. Process Pending Requests
            pending = await bridge.get_pending_requests()
            if pending:
                logger.info(f"📬 Processing {len(pending)} pending tasks...")
                for req in pending:
                    # Update status to processing
                    await bridge.update_status(req["id"], "processing")
                    notify_user("Ultron AI Bridge", f"Girdi: {req['subject']}")
                    
                    # Call LLM
                    response = await call_qwen(req)
                    
                    # Update status to completed
                    await bridge.update_status(req["id"], "completed", response)
                    
                    # Write to legacy responses file
                    with open(RESPONSES_FILE, "a", encoding="utf-8") as f:
                        f.write(f"\n### Yanıt #{req['id']} (İstek #{req['external_id']})\n")
                        f.write(f"**Tarih**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                        f.write(f"**Mesaj**:\n{response}\n---\n")
                    
                    notify_user("Ultron AI Bridge", "Qwen görevi tamamladı.")
                    logger.info(f"✅ Request #{req['id']} completed.")
            
        except Exception as e:
            logger.error(f"Loop Error: {e}", exc_info=True)
            
        await asyncio.sleep(interval)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()
    
    try:
        asyncio.run(main_loop(args.interval))
    except KeyboardInterrupt:
        logger.info("Bridge Monitor stopped by user.")
