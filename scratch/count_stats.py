import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ultron.v2.core.agent_registry import registry
from ultron.v2.core.skill_manager import discover_all_skills, discover_all_agents
import ultron.v2.agents as agents_pkg

def count_resources():
    # 1. Registered Core Agents
    core_agents_count = len(agents_pkg.__all__) - 1 # Subtract "Agent" base class
    
    # 2. Discovered External Agents
    external_agents = discover_all_agents()
    external_agents_count = len(external_agents)
    
    # 3. Discovered Skills
    skills = discover_all_skills()
    skills_count = len(skills)
    
    print(f"Core Agents: {core_agents_count}")
    print(f"External Agents: {external_agents_count}")
    print(f"Total Skills: {skills_count}")

if __name__ == "__main__":
    count_resources()
