"""ReAct Orchestrator for Ultron v3.0 — The AGI Brain."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.agent_registry import registry
from ultron.core.event_bus import event_bus
from ultron.core.llm_router import router
from ultron.memory.user_profile_manager import manager as user_profile
from ultron.core.personality import personality_engine
from ultron.core.reasoning_engine import ReasoningEngine
from ultron.core.safety_filter import SafetyFilter

logger = logging.getLogger("ultron.orchestrator")

MAX_ITERATIONS = 8
TOKEN_BUDGET = 1000

class StepType(str, Enum):
    THINK = "think"
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    REFLECT = "reflect"

@dataclass
class ReActStep:
    step_type: StepType
    content: str
    tokens_used: int = 0
    tool_used: Optional[str] = None
    result: Optional[Any] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class SubTask:
    agent_name: str
    description: str
    input_data: str
    parallel: bool = False
    status: str = "pending"
    result: Optional[Any] = None

@dataclass
class ReActChain:
    steps: List[ReActStep] = field(default_factory=list)
    max_iterations: int = MAX_ITERATIONS
    token_budget: int = TOKEN_BUDGET
    current_iteration: int = 0
    tokens_consumed: int = 0
    is_complete: bool = False

    @property
    def budget_remaining(self) -> int:
        return max(0, self.token_budget - self.tokens_consumed)

    @property
    def budget_exhausted(self) -> bool:
        return self.tokens_consumed >= self.token_budget

    def add_step(self, step: ReActStep) -> None:
        self.steps.append(step)
        self.tokens_consumed += step.tokens_used
        if self.budget_exhausted:
            self.is_complete = True


class AuditLogger:
    def __init__(self, db_path: str):
        import sqlite3
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS react_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                step_number INTEGER,
                step_type TEXT,
                content TEXT,
                success INTEGER,
                timestamp TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def log_step(self, session_id: str, step_number: int, step: ReActStep, success: bool) -> None:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO react_audit (session_id, step_number, step_type, content, success, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id,
                step_number,
                step.step_type.value if isinstance(step.step_type, StepType) else str(step.step_type),
                step.content,
                int(success),
                datetime.now().isoformat(),
            )
        )
        conn.commit()
        conn.close()


def _estimate_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return max(1, len(text) // 3)

class ReActOrchestrator(BaseAgent):
    """The central AGI brain of Ultron v3.0 using ReAct + CoT reasoning."""

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="ReActOrchestrator",
            agent_description="Central AGI brain using Reason+Act logic to coordinate all agents.",
            capabilities=["reasoning", "planning", "orchestration", "reflection"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.chain = ReActChain()
        self.reasoner = ReasoningEngine(router)
        self.safety = SafetyFilter(router)

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute the high-level orchestration loop."""
        self.status = AgentStatus.RUNNING
        self.chain = ReActChain()
        start_time = datetime.now()

        try:
            # 0. RECALL & LEARN
            user_context = user_profile.get_summary_for_prompt()
            task.context["user_profile"] = user_context
            
            lesson_context = ""
            if self.memory:
                lesson_context = self.memory.get_lesson_context(task.input_data)
                if lesson_context:
                    logger.info("Orchestrator found relevant lessons in memory.")
                    task.context["lesson_context"] = lesson_context

            # 1. PERCEIVE, THINK & ANALYZE MOOD
            thought = await self._think(task)
            sentiment = await self._analyze_sentiment(task.input_data)
            task.context["current_mood"] = sentiment
            logger.info(f"Detected user sentiment: {sentiment}")
            
            self.chain.steps.append(ReActStep("think", f"[Mood: {sentiment}] {thought}"))
            await self._emit_step(self.chain.steps[-1])

            # 2. DECOMPOSE & PLAN
            plan = await self._plan(task, thought)
            self.chain.steps.append(ReActStep("plan", json.dumps(plan, indent=2)))
            await self._emit_step(self.chain.steps[-1])

            # 3. ACT & OBSERVE loop
            while self.chain.current_iteration < self.chain.max_iterations and not self.chain.is_complete:
                self.chain.current_iteration += 1
                logger.info(f"Orchestration Iteration {self.chain.current_iteration}")

                # Execute planned steps for this iteration
                results = await self._execute_plan_steps(plan)
                
                observation = self._synthesize_observation(results)
                self.chain.steps.append(ReActStep("observe", observation))
                await self._emit_step(self.chain.steps[-1])

                # 4. REFLECT
                reflection = await self._reflect(task, self.chain.steps)
                self.chain.steps.append(ReActStep("reflect", reflection))
                await self._emit_step(self.chain.steps[-1])

                if "TASK_COMPLETE" in reflection:
                    self.chain.is_complete = True
                else:
                    # Re-plan if not complete
                    plan = await self._plan(task, reflection)
                    self.chain.steps.append(ReActStep("plan", json.dumps(plan, indent=2)))
                    await self._emit_step(self.chain.steps[-1])

            # 5. RESPOND
            final_response = await self._generate_final_response(task, self.chain.steps)
            
            # 6. LEARN FROM INTERACTION (Priority 2: User Profiling)
            asyncio.create_task(user_profile.update_from_interaction(
                task.input_data, final_response, 
                llm_callable=lambda p: router.generate(p, model_type="fast")
            ))
            
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=self.chain.is_complete,
                output=final_response,
                latency_ms=latency,
                tools_used=[s.tool_used for s in self.chain.steps if s.tool_used]
            )

        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error=str(e)
            )
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True

    # ── Internal Reasoning Methods ────────────────────────────────────────

    async def _think(self, task: AgentTask) -> str:
        agents_info = "\n".join([f"- {a['name']}: {a['description']}" for a in registry.list_agents()])
        user_profile_data = task.context.get("user_profile", "")
        
        # 1. Personality Guided Prompt
        context = f"AVAILABLE AGENTS:\n{agents_info}\n\nUSER PROFILE:\n{user_profile_data}"
        
        # 2. Advanced Reasoning (CoT)
        reasoning = await self.reasoner.think_and_answer(task.input_data)
        
        # Emit thinking to frontend
        if reasoning.thinking:
            await self._emit_step(ReActStep("think", reasoning.thinking))
            
        return reasoning.answer

    async def _plan(self, task: AgentTask, thought: str) -> List[Dict[str, Any]]:
        agents_names = ", ".join([a['name'] for a in registry.list_agents()])
        prompt = [
            {"role": "system", "content": (
                "Convert the thought process into a formal execution plan.\n"
                "Rules:\n"
                "- Return ONLY a JSON list of subtasks.\n"
                "- Each subtask must map to an available agent.\n"
                "- Use 'parallel': true if a task can run alongside others.\n"
                "- Use 'input_data' to provide the EXACT prompt for the sub-agent.\n\n"
                f"AVAILABLE AGENTS: [{agents_names}]\n\n"
                "JSON Format: [{\"agent_name\": \"...\", \"description\": \"...\", \"input_data\": \"...\", \"parallel\": bool}]"
            )},
            {"role": "user", "content": f"Thought Process: {thought}"}
        ]
        resp = await router.chat(prompt)
        try:
            # Extract JSON from response
            match = re.search(r"\[[\s\S]*\]", resp.content)
            if match:
                plan = json.loads(match.group())
                # Validation: Ensure agents exist
                valid_plan = []
                available = [a['name'] for a in registry.list_agents()]
                for step in plan:
                    if step.get("agent_name") in available:
                        valid_plan.append(step)
                    else:
                        logger.warning(f"Orchestrator planned unknown agent: {step.get('agent_name')}. Skipping step.")
                return valid_plan
            return []
        except Exception:
            logger.warning("Failed to parse plan JSON. Using fallback.")
            return []

    async def _execute_plan_steps(self, plan: List[Dict[str, Any]]) -> List[AgentResult]:
        # Sort plan into sequential and parallel batches
        batches = []
        current_batch = []
        for step in plan:
            if step.get("parallel"):
                current_batch.append(step)
            else:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                batches.append([step])
        if current_batch:
            batches.append(current_batch)

        all_results = []
        for batch in batches:
            tasks = [self._execute_single_step(step) for step in batch]
            batch_results = await asyncio.gather(*tasks)
            all_results.extend(batch_results)
        
        return all_results

    async def _execute_single_step(self, step: Dict[str, Any]) -> AgentResult:
        agent_name = step.get("agent_name")
        agent = registry.get_agent(agent_name)
        
        if not agent:
            return AgentResult(task_id="error", agent_id="none", success=False, error=f"Agent {agent_name} not found.")

        subtask = AgentTask(
            task_type="subtask",
            input_data=step.get("input_data"),
            context={"orchestrator_context": step.get("description")}
        )
        
        logger.info(f"Orchestrator calling agent: {agent_name}")
        return await agent.execute(subtask)

    def _synthesize_observation(self, results: List[AgentResult]) -> str:
        obs = []
        for r in results:
            status = "SUCCESS" if r.success else "FAILED"
            obs.append(f"Agent: {r.agent_id} | Status: {status} | Output: {str(r.output)[:500]}")
        return "\n".join(obs)

    async def _reflect(self, task: AgentTask, steps: List[ReActStep]) -> str:
        history = "\n".join([f"{s.step_type.upper()}: {s.content[:300]}" for s in steps])
        user_profile = task.context.get("user_profile", "")
        lesson_context = task.context.get("lesson_context", "")
        
        system_prompt = (
            "Critically reflect on the orchestration progress.\n"
            "Evaluate:\n"
            "1. Did the agents actually solve the problem?\n"
            "2. Is there any missing information or unresolved constraint?\n"
            "3. Does the result align with the USER PROFILE?\n\n"
            "If the task is fully complete, include 'TASK_COMPLETE'.\n"
            "If NOT, describe EXACTLY what remains to be done.\n\n"
            f"USER PROFILE: {user_profile}\n"
            f"RELEVANT LESSONS: {lesson_context}"
        )
        
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original Goal: {task.input_data}\nHistory:\n{history}"}
        ]
        resp = await router.chat(prompt)
        return resp.content

    async def _analyze_sentiment(self, text: str, chain: Optional[ReActChain] = None) -> str:
        """Detects the user's emotional tone to adapt the response."""
        prompt = (
            "Analyze the emotional tone of this message. Return ONLY ONE word "
            "from this list: [CHILL, STRESSED, CURIOUS, ANGRY, EXCITED, CONFUSED].\n\n"
            f"TEXT: {text}"
        )
        try:
            resp = await router.chat([{"role": "user", "content": prompt}])
            mood = resp.content.strip().upper()
            if mood in {"CHILL", "STRESSED", "CURIOUS", "ANGRY", "EXCITED", "CONFUSED"}:
                return mood
            return "CHILL"
        except Exception:
            return "CHILL"

    async def _generate_final_response(self, task: AgentTask, steps: List[ReActStep]) -> str:
        history = "\n".join([f"{s.step_type.upper()}: {s.content}" for s in steps])
        mood = task.context.get("current_mood", "CHILL")
        
        # 1. Personality Engine
        system_prompt = personality_engine.get_system_prompt(
            user_name=task.context.get("user_name", "User"),
            context=f"CURRENT USER MOOD: {mood}\nPROCESS HISTORY:\n{history}"
        )
        
        # 2. Advanced Generation with Self-Correction
        reasoning = await self.reasoner.think_and_answer(
            f"Generate final response for: {task.input_data}",
            max_revisions=1 # Self-correction enabled for final response
        )
        
        # 3. Personality Filter (Boilerplate removal)
        final_answer = personality_engine.filter_response(reasoning.answer)
        
        # 4. Safety Check (Constitutional AI)
        safe_answer = await self.safety.check_response(task.input_data, final_answer)
        
        # 5. POST-PROCESS: Learn from interaction
        try:
            async def llm_helper(prompt: str) -> str:
                resp = await self.reasoner.router.chat([{"role": "user", "content": prompt}])
                return resp.content

            asyncio.create_task(user_profile.update_from_interaction(
                task.input_data, 
                safe_answer, 
                llm_helper
            ))
        except Exception as e:
            logger.warning(f"Failed to trigger user profile update: {e}")
            
        return safe_answer

    async def _emit_step(self, step: ReActStep):
        """Emit step to event bus for frontend visualization."""
        await event_bus.publish_simple(
            "orchestrator_step",
            self.agent_name,
            {
                "type": step.step_type,
                "content": step.content,
                "timestamp": step.timestamp.isoformat()
            }
        )
