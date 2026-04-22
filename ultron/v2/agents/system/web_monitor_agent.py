"""WebMonitorAgent — Monitoring websites for changes, price drops, and keywords."""

import asyncio
import logging
import sqlite3
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Any, List, Optional
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

from ultron.v2.core.security import ssrf_guard

logger = logging.getLogger("ultron.agents.system.web_monitor")

class WebMonitorAgent(BaseAgent):
    """Monitors web pages for specific changes."""

    def __init__(self, db_path: str = "data/monitors.db", memory=None, skill_engine=None):
        super().__init__(
            agent_name="WebMonitorAgent",
            agent_description="Autonomous agent that watches websites for changes and alerts the user.",
            capabilities=["web_monitoring", "change_detection", "price_tracking"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitors (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                selector TEXT,
                keyword TEXT,
                last_value TEXT,
                last_checked TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        conn.commit()
        conn.close()

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        
        action = task.input_data.get("action", "check_all")
        
        try:
            if action == "add":
                url = task.input_data.get("url")
                selector = task.input_data.get("selector")
                keyword = task.input_data.get("keyword")
                self._add_monitor(url, selector, keyword)
                result = "Monitor added successfully."
            else:
                result = await self.check_all()

            self.status = AgentStatus.IDLE
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=True, output=result)
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"WebMonitorAgent failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))

    def _add_monitor(self, url: str, selector: str = None, keyword: str = None):
        import uuid
        mid = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO monitors (id, url, selector, keyword) VALUES (?, ?, ?, ?)",
            (mid, url, selector, keyword)
        )
        conn.commit()
        conn.close()

    async def check_all(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM monitors WHERE status = 'active'")
        monitors = cursor.fetchall()
        
        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for m in monitors:
                if not ssrf_guard.is_safe_url(m["url"]):
                    logger.warning(f"Unsafe URL blocked: {m['url']}")
                    continue
                try:
                    resp = await client.get(m["url"])
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    current_value = ""
                    if m["selector"]:
                        elem = soup.select_one(m["selector"])
                        current_value = elem.get_text().strip() if elem else "Not found"
                    elif m["keyword"]:
                        current_value = "Present" if m["keyword"].lower() in resp.text.lower() else "Absent"
                    
                    changed = current_value != m["last_value"]
                    
                    # Update DB
                    cursor.execute(
                        "UPDATE monitors SET last_value = ?, last_checked = ? WHERE id = ?",
                        (current_value, datetime.now().isoformat(), m["id"])
                    )
                    
                    results.append({
                        "url": m["url"],
                        "changed": changed,
                        "old": m["last_value"],
                        "new": current_value
                    })
                except Exception as e:
                    logger.warning(f"Failed to check {m['url']}: {e}")
        
        conn.commit()
        conn.close()
        return results

    async def health_check(self) -> bool:
        return True
