
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def check_ollama():
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.getenv("ULTRON_MODEL", "qwen2.5:14b")
    
    print(f"Checking Ollama at {base_url}...")
    
    # 1. HTTP Check
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                print("[OK] Ollama HTTP API is accessible.")
                models = [m["name"] for m in resp.json().get("models", [])]
                print(f"Available models: {models}")
                if model in models:
                    print(f"[OK] Model '{model}' is available.")
                else:
                    # Check for partial matches
                    matches = [m for m in models if model.split(':')[0] in m]
                    if matches:
                        print(f"[?] Model '{model}' not found exactly, but similar models found: {matches}")
                    else:
                        print(f"[FAIL] Model '{model}' is NOT found in Ollama.")
            else:
                print(f"[FAIL] Ollama HTTP API returned status {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] Failed to connect to Ollama HTTP API: {e}")

    # 2. Python Package Check
    try:
        import ollama
        print("[OK] 'ollama' python package is installed.")
        client = ollama.AsyncClient(host=base_url)
        # Try a simple chat if possible
        print(f"Testing chat with {model}...")
        try:
            response = await asyncio.wait_for(
                client.chat(model=model, messages=[{'role': 'user', 'content': 'hi'}]),
                timeout=10
            )
            print("[OK] Ollama chat test successful.")
        except Exception as e:
            print(f"[FAIL] Ollama chat test failed: {e}")
    except ImportError:
        print("[FAIL] 'ollama' python package is NOT installed.")

if __name__ == "__main__":
    asyncio.run(check_ollama())
