import time
import subprocess
import os
import sys
from pathlib import Path

def monitor_training():
    print("[+] Ultron Training Watchdog ACTIVE.")
    print("[+] Monitoring 'ultron_brain_v1' evolution...")
    
    log_file = Path(r"Ultron Factory/saves/Qwen2.5-14B/lora/ultron_brain_v1/trainer_log.jsonl")
    train_cmd = [
        r".venv\Scripts\python.exe", "-m", "ultronfactory.cli", "train", 
        "examples/train_lora/ultron_quick_train.yaml"
    ]
    cwd = Path(r"c:\Users\nemes\Desktop\Ultron\Ultron Factory")

    last_step = 0
    fail_count = 0

    while True:
        try:
            # Check if training process is still alive
            # (In a real scenario, we'd check the PID, but here we monitor the log growth)
            if log_file.exists():
                with open(log_file, "r") as f:
                    lines = f.readlines()
                    if lines:
                        import json
                        last_log = json.loads(lines[-1])
                        current_step = last_log.get("current_steps", 0)
                        
                        if current_step > last_step:
                            print(f"[WATCHDOG] Progress detected: Step {current_step}/{last_log['total_steps']} - Loss: {last_log['loss']}")
                            last_step = current_step
                            fail_count = 0
                        else:
                            fail_count += 1
            
            if fail_count > 10: # No progress for ~5 minutes
                print("[!] CRITICAL: Training seems stalled. Restarting...")
                subprocess.Popen(train_cmd, cwd=cwd)
                fail_count = 0
                time.sleep(60) # Give it time to start

            time.sleep(30) # Poll every 30 seconds
            
        except Exception as e:
            print(f"[!] Watchdog Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_training()
