"""Image Generation Agent — Intelligent image creation with prompt optimization."""

import os
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router
from ultron.providers.image_providers.flux_local_provider import flux_local

logger = logging.getLogger("ultron.agents.creative.image")

class ImageGenerationAgent(BaseAgent):
    agent_name = "ImageGenerationAgent"
    agent_description = "Generates images using local or cloud models with prompt optimization."

    """Generates images using local or cloud models with prompt optimization."""
    
    def __init__(self):
        super().__init__(
            agent_name="ImageGenerationAgent",
            agent_description="Expert in creating high-quality images from text descriptions.",
            capabilities=["image_generation", "prompt_optimization", "art_direction"],
        )
        self.output_dir = "data/generated/images"
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.STYLE_TEMPLATES = {
            "realistic": "photorealistic, ultra-detailed, 8K, cinematic lighting, sharp focus",
            "anime": "anime style, vibrant colors, clean lines, Studio Ghibli inspired",
            "cyberpunk": "cyberpunk aesthetic, neon lights, rainy atmosphere, futuristic, high contrast",
            "oil_painting": "classical oil painting, textured brush strokes, museum quality, rich colors",
            "watercolor": "watercolor painting, soft edges, translucent washes, artistic",
            "sketch": "pencil sketch, hand-drawn, graphite texture, cross-hatching"
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute the image generation task."""
        self.status = AgentStatus.RUNNING
        start_time = datetime.now()
        
        try:
            raw_prompt = task.input_data
            style = task.context.get("style", "realistic")
            size = task.context.get("size", "1024x1024")
            
            # 1. Optimize Prompt
            optimized_prompt = await self._optimize_prompt(raw_prompt, style)
            logger.info(f"Generating image with optimized prompt: {optimized_prompt}")
            
            # 2. Select Provider & Generate
            width, height = map(int, size.split('x'))
            
            # For now, we prioritize local FLUX
            if flux_local.is_available():
                image_bytes = await flux_local.generate(
                    prompt=optimized_prompt,
                    width=width,
                    height=height
                )
            else:
                # Fallback to DALL-E 3 if OpenAI is configured
                image_bytes = await self._generate_openai(optimized_prompt, size)
                
            # 3. Save Image
            filename = f"gen_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_bytes)
                
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "image_path": filepath,
                    "image_url": f"/api/v2/image/{filename}",
                    "optimized_prompt": optimized_prompt,
                    "style": style,
                    "model": "FLUX.1-schnell" if flux_local.is_available() else "DALL-E 3"
                },
                latency_ms=latency
            )

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error=str(e)
            )
        finally:
            self.status = AgentStatus.IDLE

    async def _optimize_prompt(self, user_prompt: str, style: str) -> str:
        """Use LLM to expand user prompt into a high-quality image prompt."""
        style_hint = self.STYLE_TEMPLATES.get(style, self.STYLE_TEMPLATES["realistic"])
        
        prompt = f"""
Convert the following user description into a highly detailed English image generation prompt.
User Input: {user_prompt}
Style: {style}
Style Hint: {style_hint}

Return ONLY the optimized prompt string. No chat, no quotes.
"""
        resp = await router.chat([{"role": "user", "content": prompt}])
        return f"{resp.content}, {style_hint}".strip()

    async def _generate_openai(self, prompt: str, size: str) -> bytes:
        """Fallback generation using OpenAI DALL-E 3."""
        # This assumes the router has openai provider
        # For simplicity, we'll implement a direct call or placeholder
        # In a real scenario, this would use the OpenAI API
        raise NotImplementedError("OpenAI fallback not implemented yet. Use local FLUX.")

    async def health_check(self) -> bool:
        return flux_local.is_available()
