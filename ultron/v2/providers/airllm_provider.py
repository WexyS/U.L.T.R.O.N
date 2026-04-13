"""AirLLM Provider — Llama 3.1 405B (4-bit) ile devasa modeli düşük VRAM'da çalıştır.

Özellikler:
- Llama 3.1 405B → ~230GB disk (4-bit), ~8GB VRAM
- Layer-wise loading (sadece aktif layer GPU'da)
- Prefetching (sonraki layer önceden yüklenir)
- Async execution (UI/event loop kilitlenmez)
- ChatML format desteği (Llama 3 format)
- Lazy loading (ilk kullanımda yüklenir)

Kurulum:
    pip install airllm

Kullanım:
    from ultron.v2.providers.airllm_provider import AirLLMProvider

    provider = AirLLMProvider(
        model_name="meta-llama/Llama-3.1-405B-Instruct",
        compression="4bit"
    )

    response = await provider.chat([
        {"role": "user", "content": "Merhaba!"}
    ])
"""

import os
import asyncio
import logging
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AirLLMProvider:
    """AirLLM Provider - 405B modeli düşük VRAM'da çalıştır

    4-bit compression ile:
    - 405B model → ~230GB disk (810GB yerine!)
    - VRAM → ~8GB
    - Speed → ~0.5-1 tok/s (uyku modu için yeterli)

    Katkıda Bulunanlar:
    - Qwen: Temel implementasyon
    - Gemini: ChatML format + async executor optimizasyonu
    - Claude: Provider factory + error handling
    """

    def __init__(
        self,
        model_name: str = "meta-llama/Llama-3.1-405B-Instruct",
        compression: str = "4bit",
        prefetching: bool = True
    ):
        self.model_name = model_name
        self.compression = compression
        self.prefetching = prefetching
        self.model = None
        self.tokenizer = None

        # Model'i lazy load et (ilk kullanımda yükle)
        logger.info(
            f"🧠 AirLLM Provider initialized\n"
            f"   Model: {model_name}\n"
            f"   Compression: {compression}\n"
            f"   Prefetching: {prefetching}\n"
            f"   Disk: ~230GB (4-bit)\n"
            f"   VRAM: ~8GB"
        )

    def _load_model(self):
        """Model'i yükle (lazy loading - sadece ilk seferde)"""
        if self.model is not None:
            return

        try:
            from airllm import AutoModel
            from transformers import AutoTokenizer

            logger.info(f"📥 Loading AirLLM model: {self.model_name}...")
            logger.info(f"   Compression: {self.compression}")
            logger.info(f"   This will take a few minutes for 405B model...")

            # Tokenizer yükle
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )

            # Model yükle (4-bit compression + prefetching)
            self.model = AutoModel.from_pretrained(
                self.model_name,
                compression=self.compression,
                prefetching=self.prefetching
            )

            logger.info(f"✅ AirLLM model loaded successfully!")
            logger.info(f"   VRAM usage: ~8GB")
            logger.info(f"   Disk usage: ~230GB")

        except ImportError:
            logger.error(
                "❌ AirLLM not installed!\n"
                "   Run: pip install airllm"
            )
            raise
        except Exception as e:
            logger.error(f"❌ Failed to load AirLLM model: {e}")
            raise

    def _generate_sync(self, prompt: str, max_tokens: int = 1024) -> str:
        """Senkron AirLLM çıkarımı (Layer-wise inference)"""
        self._load_model()

        input_text = [prompt]
        inputs = self.tokenizer(input_text, max_length=4096, return_tensors="pt")

        logger.info("⏳ Derin analiz yapılıyor (Llama 405B katmanları sırayla işleniyor)...")
        outputs = self.model.generate(
            inputs['input_ids'],
            max_new_tokens=max_tokens,
            use_cache=True,
            return_dict_in_generate=True
        )

        result = self.tokenizer.decode(outputs.sequences[0], skip_special_tokens=True)

        # Prompt'u sonuçtan çıkar
        if result.startswith(prompt):
            result = result[len(prompt):].strip()

        return result

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1024, **kwargs) -> Any:
        """
        Chat completion (Llama 3 ChatML format + async executor)

        Args:
            messages: [{"role": "user", "content": "..."}]
            max_tokens: Maksimum yeni token (default: 1024)

        Returns:
            ProviderResult benzeri obje
        """
        start_time = time.time()

        # Llama 3 ChatML format
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>\n"
        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"

        # Async executor (UI/event loop kilitlenmesin)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._generate_sync, prompt, max_tokens)

        latency_ms = (time.time() - start_time) * 1000
        tokens_used = len(self.tokenizer.encode(result)) if self.tokenizer else 0

        logger.info(
            f"✅ AirLLM chat completed\n"
            f"   Tokens: {tokens_used}\n"
            f"   Latency: {latency_ms:.0f}ms ({latency_ms/1000:.1f}s)\n"
            f"   Speed: ~{tokens_used / (latency_ms/1000) if latency_ms > 0 else 0:.1f} tok/s"
        )

        # Ultron provider interface uyumlu
        class MockMessage:
            def __init__(self, content): self.content = content
        class MockResponse:
            def __init__(self, content):
                self.content = content
                self.message = MockMessage(content)
                self.tokens_used = tokens_used
                self.latency_ms = latency_ms

        return MockResponse(result)

    async def complete(self, prompt: str, max_tokens: int = 1024) -> dict:
        """
        Text completion (chat değil, düz text)

        Args:
            prompt: Tam prompt text
            max_tokens: Maksimum yeni token

        Returns:
            {"content": "...", "tokens_used": 123, "latency_ms": 5000}
        """
        start_time = time.time()

        # Async executor
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._generate_sync, prompt, max_tokens)

        latency_ms = (time.time() - start_time) * 1000
        tokens_used = len(self.tokenizer.encode(result)) if self.tokenizer else 0

        return {
            "content": result,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "model": self.model_name,
            "compression": self.compression
        }

    def get_model_info(self) -> dict:
        """Model bilgisi"""
        return {
            "name": self.model_name,
            "compression": self.compression,
            "disk_usage_gb": 230 if "405" in self.model_name else 35,
            "vram_usage_gb": 8 if "405" in self.model_name else 4,
            "estimated_speed_toks_per_sec": 0.5 if "405" in self.model_name else 10,
            "prefetching": self.prefetching,
            "chatml_format": True,
            "async_executor": True
        }

    def unload_model(self):
        """Model'i bellekten kaldır (disk/VRAM alanı geri kazan)"""
        if self.model is not None:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None

            import gc
            gc.collect()

            logger.info("✅ AirLLM model unloaded - memory freed")

    async def is_available(self) -> bool:
        """Provider kullanılabilir mi?"""
        try:
            import airllm
            return True
        except ImportError:
            return False


# ─── Ultron Provider Registry için ───────────────────────────────────────

def create_provider(config: dict) -> AirLLMProvider:
    """Provider factory function

    Args:
        config: {
            "model_name": "meta-llama/Llama-3.1-405B-Instruct",
            "compression": "4bit",
            "prefetching": true
        }

    Returns:
        AirLLMProvider instance
    """
    return AirLLMProvider(
        model_name=config.get("model_name", "meta-llama/Llama-3.1-405B-Instruct"),
        compression=config.get("compression", "4bit"),
        prefetching=config.get("prefetching", True)
    )
