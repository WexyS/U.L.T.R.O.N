import os
import requests
from pathlib import Path

def fetch_datasets():
    print("[+] Starting Massive Data Harvesting (Goal: 500,000+ samples)...")
    
    # Target directory
    root_dir = Path(__file__).parent.parent.parent
    data_dir = root_dir / "data" / "training" / "mega_pool"
    os.makedirs(data_dir, exist_ok=True)
    
    # High-quality dataset URLs (JSON/JSONL formats)
    # These are just a few starters to hit that 500k mark
    datasets = [
        {
            "name": "open_hermes_2.5",
            "url": "https://huggingface.co/datasets/teknium/OpenHermes-2.5/resolve/main/openhermes2_5.json",
            "description": "1 million high-quality multi-turn conversations and logic samples."
        },
        {
            "name": "wizard_lm_evol_instruct",
            "url": "https://huggingface.co/datasets/WizardLMTeam/WizardLM_evol_instruct_V2_196k/resolve/main/WizardLM_evol_instruct_V2_143k.json",
            "description": "143k highly complex instruction following data."
        },
        {
            "name": "evol_instruct_code",
            "url": "https://huggingface.co/datasets/nickrosh/Evol-Instruct-Code-80k-v1/resolve/main/Evol-Instruct-Code-80k.json",
            "description": "80k high-quality coding instructions."
        },
        {
            "name": "code_feedback",
            "url": "https://huggingface.co/datasets/m-a-p/CodeFeedback-Filtered-Instruction/resolve/main/data/train-00000-of-00001.parquet",
            "description": "Massive high-quality coding feedback data."
        },
        {
            "name": "sharegpt_deep_clean",
            "url": "https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json",
            "description": "Thousands of long, complex human-AI conversations."
        }
    ]
    
    for ds in datasets:
        target_path = data_dir / f"{ds['name']}.json"
        if target_path.exists():
            print(f"[-] {ds['name']} already exists. Skipping.")
            continue
            
        print(f"[+] Downloading {ds['name']} ({ds['description']})...")
        try:
            # Note: We use stream for large files
            with requests.get(ds['url'], stream=True) as r:
                r.raise_for_status()
                with open(target_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"[SUCCESS] {ds['name']} downloaded.")
        except Exception as e:
            print(f"[!] Error downloading {ds['name']}: {e}")

if __name__ == "__main__":
    fetch_datasets()
