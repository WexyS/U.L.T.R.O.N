"""CalendarTaskAgent — Managing tasks and events using a local SQLite database."""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

logger = logging.getLogger("ultron.agents.productivity.calendar")

class CalendarTaskAgent(BaseAgent):
    agent_name = "CalendarTaskAgent"
    agent_description = "Manages tasks, events, and daily briefings."

    """Manages tasks, events, and daily briefings."""

    def __init__(self, db_path: str = "data/calendar.db", memory=None, skill_engine=None):
        super().__init__(
            agent_name="CalendarTaskAgent",
            agent_description="Personal assistant for managing tasks, events, and schedules.",
            capabilities=["task_management", "event_scheduling", "daily_briefing", "reminders"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT,
                priority INTEGER DEFAULT 3,
                status TEXT DEFAULT 'pending',
                tags TEXT,
                created_at TEXT,
                completed_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                start_datetime TEXT NOT NULL,
                end_datetime TEXT NOT NULL,
                description TEXT,
                location TEXT,
                reminder_minutes INTEGER DEFAULT 30,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        
        intent = task.input_data.get("intent", "").lower()
        params = task.input_data.get("params", {})

        try:
            if "ekle" in intent or "add" in intent:
                if "görev" in intent or "task" in intent:
                    result = self.add_task(params)
                else:
                    result = self.add_event(params)
            elif "list" in intent or "göster" in intent:
                result = self.list_tasks(params)
            elif "brifing" in intent or "briefing" in intent:
                result = self.daily_briefing()
            elif "tamamla" in intent or "complete" in intent:
                result = self.complete_task(params.get("id"))
            else:
                # LLM based intent parsing fallback
                result = await self._parse_and_execute(task.input_data)

            self.status = AgentStatus.IDLE
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=result
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"CalendarTaskAgent failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error=str(e)
            )

    def add_task(self, p: Dict) -> str:
        tid = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (id, title, description, due_date, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (tid, p.get("title"), p.get("description"), p.get("due_date"), p.get("priority", 3), now)
        )
        conn.commit()
        conn.close()
        return f"Görev başarıyla eklendi. ID: {tid}"

    def list_tasks(self, p: Dict) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE status != 'done' ORDER BY priority DESC, due_date ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def daily_briefing(self) -> str:
        tasks = self.list_tasks({})
        pending_count = len(tasks)
        high_priority = len([t for t in tasks if t["priority"] >= 4])
        
        brief = f"Günaydın! Bugün için {pending_count} bekleyen göreviniz var."
        if high_priority > 0:
            brief += f" Bunlardan {high_priority} tanesi yüksek öncelikli."
        
        return brief

    async def _parse_and_execute(self, input_data: Any) -> Any:
        # Simplified: In a real scenario, use LLM to map natural language to methods
        return "Anladım, takviminize baktım."

    async def health_check(self) -> bool:
        return True
