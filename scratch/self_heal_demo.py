import asyncio
import sys
import os
import hmac
from pathlib import Path

# Add root to sys.path
sys.path.append(os.getcwd())

from ultron.agents.error_analyzer import ErrorAnalyzerAgent
from ultron.core.llm_router import LLMRouter

async def self_heal_demo():
    print("Self-Healing Initiation: Fixing Security Vulnerability (Timing Attack in API)...")
    
    llm = LLMRouter()
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    llm.enable_all_providers(os.environ)
    
    agent = ErrorAnalyzerAgent(llm_router=llm)
    
    target_file = "ultron/api/main.py"
    if not os.path.exists(target_file):
        print(f"Error: {target_file} not found")
        return

    content = Path(target_file).read_text(encoding="utf-8")
    
    # We provide the specific finding to the agent and ask it to generate a fix
    print("Generating secure code patch...")
    messages = [
        {
            "role": "system",
            "content": "You are the Ultron Self-Healing Agent. Your goal is to fix the 'Timing Attack' vulnerability in the verify_api_key function in main.py. Use hmac.compare_digest for secure comparison. Return only the full fixed code for the entire file."
        },
        {
            "role": "user",
            "content": f"Original Code:\n{content[:15000]}" # Limit context
        }
    ]
    
    try:
        response = await llm.chat(messages, max_tokens=2048)
        # Extract code
        import re
        code_match = re.search(r'```(?:python)?\n([\s\S]*?)```', response.content)
        fixed_code = code_match.group(1).strip() if code_match else response.content.strip()
        
        if "compare_digest" in fixed_code:
            print("Patch generated successfully with security enhancements.")
            # Apply fix
            Path(target_file).write_text(fixed_code, encoding="utf-8")
            print(f"SUCCESS: {target_file} has been autonomously patched and secured.")
        else:
            print("FAIL: Generated patch did not include the required security fix.")
            
    except Exception as e:
        print(f"Error during self-healing: {e}")

if __name__ == "__main__":
    asyncio.run(self_heal_demo())
