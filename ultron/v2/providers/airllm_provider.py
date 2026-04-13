"""AirLLM Provider — 405B modeli 4-bit compression ile düşük VRAM'da çalıştır.

Özellikler:
- Llama 3.1 405B → ~230GB disk (4-bit), ~8GB VRAM
- Layer-wise loading (sadece aktif layer GPU'da)
- Prefetching (sonraki layer önceden yüklenir)
- Drop-in replacement for HuggingFace API

Kurulum:
    pip install airllm

Kullanım:
    from ultron.v2.providers.airllm_provider import AirLLMProvider
    
    provider = AirLLMProvider(
        model_name="meta-llama/Llama-3.1-405B",
        compression="4bit"
    )
    
    response = await provider.chat([
        {"role": "user", "content": "Merhaba!"}
    ])
"""

import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AirLLMProvider:
    """AirLLM Provider - 405B modeli düşük VRAM'da çalıştır
    
    4-bit compression ile:
    - 405B model → ~230GB disk (810GB yerine!)
    - VRAM → ~8GB
    - Speed → ~0.5-1 tok/s (uyku modu için yeterli)
    """
    
    def __init__(
        self,
        model_name: str = "meta-llama/Llama-3.1-405B",
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
        """Model'i yükle (lazy loading)"""
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
            
            # Model yükle (4-bit compression)
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
    
    async def chat(self, messages: list[dict]) -> dict:
        """
        Chat completion
        
        Args:
            messages: [{"role": "user", "content": "..."}]
        
        Returns:
            {"content": "...", "tokens_used": 123, "latency_ms": 5000}
        """
        import time
        start_time = time.time()
        
        # Model yükle (lazy)
        self._load_model()
        
        # Mesajları text'e çevir
        input_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize
        inputs = self.tokenizer(input_text, return_tensors="pt")
        
        # Generate
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True
        )
        
        # Decode
        response_text = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )
        
        latency_ms = (time.time() - start_time) * 1000
        tokens_used = outputs.shape[1]
        
        logger.info(
            f"✅ AirLLM chat completed\n"
            f"   Tokens: {tokens_used}\n"
            f"   Latency: {latency_ms:.0f}ms ({latency_ms/1000:.1f}s)\n"
            f"   Speed: ~{tokens_used / (latency_ms/1000):.1f} tok/s"
        )
        
        return {
            "content": response_text,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "model": self.model_name,
            "compression": self.compression
        }
    
    async def complete(self, prompt: str, max_tokens: int = 512) -> dict:
        """
        Text completion (chat değil)
        
        Args:
            prompt: Tam prompt text
            max_tokens: Maksimum yeni token
        
        Returns:
            {"content": "...", "tokens_used": 123}
        """
        import time
        start_time = time.time()
        
        # Model yükle
        self._load_model()
        
        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt")
        
        # Generate
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9
        )
        
        # Decode
        response_text = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )
        
        latency_ms = (time.time() - start_time) * 1000
        tokens_used = outputs.shape[1]
        
        return {
            "content": response_text,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms
        }
    
    def get_model_info(self) -> dict:
        """Model bilgisi"""
        return {
            "name": self.model_name,
            "compression": self.compression,
            "disk_usage_gb": 230 if "405" in self.model_name else 35,
            "vram_usage_gb": 8 if "405" in self.model_name else 4,
            "estimated_speed_toks_per_sec": 0.5 if "405" in self.model_name else 10,
            "prefetching": self.prefetching
        }
    
    def unload_model(self):
        """Model'i bellekten kaldır (disk alanı geri kazan)"""
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
            "model_name": "meta-llama/Llama-3.1-405B",
            "compression": "4bit",
            "prefetching": true
        }
    
    Returns:
        AirLLMProvider instance
    """
    return AirLLMProvider(
        model_name=config.get("model_name", "meta-llama/Llama-3.1-405B"),
        compression=config.get("compression", "4bit"),
        prefetching=config.get("prefetching", True)
    )
