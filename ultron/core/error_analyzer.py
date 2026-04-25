import re
import logging
import traceback
import json
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ErrorAnalyzer:
    """Advanced error analysis and self-healing logic for Ultron."""
    
    COMMON_FIXES = {
        r"ModuleNotFoundError: No module named '([^']+)'": "pip install {0}",
        r"ImportError: cannot import name '([^']+)' from '([^']+)'": "Check if {0} exists in {1} or if there's a circular import.",
        r"SyntaxError: (.*)": "Fix the syntax at the specified location.",
        r"ConnectionError: (.*)": "Check your internet connection or if the local service is running.",
        r"PermissionError: (.*)": "Ensure the application has write permissions.",
    }

    @staticmethod
    async def analyze(error_str: str, stack_trace: Optional[str] = None) -> Dict[str, Any]:
        """Analyze an error using heuristics first, then LLM if needed."""
        from ultron.core.llm_router import router
        analysis = {
            "error_type": "Unknown",
            "explanation": "An unexpected error occurred.",
            "suggested_fix": None,
            "can_self_heal": False,
            "semantic_fix": None
        }

        # 1. Heuristic Check (Fast)
        error_lines = error_str.strip().split('\n')
        last_line = error_lines[-1] if error_lines else ""
        
        found_heuristic = False
        for pattern, fix_template in ErrorAnalyzer.COMMON_FIXES.items():
            match = re.search(pattern, last_line)
            if match:
                analysis["error_type"] = last_line.split(':')[0]
                groups = match.groups()
                analysis["explanation"] = f"Heuristic match: {last_line}"
                analysis["suggested_fix"] = fix_template.format(*groups) if "{0}" in fix_template else fix_template
                analysis["can_self_heal"] = "pip install" in analysis["suggested_fix"]
                found_heuristic = True
                break

        # 2. Semantic Analysis (LLM) - Deep Dive
        if not found_heuristic or "Unknown" in analysis["error_type"]:
            try:
                prompt = (
                    "You are a Senior Python Engineer. Analyze this error and provide a fix.\n"
                    f"ERROR: {error_str}\n"
                    f"STACK TRACE: {stack_trace}\n\n"
                    "Return ONLY a JSON object with:\n"
                    "- 'error_type': string\n"
                    "- 'explanation': concise explanation\n"
                    "- 'suggested_fix': shell command or action\n"
                    "- 'semantic_fix': a Python code snippet to fix it (if applicable)\n"
                    "- 'can_self_heal': boolean"
                )
                resp = await router.chat([{"role": "user", "content": prompt}], model_type="fast")
                # Cleanup JSON
                content = re.sub(r"```json\n?|\n?```", "", resp.content).strip()
                llm_analysis = json.loads(content)
                analysis.update(llm_analysis)
            except Exception as e:
                logger.error(f"Semantic analysis failed: {e}")

        return analysis

    @staticmethod
    async def format_diagnostic_report(error: Exception) -> str:
        """Generate a detailed diagnostic report."""
        error_str = str(error)
        stack_trace = traceback.format_exc()
        analysis = await ErrorAnalyzer.analyze(error_str, stack_trace)
        
        report = [
            "============================================================",
            "🚨 ULTRON DIAGNOSTIC REPORT",
            "============================================================",
            f"ERROR TYPE: {analysis['error_type']}",
            f"EXPLANATION: {analysis['explanation']}",
            f"SUGGESTED FIX: {analysis['suggested_fix'] or 'No automatic fix available.'}",
            "------------------------------------------------------------",
            "STACK TRACE:",
            stack_trace,
            "============================================================",
        ]
        return "\n".join(report)
