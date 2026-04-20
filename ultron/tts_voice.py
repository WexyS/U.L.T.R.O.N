"""TTS motoru: OpenAI TTS (onyx, birincil) → edge-tts (yedek) → pyttsx3 (son çare).
Streaming destekli: ilk cümle bitince sesli okumaya başlar."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class OpenAITTS:
    """OpenAI TTS API — onyx sesi, streaming destekli."""

    def __init__(self, api_key: str = "", voice: str = "onyx", model: str = "tts-1"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.voice = voice
        self.model = model
        self._stop_event = threading.Event()
        self._playing = False
        self._lock = threading.Lock()
        self._available = bool(self.api_key)

    def speak_streaming(self, text_stream) -> threading.Thread: # type: ignore
        """Metin akışını sesli oku. Her cümle bitince hemen okumaya başlar."""
        self._stop_event.clear()
        with self._lock:
            self._playing = True
        t = threading.Thread(target=self._streaming_worker, args=(text_stream,), daemon=True) # type: ignore
        t.start()
        return t

    def speak(self, text: str) -> threading.Thread:
        """Tam metni sesli oku."""
        self._stop_event.clear()
        with self._lock:
            self._playing = True
        t = threading.Thread(target=self._worker, args=(text,), daemon=True)
        t.start()
        return t

    def _worker(self, text: str) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_speak(text))
            loop.close()
        except Exception as e:
            logger.warning("OpenAI TTS başarısız: %s", e)
        finally:
            with self._lock:
                self._playing = False

    async def _async_speak(self, text: str) -> None:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)

        clean = re.sub(r'[#*`_\[\](){}]', '', text)
        clean = clean.strip()
        if not clean:
            return

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()

        try:
            with client.audio.speech.with_streaming_response.create(
                model=self.model,
                voice=self.voice,
                input=clean[:4096],
            ) as response:
                response.stream_to_file(tmp.name)

            if self._stop_event.is_set():
                return

            self._play_mp3(tmp.name)
        except Exception as e:
            logger.warning("OpenAI TTS hatası: %s", e)
            raise
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def _streaming_worker(self, text_stream) -> None: # type: ignore
        """Cümle cümle sesli okur — daha hızlı yanıt."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_streaming_speak(text_stream)) # type: ignore
            loop.close()
        except Exception as e:
            logger.warning("OpenAI streaming TTS başarısız: %s", e)
        finally:
            with self._lock:
                self._playing = False

    async def _async_streaming_speak(self, text_stream) -> None: # type: ignore
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)

        sentence = ""
        tmp_files = []

        for chunk in text_stream: # type: ignore
            if self._stop_event.is_set():
                break

            sentence += chunk # type: ignore

            # Cümle bitti mi kontrol et (nokta, ünlem, soru işareti)
            if re.search(r'[.!?]\s*$', sentence) and len(sentence) > 20: # type: ignore
                clean = re.sub(r'[#*`_\[\](){}]', '', sentence).strip() # type: ignore
                if clean:
                    # Bu cümleyi sesli oku
                    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    tmp.close()
                    tmp_files.append(tmp.name) # type: ignore

                    try:
                        with client.audio.speech.with_streaming_response.create(
                            model=self.model,
                            voice=self.voice,
                            input=clean[:4096],
                        ) as response:
                            response.stream_to_file(tmp.name)

                        if self._stop_event.is_set():
                            break

                        self._play_mp3(tmp.name)
                    except Exception as e:
                        logger.warning("Streaming TTS hatası: %s", e)

                    sentence = ""

        # Kalan metni de oku
        if sentence.strip() and not self._stop_event.is_set(): # type: ignore
            clean = re.sub(r'[#*`_\[\](){}]', '', sentence).strip() # type: ignore
            if clean:
                tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                tmp.close()
                tmp_files.append(tmp.name) # type: ignore
                try:
                    with client.audio.speech.with_streaming_response.create(
                        model=self.model,
                        voice=self.voice,
                        input=clean[:4096],
                    ) as response:
                        response.stream_to_file(tmp.name)
                    if not self._stop_event.is_set():
                        self._play_mp3(tmp.name)
                except Exception as e:
                    logger.warning("Streaming TTS kalan metin hatası: %s", e)

        # Temp dosyalarını temizle
        for f in tmp_files: # type: ignore
            try:
                os.unlink(f) # type: ignore
            except OSError:
                pass

    def _play_mp3(self, filepath: str) -> None:
        """MP3 dosyasını pygame ile çal."""
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=24000, size=-16, channels=1)
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
            time.sleep(0.1)
        pygame.mixer.music.stop()
        try:
            pygame.mixer.quit()
        except Exception:
            pass

    def stop(self) -> None:
        self._stop_event.set()
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._playing


