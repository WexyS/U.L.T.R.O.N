import sys
import asyncio
import threading
import time

sys.stdout.reconfigure(encoding='utf-8')

# Test TTSEngine from ultron.tts_voice
try:
    from ultron.tts_voice import TTSEngine
    
    print("Testing TTSEngine...")
    engine = TTSEngine(voice="tr-TR-AhmetNeural")
    print(f"TTSEngine provider: {engine.provider_name}")
    print(f"TTSEngine available: {engine.available}")
    
    t = engine.speak("Merhaba, ben Ultron. Bu bir test mesajıdır.")
    if t:
        t.join(timeout=10)
        print("TTSEngine test completed.")
    else:
        print("TTSEngine speak returned None.")
except Exception as e:
    print(f"TTSEngine test failed: {e}")

print("-" * 50)

# Test VoiceBoxTTS from ultron.voice_pipeline
try:
    from ultron.voice_pipeline import VoiceBoxTTS
    
    print("Testing VoiceBoxTTS...")
    vb = VoiceBoxTTS(language="tr")
    
    t = vb.speak("Merhaba, ben Ultron. Ses modülü test ediliyor.")
    if t:
        t.join(timeout=10)
        print("VoiceBoxTTS test completed.")
    else:
        print("VoiceBoxTTS speak returned None.")
except Exception as e:
    print(f"VoiceBoxTTS test failed: {e}")
