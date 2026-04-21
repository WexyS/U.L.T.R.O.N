
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ultron.v2.core.llm_router import LLMRouter

async def test_all_keys():
    load_dotenv()
    
    print("=== Ultron API Key Connectivity Test ===")
    
    router = LLMRouter()
    # Enable all providers from environment
    router.enable_all_providers(dict(os.environ))
    
    available = router.priority_order
    print(f"Detected providers in priority: {available}")
    print("-" * 40)
    
    results = {}
    
    for name in available:
        print(f"Testing provider: {name}...")
        try:
            # Use LLMRouter.chat with preferred_provider to test specific ones
            messages = [{"role": "user", "content": "hi"}]
            response = await asyncio.wait_for(
                router.chat(messages, preferred_provider=name),
                timeout=20
            )
            print(f"  [OK] Response received from {name}: {response.content[:50]}...")
            results[name] = "OK"
        except Exception as e:
            print(f"  [FAIL] {name} failed ({type(e).__name__}): {e}")
            results[name] = f"FAIL ({type(e).__name__}): {str(e)[:100]}"
            
    print("-" * 40)
    print("Summary:")
    for name, res in results.items():
        print(f"  {name:15}: {res}")

if __name__ == "__main__":
    asyncio.run(test_all_keys())
