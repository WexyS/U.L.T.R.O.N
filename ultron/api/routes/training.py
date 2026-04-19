"""LlamaFactory Fine-Tuning API Routes

Endpoints for managing fine-tuning jobs:
- GET /api/v2/training/status - Get training status
- POST /api/v2/training/start - Start a training job
- POST /api/v2/training/stop - Stop a training job
- GET /api/v2/training/jobs - List all training jobs
- GET /api/v2/training/jobs/{job_id} - Get job details
- POST /api/v2/training/export - Export trained model
- GET /api/v2/training/models - List available models
"""

import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/training", tags=["training"])

# In-memory job storage
training_jobs: Dict[str, Dict[str, Any]] = {}
active_process: Optional[subprocess.Popen] = None


class TrainingStartRequest(BaseModel):
    base_model: str = "meta-llama/Llama-3.1-8B"
    dataset: str = "data/ultron_training.json"
    method: str = "qlora"  # lora, qlora, full
    output_dir: str = "output/ultron_model"
    num_epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 4
    use_deepspeed: bool = False
    template: str = "llama3"


class TrainingExportRequest(BaseModel):
    model_path: str
    export_dir: str = "output/exported_model"
    export_quantization_bit: int = 4


@router.get("/status")
async def get_training_status():
    """Get overall training status"""
    active_jobs = [job for job in training_jobs.values() if job.get("status") in ["running", "queued"]]
    completed_jobs = [job for job in training_jobs.values() if job.get("status") == "completed"]
    failed_jobs = [job for job in training_jobs.values() if job.get("status") == "failed"]

    return {
        "total_jobs": len(training_jobs),
        "active_jobs": len(active_jobs),
        "completed_jobs": len(completed_jobs),
        "failed_jobs": len(failed_jobs),
        "is_training": active_process is not None,
        "supported_models": [
            "meta-llama/Llama-3.1-8B",
            "meta-llama/Llama-3.1-70B",
            "Qwen/Qwen2.5-7B",
            "Qwen/Qwen2.5-72B",
            "mistralai/Mistral-7B-v0.3",
            "google/gemma-2-9b",
        ],
        "methods": {
            "lora": {"vram": "8GB", "quality": "Good", "speed": "Fast"},
            "qlora": {"vram": "6GB", "quality": "Very Good", "speed": "Fast"},
            "full": {"vram": "80GB+", "quality": "Best", "speed": "Slow"},
        }
    }


