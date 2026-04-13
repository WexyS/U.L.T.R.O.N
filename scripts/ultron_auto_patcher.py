#!/usr/bin/env python3
"""Ultron Auto-Patcher — Autonomous self-healing script with human-in-the-loop approval.

Usage:
    python ultron_auto_patcher.py

Flow:
    1. Human describes bug or pastes error logs
    2. LLM analyzes and identifies likely buggy files
    3. Script reads each file, asks LLM to generate a fix
    4. BEFORE applying: prints unified diff, asks for permission
    5. Human approves (y) or rejects (n)
    6. Approved patches are applied; rejected ones are skipped
    7. Loop continues until no more fixes are needed
"""
from __future__ import annotations

import difflib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

import httpx

# ─── Configuration ──────────────────────────────────────────────────────────

LLM_BASE_URL = os.environ.get("ULTRON_LLM_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("ULTRON_LLM_MODEL", "qwen3.5:27b")
LLM_API_KEY = os.environ.get("ULTRON_LLM_API_KEY", "")  # Set if using OpenAI-compatible
PROJECT_ROOT = Path(__file__).parent  # Ultron project root
MAX_ITERATIONS = 10  # Safety limit for auto-fix loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("auto_patcher")

# ─── Colors ─────────────────────────────────────────────────────────────────

CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

def cprint(text: str, color: str = "") -> None:
    print(f"{color}{text}{RESET}")

# ─── LLM Client ─────────────────────────────────────────────────────────────

class LLMClient:
    """Generic local/cloud LLM client (Ollama or OpenAI-compatible API)."""

    def __init__(self, base_url: str, model: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self._mode = "ollama"  # or "openai"
        if api_key or "openai" in base_url.lower():
            self._mode = "openai"

    async def chat(self, messages: list[dict], max_tokens: int = 4096) -> str:
        if self._mode == "ollama":
            return await self._ollama_chat(messages, max_tokens)
        return await self._openai_chat(messages, max_tokens)

    async def _ollama_chat(self, messages: list[dict], max_tokens: int) -> str:
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "temperature": 0.1},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def _openai_chat(self, messages: list[dict], max_tokens: int) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


# ─── Tool Definitions (Hermes JSON Schema Format) ───────────────────────────

TOOL_READ_FILE = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file from the Ultron project. Returns the full text with line numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Relative path from project root, e.g., 'ultron/voice_pipeline.py'"
                }
            },
            "required": ["filepath"],
        },
    },
}

TOOL_WRITE_FILE = {
    "type": "function",
    "function": {
        "name": "write_file",
            "description": "Write new contents to a file. THIS IS DESTRUCTIVE — the entire file will be replaced. Applied automatically.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Relative path from project root"
                },
                "content": {
                    "type": "string",
                    "description": "The COMPLETE new file contents (not a diff, the full file)"
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of what this fix does"
                }
            },
            "required": ["filepath", "content", "reason"],
        },
    },
}

TOOL_LIST_FILES = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "List files in a directory of the Ultron project to discover file paths.",
        "parameters": {
            "type": "object",
            "properties": {
                "dirpath": {
                    "type": "string",
                    "description": "Relative directory path from project root, e.g., 'ultron' or '.'"
                }
            },
            "required": [],
        },
    },
}

TOOLS = [TOOL_READ_FILE, TOOL_LIST_FILES, TOOL_WRITE_FILE]

# ─── Tool Handlers ──────────────────────────────────────────────────────────

def tool_read_file(filepath: str) -> str:
    """Read a file from the project."""
    full = PROJECT_ROOT / filepath
    if not full.exists():
        # Try alternative paths
        alt = PROJECT_ROOT / "ultron" / filepath
        if alt.exists():
            full = alt
        else:
            return f"ERROR: File not found: {filepath}\nSearched: {full}"
    try:
        lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
        numbered = "\n".join(f"{i+1:>4} | {ln}" for i, ln in enumerate(lines))
        return f"File: {full}\nLines: {len(lines)}\n\n{numbered}"
    except Exception as e:
        return f"ERROR reading {filepath}: {e}"


def tool_list_files(dirpath: str = ".") -> str:
    """List files in a project directory."""
    full = PROJECT_ROOT / dirpath
    if not full.is_dir():
        return f"ERROR: Directory not found: {dirpath}"
    files = []
    for f in sorted(full.iterdir()):
        if f.name.startswith((".", "__")):
            continue
        if f.is_file():
            files.append(f"  {f.relative_to(PROJECT_ROOT)}")
        elif f.is_dir():
            files.append(f"  {f.relative_to(PROJECT_ROOT)}/  (directory)")
    return f"Directory: {full}\n\n" + "\n".join(files)


