import logging
from typing import Any, Dict, List, Optional
from ultron.v2.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)

class ReasoningEngine:
    """Engine for high-level logical reasoning, CoT, and reflection."""
    
    def __init__(self, llm_router: LLMRouter, memory: Any):
        self.llm = llm_router
        self.memory = memory

    async def think(self, query: str, context: Optional[str] = None) -> str:
        """Process a query through a deep reasoning pipeline (Chain-of-Thought)."""
        logger.info("Deep reasoning triggered for: %s", query[:50])
        
        # Phase 1: Decomposition
        plan = await self._generate_reasoning_plan(query, context)
        
        # Phase 2: Step-by-step execution
        thought_process = []
        for step in plan:
            result = await self._execute_reasoning_step(step, thought_process, context)
            thought_process.append(f"Step: {step}\nResult: {result}")
        
        # Phase 3: Final synthesis
        final_answer = await self._synthesize_final_answer(query, thought_process)
        return final_answer

    async def _generate_reasoning_plan(self, query: str, context: Optional[str]) -> List[str]:
        prompt = (
            f"Query: {query}\n"
            f"Context: {context or 'None'}\n\n"
            "Break this down into logical reasoning steps to reach a foolproof conclusion. "
            "Output only the steps as a numbered list."
        )
        resp = await self.llm.chat([{"role": "user", "content": prompt}])
        steps = [line.strip() for line in resp.content.split("\n") if line.strip() and any(c.isdigit() for c in line[:2])]
        return steps or [query]

    async def _execute_reasoning_step(self, step: str, history: List[str], context: Optional[str]) -> str:
        history_str = "\n".join(history)
        prompt = (
            f"Context: {context or 'None'}\n"
            f"Past Thoughts:\n{history_str}\n\n"
            f"Current Step to Solve: {step}\n"
            "Provide a logical analysis for this step."
        )
        resp = await self.llm.chat([{"role": "user", "content": prompt}])
        return resp.content

    async def _synthesize_final_answer(self, query: str, thought_process: List[str]) -> str:
        thoughts = "\n".join(thought_process)
        prompt = (
            f"Original Query: {query}\n"
            f"Detailed Thought Process:\n{thoughts}\n\n"
            "Based on the above reasoning, provide the final, most accurate and comprehensive answer. "
            "Include general knowledge context where appropriate."
        )
        resp = await self.llm.chat([{"role": "user", "content": prompt}])
        return resp.content

    def get_stats(self) -> dict:
        """Return reasoning engine statistics for the status dashboard."""
        return {
            "engine": "CoT-ReasoningEngine",
            "status": "active",
        }
