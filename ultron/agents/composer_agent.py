"""Composer Agent — Cursor-like multi-file code generation & editing.

Capabilities:
- Generate/edit multiple files from a single prompt
- Project-aware context: scan workspace, understand file relationships
- Diff-based editing: produce unified diffs before applying changes
- Iterative refinement: user can request changes
- Auto-apply with rollback support via Git
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ultron.agents.base import Agent
from ultron.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class FileChange:
    """Represents a single file change."""
    def __init__(self, path: str, action: str, content: str = "", original: str = ""):
        self.path = path
        self.action = action  # "create", "modify", "delete"
        self.content = content  # new content
        self.original = original  # original content (for diff/rollback)
        self.applied = False

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "action": self.action,
            "content": self.content,
            "original": self.original,
            "applied": self.applied,
        }

    def diff(self) -> str:
        """Generate a unified diff string."""
        if self.action == "create":
            lines = self.content.splitlines()
            return f"--- /dev/null\n+++ {self.path}\n" + "\n".join(f"+{l}" for l in lines)
        elif self.action == "delete":
            lines = self.original.splitlines()
            return f"--- {self.path}\n+++ /dev/null\n" + "\n".join(f"-{l}" for l in lines)
        elif self.action == "modify":
            import difflib
            orig_lines = self.original.splitlines(keepends=True)
            new_lines = self.content.splitlines(keepends=True)
            diff = difflib.unified_diff(orig_lines, new_lines, fromfile=f"a/{self.path}", tofile=f"b/{self.path}")
            return "".join(diff)
        return ""


class ComposerSession:
    """Tracks a composer session with pending changes."""
    def __init__(self, session_id: str, prompt: str, workspace: str):
        self.session_id = session_id
        self.prompt = prompt
        self.workspace = workspace
        self.changes: list[FileChange] = []
        self.created_at = datetime.now()
        self.status = "pending"  # pending, applied, rolled_back

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "prompt": self.prompt,
            "workspace": self.workspace,
            "changes": [c.to_dict() for c in self.changes],
            "created_at": self.created_at.isoformat(),
            "status": self.status,
        }


class ComposerAgent(Agent):
    agent_name = "ComposerAgent"
    agent_description = "Multi-file code generation agent with diff-based editing and rollback."

    """Multi-file code generation agent with diff-based editing and rollback."""

    role = "composer"

    def __init__(
        self,
        llm_router=None,
        event_bus=None,
        blackboard=None,
        workspace_dir: str = "./workspace",
    ):
        super().__init__(
            role=self.role,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
            system_prompt=self._default_system_prompt(),
        )
        self.workspace_dir = Path(workspace_dir)
        self._sessions: dict[str, ComposerSession] = {}
        self._backup_dir = Path("data/composer_backups")
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def _default_system_prompt(self) -> str:
        return (
            "You are an expert code composer. Given a user prompt and project context, "
            "you generate precise, production-quality code changes across multiple files.\n\n"
            "RULES:\n"
            "1. Output ONLY valid JSON with the exact schema specified\n"
            "2. Each file change must have: path, action (create/modify/delete), content\n"
            "3. For modifications, output the COMPLETE new file content, not just diffs\n"
            "4. Use proper indentation and coding standards\n"
            "5. Maintain existing code style and conventions\n"
            "6. Add helpful comments for complex logic\n"
            "7. Never break existing functionality unless explicitly asked"
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute a composer task."""
        self.state.status = AgentStatus.BUSY
        try:
            return await self._generate_changes(task)
        except Exception as e:
            logger.exception("Composer agent failed")
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(e),
            )
        finally:
            self.state.status = AgentStatus.IDLE

    async def _subscribe_events(self) -> None:
        """Subscribe to relevant events on the event bus."""
        # Composer is mostly invoked directly via API or specific orchestrator tasks,
        # but we must implement this abstract method.
        pass

    async def generate(self, prompt: str, workspace: str = "", context_files: list[str] | None = None) -> ComposerSession:
        """Generate code changes from a prompt."""
        import uuid
        session_id = f"composer_{uuid.uuid4().hex[:8]}"
        workspace = workspace or str(self.workspace_dir)

        session = ComposerSession(session_id, prompt, workspace)

        # Gather project context
        project_context = self._scan_project(workspace, context_files)

        # Generate changes via LLM
        changes = await self._llm_generate(prompt, project_context, workspace)
        session.changes = changes

        self._sessions[session_id] = session
        return session

    def _scan_project(self, workspace: str, context_files: list[str] | None = None) -> str:
        """Scan workspace to build project context."""
        ws = Path(workspace)
        if not ws.exists():
            return "Workspace does not exist."

        parts = []

        # Build file tree (limit depth and count)
        parts.append("## Project Structure\n```")
        file_count = 0
        max_files = 200
        skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".cache"}
        skip_exts = {".pyc", ".pyo", ".exe", ".dll", ".so", ".o", ".a", ".class", ".jar", ".whl"}

        for root, dirs, files in os.walk(ws):
            # Skip hidden/large directories
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            rel_root = os.path.relpath(root, ws)
            depth = rel_root.count(os.sep) if rel_root != "." else 0
            if depth > 4:
                continue

            indent = "  " * depth
            dirname = os.path.basename(root)
            if rel_root != ".":
                parts.append(f"{indent}{dirname}/")

            for f in sorted(files)[:30]:  # max 30 files per dir
                ext = Path(f).suffix.lower()
                if ext in skip_exts:
                    continue
                file_count += 1
                if file_count > max_files:
                    parts.append(f"{indent}  ... (truncated)")
                    break
                parts.append(f"{indent}  {f}")
            if file_count > max_files:
                break

        parts.append("```\n")

        # Read specific context files
        if context_files:
            parts.append("## Context Files\n")
            for filepath in context_files[:10]:  # max 10 context files
                full_path = Path(filepath) if Path(filepath).is_absolute() else ws / filepath
                if full_path.exists() and full_path.is_file():
                    try:
                        content = full_path.read_text(encoding="utf-8", errors="replace")
                        if len(content) > 8000:
                            content = content[:8000] + "\n... (truncated)"
                        rel = os.path.relpath(full_path, ws)
                        parts.append(f"### {rel}\n```\n{content}\n```\n")
                    except Exception:
                        pass

        # Auto-detect key config files
        key_files = ["package.json", "pyproject.toml", "requirements.txt", "tsconfig.json",
                     "Cargo.toml", "go.mod", "Makefile", "README.md"]
        for kf in key_files:
            kf_path = ws / kf
            if kf_path.exists() and kf not in (context_files or []):
                try:
                    content = kf_path.read_text(encoding="utf-8", errors="replace")[:2000]
                    parts.append(f"### {kf}\n```\n{content}\n```\n")
                except Exception:
                    pass

        return "\n".join(parts)

    async def _llm_generate(self, prompt: str, project_context: str, workspace: str) -> list[FileChange]:
        """Use LLM to generate file changes."""
        if not self.llm_router:
            raise RuntimeError("LLM router not available")

        system_msg = (
            self._default_system_prompt() + "\n\n"
            f"WORKSPACE: {workspace}\n\n"
            f"PROJECT CONTEXT:\n{project_context}\n\n"
            "OUTPUT FORMAT: Respond with a JSON array of file changes:\n"
            '[\n'
            '  {"path": "relative/file/path.py", "action": "create|modify|delete", "content": "full file content here"},\n'
            '  ...\n'
            ']\n\n'
            'IMPORTANT: For "modify" actions, provide the COMPLETE new file content. '
            'For "create" actions, provide the full file content. '
            'For "delete" actions, content can be empty.\n'
            'Return ONLY the JSON array, no markdown fences, no explanation.'
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        response = await self.llm_router.chat(messages, max_tokens=8192, temperature=0.2)

        # Parse JSON response
        content = response.content.strip()
        # Remove markdown code fences if present
        content = re.sub(r'^```(?:json)?\s*\n?', '', content)
        content = re.sub(r'\n?```\s*$', '', content)

        try:
            changes_data = json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            match = re.search(r'\[[\s\S]*\]', content)
            if match:
                changes_data = json.loads(match.group())
            else:
                raise ValueError(f"Failed to parse LLM response as JSON: {content[:200]}")

        changes = []
        ws = Path(workspace)
        for item in changes_data:
            path = item.get("path", "")
            action = item.get("action", "create")
            new_content = item.get("content", "")

            # Read original content for modify/delete
            original = ""
            full_path = ws / path
            if full_path.exists() and action in ("modify", "delete"):
                try:
                    original = full_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

            changes.append(FileChange(
                path=path,
                action=action,
                content=new_content,
                original=original,
            ))

        return changes

    async def apply_changes(self, session_id: str) -> dict:
        """Apply all pending changes from a session."""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}

        ws = Path(session.workspace)
        applied = []
        errors = []

        # Create backup
        backup_id = f"{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = self._backup_dir / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        for change in session.changes:
            full_path = ws / change.path
            try:
                # Backup original
                if full_path.exists():
                    backup_file = backup_dir / change.path
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(full_path, backup_file)

                if change.action == "create":
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(change.content, encoding="utf-8")
                    change.applied = True
                    applied.append(change.path)

                elif change.action == "modify":
                    full_path.write_text(change.content, encoding="utf-8")
                    change.applied = True
                    applied.append(change.path)

                elif change.action == "delete":
                    if full_path.exists():
                        full_path.unlink()
                    change.applied = True
                    applied.append(change.path)

            except Exception as e:
                errors.append({"path": change.path, "error": str(e)})

        session.status = "applied"

        return {
            "session_id": session_id,
            "applied": applied,
            "errors": errors,
            "backup_id": backup_id,
        }

    async def rollback(self, session_id: str) -> dict:
        """Rollback changes from a session."""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}

        ws = Path(session.workspace)
        rolled_back = []

        for change in session.changes:
            if not change.applied:
                continue
            full_path = ws / change.path
            try:
                if change.action == "create":
                    if full_path.exists():
                        full_path.unlink()
                elif change.action in ("modify", "delete"):
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(change.original, encoding="utf-8")
                change.applied = False
                rolled_back.append(change.path)
            except Exception as e:
                logger.error("Rollback failed for %s: %s", change.path, e)

        session.status = "rolled_back"
        return {"rolled_back": rolled_back}

    def get_session(self, session_id: str) -> Optional[ComposerSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[dict]:
        """List all sessions."""
        return [s.to_dict() for s in self._sessions.values()]

    def get_workspace_context(self, workspace: str = "", context_files: list[str] | None = None) -> str:
        """Get workspace context for frontend display."""
        workspace = workspace or str(self.workspace_dir)
        return self._scan_project(workspace, context_files)

    async def _generate_changes(self, task: Task) -> TaskResult:
        """Handle a composer task from the orchestrator."""
        prompt = task.input_data
        workspace = task.context.get("workspace", str(self.workspace_dir))
        context_files = task.context.get("context_files", [])

        session = await self.generate(prompt, workspace, context_files)

        diffs = []
        for change in session.changes:
            diffs.append(f"### {change.action.upper()}: {change.path}\n```diff\n{change.diff()}\n```")

        return TaskResult(
            task_id=task.task_id,
            status=TaskStatus.SUCCESS,
            output="\n\n".join(diffs) if diffs else "No changes generated.",
            metadata={
                "session_id": session.session_id,
                "changes_count": len(session.changes),
                "changes": [c.to_dict() for c in session.changes],
            },
        )
