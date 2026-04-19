"""Goal-Oriented Planner — Hierarchical task decomposition and execution.

The planner transforms high-level goals into executable step sequences:

    Goal: "Deploy a FastAPI app to production"
    ├── SubGoal 1: "Prepare the application"
    │   ├── Step 1.1: "Write Dockerfile"
    │   ├── Step 1.2: "Create requirements.txt"
    │   └── Step 1.3: "Add health check endpoint"
    ├── SubGoal 2: "Set up infrastructure"
    │   ├── Step 2.1: "Provision server"
    │   └── Step 2.2: "Configure DNS"
    └── SubGoal 3: "Deploy and verify"
        ├── Step 3.1: "Build and push Docker image"
        ├── Step 3.2: "Deploy to server"
        └── Step 3.3: "Run smoke tests"

Features:
 - Goal → Sub-goals → Steps decomposition
 - Dependency graph between steps
 - Parallel step detection
 - Plan revision on failure
 - Progress tracking
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """An atomic step in a plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    agent: str = ""                # Which agent should execute this
    depends_on: list[str] = field(default_factory=list)  # Step IDs this depends on
    status: StepStatus = StepStatus.PENDING
    result: str = ""
    error: str = ""
    estimated_effort: str = "low"  # low, medium, high
    order: int = 0
    can_parallelize: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class SubGoal:
    """A sub-goal containing multiple steps."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    steps: list[PlanStep] = field(default_factory=list)
    priority: int = 0  # Higher = more important
    status: StepStatus = StepStatus.PENDING


@dataclass
class ExecutionPlan:
    """Complete execution plan for a goal."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    goal: str = ""
    sub_goals: list[SubGoal] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    status: StepStatus = StepStatus.PENDING
    revision: int = 0  # How many times the plan was revised
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        return sum(len(sg.steps) for sg in self.sub_goals)

    @property
    def completed_steps(self) -> int:
        return sum(
            1 for sg in self.sub_goals
            for s in sg.steps
            if s.status == StepStatus.COMPLETED
        )

    @property
    def progress(self) -> float:
        total = self.total_steps
        if total == 0:
            return 0.0
        return self.completed_steps / total

    def get_next_executable_steps(self) -> list[PlanStep]:
        """Get steps whose dependencies are satisfied and can be executed now."""
        completed_ids = {
            s.id for sg in self.sub_goals for s in sg.steps
            if s.status == StepStatus.COMPLETED
        }

        executable = []
        for sg in self.sub_goals:
            for step in sg.steps:
                if step.status != StepStatus.PENDING:
                    continue
                # Check all dependencies are met
                if all(dep in completed_ids for dep in step.depends_on):
                    executable.append(step)

        return executable

    def get_parallelizable_groups(self) -> list[list[PlanStep]]:
        """Get groups of steps that can run in parallel."""
        executable = self.get_next_executable_steps()
        parallel = [s for s in executable if s.can_parallelize]
        sequential = [s for s in executable if not s.can_parallelize]

        groups = []
        if parallel:
            groups.append(parallel)
        for s in sequential:
            groups.append([s])

        return groups

    def to_readable(self) -> str:
        """Human-readable representation of the plan."""
        lines = [f"📋 Plan: {self.goal}", f"   Progress: {self.progress*100:.0f}%\n"]

        for i, sg in enumerate(self.sub_goals, 1):
            status_icon = {
                StepStatus.PENDING: "⏳",
                StepStatus.RUNNING: "🔄",
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
            }
            lines.append(f"  {status_icon.get(sg.status, '?')} Sub-goal {i}: {sg.description}")

            for step in sg.steps:
                icon = status_icon.get(step.status, "?")
                dep_str = f" (depends on: {', '.join(step.depends_on)})" if step.depends_on else ""
                parallel = " ⚡" if step.can_parallelize else ""
                lines.append(f"    {icon} {step.description}{dep_str}{parallel}")

        return "\n".join(lines)


