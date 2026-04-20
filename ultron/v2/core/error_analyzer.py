import re
import logging
import traceback
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ErrorAnalyzer:
    """Advanced error analysis and self-healing logic for Ultron."""
    
    COMMON_FIXES = {
        r"ModuleNotFoundError: No module named '([^']+)'": "pip install {0}",
        r"ImportError: cannot import name '([^']+)' from '([^']+)'": "Check if {0} exists in {1} or if there's a circular import.",
        r"SyntaxError: (.*)": "Fix the syntax at the specified location. Common cause: unclosed brackets or escaped quotes.",
        r"ConnectionError: (.*)": "Check your internet connection or if the local service (Ollama/VoiceBox) is running.",
        r"PermissionError: (.*)": "Ensure the application has write permissions to the directory or file: {0}",
    }

    @staticmethod
    def analyze(error_str: str, stack_trace: Optional[str] = None) -> Dict[str, Any]:
        """Analyze an error and provide human-readable explanation and suggested fix."""
        analysis = {
            "error_type": "Unknown",
            "explanation": "An unexpected error occurred.",
            "suggested_fix": None,
            "can_self_heal": False
        }

        # Extract error type and message
        error_lines = error_str.strip().split('\n')
        last_line = error_lines[-1]
        
        for pattern, fix_template in ErrorAnalyzer.COMMON_FIXES.items():
            match = re.search(pattern, last_line)
            if match:
                analysis["error_type"] = last_line.split(':')[0]
                groups = match.groups()
                analysis["explanation"] = f"Detected a {analysis['error_type']} indicating: {last_line}"
                
                if "{0}" in fix_template:
                    analysis["suggested_fix"] = fix_template.format(*groups)
                else:
                    analysis["suggested_fix"] = fix_template
                
                if "pip install" in fix_template:
                    analysis["can_self_heal"] = True
                break

        # Check for specific Ultron rebranding errors
        if "llamafactory" in error_str.lower() or "openguider" in error_str.lower():
            analysis["explanation"] += " (Potentially legacy branding reference detected)"
            analysis["suggested_fix"] = "Update legacy naming to UltronFactory or UltronVision."
            analysis["can_self_heal"] = True

        return analysis

    @staticmethod
    def format_diagnostic_report(error: Exception) -> str:
        """Generate a detailed diagnostic report for logging or user display."""
        error_str = str(error)
        stack_trace = traceback.format_exc()
        analysis = ErrorAnalyzer.analyze(error_str, stack_trace)
        
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
