"""Error Analysis & Self-Healing Agent — Autonomous bug detection and fixing.

This agent provides:
1. Automatic error detection from logs
2. Root cause analysis using AI
3. Automated fix generation
4. Safe fix application with rollback
5. Pattern learning from past fixes
6. Preventive measures for future errors

Usage:
    from ultron.v2.agents.error_analyzer import ErrorAnalyzerAgent
    
    agent = ErrorAnalyzerAgent()
    result = await agent.analyze_and_fix(error_log, code_context)
"""

import os
import re
import json
import logging
import asyncio
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

from ultron.v2.core.types import Task, TaskResult, TaskStatus
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter
from ultron.v2.core.error_analyzer import ErrorAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ErrorAnalysis:
    """Structured error analysis result."""
    error_type: str
    error_message: str
    root_cause: str
    severity: str  # critical, high, medium, low
    affected_files: List[str]
    fix_suggestion: str
    fix_code: Optional[str] = None
    confidence: float = 0.0
    preventive_measures: List[str] = field(default_factory=list)


class ErrorAnalyzerAgent:
    """Autonomous error analysis and self-healing agent.
    
    Detects, analyzes, and fixes errors in the Ultron system.
    """

    def __init__(self, llm_router: Optional[LLMRouter] = None):
        self.llm_router = llm_router
        self.event_bus = EventBus()
        self.blackboard = Blackboard()
        self._fix_history = []
        self._error_patterns = {}
        self._load_error_patterns()

    def _load_error_patterns(self):
        """Load known error patterns from file."""
        patterns_file = Path(__file__).parent.parent.parent.parent / "data" / "error_patterns.json"
        if patterns_file.exists():
            try:
                self._error_patterns = json.loads(patterns_file.read_text())
                logger.info(f"Loaded {len(self._error_patterns)} error patterns")
            except Exception as e:
                logger.warning(f"Failed to load error patterns: {e}")

    async def analyze_error(self, error_log: str, code_context: Optional[str] = None) -> ErrorAnalysis:
        """Analyze an error and determine root cause."""
        
        # Step 1: Pattern matching (fast)
        pattern_match = self._match_error_pattern(error_log)
        if pattern_match and pattern_match['confidence'] > 0.9:
            logger.info(f"Error matched known pattern: {pattern_match['type']}")
            return ErrorAnalysis(**pattern_match)

        # Step 2: AI-powered analysis (slower but more accurate)
        if self.llm_router:
            return await self._ai_analyze(error_log, code_context)
        
        # Fallback: Basic analysis
        return self._basic_analyze(error_log)

    def _match_error_pattern(self, error_log: str) -> Optional[Dict]:
        """Match error against known patterns."""
        error_lower = error_log.lower()
        
        for pattern_type, pattern_data in self._error_patterns.items():
            for keyword in pattern_data.get("keywords", []):
                if keyword.lower() in error_lower:
                    return {
                        "error_type": pattern_type,
                        "error_message": error_log[:200],
                        "root_cause": pattern_data.get("root_cause", "Unknown"),
                        "severity": pattern_data.get("severity", "medium"),
                        "affected_files": pattern_data.get("affected_files", []),
                        "fix_suggestion": pattern_data.get("fix", ""),
                        "confidence": pattern_data.get("confidence", 0.7),
                        "preventive_measures": pattern_data.get("preventive", [])
                    }
        return None

    async def _ai_analyze(self, error_log: str, code_context: Optional[str] = None) -> ErrorAnalysis:
        """Use AI to analyze error."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert error analysis specialist. Analyze the provided error log and:\n"
                    "1. Identify the error type\n"
                    "2. Determine the root cause\n"
                    "3. Assess severity (critical/high, medium, low)\n"
                    "4. List affected files\n"
                    "5. Provide a detailed fix suggestion\n"
                    "6. If possible, provide the exact fix code\n"
                    "7. Estimate confidence (0.0-1.0)\n"
                    "8. Suggest preventive measures\n\n"
                    "Return JSON format:\n"
                    "{\n"
                    '  "error_type": "...",\n'
                    '  "root_cause": "...",\n'
                    '  "severity": "critical|high|medium|low",\n'
                    '  "affected_files": ["file1.py", ...],\n'
                    '  "fix_suggestion": "...",\n'
                    '  "fix_code": "...",\n'
                    '  "confidence": 0.85,\n'
                    '  "preventive_measures": ["measure1", ...]\n'
                    "}"
                )
            },
            {
                "role": "user",
                "content": f"Error log:\n{error_log}\n\n" + (f"Code context:\n{code_context}" if code_context else "")
            }
        ]

        try:
            response = await self.llm_router.chat(messages, max_tokens=1024)
            analysis = self._parse_json_response(response.content)
            analysis["error_message"] = error_log[:200]
            return ErrorAnalysis(**analysis)
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
            return self._basic_analyze(error_log)

    def _basic_analyze(self, error_log: str) -> ErrorAnalysis:
        """Basic error analysis using core ErrorAnalyzer."""
        analysis = ErrorAnalyzer.analyze(error_log)
        
        # Map to structured ErrorAnalysis
        affected_files = re.findall(r'File "([^"]+\.py)"', error_log)
        
        return ErrorAnalysis(
            error_type=analysis["error_type"],
            error_message=error_log[:200],
            root_cause=analysis["explanation"],
            severity="high" if analysis["can_self_heal"] else "medium",
            affected_files=list(set(affected_files)),
            fix_suggestion=analysis["suggested_fix"] or "Manual review required",
            confidence=0.6,
            preventive_measures=["Add proper error handling", "Verify system consistency"]
        )

    def _parse_json_response(self, response: str) -> Dict:
        """Extract JSON from LLM response."""
        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Fallback: Try to parse key-value pairs
        result = {
            "error_type": "unknown",
            "root_cause": "Unable to determine",
            "severity": "medium",
            "affected_files": [],
            "fix_suggestion": "Review the error and fix manually",
            "confidence": 0.5,
            "preventive_measures": []
        }
        
        for key in result.keys():
            match = re.search(f'"{key}"\s*:\s*"([^"]*)"', response)
            if match:
                result[key] = match.group(1)
        
        return result

    async def generate_fix(self, analysis: ErrorAnalysis, file_content: Optional[str] = None) -> Optional[str]:
        """Generate code fix for the analyzed error."""
        if analysis.fix_code:
            return analysis.fix_code
        
        if not self.llm_router or not file_content:
            return None

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert code fixer. Given an error analysis and the original code,\n"
                    "provide ONLY the fixed code block. Do not explain, just output the corrected code.\n"
                    "Keep all other code unchanged. Use minimal diff-style fixes."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Error: {analysis.error_type}\n"
                    f"Root cause: {analysis.root_cause}\n"
                    f"Fix suggestion: {analysis.fix_suggestion}\n\n"
                    f"Original code:\n{file_content}\n\n"
                    f"Provide the fixed code:"
                )
            }
        ]

        try:
            response = await self.llm_router.chat(messages, max_tokens=2048)
            return self._extract_code_from_response(response.content)
        except Exception as e:
            logger.error(f"Failed to generate fix: {e}")
            return None

    def _extract_code_from_response(self, response: str) -> str:
        """Extract code blocks from LLM response."""
        # Try markdown code block
        code_match = re.search(r'```(?:python)?\n([\s\S]*?)```', response)
        if code_match:
            return code_match.group(1).strip()
        return response.strip()

    async def apply_fix(self, file_path: str, fix_code: str, backup: bool = True) -> bool:
        """Safely apply a fix to a file."""
        filepath = Path(file_path)
        
        if not filepath.exists():
            logger.error(f"File not found: {file_path}")
            return False

        # Create backup
        if backup:
            backup_path = filepath.with_suffix(f"{filepath.suffix}.bak.{int(datetime.now().timestamp())}")
            backup_path.write_text(filepath.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info(f"Backup created: {backup_path}")

        # Apply fix
        try:
            filepath.write_text(fix_code, encoding="utf-8")
            self._fix_history.append({
                "file": file_path,
                "timestamp": datetime.now().isoformat(),
                "backup": str(backup_path) if backup else None
            })
            logger.info(f"Fix applied to: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply fix: {e}")
            # Restore backup if available
            if backup and 'backup_path' in locals() and backup_path.exists():
                filepath.write_text(backup_path.read_text())
                logger.info("Restored from backup")
            return False

    def rollback_fix(self) -> bool:
        """Rollback the last applied fix."""
        if not self._fix_history:
            logger.warning("No fixes to rollback")
            return False
        
        last_fix = self._fix_history.pop()
        backup_path = last_fix.get("backup")
        
        if backup_path and Path(backup_path).exists():
            try:
                Path(last_fix["file"]).write_text(Path(backup_path).read_text())
                logger.info(f"Rolled back fix for: {last_fix['file']}")
                return True
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
                return False
        
        logger.error("No backup found for rollback")
        return False

    async def analyze_and_fix(self, error_log: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Complete analyze and fix workflow."""
        # Step 1: Analyze error
        analysis = await self.analyze_error(error_log)
        
        result = {
            "success": False,
            "analysis": analysis,
            "fix_applied": False,
            "message": ""
        }

        if analysis.severity in ["critical", "high"] and analysis.fix_suggestion:
            # Step 2: Generate fix if we have file content
            if file_path and Path(file_path).exists():
                file_content = Path(file_path).read_text()
                fix_code = await self.generate_fix(analysis, file_content)
                
                if fix_code:
                    # Step 3: Apply fix
                    success = await self.apply_fix(file_path, fix_code)
                    result["fix_applied"] = success
                    result["message"] = "Fix applied successfully" if success else "Fix application failed"
                    result["success"] = success
                else:
                    result["message"] = "Could not generate fix"
            else:
                result["message"] = f"Fix suggestion: {analysis.fix_suggestion}"
                result["success"] = True
        else:
            result["message"] = f"Analysis complete: {analysis.root_cause}"
            result["success"] = True

        return result

    def learn_from_fix(self, error_pattern: str, fix_details: Dict):
        """Save fix to knowledge base for future use."""
        if error_pattern not in self._error_patterns:
            self._error_patterns[error_pattern] = {
                "type": error_pattern,
                "keywords": [],
                "root_cause": fix_details.get("root_cause", ""),
                "severity": fix_details.get("severity", "medium"),
                "fix": fix_details.get("fix", ""),
                "confidence": 0.7,
                "preventive": []
            }
        
        # Update pattern with new keywords
        keywords = fix_details.get("keywords", [])
        existing = self._error_patterns[error_pattern].get("keywords", [])
        self._error_patterns[error_pattern]["keywords"] = list(set(existing + keywords))

        # Save to file
        patterns_file = Path(__file__).parent.parent.parent.parent / "data" / "error_patterns.json"
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        patterns_file.write_text(json.dumps(self._error_patterns, indent=2))
        
        logger.info(f"Learned new error pattern: {error_pattern}")

    async def batch_analyze(self, error_logs: List[str]) -> List[ErrorAnalysis]:
        """Analyze multiple errors in parallel."""
        tasks = [self.analyze_error(log) for log in error_logs]
        return await asyncio.gather(*tasks)

    def get_error_statistics(self) -> Dict:
        """Get statistics about analyzed errors."""
        stats = {
            "total_analyses": len(self._fix_history),
            "error_types": {},
            "severity_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0}
        }
        
        # Would need to store analyses separately for this to work fully
        return stats

    def get_known_patterns(self) -> List[str]:
        """List all known error patterns."""
        return list(self._error_patterns.keys())
