"""ReAct Orchestrator for Ultron v3.0 — The AGI Brain."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.agent_registry import registry
from ultron.v2.core.event_bus import event_bus
from ultron.v2.core.llm_router import router
from ultron.v2.memory.user_profile_manager import manager as user_profile

logger = logging.getLogger("ultron.orchestrator")

@dataclass
class ReActStep:
    step_type: Literal["think", "plan", "act", "observe", "reflect"]
    content: str
    tool_used: Optional[str] = None
    result: Optional[Any] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ReActChain:
    steps: List[ReActStep] = field(default_factory=list)
    max_iterations: int = 8
    current_iteration: int = 0
    is_complete: bool = False

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
        prompt = [
            {"role": "system", "content": (
                "You are the ULTRON v3.0 AGI Brain. Analyze the user request and think step-by-step how to solve it.\n"
                "You have access to the following specialized agents:\n"
                f"{agents_info}\n\n"
                "Think about which agents are needed and in what order."
            )},
            {"role": "user", "content": f"Task: {task.input_data}\nContext: {task.context}"}
        ]
        resp = await router.chat(prompt)
        return resp.content

    async def _plan(self, task: AgentTask, thought: str) -> List[Dict[str, Any]]:
        agents_names = ", ".join([a['name'] for a in registry.list_agents()])
        prompt = [
            {"role": "system", "content": (
                "Based on the thought process, create an execution plan as a JSON list of subtasks.\n"
                f"Available Agents: [{agents_names}]\n\n"
                "Each subtask MUST use one of the available agents.\n"
                "Format: [{\"agent_name\": \"...\", \"description\": \"...\", \"input_data\": \"...\", \"parallel\": bool}]"
            )},
            {"role": "user", "content": f"Thought: {thought}"}
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
            "Reflect on the actions so far. Is the task complete? "
            "If yes, include 'TASK_COMPLETE'. If not, explain missing steps.\n"
            f"CONSIDER USER PROFILE: {user_profile}\n"
            f"RELEVANT LESSONS: {lesson_context}"
        )
        
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original Goal: {task.input_data}\nHistory:\n{history}"}
        ]
        resp = await router.chat(prompt)
        return resp.content

    async def _analyze_sentiment(self, text: str) -> str:
        """Detects the user's emotional tone to adapt the response."""
        prompt = (
            "Analyze the emotional tone of this message. Return ONLY ONE word "
            "from this list: [CHILL, STRESSED, CURIOUS, ANGRY, EXCITED, CONFUSED].\n\n"
            f"TEXT: {text}"
        )
        try:
            resp = await router.chat([{"role": "user", "content": prompt}])
            return resp.content.strip().upper()
        except Exception:
            return "CHILL"

    async def _generate_final_response(self, task: AgentTask, steps: List[ReActStep]) -> str:
        history = "\n".join([f"{s.step_type.upper()}: {s.content}" for s in steps])
        user_profile = task.context.get("user_profile", "")
        mood = task.context.get("current_mood", "CHILL")
        
        system_prompt = (
            "You are ULTRON, a sophisticated and loyal AGI assistant. "
            "Provide the final response based on the orchestration process.\n"
            f"ADAPT TO USER PROFILE: {user_profile}\n"
            f"CURRENT USER MOOD: {mood}\n"
            "If the user is STRESSED, be more concise and supportive. "
            "If the user is EXCITED, share their enthusiasm. "
            "If the user is ANGRY, be ultra-professional and solution-oriented."
        )
        
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Request: {task.input_data}\nProcess History:\n{history}"}
        ]
        resp = await router.chat(prompt)
        return resp.content

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
