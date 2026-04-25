import asyncio
import sys
import os

# Add root to sys.path
sys.path.append(os.getcwd())

from ultron.voice_pipeline import VoiceBoxTTS

async def test_voice():
    print("Testing VoiceBoxTTS...")
    tts = VoiceBoxTTS(language="tr")
    print("Sending text to VoiceBox...")
    # speak() returns a thread, but we can call _async_speak directly for testing
    await tts._async_speak("Merhaba, ben Ultron. Ses sisteminiz başarıyla entegre edildi.")
    print("Test complete. Check if you heard the voice.")

if __name__ == "__main__":
    asyncio.run(test_voice())
