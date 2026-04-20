"""Ultron Voice Pipeline — STT (Google + Whisper fallback) + VAD (Silero) + LLM (Ollama) + TTS (edge-tts) + Tool Calling + Global Skills/Agents."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Any
from ultron.v2.core.llm_router import LLMRouter

import numpy as np
import requests

from ultron.memory import ResponseCache, UserMemory

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Yapilandirma
# ──────────────────────────────────────────────────────────────────────────────
def _env_url(key: str, default: str) -> str:
    """Normalize local service URLs.

    On Windows, `localhost` may resolve to IPv6 and break some stacks.
    Prefer 127.0.0.1 by default.
    """
    raw = (os.environ.get(key) or "").strip()
    if raw:
        return raw.rstrip("/")
    return default.rstrip("/")

OLLAMA_URL = _env_url("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
VOICEBOX_URL = _env_url("ULTRON_VOICEBOX_URL", "http://127.0.0.1:17493")
WORKSPACE_URL = _env_url("ULTRON_WORKSPACE_URL", "http://127.0.0.1:8000")
MODEL = os.environ.get("ULTRON_MODEL", "qwen2.5:32b")
STT_ENGINE = os.environ.get("ULTRON_STT", "google")
LANGUAGE = os.environ.get("ULTRON_LANGUAGE", "en")  # "en" or "tr"

# Language-specific voice settings
VOICE_SETTINGS = {
    "en": {
        "stt_language": "en-US",
        "whisper_language": "en",
        "tts_voice": "en-US-JennyNeural",
        "system_prompt_suffix": "You are Ultron, a helpful AI assistant. Respond in English.",
    },
    "tr": {
        "stt_language": "tr-TR",
        "whisper_language": "tr",
        "tts_voice": "tr-TR-EmelNeural",
        "system_prompt_suffix": "Sen Ultron, yardimsever bir yapay zeka asistanisin. Turkce yanit ver.",
    },
}

_settings = VOICE_SETTINGS.get(LANGUAGE, VOICE_SETTINGS["en"])

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.03
SILENCE_TIMEOUT = 1.5
MAX_CONTEXT_MESSAGES = 6
LLM_TIMEOUT = 120
LLM_NUM_PREDICT = 512
LLM_TEMPERATURE = 0.1
AUDIO_GAIN = 10.0
BARGE_IN_DEBOUNCE = 2.0


# ──────────────────────────────────────────────────────────────────────────────
# Global Skills / Agents Kesfi
# ──────────────────────────────────────────────────────────────────────────────

def _discover_skills() -> list[dict]:
    """~/.qwen/skills/ ve proje skills/ dizinlerini tara."""
    skills: list[dict] = []
    search_dirs = [
        Path.home() / ".qwen" / "skills",
        Path(__file__).parent.parent / "skills",
    ]
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for skill_dir in sorted(search_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8", errors="replace")
                    desc = content[:300].strip()
                    skills.append({
                        "name": f"skill_{skill_dir.name}",
                        "description": f"Global skill: {skill_dir.name}. {desc}",
                        "path": str(skill_dir),
                        "skill_name": skill_dir.name,
                    })
                except Exception:
                    pass
    return skills


def _discover_agents() -> list[dict]:
    """~/.qwen/agents/ dizinindeki .md dosyalarını ve proje agents/ klasörlerini tara."""
    agents: list[dict] = []
    import re as _re

    search_dirs = [
        Path.home() / ".qwen" / "agents",
        Path(__file__).parent.parent / "agents",
    ]
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        # 1. Düz .md dosyaları (Qwen Code agent formatı)
        for md_file in sorted(search_dir.glob("*.md")):
            if md_file.name.startswith("."):
                continue
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
                name_match = _re.search(r'^name:\s*(.+)$', content, _re.MULTILINE)
                desc_match = _re.search(r'^description:\s*(.+)$', content, _re.MULTILINE)
                agent_name = name_match.group(1).strip() if name_match else md_file.stem
                desc = desc_match.group(1).strip() if desc_match else content[:300].strip()
                agents.append({
                    "name": f"agent_{agent_name}",
                    "description": f"Global agent: {agent_name}. {desc}",
                    "path": str(md_file),
                    "agent_name": agent_name,
                })
            except Exception:
                pass
        # 2. Klasör yapısı (eski format)
        for agent_dir in sorted(search_dir.iterdir()):
            if not agent_dir.is_dir() or agent_dir.name.startswith("."):
                continue
            for config_name in ["AGENT.md", "agent.json", "config.json"]:
                config_file = agent_dir / config_name
                if config_file.exists():
                    try:
                        content = config_file.read_text(encoding="utf-8", errors="replace")
                        desc = content[:300].strip()
                        agents.append({
                            "name": f"agent_{agent_dir.name}",
                            "description": f"Global agent: {agent_dir.name}. {desc}",
                            "path": str(agent_dir),
                            "agent_name": agent_dir.name,
                        })
                    except Exception:
                        pass
                    break
    return agents


_DISCOVERED_SKILLS = _discover_skills()
_DISCOVERED_AGENTS = _discover_agents()

logger.info("Kesfedilen: %d skill, %d agent", len(_DISCOVERED_SKILLS), len(_DISCOVERED_AGENTS))


# ──────────────────────────────────────────────────────────────────────────────
# Araç Bildirimleri
# ──────────────────────────────────────────────────────────────────────────────

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Windows'ta bir uygulama/program acar. Kullanici 'ac', 'baslat', 'calistir' gibi kelimelerle bir program istediginde BU ARACI CAGIR.",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Program adi. Orn: 'Steam', 'Google Chrome', 'Spotify', 'Discord', 'notepad', 'calc'"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "weather_report",
        "description": "Bir sehrin hava durumunu tarayicida acar.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "Sehir adi"}},
            "required": ["city"]
        }
    },
    {
        "name": "code_helper",
        "description": "Kod yazma, duzenleme, aciklama, calistirma ve hata ayiklama.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "write, edit, explain, run veya auto"},
                "description": {"type": "string", "description": "Ne yapilacagini acikla"},
                "language": {"type": "string", "description": "Programlama dili"},
                "file_path": {"type": "string", "description": "Dosya yolu"},
                "output_path": {"type": "string", "description": "Kaydetme yolu"},
                "code": {"type": "string", "description": "Ham kod"},
                "timeout": {"type": "integer", "description": "Zaman asimi saniye"}
            },
            "required": []
        }
    },
    {
        "name": "computer_settings",
        "description": "Ses, WiFi, pencere yonetimi, kapatma/yeniden baslatma gibi sistem ayarlarini kontrol eder.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Yapilacak eylem"},
                "description": {"type": "string", "description": "Dogal dil aciklama (orn: 'sesi artir', 'wifi'yi kapat')"},
                "value": {"type": "string", "description": "Opsiyonel deger"}
            },
            "required": []
        }
    },
    {
        "name": "web_search",
        "description": "Internette arama yapar ve sonuclari ozetler.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Arama sorgusu"}},
            "required": ["query"]
        }
    },
    {
        "name": "get_system_info",
        "description": "Sistem bilgilerini doner: saat, tarih, CPU, RAM, disk.",
        "parameters": {
            "type": "object",
            "properties": {
                "info_type": {
                    "type": "string",
                    "enum": ["time", "cpu", "memory", "disk", "all"],
                    "description": "Bilgi turu"
                }
            },
            "required": []
        }
    },
    {
        "name": "read_file",
        "description": "Bir dosyanin icerigini okur.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Dosya yolu"}},
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Bir dosyaya icerik yazar.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Dosya yolu"},
                "content": {"type": "string", "description": "Icerik"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_directory",
        "description": "Bir dizinin icerigini listeler.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Dizin yolu"}},
            "required": []
        }
    },
    {
        "name": "execute_python",
        "description": "Python kodu calistirir.",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python kodu"}},
            "required": ["code"]
        }
    },
    {
        "name": "ask_architect",
        "description": "Kendi basina cozemeyecegin zor kod hatalarinda, inatci bug'larda veya karmasik yazilim mimarisi kararlarinda bulut tabanli kidemli mimara (Gemini) danis.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Mimara acikca soracagin soru veya yardim istedigin konu"},
                "code_context": {"type": "string", "description": "Varsa uzerinde calistigin kod parcasi veya hata ciktisi (error log)"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "deep_research",
        "description": "Verilen bir konuyu internette derinlemesine arastirir. Sadece aramakla kalmaz, baglantilarin icine girip makaleleri okuyarak sana kapsamli bir rapor cikarir.",
        "parameters": {
            "type": "object",
            "properties": {"topic": {"type": "string", "description": "Detayli arastirilacak konu"}},
            "required": ["topic"]
        }
    },
    {
        "name": "clone_website",
        "description": "Verilen URL'deki web sitesini klonlar, UI bilesenlerini cikarir (Workspace sistemini kullanir). Kullanici bir siteyi kopyalamak veya klonlamak istediginde cagir.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Klonlanacak sitenin URL'si (orn: https://example.com)"}},
            "required": ["url"]
        }
    },
    {
        "name": "generate_app",
        "description": "Kullanicinin verdigi fikre gore sifirdan bir uygulama/web sitesi uretir (Workspace sistemini kullanir).",
        "parameters": {
            "type": "object",
            "properties": {"idea": {"type": "string", "description": "Uygulama fikri (orn: karanlik modlu todo list)"}},
            "required": ["idea"]
        }
    },
]

# Kesfedilen skill'leri arac olarak ekle
for _skill in _DISCOVERED_SKILLS:
    TOOL_DECLARATIONS.append({
        "name": _skill["name"],
        "description": _skill["description"],
        "parameters": {
            "type": "object",
            "properties": {"input": {"type": "string", "description": "Skill'e girdi"}},
            "required": []
        }
    })

# Kesfedilen agent'lari arac olarak ekle
for _agent in _DISCOVERED_AGENTS:
    TOOL_DECLARATIONS.append({
        "name": _agent["name"],
        "description": _agent["description"],
        "parameters": {
            "type": "object",
            "properties": {"task": {"type": "string", "description": "Agent'a gorev"}},
            "required": ["task"]
        }
    })


# ──────────────────────────────────────────────────────────────────────────────
# STT — Google Web Speech API (oncelikli)
# ──────────────────────────────────────────────────────────────────────────────

class GoogleSTT:
    """Google Web Speech API ile konusmayi metne cevir. Ucretsiz, coklu dil."""

    def __init__(self, language: str = "en-US"):
        self.language = language
        self._available = self._check_availability()

    @property
    def available(self) -> bool:
        return self._available

    def _check_availability(self) -> bool:
        try:
            import speech_recognition as sr  # noqa: F401
            return True
        except ImportError:
            logger.warning("speech_recognition kutuphanesi bulunamadi. 'pip install SpeechRecognition'")
            return False

    def transcribe(self, audio_bytes: bytes) -> str:
        """int16 PCM bytes -> metin. Google Web Speech API kullanir."""
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            # int16 PCM'i dogru sekilde AudioData'ya cevir
            # (sample_rate, sample_width=2 for int16)
            audio_data = sr.AudioData(audio_bytes, SAMPLE_RATE, 2)

            # Google Web Speech API
            text = recognizer.recognize_google(audio_data, language=self.language)
            return text.strip() if text else ""
        except sr.RequestError:
            logger.warning("Google STT erisim hatasi (internet kontrol et)")
            return ""
        except sr.UnknownValueError:
            logger.debug("Google STT ses anlayamadi")
            return ""
        except Exception as e:
            logger.warning("Google STT basarisiz: %s", e)
            return ""


# ──────────────────────────────────────────────────────────────────────────────
# STT — OpenAI Whisper (yedek)
# ──────────────────────────────────────────────────────────────────────────────

class WhisperSTT:
    """OpenAI Whisper ile yerel konusma tanima. Google basarisiz oldugunda devreye girer."""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self._model = None
        self._device = None
        self._available = False
        self._init_model()

    @property
    def available(self) -> bool:
        return self._available

    def _init_model(self):
        try:
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
            import torch
            import whisper

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = whisper.load_model(self.model_name, device=self._device)
            self._available = True
            logger.info("Whisper '%s' yuklendi (%s)", self.model_name, self._device.upper())
        except ImportError:
            logger.warning("Whisper yuklenemedi. 'pip install openai-whisper torch'")
        except Exception as e:
            logger.warning("Whisper baslatma hatasi: %s", e)

    def transcribe(self, audio_bytes: bytes) -> str:
        if not self._available or len(audio_bytes) < SAMPLE_RATE * 0.2:
            return ""

        tmp_path = None
        try:
            import wave

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_bytes)

            result = self._model.transcribe(
                tmp_path,
                language=_settings["whisper_language"],
                task="transcribe",
                fp16=(self._device == "cuda"),
                verbose=False,
                temperature=0.0,
                beam_size=3,
                no_speech_threshold=0.6,
            )
            return result.get("text", "").strip()
        except Exception as e:
            logger.error("Whisper transkripsiyon hatasi: %s", e)
            return ""
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


# ──────────────────────────────────────────────────────────────────────────────
# VAD — Silero Voice Activity Detection
# ──────────────────────────────────────────────────────────────────────────────

class SileroVAD:
    """Silero VAD ile konusma tespiti. Esik degeri 0.3 (hassas)."""

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        self._model = None
        self._available = False
        self._init_model()

    @property
    def available(self) -> bool:
        return self._available

    def _init_model(self):
        try:
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
            import torch

            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                trust_repo=True,
            )
            self._model = model
            self._available = True
            dev = "CUDA" if torch.cuda.is_available() else "CPU"
            logger.info("Silero VAD yuklendi (%s, esik=%.2f)", dev, self.threshold)
        except Exception as e:
            logger.warning("Silero VAD yuklenemedi: %s. Enerji tabanli yedek kullanilacak.", e)

    def is_speech(self, audio_chunk: np.ndarray) -> float:
        """Konusma olasiligini dondur [0.0, 1.0]."""
        if not self._available or self._model is None:
            return self._energy_vad(audio_chunk)
        import torch
        try:
            tensor = torch.from_numpy(audio_chunk).float()
            with torch.no_grad():
                prob = self._model(tensor, SAMPLE_RATE).item()
            return prob
        except Exception:
            return self._energy_vad(audio_chunk)

    @staticmethod
    def _energy_vad(audio_chunk: np.ndarray) -> float:
        """Basit enerji tabanli yedek VAD."""
        energy = np.mean(np.abs(audio_chunk))
        return min(energy * 20, 1.0)


# ──────────────────────────────────────────────────────────────────────────────
# TTS — edge-tts + Pygame
# ──────────────────────────────────────────────────────────────────────────────

class EdgeTTS:
    """edge-tts ile metin-okuma. Pygame ile ses calma, barge-in destekli."""

    def __init__(self, voice: str = "en-US-JennyNeural"):
        self.voice = voice
        self._stop_event = threading.Event()
        self._playing = False
        self._lock = threading.Lock()
        self._available = self._check_availability()

    @staticmethod
    def _check_availability() -> bool:
        try:
            import edge_tts  # noqa: F401
            import pygame   # noqa: F401
            return True
        except ImportError as e:
            logger.warning("edge-tts veya pygame eksik: %s", e)
            return False

    def speak(self, text: str) -> threading.Thread:
        """Metni sesli oku. Barge-in icin _stop_event kullan."""
        self._stop_event.clear()
        with self._lock:
            self._playing = True
        t = threading.Thread(target=self._worker, args=(text,), daemon=True)
        t.start()
        return t

    def _worker(self, text: str):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_speak(text))
            loop.close()
        except Exception as e:
            logger.warning("edge-tts basarisiz: %s", e)
        finally:
            with self._lock:
                self._playing = False

    async def _async_speak(self, text: str):
        import edge_tts
        import pygame

        # Markdown ve ozel karakterleri temizle
        clean = re.sub(r"[#*`_\[\](){}]", "", text)
        clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
        if not clean:
            return

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()

        try:
            # MARVEL ULTRON VOICE: Lower pitch (-15Hz), slightly faster (+5%) for that clinical but menacing tone
            communicate = edge_tts.Communicate(clean, self.voice, rate="+5%", pitch="-15Hz")
            await communicate.save(tmp.name)

            if self._stop_event.is_set():
                return

            pygame.mixer.init(frequency=24000, size=-16, channels=1)
            pygame.mixer.music.load(tmp.name)
            pygame.mixer.music.play()

            # Barge-in: kullanan konusursa durdur
            while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                await asyncio.sleep(0.1)

            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception as e:
            logger.warning("edge-tts oynatma hatasi: %s", e)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def stop(self):
        """Sesi durdur (barge-in icin)."""
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

class VoiceBoxTTS:
    """VoiceBox API ile TTS. Basarisiz olursa EdgeTTS'e duser. Pygame ile oynatir."""
    def __init__(self, language: str = "tr", fallback_voice: str = "tr-TR-EmelNeural"):
        self.language = language
        self.fallback = EdgeTTS(voice=fallback_voice)
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
        
    def _worker(self, text: str):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_speak(text))
            loop.close()
        except Exception as e:
            logger.warning("VoiceBoxTTS basarisiz: %s", e)
        finally:
            with self._lock:
                self._playing = False
                
    async def _async_speak(self, text: str):
        # Clean text
        import re
        import pygame
        import httpx
        clean = re.sub(r"[#*`_\[\](){}]", "", text)
        clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
        if not clean: return
        
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        
        used_fallback = False
        try:
            # 1. Try VoiceBox
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{VOICEBOX_URL}/generate", json={"text": clean, "language": self.language})
                if resp.status_code == 200:
                    with open(tmp.name, "wb") as f:
                        f.write(resp.content)
                else:
                    used_fallback = True
        except Exception as e:
            logger.debug(f"VoiceBox unavailable: {e}")
            used_fallback = True
            
        if used_fallback:
            # Fallback to EdgeTTS but inside our async context
            # We just delegate to the fallback entirely and return
            self.fallback._stop_event = self._stop_event # Share stop event
            await self.fallback._async_speak(clean)
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            return

        # Play VoiceBox Audio
        if self._stop_event.is_set():
            return
            
        try:
            pygame.mixer.init(frequency=24000, size=-16, channels=1)
            pygame.mixer.music.load(tmp.name)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                await asyncio.sleep(0.1)
                
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception as e:
            logger.warning("VoiceBox oynatma hatasi: %s", e)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
                
    def stop(self):
        self._stop_event.set()
        self.fallback.stop()
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._playing or self.fallback.is_playing


