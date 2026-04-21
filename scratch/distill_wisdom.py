import os
import json
import sqlite3
from pathlib import Path

def collect_ultron_wisdom():
    """
    Ultron'un tum mimarisini ve ogrendigi dersleri toplar.
    Bu veriler fine-tuning icin temel teskil edecek.
    """
    wisdom_data = []
    project_root = Path("c:/Users/nemes/Desktop/Ultron")
    
    # 1. Ogrenilen Dersleri Topla (Memory Engine)
    lessons_path = project_root / "data/memory_v2/lessons.json"
    if lessons_path.exists():
        with open(lessons_path, "r", encoding="utf-8") as f:
            lessons = json.load(f)
            for lesson in lessons:
                wisdom_data.append({
                    "instruction": f"Analyze this failure and provide a fix: {lesson.get('failure')}",
                    "input": lesson.get("error", ""),
                    "output": f"Root Cause: {lesson.get('root_cause')}\nFix: {lesson.get('fix')}"
                })
    
    # 2. Ajan Yeteneklerini Topla
    agents_dir = project_root / "ultron/v2/agents"
    for agent_file in agents_dir.glob("*.py"):
        if agent_file.name == "__init__.py": continue
        with open(agent_file, "r", encoding="utf-8") as f:
            content = f.read()
            # Ajanin amacini ve docstringini yakala
            wisdom_data.append({
                "instruction": f"Explain the role and capabilities of the {agent_file.stem} agent in Ultron AGI.",
                "input": "",
                "output": content[:1000] # Baslangic kismini (docstring ve init) al
            })

    # 3. Veriyi Kaydet
    output_path = project_root / "Ultron Factory/data/ultron_train_v1.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in wisdom_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    return len(wisdom_data)

if __name__ == "__main__":
    count = collect_ultron_wisdom()
    print(f"Successfully collected {count} wisdom entries for training.")
