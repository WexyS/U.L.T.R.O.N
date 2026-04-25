"""News Monitor Agent — Tracking RSS feeds and news APIs for updates."""

import logging
import httpx
import feedparser
from typing import List, Dict, Any
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.knowledge.news")

class NewsMonitorAgent(BaseAgent):
    agent_name = "NewsMonitorAgent"
    agent_description = "Specialized Genesis agent for NewsMonitor tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="NewsMonitor",
            agent_description="Monitors RSS feeds and news sources for specific topics and provides summaries.",
            capabilities=["news_monitoring", "rss_parsing", "summarization"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.feeds = [
            "https://www.bbc.co.uk/turkce/index.xml",
            "https://www.trthaber.com/manset_articles.rss",
            "https://techcrunch.com/feed/"
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        topic = task.input_data or "AI"
        
        try:
            all_news = []
            for feed_url in self.feeds:
                news = await self._parse_feed(feed_url)
                all_news.extend(news)

            # Filter and summarize with LLM
            prompt = [
                {"role": "system", "content": "Filter the following news for relevance to the topic and provide a structured summary in Turkish."},
                {"role": "user", "content": f"Topic: {topic}\nNews:\n{all_news[:15]}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"News monitoring failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def _parse_feed(self, url: str) -> List[Dict[str, str]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                feed = feedparser.parse(resp.text)
                return [{"title": entry.title, "link": entry.link, "summary": entry.summary[:200]} for entry in feed.entries]
        except Exception as e:
            logger.warning(f"Failed to parse feed {url}: {e}")
            return []

    async def health_check(self) -> bool:
        return True
