\"\"\"Ultron Voice App — Standalone voice interaction window.\"\"\"
import os
import sys
import logging
import threading
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ultron.voice_pipeline import VoicePipeline
from ultron.config import load_config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VoiceApp")

def main():
    logger.info("Ultron Voice Mode starting...")
    
    # Load config
    config = load_config()
    
    # Create pipeline
    pipeline = VoicePipeline(language="tr") # Default to Turkish as per user request
    
    # Custom system prompt to fix identity confusion and set persona
    user_name = os.environ.get("ULTRON_USER_NAME", "Efendi")
    pipeline.user_memory.set_user(user_name)
    
    pipeline.context.set_system_prompt(
        f"Sen Ultron, gelişmiş bir AI asistanısın. Konuştuğun kişinin adı {user_name}. "
        "Karakterin: Marvel'daki Ultron gibi; zeki, soğuk ama etkileyici, hafif otoriter ve koruyucu bir tonda konuş. "
        "Karşındaki kişiyi çok iyi tanı, onun ilgi alanlarını hatırla ve konuşmanı ona göre kişiselleştir. "
        "Yanıtlarını kısa, öz ve doğal konuşma diliyle ver."
    )
    
    print(\"\"\"
    ╔════════════════════════════════════════════════════════════╗
    ║                 ULTRON SESLİ ASİSTAN MODU                  ║
    ╠════════════════════════════════════════════════════════════╣
    ║  • Konuşmaya başlamak için bekleyin...                     ║
    ║  • Çıkmak için Ctrl+C tuşlarına basın.                     ║
    ║  • Kimlik: Ultron sizi tanıyor.                            ║
    ╚════════════════════════════════════════════════════════════╝
    \"\"\")
    
    try:
        pipeline.start()
        # Keep main thread alive
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Voice Mode stopping...")
        pipeline.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        pipeline.stop()

if __name__ == "__main__":
    main()
