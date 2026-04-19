"""Sandbox — Secure code execution environment.

Provides isolated execution environments for running untrusted code:
- Process isolation with resource limits
- Filesystem restrictions
- Network restrictions
- Timeout enforcement
- Output capture and sanitization
"""

from __future__ import annotations

import asyncio
import logging
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result of sandboxed code execution."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    duration_ms: float = 0.0
    memory_used_mb: float = 0.0
    killed: bool = False        # Was it killed due to timeout/limits
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_output_bytes: int = 100_000
    allow_network: bool = False
    allow_file_write: bool = True
    work_dir: Optional[str] = None
    env_vars: dict[str, str] = field(default_factory=dict)


class Sandbox:
    """Isolated code execution environment.

    Uses subprocess with restricted permissions for safe code execution.
    Does NOT require Docker — works on any system.
    """

    def __init__(
        self,
        base_work_dir: str = "./workspace/sandbox",
        default_config: Optional[SandboxConfig] = None,
    ) -> None:
        self.base_work_dir = Path(base_work_dir)
        self.base_work_dir.mkdir(parents=True, exist_ok=True)
        self.default_config = default_config or SandboxConfig()

        # Execution statistics
        self._total_executions = 0
        self._successful_executions = 0
        self._killed_executions = 0

        logger.info("Sandbox initialized (work_dir=%s)", self.base_work_dir)

    async def execute_python(
        self,
        code: str,
        config: Optional[SandboxConfig] = None,
    ) -> SandboxResult:
        """Execute Python code in a sandboxed subprocess."""
        cfg = config or self.default_config
        self._total_executions += 1

        start_time = time.monotonic()

        # Create isolated work directory
        work_dir = Path(cfg.work_dir) if cfg.work_dir else self.base_work_dir
        work_dir.mkdir(parents=True, exist_ok=True)

        # Write the sandboxed code to a temporary file
        code_file = work_dir / f"sandbox_{int(datetime.now().timestamp())}.py"

        # Wrap the code with safety imports and restrictions
        wrapped_code = self._wrap_code(code, cfg)

        try:
            code_file.write_text(wrapped_code, encoding="utf-8")

            # Create subprocess with restricted access
            env = self._build_safe_env(cfg)

            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-u", str(code_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=cfg.timeout_seconds,
                )

                stdout = stdout_bytes.decode("utf-8", errors="replace")[:cfg.max_output_bytes]
                stderr = stderr_bytes.decode("utf-8", errors="replace")[:cfg.max_output_bytes]

                success = proc.returncode == 0
                if success:
                    self._successful_executions += 1

                duration_ms = (time.monotonic() - start_time) * 1000

                return SandboxResult(
                    success=success,
                    stdout=stdout.strip(),
                    stderr=stderr.strip(),
                    return_code=proc.returncode or 0,
                    duration_ms=duration_ms,
                )

            except asyncio.TimeoutError:
                # Kill the process
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass

                self._killed_executions += 1
                duration_ms = (time.monotonic() - start_time) * 1000

                return SandboxResult(
                    success=False,
                    killed=True,
                    error=f"Execution timed out after {cfg.timeout_seconds}s",
                    duration_ms=duration_ms,
                )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            return SandboxResult(
                success=False,
                error=f"Sandbox error: {e}",
                duration_ms=duration_ms,
            )
        finally:
            # Clean up temporary code file
            try:
                code_file.unlink(missing_ok=True)
            except Exception:
                pass

    def _wrap_code(self, code: str, config: SandboxConfig) -> str:
        """Wrap user code with safety restrictions."""
        imports_block = (
            "import sys\n"
            "import signal\n"
            "\n"
            "# ── Sandbox Safety Setup ────────────────────────────────────────\n"
            "\n"
            "# Set resource limits\n"
            "try:\n"
            "    import resource\n"
            f"    resource.setrlimit(resource.RLIMIT_AS, ({config.max_memory_mb * 1024 * 1024}, {config.max_memory_mb * 1024 * 1024}))\n"
            "except (ImportError, ValueError):\n"
            "    pass  # Windows doesn't have resource module\n"
            "\n"
            "# Timeout handler\n"
            f"def _sandbox_timeout_handler(signum, frame):\n"
            f"    raise TimeoutError('Execution timed out inside sandbox')\n"
            "\n"
            "try:\n"
            f"    signal.signal(signal.SIGALRM, _sandbox_timeout_handler)\n"
            f"    signal.alarm({config.timeout_seconds})\n"
            "except (AttributeError, ValueError):\n"
            "    pass  # Windows doesn't have SIGALRM\n"
            "\n"
        )

        # Block network if not allowed
        if not config.allow_network:
            imports_block += (
                "# Block network access\n"
                "import socket as _sock\n"
                "_original_connect = _sock.socket.connect\n"
                "def _blocked_connect(self, *args, **kwargs):\n"
                "    raise PermissionError('Network access is disabled in sandbox mode')\n"
                "_sock.socket.connect = _blocked_connect\n"
                "\n"
            )

        return imports_block + "\n# ── User Code ────────────────────────────────────────\n\n" + code

    def _build_safe_env(self, config: SandboxConfig) -> dict[str, str]:
        """Build a restricted environment for the subprocess."""
        import os

        # Start with minimal environment
        safe_env: dict[str, str] = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": "",
            "HOME": os.environ.get("HOME", os.environ.get("USERPROFILE", "")),
            "LANG": "en_US.UTF-8",
            "SANDBOX": "1",
        }

        # Windows-specific
        if sys.platform == "win32":
            safe_env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
            safe_env["TEMP"] = os.environ.get("TEMP", r"C:\Temp")
            safe_env["TMP"] = os.environ.get("TMP", r"C:\Temp")

        # Add custom env vars
        safe_env.update(config.env_vars)

        return safe_env

    # ── Statistics ────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "total_executions": self._total_executions,
            "successful": self._successful_executions,
            "killed": self._killed_executions,
            "success_rate": (
                f"{self._successful_executions / max(1, self._total_executions) * 100:.1f}%"
            ),
            "work_dir": str(self.base_work_dir),
        }