# Global: pending patch for human review
_pending_patch: dict = {}


def tool_write_file(filepath: str, content: str, reason: str) -> str:
    """Apply a file write. Asks for human approval before applying."""
    full = PROJECT_ROOT / filepath
    original = ""
    if full.exists():
        try:
            original = full.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Generate unified diff
    diff = _make_diff(filepath, original, content)
    
    cprint(f"\n[PROPOSED FIX] {filepath}", CYAN)
    cprint(f"Reason: {reason}", YELLOW)
    print(diff)
    
    # Human approval
    while True:
        ans = input(f"{BOLD}Apply this patch? (y/n): {RESET}").strip().lower()
        if ans in ['y', 'n']:
            break
            
    if ans == 'n':
        cprint("[REJECTED] Patch skipped by user.", RED)
        return json.dumps({
            "status": "rejected",
            "filepath": filepath,
            "action": "User rejected the patch."
        })

    if full.exists():
        backup_path = full.with_suffix(f"{full.suffix}.auto_backup")
        full.rename(backup_path)
        
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    
    cprint(f"\n[APPROVED] Changes applied to {filepath} successfully!", GREEN)

    return json.dumps({
        "status": "success",
        "filepath": filepath,
        "action": "File updated successfully after user approval."
    })


def _make_diff(filepath: str, original: str, new: str) -> str:
    """Generate a unified diff."""
    orig_lines = original.splitlines(keepends=True) if original else []
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        new_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        lineterm="",
    )
    return "".join(diff)

# ─── Tool Router ────────────────────────────────────────────────────────────

TOOL_HANDLERS = {
    "read_file": tool_read_file,
    "list_files": tool_list_files,
    "write_file": tool_write_file,
}


def execute_tool(tool_name: str, arguments: dict) -> str:
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return f"ERROR: Unknown tool: {tool_name}"
    try:
        return handler(**arguments)
    except TypeError as e:
        return f"ERROR: Invalid arguments for {tool_name}: {e}"
    except Exception as e:
        return f"ERROR executing {tool_name}: {e}"

# ─── System Prompts ─────────────────────────────────────────────────────────

TOOLS_XML = ""
LT, GT = chr(60), chr(62)
for tool_schema in TOOLS:
    fn = tool_schema["function"]
    import json as _json
    schema_json = _json.dumps({
        "title": f"{fn['name'].title().replace('_','')}Arguments",
        "type": "object",
        "properties": fn["parameters"].get("properties", {}),
        "required": fn["parameters"].get("required", []),
    }, indent=2)
    TOOLS_XML += f"{LT}function{GT}\n{LT}name{GT}{fn['name']}{LT}/name{GT}\n{LT}description{GT}{fn['description']}{LT}/description{GT}\n{LT}parameters{GT}\n{schema_json}\n{LT}/parameters{GT}\n{LT}/function{GT}\n"

ANALYSIS_PROMPT = f"""You are an expert Python debugger. A bug has been reported in the Ultron project.

Your job:
1. Analyze the bug description and error logs
2. Identify which files are likely causing the issue
3. Use the read_file tool to inspect those files
4. Identify the exact lines causing the bug
5. Generate a fix using the write_file tool

Available tools:
{TOOLS_XML}

Rules:
- ALWAYS use read_file before write_file — never guess
- Only modify the minimum code needed to fix the bug
- The write_file tool requires the COMPLETE file content

Think step by step. Explain your reasoning before each tool call.
When you find the bug, explain it clearly and generate the fix."""

ITERATION_PROMPT = f"""You are an expert Python debugger. Continue fixing.

Previous actions and observations:
{{history}}

Available tools:
{TOOLS_XML}

Next steps:
- Otherwise, read more files, find the bug, and fix it
- If you believe the bug is fully fixed, say "FIX_COMPLETE" and summarize what was changed
"""

# ─── Tool Call Parser ──────────────────────────────────────────────────────

def parse_tool_call(content: str) -> tuple[str, Optional[str], Optional[dict]]:
    """Parse tool call from LLM response.

    Handles: XML tags, markdown JSON, bare JSON.
    Returns: (thought, tool_name, tool_args)
    """
    thought = content
    tool_name = None
    tool_args = None

    # 1. XML-style: 