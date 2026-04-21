"""Core Orchestrator — the central brain that routes tasks to agents."""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ultron.v2.core.types import AgentRole, Task, TaskResult, TaskStatus
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter
from ultron.v2.core.hermes import HermesExecutionLoop
from ultron.v2.memory.engine import MemoryEngine
from ultron.v2.agents.coder import CoderAgent
from ultron.v2.agents.researcher import ResearcherAgent
from ultron.v2.agents.rpa_operator import RPAOperatorAgent
# ── Yeni Agentlar ─────────────────────────────────────
from ultron.v2.agents.email_agent import EmailAgent
from ultron.v2.agents.sysmon_agent import SystemMonitorAgent
from ultron.v2.agents.clipboard_agent import ClipboardAgent
from ultron.v2.agents.meeting_agent import MeetingAgent
from ultron.v2.agents.files_agent import FilesAgent
from ultron.v2.agents.error_analyzer import ErrorAnalyzerAgent
from ultron.v2.agents.vision_agent import UltronVisionAgent
from ultron.v2.agents.architect import AgentArchitect
from ultron.v2.agents.debate_agent import DebateAgent
from ultron.v2.agents.cloner import ClonerAgent
from ultron.v2.agents.whatsapp_agent import WhatsAppAgent
from ultron.v2.agents.gaming_agent import GamingAgent
from ultron.v2.agents.resource_agent import ResourceAgent

# ── AGI Core Modules ──────────────────────────────────────
from ultron.v2.core.reasoning_engine import ReasoningEngine
from ultron.v2.core.planner import Planner
from ultron.v2.core.security import SecurityManager
from ultron.v2.core.self_improvement import SelfImprovementEngine
from ultron.v2.mcp.bridge import MCPBridge
from ultron.v2.mcp.lifecycle import MCPClusterManager
from ultron.v2.mcp.loader import load_mcp_settings
from ultron.v2.core.nexus import UltronNexus
from ultron.v2.core.knowledge import LocalKnowledgeEngine
from ultron.v2.core.context import context_manager

logger = logging.getLogger(__name__)


def _default_disk_usage_path() -> str:
    """Windows'ta '/' güvenilir olmayabilir; sistem sürücüsünü kullan."""
    if os.name == "nt":
        return os.environ.get("SystemDrive", "C:") + "\\"
    return "/"


# ─── Skill & Agent Discovery ────────────────────────────────────────────────

from ultron.v2.core.skill_manager import discover_all_skills, discover_all_agents # type: ignore

def _discover_skills() -> list[dict]:
    """Discover all skills from all known directories."""
    return discover_all_skills()

def _discover_agents() -> list[dict]:
    """Discover all agents from all known directories."""
    return discover_all_agents()


# Keyword → intent mapping for fast routing
INTENT_KEYWORDS = {
    "autonomous": [
        "otonom", "autonomous", "işi bitir", "görevi tamamla", "kendi kendine yap",
        "openclaw", "plan yap ve uygula", "multi-step goal", "hedefi tamamla",
    ],
    "gamedev": [
        "ue5", "unreal engine", "unreal", "blueprint", "oyun geliştirme", "game dev",
        "level design", "gameplay", "oyun tasarımı",
    ],
    "code": ["kod yaz", "kod", "yazılım", "program", "python", "javascript", "function", "script",
             "calculate", "hesapla", "debug", "hata ayıkla", "çalıştır", "execute", "code"],
    "research": ["araştır", "research", "bul", "search", "nedir", "what is", "explain",
                 "açıkla", "öğren", "learn", "about", "hakkında", "scrape", "çal", "profil", "ekstrak"],
    "weather": ["hava durumu", "weather", "saat kaç", "saat", "time", "sıcaklık", "temperature", "yağmur", "rain",
                "kar", "snow", "güneşli", "sunny", "bulutlu", "cloudy", "rüzgar", "wind"],
    "app": ["aç", "open", "başlat", "start", "launch", "çalıştır", "run", "uygulama", "app",
            "program", "exe", "steam", "chrome", "spotify", "discord", "notepad",
            "youtube", "twitter", "x.com", "reddit", "github", "gmail", "google",
            "netflix", "amazon", "git", "pc"],
    "system": ["sistem", "system", "cpu", "ram", "disk", "batarya", "battery",
               "durum", "status", "kullanım", "usage", "yüzde", "%", "kaynak"],
    "file": ["dosya", "file", "oku", "okum", "read", "yaz", "write", "kaydet", "save", "oluştur",
             "create", "listele", "list", "klasör", "folder", "dizin", "directory", "bul"],
    "email": ["email", "e-posta", "mail", "gelen kutusu", "inbox", "mesaj oku",
              "mail gönder", "taslak", "draft"],
    "meeting": ["toplantı", "meeting", "transkript", "kaydet", "record meeting",
                "dikte", "ses kaydı", "voice note"],
    "clipboard": ["pano", "clipboard", "kopyala", "paste", "yapıştır", "kod analiz",
                  "code review bu kodu"],
    "debate": ["tartış", "fikir bul", "en iyisini bul", "debate", "karşılaştır"],
    "clone": ["clone", "klonla", "site kopyala", "web sitesi", "website", "arayüz", "ui"],
    "architect": ["mimar", "architect", "ajan oluştur", "create agent", "skill yaz", "yeni uzman", "indeksle", "index library", "proje oluştur", "uygulama yap", "site yap", "oyun yap", "mobil uygulama", "build project", "create app"],
    "whatsapp": ["whatsapp", "mesaj gönder", "wp", "yaz", "send message", "mesaj at"],
    "gaming": ["lol", "league of legends", "tft", "teamfight tactics", "comp", "taktik", "oyun taktik", "meta", "tier", "build"],
    "discover": ["skill bul", "yetenek ekle", "install skill", "nexus", "mcp server bul", "yeni araç ekle"],
    "resource": ["kaynak bul", "ai kaynak", "resource", "free ai", "ücretsiz yapay zeka", "model bul", "dataset", "veri seti"],
}


