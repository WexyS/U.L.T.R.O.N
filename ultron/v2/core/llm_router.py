"""Multi-provider LLM router with automatic fallback and cost/latency awareness."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from ultron.v2.mcp.bridge import MCPBridge

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    finish_reason: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None


from ultron.v2.providers.base import ProviderStats


class LLMProvider(ABC):
    """Abstract LLM provider."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        stream: bool = False,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class OllamaProvider(LLMProvider):
    """Ollama local inference provider. Zero cost, unlimited usage."""

    def __init__(
        self,
        model: str = "qwen2.5:14b",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._base_url = base_url
        self._available: Optional[bool] = None
        self.stats = ProviderStats()

    @property
    def name(self) -> str:
        return "ollama"

    def get_model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import httpx
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=3)
            self._available = resp.status_code == 200
            return self._available
        except Exception:
            self._available = False
            return False

    async def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        stream: bool = False,
    ) -> LLMResponse:
        import ollama

        start = time.monotonic()
        self.stats.total_calls += 1

        try:
            # Use async ollama client for non-blocking calls
            client = ollama.AsyncClient(host=self._base_url)
            response = await asyncio.wait_for(
                client.chat(
                    model=self._model,
                    messages=messages,
                    options={
                        "temperature": temperature or 0.3,
                        "num_predict": max_tokens or 1024,
                        "num_ctx": 1024,
                        "num_gpu": 999,
                        "mirostat": 2,
                        "mirostat_tau": 5.0,
                    },
                ),
                timeout=300,  # 5 min for 14B models
            )

            latency = (time.monotonic() - start) * 1000
            content = response.get("message", {}).get("content", "")

            self.stats.successful_calls += 1
            self.stats.total_latency_ms += latency
            self.stats.last_active = datetime.now()
            self.stats.consecutive_failures = 0

            return LLMResponse(
                content=content,
                provider=self.name,
                model=self._model,
                latency_ms=latency,
                finish_reason="stop",
            )
        except Exception as e:
            self.stats.failed_calls += 1
            self.stats.last_error = str(e)
            self.stats.consecutive_failures += 1
            raise

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        import ollama

        # Use async client for proper async streaming
        client = ollama.AsyncClient(host=self._base_url)
        response = await client.chat(
            model=self._model,
            messages=messages,
            stream=True,
            options={
                "temperature": temperature or 0.7,
                "num_predict": max_tokens or 4096,
            },
        )

        async for chunk in response:
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk["message"]["content"]


