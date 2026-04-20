"""Skill & Agent Manager — Discovery, validation, and registration."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _extra_skill_search_dirs() -> list[Path]:
    """OpenClaw / ClawHub tarzı ek dizinler: workspace, data, env."""
    extra: list[Path] = []
    raw = (os.environ.get("ULTRON_SKILLS_PATH") or "").strip()
    if raw:
        for part in raw.split(os.pathsep):
            p = Path(part.strip()).expanduser()
            if p.parts:
                extra.append(p)
    here = Path(__file__).resolve()
    project_root = here.parent.parent.parent.parent
    extra.extend(
        [
            project_root / "workspace" / "skills",
            project_root / "data" / "openclaw_skills",
            project_root / "skills",
        ]
    )
    return extra


def _skills_from_manifest(manifest_path: Path) -> list[dict]:
    """JSON manifest: [{"name": "...", "path": "...", "description": "..."}, ...]"""
    out: list[dict] = []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        logger.warning("Skill manifest okunamadı %s: %s", manifest_path, e)
        return out
    if not isinstance(data, list):
        return out
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("id")
        path = item.get("path") or item.get("dir")
        if not name or not path:
            continue
        p = Path(str(path)).expanduser()
        out.append(
            {
                "name": str(name),
                "description": str(item.get("description", item.get("summary", "")))[:500],
                "path": str(p),
                "source": f"manifest:{manifest_path.name}",
            }
        )
    return out


def discover_all_skills() -> list[dict]:
    """Discover all skills from all known directories."""
    skills = []
    search_dirs = [
        Path.home() / ".qwen" / "skills",
        Path(__file__).parent.parent.parent / "skills",
        Path(__file__).parent.parent / "skills",
        *_extra_skill_search_dirs(),
    ]

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        
        # Use rglob to find all SKILL.md files at any depth
        for skill_md in search_dir.rglob("SKILL.md"):
            try:
                item = skill_md.parent
                content = skill_md.read_text(encoding="utf-8", errors="replace")
                # Extract description (first 200 chars or first line)
                desc = content.split('\n')[0].replace('# Skill:', '').strip() if content.startswith('# Skill:') else content[:200].strip()
                
                skills.append({
                    "name": item.name,
                    "description": f"Skill: {item.name}. {desc}",
                    "path": str(item),
                    "source": str(search_dir),
                })
            except Exception as e:
                logger.debug("Failed to read skill %s: %s", skill_md, e)
        
        # Also check for direct .md files (non-recursive for simple files)
        for item in search_dir.glob("*.md"):
            if item.name == "SKILL.md" or item.name.startswith("."):
                continue
            try:
                content = item.read_text(encoding="utf-8", errors="replace")
                desc = content[:200].strip()
                skills.append({
                    "name": item.stem,
                    "description": f"Skill: {item.stem}. {desc}",
                    "path": str(item),
                    "source": str(search_dir),
                })
            except Exception as e:
                logger.debug("Failed to read skill file %s: %s", item.name, e)

    manifest = (os.environ.get("ULTRON_SKILLS_MANIFEST") or "").strip()
    if manifest:
        mp = Path(manifest).expanduser()
        if mp.is_file():
            for s in _skills_from_manifest(mp):
                if s["name"] not in {x["name"] for x in skills}:
                    skills.append(s)

    return skills


def _extra_agent_search_dirs() -> list[Path]:
    extra: list[Path] = []
    raw = (os.environ.get("ULTRON_AGENTS_PATH") or "").strip()
    if raw:
        for part in raw.split(os.pathsep):
            p = Path(part.strip()).expanduser()
            if p.parts:
                extra.append(p)
    here = Path(__file__).resolve()
    root = here.parent.parent.parent.parent
    extra.extend([root / "workspace" / "agents", root / "data" / "openclaw_agents"])
    return extra


def discover_all_agents() -> list[dict]:
    """Discover all agents from all known directories."""
    agents = []
    search_dirs = [
        Path.home() / ".qwen" / "agents",
        Path(__file__).parent.parent.parent / "agents",
        Path(__file__).parent.parent / "agents",
        *_extra_agent_search_dirs(),
    ]

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for item in sorted(search_dir.iterdir()):
            # Check for AGENT.md, agent.json, config.json, README.md in directories
            if item.is_dir() and not item.name.startswith("."):
                for config_name in ["AGENT.md", "agent.json", "config.json", "README.md"]:
                    config_file = item / config_name
                    if config_file.exists():
                        try:
                            content = config_file.read_text(encoding="utf-8", errors="replace")
                            desc = content[:200].strip()
                            agents.append({
                                "name": item.name,
                                "description": f"Agent: {item.name}. {desc}",
                                "path": str(item),
                                "source": str(search_dir),
                            })
                        except Exception as e:
                            logger.debug("Failed to read agent %s: %s", item.name, e)
                        break
            # Check for .md files directly (e.g., accessibility-tester.md)
            elif item.is_file() and item.suffix == ".md" and not item.name.startswith("."):
                try:
                    content = item.read_text(encoding="utf-8", errors="replace")
                    desc = content[:200].strip()
                    agents.append({
                        "name": item.stem,
                        "description": f"Agent: {item.stem}. {desc}",
                        "path": str(item),
                        "source": str(search_dir),
                    })
                except Exception as e:
                    logger.debug("Failed to read agent file %s: %s", item.name, e)

    return agents


def get_skill_summary(skills: list[dict]) -> str:
    """Generate a readable summary of all discovered skills."""
    if not skills:
        return "No skills discovered."

    lines = [f"📚 Discovered {len(skills)} skills:"]
    for i, skill in enumerate(skills[:20], 1):
        name = skill["name"]
        source = Path(skill["source"]).name
        lines.append(f"  {i}. {name} (from {source})")

    if len(skills) > 20:
        lines.append(f"  ... and {len(skills) - 20} more")

    return "\n".join(lines)


def get_agent_summary(agents: list[dict]) -> str:
    """Generate a readable summary of all discovered agents."""
    if not agents:
        return "No agents discovered."

    lines = [f"🤖 Discovered {len(agents)} agents:"]
    for i, agent in enumerate(agents[:20], 1):
        name = agent["name"]
        source = Path(agent["source"]).name
        lines.append(f"  {i}. {name} (from {source})")

    if len(agents) > 20:
        lines.append(f"  ... and {len(agents) - 20} more")

    return "\n".join(lines)
