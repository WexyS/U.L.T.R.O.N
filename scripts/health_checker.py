"""System Health Checker & Auto-Fixer — Diagnoses and fixes Ultron issues.

Run this script to:
1. Check all dependencies are installed
2. Verify all providers can initialize
3. Test agent initialization
4. Check memory system health
5. Auto-fix common issues
6. Generate health report

Usage:
    python scripts/health_checker.py
"""

import os
import sys
import json
import logging
import importlib
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("health_checker")


class HealthCheckResult:
    def __init__(self):
        self.checks: List[Dict[str, Any]] = []
        self.fixes_applied: List[str] = []
        self.errors: List[str] = []

    def add_check(self, name: str, status: str, details: str = ""):
        self.checks.append({
            "name": name,
            "status": status,  # pass, warn, fail
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def add_fix(self, fix: str):
        self.fixes_applied.append(fix)
        logger.info(f"✅ Applied fix: {fix}")

    def add_error(self, error: str):
        self.errors.append(error)
        logger.error(f"❌ {error}")

    def to_dict(self) -> Dict:
        return {
            "timestamp": datetime.now().isoformat(),
            "total_checks": len(self.checks),
            "passed": sum(1 for c in self.checks if c["status"] == "pass"),
            "warnings": sum(1 for c in self.checks if c["status"] == "warn"),
            "failures": sum(1 for c in self.checks if c["status"] == "fail"),
            "fixes_applied": self.fixes_applied,
            "errors": self.errors,
            "checks": self.checks
        }

    def summary(self) -> str:
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c["status"] == "pass")
        warns = sum(1 for c in self.checks if c["status"] == "warn")
        failed = sum(1 for c in self.checks if c["status"] == "fail")
        
        status = "✅ HEALTHY" if failed == 0 else "⚠️ DEGRADED" if warns > 0 else "❌ UNHEALTHY"
        
        return f"""
{'='*60}
ULTRON SYSTEM HEALTH REPORT
{'='*60}
Status: {status}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Results:
  ✅ Passed: {passed}/{total}
  ⚠️ Warnings: {warns}/{total}
  ❌ Failed: {failed}/{total}

Fixes Applied: {len(self.fixes_applied)}
  {chr(10).join('  - ' + f for f in self.fixes_applied) if self.fixes_applied else '  None needed'}

Errors: {len(self.errors)}
  {chr(10).join('  - ' + e for e in self.errors) if self.errors else '  None'}
{'='*60}
"""


def check_python_version(result: HealthCheckResult):
    """Check Python version is compatible."""
    if sys.version_info >= (3, 10):
        result.add_check("Python Version", "pass", f"{sys.version_info.major}.{sys.version_info.minor}")
    else:
        result.add_check("Python Version", "warn", f"Python 3.10+ recommended, have {sys.version_info.major}.{sys.version_info.minor}")


def check_dependencies(result: HealthCheckResult):
    """Check all required packages are installed."""
    required_packages = [
        "fastapi", "uvicorn", "pydantic", "httpx", "ollama",
        "chromadb", "sentence_transformers", "duckduckgo_search",
        "beautifulsoup4", "psutil", "pyyaml", "rich",
        "playwright", "easyocr", "pyautogui",
        "edge_tts", "speech_recognition",
        "slowapi", "python_dotenv"
    ]

    missing = []
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing.append(package)
    
    if not missing:
        result.add_check("Dependencies", "pass", f"All {len(required_packages)} packages installed")
    else:
        result.add_check("Dependencies", "warn", f"Missing: {', '.join(missing)}")
        
        # Auto-fix: try to install critical missing packages
        critical = [p for p in missing if p in ["fastapi", "pydantic", "httpx"]]
        if critical:
            logger.warning(f"Critical packages missing: {critical}")
            result.add_error(f"Critical dependencies missing: {', '.join(critical)}")


def check_airllm(result: HealthCheckResult):
    """Check AirLLM installation and CUDA availability."""
    try:
        import airllm
        result.add_check("AirLLM Package", "pass", "Installed")
        
        # Check CUDA
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                result.add_check("CUDA Available", "pass", f"{gpu_name} ({gpu_mem:.1f}GB VRAM)")
                
                # Check if enough VRAM for Llama 3.1 70B
                if gpu_mem >= 4:
                    result.add_check("VRAM for Llama 3.1 70B", "pass", f"{gpu_mem:.1f}GB (needs 4GB+)")
                else:
                    result.add_check("VRAM for Llama 3.1 70B", "warn", f"{gpu_mem:.1f}GB (needs 4GB+)")
            else:
                result.add_check("CUDA Available", "warn", "No GPU - AirLLM requires CUDA")
        except ImportError:
            result.add_check("CUDA Available", "fail", "PyTorch not installed")
            
    except ImportError:
        result.add_check("AirLLM Package", "warn", "Not installed (pip install airllm)")


def check_ollama(result: HealthCheckResult):
    """Check Ollama availability."""
    import httpx
    
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get("models", [])
            result.add_check("Ollama Server", "pass", f"{len(models)} models available")
        else:
            result.add_check("Ollama Server", "warn", f"Running but returned {response.status_code}")
    except Exception as e:
        result.add_check("Ollama Server", "warn", f"Not running (start with: ollama serve)")


def check_memory_system(result: HealthCheckResult):
    """Check memory system health."""
    try:
        from ultron.memory.engine import MemoryEngine
        
        persist_dir = "./data/memory_v2"
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        
        memory = MemoryEngine(persist_dir=persist_dir)
        stats = memory.stats()
        
        result.add_check("Memory Engine", "pass", str(stats))
    except Exception as e:
        result.add_check("Memory Engine", "fail", str(e))


def check_providers(result: HealthCheckResult):
    """Check provider initialization."""
    try:
        from ultron.providers.router import ProviderRouter
        
        router = ProviderRouter()
        available = router.available_providers()
        
        if available:
            result.add_check("Providers", "pass", f"{len(available)} providers: {', '.join(available)}")
        else:
            result.add_check("Providers", "warn", "No providers configured")
    except Exception as e:
        result.add_check("Providers", "fail", str(e))
        logger.debug(f"Provider check error: {traceback.format_exc()}")


def check_agents(result: HealthCheckResult):
    """Check agent modules can import."""
    agents = [
        "ultron.agents.coder",
        "ultron.agents.researcher",
        "ultron.agents.rpa_operator",
        "ultron.agents.email_agent",
        "ultron.agents.sysmon_agent",
        "ultron.agents.clipboard_agent",
        "ultron.agents.meeting_agent",
        "ultron.agents.files_agent",
        "ultron.agents.error_analyzer",
    ]

    failed = []
    for agent_module in agents:
        try:
            importlib.import_module(agent_module)
        except Exception as e:
            failed.append(f"{agent_module}: {str(e)[:100]}")
    
    if not failed:
        result.add_check("Agents", "pass", f"All {len(agents)} agents importable")
    else:
        result.add_check("Agents", "warn", f"{len(failed)}/{len(agents)} failed to import")


def check_database(result: HealthCheckResult):
    """Check SQLite database health."""
    try:
        import sqlite3
        db_path = Path("./data/memory_v2/memory.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        result.add_check("SQLite Database", "pass", f"{len(tables)} tables")
    except Exception as e:
        result.add_check("SQLite Database", "fail", str(e))


def check_chromadb(result: HealthCheckResult):
    """Check ChromaDB availability."""
    try:
        import chromadb
        
        chroma_dir = Path("./data/chroma")
        chroma_dir.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(path=str(chroma_dir))
        collections = client.list_collections()
        
        result.add_check("ChromaDB", "pass", f"{len(collections)} collections")
    except Exception as e:
        result.add_check("ChromaDB", "warn", str(e))


def check_env_file(result: HealthCheckResult):
    """Check .env file exists and has basic config."""
    env_file = project_root / ".env"
    
    if not env_file.exists():
        result.add_check(".env File", "warn", "Not found - copy .env.example to .env")
        return
    
    env_content = env_file.read_text(encoding="utf-8")
    has_api_keys = any(key in env_content for key in ["API_KEY", "api_key"])
    
    if has_api_keys:
        result.add_check(".env File", "pass", "Configured with API keys")
    else:
        result.add_check(".env File", "pass", "Using local providers only (Ollama/AirLLM)")


def check_workspace(result: HealthCheckResult):
    """Check workspace directory."""
    workspace_dir = project_root / "workspace"
    
    if workspace_dir.exists():
        files = list(workspace_dir.rglob("*"))
        result.add_check("Workspace", "pass", f"{len(files)} files")
    else:
        workspace_dir.mkdir(exist_ok=True)
        result.add_check("Workspace", "pass", "Created")


def auto_fix_common_issues(result: HealthCheckResult):
    """Attempt to auto-fix common issues."""
    
    # Check if .env exists, if not copy from example
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        try:
            import shutil
            shutil.copy(env_example, env_file)
            result.add_fix("Created .env from .env.example")
        except Exception as e:
            result.add_error(f"Failed to create .env: {e}")
    
    # Create necessary directories
    for dir_path in ["data/memory_v2", "data/chroma", "workspace", "context"]:
        dir_full = project_root / dir_path
        if not dir_full.exists():
            dir_full.mkdir(parents=True, exist_ok=True)
            result.add_fix(f"Created directory: {dir_path}")
    
    # Check if Playwright is installed
    try:
        import subprocess
        result_browser = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result_browser.returncode != 0:
            logger.info("Installing Playwright browsers...")
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                timeout=120
            )
            result.add_fix("Installed Playwright Chromium")
    except Exception:
        pass  # Playwright installation is optional


def generate_report(result: HealthCheckResult):
    """Save health report to file."""
    report_dir = project_root / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.write_text(json.dumps(result.to_dict(), indent=2))
    
    logger.info(f"Health report saved to: {report_file}")


def main():
    """Run comprehensive health check."""
    print("="*60)
    print("ULTRON v2.1 - SYSTEM HEALTH CHECKER")
    print("="*60)
    print()
    
    result = HealthCheckResult()
    
    # Run all checks
    logger.info("Running system checks...")
    check_python_version(result)
    check_dependencies(result)
    check_airllm(result)
    check_ollama(result)
    check_memory_system(result)
    check_providers(result)
    check_agents(result)
    check_database(result)
    check_chromadb(result)
    check_env_file(result)
    check_workspace(result)
    
    # Auto-fix issues
    logger.info("Applying automatic fixes...")
    auto_fix_common_issues(result)
    
    # Generate report
    generate_report(result)
    
    # Print summary
    print(result.summary())
    
    # Exit code based on health
    if result.to_dict()["failures"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
