import json
import os
from pathlib import Path

def clean_and_merge():
    print("[+] Cleaning and Merging all datasets for Ultron AGI...")
    
    root_dir = Path(__file__).parent.parent.parent
    raw_file = root_dir / "data" / "training" / "alpaca_full_raw.json"
    master_file = root_dir / "data" / "training" / "master_intelligence.json"
    harvested_file = root_dir / "data" / "training" / "harvested_sft.json"
    output_file = root_dir / "Ultron Factory" / "data" / "ultron_mega_dataset.json"

    merged_data = []

    # 1. Load Master Intelligence (Eren's Protocols) - High Priority
    if master_file.exists():
        with open(master_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged_data.extend(data)
            print(f"[+] Added {len(data)} Master Intelligence samples.")

    # 2. Load Harvested Data (Self-improvement traces)
    if harvested_file.exists():
        with open(harvested_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged_data.extend(data)
            print(f"[+] Added {len(data)} Harvested samples.")

    # 3. Load and Clean Alpaca Data (The 52k dataset)
    if raw_file.exists():
        try:
            with open(raw_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Find the first '[' and last ']'
                start = content.find("[")
                end = content.rfind("]") + 1
                if start != -1 and end != -1:
                    json_str = content[start:end]
                    # Fix common malformations if any
                    alpaca_data = json.loads(json_str)
                    merged_data.extend(alpaca_data)
                    print(f"[+] Added {len(alpaca_data)} Alpaca samples.")
        except Exception as e:
            print(f"[!] Error processing Alpaca data: {e}")

    # 4. Save Mega Dataset
    os.makedirs(output_file.parent, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Mega dataset created with {len(merged_data)} total samples!")
    print(f"[Location] {output_file}")

if __name__ == "__main__":
    clean_and_merge()
