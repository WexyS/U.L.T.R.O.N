"""Image Analysis Agent — Understanding and describing visual content."""

import logging
import json
import re
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.media.image_analysis")

class ImageAnalysisAgent(BaseAgent):
    agent_name = "ImageAnalysisAgent"
    agent_description = "Specialized Genesis agent for ImageAnalysis tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="ImageAnalysis",
            agent_description="Analyzes images to describe content, detect objects, and extract text using vision models.",
            capabilities=["image_description", "object_detection", "vision_ocr"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        image_path = task.input_data
        
        try:
            # 1. OCR (using skill_engine)
            ocr_text = await self.request_skill("skill_ocr", path=image_path)
            
            # 2. Vision Analysis (LLM with Vision Support)
            # Assuming LLMRouter supports vision in the future, for now we describe based on OCR and metadata
            prompt = [
                {"role": "system", "content": "Analyze the image data. Describe what is likely in the image based on OCR text and context."},
                {"role": "user", "content": f"Image Path: {image_path}\nOCR Extracted: {ocr_text}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "description": resp.content,
                    "ocr_text": ocr_text
                }
            )
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
