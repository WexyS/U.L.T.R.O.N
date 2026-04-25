"""Note-Taking Agent — Creating and managing Markdown notes."""

import logging
import os
from typing import List, Dict, Any
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.productivity.notes")

class NoteTakingAgent(BaseAgent):
    agent_name = "NoteTakingAgent"
    agent_description = "Specialized Genesis agent for NoteTaking tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="NoteTaking",
            agent_description="Expert in structured note-taking using Markdown. Automatically tags and links notes.",
            capabilities=["note_taking", "markdown", "archiving"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.notes_dir = "data/notes"

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        action = task.task_type # create, search, list
        
        try:
            if action == "create":
                result = await self._create_note(task.input_data)
            else:
                result = await self._list_notes()

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=result
            )
        except Exception as e:
            logger.error(f"Note-taking failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def _create_note(self, data: Dict[str, Any]) -> str:
        os.makedirs(self.notes_dir, exist_ok=True)
        title = data.get("title", "Untitled Note")
        content = data.get("content", "")
        
        # Automatic tagging via LLM
        prompt = [{"role": "system", "content": "Generate 3 relevant tags for the following note. Return as a comma-separated list."}, {"role": "user", "content": content}]
        tag_resp = await router.chat(prompt)
        tags = tag_resp.content.strip()
        
        filename = f"{title.lower().replace(' ', '_')}.md"
        path = os.path.join(self.notes_dir, filename)
        
        full_content = f"# {title}\n\nTags: {tags}\nDate: {datetime.now().strftime('%Y-%m-%d')}\n\n{content}"
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(full_content)
            
        return f"Note created: {path}"

    async def _list_notes(self) -> List[str]:
        if not os.path.exists(self.notes_dir):
            return []
        return os.listdir(self.notes_dir)

    async def health_check(self) -> bool:
        return True
