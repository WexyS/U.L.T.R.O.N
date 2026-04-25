import asyncio
import sys
import os
import json
from pathlib import Path

# Add root to sys.path
sys.path.append(os.getcwd())

from ultron.v2.agents.error_analyzer import ErrorAnalyzerAgent
from ultron.v2.core.llm_router import LLMRouter

async def self_audit():
    print("Ultron Self-Audit Initiation...")
    
    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
        
    # Initialize components
    llm = LLMRouter()
    llm.enable_all_providers(os.environ)
    agent = ErrorAnalyzerAgent(llm_router=llm)
    
    files_to_scan = [
        "ultron/api/main.py",
        "ultron/voice_pipeline.py",
        "ultron/v2/core/react_orchestrator.py"
    ]
    
    audit_report = {
        "timestamp": str(asyncio.get_event_loop().time()),
        "findings": []
    }
    
    for file_path in files_to_scan:
        print(f"Scanning {file_path}...")
        if not os.path.exists(file_path):
            continue
            
        content = Path(file_path).read_text(encoding="utf-8")
        
        # We simulate an 'audit' by asking the analyzer to look for vulnerabilities instead of just errors
        # We'll use a specialized prompt for this
        messages = [
            {
                "role": "system",
                "content": "You are the Ultron System Auditor. Analyze the provided code for: 1. Logic bugs 2. Security vulnerabilities 3. Performance bottlenecks 4. Missing error handling. Return findings in JSON format."
            },
            {
                "role": "user",
                "content": f"File: {file_path}\n\nCode:\n{content[:15000]}" # Limit context
            }
        ]
        
        try:
            response = await llm.chat(messages, max_tokens=1500)
            # Try to extract JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if json_match:
                finding = json.loads(json_match.group())
                finding["file"] = file_path
                audit_report["findings"].append(finding)
                print(f"DONE: Found {len(finding.get('vulnerabilities', []))} potential issues in {file_path}")
            else:
                print(f"WARN: Could not parse audit result for {file_path}")
        except Exception as e:
            print(f"ERROR: Audit failed for {file_path}: {e}")

    # Output report
    report_path = "data/audit_report.json"
    os.makedirs("data", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    
    print(f"\nAudit Report saved to {report_path}")
    return audit_report

if __name__ == "__main__":
    asyncio.run(self_audit())
