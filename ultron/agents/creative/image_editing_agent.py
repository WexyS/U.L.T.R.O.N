"""Image Editing Agent — Background removal, upscaling, and descriptions."""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image

from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

logger = logging.getLogger("ultron.agents.creative.edit")

class ImageEditingAgent(BaseAgent):
    agent_name = "ImageEditingAgent"
    agent_description = "Handles image manipulation tasks like background removal and upscaling."

    """Handles image manipulation tasks like background removal and upscaling."""
    
    def __init__(self):
        super().__init__(
            agent_name="ImageEditingAgent",
            agent_description="Specialist in image manipulation and quality enhancement.",
            capabilities=["background_removal", "upscaling", "image_description"],
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute the editing task."""
        self.status = AgentStatus.RUNNING
        start_time = datetime.now()
        
        try:
            operation = task.context.get("operation")
            image_path = task.input_data # Usually the path to the image
            
            if not os.path.exists(image_path):
                return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=f"File not found: {image_path}")

            if operation == "remove_bg":
                result_path = await self._remove_bg(image_path)
            elif operation == "upscale":
                result_path = await self._upscale(image_path)
            elif operation == "describe":
                description = await self._describe(image_path)
                return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=True, output={"description": description})
            else:
                return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=f"Unknown operation: {operation}")

            latency = (datetime.now() - start_time).total_seconds() * 1000
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={"result_path": result_path},
                latency_ms=latency
            )

        except Exception as e:
            logger.error(f"Image editing failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def _remove_bg(self, image_path: str) -> str:
        """Remove background using rembg."""
        from rembg import remove
        
        output_path = image_path.replace(".png", "_nobg.png").replace(".jpg", "_nobg.png")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._process_remove_bg, image_path, output_path)
        
        return output_path

    def _process_remove_bg(self, input_path, output_path):
        from rembg import remove
        with open(input_path, 'rb') as i:
            input_data = i.read()
            output_data = remove(input_data)
            with open(output_path, 'wb') as o:
                o.write(output_data)

    async def _upscale(self, image_path: str) -> str:
        """Upscale image (Simulation for now)."""
        # Real implementation would use realesrgan or similar
        await asyncio.sleep(1)
        output_path = image_path.replace(".png", "_upscaled.png").replace(".jpg", "_upscaled.png")
        
        # Simple PIL resize as placeholder
        img = Image.open(image_path)
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        img.save(output_path)
        
        return output_path

    async def _describe(self, image_path: str) -> str:
        """Describe image using vision capabilities (e.g. LLaVA)."""
        # Placeholder
        return "A high-quality generated image being processed by Ultron."

    async def health_check(self) -> bool:
        return True