class Planner:
    """Goal-oriented hierarchical planner.

    Transforms high-level goals into structured execution plans
    with dependency tracking and parallel execution support.
    """

    def __init__(self, llm_router, memory=None) -> None:
        self.llm_router = llm_router
        self.memory = memory
        self._active_plans: dict[str, ExecutionPlan] = {}
        self._plan_history: list[ExecutionPlan] = []

    # ── Plan Creation ────────────────────────────────────────────────────

    async def create_plan(
        self,
        goal: str,
        context: Optional[dict] = None,
        max_sub_goals: int = 5,
        max_steps_per_goal: int = 6,
    ) -> ExecutionPlan:
        """Create an execution plan for a goal."""
        logger.info("Creating plan for goal: %s", goal[:80])

        # Use LLM to decompose the goal
        plan_prompt = (
            "You are a planning specialist. Decompose this goal into a structured execution plan.\n\n"
            f"Goal: {goal}\n\n"
            "Return a JSON object with this structure:\n"
            "{\n"
            "  \"sub_goals\": [\n"
            "    {\n"
            "      \"description\": \"sub-goal description\",\n"
            "      \"priority\": 1,\n"
            "      \"steps\": [\n"
            "        {\n"
            "          \"description\": \"step description\",\n"
            "          \"agent\": \"coder|researcher|rpa_operator|orchestrator\",\n"
            "          \"depends_on\": [],\n"
            "          \"effort\": \"low|medium|high\",\n"
            "          \"can_parallelize\": true|false\n"
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"RULES:\n"
            f"- Maximum {max_sub_goals} sub-goals\n"
            f"- Maximum {max_steps_per_goal} steps per sub-goal\n"
            f"- Steps should be atomic and actionable\n"
            f"- Use depends_on to reference step indices (e.g., [\"step_0_0\"] = sub-goal 0, step 0)\n"
            f"- Mark steps as can_parallelize=true if they have no mutual dependencies\n"
            f"- Assign the correct agent for each step type"
        )

        messages = [
            {"role": "system", "content": plan_prompt},
            {"role": "user", "content": goal},
        ]

        try:
            response = await self.llm_router.chat(messages, temperature=0.2, max_tokens=4096)
            plan_data = self._parse_plan_json(response.content)
        except Exception as e:
            logger.warning("Plan generation failed: %s", e)
            # Fallback: create a simple single-step plan
            plan_data = {
                "sub_goals": [{
                    "description": goal,
                    "priority": 1,
                    "steps": [{"description": goal, "agent": "orchestrator", "effort": "medium"}]
                }]
            }

        # Build ExecutionPlan
        plan = ExecutionPlan(goal=goal)

        for sg_idx, sg_data in enumerate(plan_data.get("sub_goals", [])[:max_sub_goals]):
            sub_goal = SubGoal(
                description=sg_data.get("description", f"Sub-goal {sg_idx + 1}"),
                priority=sg_data.get("priority", sg_idx),
            )

            for step_idx, step_data in enumerate(sg_data.get("steps", [])[:max_steps_per_goal]):
                step = PlanStep(
                    id=f"step_{sg_idx}_{step_idx}",
                    description=step_data.get("description", ""),
                    agent=step_data.get("agent", "orchestrator"),
                    depends_on=step_data.get("depends_on", []),
                    estimated_effort=step_data.get("effort", "medium"),
                    can_parallelize=step_data.get("can_parallelize", False),
                    order=step_idx,
                )
                sub_goal.steps.append(step)

            plan.sub_goals.append(sub_goal)

        self._active_plans[plan.id] = plan
        logger.info("Plan created: %s (%d sub-goals, %d total steps)",
                    plan.id, len(plan.sub_goals), plan.total_steps)

        return plan

    # ── Plan Execution ───────────────────────────────────────────────────

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        orchestrator=None,
        *,
        process_depth: int = 0,
    ) -> ExecutionPlan:
        """Execute a plan step by step, respecting dependencies.

        process_depth: orchestrator.process için _depth tabanı (sonsuz görev önleme).
        """
        plan.status = StepStatus.RUNNING

        while True:
            executable = plan.get_next_executable_steps()
            if not executable:
                # Check if all done or stuck
                all_completed = all(
                    s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
                    for sg in plan.sub_goals for s in sg.steps
                )
                if all_completed:
                    plan.status = StepStatus.COMPLETED
                    logger.info("Plan completed: %s (%.0f%% progress)", plan.id, plan.progress * 100)
                else:
                    plan.status = StepStatus.FAILED
                    logger.error("Plan stuck — dependencies cannot be resolved: %s", plan.id)
                break

            # Execute steps (parallel groups handled here)
            for step in executable:
                step.status = StepStatus.RUNNING
                step.started_at = datetime.now()

                try:
                    if orchestrator:
                        result = await orchestrator.process(
                            step.description,
                            _depth=process_depth + 1,
                        )
                        step.result = str(result)[:1000]
                        step.status = StepStatus.COMPLETED
                    else:
                        # Without orchestrator, mark as completed with a note
                        step.result = "Executed (no orchestrator attached)"
                        step.status = StepStatus.COMPLETED
                except Exception as e:
                    step.error = str(e)
                    step.status = StepStatus.FAILED
                    logger.error("Step failed: %s — %s", step.description, e)

                    # Try to revise the plan
                    plan = await self.revise_plan(plan, step)

                step.completed_at = datetime.now()

            # Update sub-goal statuses
            for sg in plan.sub_goals:
                if all(s.status == StepStatus.COMPLETED for s in sg.steps):
                    sg.status = StepStatus.COMPLETED
                elif any(s.status == StepStatus.FAILED for s in sg.steps):
                    sg.status = StepStatus.FAILED
                elif any(s.status == StepStatus.RUNNING for s in sg.steps):
                    sg.status = StepStatus.RUNNING

        self._plan_history.append(plan)
        return plan

    # ── Plan Revision ────────────────────────────────────────────────────

    async def revise_plan(self, plan: ExecutionPlan, failed_step: PlanStep) -> ExecutionPlan:
        """Revise a plan when a step fails."""
        plan.revision += 1

        if plan.revision > 3:
            logger.warning("Max plan revisions reached for plan %s", plan.id)
            return plan

        messages = [
            {"role": "system", "content": (
                "A step in the execution plan has failed. Suggest a revised approach.\n"
                "Options:\n"
                "1. Retry the step with different parameters\n"
                "2. Skip the step and adjust downstream steps\n"
                "3. Add alternative steps\n\n"
                "Return JSON: {\"action\": \"retry|skip|alternative\", \"reason\": \"...\", "
                "\"alternative_step\": {\"description\": \"...\", \"agent\": \"...\"}}"
            )},
            {"role": "user", "content": (
                f"Plan: {plan.goal}\n"
                f"Failed step: {failed_step.description}\n"
                f"Error: {failed_step.error}\n"
                f"Revision #{plan.revision}"
            )},
        ]

        try:
            response = await self.llm_router.chat(messages, temperature=0.2, max_tokens=512)
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if json_match:
                revision = json.loads(json_match.group())
                action = revision.get("action", "skip")

                if action == "skip":
                    failed_step.status = StepStatus.SKIPPED
                    logger.info("Step skipped by planner: %s", failed_step.description)
                elif action == "retry":
                    failed_step.status = StepStatus.PENDING
                    failed_step.error = ""
                    logger.info("Step will be retried: %s", failed_step.description)
                elif action == "alternative":
                    alt_data = revision.get("alternative_step", {})
                    if alt_data:
                        alt_step = PlanStep(
                            description=alt_data.get("description", failed_step.description),
                            agent=alt_data.get("agent", failed_step.agent),
                            depends_on=failed_step.depends_on,
                            order=failed_step.order + 1,
                        )
                        # Find the sub-goal and add alternative step
                        for sg in plan.sub_goals:
                            if failed_step in sg.steps:
                                failed_step.status = StepStatus.SKIPPED
                                sg.steps.append(alt_step)
                                logger.info("Alternative step added: %s", alt_step.description)
                                break
        except Exception as e:
            logger.warning("Plan revision failed: %s", e)

        return plan

    # ── Helpers ───────────────────────────────────────────────────────────

    def _parse_plan_json(self, content: str) -> dict:
        """Extract plan JSON from LLM response."""
        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback
        return {"sub_goals": [{"description": "Execute task", "steps": [{"description": content[:200]}]}]}

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        return self._active_plans.get(plan_id)

    def get_stats(self) -> dict:
        return {
            "active_plans": len(self._active_plans),
            "completed_plans": len(self._plan_history),
            "total_plans": len(self._active_plans) + len(self._plan_history),
        }
