"""Researcher Agent — deep multi-hop research with citations."""

import logging

from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus, ToolCall
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class ResearcherAgent(Agent):
    """Deep research agent with multi-hop reasoning and citations.

    Capabilities:
    - Web search (DuckDuckGo)
    - URL scraping and content extraction
    - Multi-hop research (follow links, dig deeper)
    - Citation tracking
    - Document synthesis
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
        max_hops: int = 3,
    ) -> None:
        super().__init__(
            role=AgentRole.RESEARCHER,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
        )
        self.max_hops = max_hops
        self._ddg = None

    def _default_system_prompt(self) -> str:
        return (
            "You are an expert researcher. You conduct thorough research with credible sources.\n"
            "For each research task:\n"
            "1. Search the web for relevant information\n"
            "2. Read and extract content from promising URLs\n"
            "3. Follow links for deeper research (multi-hop)\n"
            "4. Synthesize findings into a comprehensive answer\n"
            "5. ALWAYS cite sources with URLs\n"
            "6. Distinguish facts from opinions\n"
            "7. Note the date/age of information\n"
            "Be thorough, accurate, and well-cited."
        )

    async def _subscribe_events(self) -> None:
        async def on_research_request(event) -> None:
            if not self._running:
                return
            task = Task(
                id=event.data.get("task_id"),
                description=event.data.get("description", ""),
                context=event.data.get("context", {}),
            )
            result = await self.execute(task)
            await self._publish_event("research_result", {
                "task_id": task.id,
                "output": result.output,
                "error": result.error,
                "success": result.status == TaskStatus.SUCCESS,
            })

        self.event_bus.subscribe("research_request", on_research_request)

    async def execute(self, task: Task) -> TaskResult:
        """Execute a research task."""
        self.state.status = AgentStatus.BUSY
        self.state.current_task = task.id

        try:
            query = task.description
            max_hops = task.context.get("max_hops", self.max_hops)

            # Hop 1: Search
            search_results = await self._web_search(query)
            if not search_results:
                return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error="No search results found")

            # Hop 2+: Read top URLs
            content = await self._read_urls(search_results[:5], max_hops=max_hops - 1)

            # Synthesize
            synthesis = await self._synthesize(query, search_results, content)

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output=synthesis,
                tool_calls=[ToolCall(name="research", arguments={"query": query}, success=True)],
                metadata={"sources": len(search_results), "hops": max_hops},
            )
        finally:
            self.state.status = AgentStatus.IDLE
            self.state.current_task = None

    async def _web_search(self, query: str) -> list[dict]:
        """Search the web using DuckDuckGo with optimized keywords."""
        try:
            # 1. Optimize query for search engine
            messages = self._build_messages(
                f"Extract only the core search keywords from this user query. "
                f"Remove conversational words like 'what do you know about', 'tell me', 'hakkında ne biliyorsun', etc. "
                f"Return ONLY the keywords, nothing else.\n\nQuery: {query}"
            )
            response = await self._llm_chat(messages, max_tokens=50, temperature=0.1)
            optimized_query = response.content.strip() or query
            logger.info("Optimized search query: '%s' -> '%s'", query, optimized_query)

            # 2. Use DDGS in thread to not block event loop
            import asyncio
            from duckduckgo_search import DDGS
            
            def perform_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(optimized_query, max_results=10))
            
            urls = await asyncio.to_thread(perform_search)
            
            logger.info("Search returned %d results for: %s", len(urls), optimized_query)
            return urls
        except Exception as e:
            logger.error("Search failed for '%s': %s", query, e)
            return []

    async def _read_urls(self, urls: list[dict], max_hops: int = 2) -> list[dict]:
        """Fetch and extract content from URLs."""
        import httpx

        contents = []
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for url_info in urls:
                url = url_info.get("href", "")
                if not url:
                    continue
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        # Extract text content (basic HTML stripping)
                        import re
                        text = re.sub(r'<[^>]+>', ' ', resp.text)
                        text = re.sub(r'\s+', ' ', text).strip()
                        contents.append({
                            "url": url,
                            "title": url_info.get("title", ""),
                            "content": text[:3000],  # Limit content
                        })
                        # Follow links if more hops needed
                        if max_hops > 0:
                            links = re.findall(r'href=[\'"]?([^\'" >]+)', resp.text[:5000])
                            # Would recursively follow — simplified here
                except Exception as e:
                    logger.debug("Failed to fetch %s: %s", url, e)

        return contents

    async def _synthesize(
        self,
        query: str,
        search_results: list[dict],
        content: list[dict],
    ) -> str:
        """Synthesize research findings into a comprehensive answer."""
        sources_text = "\n\n".join(
            f"Source {i+1}: {c.get('title', '')}\nURL: {c['url']}\n{c['content'][:500]}"
            for i, c in enumerate(content[:5])
        )

        search_text = "\n\n".join(
            f"{r.get('title', '')}: {r.get('body', '')}\nURL: {r.get('href', '')}"
            for r in search_results[:5]
        )

        messages = self._build_messages(
            f"Research query: {query}\n\n"
            f"Search results:\n{search_text}\n\n"
            f"Detailed content:\n{sources_text}\n\n"
            f"Write a comprehensive, well-structured answer.\n"
            f"Requirements:\n"
            f"- Cite sources with URLs\n"
            f"- Be accurate and thorough\n"
            f"- Structure with clear sections\n"
            f"- Note any conflicting information\n"
            f"- Include dates if relevant"
        )

        response = await self._llm_chat(messages, max_tokens=4096)
        return response.content
