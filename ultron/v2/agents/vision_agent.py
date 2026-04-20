"""Ultron Vision Agent - High-performance desktop awareness and visual analysis."""
from typing import Any, Dict, Optional
import base64
import io
import logging
import asyncio
from datetime import datetime

from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)

class UltronVisionAgent(Agent):
    """Integrated vision agent for desktop awareness.
    
    Can capture screen natively or receive snapshots from Ultron Vision Desktop app.
    """
    def __init__(self, llm_router: LLMRouter, event_bus: EventBus, blackboard: Blackboard):
        # We use AgentRole.VISION which was rebranded in types.py
        super().__init__(role=AgentRole.VISION, llm_router=llm_router, event_bus=event_bus, blackboard=blackboard)
        self.latest_screen: Optional[str] = None
        self.last_capture_time: Optional[datetime] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitor_interval = 5.0 # seconds
        self._indicator_process: Optional[Any] = None

    def _default_system_prompt(self) -> str:
        return (
            "You are Ultron Vision, the visual cortex of the Ultron AGI system.\n"
            "Your role is to analyze screen context, identify UI elements, and assist with desktop-based tasks.\n"
            "You have direct access to visual data and can describe precisely what is happening on the user's screen."
        )

    async def _subscribe_events(self) -> None:
        async def on_vision_request(event):
            if not self._running: return
            task = Task(id=event.data.get("task_id"), description=event.data.get("description", ""), context=event.data.get("context", {}))
            result = await self.execute(task)
            await self._publish_event("vision_result", {"task_id": task.id, "output": result.output, "error": result.error})
            
        self.event_bus.subscribe("vision_request", on_vision_request)
        
        # New: Toggle monitoring via events
        async def on_toggle_vision(event):
            enabled = event.data.get("enabled", True)
            if enabled:
                await self.start_monitoring()
            else:
                await self.stop_monitoring()
        
        self.event_bus.subscribe("toggle_vision", on_toggle_vision)
        
        # Start monitoring immediately when agent starts
        asyncio.create_task(self.start_monitoring())

    async def start_monitoring(self):
        """Start continuous screen monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("Ultron Vision: Continuous monitoring started.")
        await self._show_indicator()

    async def stop_monitoring(self):
        """Stop continuous screen monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
        logger.info("Ultron Vision: Continuous monitoring stopped.")
        await self._hide_indicator()

    async def _monitor_loop(self):
        """Background loop to capture screen periodically."""
        while self._running:
            try:
                await self.capture_screen()
                await asyncio.sleep(self._monitor_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Vision monitor loop error: {e}")
                await asyncio.sleep(10)

    async def _show_indicator(self):
        """Show the visual 'eye' indicator on screen."""
        if self._indicator_process:
            return
        
        try:
            import subprocess
            import sys
            # Start the indicator script as a separate process
            indicator_script = "ultron/v2/agents/vision_indicator.py"
            self._indicator_process = subprocess.Popen([sys.executable, indicator_script])
        except Exception as e:
            logger.error(f"Failed to show vision indicator: {e}")

    async def _hide_indicator(self):
        """Hide the visual indicator."""
        if self._indicator_process:
            self._indicator_process.terminate()
            self._indicator_process = None

    async def capture_screen(self) -> Optional[str]:
        """Capture the screen natively as base64."""
        try:
            import pyautogui
            from PIL import Image
            import asyncio
            
            # Use a thread pool to avoid blocking the async loop
            screenshot = await asyncio.to_thread(pyautogui.screenshot)
            
            buffered = io.BytesIO()
            # Resize for LLM processing if too large
            if screenshot.width > 1920:
                screenshot.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
            
            screenshot.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            self.latest_screen = img_str
            self.last_capture_time = datetime.now()
            
            await self.blackboard.write("latest_vision_screen", {
                "image_b64": img_str,
                "timestamp": self.last_capture_time.isoformat()
            }, owner=self.role.value)
            return img_str
        except ImportError:
            logger.warning("pyautogui or pillow not installed. Native screen capture unavailable.")
            return None
        except Exception as e:
            logger.error(f"Native capture failed: {e}")
            return None

    async def execute(self, task: Task) -> TaskResult:
        self.state.status = AgentStatus.BUSY
        try:
            action = task.context.get("action", "analyze")
            
            # 1. Prepare visual context
            image_b64 = task.context.get("image_b64") or self.latest_screen
            
            # If no image provided and no latest screen, try native capture
            if not image_b64 or action == "capture":
                image_b64 = await self.capture_screen()
                
            if not image_b64:
                return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error="No visual context available. Ensure Ultron Vision is running or dependencies are installed.")

            # 2. Process based on action
            if action in ["analyze", "capture", "process_screen"]:
                query = task.description or "Describe what is on the screen and identify key UI elements."
                
                # Use Multimodal Vision Support if available in LLM Router
                try:
                    # Check if llm_router has vision_chat (we might need to implement it in llm_router if not there)
                    if hasattr(self.llm_router, 'vision_chat'):
                        resp = await self.llm_router.vision_chat(
                            prompt=f"{self._default_system_prompt()}\n\nTask: {query}",
                            image_base64=image_b64
                        )
                    else:
                        raise AttributeError("LLM Router does not support vision_chat yet.")
                        
                    return TaskResult(task_id=task.id, status=TaskStatus.SUCCESS, output=resp.content)
                except Exception as vision_err:
                    logger.warning(f"Vision analysis failed or not supported, falling back to text description: {vision_err}")
                    messages = [
                        {"role": "system", "content": self._default_system_prompt()},
                        {"role": "user", "content": f"[Visual Data Present] Query: {query}"}
                    ]
                    resp = await self.llm_router.chat(messages, max_tokens=1024)
                    return TaskResult(task_id=task.id, status=TaskStatus.SUCCESS, output=resp.content)
            
            elif action == "chat":
                messages = [
                    {"role": "system", "content": self._default_system_prompt()},
                    {"role": "user", "content": task.description}
                ]
                resp = await self.llm_router.chat(messages, max_tokens=1024)
                return TaskResult(task_id=task.id, status=TaskStatus.SUCCESS, output=resp.content)
            else:
                return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error=f"Unknown action {action}")
                
        except Exception as e:
            logger.error(f"Vision execution error: {e}")
            return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self.state.status = AgentStatus.IDLE
