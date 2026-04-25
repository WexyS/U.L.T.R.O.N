
import asyncio
import edge_tts
import pygame
import tempfile
import os

async def test_tts():
    text = "Merhaba, ben Ultron. Ses sistemini test ediyorum."
    voice = "tr-TR-EmelNeural"
    communicate = edge_tts.Communicate(text, voice)
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        await communicate.save(tmp.name)
        
    print(f"Audio saved to {tmp.name}")
    
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(tmp.name)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        print("Success: Audio played")
    except Exception as e:
        print(f"Error playing audio: {e}")
    finally:
        pygame.mixer.quit()
        os.unlink(tmp.name)

if __name__ == "__main__":
    asyncio.run(test_tts())
