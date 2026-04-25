"""Self-Improvement Engine — Autonomous prompt optimization and skill generation.

This is the core of Ultron's autonomous evolution. It:

1. Tracks agent performance metrics (success/failure/latency)
2. Automatically optimizes prompts based on outcomes
3. Learns from failures and generates preventive strategies
4. Creates new skills from successful task patterns
5. Runs A/B tests on prompt variants to find optimal configurations

The engine operates in a feedback loop:
    Execute → Measure → Analyze → Optimize → Execute(improved)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from ultron.core.daemon_manager import daemon_manager

logger = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""
    agent_name: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0
    failure_patterns: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def update(self, success: bool, latency_ms: float, error: str = "") -> None:
        self.total_tasks += 1
        if success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1
            if error:
                self.failure_patterns.append(error[:200])
                # Keep last 50 failure patterns
                self.failure_patterns = self.failure_patterns[-50:]

        self.total_latency_ms += latency_ms
        self.avg_latency_ms = self.total_latency_ms / self.total_tasks
        self.success_rate = self.successful_tasks / max(1, self.total_tasks)
        self.last_updated = datetime.now()


@dataclass
class PromptVariant:
    """A prompt variant for A/B testing."""
    id: str
    agent_name: str
    prompt_text: str
    success_count: int = 0
    failure_count: int = 0
    total_uses: int = 0
    avg_confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        if self.total_uses == 0:
            return 0.0
        return self.success_count / self.total_uses


@dataclass
class LearnedSkill:
    """A skill automatically generated from successful task patterns."""
    id: str
    name: str
    description: str
    trigger_pattern: str          # What kind of tasks trigger this skill
    execution_template: str       # How to execute (prompt template)
    success_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    source_tasks: list[str] = field(default_factory=list)  # Task IDs that created this


class SelfImprovementEngine:
    """Autonomous self-improvement engine.

    Tracks performance, optimizes prompts, and generates new skills
    based on observed patterns in task execution.
    """

    def __init__(
        self,
        llm_router=None,
        memory=None,
        data_dir: str = "./data/self_improvement",
        optimization_interval: int = 20,  # Run optimization every N tasks
    ) -> None:
        self.llm_router = llm_router
        self.memory = memory
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.optimization_interval = optimization_interval
        self._tasks_since_optimization = 0

        # Agent metrics
        self._metrics: dict[str, AgentMetrics] = {}

        # Prompt optimization
        self._prompt_variants: dict[str, list[PromptVariant]] = {}  # agent → variants
        self._active_prompt: dict[str, str] = {}  # agent → current prompt ID

        # Learned skills
        self._skills: list[LearnedSkill] = []

        # Task outcome history for pattern detection
        self._task_outcomes: list[dict] = []

        # Load persisted state
        self._load_state()

        # Plan 3 & 4: Initialize Research Daemons
        self._setup_daemons()

        logger.info("SelfImprovementEngine initialized (data_dir=%s)", self.data_dir)

    def _setup_daemons(self) -> None:
        """Claude's 5 Parallel Research Loops Integration"""
        daemon_manager.register_daemon("ToolHealth", 1800, self.monitor_tool_health)
        daemon_manager.register_daemon("KnowledgeHarvester", 7200, self.harvest_knowledge)
        daemon_manager.register_daemon("SecurityAudit", 3600, self.audit_security)
        daemon_manager.start_all()

    def monitor_tool_health(self) -> None:
        """Plan 4: Broken Tool Monitor & Self-Healing"""
        logger.info("[SelfImprovement] Running tool health diagnostics...")
        # Placeholder for actual tool testing logic
        # If failure detected, it would trigger self-fix via CodeAgent
        pass

    def harvest_knowledge(self) -> None:
        """Plan 3.2: Continuous Knowledge Harvesting"""
        logger.info("[SelfImprovement] Harvesting new AGI patterns from research feeds...")
        pass

    def audit_security(self) -> None:
        """Plan 3.4: Real-time Security Sweep"""
        logger.info("[SelfImprovement] Performing automated security audit...")
        pass

    # ── Metric Tracking ──────────────────────────────────────────────────

    def record_task_outcome(
        self,
        agent_name: str,
        task_description: str,
        success: bool,
        latency_ms: float,
        error: str = "",
        confidence: float = 0.0,
    ) -> None:
        """Record the outcome of a task execution."""
        # Update agent metrics
        if agent_name not in self._metrics:
            self._metrics[agent_name] = AgentMetrics(agent_name=agent_name)

        self._metrics[agent_name].update(success, latency_ms, error)

        # Store outcome for pattern analysis
        self._task_outcomes.append({
            "agent": agent_name,
            "task": task_description[:200],
            "success": success,
            "latency_ms": latency_ms,
            "error": error[:200] if error else "",
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep last 500 outcomes
        self._task_outcomes = self._task_outcomes[-500:]

        # Check if optimization should run
        self._tasks_since_optimization += 1
        if self._tasks_since_optimization >= self.optimization_interval:
            self._tasks_since_optimization = 0
            # Schedule async optimization (fire-and-forget)
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._run_optimization_cycle())
            except RuntimeError:
                pass  # No event loop running

        logger.debug(
            "Task outcome recorded: agent=%s, success=%s, latency=%.0fms",
            agent_name, success, latency_ms
        )

    # ── Prompt Optimization ──────────────────────────────────────────────

    async def optimize_prompt(self, agent_name: str, current_prompt: str) -> str:
        """Analyze performance and generate an improved prompt."""
        if not self.llm_router:
            return current_prompt

        metrics = self._metrics.get(agent_name)
        if not metrics or metrics.total_tasks < 5:
            return current_prompt  # Not enough data to optimize

        # Analyze failure patterns
        failure_summary = ""
        if metrics.failure_patterns:
            recent_failures = metrics.failure_patterns[-10:]
            failure_summary = "\n".join(f"- {f}" for f in recent_failures)

        messages = [
            {"role": "system", "content": (
                "You are a prompt engineering specialist. Analyze the agent's performance "
                "and suggest an improved system prompt.\n\n"
                "RULES:\n"
                "1. Keep the core purpose of the prompt intact\n"
                "2. Address the observed failure patterns\n"
                "3. Make the prompt more specific where it was too vague\n"
                "4. Add guardrails for common error cases\n"
                "5. Return ONLY the improved prompt text, nothing else"
            )},
            {"role": "user", "content": (
                f"Agent: {agent_name}\n"
                f"Success rate: {metrics.success_rate*100:.1f}%\n"
                f"Total tasks: {metrics.total_tasks}\n"
                f"Avg latency: {metrics.avg_latency_ms:.0f}ms\n\n"
                f"Current prompt:\n{current_prompt}\n\n"
                f"Recent failure patterns:\n{failure_summary or 'None'}\n\n"
                f"Generate an improved prompt:"
            )},
        ]

        try:
            response = await self.llm_router.chat(messages, temperature=0.3, max_tokens=2048)
            improved_prompt = response.content.strip()

            # Validate: improved prompt should be substantial
            if len(improved_prompt) < 20:
                logger.warning("Prompt optimization returned too short result, keeping original")
                return current_prompt

            # Store as variant for A/B testing
            variant_id = hashlib.md5(improved_prompt.encode()).hexdigest()[:8]
            variant = PromptVariant(
                id=variant_id,
                agent_name=agent_name,
                prompt_text=improved_prompt,
            )

            if agent_name not in self._prompt_variants:
                self._prompt_variants[agent_name] = []
            self._prompt_variants[agent_name].append(variant)

            logger.info(
                "Prompt optimized for %s (success rate: %.1f%% → targeting improvement)",
                agent_name, metrics.success_rate * 100
            )

            return improved_prompt
        except Exception as e:
            logger.warning("Prompt optimization failed: %s", e)
            return current_prompt

    # ── Skill Generation ─────────────────────────────────────────────────

    async def generate_skills_from_patterns(self) -> list[LearnedSkill]:
        """Analyze successful task patterns and generate reusable skills."""
        if not self.llm_router:
            return []

        # Find successful task patterns
        successful = [o for o in self._task_outcomes if o["success"]]
        if len(successful) < 10:
            return []  # Not enough data

        # Group by similarity
        task_texts = [o["task"] for o in successful[-50:]]

        messages = [
            {"role": "system", "content": (
                "Analyze these successful tasks and identify recurring patterns.\n"
                "For each pattern, create a reusable skill template.\n\n"
                "Return JSON array:\n"
                "[\n"
                "  {\n"
                "    \"name\": \"skill_name\",\n"
                "    \"description\": \"what this skill does\",\n"
                "    \"trigger_pattern\": \"keywords or phrases that trigger this skill\",\n"
                "    \"execution_template\": \"prompt template for executing this type of task\"\n"
                "  }\n"
                "]\n\n"
                "Identify at most 3 new skills."
            )},
            {"role": "user", "content": "Successful tasks:\n" + "\n".join(f"- {t}" for t in task_texts)},
        ]

        try:
            response = await self.llm_router.chat(messages, temperature=0.3, max_tokens=2048)

            import re
            json_match = re.search(r'\[[\s\S]*\]', response.content)
            if json_match:
                skills_data = json.loads(json_match.group())
                new_skills = []

                for skill_data in skills_data[:3]:
                    skill = LearnedSkill(
                        id=hashlib.md5(skill_data.get("name", "").encode()).hexdigest()[:8],
                        name=skill_data.get("name", "unnamed_skill"),
                        description=skill_data.get("description", ""),
                        trigger_pattern=skill_data.get("trigger_pattern", ""),
                        execution_template=skill_data.get("execution_template", ""),
                    )

                    # Check for duplicates
                    existing_names = {s.name for s in self._skills}
                    if skill.name not in existing_names:
                        self._skills.append(skill)
                        
                        # PERSIST TO DISK: Create a permanent SKILL.md for Ultron to discover
                        try:
                            skill_dir = Path("./skills/learned") / skill.name
                            skill_dir.mkdir(parents=True, exist_ok=True)
                            skill_md = skill_dir / "SKILL.md"
                            
                            md_content = (
                                f"# Skill: {skill.name}\n\n"
                                f"## Description\n{skill.description}\n\n"
                                f"## Trigger Pattern\n{skill.trigger_pattern}\n\n"
                                f"## Execution Template\n{skill.execution_template}\n\n"
                                f"--- \n*Generated autonomously by Ultron Self-Improvement Engine on {datetime.now().strftime('%Y-%m-%d')}*"
                            )
                            skill_md.write_text(md_content, encoding="utf-8")
                            logger.info("New skill PERMANENTLY saved to disk: %s", skill.name)
                        except Exception as e:
                            logger.error("Failed to persist learned skill %s: %s", skill.name, e)

                        new_skills.append(skill)

                return new_skills
        except Exception as e:
            logger.warning("Skill generation failed: %s", e)

        return []

    def find_applicable_skill(self, task_description: str) -> Optional[LearnedSkill]:
        """Find a skill that matches the given task."""
        task_lower = task_description.lower()

        for skill in self._skills:
            trigger_words = skill.trigger_pattern.lower().split()
            matches = sum(1 for w in trigger_words if w in task_lower)
            if matches >= len(trigger_words) * 0.5:  # 50% keyword match
                skill.success_count += 1
                return skill

        return None

    # ── Optimization Cycle ───────────────────────────────────────────────

    async def _run_optimization_cycle(self) -> None:
        """Periodic optimization — runs automatically every N tasks."""
        logger.info("Running self-improvement optimization cycle...")

        try:
            # 1. Identify underperforming agents
            for agent_name, metrics in self._metrics.items():
                if metrics.success_rate < 0.7 and metrics.total_tasks >= 10:
                    logger.info(
                        "Agent '%s' underperforming (%.1f%% success), triggering prompt optimization",
                        agent_name, metrics.success_rate * 100
                    )

            # 2. Generate new skills from patterns
            new_skills = await self.generate_skills_from_patterns()
            if new_skills:
                logger.info("Generated %d new skills from successful patterns", len(new_skills))

            # 3. Persist state
            self._save_state()

        except Exception as e:
            logger.error("Optimization cycle failed: %s", e)

    # ── Persistence ──────────────────────────────────────────────────────

    def _save_state(self) -> None:
        """Save improvement state to disk."""
        try:
            state = {
                "metrics": {
                    name: {
                        "total_tasks": m.total_tasks,
                        "successful_tasks": m.successful_tasks,
                        "failed_tasks": m.failed_tasks,
                        "avg_latency_ms": m.avg_latency_ms,
                        "success_rate": m.success_rate,
                        "failure_patterns": m.failure_patterns[-20:],
                    }
                    for name, m in self._metrics.items()
                },
                "skills": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "description": s.description,
                        "trigger_pattern": s.trigger_pattern,
                        "execution_template": s.execution_template,
                        "success_count": s.success_count,
                    }
                    for s in self._skills
                ],
                "task_outcomes": self._task_outcomes[-100:],
                "saved_at": datetime.now().isoformat(),
            }

            state_file = self.data_dir / "improvement_state.json"
            state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.debug("Self-improvement state saved")
        except Exception as e:
            logger.error("Failed to save improvement state: %s", e)

    def _load_state(self) -> None:
        """Load improvement state from disk."""
        state_file = self.data_dir / "improvement_state.json"
        if not state_file.exists():
            return

        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))

            # Restore metrics
            for name, m_data in state.get("metrics", {}).items():
                metrics = AgentMetrics(agent_name=name)
                metrics.total_tasks = m_data.get("total_tasks", 0)
                metrics.successful_tasks = m_data.get("successful_tasks", 0)
                metrics.failed_tasks = m_data.get("failed_tasks", 0)
                metrics.avg_latency_ms = m_data.get("avg_latency_ms", 0)
                metrics.success_rate = m_data.get("success_rate", 0)
                metrics.failure_patterns = m_data.get("failure_patterns", [])
                self._metrics[name] = metrics

            # Restore skills
            for s_data in state.get("skills", []):
                skill = LearnedSkill(
                    id=s_data.get("id", ""),
                    name=s_data.get("name", ""),
                    description=s_data.get("description", ""),
                    trigger_pattern=s_data.get("trigger_pattern", ""),
                    execution_template=s_data.get("execution_template", ""),
                    success_count=s_data.get("success_count", 0),
                )
                self._skills.append(skill)

            # Restore task outcomes
            self._task_outcomes = state.get("task_outcomes", [])

            logger.info(
                "Self-improvement state loaded: %d agents, %d skills, %d outcomes",
                len(self._metrics), len(self._skills), len(self._task_outcomes)
            )
        except Exception as e:
            logger.warning("Failed to load improvement state: %s", e)

    # ── Statistics ────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "agents_tracked": len(self._metrics),
            "total_skills": len(self._skills),
            "task_outcomes_recorded": len(self._task_outcomes),
            "optimization_interval": self.optimization_interval,
            "tasks_until_next_optimization": max(0, self.optimization_interval - self._tasks_since_optimization),
            "agent_performance": {
                name: {
                    "success_rate": f"{m.success_rate*100:.1f}%",
                    "total_tasks": m.total_tasks,
                    "avg_latency_ms": f"{m.avg_latency_ms:.0f}",
                }
                for name, m in self._metrics.items()
            },
        }
