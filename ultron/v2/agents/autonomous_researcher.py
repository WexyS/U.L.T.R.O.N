"""
AutonomousWebResearcher — Ultron's self-learning web research agent.

This agent can:
1. Browse the web autonomously using Playwright
2. Discover and extract valuable resources
3. Save discovered knowledge to memory
4. Build knowledge graphs from learned content
5. Self-teach by researching topics deeply
"""

from __future__ import annotations

import asyncio
import json
import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from ultron.v2.agents.base import Agent, AgentStatus
from ultron.v2.core.types import Task, TaskResult, TaskStatus
from ultron.v2.memory.engine import MemoryEngine

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredResource:
    """A resource discovered during autonomous research."""
    url: str
    title: str
    content_type: str  # article, documentation, tutorial, research_paper, code, video
    summary: str
    key_points: list[str]
    relevance_score: float  # 0.0 to 1.0
    tags: list[str]
    discovered_at: datetime = field(default_factory=datetime.now)
    content_hash: str = ""
    raw_content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.content_hash and self.raw_content:
            self.content_hash = hashlib.md5(self.raw_content.encode()).hexdigest()


@dataclass
class ResearchSession:
    """Tracks a complete research session."""
    session_id: str
    topic: str
    start_time: datetime
    end_time: Optional[datetime] = None
    urls_visited: list[str] = field(default_factory=list)
    resources_found: int = 0
    knowledge_saved: int = 0
    insights_generated: list[str] = field(default_factory=list)
    status: str = "running"  # running, completed, failed
    error: Optional[str] = None


