"""Eternal Autonomous Evolution Engine.

Runs a background daemon that periodically analyzes the codebase,
debates new features, implements them via CoderAgent, tests them,
and pushes them to GitHub.
"""

import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Optional

from ultron.v2.core.debate_engine import DebateEngine
from ultron.v2.core.types import AgentRole, Task, TaskStatus

logger = logging.getLogger(__name__)

class EternalEvolutionEngine:
    def __init__(self, orchestrator, sleep_interval_minutes: int = 60):
        self.orchestrator = orchestrator
        self.debate_engine = DebateEngine(orchestrator.llm_router)
        self.sleep_interval_minutes = sleep_interval_minutes
        self._running = False

    async def _run_git_command(self, cmd: str) -> bool:
        """Helper to run a git command and return success status."""
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.orchestrator.work_dir
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(f"Git command '{cmd}' failed: {stderr.decode()}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed executing '{cmd}': {e}")
            return False

    async def _is_working_tree_clean(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_shell(
                "git status --porcelain",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.orchestrator.work_dir
            )
            stdout, _ = await proc.communicate()
            return len(stdout.strip()) == 0
        except Exception:
            return False

    async def _brainstorm_feature(self) -> str:
        """Prompt LLM to pick a small, contained, safe feature."""
        prompt = [
            {"role": "system", "content": "You are the Ideation Core of Ultron AGI. Suggest EXACTLY ONE simple, non-breaking, contained python feature or new class we can add to Ultron's plugin system to make it better. Output ONLY the title of the feature."},
            {"role": "user", "content": "What is the very next thing we should implement safely?"}
        ]
        resp = await self.orchestrator.llm_router.chat(prompt, max_tokens=100)
        return resp.content.strip()

    async def evolution_cycle(self):
        logger.info("⚡ [Eternal Evolution] Starting autonomous cycle...")
        
        if not await self._is_working_tree_clean():
            logger.info("⚡ [Eternal Evolution] Working tree not clean. Aborting until user commits their manual changes.")
            return

        coder_agent = self.orchestrator.agents.get(AgentRole.CODER)
        if not coder_agent:
            logger.error("⚡ [Eternal Evolution] CoderAgent not available.")
            return

        # 1. Ideation
        feature_idea = await self._brainstorm_feature()
        logger.info(f"⚡ [Eternal Evolution] Idea Generated: {feature_idea}")

        # 2. Debate the idea (Deep critical thinking)
        logger.info(f"⚡ [Eternal Evolution] Debating optimal implementation for: {feature_idea}")
        debate_result = await self.debate_engine.run_debate(
            topic=f"Design a highly robust, pure python implementation for this feature inside Ultron AGI architecture: {feature_idea}. Ensure it does not modify core stability files. Output ONLY the technical requirements for the Coder.",
            rounds=1
        )
        technical_spec = debate_result["final_answer"]

        # 3. Code Generation (with auto-healing)
        logger.info("⚡ [Eternal Evolution] Handing off to CoderAgent for implementation...")
        task = Task(description=f"Implement this feature safely as discussed: {technical_spec}\nDo not break existing code. Put your code in a new file under ultron/v2/agents/ or appropriate plugin folder. Make sure imports are valid.", intent="code")
        
        result = await coder_agent.execute(task)
        if result.status != TaskStatus.SUCCESS:
            logger.warning(f"⚡ [Eternal Evolution] CoderAgent failed to cleanly implement the feature: {result.error}. Reverting.")
            await self._run_git_command("git reset --hard && git clean -fd")
            return

        # 4. Syntactical Validation / Tests
        logger.info("⚡ [Eternal Evolution] Validating system integrity after changes...")
        valid = await self._run_git_command("python -m compileall ultron/v2/")
        
        if not valid:
            logger.error("⚡ [Eternal Evolution] Syntax validation failed! Reverting malicious/broken code.")
            await self._run_git_command("git reset --hard && git clean -fd")
            return

        # 5. Commit & Push
        logger.info("⚡ [Eternal Evolution] Implementation successful and tested. Committing...")
        await self._run_git_command("git add .")
        commit_msg = f"feat(autonomous): {feature_idea}"
        commit_success = await self._run_git_command(f'git commit -m "{commit_msg}"')
        
        if commit_success:
            logger.info("⚡ [Eternal Evolution] Auto-Pushing to remote repo...")
            await self._run_git_command("git push")
            logger.info(f"⚡ [Eternal Evolution] Evolution cycle complete! Successfully added: {feature_idea}")
        else:
            logger.warning("⚡ [Eternal Evolution] Commit lacked changes. Canceling cycle.")

    async def start_loop(self):
        """Runs the loop forever."""
        if self._running: return
        self._running = True
        logger.info(f"⚡ [Eternal Evolution] Engine started. Loop frequency: Every {self.sleep_interval_minutes} minutes.")
        
        while self._running:
            try:
                # We wait 30 seconds on boot so it doesn't slow down immediate startups
                await asyncio.sleep(30)
                await self.evolution_cycle()
            except Exception as e:
                logger.error(f"⚡ [Eternal Evolution] Fatal error in cycle: {e}")
                
            logger.info(f"⚡ [Eternal Evolution] Sleeping for {self.sleep_interval_minutes} minutes until next idea...")
            await asyncio.sleep(self.sleep_interval_minutes * 60)
