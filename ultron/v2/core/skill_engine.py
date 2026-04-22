"""Skill Engine for Ultron v3.0 — Tool registration and execution."""

import asyncio
import logging
import subprocess
import os
import psutil
import mss
import pyperclip
from pathlib import Path
from typing import Any, Dict, List, Callable, Optional
from datetime import datetime
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger("ultron.skill_engine")

class SkillEngine:
    """Central engine for managing and executing agent skills."""

    def __init__(self):
        self.skills: Dict[str, Callable] = {}
        self.skill_metadata: Dict[str, Dict[str, Any]] = {}
        self.skills_dir = Path("ultron/v2/skills")
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._register_core_skills()
        self.load_dynamic_skills()

    def load_dynamic_skills(self):
        """Scan skills_dir for Python scripts and register them."""
        import importlib.util
        for file in self.skills_dir.glob("*.py"):
            if file.name == "__init__.py":
                continue
            try:
                module_name = f"ultron.v2.skills.{file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    # Look for register_skill function
                    if hasattr(module, "register_skill"):
                        module.register_skill(self)
                        logger.info(f"Dynamic skill loaded from {file.name}")
            except Exception as e:
                logger.error(f"Failed to load dynamic skill {file.name}: {e}")

    def register(self, name: str, func: Callable, description: str = ""):
        """Register a new skill."""
        self.skills[name] = func
        self.skill_metadata[name] = {
            "name": name,
            "description": description,
            "registered_at": datetime.now().isoformat()
        }
        logger.info(f"Skill registered: {name}")

    async def run(self, name: str, **kwargs) -> Any:
        """Run a skill by name with automatic retries and timeout."""
        if name not in self.skills:
            raise ValueError(f"Skill not found: {name}")

        func = self.skills[name]
        max_retries = 3
        timeout = kwargs.pop("timeout", 60)

        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await asyncio.wait_for(func(**kwargs), timeout=timeout)
                else:
                    return await asyncio.to_thread(func, **kwargs)
            except asyncio.TimeoutError:
                logger.error(f"Skill {name} timed out (Attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"Skill {name} failed: {e} (Attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))

    def _register_core_skills(self):
        """Register built-in v3.0 skills."""
        self.register("skill_web_search", self.skill_web_search, "Search the web using DuckDuckGo.")
        self.register("skill_web_fetch", self.skill_web_fetch, "Fetch and clean text from a URL.")
        self.register("skill_code_execute", self.skill_code_execute, "Execute Python code in a subprocess.")
        self.register("skill_file_read", self.skill_file_read, "Read content from a file.")
        self.register("skill_file_write", self.skill_file_write, "Write content to a file.")
        self.register("skill_system_metrics", self.skill_system_metrics, "Get CPU, RAM, and Disk metrics.")
        self.register("skill_screenshot", self.skill_screenshot, "Capture a screenshot of the primary monitor.")
        self.register("skill_clipboard_read", self.skill_clipboard_read, "Read text from the system clipboard.")
        self.register("skill_notification_send", self.skill_notification_send, "Send a desktop notification.")
        self.register("skill_create_new_skill", self.skill_create_new_skill, "Create and register a new autonomous skill.")

    # ── Core Skill Implementations ────────────────────────────────────────

    async def skill_create_new_skill(self, name: str, code: str, description: str) -> Dict[str, Any]:
        """Agents can use this to teach Ultron new tricks."""
        file_path = self.skills_dir / f"{name}.py"
        
        # Wrap code in a standard register_skill structure
        full_code = (
            f"import logging\n"
            f"logger = logging.getLogger('ultron.skills.{name}')\n\n"
            f"def {name}(**kwargs):\n"
            f"    \"\"\"{description}\"\"\"\n"
            f"    {code.replace(chr(10), chr(10) + '    ')}\n\n"
            f"def register_skill(engine):\n"
            f"    engine.register('{name}', {name}, '{description}')\n"
        )
        
        try:
            self.skill_file_write(str(file_path), full_code)
            self.load_dynamic_skills()
            return {"success": True, "message": f"Skill {name} created and registered."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def skill_web_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """DuckDuckGo search implementation."""
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [{"title": r["title"], "href": r["href"], "body": r["body"]} for r in results]

    async def skill_web_fetch(self, url: str) -> str:
        """BeautifulSoup web scraper implementation."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text(separator=" ")
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return "\n".join(chunk for chunk in chunks if chunk)

    def skill_code_execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Execute code in a subprocess safely (with timeout)."""
        if language.lower() == "python":
            cmd = ["python", "-c", code]
        elif language.lower() in ["bash", "sh"]:
            cmd = ["bash", "-c", code]
        else:
            return {"success": False, "error": f"Language {language} not supported."}

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Code execution timed out."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def skill_file_read(self, path: str) -> str:
        """Read file implementation."""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def skill_file_write(self, path: str, content: str):
        """Write file implementation."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    def skill_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics using psutil."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "timestamp": datetime.now().isoformat()
        }

    def skill_screenshot(self, output_path: str = "data/screenshots/latest.png") -> str:
        """Capture screenshot implementation."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with mss.mss() as sct:
            sct.shot(output=output_path)
        return output_path

    def skill_clipboard_read(self) -> str:
        """Clipboard read implementation."""
        return pyperclip.paste()

    def skill_notification_send(self, title: str, message: str) -> bool:
        """Desktop notification implementation (simplified fallback)."""
        # In a real v3.0, we might use plyer or a custom bridge
        # For now, we log it and return True
        logger.info(f"NOTIFICATION: {title} - {message}")
        return True