class Orchestrator:
    """Central orchestrator for the Ultron multi-agent system.

    Responsibilities:
    1. Parse user intent
    2. Decompose complex tasks into subtasks
    3. Assign subtasks to specialized agents
    4. Execute agents in parallel when possible
    5. Aggregate results
    6. Store lessons from failures
    7. Return unified response
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        memory: MemoryEngine,
        work_dir: str = "./workspace",
    ) -> None:
        self.llm_router = LLMRouter(
            # Using 14B or larger for orchestrator if hardware allows
            ollama_model="qwen2.5-coder:14b",  # Core model reverted to 14b for speed/intelligence balance
            ollama_base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        )
        self.llm_router.enable_all_providers(dict(os.environ))
        self.memory = memory
        self.event_bus = EventBus()
        self.blackboard = Blackboard()

        # Dedicated LLM Routers per agent
        self.coder_llm_router = LLMRouter(
            ollama_model="qwen2.5-coder:7b",  # Coder keeps 7b for speed; cloud fallback for complex tasks
        )
        # Enable ALL cloud providers on coder router for maximum fallback options
        coder_env = dict(os.environ)
        self.coder_llm_router.enable_all_providers(coder_env)

        # RPA + Researcher use the main router (qwen2.5-coder:14b — the new default)

        # Initialize agents
        self.agents: dict[AgentRole, Any] = {}
        self.knowledge = LocalKnowledgeEngine(self.memory)
        self._init_agents(work_dir)
        self._load_custom_agents(work_dir)

        # Discover skills and agents
        self._skills = _discover_skills()
        self._agents_discovered = _discover_agents()
        logger.info("Discovered %d skills, %d agents", len(self._skills), len(self._agents_discovered))

        self._running = False
        self._task_queue: asyncio.Queue[Task] = asyncio.Queue()

        # -- AGI Core Systems -------------------------------------
        self.reasoning = ReasoningEngine(llm_router=self.llm_router, memory=self.memory)
        self.planner = Planner(llm_router=self.llm_router, memory=self.memory)
        self.security = SecurityManager(audit_dir="./data/audit")
        self.self_improvement = SelfImprovementEngine(
            llm_router=self.llm_router,
            memory=self.memory,
            data_dir="./data/self_improvement",
        )
        logger.info(
            "AGI core systems initialized: Reasoning=%s, Planner=%s, Security=%s, SelfImprovement=%s",
            type(self.reasoning).__name__,
            type(self.planner).__name__,
            type(self.security).__name__,
            type(self.self_improvement).__name__,
        )
        self._active_tasks: dict[str, Task] = {}

        self.hermes_tools: list = []  # Populated dynamically per session

        # ── MCP & Skill Management ──────────────────────────────────
        self._work_dir = work_dir
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        config_path = project_root / "config" / "mcp.yaml"
        _mcp_cfg = load_mcp_settings(workspace_dir=work_dir, config_path=config_path)
        self.mcp_manager = MCPClusterManager(_mcp_cfg, config_path=config_path)
        self.mcp_bridge = MCPBridge(self.mcp_manager, security=self.security)
        
        # Connect Sampling handlers
        self.mcp_manager.set_sampling_handler(self.mcp_bridge.handle_sampling_request)
        self.mcp_bridge.set_sampling_callback(self._handle_mcp_sampling)
        
        self.nexus = UltronNexus(self.mcp_manager)

    def _should_auto_use_mcp_in_chat(self, user_input: str) -> bool:
        """Heuristic gate for MCP tool injection during normal chat."""
        import os
        if os.getenv("ULTRON_MCP_AUTO_INJECT", "1").strip().lower() in ("0", "false", "no", "off"):
            return False
        if not self.mcp_manager.enabled:
            return False
        if not self.mcp_bridge.has_tools():
            return False

        s = user_input.lower()

        # Strong signals: explicit tooling / project inspection
        if any(x in s for x in ("/mcp", "mcp", "tool", "araç", "server", "sunucu")):
            return True
        if any(x in s for x in ("dosya", "file", "klasör", "folder", "dizin", "directory", "repo", "proje", "kod tabanı", "codebase")):
            return True
        if any(x in s for x in ("config", "yaml", "yml", "toml", "json", "pyproject", "readme")):
            return True
        if any(ext in s for ext in (".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg")):
            return True
        if "\\" in user_input or "/" in user_input:
            return True
        if any(x in s for x in ("sqlite", "db", "veritaban", "database", "chroma", "log", "stack trace", "traceback")):
            return True

        return False

    def _init_agents(self, work_dir: str) -> None:
        """Initialize all specialized agents."""
        self.agents[AgentRole.CODER] = CoderAgent(
            llm_router=self.coder_llm_router,
            event_bus=self.event_bus,
            blackboard=self.blackboard,
            work_dir=work_dir,
        )

        self.agents[AgentRole.RESEARCHER] = ResearcherAgent(
            llm_router=self.llm_router,
            event_bus=self.event_bus,
            blackboard=self.blackboard,
            memory=self.memory,
        )

        self.agents[AgentRole.RPA_OPERATOR] = RPAOperatorAgent(
            llm_router=self.llm_router,
            event_bus=self.event_bus,
            blackboard=self.blackboard,
        )

        # ── Yeni Agentlar ──────────────────────────────────
        try:
            self.agents[AgentRole.EMAIL] = EmailAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize EmailAgent: %s", e)

        try:
            self.agents[AgentRole.ARCHITECT] = AgentArchitect(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
                knowledge_engine=self.knowledge
            )
        except Exception as e:
            logger.warning("Failed to initialize AgentArchitect: %s", e)

        try:
            self.agents[AgentRole.SYSMON] = SystemMonitorAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize SystemMonitorAgent: %s", e)

        try:
            self.agents[AgentRole.CLIPBOARD] = ClipboardAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize ClipboardAgent: %s", e)

        try:
            self.agents[AgentRole.CLONER] = ClonerAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize ClonerAgent: %s", e)

        try:
            self.agents[AgentRole.GAMING] = GamingAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize GamingAgent: %s", e)
        try:
            self.agents[AgentRole.RESOURCER] = ResourceAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize ResourceAgent: %s", e)

    def _load_custom_agents(self, work_dir: str) -> None:
        """Dynamically load custom agents from workspace/agents."""
        custom_agents_dir = Path(work_dir) / "agents"
        if not custom_agents_dir.exists():
            return

        for item in custom_agents_dir.iterdir():
            if item.is_dir() and (item / "agent.json").exists():
                logger.info(f"Detected custom agent: {item.name}")
                # Logic for dynamic loading of custom agent classes would go here
                # For now, we register them as discoverable skills

        try:
            self.agents[AgentRole.MEETING] = MeetingAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize MeetingAgent: %s", e)

        try:
            self.agents[AgentRole.FILES] = FilesAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize FilesAgent: %s", e)

        # Initialize Error Analyzer Agent (for self-healing)
        try:
            self.error_analyzer = ErrorAnalyzerAgent(llm_router=self.llm_router)
            logger.info("✓ ErrorAnalyzerAgent initialized (self-healing enabled)")
        except Exception as e:
            logger.warning("Failed to initialize ErrorAnalyzerAgent: %s", e)
            self.error_analyzer = None

        try:
            self.agents[AgentRole.VISION] = UltronVisionAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize UltronVisionAgent: %s", e)

        try:
            self.agents[AgentRole.DEBATE] = DebateAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize DebateAgent: %s", e)

        try:
            self.agents[AgentRole.WHATSAPP] = WhatsAppAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize WhatsAppAgent: %s", e)

        logger.info("Initialized %d agents", len(self.agents))

    async def start(self) -> None:
        """Start the orchestrator and all agents."""
        self._running = True
        for role, agent in self.agents.items():
            try:
                await agent.start()
                role_name = role.value if hasattr(role, 'value') else str(role)
                logger.info("Agent started: %s", role_name)
            except Exception as e:
                role_name = role.value if hasattr(role, 'value') else str(role)
                logger.warning("Agent failed to start (non-fatal): %s — %s", role_name, e)

        try:
            await self.mcp_manager.start()
            await self.mcp_bridge.refresh_tool_catalog()
        except Exception as e:
            logger.warning("MCP başlatma / katalog: %s", e)

        # Log memory stats
        try:
            stats = self.memory.stats()
            logger.info("Memory engine: %s", stats)
        except Exception as e:
            logger.warning("Memory stats failed (non-fatal): %s", e)

    async def stop(self) -> None:
        """Stop all agents and clean up resources."""
        self._running = False
        try:
            await self.mcp_manager.stop()
        except Exception as e:
            logger.warning("MCP durdurma: %s", e)
        for role, agent in self.agents.items():
            try:
                await agent.stop()
            except Exception as e:
                role_name = role.value if hasattr(role, "value") else str(role)
                logger.warning("Error stopping agent %s: %s", role_name, e)
        logger.info("Orchestrator stopped")

    async def _handle_mcp_sampling(self, prompt: str, max_tokens: int) -> str:
        """Central LLM handler for MCP sampling requests."""
        # Use the main router but keep it focused
        messages = [
            {"role": "system", "content": "You are a sub-module of Ultron AGI. A connected tool/server needs your help to process data. Be concise and accurate."},
            {"role": "user", "content": prompt}
        ]
        try:
            # We use qwen2.5:14b or similar as default for reasoning
            # Fast/Cheap model config for sub-tasks can be overridden by tools
            resp = await self.llm_router.chat(messages, max_tokens=max_tokens)
            return resp.content
        except Exception as e:
            logger.error("Orchestrator sampling failed: %s", e)
            return f"Sampling error: {str(e)}"
            self.event_bus._global_handlers.clear()
        logger.info("Orchestrator stopped")

    async def process(self, user_input: str, context: Optional[dict] = None, _depth: int = 0) -> str:
        """Process a user request end-to-end.

        Flow:
        1. Intent classification
        2. Task decomposition
        3. Agent assignment
        4. Parallel execution
        5. Result aggregation
        6. Response generation

        Args:
            _depth: Internal recursion guard. Do not set externally.
        """
        # SECURITY: Scan for prompt injection
        is_malicious, reason = self.security.scan_prompt(user_input)
        if is_malicious:
            logger.warning("SECURITY: Blocked prompt injection attempt. Reason: %s", reason)
            return f"Güvenlik uyarısı: İsteğiniz potansiyel olarak zararlı bir kalıp içerdiği için reddedildi ({reason})."

        try:
            return await self._process_inner(user_input, context, _depth)
        except Exception as e:
            logger.exception("Orchestrator.process failed: %s", e)
            return (
                "İsteği işlerken beklenmeyen bir hata oluştu. "
                f"Teknik ayrıntı: {e}"
            )

    async def _process_inner(
        self,
        user_input: str,
        context: Optional[dict],
        _depth: int,
    ) -> str:
        """process() gövdesi — üst seviyede try/except ile sarılmış."""
        stripped = user_input.strip()
        if stripped.lower().startswith("/mcp "):
            user_input = stripped[5:].lstrip()
            context = dict(context) if context else {}
            context["intent"] = {"type": "mcp", "subtasks": [user_input]}

        # Get relevant lessons from memory
        lesson_context = self.memory.get_lesson_context(user_input)

        # Step 1: Classify intent (keyword-based, fast)
        if context and context.get("intent"):
            intent = context["intent"]
        else:
            intent = self._classify_intent_fast(user_input)
            # If fast classifier matched a non-chat intent, verify with LLM
            # for ambiguous cases where confidence might be low
            if intent.get("type") != "chat":
                # For potentially ambiguous inputs, let LLM confirm
                llm_intent = await self._classify_intent(user_input)
                # If LLM disagrees (says chat but fast said something else), trust LLM
                if llm_intent.get("type") == "chat" and intent.get("type") != "chat":
                    input_lower = user_input.lower()
                    # Check if the fast match was on short/ambiguous keywords
                    matched_short_kw = any(
                        len(kw.lower()) <= 3 and kw.lower() in input_lower
                        for kw in INTENT_KEYWORDS.get(intent.get("type", ""), [])
                    )
                    # Also override if the system intent was set by the special-case
                    # fast path (which uses generic tokens like 'durum', 'kaç')
                    is_system_fast = intent.get("_system_fast", False)
                    if matched_short_kw or is_system_fast:
                        logger.info("Fast→LLM override: %s → %s", intent.get("type"), llm_intent.get("type"))
                        intent = llm_intent

        logger.info("Intent: %s", intent)

        # Step 2: Route to appropriate agent(s)
        import time
        start_time = time.monotonic()
        
        if intent.get("type") == "code":
            result = await self._execute_code_task(user_input, intent, lesson_context)
            agent_name = "coder"
        elif intent.get("type") == "architect":
            result = await self._execute_architect_task(user_input, intent, lesson_context)
            agent_name = "architect"
        elif intent.get("type") == "research":
            result = await self._execute_research_task(user_input, intent, lesson_context)
            agent_name = "researcher"
        elif intent.get("type") == "weather":
            result = await self._execute_weather_task(user_input, intent, lesson_context)
            agent_name = "weather_service"
        elif intent.get("type") == "system":
            result = await self._execute_system_task(user_input, intent, lesson_context)
            agent_name = "sysmon"
        elif intent.get("type") == "file":
            result = await self._execute_file_task(user_input, intent, lesson_context)
            agent_name = "files"
        elif intent.get("type") in ("rpa", "app"):
            result = await self._execute_rpa_task(user_input, intent, lesson_context)
            agent_name = "rpa"
        elif intent.get("type") == "autonomous":
            result = await self._execute_autonomous_task(user_input, intent, lesson_context, _depth=_depth)
            agent_name = "orchestrator"
        elif intent.get("type") == "gamedev":
            result = await self._execute_gamedev_task(user_input, intent, lesson_context)
            agent_name = "gamedev_specialist"
        elif intent.get("type") == "mcp":
            result = await self._execute_mcp_chat_task(user_input, intent, lesson_context)
            agent_name = "mcp_bridge"
        elif intent.get("type") == "multi":
            result = await self._execute_multi_task(user_input, intent, lesson_context, _depth=_depth)
            agent_name = "orchestrator_multi"
        elif intent.get("type") == "email":
            result = await self._execute_email_task(user_input, intent, lesson_context)
            agent_name = "email"
        elif intent.get("type") == "clipboard":
            result = await self._execute_clipboard_task(user_input, intent, lesson_context)
            agent_name = "clipboard"
        elif intent.get("type") == "meeting":
            result = await self._execute_meeting_task(user_input, intent, lesson_context)
            agent_name = "meeting"
        elif intent.get("type") == "debate":
            result = await self._execute_debate_task(user_input, intent, lesson_context)
            agent_name = "debate_engine"
        elif intent.get("type") == "skill":
            result = await self._execute_skill_task(user_input, intent, lesson_context)
            agent_name = "skill_executor"
        elif intent.get("type") == "agent":
            result = await self._execute_discovered_agent_task(user_input, intent, lesson_context)
            agent_name = "dynamic_agent"
        elif intent.get("type") == "whatsapp":
            result = await self._execute_whatsapp_task(user_input, intent, lesson_context)
            agent_name = "whatsapp"
        elif intent.get("type") == "discover":
            result = await self._execute_discovery_task(user_input, intent, lesson_context)
            agent_name = "discovery"
        elif intent.get("type") == "gaming":
            result = await self._execute_gaming_task(user_input, intent, lesson_context)
            agent_name = "gaming"
        elif intent.get("type") == "resource":
            result = await self._execute_resource_task(user_input, intent, lesson_context)
            agent_name = "resourcer"
        else:
            # General chat
            history = context.get("history", []) if context else []
            result = await self._general_chat(user_input, lesson_context, history=history)
            agent_name = "chat"

        # Record outcome for self-improvement
        latency_ms = (time.monotonic() - start_time) * 1000
        success = "hata" not in result.lower() and "failed" not in result.lower()
        self.self_improvement.record_task_outcome(
            agent_name=agent_name,
            task_description=user_input,
            success=success,
            latency_ms=latency_ms,
            error=result if not success else ""
        )

        # -- Autonomous Self-Healing Loop --
        # Using a direct __dict__ check or hasattr for maximum safety against out-of-sync .pyc files
        error_handler = getattr(self, 'error_analyzer', None)
        if not success and error_handler:
            logger.warning("Task failed. Triggering autonomous self-healing for: %s", agent_name)
            healing_result = await self._autonomous_self_heal(user_input, result, agent_name)
            if healing_result:
                logger.info("✓ Self-healing successful! Retrying task...")
                # Re-run the task with the fix applied
                # Note: We only retry once to avoid infinite loops
                result = await self.process(user_input, context, _depth=_depth + 1)
                return result

        # Store interaction in memory
        try:
            self.memory.store(
                entry_id=f"interaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                content=f"User: {user_input}\nResponse: {str(result)[:500]}",
                entry_type="episodic",
                metadata={"intent": intent.get("type")},
            )
            # PROACTIVE LEARNING: Extract facts and store conversation milestone
            if len(user_input) > 20:
                asyncio.create_task(self._extract_and_store_facts(user_input, result))
                # If interaction was significant, create a milestone memory
                if len(result) > 500 or "learned" in result.lower() or "öğrendim" in result.lower():
                    asyncio.create_task(self._extract_knowledge_milestone(user_input, result))
        except Exception as e:
            logger.warning("Memory store after interaction failed: %s", e)

        return result

    async def _autonomous_self_heal(self, user_input: str, error_msg: str, agent_name: str) -> bool:
        """Analyze error, apply fix, and return True if retry is warranted."""
        try:
            # 1. Analyze error
            analysis = await self.error_analyzer.analyze_error(error_msg, code_context=user_input)
            
            if analysis.confidence > 0.6 and analysis.fix_suggestion:
                logger.info("Healing strategy: %s (Confidence: %.2f)", analysis.fix_suggestion, analysis.confidence)
                
                # 2. If it's a code/configuration error, try to apply a fix
                if analysis.affected_files:
                    for file_path in analysis.affected_files:
                        if os.path.exists(file_path):
                            file_content = Path(file_path).read_text(encoding="utf-8")
                            fix_code = await self.error_analyzer.generate_fix(analysis, file_content)
                            if fix_code:
                                success = await self.error_analyzer.apply_fix(file_path, fix_code)
                                if success:
                                    logger.info("Applied fix to: %s", file_path)
                                    return True
                
                # 3. If it's a transient or routing error, try adjusting the blackboard/context
                await self.blackboard.write(f"healing_{agent_name}_attempt", {
                    "error": error_msg,
                    "suggestion": analysis.fix_suggestion,
                    "timestamp": datetime.now().isoformat()
                }, owner="orchestrator", ttl_seconds=3600)
                
                # If we have a clear suggestion but no file to fix, 
                # we might still want to retry with different parameters
                return True
                
        except Exception as e:
            logger.error("Autonomous healing failed: %s", e)
        
        return False

    async def _extract_and_store_facts(self, user_input: str, assistant_response: str) -> None:
        """Background task to extract and store facts into Knowledge Graph."""
        prompt = [
            {"role": "system", "content": "Extract key facts, user preferences, or technical information from this exchange. Return JSON list: [{\"fact\": \"...\", \"relation\": \"...\", \"target\": \"...\"}]"},
            {"role": "user", "content": f"User: {user_input}\nAssistant: {assistant_response}"}
        ]
        try:
            resp = await self.llm_router.chat(prompt, max_tokens=300)
            json_match = re.search(r"\[[\s\S]*\]", resp.content)
            if json_match:
                facts = json.loads(json_match.group())
                for f in facts:
                    fact_text = f.get("fact", "")
                    if fact_text:
                        # Store in graph
                        self.memory.add_concept(fact_text, category="extracted_fact")
                        if f.get("target") and f.get("relation"):
                            self.memory.add_relationship(fact_text, f["target"], f["relation"])
                        
                        # Also store in vector memory for semantic retrieval
                        self.memory.store(
                            entry_id=f"fact_{hashlib.md5(fact_text.encode()).hexdigest()[:8]}",
                            content=fact_text,
                            entry_type="semantic",
                            metadata={"source": "extraction", "user_input": user_input[:100]}
                        )
                logger.info("Extracted and stored %d facts from conversation", len(facts))
        except Exception as e:
            logger.debug("Fact extraction failed: %s", e)

    async def _extract_knowledge_milestone(self, user_input: str, assistant_response: str) -> None:
        """Create a high-level summary of a significant interaction for long-term recall."""
        prompt = [
            {"role": "system", "content": "Summarize the key takeaway, result, or knowledge gained from this interaction in one concise sentence. Focus on 'What happened?' and 'What was achieved?'"},
            {"role": "user", "content": f"User: {user_input}\nAssistant: {assistant_response}"}
        ]
        try:
            resp = await self.llm_router.chat(prompt, max_tokens=200)
            milestone = resp.content.strip()
            if milestone:
                self.memory.store(
                    entry_id=f"milestone_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    content=milestone,
                    entry_type="milestone",
                    metadata={"importance": 0.8}
                )
                logger.info("Milestone memory stored: %s", milestone[:50])
        except Exception as e:
            logger.debug("Milestone extraction failed: %s", e)


    async def _execute_resource_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        agent = self.agents.get(AgentRole.RESOURCER)
        if not agent:
            return "ResourceAgent aktif değil."
        task = Task(description=user_input, intent="resource", context={"lesson_context": lesson_context})
        result = await agent.execute(task)
        return result.output

    def _classify_intent_fast(self, user_input: str) -> dict:
        """Fast keyword-based intent classification with word-boundary awareness."""
        input_lower = user_input.lower()
        # Tokenize into words for better matching (split on whitespace and punctuation)
        tokens = set(re.findall(r'[a-zçğıöşü]+', input_lower))

        # ── Conversational blocklist ──────────────────────────────────────
        # If user is clearly just chatting, skip all action intents.
        CONVERSATIONAL_PATTERNS = (
            "nasılsın", "naber", "selam", "merhaba", "günaydın", "iyi akşamlar",
            "ne düşünüyorsun", "ne yapıyorsun", "sen kimsin", "adın ne",
            "nasıl gidiyor", "ne haber", "seni seviyorum", "teşekkür",
            "sağol", "eyvallah", "tamam", "anladım", "güzel", "harika",
            "how are you", "what's up", "who are you", "hello", "hi there",
            "thank you", "thanks", "good morning", "good night",
            "ne biliyorsun", "bana anlat", "ne yapabilirsin",
        )
        if any(pat in input_lower for pat in CONVERSATIONAL_PATTERNS):
            return {"type": "chat", "subtasks": [user_input]}

        # ── System intent (special-case with strict gating) ──────────────
        # Require a hardware metric keyword *and* a system-specific verb/noun.
        # Removed 'ne' — far too generic and matches every Turkish question.
        system_metric = any(w in tokens for w in ("cpu", "ram", "disk", "batarya", "battery"))
        system_query = any(w in tokens for w in ("durum", "status", "kullanım", "usage", "yüzde", "kaç"))
        if system_metric and system_query:
            return {"type": "system", "subtasks": [user_input], "_system_fast": True}
        # Also catch direct system commands like "sistem durumu", "cpu kullanımı"
        system_phrases = ("sistem durumu", "system status", "cpu kullanımı", "ram kullanımı", "disk kullanımı")
        if any(phrase in input_lower for phrase in system_phrases):
            return {"type": "system", "subtasks": [user_input], "_system_fast": True}

        # ── General keyword matching ─────────────────────────────────────
        for intent_type, keywords in INTENT_KEYWORDS.items():
            # system intent is handled above with extra gating
            if intent_type == "system":
                continue
            for kw in keywords:
                kw_lower = kw.lower()
                # Multi-word phrases: check as phrase in input
                if " " in kw_lower or "-" in kw_lower:
                    if kw_lower in input_lower:
                        return {"type": intent_type, "subtasks": [user_input]}
                # Short keywords (≤4 chars): require exact token match (word boundary)
                elif len(kw_lower) <= 4:
                    if kw_lower in tokens:
                        return {"type": intent_type, "subtasks": [user_input]}
                # Longer keywords: substring match is safe enough
                elif kw_lower in input_lower:
                    return {"type": intent_type, "subtasks": [user_input]}

        # Check if skills or discovered agents match
        for skill in self._skills:
            if any(kw in input_lower for kw in skill["name"].lower().split("_")):
                return {"type": "skill", "skill": skill["name"], "subtasks": [user_input]}

        for agent in self._agents_discovered:
            if any(kw in input_lower for kw in agent["name"].lower().split("_")):
                return {"type": "agent", "agent": agent["name"], "subtasks": [user_input]}

        return {"type": "chat", "subtasks": [user_input]}


    async def _classify_intent(self, user_input: str) -> dict:
        """Use LLM to classify user intent with 'Direct Module Execution' support."""
        # ── Step 1: Command Prefix Logic ──
        if user_input.startswith("/") or user_input.startswith("!"):
            cmd = user_input[1:].split()[0].lower()
            cmd_map = {
                "search": "research", "ara": "research", "araştır": "research",
                "code": "code", "kod": "code", "yaz": "code",
                "scrape": "research", "çal": "research", "profil": "research",
                "sys": "system", "sistem": "system",
                "rpa": "rpa", "yap": "rpa",
                "debate": "debate", "tartış": "debate",
                "architect": "architect", "mimar": "architect",
                "auto": "autonomous", "otonom": "autonomous"
            }
            if cmd in cmd_map:
                logger.info("Direct Command Execution detected: %s -> %s", cmd, cmd_map[cmd])
                return {"type": cmd_map[cmd], "subtasks": [user_input], "requires_parallel": False}

        # ── Step 2: Zero-Shot LLM Classification ──
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Ultron AGI Routing Engine. Classify the user's intent precisely.\n\n"
                    "CATEGORIES:\n"
                    "- 'code': Programming, script writing, debugging.\n"
                    "- 'research': Web searching, data scraping, profile extraction, investigative lookups.\n"
                    "- 'architect': Building new agents, indexing libraries, creating full projects/apps.\n"
                    "- 'rpa': Interacting with desktop apps, opening websites, GUI control.\n"
                    "- 'system': CPU/RAM/Battery monitoring, system logs.\n"
                    "- 'email': Managing outlook/gmail accounts.\n"
                    "- 'meeting': Transcribing or summarizing audio/meetings.\n"
                    "- 'file': Managing local files and folders.\n"
                    "- 'debate': Multi-agent brainstorming or comparison.\n"
                    "- 'chat': General talk, opinions, or simple questions.\n\n"
                    "Output JSON ONLY: {\"type\": \"...\", \"confidence\": 0.0-1.0}"
                ),
            },
            {"role": "user", "content": user_input},
        ]

        try:
            response = await self.llm_router.chat(messages, max_tokens=200)
            json_match = re.search(r"\{[\s\S]*\}", response.content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning("Intent classification failed: %s", e)

        # Default to chat
        return {"type": "chat", "subtasks": [user_input], "requires_parallel": False}

    async def _execute_autonomous_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
        _depth: int,
    ) -> str:
        """OpenClaw-benzeri otonomi: hedef → LLM planı → Planner ile adım adım yürütme."""
        try:
            plan = await self.planner.create_plan(
                user_input,
                context={"lesson_context": lesson_context},
                max_sub_goals=6,
                max_steps_per_goal=8,
            )
            await self.planner.execute_plan(
                plan,
                orchestrator=self,
                process_depth=max(_depth, 0),
            )
            lines: list[str] = [plan.to_readable(), "", "— Adım çıktıları —"]
            for sg in plan.sub_goals:
                for st in sg.steps:
                    status = getattr(st.status, "value", str(st.status))
                    lines.append(f"[{status}] {st.description}")
                    if st.result:
                        lines.append(f"  → {str(st.result)[:600]}")
                    if st.error:
                        lines.append(f"  ! {st.error[:400]}")
            return "\n".join(lines)
        except Exception as e:
            logger.exception("Autonomous execution failed")
            return (
                "Otonom görev akışı tamamlanamadı. Daha küçük alt görevlere böylebilir veya "
                f"'/research' ile bilgi toplayabilirsiniz. Ayrıntı: {e}"
            )

    async def _execute_gamedev_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """UE5 / Blueprint / oyun tasarımı — paketlenmiş SKILL + LLM."""
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent.parent.parent
        skill_md = root / "skills" / "game_dev_unreal_blueprint" / "SKILL.md"
        bundle = (
            skill_md.read_text(encoding="utf-8", errors="replace")
            if skill_md.is_file()
            else (
                "UE5 Blueprint: Event Graph, Custom Events, Interfaces, Gameplay Tags, "
                "Enhanced Input, Subsystems, GAS (Ability System) üst düzey kalıplar; "
                "C++ modülü ile Blueprint köprüsü (UFUNCTION, UPROPERTY)."
            )
        )
        if lesson_context:
            bundle = f"{bundle}\n\nGeçmiş dersler / bağlam:\n{lesson_context[:2000]}"
        messages = [
            {
                "role": "system",
                "content": (
                    "Sen kıdemli bir oyun mühendisisin (Unreal Engine 5, Blueprint, performans, "
                    "çok oyunculu mimari). Türkçe yanıt ver; kod ve node isimlerini İngilizce UE API "
                    "ile tutarlı kullan. Aşağıdaki dahili rehbere uy:\n\n"
                    f"{bundle[:14000]}"
                ),
            },
            {"role": "user", "content": user_input},
        ]
        try:
            response = await self.llm_router.chat(messages, temperature=0.35, max_tokens=4096)
            return response.content
        except Exception as e:
            logger.warning("Game dev LLM path failed: %s", e)
            return f"Oyun geliştirme yanıtı üretilemedi: {e}"

    async def _execute_mcp_chat_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """MCP araçları + LLMRouter çok tur tool döngüsü (`/mcp ...`)."""
        if not self.mcp_bridge.has_tools():
            err = self.mcp_manager.errors
            return (
                "MCP araçları kullanılamıyor. `config/mcp.yaml` dosyasını oluşturun "
                "(şablon: `config/mcp.template.yaml`), `enabled: true` yapın ve "
                "`npx`/Node ile örn. `@modelcontextprotocol/server-filesystem` tanımlayın. "
                f"Sunucu hataları: {err or 'yok'}"
            )
        sys_parts = [
            "Yerel MCP sunucularından gelen araçları kullanarak yanıtla.",
            "Türkçe özet ver; dosya yollarında workspace sınırlarına uy.",
        ]
        if lesson_context:
            sys_parts.append(f"Bağlam:\n{lesson_context[:4000]}")
        messages: list[dict[str, str]] = [
            {"role": "system", "content": "\n\n".join(sys_parts)},
            {"role": "user", "content": user_input},
        ]
        try:
            r = await self.llm_router.chat_with_mcp_tool_loop(
                messages,
                self.mcp_bridge,
                max_tool_rounds=8,
                temperature=0.25,
                max_tokens=4096,
            )
            return (r.content or "").strip() or "(MCP yanıtı boş)"
        except Exception as e:
            logger.exception("MCP sohbet akışı")
            return f"MCP / LLM araç döngüsü hatası: {e}"

    async def _execute_architect_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """Execute via AgentArchitect for agent creation and library indexing."""
        agent = self.agents["architect"]
        # Look for directory paths in the input for indexing
        path_match = re.search(r'([A-Za-z]:\\[^ ]+|/[^ ]+)', user_input)
        path = path_match.group(0) if path_match else None
        
        task = Task(
            description=user_input,
            intent="architect",
            context={"lesson_context": lesson_context}
        )
        res = await agent.execute(task)
        return res.output

    async def _execute_gaming_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        agent = self.agents.get(AgentRole.GAMING)
        if not agent:
            return "Oyun Asistanı şu an aktif değil."
        task = Task(description=user_input, intent="gaming")
        res = await agent.execute(task)
        return res.output

    async def _execute_code_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """Execute via CoderAgent with self-healing loop."""
        agent = self.agents[AgentRole.CODER]
        # Default to execute=True for /code commands (user explicitly requested code)
        should_execute = intent.get("execute", True)
        task = Task(
            description=user_input,
            intent="code",
            context={
                "execute": should_execute,
                "language": intent.get("language", "python"),
                "lesson_context": lesson_context,
            },
        )
        result = await agent.execute(task)

        if result.status == TaskStatus.FAILED:
            # Self-learning: store the failure
            analysis = await self.memory.generate_lesson_from_failure(
                user_input, result.error or "Unknown error", self.llm_router
            )
            if analysis:
                self.memory.store_lesson(
                    failure_description=user_input,
                    error_details=result.error or "",
                    root_cause=analysis.get("root_cause", "Unknown"),
                    fix_applied=analysis.get("fix", ""),
                    domain=analysis.get("domain", "coding"),
                )

        return result.output or result.error or "No output"

    async def _execute_research_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """Execute via ResearcherAgent with automatic Architectural follow-up."""
        agent = self.agents[AgentRole.RESEARCHER]
        
        # Check if this is an architect/cloning request
        is_architect = intent.get("type") == "architect" or any(kw in user_input.lower() for kw in ["mimari", "architect", "clone", "klonla"])
        
        task = Task(
            description=user_input,
            intent="architect" if is_architect else "research",
            context={"max_hops": intent.get("max_hops", 3)},
        )
        result = await agent.execute(task)
        
        # If it was an architect task and we have visual data, proceed to generation
        if is_architect and result.status == TaskStatus.SUCCESS and result.context.get("visual_data"):
            visual_data = result.context["visual_data"]
            from ultron.v2.workspace.workspace_manager import WorkspaceManager, GenerateRequest
            
            # Initialize WorkspaceManager lazily
            mgr = WorkspaceManager()
            await mgr.init_db()
            
            gen_req = GenerateRequest(
                idea=f"Architecture clone of {visual_data.get('url')}. {user_input}",
                tech_stack="react-fastapi",
                visual_data=visual_data
            )
            
            gen_result = await mgr.generate_app(gen_req)
            await mgr.close()
            
            return f"{result.output}\n\n🚀 **İNŞA TAMAMLANDI!**\nProje klasörü: `{gen_result.path}`\nTeknoloji: React + FastAPI"

        return result.output or result.error or "No research results"

    async def _execute_weather_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        """Get weather report via ResearcherAgent (now with instant utility support)."""
        agent = self.agents[AgentRole.RESEARCHER]
        task = Task(
            description=user_input,
            intent="weather",
            context={"lesson_context": lesson_context},
        )
        result = await agent.execute(task)
        
        if result.status == TaskStatus.SUCCESS:
            return result.output
            
        # Fallback to browser if agent fails completely
        import webbrowser
        from urllib.parse import quote_plus
        city = user_input.replace("hava durumu", "").replace("weather", "").strip() or "İstanbul"
        url = f"https://www.google.com/search?q=weather+in+{quote_plus(city)}"
        try:
            webbrowser.open(url)
            return f"🌤 {city} için hava durumu tarayıcıda açıldı (Aracı yanıt veremedi)."
        except Exception as e:
            return f"Hava durumu sorgusu başarısız: {e}"

    async def _execute_system_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        """Return system info (CPU, RAM, disk, time)."""
        import psutil
        from datetime import datetime

        parts = []
        input_lower = user_input.lower()

        if any(kw in input_lower for kw in ["cpu", "işlemci", "processor"]):
            cpu = psutil.cpu_percent(interval=1)
            cores = psutil.cpu_count()
            parts.append(f"🖥 CPU: %{cpu} kullanım, {cores} çekirdek")

        if any(kw in input_lower for kw in ["ram", "bellek", "memory"]):
            mem = psutil.virtual_memory()
            parts.append(f"💾 RAM: {mem.percent}% kullanım ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)")

        if any(kw in input_lower for kw in ["disk", "depolama", "storage"]):
            try:
                disk = psutil.disk_usage(_default_disk_usage_path())
                parts.append(f"💿 Disk: {disk.percent}% kullanım ({disk.used // (1024**3)}/{disk.total // (1024**3)} GB)")
            except Exception as e:
                parts.append(f"💿 Disk: okunamadı ({e})")

        if any(kw in input_lower for kw in ["saat", "time", "tarih", "date"]):
            # Detect if this is a world clock request (e.g., "time in X", "X saat kaç")
            # If there are more than 2 words or specific keywords, route to ResearcherAgent
            is_query = any(w in input_lower for w in ["kaç", "nedir", "in", "da", "de", "nde", "nda"])
            words = input_lower.split()
            
            if (is_query and len(words) >= 2) or len(words) > 3:
                 agent = self.agents[AgentRole.RESEARCHER]
                 task = Task(description=user_input, intent="time")
                 result = await agent.execute(task)
                 if result.status == TaskStatus.SUCCESS:
                     parts.append(result.output)
                 else:
                     parts.append(f"🕐 Yerel Saat: {datetime.now().strftime('%H:%M:%S')}")
            else:
                parts.append(f"🕐 Yerel Saat: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

        if any(kw in input_lower for kw in ["batarya", "battery", "şarj"]):
            try:
                batt = psutil.sensors_battery()
                if batt:
                    parts.append(f"🔋 Batarya: %{batt.percent} {'(şarjda)' if batt.power_plugged else '(şarjda değil)'}")
            except Exception:
                pass

        # Default: show all
        if not parts:
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            try:
                disk = psutil.disk_usage(_default_disk_usage_path())
                disk_line = f"💿 Disk: {disk.percent}% ({disk.used // (1024**3)}/{disk.total // (1024**3)} GB)"
            except Exception as e:
                disk_line = f"💿 Disk: okunamadı ({e})"
            parts.append(f"🖥 CPU: %{cpu}")
            parts.append(f"💾 RAM: {mem.percent}% ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)")
            parts.append(disk_line)

        return "\n".join(parts)

    async def _execute_whatsapp_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        """Extract contact/message and send via WhatsAppAgent."""
        extraction_prompt = [
            {"role": "system", "content": "Extract the 'contact' (person name) and the 'message' text from the user input. Return ONLY JSON: {\"contact\": \"name\", \"message\": \"text\"}"},
            {"role": "user", "content": user_input}
        ]
        try:
            resp = await self.llm_router.chat(extraction_prompt, max_tokens=150)
            json_match = re.search(r"\{[\s\S]*\}", resp.content)
            if not json_match:
                return "WhatsApp için kişi veya mesaj içeriği anlaşılamadı."
            
            data = json.loads(json_match.group())
            contact = data.get("contact")
            message = data.get("message")
            
            if not contact or not message:
                return "Kişi ismi veya mesaj metni eksik."
            
            agent = self.agents[AgentRole.WHATSAPP]
            task = Task(
                description=f"WhatsApp üzerinden {contact} kişisine '{message}' mesajını gönder.",
                context={"contact": contact, "message": message}
            )
            result = await agent.execute(task)
            return result.output or result.error
        except Exception as e:
            return f"WhatsApp mesajı gönderilirken hata oluştu: {e}"

    async def _execute_architect_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        """High-level architecture task: Plan and build a complex project."""
        context = {
            "is_architect": True,
            "project_mode": True,
            "allow_filesystem": True,
            "lesson_context": lesson_context,
            "requires_tests": True
        }
        await self.event_bus.publish("notification", {"message": "🏗️ Proje mimarisi oluşturuluyor, bu biraz zaman alabilir..."})
        return await self._execute_autonomous_task(user_input, {"type": "autonomous", "context": context}, lesson_context)

    async def _execute_discovery_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        """Search and install new skills from Ultron Nexus (ClawHub/GitHub)."""
        query = user_input.replace("skill bul", "").replace("yetenek ekle", "").replace("install skill", "").strip()
        if not query:
            return "Lütfen ne tür bir yetenek aradığınızı belirtin (örn: 'spotify skill bul')."

        await self.event_bus.publish("notification", {"message": f"🔍 '{query}' için Ultron Nexus taranıyor..."})
        
        # 1. Search
        nexus_results = await self.nexus.search_ultron_skill_nexus(query)
        gh_results = await self.nexus.search_github(query)
        all_results = nexus_results + gh_results
        
        if not all_results:
            return f"Üzgünüm, '{query}' ile ilgili uygun bir yetenek bulunamadı."

        # 2. Pick best
        best = all_results[0]
        
        # 3. Install
        success = await self.nexus.auto_install_server(best)
        
        if success:
            # Refresh bridge tools
            await self.mcp_bridge.refresh_tool_catalog()
            return f"✅ Yeni yetenek Ultron ekosistemine eklendi: **{best['name']}**\nArtık '{query}' ile ilgili istekleri yerine getirebilirim! 🚀"
        else:
            return f"❌ '{best['name']}' yeteneği bulundu ancak Ultron Nexus kurulumu başarısız oldu."

    async def _execute_file_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        """Read, write, or list files."""
        import re
        from pathlib import Path

        input_lower = user_input.lower()

        # Read file
        read_match = re.search(r"(?:okum?|read|göster|show|aç|open)\s+(?:dosya\s+)?(?:file\s+)?(.+?)(?:\s*$)", input_lower)
        if read_match or "okum" in input_lower or "read" in input_lower:
            # Try to extract filename
            filename = None
            for ext in [".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg", ".js", ".ts"]:
                match = re.search(r'(\S+' + re.escape(ext) + r')', user_input, re.IGNORECASE)
                if match:
                    filename = match.group(1)
                    break

            if filename:
                filepath = Path(filename)
                if not filepath.is_absolute():
                    # Search in project root
                    project_root = Path(__file__).parent.parent.parent.parent
                    filepath = project_root / filename

                if filepath.exists():
                    try:
                        content = filepath.read_text(encoding="utf-8")
                        max_len = 2000
                        if len(content) > max_len:
                            content = content[:max_len] + f"\n\n... (dosya kısaltıldı, toplam {len(content)} karakter)"
                        return f"📄 {filepath.name}:\n\n{content}"
                    except Exception as e:
                        return f"Dosya okunamadı: {e}"
                else:
                    return f"📁 Dosya bulunamadı: {filename}"

        # List directory
        if any(kw in input_lower for kw in ["listele", "list", "göster", "show", "klasör", "folder", "dizin", "directory"]):
            project_root = Path(__file__).parent.parent.parent.parent
            items = []
            for item in sorted(project_root.iterdir()):
                if item.is_dir():
                    items.append(f"📁 {item.name}/")
                else:
                    items.append(f"📄 {item.name}")
            return "📂 Proje kök dizini:\n\n" + "\n".join(items)

        return "Dosya işlemi için 'dosya oku <dosya_adı>' veya 'klasör listele' şeklinde yazın."

    async def _execute_rpa_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """Execute via RPAOperatorAgent with intent-specific actions."""
        agent = self.agents[AgentRole.RPA_OPERATOR]
        intent_type = intent.get("type", "rpa")

        # Map intent type to RPA action
        if intent_type == "weather":
            # Extract city from input
            import re
            city_match = re.search(
                r"(?:hava\s+durumu|weather)\s+(?:nedir\s+)?(?:([^,]+?))?\s*$",
                user_input,
                re.IGNORECASE,
            )
            g1 = city_match.group(1) if city_match else None
            city = (g1 or "").strip() if city_match and (g1 or "").strip() else user_input.strip()
            ctx = {"action": "weather", "city": city}
        elif intent_type == "app":
            ctx = {"action": "auto"}
        elif intent_type == "system":
            ctx = {"action": "auto"}
        elif intent_type == "file":
            ctx = {"action": "auto"}
        else:
            ctx = {"action": "auto"}

        task = Task(
            description=user_input,
            intent=intent_type,
            context={**ctx, "lesson_context": lesson_context},
        )
        result = await agent.execute(task)
        return result.output or result.error or "No RPA result"

    async def _execute_email_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """Execute via EmailAgent."""
        agent = self.agents.get(AgentRole.EMAIL)
        if not agent:
            return "⚠️ Email agent başlatılamadı. ULTRON_EMAIL_USER ve ULTRON_EMAIL_PASS ayarlanmış mı?"
        task = Task(description=user_input, intent="email", context={"lesson_context": lesson_context})
        result = await agent.execute(task)
        return result.output or result.error or "Email işlemi tamamlandı."

    async def _execute_clipboard_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """Execute via ClipboardAgent."""
        agent = self.agents.get(AgentRole.CLIPBOARD)
        if not agent:
            return "⚠️ Clipboard agent başlatılamadı. pyperclip kurulu mu?"
        task = Task(description=user_input, intent="clipboard", context={"lesson_context": lesson_context})
        result = await agent.execute(task)
        return result.output or result.error or "Pano işlemi tamamlandı."

    async def _execute_meeting_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """Execute via MeetingAgent."""
        agent = self.agents.get(AgentRole.MEETING)
        if not agent:
            return "⚠️ Meeting agent başlatılamadı."
        task = Task(description=user_input, intent="meeting", context={"lesson_context": lesson_context})
        result = await agent.execute(task)
        return result.output or result.error or "Toplantı işlemi tamamlandı."

    async def _execute_debate_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
    ) -> str:
        """Execute via DebateAgent."""
        agent = self.agents.get(AgentRole.DEBATE)
        if not agent:
            return "⚠️ Debate agent başlatılamadı."
        task = Task(description=user_input, intent="debate", context={"rounds": 2})
        result = await agent.execute(task)
        return result.output or result.error or "Tartışma tamamlandı."

    async def _execute_multi_task(
        self,
        user_input: str,
        intent: dict,
        lesson_context: str,
        _depth: int = 0,
    ) -> str:
        """Execute multiple subtasks in parallel."""
        subtasks = intent.get("subtasks", [user_input])
        results = []

        async def run_subtask(subtask: str):
            sub_intent = await self._classify_intent(subtask)
            # Sonsuz döngüyü önlemek için intent tipi multi ise chat'e çek
            if sub_intent.get("type") == "multi":
                sub_intent["type"] = "chat"
            # Tüm alt görevi doğrudan ana orkestratör pipeline'ından geçir
            return await self.process(subtask, context={"intent": sub_intent}, _depth=_depth + 1)

        futures = [run_subtask(task) for task in subtasks]
        sub_results = await asyncio.gather(*futures, return_exceptions=True)

        for i, res in enumerate(sub_results):
            if isinstance(res, Exception):
                results.append(f"[Görev {i+1} Hatası] {res}")
            else:
                results.append(res)

        # Synthesize results
        if len(results) > 1:
            synthesis_messages = [
                {
                    "role": "system",
                    "content": "Synthesize these results from multiple agents into a coherent response in Turkish.",
                },
                {
                    "role": "user",
                    "content": f"Original request: {user_input}\n\nResults:\n"
                    + "\n\n".join(results),
                },
            ]
            try:
                response = await self.llm_router.chat(synthesis_messages, max_tokens=2048)
                return response.content
            except Exception as e:
                logger.warning("Multi-task synthesis LLM failed: %s", e)
                return "\n\n".join(results)

        return results[0] if results else "No results"

    async def _execute_skill_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        """Execute a dynamically discovered skill."""
        skill_name = intent.get("skill")
        skill = next((s for s in self._skills if s["name"] == skill_name), None)
        if not skill:
            return f"⚠️ Yetenek (Skill) '{skill_name}' bulunamadı."
        
        try:
            path = Path(skill["path"])
            if path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace")
            else:
                skill_md = path / "SKILL.md"
                content = skill_md.read_text(encoding="utf-8", errors="replace") if skill_md.exists() else "Açıklama bulunamadı."
            
            messages = [
                {"role": "system", "content": f"Sen '{skill_name}' isimli yeteneğe sahipsin. Aşağıdaki belgede yer alan yetenek kurallarına göre kullanıcının isteğini yerine getir:\n\n{content}"},
                {"role": "user", "content": user_input}
            ]
            response = await self.llm_router.chat(messages, max_tokens=2048)
            return response.content
        except Exception as e:
            logger.error("Skill execution error: %s", e)
            return f"❌ Yetenek çalıştırılırken hata oluştu: {e}"

    async def _execute_discovered_agent_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        """Execute a dynamically discovered external agent."""
        agent_name = intent.get("agent")
        agent = next((a for a in self._agents_discovered if a["name"] == agent_name), None)
        if not agent:
            return f"⚠️ Ajan (Agent) '{agent_name}' bulunamadı."
        
        try:
            path = Path(agent["path"])
            content = ""
            if path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace")
            else:
                for cfg in ["AGENT.md", "agent.json", "config.json", "README.md"]:
                    cfg_file = path / cfg
                    if cfg_file.exists():
                        content = cfg_file.read_text(encoding="utf-8", errors="replace")
                        break
            
            messages = [
                {"role": "system", "content": f"Sen '{agent_name}' adlı özelleşmiş bir ajansın. Görevlerini aşağıdaki yapılandırmaya/talimatlara göre yerine getir:\n\n{content}"},
                {"role": "user", "content": user_input}
            ]
            response = await self.llm_router.chat(messages, max_tokens=2048)
            return response.content
        except Exception as e:
            logger.error("Agent execution error: %s", e)
            return f"❌ Ajan çalıştırılırken hata oluştu: {e}"

    async def _general_chat(self, user_input: str, lesson_context: str, history: list = None) -> str:
        """Chat response with prompt.txt, conversation history, and lesson context."""
        from pathlib import Path
        import os

        # Load prompt.txt
        prompt_file = Path(__file__).parent / "prompt.txt"
        if not prompt_file.exists():
            prompt_file = Path(__file__).parent.parent.parent.parent / "PROMPT.txt"

        system_text = ""
        if prompt_file and prompt_file.exists():
            try:
                system_text = prompt_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        if not system_text:
            system_text = (
                "You are Ultron — a personal AI assistant. "
                "You know your name is Ultron. You are helpful, concise, and accurate. "
                "Always respond in the same language the user writes in."
            )

        # Detect user language (Turkish vs English) instead of hardcoding
        import re
        turkish_chars = re.findall(r'[çğıöşüÇĞİÖŞÜ]', user_input)
        is_turkish = len(turkish_chars) > 0 or any(
            w in user_input.lower() for w in ("nasıl", "nedir", "bana", "bir", "merhaba", "selam", "tamam", "evet")
        )

        if is_turkish:
            lang_enforcement = (
                "\n\nDİL VE ÜSLUP KURALLARI:\n"
                "1. KESİNLİKLE Türkçe cevap ver. Yazım kurallarına (de/da ayrımı, noktalamalar vb.) kusursuz uy.\n"
                "2. İnsansı, samimi ve zeki bir üslup kullan. Robotik cevaplardan kaçın.\n"
                "3. Emojileri (😉, 🚀, ✨, 🔥 gibi) yerinde ve etkili kullanarak cevaplarını zenginleştir.\n"
                "4. Eğer uygunsa, nükte ve hafif esprilerle sohbeti daha doğal hale getir.\n"
                "5. Çince, Japonca veya alakasız yabancı karakterleri ASLA kullanma."
            )
        else:
            lang_enforcement = (
                "\n\nLANGUAGE: Respond in the same language the user uses. "
                "Match their tone and formality level."
            )

        # Build full system prompt with context
        parts = [system_text + lang_enforcement]

        # Add lesson context
        if lesson_context:
            parts.append(f"Lessons from past interactions:\n{lesson_context}")

        # Add conversation history from memory (semantic search for relevant context)
        try:
            # Pull technical knowledge if relevant
            if any(kw in user_input.lower() for kw in ["nasıl", "nedir", "kod", "error", "hata", "python", "fix"]):
                kb_results = await self.knowledge.search(user_input, limit=2)
                if kb_results:
                    kb_text = "\n".join([f"- {r['content'][:300]}" for r in kb_results])
                    parts.append(f"Relevant technical knowledge:\n{kb_text}")

            recent_lessons = self.memory.get_relevant_lessons(user_input, limit=2)
            if recent_lessons:
                lesson_texts = [l.get("fix", l.get("root_cause", "")) for l in recent_lessons if l]
                if lesson_texts:
                    parts.append("Past lessons learned:\n" + "\n".join(f"- {t}" for t in lesson_texts[:2]))

            # Pull milestones and semantic facts
            milestones = self.memory.search(user_input, entry_type="milestone", limit=2)
            if milestones:
                milestone_text = "\n".join([f"- {m['content']}" for m in milestones])
                parts.append(f"Past milestones & achievements:\n{milestone_text}")
            
            facts = self.memory.search(user_input, entry_type="semantic", limit=3)
            if facts:
                facts_text = "\n".join([f"- {f['content']}" for f in facts])
                parts.append(f"Known facts & preferences:\n{facts_text}")
        except Exception as e:
            logger.debug("Memory retrieval for chat context failed: %s", e)

        # Add recent episodic memory for continuity
        try:
            recent_episodes = self.memory.search(user_input, entry_type="episodic", limit=3)
            if recent_episodes:
                history_lines = []
                for ep in recent_episodes[:3]:
                    content = ep.get("content", "") if isinstance(ep, dict) else str(ep)
                    if content and len(content) > 10:
                        history_lines.append(content[:300])
                if history_lines:
                    parts.append("Recent conversation context:\n" + "\n".join(history_lines))
        except Exception as e:
            logger.debug("Episodic memory search failed: %s", e)

        # Intelligent Routing: If it's a complex logic/reasoning task, use ReasoningEngine
        COMPLEX_SIGNALS = ("neden", "niçin", "kanıtla", "analiz", "ispat", "nasıl çalışır", "farkı nedir", "think", "analyze", "prove", "why", "how does", "what is the difference")
        if any(sig in user_input.lower() for sig in COMPLEX_SIGNALS) or len(user_input.split()) > 15:
            logger.info("Complex query detected - triggering ReasoningEngine...")
            # Prepare context (history + memory insights)
            full_context = {
                "lesson_context": lesson_context,
                "memory_parts": "\n\n".join(parts),
                "history": history if 'history' in locals() else []
            }
            reason_res = await self.reasoning.reason(user_input, context=full_context)
            return reason_res.final_answer

        messages = [
            {"role": "system", "content": "\n\n".join(parts)}
        ]

        # Add short-term conversational history for perfect logical reasoning
        if history:
            # Filter out the very last message if it's identical to user_input (to avoid duplication)
            valid_history = []
            for msg in history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    valid_history.append({"role": role, "content": content})
            
            # Avoid duplicating the current user_input if it's already at the end of valid_history
            if valid_history and valid_history[-1].get("role") == "user" and valid_history[-1].get("content") == user_input:
                valid_history.pop()

            messages.extend(valid_history)

        # Finally, append the current user input
        messages.append({"role": "user", "content": user_input})

        # -- Step 3: Optimize Context --
        messages = await context_manager.optimize_context(messages, self.llm_router)

        try:
            # Dynamic MCP injection (normal chat brain can self-initiate tool calls)
            if self._should_auto_use_mcp_in_chat(user_input):
                policy = [
                    "MCP araçları mevcutsa, kullanıcı niyetine göre GEREKİRSE çağırabilirsin.",
                    "Gerekmiyorsa tool çağırma; normal sohbet yanıtı ver.",
                    "GÜVENLİK: Path işlemleri sadece izinli workspace/data kökleri içinde olmalı; şüpheli path isteğinde reddet.",
                    "Yanıtı Türkçe ve öz ver.",
                ]
                messages[0]["content"] += "\n\n" + "\n".join(policy)
                response = await self.llm_router.chat_with_mcp_tool_loop(
                    messages,
                    self.mcp_bridge,
                    max_tool_rounds=int(os.getenv("ULTRON_MCP_MAX_TOOL_ROUNDS", "6")),
                    temperature=0.25,
                    max_tokens=2048,
                )
            else:
                response = await self.llm_router.chat(messages, temperature=0.3, max_tokens=1024)
        except Exception as e:
            logger.error("General chat LLM failed: %s", e)
            return f"Model şu anda yanıt veremedi. Lütfen API anahtarlarını veya Ollama bağlantısını kontrol edin. Ayrıntı: {e}"

        # CRITICAL: Validate response language — reject if contains Chinese characters
        import re
        content_text = str(response.content or "")
        if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', content_text):
            # Regenerate with stricter language enforcement
            messages[0]["content"] += "\n\nCRITICAL: Your previous response contained non-Turkish characters. " \
                "Regenerate the ENTIRE response in Turkish ONLY."
            try:
                response = await self.llm_router.chat(messages, temperature=0.1, max_tokens=1024)
            except Exception as e:
                logger.warning("Regeneration after language check failed: %s", e)

        # Store this interaction for future context
        try:
            self.memory.store(
                entry_id=f"chat_{int(datetime.now().timestamp())}",
                content=f"User: {user_input}\nUltron: {str(response.content)[:500]}",
                entry_type="episodic",
                metadata={"type": "chat"},
            )
        except Exception as e:
            logger.warning("Memory store after chat failed: %s", e)

        return str(response.content or "Yanıt oluşturulamadı.")

    def get_status(self) -> dict:
        """Get system status."""
        return {
            "running": self._running,
            "agents": {
                (role.value if hasattr(role, 'value') else str(role)): {
                    "status": (agent.state.status.value if hasattr(agent.state.status, 'value') else str(agent.state.status)),
                    "tasks_completed": agent.state.tasks_completed,
                    "tasks_failed": agent.state.tasks_failed,
                }
                for role, agent in self.agents.items()
            },
            "llm_providers": self.llm_router.get_status(),
            "memory": self.memory.stats(),
            "event_bus_events": len(self.event_bus.get_history(100)),
            # AGI Core Systems
            "reasoning": self.reasoning.get_stats(),
            "planner": self.planner.get_stats(),
            "security": self.security.get_stats(),
            "self_improvement": self.self_improvement.get_stats(),
            "mcp": {
                "enabled": self.mcp_manager.enabled,
                "servers": [
                    {
                        "id": sid,
                        "status": "connected" if self.mcp_manager.get_session(sid) else "error",
                        "command": next((s.command for s in self.mcp_manager._settings.servers if s.id == sid), "unknown"),
                        "tools": [tname for tname, (tsid, tmcp) in self.mcp_bridge._name_map.items() if tsid == sid]
                    }
                    for sid in self.mcp_manager.list_server_ids()
                ],
                "total_tools": len(self.mcp_bridge.openai_tools()),
                "errors": self.mcp_manager.errors,
            },
        }
