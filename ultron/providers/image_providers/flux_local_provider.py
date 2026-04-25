"""Local FLUX.1-schnell Image Provider — High-quality local image generation."""

import torch
import io
import asyncio
import logging
from typing import Optional
from diffusers import FluxPipeline

logger = logging.getLogger("ultron.providers.image.flux")

class FluxLocalProvider:
    """Local FLUX.1-schnell implementation using diffusers."""
    _instance = None
    _pipeline = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FluxLocalProvider, cls).__new__(cls)
        return cls._instance

    async def _load_pipeline(self):
        if self._pipeline is None:
            logger.info("Loading FLUX.1-schnell pipeline (this may take a while)...")
            loop = asyncio.get_event_loop()
            # Offload heavy model loading to thread pool
            try:
                self._pipeline = await loop.run_in_executor(
                    None,
                    lambda: FluxPipeline.from_pretrained(
                        "black-forest-labs/FLUX.1-schnell",
                        torch_dtype=torch.bfloat16
                    ).to("cuda" if torch.cuda.is_available() else "cpu")
                )
            except Exception as e:
                if "401" in str(e) or "gated" in str(e).lower():
                    logger.error("FLUX.1-schnell is a gated model. You must login to Hugging Face.")
                    raise RuntimeError(
                        "FLUX model access denied. Please run 'huggingface-cli login' in your terminal "
                        "and ensure you have accepted the terms at: "
                        "https://huggingface.co/black-forest-labs/FLUX.1-schnell"
                    )
                raise e
            logger.info("FLUX.1-schnell loaded successfully.")

    async def generate(
        self, 
        prompt: str, 
        width: int = 1024, 
        height: int = 1024, 
        steps: int = 4, 
        seed: int = -1
    ) -> bytes:
        """Generate an image from prompt and return as bytes."""
        await self._load_pipeline()

        generator = torch.Generator().manual_seed(
            seed if seed != -1 else torch.randint(0, 2**32, (1,)).item()
        )

        loop = asyncio.get_event_loop()
        image = await loop.run_in_executor(
            None,
            lambda: self._pipeline(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=steps,
                generator=generator,
            ).images[0]
        )

        # Convert PIL to bytes
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()

    def is_available(self) -> bool:
        """Check if local GPU or CPU is available for generation."""
        try:
            import diffusers
            return True
        except ImportError:
            return False

# Global Instance
flux_local = FluxLocalProvider()
