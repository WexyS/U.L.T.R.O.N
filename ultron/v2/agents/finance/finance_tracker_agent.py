"""Finance Tracker Agent — Personal expense and budget management."""

import logging
import aiosqlite
import os
from typing import List, Dict, Any
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

logger = logging.getLogger("ultron.agents.finance.tracker")

class FinanceTrackerAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="FinanceTracker",
            agent_description="Tracks personal expenses, income, and budgets with periodic reports.",
            capabilities=["expense_tracking", "budgeting", "financial_reporting"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.db_path = "data/finance/finance.db"

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        action = task.task_type # add_expense, report, budget_status
        
        try:
            await self._ensure_db()
            if action == "add_expense":
                result = await self._add_expense(task.input_data)
            elif action == "report":
                result = await self._get_report()
            else:
                result = "Unknown finance action."

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=result
            )
        except Exception as e:
            logger.error(f"Finance tracking failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def _ensure_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    category TEXT,
                    description TEXT,
                    date TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def _add_expense(self, data: Dict[str, Any]) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO expenses (amount, category, description) VALUES (?, ?, ?)",
                (data["amount"], data.get("category", "General"), data.get("description", ""))
            )
            await db.commit()
        return f"Expense added: {data['amount']} ({data.get('category')})"

    async def _get_report(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category") as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    async def health_check(self) -> bool:
        return True
