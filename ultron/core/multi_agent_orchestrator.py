"""Multi-Agent Task Orchestrator — Agent'lar arası görev yönetimi.

Özellikler (Option 3: In-memory + periodic checkpoint):
- TaskQueue: Öncelik kuyruğu (high/medium/low)
- Agent Load Balancing: Boş agent'a görev ata
- Task Dependencies: Görevler arası bağımlılık
- State Persistence: In-memory + disk checkpoint
- Retry Mechanism: Başarısız görevleri tekrar dene
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Task States ─────────────────────────────────────────────────────────

class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


# ─── Task Model ──────────────────────────────────────────────────────────

@dataclass
class Task:
    """Görev tanımı"""
    id: str
    name: str
    agent_name: str  # Hangi agent çalıştıracak
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    payload: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)  # Bağımlı olduğu görev IDs
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    
    def __lt__(self, other):
        """Priority queue için karşılaştırma"""
        return self.priority.value < other.priority.value


# ─── Task Queue ──────────────────────────────────────────────────────────

class TaskQueue:
    """Agent'lar arası görev kuyruğu"""
    
    def __init__(self):
        self._queue: list[Task] = []
        self._tasks: dict[str, Task] = {}  # ID -> Task
        self._completed: dict[str, Task] = {}
        
    def add(self, task: Task) -> None:
        """Kuyruğa görev ekle"""
        self._queue.append(task)
        self._tasks[task.id] = task
        task.status = TaskStatus.QUEUED
        logger.info("Task queued: %s (priority=%s, agent=%s)", 
                   task.name, task.priority.name, task.agent_name)
    
    def get_next(self, agent_name: Optional[str] = None) -> Optional[Task]:
        """Sıradaki görevi al (öncelik sıralı)"""
        # Priority'ye göre sırala (en yüksek önce)
        self._queue.sort(key=lambda t: t.priority.value, reverse=True)
        
        for i, task in enumerate(self._queue):
            # Agent filtreleme
            if agent_name and task.agent_name != agent_name:
                continue
            
            # Dependencies kontrol
            if not self._are_dependencies_met(task):
                continue
            
            # Kuyruktan çıkar
            self._queue.pop(i)
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            logger.info("Task dequeued: %s (agent=%s)", task.name, task.agent_name)
            return task
        
        return None
    
    def complete(self, task_id: str, result: Any = None) -> None:
        """Görevi tamamla"""
        if task_id not in self._tasks:
            logger.warning("Task not found: %s", task_id)
            return
        
        task = self._tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.result = result
        
        self._completed[task_id] = task
        
        logger.info("Task completed: %s (duration=%s)", 
                   task.name, task.completed_at - task.started_at)
    
    def fail(self, task_id: str, error: str) -> bool:
        """Görevi başarısız - retry varsa True
        
        Returns:
            bool: Retry yapılacaksa True
        """
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        task.retries += 1
        task.error = error
        
        if task.retries < task.max_retries:
            task.status = TaskStatus.RETRYING
            logger.warning("Task failed, will retry (%d/%d): %s", 
                         task.retries, task.max_retries, task.name)
            return True
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            self._completed[task_id] = task
            logger.error("Task failed (max retries): %s - %s", task.name, error)
            self._cancel_dependent_tasks(task_id)
            return False
            
    def _cancel_dependent_tasks(self, failed_task_id: str) -> None:
        """Bir görev iptal/fail olduğunda, ona bağlı görevleri (dependency) de rekürsif iptal et."""
        to_cancel = []
        for task in self._queue:
            if failed_task_id in task.dependencies and task.status != TaskStatus.CANCELLED:
                task.status = TaskStatus.CANCELLED
                task.error = f"Dependency failed: {failed_task_id}"
                task.completed_at = datetime.now()
                logger.warning("Task cancelled due to dependency failure: %s (Dependency: %s)", task.name, failed_task_id)
                to_cancel.append(task)
                
        for t in to_cancel:
            self._queue.remove(t)
            self._completed[t.id] = t
            self._cancel_dependent_tasks(t.id)
    
    def _are_dependencies_met(self, task: Task) -> bool:
        """Görevin bağımlılıkları karşılandı mı?"""
        for dep_id in task.dependencies:
            if dep_id not in self._completed:
                return False
            if self._completed[dep_id].status != TaskStatus.COMPLETED:
                return False
        return True
    
    def get_status(self) -> dict[str, Any]:
        """Kuyruk durumu"""
        return {
            "queued": len(self._queue),
            "total": len(self._tasks),
            "completed": len(self._completed),
            "by_priority": {
                "critical": sum(1 for t in self._tasks.values() if t.priority == TaskPriority.CRITICAL),
                "high": sum(1 for t in self._tasks.values() if t.priority == TaskPriority.HIGH),
                "medium": sum(1 for t in self._tasks.values() if t.priority == TaskPriority.MEDIUM),
                "low": sum(1 for t in self._tasks.values() if t.priority == TaskPriority.LOW),
            }
        }


# ─── State Manager (Option 3: In-memory + checkpoint) ────────────────────

