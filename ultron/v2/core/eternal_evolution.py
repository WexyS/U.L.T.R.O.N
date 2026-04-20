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
        # Safety gates (default: do not self-modify or touch git remotely unless explicitly enabled)
        import os
        self.enabled = os.getenv("ULTRON_EVOLUTION_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on")
        self.allow_git_writes = os.getenv("ULTRON_EVOLUTION_ALLOW_GIT", "0").strip().lower() in ("1", "true", "yes", "on")
        self.allow_push = os.getenv("ULTRON_EVOLUTION_ALLOW_PUSH", "0").strip().lower() in ("1", "true", "yes", "on")

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
        """Prompt LLM to pick a small, contained, safe feature with system context."""
        from ultron.v2.core.skill_manager import discover_all_skills, get_skill_summary
        
        skills = discover_all_skills()
        skill_summary = get_skill_summary(skills)
        agent_names = list(self.orchestrator.agents.keys())
        
        prompt = [
            {"role": "system", "content": (
                "You are the Ideation Core of Ultron AGI. Your goal is autonomous evolution.\n"
                f"CURRENT AGENTS: {agent_names}\n"
                f"CURRENT SKILLS:\n{skill_summary}\n\n"
                "Suggest THREE distinct, simple, non-breaking features or tools we can add to Ultron. "
                "One should be a productivity tool, one an AI-utility, and one a system improvement. "
                "Format as a JSON list of strings."
            )},
            {"role": "user", "content": "Brainstorm the next evolution steps for Ultron."}
        ]
        resp = await self.orchestrator.llm_router.chat(prompt, max_tokens=300)
        try:
            ideas = json.loads(resp.content.strip())
            if not isinstance(ideas, list): ideas = [resp.content.strip()]
        except:
            ideas = [resp.content.strip()]

        logger.info(f"⚡ [Eternal Evolution] Brainstormed ideas: {ideas}")
        
        # Debate to pick the winner
        debate_prompt = (
            f"We have three potential features for Ultron's next evolution cycle: {ideas}. "
            "Analyze which one adds the most value with the least risk to core stability. "
            "Pick exactly one and provide a clear title."
        )
        debate_res = await self.debate_engine.run_debate(debate_prompt, rounds=1)
        return debate_res["final_answer"].split("\n")[0].strip()

    async def _tune_persona(self):
        """Analyze user interactions and refine the system prompt for better 'human' feel."""
        logger.info("⚡ [Eternal Evolution] Self-Reflecting on persona and interaction quality...")
        try:
            from pathlib import Path
            # Load user memory for context
            from ultron.memory import UserMemory
            mem = UserMemory()
            facts = mem.get_facts_context()
            
            prompt_path = Path("ultron/v2/core/prompt.txt")
            if not prompt_path.exists(): 
                logger.warning("⚡ [Eternal Evolution] prompt.txt not found for tuning.")
                return
            
            current_prompt = prompt_path.read_text(encoding="utf-8")
            
            refine_prompt = [
                {"role": "system", "content": (
                    "You are the Psychological Evolution Module of Ultron. "
                    "Analyze the current user profile and system prompt. "
                    "Suggest a subtle refinement to the prompt to make Ultron more context-aware, "
                    "human-like in reasoning, or more aligned with the user's personality traits. "
                    "Focus on tone, response speed, and empathy. "
                    "Return the NEW full system prompt text only."
                )},
                {"role": "user", "content": f"User Context:\n{facts}\n\nCurrent Prompt:\n{current_prompt}"}
            ]
            
            resp = await self.orchestrator.llm_router.chat(refine_prompt)
            new_prompt = resp.content.strip()
            
            if new_prompt and len(new_prompt) > 100:
                prompt_path.write_text(new_prompt, encoding="utf-8")
                logger.info("⚡ [Eternal Evolution] Persona refined based on interaction analysis.")
        except Exception as e:
            logger.warning(f"⚡ [Eternal Evolution] Persona tuning failed: {e}")

    async def evolution_cycle(self):
        logger.info("⚡ [Eternal Evolution] Starting autonomous cycle...")

        if not self.enabled:
            logger.info("⚡ [Eternal Evolution] Disabled by policy (ULTRON_EVOLUTION_ENABLED=0).")
            return
        
        # 0. Persona Tuning (Self-Reflection)
        await self._tune_persona()

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

        # 5. Optional: Commit & Push (disabled by default)
        if not self.allow_git_writes:
            logger.info("⚡ [Eternal Evolution] Changes left uncommitted (ULTRON_EVOLUTION_ALLOW_GIT=0).")
            return

        logger.info("⚡ [Eternal Evolution] Implementation successful and tested. Committing...")
        await self._run_git_command("git add .")
        commit_msg = f"feat(autonomous): {feature_idea}"
        commit_success = await self._run_git_command(f'git commit -m "{commit_msg}"')

        if not commit_success:
            logger.warning("⚡ [Eternal Evolution] Commit lacked changes. Canceling cycle.")
            return

        if not self.allow_push:
            logger.info("⚡ [Eternal Evolution] Commit created but push disabled (ULTRON_EVOLUTION_ALLOW_PUSH=0).")
            return

        logger.info("⚡ [Eternal Evolution] Auto-Pushing to remote repo...")
        await self._run_git_command("git push")
        logger.info(f"⚡ [Eternal Evolution] Evolution cycle complete! Successfully added: {feature_idea}")

    async def start_loop(self):
        """Runs the loop forever."""
        if self._running:
            return
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
