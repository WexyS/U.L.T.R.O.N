"""Eternal Autonomous Evolution Engine v3.0.

A high-level daemon that manages the continuous self-improvement and expansion 
of the Ultron AGI system through autonomous coding, testing, and reflection.
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from ultron.core.agent_registry import registry
from ultron.core.base_agent import AgentTask, AgentStatus
from ultron.core.event_bus import event_bus

logger = logging.getLogger("ultron.core.evolution")

class EternalEvolutionEngine:
    """The 'Brain' behind Ultron's autonomous growth."""

    def __init__(self, orchestrator=None, sleep_interval_minutes: int = 60):
        self.orchestrator = orchestrator
        self.sleep_interval_minutes = sleep_interval_minutes
        self._running = False
        self.enabled = os.getenv("ULTRON_EVOLUTION_ENABLED", "0") in ("1", "true")
        self.allow_git = os.getenv("ULTRON_EVOLUTION_ALLOW_GIT", "0") in ("1", "true")
        self.work_dir = os.getcwd()

    async def _run_git(self, args: List[str]):
        """Helper to run git commands."""
        if not self.allow_git:
            return
        cmd = ["git"] + args
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(f"Git command failed: {' '.join(cmd)} | Error: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Git error: {e}")

    async def start_loop(self):
        """Starts the autonomous evolution loop."""
        if self._running:
            return
        self._running = True
        logger.info(f"Eternal Evolution Engine v3.0 started. Interval: {self.sleep_interval_minutes}m")

        while self._running:
            try:
                if self.enabled:
                    await self.evolution_cycle()
                else:
                    logger.debug("Evolution cycle skipped (disabled).")
            except Exception as e:
                logger.error(f"Evolution cycle failed: {e}")
            
            await asyncio.sleep(self.sleep_interval_minutes * 60)

    async def evolution_cycle(self):
        """A single cycle of brainstorming, debating, and implementing improvements."""
        logger.info("[GENESIS] Starting Autonomous Evolution Cycle...")
        
        # 1. Brainstorming (Swarm Catalyst)
        catalyst = registry.get_agent("SwarmCatalyst")
        if not catalyst:
            logger.warning("[GENESIS] SwarmCatalyst not found. Skipping cycle.")
            return

        brainstorm_task = AgentTask(task_type="catalyze_evolution", input_data="system_growth")
        ideas = await catalyst.execute(brainstorm_task)
        if not (ideas.success and ideas.output):
            logger.warning("[GENESIS] Brainstorming failed or empty output.")
            return

        idea = ideas.output
        topic = idea.get('topic', 'feature_enhancement')
        branch_name = f"evolution/{topic.lower().replace(' ', '_')[:20]}_{int(datetime.now().timestamp())}"
        
        # 2. Safety: Create a new Git branch
        if self.allow_git:
            await self._run_git(["checkout", "-b", branch_name])
            logger.info(f"[GENESIS] Created evolution branch: {branch_name}")

        # 3. Architect Review
        architect = registry.get_agent("ArchitectAgent")
        if not architect:
            logger.warning("[GENESIS] ArchitectAgent not found. Skipping cycle.")
            return
            
        arch_task = AgentTask(task_type="design", input_data=topic, context=idea)
        design = await architect.execute(arch_task)
        if not design.success:
            logger.warning(f"[GENESIS] Design failed for {topic}")
            if self.allow_git: await self._run_git(["checkout", "main"])
            return

        # 4. Implementation (ReAct Orchestrator)
        orchestrator = registry.get_agent("ReActOrchestrator")
        if not orchestrator:
            logger.warning("[GENESIS] ReActOrchestrator not found. Skipping cycle.")
            return

        impl_task = AgentTask(
            task_type="implement_feature",
            input_data=f"Implement the following feature based on this design: {design.output}",
            context={"idea": idea, "design": design.output}
        )
        
        result = await orchestrator.execute(impl_task)
        
        if result.success:
            # 5. Automated Testing
            logger.info(f"[GENESIS] Feature implemented: {topic}. Running tests...")
            test_proc = await asyncio.create_subprocess_exec(
                "python", "-m", "pytest", "tests/",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, _ = await test_proc.communicate()
            
            if test_proc.returncode == 0:
                logger.info(f"[GENESIS] Evolution Success: {topic} implemented and tested.")
                if self.allow_git:
                    await self._run_git(["add", "."])
                    await self._run_git(["commit", "-m", f"feat(evolution): {topic}"])
                event_bus.publish("evolution_success", {"topic": topic, "branch": branch_name})
            else:
                logger.warning(f"[GENESIS] Evolution Failed Tests: {topic}. Rolling back.")
                if self.allow_git:
                    await self._run_git(["checkout", "."])
                    await self._run_git(["checkout", "main"])
                event_bus.publish("evolution_failure", {"topic": topic, "error": "Tests failed after implementation."})
        else:
            logger.warning(f"[GENESIS] Evolution Implementation Failed: {result.error}")
            if self.allow_git:
                await self._run_git(["checkout", "."])
                await self._run_git(["checkout", "main"])
            event_bus.publish("evolution_failure", {"topic": topic, "error": result.error})

    def stop(self):
        self._running = False
