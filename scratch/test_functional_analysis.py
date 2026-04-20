import asyncio
import logging
import os
from pathlib import Path
from ultron.v2.agents.researcher import ResearcherAgent
from ultron.v2.core.llm_router import LLMRouter
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.types import Task

logging.basicConfig(level=logging.INFO)

async def test_functional_architect():
    # 1. Setup
    llm = LLMRouter()
    llm.enable_all_providers(dict(os.environ))
    bus = EventBus()
    bb = Blackboard()
    
    agent = ResearcherAgent(llm, bus, bb)
    
    # 2. Test URL (using a simple public site with forms, e.g., google.com or a dummy one)
    # For testing, we'll use a known site with a search form
    test_url = "https://www.google.com" 
    print(f"\n[TEST] Analysing {test_url} for visual AND functional elements...")
    
    task = Task(
        description=f"Clone this site: {test_url}",
        intent="architect"
    )
    
    result = await agent.execute(task)
    
    print("\n[RESULT] Output Summary:")
    print(result.output)
    
    if result.context.get("visual_data"):
        vd = result.context["visual_data"]
        print("\n[DATA] Extracted Functional Elements:")
        for el in vd.get("interactive_elements", []):
            print(f" - {el}")
            
        if vd.get("interactive_elements"):
            print("\n✅ SUCCESS: Functional elements detected!")
        else:
            print("\n⚠️ WARNING: No functional elements detected (might be a very simple site).")
            
    else:
        print("\n❌ FAILED: No visual_data returned.")

if __name__ == "__main__":
    asyncio.run(test_functional_architect())
