"""AirLLM Provider — Run Llama 3.1 70B/405B with minimal VRAM (4-8GB).

AirLLM uses layer-wise loading to run massive models on consumer GPUs.
- Llama 3.1 70B → ~4GB VRAM, ~35GB disk
- Llama 3.1 405B → ~8GB VRAM, ~230GB disk

Features:
- Automatic model download from HuggingFace
- Layer-wise inference (only active layers on GPU)
- Prefetching for faster inference
- 4-bit/8-bit compression support
- Lazy loading (model loaded on first use)
- Automatic cleanup on shutdown

Installation:
    pip install airllm accelerate

Environment Variables:
    AIRLLM_MODEL: Model name (default: meta-llama/Llama-3.1-70B-Instruct)
    AIRLLM_COMPRESSION: Compression type (default: 4bit, options: 4bit, 8bit, None)
    AIRLLM_PREFETCHING: Enable prefetching (default: true)
    AIRLLM_MAX_LENGTH: Max context length (default: 4096)
    HUGGING_FACE_HUB_TOKEN: HuggingFace token for gated models like Llama 3
"""

import os
import asyncio
import logging
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from pathlib import Path

from ultron.providers.base import BaseProvider, Message, ProviderConfig, ProviderResult

logger = logging.getLogger(__name__)