class VLLMProvider(LLMProvider):
    """vLLM local inference provider. Optimized for RTX 4080 (24GB VRAM)."""

    def __init__(
        self,
        model: str = "Qwen/Qwen2.5-32B-Instruct",
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "vllm",
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._available: Optional[bool] = None
        self.stats = ProviderStats()

    @property
    def name(self) -> str:
        return "vllm"

    def get_model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import httpx
            resp = httpx.get(f"{self._base_url}/models", timeout=5, headers={"Authorization": f"Bearer {self._api_key}"})
            self._available = resp.status_code == 200
            return self._available
        except Exception:
            self._available = False
            return False

    async def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        stream: bool = False,
    ) -> LLMResponse:
        from openai import AsyncOpenAI

        start = time.monotonic()
        self.stats.total_calls += 1

        try:
            client = AsyncOpenAI(base_url=self._base_url, api_key=self._api_key)

            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature or 0.7,
                "max_tokens": max_tokens or 4096,
            }

            if tools:
                kwargs["tools"] = tools

            response = await client.chat.completions.create(**kwargs)

            latency = (time.monotonic() - start) * 1000
            content = response.choices[0].message.content or ""

            self.stats.successful_calls += 1
            self.stats.total_latency_ms += latency
            self.stats.last_active = datetime.now()
            self.stats.consecutive_failures = 0

            return LLMResponse(
                content=content,
                provider=self.name,
                model=self._model,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                latency_ms=latency,
                finish_reason=response.choices[0].finish_reason,
            )
        except Exception as e:
            self.stats.failed_calls += 1
            self.stats.last_error = str(e)
            self.stats.consecutive_failures += 1
            raise

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=self._base_url, api_key=self._api_key)

        stream = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature or 0.7,
            max_tokens=max_tokens or 4096,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class OpenAIProvider(LLMProvider):
    """OpenAI cloud provider. Fallback for complex reasoning."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._available: Optional[bool] = None
        self.stats = ProviderStats()

    @property
    def name(self) -> str:
        return "openai"

    def get_model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        stream: bool = False,
    ) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")

        from openai import AsyncOpenAI

        start = time.monotonic()
        self.stats.total_calls += 1

        try:
            client = AsyncOpenAI(api_key=self._api_key)
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature or 0.7,
                "max_tokens": max_tokens or 4096,
            }
            if tools:
                kwargs["tools"] = tools

            response = await client.chat.completions.create(**kwargs)
            latency = (time.monotonic() - start) * 1000
            content = response.choices[0].message.content or ""

            self.stats.successful_calls += 1
            self.stats.total_latency_ms += latency
            self.stats.total_tokens += response.usage.total_tokens if response.usage else 0
            self.stats.last_active = datetime.now()
            self.stats.consecutive_failures = 0

            # Approximate cost (GPT-4o: $5/M input, $15/M output)
            usage = response.usage or {}
            input_cost = getattr(usage, 'prompt_tokens', 0) * 5 / 1_000_000
            output_cost = getattr(usage, 'completion_tokens', 0) * 15 / 1_000_000
            self.stats.total_cost_usd += input_cost + output_cost

            msg = response.choices[0].message
            tcalls = getattr(msg, "tool_calls", None)
            serialized: Optional[list[dict[str, Any]]] = None
            if tcalls:
                serialized = []
                for c in tcalls:
                    fn = getattr(c, "function", None)
                    serialized.append(
                        {
                            "id": getattr(c, "id", ""),
                            "type": getattr(c, "type", "function"),
                            "function": {
                                "name": getattr(fn, "name", "") if fn else "",
                                "arguments": getattr(fn, "arguments", "") if fn else "",
                            },
                        }
                    )

            return LLMResponse(
                content=content,
                provider=self.name,
                model=self._model,
                tokens_used=getattr(usage, 'total_tokens', 0),
                cost_usd=input_cost + output_cost,
                latency_ms=latency,
                finish_reason=response.choices[0].finish_reason,
                tool_calls=serialized,
            )
        except Exception as e:
            self.stats.failed_calls += 1
            self.stats.last_error = str(e)
            self.stats.consecutive_failures += 1
            raise

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key)
        stream = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature or 0.7,
            max_tokens=max_tokens or 4096,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class LLMRouter:
    """Routes LLM requests across providers with automatic fallback.

    Priority: vLLM (fastest local) → Ollama (reliable local) → OpenAI (cloud fallback)
    """

    def __init__(
        self,
        ollama_model: str = "qwen2.5-coder:14b",
        vllm_model: Optional[str] = None,
        openai_model: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        ollama_base_url: str = "http://localhost:11434",
        vllm_base_url: str = "http://localhost:8000/v1",
    ) -> None:
        self.providers: dict[str, LLMProvider] = {}
        self.priority_order: list[str] = []

        # Always add Ollama (default local)
        self.providers["ollama"] = OllamaProvider(
            model=ollama_model,
            base_url=ollama_base_url,
        )
        self.priority_order.append("ollama")

        # Add vLLM if model specified
        if vllm_model:
            self.providers["vllm"] = VLLMProvider(
                model=vllm_model,
                base_url=vllm_base_url,
            )
            self.priority_order.insert(0, "vllm")  # vLLM is fastest

        # Add OpenAI as last resort
        if openai_api_key:
            self.providers["openai"] = OpenAIProvider(
                model=openai_model or "gpt-4o",
                api_key=openai_api_key,
            )
            self.priority_order.append("openai")

        self._active_provider: Optional[str] = None

    def enable_openrouter(self, api_key: str, model: str = "google/gemini-2.0-flash-exp:free"):
        """Add OpenRouter as a smart routing provider.

        Default model changed to Gemini 2.0 Flash (free) — much better Turkish support.
        """
        if api_key and api_key.startswith("sk-or-"):
            # Add FREE model router first — no credits needed!
            self.providers["openrouter_free"] = OpenRouterProvider(
                model=model,
                api_key=api_key,
            )
            if "openrouter_free" not in self.priority_order:
                idx = 0
                if "vllm" in self.priority_order:
                    idx = self.priority_order.index("vllm") + 1
                self.priority_order.insert(idx, "openrouter_free")
                logger.info("OpenRouter FREE models enabled: %s", model)

            # Also add the paid model as fallback
            self.providers["openrouter"] = OpenRouterProvider(
                model="anthropic/claude-sonnet-4",
                api_key=api_key,
            )
            if "openrouter" not in self.priority_order:
                self.priority_order.append("openrouter")

    # ═══════════════════════════════════════════════════════════════════════
    # Multi-Provider Enable Methods
    # ═══════════════════════════════════════════════════════════════════════

    def enable_groq(self, api_key: str, model: str = "fast"):
        """Add Groq — ultra-fast free tier (300-500 tok/s)."""
        if api_key and api_key.startswith("gsk_"):
            from ultron.v2.providers.all_providers import GroqProvider
            # Map shorthand model names to actual Groq model names
            model_map = {
                "fast": "llama-3.3-70b-versatile",
                "llama": "llama-3.3-70b-versatile",
                "mixtral": "mixtral-8x7b-32768",
                "gemma": "gemma2-9b-it",
            }
            actual_model = model_map.get(model, model)
            self.providers["groq"] = GroqProvider(api_key=api_key, model=actual_model)
            if "groq" not in self.priority_order:
                self.priority_order.insert(0, "groq")
                logger.info("Groq enabled (%s) - FREE, ultra-fast", actual_model)

    def enable_gemini(self, api_key: str, model: str = "gemini-2.0-flash"):
        """Add Google Gemini — free tier, 1M+ context."""
        if api_key and api_key.startswith("AIza"):
            from ultron.v2.providers.all_providers import GeminiProvider
            self.providers["gemini"] = GeminiProvider(api_key=api_key, model=model)
            if "gemini" not in self.priority_order:
                # Prioritize Gemini near the top as it is high quality and free
                self.priority_order.insert(0, "gemini")
                logger.info("Google Gemini enabled (%s) - FREE, 1M context", model)

    def enable_cloudflare(self, api_key: str, account_id: str, model: str = "@cf/meta/llama-3.1-8b-instruct"):
        """Add Cloudflare Workers AI — free, 10K/day."""
        if api_key and account_id:
            from ultron.v2.providers.all_providers import CloudflareProvider
            # Set account_id in env so CloudflareProvider can use it
            import os
            os.environ.setdefault("CLOUDFLARE_ACCOUNT_ID", account_id)
            self.providers["cloudflare"] = CloudflareProvider(
                api_key=api_key, model=model)
            if "cloudflare" not in self.priority_order:
                idx = 1
                self.priority_order.insert(idx, "cloudflare")
                logger.info("Cloudflare Workers AI enabled (%s) - FREE, 10K/day", model)

    def enable_together(self, api_key: str, model: str = "Qwen/Qwen2.5-72B-Instruct-Turbo"):
        """Add Together AI — $25 free credits."""
        if api_key:
            from ultron.v2.providers.all_providers import TogetherProvider
            self.providers["together"] = TogetherProvider(api_key=api_key, model=model)
            if "together" not in self.priority_order:
                idx = len(self.priority_order) - 1
                self.priority_order.insert(idx, "together")
                logger.info("Together AI enabled (%s) - $25 free credits", model)

    def enable_huggingface(self, api_key: str, model: str = "Qwen/Qwen2.5-72B-Instruct"):
        """Add Hugging Face Inference API — free tier."""
        if api_key:
            from ultron.v2.providers.all_providers import HFProvider
            self.providers["huggingface"] = HFProvider(api_key=api_key, model=model)
            if "huggingface" not in self.priority_order:
                idx = len(self.priority_order) - 1
                self.priority_order.insert(idx, "huggingface")
                logger.info("Hugging Face enabled (%s) - FREE inference API", model)

    def enable_all_providers(self, env: dict):
        """Enable all available providers from environment variables."""
        # OpenRouter
        if env.get("OPENROUTER_API_KEY"):
            self.enable_openrouter(env["OPENROUTER_API_KEY"])
        # Groq
        if env.get("GROQ_API_KEY"):
            self.enable_groq(env["GROQ_API_KEY"])
        # Google Gemini
        if env.get("GEMINI_API_KEY"):
            self.enable_gemini(env["GEMINI_API_KEY"])
        # Cloudflare
        if env.get("CLOUDFLARE_API_KEY") and env.get("CLOUDFLARE_ACCOUNT_ID"):
            self.enable_cloudflare(env["CLOUDFLARE_API_KEY"], env["CLOUDFLARE_ACCOUNT_ID"])
        # Together AI
        if env.get("TOGETHER_API_KEY"):
            self.enable_together(env["TOGETHER_API_KEY"])
        # Hugging Face
        if env.get("HF_API_KEY"):
            self.enable_huggingface(env["HF_API_KEY"])
        # DeepSeek
        if env.get("DEEPSEEK_API_KEY"):
            from ultron.v2.providers.extra_providers import DeepSeekProvider
            self.providers["deepseek"] = DeepSeekProvider(api_key=env["DEEPSEEK_API_KEY"])
            if "deepseek" not in self.priority_order:
                # Put DeepSeek after the free ones
                self.priority_order.append("deepseek")
                logger.info("DeepSeek enabled - cheap + powerful code")
        # Anthropic
        if env.get("ANTHROPIC_API_KEY"):
            from ultron.v2.providers.extra_providers import AnthropicProvider
            self.providers["anthropic"] = AnthropicProvider(api_key=env["ANTHROPIC_API_KEY"])
            if "anthropic" not in self.priority_order:
                # Put paid models at the very end as ultimate fallbacks
                self.priority_order.append("anthropic")
                logger.info("Anthropic Claude enabled - best understanding (Paid Fallback)")
        # Mistral
        if env.get("MISTRAL_API_KEY"):
            from ultron.v2.providers.extra_providers import MistralProvider
            self.providers["mistral"] = MistralProvider(api_key=env["MISTRAL_API_KEY"])
            if "mistral" not in self.priority_order:
                idx = len(self.priority_order) - 1
                self.priority_order.insert(idx, "mistral")
                logger.info("Mistral enabled - GDPR compliant")
        # Cohere
        if env.get("COHERE_API_KEY"):
            from ultron.v2.providers.extra_providers import CohereProvider
            self.providers["cohere"] = CohereProvider(api_key=env["COHERE_API_KEY"])
            if "cohere" not in self.priority_order:
                idx = len(self.priority_order) - 1
                self.priority_order.insert(idx, "cohere")
                logger.info("Cohere enabled - RAG reranking")
        # Fireworks
        if env.get("FIREWORKS_API_KEY"):
            from ultron.v2.providers.extra_providers import FireworksProvider
            self.providers["fireworks"] = FireworksProvider(api_key=env["FIREWORKS_API_KEY"])
            if "fireworks" not in self.priority_order:
                idx = len(self.priority_order) - 1
                self.priority_order.insert(idx, "fireworks")
                logger.info("Fireworks enabled - ultra-fast inference")
        # OpenAI
        if env.get("OPENAI_API_KEY"):
            self.providers["openai"] = OpenAIProvider(
                model=env.get("OPENAI_MODEL", "gpt-4o"),
                api_key=env["OPENAI_API_KEY"],
            )
            if "openai" not in self.priority_order:
                self.priority_order.append("openai")

    def get_healthy_providers(self) -> list[str]:
        """Get list of available providers in priority order, excluding those currently failing (Circuit Breaker)."""
        healthy = []
        for name in self.priority_order:
            provider = self.providers.get(name)
            if not provider:
                continue
            
            # Check circuit breaker limit (max 3 consecutive failures)
            if hasattr(provider, 'stats') and hasattr(provider.stats, 'consecutive_failures'):
                if getattr(provider.stats, 'consecutive_failures') >= 3:
                    # After 10 minutes (increased from 5), let it try again
                    last_active = getattr(provider.stats, 'last_active')
                    if last_active and (datetime.now() - last_active).total_seconds() < 600:
                        logger.warning(f"Provider {name} is rate-limited or circuit-broken. Skipping for cooldown.")
                        continue
                    else:
                        # Reset to allow a retry
                        setattr(provider.stats, 'consecutive_failures', 0)

            # Handle both BaseProvider (is_configured) and LLMProvider (is_available)
            if hasattr(provider, 'is_configured'):
                available = provider.is_configured()
            else:
                available = provider.is_available()
            if available:
                healthy.append(name)
        return healthy

    @property
    def active_provider(self) -> Optional[str]:
        return self._active_provider

    def _select_provider(self) -> Optional[str]:
        """Select the best available provider."""
        healthy = self.get_healthy_providers()
        if not healthy:
            return None
        self._active_provider = healthy[0]
        return self._active_provider

    async def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
    ) -> LLMResponse:
        """Chat with automatic fallback across providers."""
        healthy = self.get_healthy_providers()
        if not healthy:
            raise RuntimeError("No LLM providers available. Is Ollama running?")

        last_error = None
        for provider_name in list(healthy):
            provider = self.providers[provider_name]
            try:
                # BaseProvider subclasses (from all_providers/extra_providers)
                # have a different signature: chat(messages, model, max_tokens, temperature, stream)
                # and expect Message objects, not dicts. They do NOT accept `tools`.
                # LLMProvider subclasses (Ollama/vLLM/OpenAI in this file)
                # accept: chat(messages, temperature, max_tokens, tools, stream)
                import inspect
                sig = inspect.signature(provider.chat)
                params = set(sig.parameters.keys())

                start_time = time.monotonic()
                if 'tools' in params:
                    # LLMProvider interface (Ollama, vLLM, OpenAI from this file)
                    response = await provider.chat(
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        tools=tools,
                    )
                else:
                    # BaseProvider interface (Groq, Cloudflare, DeepSeek, etc.)
                    from ultron.v2.providers.base import Message
                    converted = []
                    for m in messages:
                        if isinstance(m, dict):
                            converted.append(Message(role=m.get('role', 'user'), content=m.get('content', '')))
                        else:
                            converted.append(m)
                    
                    result = await provider.chat(
                        converted,
                        max_tokens=max_tokens or 2048,
                        temperature=temperature or 0.7,
                    )
                    
                    latency = (time.monotonic() - start_time) * 1000
                    # Convert ProviderResult -> LLMResponse
                    response = LLMResponse(
                        content=result.content,
                        provider=result.provider,
                        model=result.model,
                        tokens_used=result.tokens_used,
                        cost_usd=0.0,
                        latency_ms=latency,
                    )
                    
                    # Update stats if provider has them (Circuit Breaker support)
                    if hasattr(provider, 'stats'):
                        stats = getattr(provider, 'stats')
                        stats.total_calls += 1
                        stats.successful_calls += 1
                        stats.total_latency_ms += latency
                        stats.last_active = datetime.now()
                        stats.consecutive_failures = 0

                logger.info(
                    "LLM response from %s (%s): %.0fms, %d tokens",
                    provider_name,
                    provider.get_model_name() if hasattr(provider, 'get_model_name') else provider_name,
                    response.latency_ms,
                    response.tokens_used,
                )
                return response
            except Exception as e:
                last_error = e
                logger.warning("Provider %s failed: %s", provider_name, e)
                
                # Check for rate limit (429) to trigger immediate cooldown
                error_str = str(e).lower()
                if "429" in error_str or "too many requests" in error_str or "rate limit" in error_str:
                    if hasattr(provider, 'stats'):
                        stats = getattr(provider, 'stats')
                        # Force a circuit break by setting consecutive failures
                        stats.consecutive_failures = 3
                        stats.last_active = datetime.now()
                        logger.info(f"Provider {provider_name} is being cooled down due to 429 error.")
                
                continue

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    async def vision_chat(
        self,
        prompt: str,
        image_base64: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Analyze an image using a multimodal model (GPT-4o, Claude 3.5, or Gemini)."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ],
            }
        ]
        
        # Prioritize vision-capable providers
        vision_providers = ["openai", "anthropic", "gemini", "openrouter_free", "cloudflare"]
        
        last_error: Optional[Exception] = None
        for provider_name in vision_providers:
            if provider_name not in self.providers:
                continue
            provider = self.providers[provider_name]
            if not provider.is_available():
                continue
                
            try:
                # Force vision models if possible
                model = None
                if provider_name == "openai": model = "gpt-4o"
                elif provider_name == "anthropic": model = "claude-3-5-sonnet-20241022"
                elif provider_name == "gemini": model = "gemini-1.5-flash"
                
                from ultron.v2.providers.base import Message
                converted_messages = []
                for m in messages:
                    converted_messages.append(Message(role=m["role"], content=m["content"]))

                response = await provider.chat(
                    converted_messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                logger.info("Vision analysis via %s successful", provider_name)
                return response
            except Exception as e:
                last_error = e
                logger.warning("Vision provider %s failed: %s", provider_name, e)
                
                # Check for rate limit (429) to trigger immediate cooldown
                error_str = str(e).lower()
                if "429" in error_str or "too many requests" in error_str or "rate limit" in error_str:
                    if hasattr(provider, 'stats'):
                        stats = getattr(provider, 'stats')
                        stats.consecutive_failures = 3
                        stats.last_active = datetime.now()
                        logger.info(f"Vision provider {provider_name} cooled down due to 429 error.")
                
                continue
                
        raise RuntimeError(f"All vision providers failed. Last error: {last_error}")

    def _providers_supporting_tools(self) -> list[str]:
        """tools= destekleyen sağlıklı sağlayıcılar (OpenAI uyumlu MCP döngüsü için)."""
        import inspect

        ordered: list[str] = []
        for name in self.get_healthy_providers():
            provider = self.providers.get(name)
            if not provider:
                continue
            try:
                if "tools" in inspect.signature(provider.chat).parameters:
                    ordered.append(name)
            except (TypeError, ValueError):
                continue
        return ordered

    async def _chat_with_tools_single(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> LLMResponse:
        names = self._providers_supporting_tools()
        if not names:
            raise RuntimeError(
                "MCP araç döngüsü için `tools` destekleyen sağlayıcı yok. "
                "OPENAI_API_KEY veya OPENROUTER_API_KEY ekleyin."
            )
        last_error: Optional[Exception] = None
        for provider_name in names:
            provider = self.providers[provider_name]
            try:
                return await provider.chat(
                    messages,
                    temperature=temperature or 0.3,
                    max_tokens=max_tokens or 4096,
                    tools=tools,
                )
            except Exception as e:
                last_error = e
                logger.warning("Tool-chat provider %s failed: %s", provider_name, e)
                
                # Check for rate limit (429) to trigger immediate cooldown
                error_str = str(e).lower()
                if "429" in error_str or "too many requests" in error_str or "rate limit" in error_str:
                    if hasattr(provider, 'stats'):
                        stats = getattr(provider, 'stats')
                        stats.consecutive_failures = 3
                        stats.last_active = datetime.now()
                        logger.info(f"Tool provider {provider_name} cooled down due to 429 error.")
        raise RuntimeError(f"MCP tool chat başarısız: {last_error}")

    async def chat_with_mcp_tool_loop(
        self,
        messages: list[dict],
        mcp_bridge: MCPBridge,
        *,
        max_tool_rounds: int = 8,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """MCP araç şemaları ile çok tur tool çağrısı (OpenAI/OpenRouter tool_calls)."""
        tools = mcp_bridge.openai_tools()
        if not tools:
            return await self.chat(messages, temperature=temperature, max_tokens=max_tokens)

        msgs: list[dict[str, Any]] = [dict(x) for x in messages]
        last = LLMResponse(content="", provider="none", model="none")

        for _ in range(max_tool_rounds):
            last = await self._chat_with_tools_single(msgs, tools, temperature, max_tokens)
            if not last.tool_calls:
                return last

            msgs.append(
                {
                    "role": "assistant",
                    "content": last.content or None,
                    "tool_calls": last.tool_calls,
                }
            )
            for tc in last.tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name") or ""
                raw_a = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw_a) if isinstance(raw_a, str) else (raw_a or {})
                except json.JSONDecodeError:
                    args = {}
                out = await mcp_bridge.invoke_openai_function(name, args)
                msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": out,
                    }
                )
        return last

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        """Stream chat with automatic fallback."""
        provider_name = self._select_provider()
        if not provider_name:
            raise RuntimeError("No LLM providers available")

        provider = self.providers[provider_name]
        try:
            import inspect
            sig = inspect.signature(provider.stream_chat)
            params = set(sig.parameters.keys())

            if 'tools' in params:
                async for token in provider.stream_chat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                ):
                    yield token
            else:
                # BaseProvider: convert dicts -> Message, no tools param
                from ultron.v2.providers.base import Message
                converted = []
                for m in messages:
                    if isinstance(m, dict):
                        converted.append(Message(role=m.get('role', 'user'), content=m.get('content', '')))
                    else:
                        converted.append(m)
                async for token in provider.stream_chat(converted):
                    yield token
        except Exception as e:
            logger.warning("Streaming provider %s failed: %s", provider_name, e)
            # Streaming fallback: use non-streaming chat
            response = await self.chat(messages, temperature, max_tokens, tools)
            yield response.content

    def get_status(self) -> dict:
        """Get status of ALL providers (active + inactive)."""
        result = {}
        # Show providers in priority order
        all_known = ["groq", "deepseek", "anthropic", "openrouter_free", "ollama", "gemini",
                     "cloudflare", "together", "huggingface", "mistral", "cohere",
                     "fireworks", "openrouter", "openai"]
        for name in all_known:
            provider = self.providers.get(name)
            if provider:
                # Handle both BaseProvider (is_configured) and LLMProvider (is_available)
                available = provider.is_configured() if hasattr(provider, 'is_configured') else provider.is_available()
                # Defansif: provider.get_model_name() yoksa fallback kullan
                model_name = provider.get_model_name() if hasattr(provider, 'get_model_name') else getattr(provider.config, 'default_model', 'unknown')
                
                # Defansif: stats attribute kontrolü
                if hasattr(provider, 'stats') and provider.stats:
                    stats_data = {
                        "total_calls": provider.stats.total_calls,
                        "success_rate": f"{provider.stats.success_rate:.1%}",
                        "avg_latency_ms": f"{provider.stats.avg_latency_ms:.0f}ms",
                        "health_score": f"{provider.stats.health_score:.2f}",
                    }
                else:
                    stats_data = {
                        "total_calls": 0,
                        "success_rate": "N/A",
                        "avg_latency_ms": "N/A",
                        "health_score": "N/A",
                    }
                
                result[name] = {
                    "available": available,
                    "model": model_name,
                    "stats": stats_data,
                }
        return result


class OpenRouterProvider(LLMProvider):
    """OpenRouter multi-model API gateway."""
    def __init__(self, model='openai/gpt-4o', api_key=''):
        self._model = model
        self._api_key = api_key
        self._base_url = 'https://openrouter.ai/api/v1'
        self.stats = ProviderStats()
    @property
    def name(self): return 'openrouter'
    def get_model_name(self): return self._model
    def is_available(self):
        return bool(self._api_key) and self._api_key.startswith('sk-or-')
    async def chat(self, messages, temperature=None, max_tokens=None, tools=None, stream=False):
        if not self.is_available():
            raise RuntimeError('OpenRouter API key not configured')
        from openai import AsyncOpenAI
        start = time.monotonic()
        self.stats.total_calls += 1
        try:
            client = AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/eren/ultron-assistant",
                    "X-Title": "Ultron v2.0 - Personal AI Assistant",
                },
                timeout=120.0,
            )
            kw = {'model': self._model, 'messages': messages}
            kw['temperature'] = temperature or 0.3
            kw['max_tokens'] = max_tokens or 4096
            if tools: kw['tools'] = tools
            resp = await client.chat.completions.create(**kw)
            # Close client to prevent resource leak
            await client.close()
            latency = (time.monotonic() - start) * 1000
            msg = resp.choices[0].message
            content = msg.content or ''
            tcalls = getattr(msg, "tool_calls", None)
            serialized: Optional[list[dict[str, Any]]] = None
            if tcalls:
                serialized = []
                for c in tcalls:
                    fn = getattr(c, "function", None)
                    serialized.append(
                        {
                            "id": getattr(c, "id", ""),
                            "type": getattr(c, "type", "function"),
                            "function": {
                                "name": getattr(fn, "name", "") if fn else "",
                                "arguments": getattr(fn, "arguments", "") if fn else "",
                            },
                        }
                    )
            self.stats.successful_calls += 1
            self.stats.total_latency_ms += latency
            self.stats.last_active = datetime.now()
            self.stats.consecutive_failures = 0
            u = resp.usage
            ic = getattr(u, 'prompt_tokens', 0) * 3 / 1_000_000
            oc = getattr(u, 'completion_tokens', 0) * 10 / 1_000_000
            self.stats.total_cost_usd += ic + oc
            return LLMResponse(content=content, provider=self.name, model=self._model,
                               tokens_used=getattr(u, 'total_tokens', 0),
                               cost_usd=ic+oc, latency_ms=latency,
                               finish_reason=resp.choices[0].finish_reason,
                               tool_calls=serialized)
        except Exception as e:
            self.stats.failed_calls += 1
            self.stats.last_error = str(e)
            self.stats.consecutive_failures += 1
            raise
    async def stream_chat(self, messages, temperature=None, max_tokens=None, tools=None):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(base_url=self._base_url, api_key=self._api_key)
        st = await client.chat.completions.create(
            model=self._model, messages=messages,
            temperature=temperature or 0.3, max_tokens=max_tokens or 4096, stream=True)
        async for chunk in st:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
