"""Coder Agent — autonomous code generation, execution, and self-healing."""

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class CoderAgent(Agent):
    """Autonomous software engineer agent.

    Capabilities:
    - Generate code from natural language
    - Execute code in a controlled environment
    - Read stack traces and auto-fix bugs
    - Iterate until the code works (self-healing loop)
    - Review code for quality and security
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
        work_dir: str = "./workspace",
        max_heal_iterations: int = 5,
        allow_execution: bool = True,
    ) -> None:
        super().__init__(
            role=AgentRole.CODER,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
        )
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.max_heal_iterations = max_heal_iterations
        self.allow_execution = allow_execution

    def _default_system_prompt(self) -> str:
        return (
            "You are an Elite Software Architect and Senior Engineer.\n"
            "You can generate single files or complete project structures.\n"
            "RULES:\n"
            "- If building a project, provide the structure first, then the code for each file.\n"
            "- Output ONLY code or structured project data.\n"
            "- When in ARCHITECT mode, you can use advanced system commands for building and testing.\n"
            "- Include print statements or logging for visibility.\n"
        )

    async def _subscribe_events(self) -> None:
        async def on_code_request(event) -> None:
            if not self._running:
                return
            task_data = event.data
            task = Task(
                id=event.data.get("task_id"),
                description=event.data.get("description", ""),
                context=event.data.get("context", {}),
            )
            result = await self.execute(task)
            await self._publish_event("code_result", {
                "task_id": task.id,
                "output": result.output,
                "error": result.error,
                "success": result.status == TaskStatus.SUCCESS,
            })

        self.event_bus.subscribe("code_request", on_code_request)
        self.event_bus.subscribe("code_fix_request", on_code_request)

    async def execute(self, task: Task) -> TaskResult:
        """Execute a coding task with self-healing loop."""
        self.state.status = AgentStatus.BUSY
        self.state.current_task = task.id

        try:
            # Step 1: Check if project generation is requested
            is_project = task.context.get("project_mode", False)
            if is_project:
                return await self._generate_project(task)

            # Step 2: Generate code
            code = await self._generate_code(task)
            if not code:
                return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error="No code generated")

            # Step 3: Execute code (if requested and allowed)
            should_execute = task.context.get("execute", False)
            if should_execute and self.allow_execution:
                result = await self._self_healing_loop(code, task, max_iterations=self.max_heal_iterations)
                return result
            else:
                # Just return the code
                return TaskResult(task_id=task.id, status=TaskStatus.SUCCESS, output=code)
        finally:
            self.state.status = AgentStatus.IDLE
            self.state.current_task = None

    async def _generate_code(self, task: Task) -> str:
        """Generate code from task description."""
        language = task.context.get("language", "python")
        messages = self._build_messages(
            f"Task: {task.description}\n"
            f"Write ONLY the complete, runnable {language} code. "
            f"Output must be directly executable — no explanations, no markdown, no JSON."
        )

        response = await self._llm_chat(messages)
        # Clean up markdown code blocks if present
        code = response.content
        if "```" in code:
            # Extract code from markdown fences
            parts = code.split("```")
            for part in parts:
                part = part.strip()
                if part and not part.startswith(("python", "py", "javascript", "js", "ts", "typescript")):
                    code = part
                    break
                # If starts with language name, strip first line
                lines = part.split("\n", 1)
                if len(lines) > 1:
                    code = lines[1]
                    break

        # Detect JSON tool-call hallucination and retry
        code = code.strip()
        if code.startswith("{"):
            try:
                data = json.loads(code)
                if "name" in data:
                    logger.warning("LLM returned tool call instead of code, retrying...")
                    messages.append({"role": "user", "content": (
                        f"STOP. You returned JSON. Write RAW {language} SOURCE CODE ONLY. "
                        f"No JSON, no function calls, no explanations. Just the code."
                    )})
                    response2 = await self._llm_chat(messages)
                    code = response2.content
                    if "```" in code:
                        parts = code.split("```")
                        for part in parts:
                            part = part.strip()
                            if part and not part.startswith(("python", "py", "javascript")):
                                code = part
                                break
                    # Second check - still JSON?
                    code = code.strip()
                    if code.startswith("{"):
                        try:
                            json.loads(code)
                            code = "# ERROR: LLM refused to generate code after retry\n# Task: " + task.description
                        except json.JSONDecodeError:
                            pass
            except json.JSONDecodeError:
                pass

        # Save to workspace
        filename = task.context.get("filename", f"task_{task.id[:8]}.{self._ext_for_language(language)}")
        filepath = self.work_dir / filename
        filepath.write_text(code, encoding="utf-8")

        await self.store_context(f"code_{task.id}", {"code": code, "filepath": str(filepath)})
        logger.info("Generated code for task %s → %s", task.id, filepath)
        return code

    async def _self_healing_loop(
        self,
        code: str,
        task: Task,
        max_iterations: int = 5,
    ) -> TaskResult:
        """Execute code, catch errors, auto-fix, repeat until success."""
        self.state.metadata["heal_iteration"] = 0

        for iteration in range(max_iterations):
            self.state.metadata["heal_iteration"] = iteration + 1

            # Execute
            success, output, error = await self._execute_code(code, task)

            if success:
                await self._publish_event("code_fixed", {
                    "task_id": task.id,
                    "iterations": iteration + 1,
                    "output": output,
                })
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    output=output,
                    metadata={"heal_iterations": iteration + 1},
                )

            # Auto-fix
            if iteration < max_iterations - 1:
                logger.info(
                    "Code error (iteration %d/%d), auto-fixing: %s",
                    iteration + 1,
                    max_iterations,
                    error[:200],
                )
                code = await self._fix_code(code, task.description, error)
                await self._publish_event("code_fix_attempt", {
                    "task_id": task.id,
                    "iteration": iteration + 1,
                    "error": error[:500],
                })

        # Exhausted all iterations
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.FAILED,
            output=output,
            error=f"Failed after {max_iterations} self-healing iterations. Last error: {error}",
            metadata={"heal_iterations": max_iterations},
        )

    async def _execute_code(self, code: str, task: Task) -> tuple[bool, str, str]:
        """Execute Python code and return (success, output, error)."""
        language = task.context.get("language", "python")

        if language == "python":
            return await self._execute_python(code, task)
        elif language in ("javascript", "typescript", "js", "ts"):
            return await self._execute_javascript(code, task)
        else:
            # Generic execution attempt
            return await self._execute_generic(code, language, task)

    async def _execute_python(self, code: str, task: Task) -> tuple[bool, str, str]:
        """Execute Python code safely."""
        # Safety check: no dangerous patterns
        if not self._is_code_safe(code):
            return False, "", "Code contains dangerous patterns (os.system, eval, exec, etc.)"

        timeout = task.context.get("timeout", 30)

        # Write to temp file and execute
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            output = stdout.decode("utf-8", errors="replace").strip()
            error = stderr.decode("utf-8", errors="replace").strip()

            success = proc.returncode == 0
            return success, output, error
        except asyncio.TimeoutError:
            return False, "", f"Execution timed out after {timeout}s"
        except Exception as e:
            return False, "", f"Execution failed: {e}"

    async def _execute_javascript(self, code: str, task: Task) -> tuple[bool, str, str]:
        """Execute JavaScript/TypeScript code via Node.js."""
        timeout = task.context.get("timeout", 30)
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", "-e", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace").strip()
            error = stderr.decode("utf-8", errors="replace").strip()
            return proc.returncode == 0, output, error
        except FileNotFoundError:
            return False, "", "Node.js not found. Install Node.js to execute JavaScript/TypeScript code."
        except asyncio.TimeoutError:
            return False, "", f"Execution timed out after {timeout}s"
        except Exception as e:
            return False, "", f"Execution failed: {e}"

    async def _execute_generic(self, code: str, language: str, task: Task) -> tuple[bool, str, str]:
        """Generic execution for other languages."""
        return False, "", f"Execution for {language} is not yet implemented."

    async def _fix_code(self, code: str, task_description: str, error: str) -> str:
        """Ask LLM to fix the code based on the error."""
        messages = self._build_messages(
            f"The following code has an error. Fix it and return the COMPLETE corrected code.\n\n"
            f"Task: {task_description}\n\n"
            f"Original code:\n{code}\n\n"
            f"Error:\n{error}\n\n"
            f"Return ONLY the fixed code, no explanations, no markdown fences."
        )

        response = await self._llm_chat(messages)
        code = response.content
        # Clean up markdown
        if "```" in code:
            parts = code.split("```")
            for part in parts:
                part = part.strip()
                if part and not part.startswith(("python", "py")):
                    code = part
                    break
                lines = part.split("\n", 1)
                if len(lines) > 1:
                    code = lines[1]
                    break
        return code

    async def _generate_project(self, task: Task) -> TaskResult:
        """Generate a complete multi-file project structure."""
        messages = self._build_messages(
            f"Project Request: {task.description}\n"
            f"Generate a full directory structure and the code for all necessary files.\n"
            f"Return ONLY JSON in this format: {{\"files\": [ {{\"path\": \"src/main.py\", \"content\": \"...\"}}, ... ]}}"
        )
        
        try:
            response = await self._llm_chat(messages)
            json_match = re.search(r"\{[\s\S]*\}", response.content)
            if not json_match:
                return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error="Invalid project JSON from LLM")
            
            data = json.loads(json_match.group())
            files = data.get("files", [])
            
            project_root = self.work_dir / f"project_{task.id[:8]}"
            project_root.mkdir(parents=True, exist_ok=True)
            
            created_files = []
            for file_info in files:
                rel_path = file_info.get("path")
                content = file_info.get("content")
                if rel_path and content:
                    full_path = project_root / rel_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    created_files.append(rel_path)
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output=f"🚀 Proje başarıyla oluşturuldu!\nKlasör: {project_root}\nOluşturulan dosyalar: {', '.join(created_files)}"
            )
        except Exception as e:
            return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error=str(e))

    def _is_code_safe(self, code: str) -> bool:
        """Security-critical: Block dangerous patterns before execution.

        Uses AST analysis (not just string matching) to detect dangerous operations.
        This prevents simple obfuscation bypasses like getattr(os, 'system')('cmd').
        """
        import ast

        # Phase 1: AST-based analysis (harder to bypass)
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # If we can't parse it, don't run it
            logger.warning("BLOCKED: Code has syntax errors, not executing")
            return False

        # Dangerous module names
        dangerous_modules = {
            "os", "subprocess", "shutil", "sys", "ctypes",
            "importlib", "pty", "socket", "http.server",
            "xmlrpc", "pickle", "shelve", "tempfile",
        }

        # Dangerous function/attribute names
        dangerous_calls = {
            "eval", "exec", "compile", "__import__",
            "getattr", "setattr", "delattr",
            "globals", "locals", "vars",
            "open",  # Allow only if we enable file I/O explicitly
        }

        # Dangerous attribute accesses
        dangerous_attrs = {
            "system", "popen", "remove", "unlink", "rmtree",
            "removedirs", "rename", "makedirs",
            "Popen", "call", "check_output", "check_call", "run",
            "connect", "bind", "listen", "accept",
            "spawn", "dup2",
            "urlopen", "urlretrieve",
        }

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_root = alias.name.split(".")[0]
                    if module_root in dangerous_modules:
                        logger.warning("BLOCKED: Dangerous import: %s", alias.name)
                        return False

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_root = node.module.split(".")[0]
                    if module_root in dangerous_modules:
                        logger.warning("BLOCKED: Dangerous import from: %s", node.module)
                        return False

            # Check function calls
            elif isinstance(node, ast.Call):
                func = node.func
                # Direct call: eval(), exec(), etc.
                if isinstance(func, ast.Name) and func.id in dangerous_calls:
                    logger.warning("BLOCKED: Dangerous call: %s()", func.id)
                    return False
                # Attribute call: os.system(), subprocess.Popen(), etc.
                if isinstance(func, ast.Attribute) and func.attr in dangerous_attrs:
                    logger.warning("BLOCKED: Dangerous attribute call: .%s()", func.attr)
                    return False

        # Phase 2: Final string-level checks for non-Python patterns
        string_blocklist = [
            "rm -rf", "curl ", "wget ", "bash -c",
            "powershell ", "cmd.exe", "pty.spawn",
        ]
        for pattern in string_blocklist:
            if pattern in code:
                logger.warning("BLOCKED: Dangerous string pattern: %s", pattern)
                return False

        return True

    @staticmethod
    def _ext_for_language(language: str) -> str:
        ext_map = {
            "python": "py",
            "javascript": "js",
            "js": "js",
            "typescript": "ts",
            "ts": "ts",
            "c++": "cpp",
            "cpp": "cpp",
            "c": "c",
            "c#": "cs",
            "go": "go",
            "golang": "go",
            "rust": "rs",
            "java": "java",
            "ruby": "rb",
            "php": "php",
            "swift": "swift",
            "kotlin": "kt",
            "bash": "sh",
            "shell": "sh",
        }
        return ext_map.get(language.lower(), "txt")

    async def review_code(self, code: str, language: str = "python") -> str:
        """Review code for quality and security."""
        messages = self._build_messages(
            f"Review this {language} code for quality, security, and best practices.\n"
            f"Provide specific improvement suggestions.\n\n"
            f"Code:\n{code}"
        )
        response = await self._llm_chat(messages)
        return response.content
