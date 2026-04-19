import threading
import speech_recognition as sr
import time
from typing import Callable

class OfflineHotwordListener:
    """Sesli uyandırma kelimesi (Wake Word) dinleyicisi."""
    def __init__(self, hotword: str, callback: Callable, log_callback: Callable = None):
        self.hotword = hotword.lower()
        self.callback = callback
        self.log_callback = log_callback
        self.recognizer = sr.Recognizer()
        
        # Daha iyi algılama için eşik değerlerini ayarlıyoruz
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.running = False
        self.listen_thread = None

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        print(msg)

    def _listen_loop(self):
        with sr.Microphone() as source:
            self._log("> KALİBRASYON: Ortam gürültüsü analiz ediliyor... (1 sn bekleyin)")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            self._log("> MİKROFON AKTİF: Dinleniyor...")
            
            while self.running:
                try:
                    audio = self.recognizer.listen(source, timeout=1.0, phrase_time_limit=3.0)
                    self._log("> Ses girişi alındı, analiz ediliyor...")
                    
                    text = self.recognizer.recognize_google(audio, language="tr-TR").lower()
                    self._log(f"> DUYULAN METİN: '{text}'")
                    
                    wake_words = ["ultron", "altron", "oltron", "artron", "açıl", "uyan"]
                    if any(w in text for w in wake_words):
                        self._log("> WAKE WORD ONAYLANDI!")
                        self.callback()
                        time.sleep(2)
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    # Ses anlaşılamadı, loglamaya gerek yok kalabalık yapmasın
                    pass
                except Exception as e:
                    import traceback
                    self._log(f"> SES HATASI: {str(e)[:50]}")

    def start(self):
        if self.running:
            return
        self.running = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()

    def stop(self):
        self.running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