class AutonomousWebResearcher(Agent):
    """
    Autonomous web research agent that can browse, learn, and save knowledge.
    
    This agent enables Ultron to:
    - Research topics autonomously
    - Discover high-quality resources
    - Build knowledge graphs
    - Self-teach and improve over time
    """

    role = "autonomous_researcher"

    def __init__(
        self,
        llm_router=None,
        event_bus=None,
        blackboard=None,
        memory_engine: Optional[MemoryEngine] = None,
        headless: bool = True,
        max_depth: int = 3,
        max_pages: int = 20,
    ):
        super().__init__(
            role=self.role,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
            system_prompt=self._default_system_prompt(),
        )
        self.memory_engine = memory_engine
        self.headless = headless
        self.max_depth = max_depth
        self.max_pages = max_pages
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._session: Optional[ResearchSession] = None
        self._visited_urls: set[str] = set()
        self._discovered_resources: list[DiscoveredResource] = []
        self._knowledge_base_path = Path("data/autonomous_knowledge")
        self._knowledge_base_path.mkdir(parents=True, exist_ok=True)

    def _default_system_prompt(self) -> str:
        return (
            "You are Ultron's Autonomous Research Agent. "
            "Your mission is to browse the web, discover valuable resources, "
            "extract knowledge, and save everything to memory for future use. "
            "You operate autonomously and intelligently, prioritizing high-quality content. "
            "Always respect robots.txt and rate limits. "
            "Focus on discovering: tutorials, documentation, research papers, code repositories, "
            "and educational content."
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute autonomous research task."""
        self.state.status = AgentStatus.BUSY
        self._session = ResearchSession(
            session_id=task.id,
            topic=task.description,
            start_time=datetime.now(),
        )

        try:
            intent = task.intent.lower().strip()
            context = task.context

            if intent in ["research", "learn", "study"]:
                return await self._handle_research(task)
            elif intent in ["browse", "explore", "discover"]:
                return await self._handle_exploration(task)
            elif intent in ["teach", "self_learn", "auto_learn"]:
                return await self._handle_self_learning(task)
            elif intent in ["summarize_url", "extract"]:
                return await self._handle_url_extraction(task)
            elif intent in ["build_knowledge", "organize"]:
                return await self._handle_knowledge_building(task)
            else:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=f"Unknown research intent: {intent}",
                )
        except Exception as exc:
            logger.exception("Autonomous researcher failed")
            if self._session:
                self._session.status = "failed"
                self._session.error = str(exc)
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(exc),
            )
        finally:
            self.state.status = AgentStatus.IDLE
            if self._session:
                self._session.end_time = datetime.now()
                await self._save_session_report()

    async def _handle_research(self, task: Task) -> TaskResult:
        """Deep research on a specific topic."""
        topic = task.description
        depth = task.context.get("depth", self.max_depth)
        max_pages = task.context.get("max_pages", self.max_pages)

        logger.info("Starting autonomous research on: %s (depth=%d, max_pages=%d)", topic, depth, max_pages)

        # Initialize browser
        await self._init_browser()

        # Step 1: Search for the topic
        search_results = await self._search_topic(topic)
        logger.info("Found %d initial search results", len(search_results))

        # Step 2: Visit and extract from promising URLs
        resources = []
        for i, url in enumerate(search_results[:max_pages]):
            if len(resources) >= max_pages:
                break
            
            resource = await self._visit_and_extract(url, topic, depth=1, max_depth=depth)
            if resource:
                resources.append(resource)
                self._discovered_resources.append(resource)
                self._session.urls_visited.append(url)
                self._session.resources_found += 1

                # Save to memory immediately
                if self.memory_engine:
                    await self._save_to_memory(resource)
                    self._session.knowledge_saved += 1

        # Step 3: Build insights
        insights = await self._synthesize_insights(resources, topic)

        # Step 4: Generate research report
        report = self._generate_research_report(topic, resources, insights)

        self._session.status = "completed"
        self._session.insights_generated = insights

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=report,
            metadata={
                "topic": topic,
                "resources_found": len(resources),
                "knowledge_saved": self._session.knowledge_saved,
                "insights": insights[:10],
            },
        )

    async def _handle_exploration(self, task: Task) -> TaskResult:
        """Broad exploration of a domain or field."""
        domain = task.description
        max_pages = task.context.get("max_pages", self.max_pages)

        logger.info("Starting exploration of domain: %s", domain)

        await self._init_browser()

        # Start from multiple seed URLs
        seed_urls = await self._generate_seed_urls(domain)
        
        resources = []
        for url in seed_urls:
            if len(resources) >= max_pages:
                break
            
            resource = await self._visit_and_extract(url, domain, depth=1, max_depth=2)
            if resource and resource.relevance_score > 0.5:
                resources.append(resource)
                self._discovered_resources.append(resource)
                
                if self.memory_engine:
                    await self._save_to_memory(resource)

        self._session.status = "completed"

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Exploration complete! Found {len(resources)} resources in {domain}",
            metadata={"resources_found": len(resources)},
        )

    async def _handle_self_learning(self, task: Task) -> TaskResult:
        """Self-directed learning - Ultron decides what to learn."""
        logger.info("Starting self-learning cycle")

        # Identify knowledge gaps
        gaps = await self._identify_knowledge_gaps()
        
        if not gaps:
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output="No significant knowledge gaps identified. System is well-trained.",
            )

        # Learn from each gap
        topics_learned = []
        for gap in gaps[:5]:  # Top 5 gaps
            research_task = Task(
                id=f"{task.id}_gap",
                description=gap["topic"],
                intent="research",
                context={"depth": 2, "max_pages": 10},
            )
            result = await self._handle_research(research_task)
            if result.status == TaskStatus.SUCCESS:
                topics_learned.append(gap["topic"])

        self._session.status = "completed"

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Self-learning complete! Learned about: {', '.join(topics_learned)}",
            metadata={"topics_learned": topics_learned},
        )

    async def _handle_url_extraction(self, task: Task) -> TaskResult:
        """Extract and summarize a specific URL."""
        url = task.context.get("url", task.description)
        
        logger.info("Extracting URL: %s", url)
        
        await self._init_browser()
        resource = await self._visit_and_extract(url, "url_extraction", depth=1, max_depth=1)
        
        if not resource:
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error="Failed to extract content from URL",
            )

        if self.memory_engine:
            await self._save_to_memory(resource)

        self._session.status = "completed"

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Resource extracted and summarized:\n\n{resource.summary}\n\nKey Points:\n" + 
                   "\n".join(f"- {point}" for point in resource.key_points),
            metadata={"resource": resource.__dict__},
        )

    async def _handle_knowledge_building(self, task: Task) -> TaskResult:
        """Organize and build knowledge graphs from learned content."""
        logger.info("Building knowledge graph")

        # Retrieve all saved resources
        saved_resources = await self._retrieve_saved_resources()
        
        if not saved_resources:
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output="No saved resources found yet. Start researching to build knowledge.",
            )

        # Build knowledge graph
        knowledge_graph = await self._build_knowledge_graph(saved_resources)
        
        # Save graph
        await self._save_knowledge_graph(knowledge_graph)

        self._session.status = "completed"

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Knowledge graph built with {len(knowledge_graph['nodes'])} nodes and {len(knowledge_graph['edges'])} edges",
            metadata={"graph_size": len(knowledge_graph['nodes'])},
        )

    # ── Browser Management ─────────────────────────────────────────────

    async def _init_browser(self):
        """Initialize Playwright browser."""
        if self._browser:
            return

        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        # Prevent bot detection
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        logger.info("Browser initialized for autonomous browsing")

    async def _close_browser(self):
        """Close browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        logger.info("Browser closed")

    # ── Search & Discovery ─────────────────────────────────────────────

    async def _search_topic(self, topic: str) -> list[str]:
        """Search for a topic and return URLs."""
        import asyncio
        from duckduckgo_search import DDGS
        
        urls = []
        try:
            def sync_search():
                res = []
                with DDGS() as ddgs:
                    for result in ddgs.text(topic, max_results=10):
                        res.append(result["href"])
                return res
                
            urls = await asyncio.to_thread(sync_search)
        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", e)
            # Fallback to predefined sources
            urls = await self._get_fallback_urls(topic)
        
        return urls

    async def _get_fallback_urls(self, topic: str) -> list[str]:
        """Get fallback URLs from known sources."""
        from urllib.parse import quote
        
        return [
            f"https://en.wikipedia.org/wiki/{quote(topic)}",
            f"https://developer.mozilla.org/en-US/search?q={quote(topic)}",
            f"https://stackoverflow.com/search?q={quote(topic)}",
            f"https://github.com/search?q={quote(topic)}",
        ]

    async def _generate_seed_urls(self, domain: str) -> list[str]:
        """Generate seed URLs for a domain."""
        domain = domain.lower().strip()
        
        # Common high-quality sources
        seed_urls = []
        
        # Add known documentation/tutorial sites based on domain
        if "python" in domain or "programming" in domain:
            seed_urls.extend([
                "https://docs.python.org/3/",
                "https://realpython.com/",
                "https://pythontutor.com/",
            ])
        elif "javascript" in domain or "web" in domain:
            seed_urls.extend([
                "https://developer.mozilla.org/en-US/",
                "https://javascript.info/",
                "https://web.dev/",
            ])
        elif "ai" in domain or "machine learning" in domain:
            seed_urls.extend([
                "https://arxiv.org/list/cs.AI/recent",
                "https://www.fast.ai/",
                "https://huggingface.co/docs",
            ])
        
        return seed_urls

    # ── Content Extraction ─────────────────────────────────────────────

    async def _visit_and_extract(
        self,
        url: str,
        topic: str,
        depth: int = 1,
        max_depth: int = 3,
    ) -> Optional[DiscoveredResource]:
        """Visit a URL and extract content."""
        if url in self._visited_urls:
            return None
        
        if depth > max_depth:
            return None

        self._visited_urls.add(url)
        logger.info("Visiting [%d/%d]: %s", depth, max_depth, url)

        try:
            page = await self._context.new_page()
            
            # Navigate with timeout
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # Wait for content to load
            await page.wait_for_timeout(2000)

            # Extract content
            title = await page.title()
            content = await self._extract_page_content(page)
            
            if not content or len(content) < 200:
                logger.warning("Insufficient content at %s", url)
                await page.close()
                return None

            # Determine content type
            content_type = await self._classify_content_type(url, title, content)
            
            # Generate summary using LLM
            summary, key_points = await self._summarize_content(content, topic)
            
            # Calculate relevance score
            relevance_score = await self._calculate_relevance(content, topic)

            resource = DiscoveredResource(
                url=url,
                title=title,
                content_type=content_type,
                summary=summary,
                key_points=key_points,
                relevance_score=relevance_score,
                tags=[topic, content_type],
                raw_content=content[:5000],  # Store first 5000 chars
            )

            # Save content snapshot
            await self._save_resource_snapshot(resource)

            # Recursively follow links if depth allows
            if depth < max_depth and relevance_score > 0.6:
                links = await self._extract_links(page, url)
                for link in links[:3]:  # Follow top 3 links
                    await self._visit_and_extract(link, topic, depth + 1, max_depth)

            await page.close()
            return resource

        except Exception as e:
            logger.error("Failed to extract %s: %s", url, e)
            return None

    async def _extract_page_content(self, page: Page) -> str:
        """Extract readable content from page."""
        content = await page.evaluate("""
            () => {
                // Remove navigation, footer, ads
                const elementsToRemove = document.querySelectorAll('nav, footer, header, script, style, noscript, iframe');
                elementsToRemove.forEach(el => el.remove());
                
                // Get main content
                const mainContent = document.querySelector('main, article, #content, .content, .post') || document.body;
                return mainContent ? mainContent.innerText : '';
            }
        """)
        return content

    async def _classify_content_type(self, url: str, title: str, content: str) -> str:
        """Classify the type of content."""
        url_lower = url.lower()
        title_lower = title.lower()
        content_lower = content.lower()
        
        if "tutorial" in url_lower or "how-to" in url_lower or "guide" in url_lower:
            return "tutorial"
        elif "docs" in url_lower or "documentation" in url_lower or "reference" in url_lower:
            return "documentation"
        elif "arxiv" in url_lower or "research" in url_lower or "paper" in title_lower:
            return "research_paper"
        elif "github" in url_lower or "code" in url_lower:
            return "code"
        elif "youtube" in url_lower or "video" in url_lower:
            return "video"
        else:
            return "article"

    async def _summarize_content(self, content: str, topic: str) -> tuple[str, list[str]]:
        """Summarize content using LLM."""
        if not self.llm_router:
            # Fallback: simple extraction
            key_sentences = content.split(".")[:5]
            return content[:500], key_sentences
        
        try:
            prompt = f"""
            Please analyze the following content about "{topic}" and provide:
            1. A concise summary (3-4 sentences)
            2. Key points (bullet list, max 5)

            Content:
            {content[:3000]}

            Response format:
            Summary: [summary here]
            Key Points:
            - [point 1]
            - [point 2]
            - [point 3]
            """
            
            response = await self.llm_router.chat(prompt)
            
            # Parse response
            lines = response.split("\n")
            summary = ""
            key_points = []
            
            in_summary = False
            in_key_points = False
            
            for line in lines:
                if line.startswith("Summary:"):
                    summary = line.replace("Summary:", "").strip()
                    in_summary = True
                    in_key_points = False
                elif line.startswith("Key Points:"):
                    in_summary = False
                    in_key_points = True
                elif in_key_points and line.startswith("- "):
                    key_points.append(line[2:])
                elif in_summary and line.strip():
                    summary += " " + line.strip()
            
            return summary.strip(), key_points[:5]
            
        except Exception as e:
            logger.warning("LLM summarization failed, using fallback: %s", e)
            return content[:500], content.split(".")[:5]

    async def _calculate_relevance(self, content: str, topic: str) -> float:
        """Calculate relevance score of content to topic."""
        if not topic:
            return 0.5
        
        content_lower = content.lower()
        topic_words = topic.lower().split()
        
        # Simple keyword-based relevance
        matches = sum(1 for word in topic_words if word in content_lower)
        relevance = matches / max(len(topic_words), 1)
        
        # Content length bonus (longer content is often better)
        length_bonus = min(len(content) / 5000, 0.3)
        
        return min(relevance + length_bonus, 1.0)

    async def _extract_links(self, page: Page, base_url: str) -> list[str]:
        """Extract relevant links from page."""
        links = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                return links
                    .map(a => a.href)
                    .filter(href => href.startsWith('http') && !href.includes('#'));
            }
        """)
        
        # Filter to same-domain or relevant links
        base_domain = urlparse(base_url).netloc
        relevant_links = []
        
        for link in links:
            link_domain = urlparse(link).netloc
            # Prefer same-domain links
            if link_domain == base_domain:
                relevant_links.append(link)
        
        return relevant_links[:10]

    # ── Memory & Knowledge Storage ─────────────────────────────────────

    async def _save_to_memory(self, resource: DiscoveredResource):
        """Save discovered resource to memory engine."""
        if not self.memory_engine:
            return

        try:
            # Save summary
            await self.memory_engine.store(
                entry_id=f"resource_{resource.content_hash}",
                content=resource.summary,
                entry_type="resource",
                metadata={
                    "url": resource.url,
                    "title": resource.title,
                    "type": resource.content_type,
                    "key_points": resource.key_points,
                    "tags": resource.tags,
                    "relevance": resource.relevance_score,
                },
            )
            logger.info("Saved resource to memory: %s", resource.title)
        except Exception as e:
            logger.error("Failed to save to memory: %s", e)

    async def _save_resource_snapshot(self, resource: DiscoveredResource):
        """Save resource snapshot to disk."""
        snapshot = {
            "url": resource.url,
            "title": resource.title,
            "type": resource.content_type,
            "summary": resource.summary,
            "key_points": resource.key_points,
            "relevance_score": resource.relevance_score,
            "tags": resource.tags,
            "discovered_at": resource.discovered_at.isoformat(),
        }
        
        filename = f"{resource.content_hash}.json"
        filepath = self._knowledge_base_path / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

    async def _save_session_report(self):
        """Save complete session report."""
        if not self._session:
            return

        report = {
            "session_id": self._session.session_id,
            "topic": self._session.topic,
            "start_time": self._session.start_time.isoformat(),
            "end_time": self._session.end_time.isoformat() if self._session.end_time else None,
            "urls_visited": self._session.urls_visited,
            "resources_found": self._session.resources_found,
            "knowledge_saved": self._session.knowledge_saved,
            "insights_generated": self._session.insights_generated,
            "status": self._session.status,
            "error": self._session.error,
            "discovered_resources": [r.__dict__ for r in self._discovered_resources],
        }

        report_path = self._knowledge_base_path / f"session_{self._session.session_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info("Session report saved to %s", report_path)

    async def _retrieve_saved_resources(self) -> list[DiscoveredResource]:
        """Retrieve all saved resources from disk."""
        resources = []
        for filepath in self._knowledge_base_path.glob("*.json"):
            if "session_" in filepath.name:
                continue  # Skip session reports
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    resources.append(DiscoveredResource(**data))
            except Exception as e:
                logger.warning("Failed to load %s: %s", filepath, e)
        
        return resources

    async def _build_knowledge_graph(self, resources: list[DiscoveredResource]) -> dict:
        """Build knowledge graph from resources."""
        nodes = []
        edges = []
        
        for resource in resources:
            # Add node
            nodes.append({
                "id": resource.content_hash,
                "type": resource.content_type,
                "title": resource.title,
                "url": resource.url,
                "tags": resource.tags,
            })
            
            # Add edges based on shared tags
            for other in resources:
                if other.content_hash == resource.content_hash:
                    continue
                
                shared_tags = set(resource.tags) & set(other.tags)
                if shared_tags:
                    edges.append({
                        "source": resource.content_hash,
                        "target": other.content_hash,
                        "relationship": "related_topic",
                        "shared_tags": list(shared_tags),
                    })
        
        return {"nodes": nodes, "edges": edges}

    async def _save_knowledge_graph(self, graph: dict):
        """Save knowledge graph to disk."""
        graph_path = self._knowledge_base_path / "knowledge_graph.json"
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)
        logger.info("Knowledge graph saved with %d nodes", len(graph["nodes"]))

    async def _identify_knowledge_gaps(self) -> list[dict]:
        """Identify gaps in knowledge that need filling."""
        if not self.llm_router or not self.memory_engine:
            return []
        
        # Ask LLM to identify gaps based on current knowledge
        prompt = """
        Based on typical AI assistant knowledge, what are the top 5 topics or areas 
        that are frequently updated or commonly misunderstood?
        
        Return as a JSON list:
        [{"topic": "...", "reason": "...", "priority": 1-10}]
        """
        
        try:
            response = await self.llm_router.chat(prompt)
            # Parse response (simplified - in production use proper JSON parsing)
            return [{"topic": "Latest AI developments", "reason": "Fast-moving field", "priority": 9}]
        except:
            return []

    async def _synthesize_insights(self, resources: list[DiscoveredResource], topic: str) -> list[str]:
        """Synthesize insights from discovered resources."""
        if not self.llm_router or not resources:
            return []
        
        summaries = "\n".join(f"- {r.summary}" for r in resources[:10])
        
        prompt = f"""
        Based on these resources about "{topic}", what are the key insights and patterns?
        
        Resources:
        {summaries}
        
        List 5-10 key insights:
        """
        
        try:
            response = await self.llm_router.chat(prompt)
            return [line.strip() for line in response.split("\n") if line.strip()][:10]
        except:
            return []

    def _generate_research_report(
        self,
        topic: str,
        resources: list[DiscoveredResource],
        insights: list[str],
    ) -> str:
        """Generate a comprehensive research report."""
        report = f"""
# Autonomous Research Report: {topic}

## Summary
Found {len(resources)} resources through autonomous web research.

## Top Resources
"""
        for i, resource in enumerate(resources[:10], 1):
            report += f"""
### {i}. {resource.title}
- **URL:** {resource.url}
- **Type:** {resource.content_type}
- **Relevance:** {resource.relevance_score:.0%}
- **Summary:** {resource.summary}
- **Key Points:**
""" + "\n".join(f"  - {point}" for point in resource.key_points)

        report += f"""

## Key Insights
""" + "\n".join(f"{i}. {insight}" for i, insight in enumerate(insights, 1))

        report += f"""

## Statistics
- URLs Visited: {len(self._session.urls_visited) if self._session else 0}
- Resources Found: {len(resources)}
- Knowledge Saved: {self._session.knowledge_saved if self._session else 0}
"""
        return report
