"""Market Monitor Agent — Tracking stocks, crypto, and market trends."""

import logging
import httpx
from typing import List, Dict, Any
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.finance.market")

class MarketMonitorAgent(BaseAgent):
    agent_name = "MarketMonitorAgent"
    agent_description = "Specialized Genesis agent for MarketMonitor tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="MarketMonitor",
            agent_description="Monitors stock market, crypto prices, and global financial trends.",
            capabilities=["market_monitoring", "stock_quotes", "crypto_tracking"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        symbol = task.input_data # e.g. BTC, AAPL
        
        try:
            # 1. Fetch market data (Simplified via search or public APIs)
            search_results = await self.request_skill("skill_web_search", query=f"{symbol} price today", max_results=3)
            
            # 2. Analyze with LLM
            prompt = [
                {"role": "system", "content": "Analyze the market data for the given symbol and provide a summary with sentiment analysis."},
                {"role": "user", "content": f"Symbol: {symbol}\nMarket Data: {search_results}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Market monitoring failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
