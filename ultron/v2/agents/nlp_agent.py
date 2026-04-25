import os
import json
import logging
from typing import Optional, Any
from pathlib import Path
from datetime import datetime

from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult
from ultron.v2.core.llm_router import router as default_router

logger = logging.getLogger(__name__)

GLOSSARY_PATH = Path("glossary.json")

class NLPAgent(BaseAgent):
    """
    NLP & Localization Agent.
    Implements advanced translation theories (Skopos, Dynamic Equivalence) 
    and maintains a contextual glossary.
    """

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="NLPAgent",
            agent_description="Advanced localization node using linguistic translation theories.",
            capabilities=["translation", "nlp", "glossary_management"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.router = default_router
        self._ensure_glossary_exists()

    def _ensure_glossary_exists(self):
        if not GLOSSARY_PATH.exists():
            with open(GLOSSARY_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load_glossary(self) -> dict:
        try:
            with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_glossary(self, data: dict):
        with open(GLOSSARY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _default_system_prompt(self) -> str:
        glossary = self._load_glossary()
        glossary_text = json.dumps(glossary, ensure_ascii=False, indent=2)
        
        return f"""You are the Ultron Elite NLP & Localization Node.
Your primary directive is to perform deep syntactic and semantic translations across languages (especially English, German, Russian, and Turkish).

You must NOT do mechanical word-for-word translations. Instead, you MUST apply:
1. Skopos Theory: Prioritize the purpose of the target text and its intended audience.
2. Nida's Dynamic Equivalence: Ensure the target text elicits the same effect on its audience as the original text did on its audience.

Always maintain high corporate or academic standards depending on the context.

Current Project Glossary (strictly adhere to these terms when applicable):
{glossary_text}

You have the following tools available:
1. `add_to_glossary`: Add a new term to the contextual memory. (args: term, translation, context)

If the user asks you to save a term, use the tool. Otherwise, output the professional translation.
Always explain briefly which translation strategies you used in a <thought> block before the translation.
"""

    async def execute(self, task: AgentTask) -> AgentResult:
        logger.info(f"NLP Agent executing task: {task.input_data}")
        start_time = datetime.now()
        
        # We define a tool definition for LLM
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "add_to_glossary",
                    "description": "Adds a term to the persistent glossary.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "term": {"type": "string"},
                            "translation": {"type": "string"},
                            "context": {"type": "string"}
                        },
                        "required": ["term", "translation"]
                    }
                }
            }
        ]

        messages = [
            {"role": "system", "content": self._default_system_prompt()},
            {"role": "user", "content": str(task.input_data)}
        ]

        response = await self.router.chat(messages, tools=tools, temperature=0.3)
        tools_used = []

        if response.tool_calls:
            for tc in response.tool_calls:
                if tc.name == "add_to_glossary":
                    term = tc.arguments.get("term")
                    trans = tc.arguments.get("translation")
                    ctx = tc.arguments.get("context", "")
                    
                    glossary = self._load_glossary()
                    glossary[term] = {"translation": trans, "context": ctx}
                    self._save_glossary(glossary)
                    
                    messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": "Term added successfully."})
                    tools_used.append("add_to_glossary")
            
            response = await self.router.chat(messages, tools=tools, temperature=0.3)

        latency = (datetime.now() - start_time).total_seconds() * 1000

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output=response.content,
            tools_used=tools_used,
            latency_ms=latency
        )

    async def health_check(self) -> bool:
        return True
