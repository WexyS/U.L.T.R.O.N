
import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath("."))

async def test_reasoning():
    try:
        from ultron.v2.core.reasoning_engine import ReasoningEngine
        engine = ReasoningEngine(router=None)
        print(f"ReasoningEngine class: {ReasoningEngine}")
        print(f"Methods: {dir(engine)}")
        if hasattr(engine, "reason"):
            print("SUCCESS: reason method found")
        else:
            print("FAILURE: reason method NOT found")
            
        if hasattr(engine, "think_and_answer"):
            print("SUCCESS: think_and_answer method found")
        else:
            print("FAILURE: think_and_answer method NOT found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_reasoning())
