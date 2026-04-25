"""Cloner Agent — Autonomous website architecture extraction and reconstruction."""

import logging
from pathlib import Path
from typing import Optional

from ultron.agents.base import Agent
from ultron.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus, ToolCall
from ultron.core.event_bus import EventBus
from ultron.core.blackboard import Blackboard
from ultron.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class ClonerAgent(Agent):
    agent_name = "ClonerAgent"
    agent_description = "Specialized agent for cloning websites (UI/UX extraction and reconstruction)."

    """Specialized agent for cloning websites (UI/UX extraction and reconstruction).

    Workflow:
    1. Visual Analysis (via Researcher)
    2. Architecture Mapping
    3. Component Generation (React/Tailwind or HTML/CSS)
    4. Backend Mocking/Integration
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
        work_dir: str = "./workspace/clones",
    ) -> None:
        super().__init__(
            role=AgentRole.CODER,  # Cloner acts as a high-level coder
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
        )
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def _default_system_prompt(self) -> str:
        return (
            "You are an expert Frontend Architect and UI/UX Cloner.\n"
            "Your goal is to reconstruct websites based on visual analysis data.\n"
            "You prefer modern stacks like React, Vite, and Tailwind CSS.\n"
            "You focus on high-fidelity replication of colors, fonts, and layouts.\n"
            "When generating code, ensure it is responsive and clean."
        )

    async def _subscribe_events(self) -> None:
        async def on_clone_request(event) -> None:
            if not self._running:
                return
            task = Task(
                id=event.data.get("task_id"),
                description=event.data.get("description", ""),
                context=event.data.get("context", {}),
            )
            result = await self.execute(task)
            await self._publish_event("clone_result", {
                "task_id": task.task_id,
                "output": result.output,
                "success": result.status == TaskStatus.SUCCESS,
            })

        self.event_bus.subscribe("clone_request", on_clone_request)

    async def execute(self, task: Task) -> TaskResult:
        """Execute a site cloning task."""
        self.state.status = AgentStatus.BUSY
        self.state.current_task = task.task_id

        try:
            url = task.context.get("url")
            if not url and "http" in task.input_data:
                import re
                match = re.search(r'https?://\S+', task.input_data)
                if match: url = match.group(0)

            if not url:
                return TaskResult(task_id=task.task_id, status=TaskStatus.FAILED, error="No URL provided for cloning")

            # Step 1: Visual Analysis (Request to Researcher)
            logger.info("Requesting visual analysis for %s", url)
            analysis_task = Task(
                description=f"Analyze the visual style and structure of {url}",
                intent="architect",
                context={"url": url}
            )
            
            # Direct call to researcher capability if available, or via event bus
            # For simplicity in this implementation, we use the blackboard/event pattern
            # but here we'll simulate the coordination.
            
            # 1. Ask Researcher to extract styles
            from ultron.agents.researcher import ResearcherAgent
            researcher = ResearcherAgent(self.llm_router, self.event_bus, self.blackboard)
            visual_data_result = await researcher.execute(analysis_task)
            
            if visual_data_result.status != TaskStatus.SUCCESS:
                return TaskResult(task_id=task.task_id, status=TaskStatus.FAILED, error=f"Visual analysis failed: {visual_data_result.error}")

            visual_data = visual_data_result.context.get("visual_data", {})
            
            # Step 2: Generate Architecture Plan
            plan = await self._generate_reconstruction_plan(url, visual_data)
            
            # Step 3: Generate Code (Frontend)
            frontend_code = await self._generate_frontend(visual_data, plan)
            
            # Step 4: Generate Backend (Mock/Real)
            backend_code = await self._generate_backend(visual_data, plan)
            
            # Step 5: Save Files
            project_name = url.split("//")[-1].split("/")[0].replace(".", "_")
            project_dir = self.work_dir / project_name
            project_dir.mkdir(parents=True, exist_ok=True)
            
            (project_dir / "index.html").write_text(frontend_code.get("html", ""), encoding="utf-8")
            if "css" in frontend_code:
                (project_dir / "style.css").write_text(frontend_code["css"], encoding="utf-8")
            if "js" in frontend_code:
                (project_dir / "app.js").write_text(frontend_code["js"], encoding="utf-8")
            
            if backend_code:
                (project_dir / "server.py").write_text(backend_code, encoding="utf-8")

            output = [
                f"✅ **KLONLAMA TAMAMLANDI: {project_name}**",
                f"📂 **Klasör:** `{project_dir}`",
                f"🎨 **Analiz:** {len(visual_data.get('colors', []))} renk, {len(visual_data.get('fonts', []))} font tespit edildi.",
                "",
                "🚀 **Sıradaki Adımlar:**",
                "1. Klasöre gidin.",
                "2. `index.html` dosyasını tarayıcıda açın.",
                "3. `server.py` dosyasını çalıştırarak backend'i simüle edin."
            ]

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.SUCCESS,
                output="\\n".join(output),
                metadata={"project_dir": str(project_dir), "visual_data": visual_data}
            )

        except Exception as e:
            logger.error("Cloning failed: %s", e)
            return TaskResult(task_id=task.task_id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self.state.status = AgentStatus.IDLE
            self.state.current_task = None

    async def _generate_reconstruction_plan(self, url: str, visual_data: dict) -> str:
        messages = self._build_messages(
            f"Based on this visual analysis of {url}, create a reconstruction plan.\n"
            f"Visual Data: {visual_data}\n"
            "Identify the main sections (Header, Hero, Features, Footer) and the tech stack."
        )
        response = await self._llm_chat(messages)
        return response.content

    async def _generate_frontend(self, visual_data: dict, plan: str) -> dict:
        messages = self._build_messages(
            f"Generate the HTML and CSS for this site reconstruction.\n"
            f"Plan: {plan}\n"
            f"Visual Styles: {visual_data}\n"
            "Use Tailwind CSS (via CDN) for styling. Return a JSON object with 'html', 'css', 'js' keys."
        )
        # Use a higher quality model for code generation if available
        response = await self._llm_chat(messages, temperature=0.1)
        
        # Simple extraction logic (LLM might return raw JSON or markdown)
        import re
        content = response.content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            import json
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        return {"html": content, "css": "", "js": ""}

    async def _generate_backend(self, visual_data: dict, plan: str) -> str:
        messages = self._build_messages(
            f"Generate a simple FastAPI backend (server.py) to support this frontend.\n"
            f"Interactive elements detected: {visual_data.get('interactive_elements', [])}\n"
            "Include basic endpoints for forms detected."
        )
        response = await self._llm_chat(messages, temperature=0.1)
        return response.content

