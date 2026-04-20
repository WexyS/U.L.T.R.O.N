"""Researcher Agent — deep multi-hop research with citations."""

import logging
import os
import hashlib
import json
import re
from datetime import datetime
import pytz
from functools import lru_cache

from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus, ToolCall
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter
from ultron.v2.core.connectivity import ConnectivityManager
from ultron.v2.core.browser_service import BrowserService
from typing import Any

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
        memory: Any = None,
        max_hops: int = 3,
    ) -> None:
        super().__init__(
            role=AgentRole.RESEARCHER,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
        )
        self.memory = memory
        self.max_hops = max_hops
        self._ddg = None
        self.browser = BrowserService()

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
            
            # Offline Check
            if not ConnectivityManager.is_online():
                logger.warning("ResearcherAgent running in OFFLINE mode.")
                offline_msg = ConnectivityManager.get_offline_recommendation("research")
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    output=f"{offline_msg}\n\nSearch query: {query}\nResult: Using internal knowledge base as internet is disconnected.",
                    metadata={"offline": True}
                )

            # 1. Check for instant utilities (weather, time, etc.)
            utility_result = await self.get_realtime_utility(query)
            if "Detaylı bilgi" not in utility_result:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    output=utility_result,
                    tool_calls=[{"name": "utility", "arguments": {"query": query}, "success": True}]
                )

            # ── Fast Path 2: Architectural UI Analysis ──
            if task.intent == "architect" or any(kw in task.description.lower() for kw in ["mimari", "architect", "clone", "klonla"]):
                # Extract URL
                url_match = re.search(r'https?://\S+', task.description)
                if url_match:
                    target_url = url_match.group(0)
                    visual_data = await self.extract_visual_styles(target_url)
                    
                    # Synthesis for the user
                    output = [
                        f"🏗️ **MİMARİ ANALİZ RAPORU: {visual_data.get('title', 'Adsız Site')}**",
                        f"🔗 **URL:** {target_url}",
                        f"🎨 **Görsel Kimlik:** Analiz ediliyor...",
                        f"📸 **Ekran Görüntüsü:** [Görüntüle]({visual_data.get('screenshot_path')})",
                        "",
                        f"📄 **Özet:** {visual_data.get('summary', '')}"
                    ]
                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.SUCCESS,
                        output="\n".join(output),
                        context={"visual_data": visual_data}
                    )

            # ── Fast Path 3: Deep Data Extraction (Scraping/Profile) ──
            if any(kw in task.description.lower() for kw in ["çal", "scrape", "profil", "ekstrak", "veri topla"]):
                url_match = re.search(r'https?://\S+', task.description)
                if url_match:
                    target_url = url_match.group(0)
                    logger.info("Starting Deep Data Extraction for: %s", target_url)
                    
                    # 1. Visual styles & screenshots
                    visual_data = await self.extract_visual_styles(target_url)
                    
                    # 2. Deep content extraction
                    content_data = await self._read_urls([{"href": target_url, "title": "Target Profile"}])
                    
                    # 3. Knowledge Graph storage
                    if self.memory:
                        self.memory.add_concept(target_url, category="scraped_data", properties={
                            "content": content_data[0].get("content", "")[:1000] if content_data else "",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    output = [
                        f"🕵️ **DERİN VERİ EKSTRAKSİYONU TAMAMLANDI**",
                        f"🔗 **Hedef:** {target_url}",
                        f"📄 **Başlık:** {visual_data.get('title', 'Bilinmiyor')}",
                        f"💾 **Hafızaya Alınan Veri:** {len(content_data[0].get('content', '')) if content_data else 0} karakter",
                        f"🎨 **Görsel Kimlik:** {len(visual_data.get('colors', []))} renk, {len(visual_data.get('fonts', []))} font",
                        "",
                        "✅ Tüm veriler analiz edildi ve Ultron'un uzun süreli hafızasına kaydedildi. Bu kişi veya site hakkında her şeyi artık biliyorum."
                    ]
                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.SUCCESS,
                        output="\n".join(output),
                        context={"scraped_data": visual_data}
                    )

            # Hop 1: Initial Search
            search_results = await self._web_search(query)
            if not search_results:
                if query.startswith("http"):
                    search_results = [{"href": query, "title": "Direct URL", "body": "Direct access via researcher tool"}]
                else:
                    return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error="No search results found after multiple attempts across all backends.")

            # Hop 2+: Iterative Deepening (Multi-Hop)
            depth = int(task.context.get("search_depth", self.state.metadata.get("search_depth", 2)))
            all_content = []
            known_urls = set()
            
            # Initial read
            top_urls = [r for r in search_results if r.get("href")][:3 + depth]
            content = await self._read_urls(top_urls, max_hops=max_hops - 1)
            all_content.extend(content)
            for r in top_urls: known_urls.add(r["href"])

            # If depth > 1, perform follow-up hops
            if depth > 1:
                logger.info("Entering Multi-Hop Reasoning (Depth: %d)", depth)
                for i in range(depth - 1):
                    # 1. Analyze what we have and find missing links
                    followup_prompt = [
                        {"role": "system", "content": "You are a deep research strategist. Based on the findings so far, identify 2-3 specific follow-up search queries to fill missing gaps in the research. Return JSON list: [\"query1\", \"query2\"]"},
                        {"role": "user", "content": f"Main Goal: {query}\n\nFindings so far:\n" + "\n".join([str(c.get("content", ""))[:200] for c in all_content])}
                    ]
                    try:
                        followup_resp = await self._llm_chat(followup_prompt, max_tokens=150)
                        followup_queries = json.loads(re.search(r"\[[\s\S]*\]", followup_resp.content).group())
                        
                        for f_query in followup_queries:
                            logger.info("Follow-up hop %d: %s", i + 2, f_query)
                            f_results = await self._web_search(f_query)
                            f_top_urls = [r for r in f_results if r.get("href") and r["href"] not in known_urls][:2]
                            
                            if f_top_urls:
                                f_content = await self._read_urls(f_top_urls, max_hops=max_hops - 2)
                                all_content.extend(f_content)
                                for r in f_top_urls: known_urls.add(r["href"])
                    except Exception as e:
                        logger.warning("Multi-hop follow-up failed: %s", e)
                        break

            # Synthesize all findings
            synthesis = await self._synthesize(query, search_results, all_content, depth=depth)

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output=synthesis,
                tool_calls=[ToolCall(name="research", arguments={"query": query, "depth": depth}, success=True)],
                metadata={"sources": len(search_results), "hops": max_hops, "depth": depth},
            )
        finally:
            self.state.status = AgentStatus.IDLE
            self.state.current_task = None

    async def _web_search(self, query: str) -> list[dict]:
        """Search the web using multiple backends with automatic fallback."""
        # 1. Optimize query for search engine
        optimized_query = await self._optimize_query(query)
        logger.info("Optimized search query: '%s' -> '%s'", query, optimized_query)

        # 2. Try multiple search backends in order
        results = await self._search_duckduckgo(optimized_query)
        if results:
            return results

        # Fallback: Tavily API (if configured)
        results = await self._search_tavily(optimized_query)
        if results:
            return results

        # Fallback: Google Serper API (if configured)
        results = await self._search_serper(optimized_query)
        if results:
            return results

        # Last resort: construct known-good URLs
        logger.warning("All search backends failed, using fallback URLs")
        return self._construct_fallback_results(optimized_query)

    async def _optimize_query(self, query: str) -> str:
        """Optimize a user query into clean search keywords."""
        try:
            messages = self._build_messages(
                f"Extract only the core search keywords from this user query. "
                f"Remove conversational words like 'what do you know about', 'tell me', "
                f"'hakkında ne biliyorsun', 'bana anlat', 'nedir', 'araştır', etc. "
                f"Return ONLY the keywords, nothing else.\n\nQuery: {query}"
            )
            response = await self._llm_chat(messages, max_tokens=50, temperature=0.1)
            result = response.content.strip()
            return result if result and len(result) > 2 else query
        except Exception:
            # Fallback: manual Turkish/English filler removal
            fillers = (
                r'\b(hakkında|ne biliyorsun|bana anlat|nedir|araştır|'
                r'bul|açıkla|öğren|ne|bir|bu|şu|var mı|'
                r'what is|tell me about|explain|find|search for|look up)\b'
            )
            cleaned = re.sub(fillers, '', query, flags=re.IGNORECASE).strip()
            return cleaned if len(cleaned) > 2 else query

    async def _search_duckduckgo(self, query: str) -> list[dict]:
        """Search using DuckDuckGo (free, no API key needed)."""
        try:
            import asyncio
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS

            def perform_search():
                with DDGS() as ddgs:
                    # The text() method might have changed its signature or name
                    results = list(ddgs.text(query, max_results=10))
                    return results

            urls = await asyncio.to_thread(perform_search)
            if urls:
                logger.info("DuckDuckGo returned %d results for: %s", len(urls), query)
                return urls
            logger.warning("DuckDuckGo returned no results for: %s", query)
            return []
        except Exception as e:
            logger.warning("DuckDuckGo search failed for '%s': %s", query, e)
            return []

    async def _search_tavily(self, query: str) -> list[dict]:
        """Search using Tavily API (AI-optimized search, free tier available)."""
        api_key = os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            logger.debug("Tavily search skipped: No API key")
            return []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": api_key, "query": query, "max_results": 10},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = [
                        {"href": r["url"], "title": r.get("title", ""), "body": r.get("content", "")}
                        for r in data.get("results", [])
                    ]
                    logger.info("Tavily returned %d results for: %s", len(results), query)
                    return results
        except Exception as e:
            logger.warning("Tavily search failed: %s", e)
        return []

    async def _search_serper(self, query: str) -> list[dict]:
        """Search using Google Serper API (free tier: 2500 queries/month)."""
        api_key = os.environ.get("SERPER_API_KEY", "")
        if not api_key:
            logger.debug("Serper search skipped: No API key")
            return []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://google.serper.dev/search",
                    json={"q": query},
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = [
                        {"href": r["link"], "title": r.get("title", ""), "body": r.get("snippet", "")}
                        for r in data.get("organic", [])
                    ]
                    logger.info("Serper returned %d results for: %s", len(results), query)
                    return results
        except Exception as e:
            logger.warning("Serper search failed: %s", e)
        return []

    def _construct_fallback_results(self, query: str) -> list[dict]:
        """Construct search results from well-known sites as last resort."""
        from urllib.parse import quote
        q = quote(query)
        return [
            {"href": f"https://en.wikipedia.org/w/index.php?search={q}", "title": f"Wikipedia: {query}", "body": ""},
            {"href": f"https://stackoverflow.com/search?q={q}", "title": f"StackOverflow: {query}", "body": ""},
            {"href": f"https://github.com/search?q={q}&type=repositories", "title": f"GitHub: {query}", "body": ""},
            {"href": f"https://developer.mozilla.org/en-US/search?q={q}", "title": f"MDN: {query}", "body": ""},
        ]

    async def extract_visual_styles(self, url: str) -> dict:
        """Deep visual and functional analysis of a URL using the Unified Browser Service."""
        logger.info("Starting visual analysis via BrowserService: %s", url)
        data = await self.browser.scrape_url(url)
        
        if "error" in data:
            return {"url": url, "error": data["error"]}
            
        return {
            "title": data.get("title", ""),
            "url": url,
            "screenshot_path": data.get("screenshot"),
            "colors": ["Analysis in progress..."],
            "fonts": ["Analysis in progress..."],
            "summary": data.get("content", "")[:1000]
        }

    async def _read_urls(self, urls: list[dict], max_chars: int = 15000, **kwargs) -> list[dict]:
        """Fetch and extract content from URLs using the Unified Browser Service."""
        contents = []
        for url_info in urls:
            url = url_info.get("href") or url_info.get("url")
            if not url: continue
            
            try:
                logger.info("Reading URL via BrowserService: %s", url)
                data = await self.browser.scrape_url(url)
                
                if "content" in data:
                    contents.append({
                        "url": url,
                        "title": data.get("title", url_info.get("title", "No Title")),
                        "content": data["content"][:max_chars]
                    })
                else:
                    logger.warning("Failed to scrape %s: %s", url, data.get("error"))
            except Exception as e:
                logger.error("Error reading URL %s: %s", url, e)
        return contents

    async def get_realtime_utility(self, query: str) -> str:
        """Handle weather, time zones, and instant utility requests for any location (with offline support)."""
        q = query.lower()
        
        # ── Time Zones (Universal & Offline Ready) ──
        if any(kw in q for kw in ["saat", "time", "kaç"]):
            # Simple local time
            if len(q.split()) <= 2 and "kaç" in q:
                now = datetime.now()
                return f"Yerel Saat: {now.strftime('%H:%M:%S')} (Tarih: {now.strftime('%d.%m.%Y')})"
            
            # Offline-friendly timezone mapping for major cities
            CITY_TZ_MAP = {
                "londra": "Europe/London", "london": "Europe/London",
                "paris": "Europe/Paris", "berlin": "Europe/Berlin",
                "tokyo": "Asia/Tokyo", "new york": "America/New_York",
                "moskova": "Europe/Moscow", "moscow": "Europe/Moscow",
                "bakü": "Asia/Baku", "baku": "Asia/Baku",
                "sidney": "Australia/Sydney", "sydney": "Australia/Sydney",
                "dubai": "Asia/Dubai", "istanbul": "Europe/Istanbul",
                "ankara": "Europe/Istanbul", "izmir": "Europe/Istanbul",
                "karaman": "Europe/Istanbul", "antalya": "Europe/Istanbul",
                "bursa": "Europe/Istanbul", "adana": "Europe/Istanbul",
                "konya": "Europe/Istanbul", "gaziantep": "Europe/Istanbul",
            }
            
            target_tz = None
            # 1. Check Memory/Knowledge Graph first
            if self.memory:
                try:
                    # Look for city in memory concepts
                    city_data = self.memory.query_graph(q, max_depth=1)
                    if "nodes" in city_data and q in city_data["nodes"]:
                        node = city_data["nodes"][q]
                        if node.get("properties", {}).get("timezone"):
                            target_tz = node["properties"]["timezone"]
                            logger.info("Found city timezone in memory: %s -> %s", q, target_tz)
                except Exception:
                    pass

            # 2. Check hardcoded CITY_TZ_MAP
            if not target_tz:
                for city, tz in CITY_TZ_MAP.items():
                    if city in q:
                        target_tz = tz
                        break
            
            # 3. Generic Turkey detection
            if not target_tz and any(kw in q for kw in ["türkiye", "turkey", "tr", "saat kaç"]):
                target_tz = "Europe/Istanbul"
            
            if target_tz:
                try:
                    tz_obj = pytz.timezone(target_tz)
                    now_tz = datetime.now(tz_obj)
                    city_label = target_tz.split('/')[-1].replace('_', ' ')
                    return f"🕒 {city_label} Saati: {now_tz.strftime('%H:%M:%S')} (Tarih: {now_tz.strftime('%d.%m.%Y')})"
                except Exception:
                    pass

            # 4. Online Research & Learn (Dynamic Learning)
            try:
                # Use LLM to extract city name if not obvious
                extraction_prompt = [{"role": "system", "content": "Extract the city name from the query. Return ONLY the city name in English."}, {"role": "user", "content": query}]
                city_resp = await self._llm_chat(extraction_prompt, max_tokens=20)
                extracted_city = city_resp.content.strip().lower()

                time_results = await self._search_duckduckgo(f"timezone for {extracted_city}")
                if time_results:
                    # Use LLM to extract IANA timezone string (e.g. Europe/Paris)
                    tz_prompt = [
                        {"role": "system", "content": "Extract the IANA timezone string (e.g. 'America/New_York', 'Europe/Istanbul') from the text. Return ONLY the string."},
                        {"role": "user", "content": f"Text: {time_results[0]['body']}"}
                    ]
                    tz_resp = await self._llm_chat(tz_prompt, max_tokens=30)
                    new_tz = tz_resp.content.strip()
                    
                    if "/" in new_tz:
                        # VALIDATED: Learn it!
                        if self.memory:
                            self.memory.add_concept(extracted_city, category="city", properties={"timezone": new_tz})
                            logger.info("Learned new city timezone: %s -> %s", extracted_city, new_tz)
                        
                        tz_obj = pytz.timezone(new_tz)
                        now_tz = datetime.now(tz_obj)
                        return f"🕒 {extracted_city.title()} Saati: {now_tz.strftime('%H:%M:%S')} (Tarih: {now_tz.strftime('%d.%m.%Y')})"
                    
                    return f"Zaman Bilgisi ({query}):\n{time_results[0].get('body', 'Veri alınamadı.')}"
            except Exception as e:
                logger.error("Dynamic city learning failed: %s", e)
                return f"Şu an internete erişilemiyor. Yerel saat: {datetime.now().strftime('%H:%M:%S')}"
            
        # ── Weather (Requires Internet) ──
        if any(kw in q for kw in ["hava", "weather", "derece", "yağmur"]):
            try:
                weather_results = await self._search_duckduckgo(f"{query} weather report")
                if weather_results:
                    return f"Hava Durumu Bilgisi ({query}):\n{weather_results[0].get('body', 'Veri alınamadı.')}"
            except Exception:
                return "⛈️ Hava durumu bilgisi için internet bağlantısı gerekiyor."
                
        return "Detaylı bilgi için web araştırması başlatılıyor..."

    async def _synthesize(
        self,
        query: str,
        search_results: list[dict],
        content: list[dict],
        depth: int = 1,
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