class EdgeTTS:
    """edge-tts — Microsoft'un ücretsiz TTS servisi."""

    def __init__(self, voice: str = "tr-TR-AhmetNeural"):
        self.voice = voice
        self._stop_event = threading.Event()
        self._playing = False
        self._lock = threading.Lock()

    def speak(self, text: str) -> threading.Thread:
        self._stop_event.clear()
        with self._lock:
            self._playing = True
        t = threading.Thread(target=self._worker, args=(text,), daemon=True)
        t.start()
        return t

    def _worker(self, text: str) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_speak(text))
            loop.close()
        except Exception as e:
            logger.warning("edge-tts başarısız: %s", e)
        finally:
            with self._lock:
                self._playing = False

    async def _async_speak(self, text: str) -> None:
        import edge_tts

        clean = re.sub(r'[#*`_\[\](){}]', '', text)
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        clean = clean.strip()
        if not clean:
            return

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()

        try:
            communicate = edge_tts.Communicate(clean, self.voice, rate="+0%")
            await communicate.save(tmp.name)

            if self._stop_event.is_set():
                return

            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1)
            pygame.mixer.music.load(tmp.name)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                await asyncio.sleep(0.1)
            pygame.mixer.music.stop()
            pygame.mixer.quit()

        except Exception as e:
            logger.warning("edge-tts oynatma hatası: %s", e)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def stop(self) -> None:
        self._stop_event.set()
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._playing


class LocalTTS:
    """pyttsx3 — tamamen çevrimdışı."""

    def __init__(self):
        self._engine = None
        self._available = True
        self._speaking = False
        self._init_voice()

    def _init_voice(self) -> None:
        try:
            import pyttsx3
            engine = pyttsx3.init() # type: ignore
            voices = engine.getProperty("voices") # type: ignore
            for v in voices: # type: ignore
                if "turkish" in v.name.lower() or "tr" in v.id.lower(): # type: ignore
                    engine.setProperty("voice", v.id) # type: ignore
                    break
            engine.setProperty("rate", 170) # type: ignore
            engine.setProperty("volume", 1.0) # type: ignore
            self._engine = engine # type: ignore
        except Exception as e:
            logger.warning("pyttsx3 başlatılamadı: %s", e)
            self._available = False

    def speak(self, text: str) -> threading.Thread:
        self._speaking = True

        def _worker():
            try:
                clean = re.sub(r'[#*`_\[\](){}]', '', text)
                if self._engine: # type: ignore
                    self._engine.say(clean) # type: ignore
                    self._engine.runAndWait() # type: ignore
            except Exception as e:
                logger.warning("pyttsx3 başarısız: %s", e)
            finally:
                self._speaking = False

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t

    def stop(self) -> None:
        if self._engine: # type: ignore
            try:
                self._engine.stop() # type: ignore
            except Exception:
                pass
        self._speaking = False

    @property
    def is_playing(self) -> bool:
        return self._speaking


class TTSEngine:
    """Çok katmanlı TTS: OpenAI (onyx) → edge-tts → pyttsx3.
    Streaming destekli — ilk cümle bitince sesli okumaya başlar."""

    def __init__(self, voice: str = "tr-TR-AhmetNeural", openai_api_key: str = ""):
        self._active = None
        self._name = ""

        # 1. OpenAI TTS (onyx) — en kaliteli
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            try:
                self.openai_tts = OpenAITTS(api_key=api_key, voice="onyx")
                self._active = self.openai_tts
                self._name = "openai/onyx"
                logger.info("TTS: OpenAI onyx")
                return
            except Exception as e:
                logger.warning("OpenAI TTS başlatılamadı: %s", e)

        # 2. edge-tts — ücretsiz, kaliteli
        try:
            import edge_tts  # type: ignore # noqa: F401
            self.edge_tts = EdgeTTS(voice=voice)
            self._active = self.edge_tts
            self._name = f"edge-tts/{voice}"
            logger.info("TTS: edge-tts (%s)", voice)
            return
        except ImportError:
            logger.warning("edge-tts kurulu değil")

        # 3. pyttsx3 — son çare
        self.local_tts = LocalTTS()
        if self.local_tts._available: # type: ignore
            self._active = self.local_tts
            self._name = "pyttsx3"
            logger.info("TTS: pyttsx3 (yerel)")

    @property
    def available(self) -> bool:
        return self._active is not None

    def speak(self, text: str) -> Optional[threading.Thread]:
        """Metni sesli oku."""
        if not self._active:
            return None
        return self._active.speak(text)

    def speak_streaming(self, text_stream) -> Optional[threading.Thread]: # type: ignore
        """Metin akışını sesli oku — daha hızlı yanıt için."""
        if not self._active:
            return None
        if hasattr(self._active, 'speak_streaming'):
            return self._active.speak_streaming(text_stream) # type: ignore
        # Streaming desteklemiyorsa tam metin olarak oku
        full_text = ""
        for chunk in text_stream: # type: ignore
            full_text += chunk # type: ignore
        return self._active.speak(full_text) # type: ignore

    def stop(self) -> None:
        if self._active:
            self._active.stop()

    @property
    def is_playing(self) -> bool:
        return self._active.is_playing if self._active else False

    @property
    def provider_name(self) -> str:
        return self._name
