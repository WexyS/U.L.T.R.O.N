"""Code Execution Sandbox — Safe and isolated code execution for Ultron."""

import asyncio
import logging
import os
import re
import subprocess
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("ultron.skills.code_sandbox")

class CodeSandbox:
    """Safely executes code snippets and captures output."""

    DANGEROUS_PATTERNS = [
        r"os\.(system|popen|execv|rmdir|remove)",
        r"subprocess\.",
        r"__import__",
        r"eval\s*\(",
        r"exec\s*\(",
        r"shutil\.",
        r"open\s*\(['\"]/etc/",
    ]

    async def execute_python(self, code: str, timeout: int = 15) -> Dict[str, Any]:
        """Executes Python code in a subprocess."""
        
        # 1. Safety Check
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                return {
                    "success": False,
                    "error": f"Security Violation: Dangerous pattern detected: {pattern}",
                    "stdout": "",
                    "stderr": ""
                }

        # 2. Run in Subprocess
        start_time = time.monotonic()
        try:
            # We use the same venv as the main app for dependencies
            python_exe = os.path.join(".venv", "Scripts", "python.exe") if os.name == "nt" else os.path.join(".venv", "bin", "python")
            
            process = await asyncio.create_subprocess_exec(
                python_exe, "-c", code,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                exit_code = process.returncode
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Execution Timed Out ({timeout}s)",
                    "stdout": "",
                    "stderr": ""
                }

            elapsed = (time.monotonic() - start_time) * 1000
            
            return {
                "success": exit_code == 0,
                "stdout": stdout.decode(errors="ignore"),
                "stderr": stderr.decode(errors="ignore"),
                "exit_code": exit_code,
                "latency_ms": elapsed
            }
            
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return {"success": False, "error": str(e)}

# Singleton
sandbox = CodeSandbox()
