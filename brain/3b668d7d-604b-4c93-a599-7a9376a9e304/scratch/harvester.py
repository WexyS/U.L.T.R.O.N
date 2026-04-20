import os
import shutil
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Harvester")

# Target directories
SKILLS_DIR = Path("C:/Users/nemes/.qwen/skills")
AGENTS_DIR = Path("C:/Users/nemes/.qwen/agents")
TEMP_DIR = Path("./data/temp_harvester")

# Sources to harvest
SOURCES = [
    {
        "url": "https://github.com/WexyS/superpowers",
        "type": "mixed",
        "branch": "main"
    },
    {
        "url": "https://github.com/WexyS/marketing-skills",
        "type": "skill",
        "branch": "main"
    },
    {
        "url": "https://github.com/microsoft/skills",
        "type": "skill",
        "branch": "main"
    }
]

def ensure_dirs():
    import stat
    def on_rm_error(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, onerror=on_rm_error)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

def clone_repo(url, target_path):
    logger.info(f"Cloning {url}...")
    try:
        subprocess.run(["git", "clone", "--depth", "1", url, str(target_path)], check=True, capture_output=True)
        return True
    except Exception as e:
        logger.error(f"Failed to clone {url}: {e}")
        return False

def harvest_content(repo_path, source_type):
    skill_count = 0
    agent_count = 0
    
    # Look for .md files
    for md_file in repo_path.rglob("*.md"):
        if md_file.name == "README.md" or md_file.name == "CONTRIBUTING.md":
            continue
            
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            
            # Heuristic for Agent
            if "# Agent" in content or "AGENT.md" in md_file.name:
                target_name = f"harvested_{md_file.stem}_{agent_count}.md"
                shutil.copy(md_file, AGENTS_DIR / target_name)
                agent_count += 1
            # Heuristic for Skill
            elif "# Skill" in content or "SKILL.md" in md_file.name or "description:" in content.lower():
                target_name = f"harvested_{md_file.stem}_{skill_count}.md"
                shutil.copy(md_file, SKILLS_DIR / target_name)
                skill_count += 1
        except Exception:
            continue
    return skill_count, agent_count

def run():
    ensure_dirs()
    total_skills = 0
    total_agents = 0
    
    for source in SOURCES:
        repo_name = source["url"].split("/")[-1]
        repo_path = TEMP_DIR / repo_name
        
        if clone_repo(source["url"], repo_path):
            s_count, a_count = harvest_content(repo_path, source["type"])
            logger.info(f"Harvested {s_count} skills and {a_count} agents from {repo_name}")
            total_skills += s_count
            total_agents += a_count
                
    logger.info(f"TOTAL HARVESTED: {total_skills} skills, {total_agents} agents.")
    
    # Clean up
    # shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    run()
