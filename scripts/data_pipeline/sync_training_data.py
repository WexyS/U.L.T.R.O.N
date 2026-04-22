import json
import os
import shutil
from pathlib import Path

def sync_data():
    print("[+] Ultron Training Data Syncing...")
    
    # 1. Paths
    root_dir = Path(__file__).parent.parent.parent
    harvested_file = root_dir / "data" / "training" / "harvested_sft.json"
    master_file = root_dir / "data" / "training" / "master_intelligence.json"
    factory_data_dir = root_dir / "Ultron Factory" / "data"
    factory_dataset_info = factory_data_dir / "dataset_info.json"
    
    if not harvested_file.exists():
        print(f"[!] Warning: {harvested_file} not found. Skipping sync.")
        return

    # 2. Copy data to factory
    if harvested_file.exists():
        shutil.copy2(harvested_file, factory_data_dir / "ultron_harvested.json")
        print("[+] Harvested data synced.")
    
    if master_file.exists():
        shutil.copy2(master_file, factory_data_dir / "ultron_master.json")
        print("[+] Master intelligence data synced.")

    # 3. Update dataset_info.json
    try:
        with open(factory_dataset_info, "r", encoding="utf-8") as f:
            info = json.load(f)
        
        info["ultron_mega"] = {
            "file_name": "ultron_mega_dataset.json",
            "columns": {"prompt": "instruction", "query": "input", "response": "output"}
        }
        
        with open(factory_dataset_info, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        
        print("[+] dataset_info.json updated successfully.")
    except Exception as e:
        print(f"[!] Error updating dataset_info.json: {e}")

if __name__ == "__main__":
    sync_data()
