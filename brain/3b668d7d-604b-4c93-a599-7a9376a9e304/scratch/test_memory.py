import asyncio
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    try:
        from ultron.v2.memory.engine import MemoryEngine
        
        print("Initializing MemoryEngine...")
        engine = MemoryEngine(persist_dir="./data/test_memory_v2")
        
        print("Testing basic async store...")
        engine.store("test_1", "Ultron is an advanced AI system.", metadata={"topic": "identity"})
        engine.store("test_2", "Ultron was created to automate tasks.", metadata={"topic": "purpose"})
        
        print("Waiting for pending tasks...")
        await engine.wait_pending_tasks()
        
        print("Testing cache and search...")
        res1 = engine.search("Who is Ultron?", limit=2)
        print(f"Search 1 results: {len(res1)}")
        
        res2 = engine.search("Who is Ultron?", limit=2)
        stats = engine.get_cache_stats()
        print(f"Cache stats after search: {stats}")
        
        print("Testing knowledge graph...")
        engine.add_concept("Ultron", "Advanced AI", category="AI")
        engine.add_concept("Automation", "Task execution", category="Function")
        engine.add_relationship("Ultron", "Automation", "performs")
        
        graph_res = engine.query_graph("Ultron", max_depth=1)
        print(f"Graph nodes: {len(graph_res.get('nodes', {}))}")
        
        print("Testing store_lesson (Self-Learning Loop)...")
        engine.store_lesson(
            failure_description="Failed to parse user input correctly.",
            error_details="KeyError: 'intent'",
            root_cause="Intent classifier returned None.",
            fix_applied="Added default intent fallback.",
            domain="core"
        )
        
        lessons = engine.get_relevant_lessons("intent classifier failure")
        print(f"Relevant lessons found: {len(lessons)}")
        if lessons:
            print(f"Lesson ID: {lessons[0]['id']}, Domain: {lessons[0]['domain']}")
            
        print("Clearing test memory...")
        engine.clear_all()
        print("Test complete.")
        
    except Exception as e:
        print(f"MemoryEngine test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