class StateManager:
    """Orchestrator state yönetimi
    
    Option 3: In-memory + periodic checkpoint to disk
    - Runtime: Hızlı in-memory state
    - Checkpoint: Her 10 task'ta veya 5 dakikada bir disk'e yaz
    """
    
    def __init__(self, checkpoint_file: str = "data/orchestrator_state.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory state
        self.session_state: dict[str, Any] = {}
        self.agent_states: dict[str, dict] = {}  # agent_name -> state
        self.task_history: list[dict] = []
        self.tasks_since_checkpoint = 0
        self.last_checkpoint: Optional[datetime] = None
        
        # Checkpoint ayarları
        self.checkpoint_interval_tasks = 10  # Her 10 task'ta
        self.checkpoint_interval_seconds = 300  # 5 dakikada bir
        
        # Yükle
        self.load()
    
    def save_task_completion(self, task: Task) -> None:
        """Task tamamlandı - history'ye ekle ve checkpoint kontrol et"""
        self.task_history.append({
            "id": task.id,
            "name": task.name,
            "agent": task.agent_name,
            "status": task.status.value,
            "duration": (task.completed_at - task.started_at).total_seconds() if task.completed_at and task.started_at else None,
            "retries": task.retries,
        })
        
        self.tasks_since_checkpoint += 1
        
        # Checkpoint gerekli mi?
        if self._should_checkpoint():
            self.checkpoint()
    
    def _should_checkpoint(self) -> bool:
        """Checkpoint gerekli mi kontrol et"""
        from datetime import datetime, timedelta
        
        # Task sayısı threshold'a ulaştı mı?
        if self.tasks_since_checkpoint >= self.checkpoint_interval_tasks:
            return True
        
        # Zaman threshold'a ulaştı mı?
        if self.last_checkpoint:
            time_since = datetime.now() - self.last_checkpoint
            if time_since > timedelta(seconds=self.checkpoint_interval_seconds):
                return True
        
        return False
    
    def checkpoint(self) -> None:
        """State'i disk'e kaydet"""
        try:
            state = {
                "session_state": self.session_state,
                "agent_states": self.agent_states,
                "task_history": self.task_history[-100:],  # Son 100 task
                "last_checkpoint": datetime.now().isoformat(),
            }
            
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            self.tasks_since_checkpoint = 0
            self.last_checkpoint = datetime.now()
            
            logger.info("State checkpoint saved (%d tasks in history)", len(self.task_history))
            
        except Exception as e:
            logger.error("Failed to save checkpoint: %s", e)
    
    def load(self) -> None:
        """State'i disk'ten yükle"""
        if not self.checkpoint_file.exists():
            logger.info("No checkpoint found, starting fresh")
            return
        
        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            self.session_state = state.get("session_state", {})
            self.agent_states = state.get("agent_states", {})
            self.task_history = state.get("task_history", [])
            self.last_checkpoint = datetime.fromisoformat(state["last_checkpoint"])
            
            logger.info("State loaded from checkpoint (%d tasks in history)", len(self.task_history))
            
        except Exception as e:
            logger.error("Failed to load checkpoint: %s", e)
    
    def get_stats(self) -> dict[str, Any]:
        """İstatistikler"""
        return {
            "total_tasks": len(self.task_history),
            "successful": sum(1 for t in self.task_history if t.get("status") == "completed"),
            "failed": sum(1 for t in self.task_history if t.get("status") == "failed"),
            "avg_retries": sum(t.get("retries", 0) for t in self.task_history) / max(len(self.task_history), 1),
            "last_checkpoint": self.last_checkpoint.isoformat() if self.last_checkpoint else None,
        }


# ─── Orchestrator ────────────────────────────────────────────────────────

class MultiAgentOrchestrator:
    """Multi-Agent Task Orchestrator
    
    Agent'lar arası görev dağıtımı yapar.
    """
    
    def __init__(self):
        self.task_queue = TaskQueue()
        self.state_manager = StateManager()
        self.agents: dict[str, Any] = {}  # agent_name -> agent instance
        
        logger.info("MultiAgentOrchestrator initialized")
    
    def register_agent(self, agent_name: str, agent: Any) -> None:
        """Agent kaydet"""
        self.agents[agent_name] = agent
        self.state_manager.agent_states[agent_name] = {"status": "idle", "tasks_completed": 0}
        logger.info("Agent registered: %s", agent_name)
    
    def submit_task(self, task: Task) -> None:
        """Görev gönder"""
        self.task_queue.add(task)
    
    async def process_next(self) -> Optional[Task]:
        """Sıradaki görevi işle"""
        task = self.task_queue.get_next()
        
        if not task:
            return None
        
        # Agent'ı bul
        if task.agent_name not in self.agents:
            self.task_queue.fail(task.id, f"Agent not found: {task.agent_name}")
            return task
        
        try:
            # Agent'ı çalıştır (async)
            agent = self.agents[task.agent_name]
            result = await agent.execute(task.payload)
            
            self.task_queue.complete(task.id, result)
            self.state_manager.save_task_completion(task)
            self.state_manager.agent_states[task.agent_name]["tasks_completed"] += 1
            
        except Exception as e:
            should_retry = self.task_queue.fail(task.id, str(e))
            
            if should_retry:
                # Retry için kuyruğa geri ekle
                task.status = TaskStatus.PENDING
                self.task_queue.add(task)
            else:
                self.state_manager.save_task_completion(task)
        
        return task
    
    async def run_loop(self, max_tasks: Optional[int] = None) -> None:
        """Sürekli görev işleme döngüsü"""
        processed = 0
        
        while True:
            task = await self.process_next()
            
            if task:
                processed += 1
            
            if max_tasks and processed >= max_tasks:
                logger.info("Max tasks reached (%d)", max_tasks)
                break
            
            # Kuyruk boşsa bekle
            if not task:
                await asyncio.sleep(1)
    
    def get_status(self) -> dict[str, Any]:
        """Orchestrator durumu"""
        return {
            "queue": self.task_queue.get_status(),
            "state": self.state_manager.get_stats(),
            "agents": {
                name: state for name, state in self.state_manager.agent_states.items()
            }
        }
