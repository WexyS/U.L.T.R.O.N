"""Ultron_Factory Fine-Tuning Integration

Ultron Neural Lab: Ultron-native LLM fine-tuning framework
- LoRA, QLoRA, full fine-tuning
- 100+ model support (Llama, Qwen, Mistral, etc.)
- Ultron Training Dashboard + CLI
- DeepSpeed, LoRA+ optimizations

Integrated by Ultron Intelligence.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class UltronNeuralTuner:
    """Ultron Neural Lab Fine-Tuning Agent
    
    Ultron için özel modeller eğit:
    - Code generation
    - Research & analysis
    - Memory management
    - Agent coordination
    """
    
    def __init__(self, Ultron_Factory_path: Optional[str] = None):
        self.Ultron_Factory_path = Path(Ultron_Factory_path) if Ultron_Factory_path else Path("Ultron_Factory")
        self.is_installed = self._check_installation()
        
        # Supported models for fine-tuning
        self.supported_models = [
            "meta-llama/Llama-3.1-8B",
            "meta-llama/Llama-3.1-70B",
            "Qwen/Qwen2.5-7B",
            "Qwen/Qwen2.5-72B",
            "mistralai/Mistral-7B-v0.3",
            "google/gemma-2-9b",
        ]
        
        # Fine-tuning methods
        self.methods = {
            "lora": {"vram": "8GB", "quality": "Good", "speed": "Fast"},
            "qlora": {"vram": "6GB", "quality": "Very Good", "speed": "Fast"},
            "full": {"vram": "80GB+", "quality": "Best", "speed": "Slow"},
        }
        
        logger.info(
            f"🧠 Ultron Neural Lab initialized\n"
            f"   Engine: {self.engine_path}\n"
            f"   Ready: {self.is_installed}\n"
            f"   Native Models: {len(self.supported_models)}"
        )
    
    def _check_installation(self) -> bool:
        """Ultron_Factory kurulu mu kontrol et"""
        if not self.Ultron_Factory_path.exists():
            logger.warning(f"Ultron_Factory not found at {self.Ultron_Factory_path}")
            return False
        
        # Check if Ultron_Factory CLI exists
        cli_path = self.Ultron_Factory_path / "src" / "Ultron_Factory"
        if not cli_path.exists():
            logger.warning("Ultron_Factory src not found")
            return False
        
        return True
    
    async def install(self) -> bool:
        """Ultron_Factory'yi kur"""
        logger.info("📥 Installing Ultron_Factory...")
        
        try:
            # Clone repository
            if not self.Ultron_Factory_path.exists():
                logger.info("Cloning Ultron_Factory repository...")
                subprocess.run(
                    ["git", "clone", "https://github.com/hiyouga/Ultron_Factory.git", str(self.Ultron_Factory_path)],
                    check=True
                )
            
            # Install dependencies
            logger.info("Installing dependencies...")
            subprocess.run(
                ["pip", "install", "-e", str(self.Ultron_Factory_path), "-q"],
                check=True
            )
            
            self.is_installed = True
            logger.info("✅ Ultron_Factory installed successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Installation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False
    
    async def prepare_dataset(
        self,
        conversations: List[Dict[str, str]],
        output_file: str = "data/ultron_training.json"
    ) -> bool:
        """Training dataset hazırla
        
        Args:
            conversations: [
                {
                    "instruction": "Write a Python function to...",
                    "input": "",
                    "output": "def function()..."
                }
            ]
            output_file: Output JSON file path
        
        Returns:
            bool: Success
        """
        logger.info(f"📝 Preparing dataset with {len(conversations)} conversations...")
        
        try:
            # Convert to Ultron_Factory format
            dataset = []
            for conv in conversations:
                dataset.append({
                    "instruction": conv.get("instruction", ""),
                    "input": conv.get("input", ""),
                    "output": conv.get("output", ""),
                    "system": conv.get("system", "You are Ultron, an advanced AI assistant.")
                })
            
            # Save to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Dataset saved to {output_path} ({len(dataset)} examples)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Dataset preparation failed: {e}")
            return False
    
    async def fine_tune(
        self,
        base_model: str = "meta-llama/Llama-3.1-8B",
        dataset: str = "data/ultron_training.json",
        method: str = "qlora",
        output_dir: str = "output/ultron_model",
        num_epochs: int = 3,
        learning_rate: float = 2e-4,
        batch_size: int = 4,
        use_deepspeed: bool = False
    ) -> bool:
        """
        Model fine-tune et
        
        Args:
            base_model: Base model name
            dataset: Training dataset JSON file
            method: Fine-tuning method (lora, qlora, full)
            output_dir: Output directory for fine-tuned model
            num_epochs: Number of training epochs
            learning_rate: Learning rate
            batch_size: Training batch size
            use_deepspeed: Use DeepSpeed for multi-GPU
        
        Returns:
            bool: Success
        """
        if not self.is_installed:
            logger.error("❌ Ultron_Factory not installed! Run install() first.")
            return False
        
        if base_model not in self.supported_models:
            logger.warning(f"⚠️ Model {base_model} not in supported models list")
            logger.warning(f"   Supported: {self.supported_models}")
        
        logger.info(f"🚀 Starting fine-tuning:")
        logger.info(f"   Base model: {base_model}")
        logger.info(f"   Dataset: {dataset}")
        logger.info(f"   Method: {method}")
        logger.info(f"   Epochs: {num_epochs}")
        logger.info(f"   LR: {learning_rate}")
        logger.info(f"   Batch size: {batch_size}")
        
        # Build training command
        cmd = [
            "Ultron_Factory-cli", "train",
            "--model_name_or_path", base_model,
            "--dataset", dataset,
            "--output_dir", output_dir,
            "--finetuning_type", method,
            "--num_train_epochs", str(num_epochs),
            "--learning_rate", str(learning_rate),
            "--per_device_train_batch_size", str(batch_size),
            "--template", "llama3",
            "--cutoff_len", "2048",
        ]
        
        # LoRA specific parameters
        if method in ["lora", "qlora"]:
            cmd.extend([
                "--lora_rank", "8",
                "--lora_alpha", "16",
                "--lora_dropout", "0.1",
            ])
        
        # QLoRA specific
        if method == "qlora":
            cmd.append("--quantization_bit")
            cmd.append("4")
        
        # DeepSpeed
        if use_deepspeed:
            cmd.extend([
                "--deepspeed", "ds_z3_config.json",
            ])
        
        logger.info(f"📋 Training command: {' '.join(cmd)}")
        
        try:
            # Run training
            subprocess.run(cmd, check=True)
            
            logger.info(f"✅ Fine-tuning completed!")
            logger.info(f"   Model saved to: {output_dir}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Training failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False
    
    async def export_model(
        self,
        model_path: str,
        export_dir: str = "output/exported_model"
    ) -> bool:
        """Fine-tuned modeli export et (GGUF, ONNX, vb.)"""
        logger.info(f"📦 Exporting model from {model_path}...")
        
        try:
            cmd = [
                "Ultron_Factory-cli", "export",
                "--model_name_or_path", model_path,
                "--export_dir", export_dir,
                "--export_size", "2",
                "--export_quantization_bit", "4",
            ]
            
            subprocess.run(cmd, check=True)
            
            logger.info(f"✅ Model exported to {export_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Export failed: {e}")
            return False
    
    async def launch_training_dashboard(self) -> bool:
        """Ultron Training Dashboard (Web UI) başlat"""
        logger.info("🌐 Launching Ultron Neural Lab Dashboard...")
        
        try:
            subprocess.Popen(
                ["Ultron_Factory-cli", "webui"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            logger.info("✅ Web UI launched at http://localhost:7860")
            return True
            
        except Exception as e:
            logger.error(f"❌ Web UI launch failed: {e}")
            return False
    
    def get_training_template(
        self,
        task_type: str = "code_generation"
    ) -> Dict[str, Any]:
        """Görev tipine göre training template al
        
        Args:
            task_type: code_generation, research, chat, agent
        
        Returns:
            dict: Training configuration
        """
        templates = {
            "code_generation": {
                "base_model": "Qwen/Qwen2.5-7B",
                "method": "qlora",
                "epochs": 5,
                "lr": 2e-4,
                "batch_size": 4,
                "template": "qwen",
                "description": "Code generation and debugging"
            },
            "research": {
                "base_model": "meta-llama/Llama-3.1-8B",
                "method": "qlora",
                "epochs": 3,
                "lr": 1e-4,
                "batch_size": 8,
                "template": "llama3",
                "description": "Research and analysis"
            },
            "chat": {
                "base_model": "meta-llama/Llama-3.1-8B",
                "method": "qlora",
                "epochs": 3,
                "lr": 2e-4,
                "batch_size": 4,
                "template": "llama3",
                "description": "Conversational AI"
            },
            "agent": {
                "base_model": "Qwen/Qwen2.5-72B",
                "method": "lora",
                "epochs": 2,
                "lr": 1e-4,
                "batch_size": 2,
                "template": "qwen",
                "description": "Agent coordination"
            },
        }
        
        return templates.get(task_type, templates["chat"])


# ─── Ultron Integration ───────────────────────────────────────────────

async def setup_ultron_factory() -> UltronNeuralTuner:
    """Ultron_Factory'yi kur ve hazır hale getir"""
    tuner = UltronNeuralTuner()
    
    if not tuner.is_installed:
        logger.info("📦 Ultron Engine not installed, initializing native setup...")
        success = await tuner.install()
        
        if not success:
            logger.error("❌ Ultron_Factory initialization failed!")
            return None
    
    return tuner
