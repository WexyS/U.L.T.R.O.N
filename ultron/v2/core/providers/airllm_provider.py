"""AirLLM Provider — Llama-3.1-405B-Instruct (4-bit) entegrasyonu."""

import asyncio
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class AirLLMProvider:
    """AirLLM Provider for running massive models natively (Layer-wise inference)."""
    
    def __init__(self, model_id: str = "meta-llama/Meta-Llama-3.1-405B-Instruct", compression: str = "4bit"):
        self.model_id = model_id
        self.compression = compression
        self.model = None
        
    def _load_model(self):
        if self.model is None:
            logger.info(f"🧠 AirLLM Modeli yükleniyor: {self.model_id} ({self.compression})... Bu işlem disk hızına bağlı olarak vakit alabilir.")
            from airllm import AutoModel
            self.model = AutoModel.from_pretrained(
                self.model_id,
                compression=self.compression,
                prefetching=True
            )
            logger.info("✅ AirLLM Llama 3.1 405B başarıyla yüklendi!")

    def _generate_sync(self, prompt: str, max_tokens: int = 1024) -> str:
        """Senkron AirLLM çıkarımı (Layer-wise)."""
        self._load_model()
        
        input_text = [prompt]
        inputs = self.model.tokenizer(input_text, max_length=4096, return_tensors="pt")
        
        logger.info("⏳ Derin analiz yapılıyor (Llama 405B katmanları sırayla işleniyor)...")
        outputs = self.model.generate(
            inputs['input_ids'],
            max_new_tokens=max_tokens,
            use_cache=True,
            return_dict_in_generate=True
        )
        
        result = self.model.tokenizer.decode(outputs.sequences[0], skip_special_tokens=True)
        if result.startswith(prompt):
            result = result[len(prompt):].strip()
            
        return result

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1024, **kwargs) -> Any:
        """Asenkron wrapper (Ana döngü veya UI kilitlenmesin diye thread pool kullanır)."""
        # Llama 3 ChatML Formatı
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>\n"
        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._generate_sync, prompt, max_tokens)
        
        class MockMessage:
            def __init__(self, content): self.content = content
        class MockResponse:
            def __init__(self, content): self.content = content; self.message = MockMessage(content)
            
        return MockResponse(result)