@router.post("/start")
async def start_training(request: TrainingStartRequest):
    """Start a new training job"""
    global active_process

    if active_process:
        raise HTTPException(status_code=400, detail="Training already in progress")

    # Pre-flight check: verify llamafactory-cli is available
    import shutil
    if not shutil.which("llamafactory-cli"):
        raise HTTPException(
            status_code=400,
            detail=(
                "llamafactory-cli not found on PATH. "
                "Install with: pip install llamafactory "
                "or follow: https://github.com/hiyouga/LLaMA-Factory"
            )
        )

    # Verify dataset exists
    dataset_path = Path(request.dataset)
    if not dataset_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Dataset not found: {request.dataset}. Create the training data first."
        )

    # Generate job ID
    job_id = f"job_{len(training_jobs) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Create job record
    job = {
        "id": job_id,
        "status": "running",
        "created_at": datetime.now().isoformat(),
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "config": request.model_dump(),
        "logs": [],
        "error": None,
    }
    training_jobs[job_id] = job

    # Build training command
    cmd = [
        "llamafactory-cli", "train",
        "--model_name_or_path", request.base_model,
        "--dataset", request.dataset,
        "--output_dir", request.output_dir,
        "--finetuning_type", request.method,
        "--num_train_epochs", str(request.num_epochs),
        "--learning_rate", str(request.learning_rate),
        "--per_device_train_batch_size", str(request.batch_size),
        "--template", request.template,
        "--cutoff_len", "2048",
    ]

    # LoRA specific parameters
    if request.method in ["lora", "qlora"]:
        cmd.extend([
            "--lora_rank", "8",
            "--lora_alpha", "16",
            "--lora_dropout", "0.1",
        ])

    # QLoRA specific
    if request.method == "qlora":
        cmd.extend(["--quantization_bit", "4"])

    # DeepSpeed
    if request.use_deepspeed:
        cmd.extend(["--deepspeed", "ds_z3_config.json"])

    # Start training process
    try:
        active_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent.parent.parent),
        )

        # Start log reader in background
        asyncio.create_task(_read_training_logs(job_id, active_process))

        return {
            "success": True,
            "job_id": job_id,
            "message": f"Training started: {request.base_model} ({request.method})",
        }

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        active_process = None
        logger.error("Training start failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_training():
    """Stop the current training job"""
    global active_process

    if not active_process:
        raise HTTPException(status_code=400, detail="No active training job")

    try:
        active_process.terminate()
        active_process.wait(timeout=10)
        active_process = None

        # Update job status
        for job in training_jobs.values():
            if job.get("status") == "running":
                job["status"] = "stopped"
                job["completed_at"] = datetime.now().isoformat()
                break

        return {"success": True, "message": "Training stopped"}

    except Exception as e:
        logger.error(f"❌ Training stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs():
    """List all training jobs"""
    return {
        "jobs": list(training_jobs.values()),
        "total": len(training_jobs),
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get specific job details"""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return training_jobs[job_id]


@router.post("/export")
async def export_model(request: TrainingExportRequest):
    """Export trained model"""
    try:
        cmd = [
            "llamafactory-cli", "export",
            "--model_name_or_path", request.model_path,
            "--export_dir", request.export_dir,
            "--export_size", "2",
            "--export_quantization_bit", str(request.export_quantization_bit),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        return {
            "success": True,
            "message": f"Model exported to {request.export_dir}",
            "output": result.stdout,
        }

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models():
    """List available base models for fine-tuning"""
    return {
        "models": [
            {"name": "meta-llama/Llama-3.1-8B", "size": "8B", "vram_required": "16GB"},
            {"name": "meta-llama/Llama-3.1-70B", "size": "70B", "vram_required": "140GB"},
            {"name": "Qwen/Qwen2.5-7B", "size": "7B", "vram_required": "14GB"},
            {"name": "Qwen/Qwen2.5-72B", "size": "72B", "vram_required": "144GB"},
            {"name": "mistralai/Mistral-7B-v0.3", "size": "7B", "vram_required": "14GB"},
            {"name": "google/gemma-2-9b", "size": "9B", "vram_required": "18GB"},
        ]
    }


async def _read_training_logs(job_id: str, process: subprocess.Popen):
    """Read training logs in background (non-blocking)."""
    global active_process

    try:
        if process.stdout:
            # Non-blocking readline via thread executor
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, process.stdout.readline
                )
                if not line:
                    break
                if job_id in training_jobs:
                    training_jobs[job_id]["logs"].append(line.strip())
                    # Keep only last 1000 log lines
                    if len(training_jobs[job_id]["logs"]) > 1000:
                        training_jobs[job_id]["logs"] = training_jobs[job_id]["logs"][-1000:]

        # Wait for process to complete (non-blocking)
        return_code = await asyncio.to_thread(process.wait)
        active_process = None

        if job_id in training_jobs:
            if return_code == 0:
                training_jobs[job_id]["status"] = "completed"
                training_jobs[job_id]["completed_at"] = datetime.now().isoformat()
                logger.info(f"✅ Training job {job_id} completed")
            else:
                training_jobs[job_id]["status"] = "failed"
                training_jobs[job_id]["completed_at"] = datetime.now().isoformat()
                training_jobs[job_id]["error"] = f"Process exited with code {return_code}"
                logger.error(f"❌ Training job {job_id} failed")

    except Exception as e:
        logger.error(f"❌ Log reader error for {job_id}: {e}")
        if job_id in training_jobs:
            training_jobs[job_id]["status"] = "failed"
            training_jobs[job_id]["error"] = str(e)