# ──────────────────────────────────────────────────────────────────────────────
# Baglam Yoneticisi
# ──────────────────────────────────────────────────────────────────────────────

class ContextManager:
    """Mesaj gecmisini yonet. Maksimum 8 mesaj + sistem promptu."""

    def __init__(self, max_messages: int = MAX_CONTEXT_MESSAGES):
        self.max_messages = max_messages
        self._messages: list[dict] = []
        self._lock = threading.Lock()

    def set_system_prompt(self, prompt: str):
        with self._lock:
            if self._messages and self._messages[0]["role"] == "system":
                self._messages[0]["content"] = prompt
            else:
                self._messages.insert(0, {"role": "system", "content": prompt})

    def add_user_message(self, text: str):
        with self._lock:
            self._messages.append({"role": "user", "content": text})
            self._trim()

    def add_assistant_message(self, text: str):
        with self._lock:
            self._messages.append({"role": "assistant", "content": text})
            self._trim()

    def add_tool_result(self, tool_name: str, result: str):
        with self._lock:
            self._messages.append({
                "role": "tool",
                "tool_call_id": tool_name,
                "content": result,
            })
            self._trim()

    def get_messages(self) -> list[dict]:
        with self._lock:
            return list(self._messages)

    def _trim(self):
        """Sistem promptunu koruyarak en eski mesajlari kirp."""
        if len(self._messages) > self.max_messages + 1:
            system = self._messages[0]
            self._messages = [system] + self._messages[-(self.max_messages):]

    def clear(self):
        with self._lock:
            self._messages.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Ana Pipeline