class AirLLMProvider(BaseProvider):
    """AirLLM provider for running massive LLMs on consumer GPUs.
    
    Uses layer-wise loading to run Llama 3.1 70B on just 4GB VRAM.
    """

    def __init__(self):
        model_name = os.getenv("AIRLLM_MODEL", "meta-llama/Llama-3.1-70B-Instruct")
        compression = os.getenv("AIRLLM_COMPRESSION", "4bit")
        prefetching = os.getenv("AIRLLM_PREFETCHING", "true").lower() == "true"
        self._max_length = int(os.getenv("AIRLLM_MAX_LENGTH", "4096"))
        self._hf_token = os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY") or os.getenv("HUGGING_FACE_HUB_TOKEN")
        
        config = ProviderConfig(
            name="airllm",
            base_url="",  # Local model, no URL needed
            default_model=model_name,
            timeout=600,  # 10 min timeout for large models
            priority=0,  # Highest priority (before Ollama)
        )
        super().__init__(config)
        
        self.compression = compression if compression.lower() != "none" else None
        self.prefetching = prefetching
        self.model = None
        self._loading = False

    def _load_model(self):
        """Load AirLLM model (lazy loading)."""
        if self.model is not None:
            return

        if self._loading:
            # Wait for another thread to finish loading
            while self._loading:
                time.sleep(0.1)
            return

        self._loading = True
        
        try:
            from airllm import AutoModel

            logger.info(f"🧠 Loading AirLLM model: {self.config.default_model}")
            logger.info(f"   Compression: {self.compression}")
            logger.info(f"   Prefetching: {self.prefetching}")
            logger.info(f"   This may take several minutes for large models...")

            # Build kwargs
            load_kwargs = {
                "prefetching": self.prefetching,
            }
            
            if self.compression:
                load_kwargs["compression"] = self.compression
            
            if self._hf_token:
                load_kwargs["hf_token"] = self._hf_token

            # Load model with layer-wise loading
            self.model = AutoModel.from_pretrained(
                self.config.default_model,
                **load_kwargs
            )

            logger.info(f"✅ AirLLM model loaded successfully!")
            logger.info(f"   Model: {self.config.default_model}")
            logger.info(f"   Compression: {self.compression}")
            logger.info(f"   VRAM usage: ~{'8GB' if '405' in self.config.default_model else '4GB'}")

        except ImportError as e:
            logger.error(
                f"❌ AirLLM not installed!\n"
                f"   Run: pip install airllm accelerate\n"
                f"   Error: {e}"
            )
            raise
        except Exception as e:
            logger.error(f"❌ Failed to load AirLLM model: {e}")
            logger.error(f"   Check your HuggingFace token (HF_TOKEN env var) and model name")
            raise
        finally:
            self._loading = False

    def _format_chatml(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into Llama 3 ChatML format."""
        prompt = ""
        
        # Check if this is a Llama 3 model
        model_lower = self.config.default_model.lower()
        is_llama3 = "llama-3" in model_lower or "llama3" in model_lower
        
        if is_llama3:
            # Llama 3 ChatML format
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
            prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        else:
            # Generic chat format
            system_msg = next((m for m in messages if m.get("role") == "system"), None)
            if system_msg:
                prompt += f"System: {system_msg.get('content', '')}\n\n"
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    continue
                prompt += f"{role.capitalize()}: {content}\n"
            prompt += "Assistant: "
        
        return prompt

    def _generate_sync(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Synchronous generation (runs in executor)."""
        import torch
        
        self._load_model()

        # Tokenize input
        input_tokens = self.model.tokenizer(
            [prompt],
            return_tensors="pt",
            return_attention_mask=False,
            truncation=True,
            max_length=self._max_length,
            padding=False
        )
        
        logger.info(f"⏳ Generating response (max_tokens={max_tokens}, temp={temperature})...")
        logger.info(f"   Input tokens: {input_tokens['input_ids'].shape}")
        
        # Generate (AirLLM requires .cuda())
        generation_output = self.model.generate(
            input_tokens['input_ids'].cuda(),
            max_new_tokens=max_tokens,
            use_cache=True,
            return_dict_in_generate=True
        )

        # Decode output - skip the prompt portion
        output = self.model.tokenizer.decode(generation_output.sequences[0])
        
        # Extract only the generated part (after prompt)
        result = output[len(prompt):].strip()
        
        return result

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ProviderResult:
        """Chat completion with AirLLM."""
        start = time.time()
        model_name = model or self.config.default_model
        
        # Format messages
        prompt = self._format_chatml([m.model_dump() for m in messages])
        
        # Run in executor to not block event loop
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: self._generate_sync(prompt, max_tokens, temperature)
        )

        latency_ms = int((time.time() - start) * 1000)
        
        # Count tokens (approximate)
        if self.model and self.model.tokenizer:
            prompt_tokens = len(self.model.tokenizer.encode(prompt))
            completion_tokens = len(self.model.tokenizer.encode(result))
            total_tokens = prompt_tokens + completion_tokens
        else:
            total_tokens = 0

        logger.info(
            f"✅ AirLLM chat completed\n"
            f"   Model: {model_name}\n"
            f"   Tokens: {total_tokens} (latency={latency_ms}ms)\n"
            f"   Speed: ~{total_tokens / (latency_ms/1000) if latency_ms > 0 else 0:.1f} tok/s"
        )

        return ProviderResult(
            content=result,
            provider=self.config.name,
            model=model_name,
            tokens_used=total_tokens,
            latency_ms=latency_ms,
        )

    async def stream_chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Streaming chat (emulated since AirLLM doesn't support native streaming)."""
        model_name = model or self.config.default_model
        
        # Format messages
        prompt = self._format_chatml([m.model_dump() for m in messages])
        
        # Load model
        self._load_model()
        
        # Generate full response
        loop = asyncio.get_running_loop()
        full_result = await loop.run_in_executor(
            None, 
            lambda: self._generate_sync(prompt, self._max_length, 0.7)
        )
        
        # Stream word by word
        words = full_result.split()
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.02)  # Small delay for streaming effect

    async def is_available(self) -> bool:
        """Check if AirLLM is available and CUDA is ready."""
        try:
            import torch
            import airllm
            
            # Check if CUDA is available (AirLLM requires GPU)
            if not torch.cuda.is_available():
                logger.warning("AirLLM requires CUDA but it's not available")
                return False
            
            # Check GPU memory
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
            if gpu_mem < 4:
                logger.warning(f"AirLLM requires at least 4GB VRAM, have {gpu_mem:.1f}GB")
                return False
            
            return True
        except ImportError:
            return False

    def is_configured(self) -> bool:
        """Always configured if AirLLM is installed."""
        try:
            import airllm
            return True
        except ImportError:
            return False

    async def list_models(self) -> list[str]:
        """List common Llama 3.1 models supported by AirLLM."""
        return [
            "meta-llama/Llama-3.1-8B-Instruct",
            "meta-llama/Llama-3.1-70B-Instruct",
            "meta-llama/Llama-3.1-405B-Instruct",
            "meta-llama/Llama-3.1-8B",
            "meta-llama/Llama-3.1-70B",
            "meta-llama/Llama-3.1-405B",
        ]

    def unload_model(self):
        """Unload model from memory (frees VRAM)."""
        if self.model is not None:
            import torch
            import gc
            
            del self.model
            self.model = None
            
            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            gc.collect()
            logger.info("✅ AirLLM model unloaded - VRAM freed")


def create_provider(config: dict) -> AirLLMProvider:
    """Provider factory for AirLLM."""
    return AirLLMProvider()
