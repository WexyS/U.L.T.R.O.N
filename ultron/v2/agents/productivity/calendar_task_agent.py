"""Calendar & Task Agent — Managing local tasks and upcoming events."""

import logging
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Dict, Any
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

logger = logging.getLogger("ultron.agents.productivity.calendar")

class CalendarTaskAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="CalendarTask",
            agent_description="Manages local task lists and calendar events with a focus on daily briefings.",
            capabilities=["task_management", "calendar", "scheduling"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.db_path = "data/productivity/tasks.db"

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        action = task.task_type # add_task, list_tasks, briefing
        
        try:
            await self._ensure_db()
            if action == "briefing":
                result = await self._get_daily_briefing()
            elif action == "add_task":
                result = await self._add_task(task.input_data)
            else:
                result = await self._list_tasks()

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=result
            )
        except Exception as e:
            logger.error(f"Calendar/Task operation failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def _ensure_db(self):
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due_date TEXT,
                    priority INTEGER,
                    status TEXT DEFAULT 'pending'
                )
            """)
            await db.commit()

    async def _add_task(self, data: Dict[str, Any]) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO tasks (title, due_date, priority) VALUES (?, ?, ?)",
                (data["title"], data.get("due_date"), data.get("priority", 5))
            )
            await db.commit()
        return f"Task added: {data['title']}"

    async def _list_tasks(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM tasks WHERE status = 'pending'") as cursor:
                rows = await cursor.fetchall()
                return [{"id": r[0], "title": r[1], "due_date": r[2], "priority": r[3]} for r in rows]

    async def _get_daily_briefing(self) -> str:
        tasks = await self._list_tasks()
        count = len(tasks)
        if count == 0:
            return "Bugün için bekleyen bir göreviniz bulunmuyor."
        
        task_list = "\n".join([f"- {t['title']} (P{t['priority']})" for t in tasks[:5]])
        return f"Bugün toplam {count} göreviniz var. İşte bazıları:\n{task_list}"

    async def health_check(self) -> bool:
        return True