# ──────────────────────────────────────────────────────────────────────────────

class VoicePipeline:
    """
    Ultron sesli asistan pipeline'i.

    Akis:
      1. Silero VAD ile konusma tespiti
      2. Google STT ile metne cevirme (basarisizsa Whisper)
      3. Ollama LLM ile yanit uretme (tool calling destekli)
      4. edge-tts ile sesli yanit (barge-in destekli)
    """

    class State:
        IDLE = "idle"
        LISTENING = "listening"
        TRANSCRIBING = "transcribing"
        THINKING = "thinking"
        SPEAKING = "speaking"
        PROCESSING = "processing"

    def __init__(
        self,
        response_cache: Optional[ResponseCache] = None,
        user_memory: Optional[UserMemory] = None,
        language: str = "tr",
        auto_respond: bool = True,
        input_device: Optional[int] = None,
        llm_router: Optional[LLMRouter] = None,
    ):
        self.response_cache = response_cache or ResponseCache()
        self.user_memory = user_memory or UserMemory()
        self.self_learning = SelfLearning(self.user_memory, llm=llm_router or LLMRouter(ollama_model=MODEL))
        self.auto_respond = auto_respond
        self.language = language
        self.input_device = input_device
        
        # Initialize LLMRouter
        self.llm_router = llm_router or LLMRouter(ollama_model=MODEL)
        if not llm_router:
            self.llm_router.enable_all_providers(dict(os.environ))

        # STT: Google (oncelikli) -> Whisper (yedek)
        self.stt_primary = GoogleSTT(language=_settings["stt_language"])
        self.stt_fallback = WhisperSTT(model_name="base")

        # VAD
        self.vad = SileroVAD(threshold=SILENCE_THRESHOLD)

        # TTS (VoiceBox primarily, EdgeTTS fallback)
        self.tts = VoiceBoxTTS(language=language, fallback_voice=_settings["tts_voice"])

        # Baglam
        system_prompt = self._build_system_prompt()
        self.context = ContextManager(max_messages=MAX_CONTEXT_MESSAGES)
        self.context.set_system_prompt(system_prompt)

        # Durum yonetimi
        self._lock = threading.RLock()
        self._state = self.State.IDLE
        self._mic_enabled = False
        self._processing = False
        self._cancel_requested = False

        # Ses kayit durumu
        self._audio_buffer = bytearray()
        self._speaking_detected = False
        self._silence_start: Optional[float] = None
        self._speech_start_time: Optional[float] = None
        self._last_speech_time = 0.0

        # Callback'ler
        self.on_state_change: Optional[Callable[[str], None]] = None
        self.on_user_text: Optional[Callable[[str], None]] = None
        self.on_assistant_text: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # Araclar
        self._tool_handlers = self._build_tool_handlers()

        # Ses donanim kontrolu
        self._audio_available = self._check_audio()
        if not self._audio_available:
            logger.warning("Mikrofon veya ses cihazi bulunamadi. Sesli mod devre disi.")

        self._listen_thread: Optional[threading.Thread] = None

    # ── Sistem Promptu ────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Ultron v2.0 sistem promptu — prompt.txt'den yüklenir."""
        # prompt.txt dosyasını bul
        prompt_file = None
        candidates = [
            Path(__file__).parent.parent / "ultron" / "v2" / "core" / "prompt.txt",
            Path(__file__).parent / "v2" / "core" / "prompt.txt",
            Path(__file__).parent.parent / "PROMPT.txt",
            Path(__file__).parent.parent / "prompt.txt",
        ]
        for pp in candidates:
            if pp.exists():
                prompt_file = pp
                break

        if prompt_file:
            try:
                base = prompt_file.read_text(encoding="utf-8").strip()
            except Exception:
                base = None
        else:
            base = None

        if not base:
            base = (
                "Sen Ultron'sin. Kişisel yapay zeka asistanısın.\n"
                "Kullanıcı hangi dilde yazarsa o dilde cevap ver.\n"
                "Kısa, net ve yardımsever ol."
            )

        # Araç listesini ekle
        tools = "\n\nARACLAR:\n"
        tools += "- open_app(app_name): Uygulama aç\n"
        tools += "- web_search(query): Web araması\n"
        tools += "- get_system_info(info_type): Sistem bilgisi\n"
        tools += "- read_file/write_file: Dosya okuma/yazma\n"
        tools += "- execute_python(code): Python çalıştır\n"
        tools += "- list_directory(path): Dizin listele\n"

        if _DISCOVERED_SKILLS:
            skills = ", ".join(s["skill_name"] for s in _DISCOVERED_SKILLS[:10])
            tools += f"\nSkills: {skills}\n"
        if _DISCOVERED_AGENTS:
            agents = ", ".join(a["agent_name"] for a in _DISCOVERED_AGENTS[:10])
            tools += f"\nAgents: {agents}\n"

        # Language suffix for system prompt
        tools += f"\n{_settings['system_prompt_suffix']}"

        return base + tools

    # ── Donanim Kontrol ───────────────────────────────────────────────────

    def _check_audio(self) -> bool:
        """Mikrofon/ses cihazi varligini kontrol et."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            # Giris cihazi (microphone) var mi?
            for dev in devices:
                if dev.get("max_input_channels", 0) > 0:
                    return True
            logger.warning("Giris cihazi (mikrofon) bulunamadi.")
            return False
        except Exception as e:
            logger.warning("Ses cihazi kontrolu basarisiz: %s", e)
            return False

    @staticmethod
    def list_input_devices() -> list[dict]:
        """List all available input (microphone) devices with their index, name, and max input channels.

        Use this to identify the correct device index to pass to VoicePipeline(input_device=N).
        """
        import sounddevice as sd
        devices = sd.query_devices()
        input_devs = []
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                input_devs.append({
                    "index": idx,
                    "name": dev["name"],
                    "max_input_channels": dev["max_input_channels"],
                    "default_samplerate": dev.get("default_samplerate", "N/A"),
                    "is_default": idx == sd.default.device[0],
                })
        return input_devs

    # ── Araç Isleme ───────────────────────────────────────────────────────

    def _build_tool_handlers(self) -> dict:
        """Araç çalıştırıcıları — ultron.actions modüllerini kullanır."""
        return {
            "open_app": self._tool_open_app,
            "web_search": self._tool_web_search,
            "get_system_info": self._tool_get_system_info,
            "read_file": self._tool_read_file,
            "write_file": self._tool_write_file,
            "list_directory": self._tool_list_directory,
            "execute_python": self._tool_execute_python,
            "weather_report": self._tool_weather_report,
            "code_helper": self._tool_code_helper,
            "computer_settings": self._tool_computer_settings,
            "ask_architect": self._tool_ask_architect,
            "deep_research": self._tool_deep_research,
            "clone_website": self._tool_clone_website,
            "generate_app": self._tool_generate_app,
        }

    def _tool_open_app(self, args: dict) -> str:
        """Windows'ta uygulama ac."""
        app_name = args.get("app_name", "").strip()
        if not app_name:
            return "Uygulama adi belirtilmedi."
        try:
            import subprocess
            subprocess.Popen(f'start "" "{app_name}"', shell=True)
            return f"{app_name} aciliyor."
        except Exception as e:
            return f"{app_name} acilamadi: {e}"

    def _tool_web_search(self, args: dict) -> str:
        """DuckDuckGo ile web aramasi."""
        query = args.get("query", "").strip()
        if not query:
            return "Arama sorgusu belirtilmedi."
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            if not results:
                return f"'{query}' icin sonuc bulunamadi."
            parts = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                body = r.get("body", "")[:200]
                url = r.get("href", "")
                if title and body:
                    parts.append(f"{i}. {title}\n   {body}\n   {url}")
            return "\n\n".join(parts)
        except Exception as e:
            return f"Arama hatasi: {e}"

    def _tool_get_system_info(self, args: dict) -> str:
        """Sistem bilgileri: saat, CPU, RAM, disk."""
        import time
        info_type = args.get("info_type", "all")
        parts = []

        if info_type in ("time", "all"):
            parts.append(f"Saat: {time.strftime('%H:%M:%S')}")
            parts.append(f"Tarih: {time.strftime('%d.%m.%Y')}")

        if info_type in ("cpu", "memory", "disk", "all"):
            try:
                import psutil
                if info_type in ("cpu", "all"):
                    cpu_pct = psutil.cpu_percent(interval=0.5)
                    parts.append(f"CPU: %{cpu_pct}")
                if info_type in ("memory", "all"):
                    mem = psutil.virtual_memory()
                    parts.append(
                        f"RAM: %{mem.percent} "
                        f"({mem.used // 1024**3}GB/{mem.total // 1024**3}GB)"
                    )
                if info_type in ("disk", "all"):
                    disk = psutil.disk_usage("C:")
                    parts.append(f"Disk: %{disk.percent} ({disk.free // 1024**3}GB bos)")
            except ImportError:
                parts.append("psutil kurulu degil")

        return ". ".join(parts)

    def _tool_read_file(self, args: dict) -> str:
        """Dosya oku."""
        path = args.get("path", "").strip()
        if not path:
            return "Dosya yolu belirtilmedi."
        try:
            full_path = os.path.abspath(path)
            if not os.path.exists(full_path):
                return f"Dosya bulunamadi: {full_path}"
            if os.path.getsize(full_path) > 50 * 1024:
                return "Dosya cok buyuk (50KB uzeri)."
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(3000)
            return content[:2000]
        except Exception as e:
            return f"Okuma hatasi: {e}"

    def _tool_write_file(self, args: dict) -> str:
        """Dosya yaz."""
        path = args.get("path", "").strip()
        content = args.get("content", "")
        if not path:
            return "Dosya yolu belirtilmedi."
        try:
            full_path = os.path.abspath(path)
            os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Yazildi: {full_path}"
        except Exception as e:
            return f"Yazma hatasi: {e}"

    def _tool_list_directory(self, args: dict) -> str:
        """Dizin listele."""
        path = args.get("path", ".").strip()
        try:
            full_path = os.path.abspath(path)
            if not os.path.isdir(full_path):
                return f"Dizin bulunamadi: {full_path}"
            items = []
            for item in sorted(os.listdir(full_path))[:30]:
                full = os.path.join(full_path, item)
                prefix = "[D]" if os.path.isdir(full) else "[F]"
                items.append(f"{prefix} {item}")
            return f"{full_path}:\n" + "\n".join(items)
        except Exception as e:
            return f"Hata: {e}"

    def _tool_execute_python(self, args: dict) -> str:
        """Python kodu calistir."""
        code = args.get("code", "").strip()
        if not code:
            return "Kod belirtilmedi."
        try:
            import subprocess
            import sys
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=15,
            )
            out = result.stdout.strip()
            err = result.stderr.strip()
            if result.returncode == 0:
                return (out or "(cikti yok)")[:1000]
            return f"Hata: {err[:500]}"
        except subprocess.TimeoutExpired:
            return "Zaman asimi (15s)."
        except Exception as e:
            return f"Hata: {e}"

    def _tool_weather_report(self, args: dict) -> str:
        """Hava durumu sayfasını tarayıcıda açar."""
        try:
            from ultron.actions.weather_report import run as weather_run
            return weather_run(parameters={"city": args.get("city", "")})
        except Exception as e:
            return f"Hava durumu hatası: {e}"

    def _tool_code_helper(self, args: dict) -> str:
        """Kod yazma, düzenleme, açıklama, çalıştırma."""
        try:
            from ultron.actions.code_helper import run as code_run
            return code_run(parameters=args)
        except Exception as e:
            return f"Kod yardımcısı hatası: {e}"

    def _tool_computer_settings(self, args: dict) -> str:
        """Sistem ayarlarını kontrol eder."""
        try:
            from ultron.actions.computer_settings import run as settings_run
            return settings_run(parameters=args)
        except Exception as e:
            return f"Sistem ayarları hatası: {e}"

    def _tool_ask_architect(self, args: dict) -> str:
        """Bulut tabanli mimara (Gemini) danisir."""
        try:
            from ultron.actions.ask_architect import run as ask_run
            return ask_run(parameters=args)
        except Exception as e:
            return f"Mimar araci hatasi: {e}"

    def _tool_deep_research(self, args: dict) -> str:
        """Derinlemesine internet arastirmasi yapar."""
        try:
            from ultron.actions.deep_research import run as research_run
            return research_run(parameters=args)
        except Exception as e:
            return f"Derin arastirma hatasi: {e}"

    def _tool_clone_website(self, args: dict) -> str:
        """Workspace API uzerinden site klonlar."""
        url = args.get("url", "").strip()
        if not url:
            return "URL belirtilmedi."
        try:
            response = requests.post(
                f"{WORKSPACE_URL}/api/v2/workspace/clone",
                json={"url": url, "extract_components": True},
                timeout=60,
            )
            if response.status_code == 200:
                return f"{url} basariyla klonlandi ve bilesenlerine ayrildi."
            return f"Klonlama basarisiz: {response.text}"
        except Exception as e:
            return f"Klonlama sirasinda Workspace API hatasi: {e}"

    def _tool_generate_app(self, args: dict) -> str:
        """Workspace API uzerinden uygulama uretir."""
        idea = args.get("idea", "").strip()
        if not idea:
            return "Fikir belirtilmedi."
        try:
            response = requests.post(
                f"{WORKSPACE_URL}/api/v2/workspace/generate",
                json={"idea": idea, "tech_stack": "html-css-js"},
                timeout=120,
            )
            if response.status_code == 200:
                return f"Uygulama basariyla uretildi: {idea}. Ayrintilar workspace dizininde."
            return f"Uretim basarisiz: {response.text}"
        except Exception as e:
            return f"Uretim sirasinda Workspace API hatasi: {e}"

    def _make_skill_handler(self, skill: dict):
        """Skill icin dinamik handler olustur."""
        def handler(args: dict):
            skill_path = Path(skill["path"])
            skill_md = skill_path / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8", errors="replace")
                return f"Skill '{skill['skill_name']}' yuklendi:\n{content[:500]}"
            return f"Skill '{skill['skill_name']}' SKILL.md bulunamadi."
        return handler

    def _make_agent_handler(self, agent: dict):
        """Agent icin dinamik handler olustur."""
        def handler(args: dict):
            task = args.get("task", "")
            agent_path = Path(agent["path"])
            for cfg in ["AGENT.md", "agent.json", "config.json"]:
                cfg_file = agent_path / cfg
                if cfg_file.exists():
                    content = cfg_file.read_text(encoding="utf-8", errors="replace")
                    return f"Agent '{agent['agent_name']}' bulundu. Gorev: {task}\nConfig: {content[:500]}"
            return f"Agent '{agent['agent_name']}' bulundu. Gorev: {task}"
        return handler

    def _execute_tool(self, name: str, args: dict) -> str:
        """Arac ismine gore uygun handler'i cagir."""
        # Kesfedilen skill/agent'lari once kontrol et
        for skill in _DISCOVERED_SKILLS:
            if skill["name"] == name:
                return self._make_skill_handler(skill)(args)
        for agent in _DISCOVERED_AGENTS:
            if agent["name"] == name:
                return self._make_agent_handler(agent)(args)

        handler = self._tool_handlers.get(name)
        if handler:
            return handler(args)
        return f"Bilinmeyen arac: {name}"

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def mic_enabled(self) -> bool:
        return self._mic_enabled

    def enable_mic(self):
        """Mikrofonu ac ve dinleme dongusunu baslat."""
        if not self._audio_available:
            logger.warning("Mikrofon veya ses cihazi bulunamadi. Sesli mod calismayacak.")
            if self.on_error:
                self.on_error("Mikrofon bulunamadi. Lutfen bir giris cihazi baglayin.")
            return
        self._mic_enabled = True
        if not self._processing:
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()

    def disable_mic(self):
        """Mikrofonu kapat ve aktif kaydı iptal et."""
        self._mic_enabled = False
        with self._lock:
            self._cancel_requested = True
            self._audio_buffer.clear()
            self._speaking_detected = False
            self._silence_start = None
            self._speech_start_time = None

    def toggle_mic(self):
        """Mikrofonu ac/kapat."""
        if self._mic_enabled:
            self.disable_mic()
        else:
            self.enable_mic()

    def stop(self):
        """Pipeline'i tamamen durdur."""
        self._mic_enabled = False
        self._cancel_requested = True
        self.tts.stop()

    def cancel(self):
        """Mevcut islemi iptal et."""
        with self._lock:
            self._cancel_requested = True
        self.tts.stop()

    def send_text(self, text: str):
        """Yazi ile soru gonder (mikrofon disinda kullanim icin)."""
        if self.on_user_text:
            self.on_user_text(text)
        self._process_response(text)

    def _resample_16k(self, audio: np.ndarray, src_sr: int) -> np.ndarray:
        """Hızlı ses örnekleme oranı dönüştürme (16kHz'ye)."""
        if src_sr == 16000:
            return audio
        try:
            import scipy.signal as sig
            return sig.resample_poly(audio, 16000, src_sr)
        except ImportError:
            # SciPy yoksa basit decimation/interpolation
            if src_sr % 16000 == 0:
                return audio[:: (src_sr // 16000)]
            # Lineer interpolasyon (yaklaşık)
            old_len = len(audio)
            new_len = int(old_len * 16000 / src_sr)
            old_x = np.arange(old_len)
            new_x = np.linspace(0, old_len - 1, new_len)
            return np.interp(new_x, old_x, audio)

    # ── Dinleme Dongusu (FIXED VERSION) ──────────────────────────────────

    def _select_input_device(self):
        """En uygun mikrofon cihazini sec.

        1. Varsayilan cihazi kullan (kullanici zaten Windows'tan dogru
           cihazi secmis olmalidir)
        2. 16kHz desteklenmiyorsa en dusuk desteklendigi orani kullan
        """
        import sounddevice as sd

        default_input = sd.query_devices(kind="input")
        logger.info("Varsayilan giris cihazi: %s (%d kanal, %.0f Hz)",
                    default_input["name"],
                    default_input.get("max_input_channels", 2),
                    default_input.get("default_samplerate", 16000))
        return None, default_input.get("max_input_channels", 2)

    def _listen_loop(self):
        """Ana dinleme dongusu — sounddevice callback ile ses yakalama.

        FIXES APPLIED:
        1. _select_input_device() ile dogru mikrofon cihazi secilir
        2. Stereo cihazlarda tum kanallarortalanir (was: sadece [:, 0])
        3. blocksize=None ile otomatik optimal deger (was: hardcoded 512)
        4. debug_counter thread-safe (was: hasattr/instance attribute race)
        5. RMS + Peak debug logging (was: print to stdout)
        6. Sample rate fallback: 16kHz desteklenmiyorsa yerel oranda acilir
        """
        import sounddevice as sd

        self._set_state(self.State.LISTENING)

        # Tamponu sifirla
        with self._lock:
            self._audio_buffer.clear()
            self._speaking_detected = False
            self._silence_start = None
            self._speech_start_time = None

        # FIX #1: Cihaz secimi
        device_id, num_channels = self._select_input_device()

        # FIX #4: Thread-safe debug sayaci (closure ile)
        debug_counter = [0]
        
        # Sample rate tespiti
        dev_info = sd.query_devices(device_id) if device_id is not None else sd.query_devices(kind="input")
        native_sr = int(dev_info.get("default_samplerate", SAMPLE_RATE))
        use_sr = SAMPLE_RATE
        
        # 16kHz desteklenmiyorsa yerel orani kullan
        if native_sr != SAMPLE_RATE:
            logger.warning("Cihaz 16000 Hz desteklemiyor (%d Hz). Dönüştürme uygulanacak.", native_sr)
            use_sr = native_sr

        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.debug("Ses durumu: %s", status)

            with self._lock:
                cancel = self._cancel_requested
                mic_on = self._mic_enabled
                proc = self._processing
                speaking = self.tts.is_playing

            if cancel or not mic_on:
                return

            # ── FIX #2: Audio Normalization ────────────────────────────
            if indata.ndim == 2:
                if indata.shape[1] == 1:
                    audio_float = indata[:, 0].astype(np.float32) / 32768.0
                else:
                    audio_float = indata.astype(np.float32).mean(axis=1) / 32768.0
            else:
                audio_float = indata.astype(np.float32) / 32768.0
                
            # FIX #6: Oran dönüştürme (48k/44.1k -> 16k)
            if use_sr != SAMPLE_RATE:
                audio_float = self._resample_16k(audio_float, use_sr)

            # Barge-in: TTS calarken kullanici konusursa durdur
            if speaking:
                prob = self.vad.is_speech(audio_float)
                if prob > self.vad.threshold:
                    logger.info("Barge-in algilandi! TTS durduruluyor.")
                    self.tts.stop()
                    with self._lock:
                        self._audio_buffer.clear()
                        self._processing = False
                        self._cancel_requested = False
                    return

            # Isleme sirasindaysa kaydetme
            if proc:
                return

            # VAD ile konusma tespiti
            prob = self.vad.is_speech(audio_float)

            # FIX #5: Her 20 dongude ses seviyesini logger'a yaz
            debug_counter[0] += 1
            if debug_counter[0] % 20 == 0:
                amp = float(np.mean(np.abs(audio_float)))
                peak = float(np.max(np.abs(audio_float)))
                logger.info(
                    "[DEBUG] Ses: RMS=%.5f | Peak=%.5f | VAD=%.3f | Esik=%.2f",
                    amp, peak, prob, SILENCE_THRESHOLD,
                )

            with self._lock:
                is_speech = prob > SILENCE_THRESHOLD

                if is_speech:
                    # BARGE-IN: If user talks while Ultron is speaking, STOP Ultron immediately
                    if self.tts.is_playing:
                        logger.info("BARGE-IN: User interrupted, stopping TTS.")
                        self.tts.stop()
                        self._cancel_requested = True

                    self._silence_start = None
                    self._audio_buffer.extend(indata.tobytes())
                    if self._speech_start_time is None:
                        self._speech_start_time = time.time()
                    if (time.time() - self._speech_start_time) >= 0.3:
                        self._speaking_detected = True
                else:
                    if self._speaking_detected:
                        if self._silence_start is None:
                            self._silence_start = time.time()
                        elif (time.time() - self._silence_start) >= SILENCE_TIMEOUT:
                            buf = bytes(self._audio_buffer)
                            self._audio_buffer.clear()
                            self._speaking_detected = False
                            self._speech_start_time = None
                            self._silence_start = None
                            if len(buf) >= 4800:
                                self._transcribe(buf)

        try:
            # FIX #3: blocksize=None => otomatik optimal deger
            stream_kwargs = dict(
                samplerate=use_sr,
                channels=num_channels,
                dtype="int16",
                blocksize=None,
                callback=audio_callback,
            )
            if device_id is not None:
                stream_kwargs["device"] = device_id
                logger.info("Mikrofon cihazi ID=%i kullaniliyor", device_id)

            with sd.InputStream(**stream_kwargs):
                dev_name = sd.query_devices(device_id)["name"] if device_id is not None else "varsayilan"
                logger.info("Mikrofon dinleniyor... (cihaz: %s, kanal: %d, oran: %d)", dev_name, num_channels, use_sr)
                while self._mic_enabled:
                    time.sleep(0.1)
        except Exception as e:
            logger.error("Ses yakalama hatasi: %s", e)
            if self.on_error:
                self.on_error(f"Ses yakalama hatasi: {e}")
            self._set_state(self.State.IDLE)

    # ── Transkripsiyon ───────────────────────────────────────────────────

    def _transcribe(self, audio_bytes: bytes):
        """Google STT ile metne cevir, basarisizsa Whisper'a gec."""
        self._set_state(self.State.TRANSCRIBING)

        text = ""

        # 1. Oncelikli: Google Web Speech API
        if self.stt_primary.available:
            text = self.stt_primary.transcribe(audio_bytes)

        # 2. Yedek: OpenAI Whisper
        if not text and self.stt_fallback.available:
            text = self.stt_fallback.transcribe(audio_bytes)

        # Gecerli metin varsa isle
        if text and len(text) > 1:
            if self.on_user_text:
                self.on_user_text(text)
            self._process_response(text)
        else:
            logger.debug("Transkripsiyon bos veya kisa, dinleme surduruluyor.")
            self._set_state(self.State.LISTENING)

    # ── Yanit Isleme ─────────────────────────────────────────────────────

    def _process_response(self, user_text: str):
        """Ollama'ya istek at, tool calling'i yonet, yaniti teslim et."""
        logger.info("Yanit isleniyor: '%s'...", user_text[:80])
        self._set_state(self.State.THINKING)

        # ANTI-LOOP: Aynı mesaj 3 kez geldiyse cache'i atla
        with self._lock:
            self._processing = True
            if getattr(self, '_last_user_text', '') == user_text:
                self._loop_count = getattr(self, '_loop_count', 0) + 1
                if self._loop_count >= 3:
                    logger.warning("LOOP DETECTED! Cache temizleniyor: '%s'", user_text[:80])
                    if self.response_cache:
                        self.response_cache.clear()
                    self._loop_count = 0
            else:
                self._loop_count = 0
            self._last_user_text = user_text

        def worker():
            try:
                # Onbellege kontrolu
                if self.response_cache:
                    cached = self.response_cache.get(user_text)
                    if cached:
                        logger.info("Onbellege'den yanit alindi.")
                        self._deliver_response(cached)
                        return

                # Personalization: Update context with user profile
                user_name = os.environ.get("ULTRON_USER_NAME", "Efendi")
                profile = self.user_memory.get_profile(user_name)
                if profile:
                    interests = ", ".join(profile.get("interests", []))
                    if interests:
                        self.context.set_system_prompt(
                            f"Sen Ultron'sun. Karşındaki kişi {user_name}. İlgi alanları: {interests}. "
                            "Konuşmanı bu kişiye özel, onun ilgi alanlarını gözeterek ve Marvel'daki Ultron tarzında (soğuk, zeki, otoriter ama bazen nüktedan) yap."
                        )

                # Baglam guncelle
                self.context.add_user_message(user_text)
                messages = self.context.get_messages()
                logger.info("Ollama'ya %d mesaj gonderiliyor...", len(messages))

                # LLM Cagrisi via LLMRouter
                logger.info("Yanit uretiliyor (Model: %s)...", MODEL)
                import asyncio
                
                # Check if it's a cloud model or we have healthy providers
                is_cloud = any(m in MODEL.lower() for m in ["gemini", "gpt", "claude", "llama-3"])
                
                try:
                    if is_cloud or self.llm_router.get_healthy_providers():
                        # Run async chat in sync worker
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                        response = loop.run_until_complete(self.llm_router.chat(
                            messages, 
                            temperature=LLM_TEMPERATURE,
                            max_tokens=LLM_NUM_PREDICT
                        ))
                        assistant_text = response.content
                    else:
                        # Fallback to direct Ollama HTTP if no cloud config
                        payload = {
                            "model": MODEL,
                            "messages": messages,
                            "stream": False,
                            "tools": TOOL_DECLARATIONS,
                            "options": {
                                "temperature": LLM_TEMPERATURE,
                                "num_predict": LLM_NUM_PREDICT,
                            }
                        }
                        response = requests.post(
                            f"{OLLAMA_URL}/api/chat",
                            json=payload,
                            timeout=LLM_TIMEOUT,
                        )
                        result = response.json()
                        assistant_text = result.get("message", {}).get("content", "")
                except Exception as e:
                    logger.error("LLM interaction failed: %s", e)
                    assistant_text = f"Hata olustu: {str(e)}"

                if "error" in result:
                    raise RuntimeError(f"Ollama hatasi: {result['error']}")

                message = result.get("message", {})
                tool_calls = message.get("tool_calls", [])
                assistant_text = message.get("content", "")

                logger.info("Ollama yaniti alindi (uzunluk: %d karakter, tool_calls: %d)",
                          len(assistant_text) if assistant_text else 0, len(tool_calls))

                # Tool calling var mi?
                if tool_calls:
                    logger.info("%d arac cagrildi.", len(tool_calls))
                    tool_results = []
                    for tc in tool_calls:
                        func_name = tc["function"]["name"]
                        args_raw = tc["function"]["arguments"]

                        if isinstance(args_raw, str):
                            try:
                                func_args = json.loads(args_raw)
                            except json.JSONDecodeError:
                                func_args = {}
                        else:
                            func_args = args_raw or {}

                        logger.info("Arac cagrildi: %s | Argumanlar: %s", func_name, func_args)
                        result_text = self._execute_tool(func_name, func_args)
                        tool_results.append({
                            "role": "tool",
                            "content": result_text or "Tamamlandi",
                            "tool_call_id": func_name,
                        })

                    messages.append(message)
                    messages.extend(tool_results)
                    logger.info("Araclar sonrasi ikinci Ollama cagrisi yapiliyor...")

                    response2 = requests.post(
                        f"{OLLAMA_URL}/api/chat",
                        json={
                            "model": MODEL,
                            "messages": messages,
                            "stream": False,
                            "options": {
                                "temperature": LLM_TEMPERATURE,
                                "num_predict": LLM_NUM_PREDICT,
                            }
                        },
                        timeout=LLM_TIMEOUT,
                    )
                    final = response2.json()
                    assistant_text = final.get("message", {}).get("content", "")
                    logger.info("Ollama final yanit (uzunluk: %d karakter)", len(assistant_text))

                if not assistant_text or not assistant_text.strip():
                    logger.warning("Ollama bos yanit dondu!")
                    assistant_text = "Uzgunum, su an yanit uretemiyorum."

                self.context.add_assistant_message(assistant_text)

                if self.response_cache:
                    self.response_cache.put(user_text, assistant_text)

                # Background Learning: Update user profile asynchronously
                if hasattr(self, 'self_learning') and self.self_learning:
                    asyncio.run_coroutine_threadsafe(
                        self.self_learning.learn_from_conversation(user_text, assistant_text),
                        asyncio.get_event_loop()
                    )

                self._deliver_response(assistant_text)

            except requests.ConnectionError:
                err_msg = "Ollama baglantisi kurulamadi. Ollama'nin calistigindan emin olun."
                logger.error(err_msg)
                if self.on_error:
                    self.on_error(err_msg)
            except requests.Timeout:
                err_msg = f"Ollama yanit vermedi ({LLM_TIMEOUT}s zaman asimi)."
                logger.error(err_msg)
                if self.on_error:
                    self.on_error(err_msg)
            except Exception as e:
                logger.error("Yanit isleme hatasi: %s", e)
                if self.on_error:
                    self.on_error(str(e))
            finally:
                with self._lock:
                    self._processing = False
                    self._cancel_requested = False

        threading.Thread(target=worker, daemon=True).start()

    # ── Yanit Teslim ─────────────────────────────────────────────────────

    def _deliver_response(self, response: str):
        """Metin ve sesli yaniti kullaniciya ulastir."""
        self._set_state(self.State.SPEAKING)

        if self.on_assistant_text:
            self.on_assistant_text(response)

        if self.auto_respond and self.tts._available and response:
            clean = re.sub(r"[#*`_\[\](){}]", "", response).strip()
            if clean:
                self.tts.speak(clean)

            def _wait_for_tts():
                while True:
                    with self._lock:
                        if self._cancel_requested:
                            self._cancel_requested = False
                            self._set_state(self.State.IDLE)
                            return
                    if not self.tts.is_playing:
                        break
                    time.sleep(0.1)
                self._set_state(self.State.LISTENING)

            threading.Thread(target=_wait_for_tts, daemon=True).start()
        else:
            self._set_state(self.State.IDLE)

    # ── Durum Yonetimi ───────────────────────────────────────────────────

    def _set_state(self, state: str):
        with self._lock:
            self._state = state
        if self.on_state_change:
            self.on_state_change(state)
