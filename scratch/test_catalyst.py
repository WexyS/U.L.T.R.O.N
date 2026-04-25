import asyncio
import os
import sys
from datetime import datetime

# Add root to sys.path
sys.path.append(os.getcwd())

from ultron.v2.core.llm_router import LLMRouter
from ultron.v2.agents.swarm_catalyst import SwarmCatalyst
from ultron.v2.core.base_agent import AgentTask

async def test_swarm_catalyst():
    print("--- Swarm Catalyst Autonomous Test ---")
    
    # Initialize LLM
    llm = LLMRouter()
    llm.enable_all_providers(os.environ)
    
    # Initialize Catalyst
    catalyst = SwarmCatalyst(llm_router=llm)
    
    print("\n[1] Phase: Brainstorming & Vision Generation...")
    task = AgentTask(
        task_type="catalyze",
        input_data="autonomous_evolution",
        context={
            "system_stats": {"status": "stable", "vram": "healthy"},
            "recent_events": ["Added VoiceBox integration", "Implemented Security Audit"]
        }
    )
    
    response = await catalyst.execute(task)
    
    if response.success:
        print("\n[SUCCESS] Catalyst Vision Received:")
        print(f"Vision: {response.output.get('vision')}")
        print(f"Rationale: {response.output.get('rationale')}")
        print(f"Agents Needed: {', '.join(response.output.get('agents_needed', []))}")
        print(f"Initial Steps: {response.output.get('initial_steps', [])}")
        
        # Test Debate Feature
        print("\n[2] Phase: Multi-Agent Debate Simulation...")
        debate_topic = f"Should we implement: {response.output.get('vision')}?"
        # Mocking debate since other agents need full env
        print(f"Topic: {debate_topic}")
        print("Catalyst is now analyzing internal knowledge to decide...")
        
        final_decision = await llm.chat([
            {"role": "system", "content": "You are the Swarm Catalyst. Synthesize a decision for this topic."},
            {"role": "user", "content": debate_topic}
        ])
        print(f"\nFinal Catalyst Decision: {final_decision.content[:200]}...")
    else:
        print(f"\n[FAILURE] Catalyst Error: {response.error}")

if __name__ == "__main__":
    asyncio.run(test_swarm_catalyst())
