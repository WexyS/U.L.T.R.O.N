"""
Test script for LangGraph-based CoderAgent self-healing loop.

Run this to test the new graph-based implementation.
"""

import asyncio
from ultron.agents.coder_langgraph import run_coder_self_healing
from ultron.core.llm_router import LLMRouter
from ultron.memory.engine import MemoryEngine
from ultron.core.types import Task


async def test_langgraph_coder():
    """Test the LangGraph implementation with a simple task."""

    # Initialize dependencies (mock/minimal setup for testing)
    llm_router = LLMRouter()  # Will use default Ollama
    memory = MemoryEngine()  # Minimal memory setup

    # Create a test task that will likely fail initially
    task = Task(
        description="Write a Python function that calculates the factorial of a number, but make it have a bug",
        intent="code",
        context={
            "language": "python",
            "execute": True,
            "llm_router": llm_router,
            "work_dir": "./workspace"
        }
    )

    print("🧪 Testing LangGraph-based CoderAgent self-healing loop...")
    print(f"Task: {task.description}")

    # Run the graph
    result = await run_coder_self_healing(task, llm_router, memory, max_iterations=3)

    print("
📊 Result:"    print(f"Status: {result.status}")
    print(f"Iterations: {result.metadata.get('heal_iterations', 0)}")

    if result.status.name == "SUCCESS":
        print("✅ Code generation successful!")
        print(f"Generated code:\n{result.output}")
    else:
        print("❌ Code generation failed after max attempts")
        print(f"Error: {result.error}")
        if result.output:
            print(f"Final code attempt:\n{result.output}")


if __name__ == "__main__":
    asyncio.run(test_langgraph_coder())
