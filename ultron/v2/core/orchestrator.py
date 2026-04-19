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
from ultron.v2.agents.openguider_bridge import OpenGuiderBridgeAgent
from ultron.v2.agents.debate_agent import DebateAgent

# ── AGI Core Modules ──────────────────────────────────────
from ultron.v2.core.reasoning_engine import ReasoningEngine
from ultron.v2.core.planner import Planner
from ultron.v2.core.security import SecurityManager
from ultron.v2.core.self_improvement import SelfImprovementEngine

logger = logging.getLogger(__name__)


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
    "code": ["kod yaz", "kod", "yazılım", "program", "python", "javascript", "function", "script",
             "calculate", "hesapla", "debug", "hata ayıkla", "çalıştır", "execute", "code"],
    "research": ["araştır", "research", "bul", "search", "nedir", "what is", "explain",
                 "açıkla", "öğren", "learn", "about", "hakkında"],
    "weather": ["hava durumu", "weather", "sıcaklık", "temperature", "yağmur", "rain",
                "kar", "snow", "güneşli", "sunny", "bulutlu", "cloudy", "rüzgar", "wind"],
    "app": ["aç", "open", "başlat", "start", "launch", "çalıştır", "run", "uygulama", "app",
            "program", "exe", "steam", "chrome", "spotify", "discord", "notepad",
            "youtube", "twitter", "x.com", "reddit", "github", "gmail", "google",
            "netflix", "amazon", "git"],
    "system": ["sistem", "system", "cpu", "ram", "disk", "batarya", "battery", "saat", "time",
               "bilgi", "info", "durum", "status"],
    "file": ["dosya", "file", "oku", "okum", "read", "yaz", "write", "kaydet", "save", "oluştur",
             "create", "listele", "list", "klasör", "folder", "dizin", "directory"],
    # ── Yeni Intentler ─────────────────────────────────────
    "email": ["email", "e-posta", "mail", "gelen kutusu", "inbox", "mesaj oku",
              "mail gönder", "mail gönder", "taslak", "draft"],
    "meeting": ["toplantı", "meeting", "transkript", "kaydet", "record meeting",
                "dikte", "ses kaydı", "voice note"],
    "clipboard": ["pano", "clipboard", "kopyala", "paste", "yapıştır", "kod analiz",
                  "code review bu kodu"],
    "debate": ["tartış", "fikir bul", "en iyisini bul", "debate", "karşılaştır"],
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
        self.llm_router = llm_router
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
        self._init_agents(work_dir)

        # Discover skills and agents
        self._skills = _discover_skills()
        self._agents_discovered = _discover_agents()
        logger.info("Discovered %d skills, %d agents", len(self._skills), len(self._agents_discovered))

        self._running = False
        self._task_queue: asyncio.Queue[Task] = asyncio.Queue()

        # ── AGI Core Systems ─────────────────────────────────────
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
            self.agents[AgentRole.OPENGUIDER_BRIDGE] = OpenGuiderBridgeAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize OpenGuiderBridgeAgent: %s", e)

        try:
            self.agents[AgentRole.DEBATE] = DebateAgent(
                llm_router=self.llm_router,
                event_bus=self.event_bus,
                blackboard=self.blackboard,
            )
        except Exception as e:
            logger.warning("Failed to initialize DebateAgent: %s", e)

        logger.info("Initialized %d agents", len(self.agents))

    async def start(self) -> None:
        """Start the orchestrator and all agents."""
        self._running = True
        for role, agent in self.agents.items():
            await agent.start()
            logger.info("Agent started: %s", role.value)

        # Log memory stats
        stats = self.memory.stats()
        logger.info("Memory engine: %s", stats)

    async def stop(self) -> None:
        """Stop all agents and clean up resources."""
        self._running = False
        for role, agent in self.agents.items():
            try:
                await agent.stop()
            except Exception as e:
                logger.warning("Error stopping agent %s: %s", role.value, e)
        # Close event bus
        if self.event_bus:
            self.event_bus._handlers.clear()
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
        # SECURITY FIX: Prevent infinite recursion on complex multi-task chains
        if _depth > 10:
            logger.warning("Recursion depth exceeded (depth=%d) for input: %s", _depth, user_input[:100])
            return f"Task is too complex to process (depth limit reached). Please simplify your request."

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
                    # Only override if the fast match was on short/ambiguous keywords
                    input_lower = user_input.lower()
                    matched_short_kw = any(
                        len(kw.lower()) <= 3 and kw.lower() in input_lower
                        for kw in INTENT_KEYWORDS.get(intent.get("type", ""), [])
                    )
                    if matched_short_kw:
                        intent = llm_intent
                        logger.info("Fast→LLM override: %s → %s", intent.get("type"), llm_intent.get("type"))

        logger.info("Intent: %s", intent)

        # Step 2: Route to appropriate agent(s)
        if intent.get("type") == "code":
            result = await self._execute_code_task(user_input, intent, lesson_context)
        elif intent.get("type") == "research":
            result = await self._execute_research_task(user_input, intent, lesson_context)
        elif intent.get("type") == "weather":
            result = await self._execute_weather_task(user_input, intent, lesson_context)
        elif intent.get("type") == "system":
            result = await self._execute_system_task(user_input, intent, lesson_context)
        elif intent.get("type") == "file":
            result = await self._execute_file_task(user_input, intent, lesson_context)
        elif intent.get("type") in ("rpa", "app"):
            # HITL: Return confirmation, don't execute autonomously
            app_or_url = ""
            intent_type = intent.get("type", "rpa")
            desc_lower = user_input.lower()
            for site, url in [
                ("youtube", "https://youtube.com"),
                ("twitter", "https://x.com"),
                ("reddit", "https://reddit.com"),
                ("github", "https://github.com"),
                ("gmail", "https://mail.google.com"),
                ("google", "https://google.com"),
                ("sozluk", "https://sozluk.gov.tr"),
                ("tdk", "https://sozluk.gov.tr"),
                ("netflix", "https://netflix.com"),
                ("amazon", "https://amazon.com"),
            ]:
                if site in desc_lower:
                    app_or_url = url
                    break
            if not app_or_url:
                for app in ["steam", "chrome", "firefox", "edge", "spotify", "discord", "notepad", "vscode", "excel", "word"]:
                    if app in desc_lower:
                        app_or_url = app
                        break

            if app_or_url:
                result = (
                    f"🔒 RPA Aksiyon Onayı Gerekli\n\n"
                    f"📋 Planlanan işlem:\n"
                    f"  {'Tarayıcıda aç:' if app_or_url.startswith('http') else 'Uygulama başlat:'} {app_or_url}\n\n"
                    f"⚠️ Bu işlem ekran kontrolü ve fare/klavye hareketi gerektirir.\n"
                    f"Devam etmek istiyor musunuz? Onaylamak için 'evet' veya 'onay' yazın."
                )
            else:
                result = await self._execute_rpa_task(user_input, intent, lesson_context)
        elif intent.get("type") == "multi":
            result = await self._execute_multi_task(user_input, intent, lesson_context, _depth=_depth)
        elif intent.get("type") == "email":
            result = await self._execute_email_task(user_input, intent, lesson_context)
        elif intent.get("type") == "clipboard":
            result = await self._execute_clipboard_task(user_input, intent, lesson_context)
        elif intent.get("type") == "meeting":
            result = await self._execute_meeting_task(user_input, intent, lesson_context)
        elif intent.get("type") == "debate":
            result = await self._execute_debate_task(user_input, intent, lesson_context)
        elif intent.get("type") == "skill":
            result = await self._execute_skill_task(user_input, intent, lesson_context)
        elif intent.get("type") == "agent":
            result = await self._execute_discovered_agent_task(user_input, intent, lesson_context)
        else:
            # General chat
            result = await self._general_chat(user_input, lesson_context)

        # Store interaction in memory
        self.memory.store(
            entry_id=f"interaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            content=f"User: {user_input}\nResponse: {result[:500]}",
            entry_type="episodic",
            metadata={"intent": intent.get("type")},
        )

        return result


    def _classify_intent_fast(self, user_input: str) -> dict:
        """Fast keyword-based intent classification with word-boundary awareness."""
        input_lower = user_input.lower()
        # Tokenize into words for better matching (split on whitespace and punctuation)
        tokens = set(re.findall(r'[a-zçğıöşü]+', input_lower))

        # First pass: exact word match (higher confidence)
        for intent_type, keywords in INTENT_KEYWORDS.items():
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
        """Use LLM to classify user intent."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Classify the user's intent into one of these categories.\n"
                    "IMPORTANT: If the user is just talking, asking questions, giving feedback, "
                    "or having a conversation — classify as 'chat'. Only use action types when "
                    "the user explicitly asks you to DO something.\n\n"
                    "- 'code': Writing, debugging, or executing code (user says 'write code', 'fix this', 'run script')\n"
                    "- 'research': Web search needed (user asks to look up info online, investigate)\n"
                    "- 'rpa': Controlling the computer, clicking UI, opening apps/websites\n"
                    "- 'email': Reading, summarizing, or sending emails\n"
                    "- 'system': CPU, RAM, disk monitoring, process management\n"
                    "- 'clipboard': Analyzing clipboard content, code review from clipboard\n"
                    "- 'meeting': Recording, transcribing, summarizing meetings\n"
                    "- 'file': Explicitly reading/writing/listing files or folders (user says 'read file X', 'list folder Y', 'create file Z')\n"
                    "- 'multi': Complex task requiring multiple agents\n"
                    "- 'chat': General conversation, opinions, feedback, questions, explanations\n\n"
                    "Rule of thumb: If you're unsure, it's probably 'chat'. "
                    "Only use action types when the request is clearly and explicit.\n\n"
                    'Return ONLY JSON: {"type": "code|research|rpa|email|system|clipboard|meeting|file|multi|chat", '
                    '"subtasks": ["task1", "task2"], '
                    '"requires_parallel": true/false}'
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
        """Execute via ResearcherAgent."""
        agent = self.agents[AgentRole.RESEARCHER]
        task = Task(
            description=user_input,
            intent="research",
            context={"max_hops": intent.get("max_hops", 3)},
        )
        result = await agent.execute(task)
        return result.output or result.error or "No research results"

    async def _execute_weather_task(self, user_input: str, intent: dict, lesson_context: str) -> str:
        """Open weather report in browser."""
        import re
        from urllib.parse import quote_plus
        import webbrowser

        # Extract city name
        city_match = re.search(r"(?:hava\s+durumu|weather|sıcaklık)\s+(?:nedir\s+)?(?:([^,]+?))?\s*$", user_input, re.IGNORECASE)
        city = city_match.group(1).strip() if city_match and city_match.group(1) else ""

        # Common Turkish cities if not extracted
        if not city:
            for c in ["İstanbul", "Ankara", "İzmir", "Antalya", "Bursa", "Adana", "Konya", "Gaziantep"]:
                if c.lower() in user_input.lower():
                    city = c
                    break
        if not city:
            city = "İstanbul"

        query = f"weather in {city}"
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        try:
            webbrowser.open(url)
            return f"🌤 {city} için hava durumu tarayıcıda açıldı."
        except Exception as e:
            return f"Tarayıcı açılamadı: {e}"

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
            disk = psutil.disk_usage('/')
            parts.append(f"💿 Disk: {disk.percent}% kullanım ({disk.used // (1024**3)}/{disk.total // (1024**3)} GB)")

        if any(kw in input_lower for kw in ["saat", "time", "tarih", "date"]):
            parts.append(f"🕐 Şu an: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

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
            disk = psutil.disk_usage('/')
            parts.append(f"🖥 CPU: %{cpu}")
            parts.append(f"💾 RAM: {mem.percent}% ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)")
            parts.append(f"💿 Disk: {disk.percent}% ({disk.used // (1024**3)}/{disk.total // (1024**3)} GB)")
            parts.append(f"🕐 Saat: {datetime.now().strftime('%H:%M:%S')}")

        return "\n".join(parts)

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
            city_match = re.search(r"(?:hava\s+durumu|weather)\s+(?:nedir\s+)?(?:([^,]+?))?\s*$", user_input, re.IGNORECASE)
            city = city_match.group(1).strip() if city_match else user_input
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
            context=ctx,
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
            response = await self.llm_router.chat(synthesis_messages, max_tokens=2048)
            return response.content

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

    async def _general_chat(self, user_input: str, lesson_context: str) -> str:
        """Chat response with prompt.txt, conversation history, and lesson context."""
        from pathlib import Path

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

        # CRITICAL: Force Turkish language enforcement
        lang_enforcement = (
            "\n\nIMPORTANT LANGUAGE RULE:\n"
            "The user communicates in Turkish. You MUST respond in Turkish ONLY. "
            "NEVER use Chinese, Japanese, or any non-Turkish characters. "
            "If you cannot express something in Turkish, use simple Turkish words. "
            "This rule is ABSOLUTE and cannot be overridden."
        )

        # Build full system prompt with context
        parts = [system_text + lang_enforcement]

        # Add lesson context
        if lesson_context:
            parts.append(f"Lessons from past interactions:\n{lesson_context}")

        # Add conversation history from memory
        recent_lessons = self.memory.get_relevant_lessons(user_input, limit=2)
        if recent_lessons:
            lesson_texts = [l.get("fix", l.get("root_cause", "")) for l in recent_lessons if l]
            if lesson_texts:
                parts.append(f"Past relevant interactions:\n" + "\n".join(f"- {t}" for t in lesson_texts))

        messages = [
            {"role": "system", "content": "\n\n".join(parts)},
            {"role": "user", "content": user_input},
        ]

        response = await self.llm_router.chat(messages, temperature=0.3, max_tokens=1024)

        # CRITICAL: Validate response language — reject if contains Chinese characters
        import re
        if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', response.content):
            # Regenerate with stricter language enforcement
            messages[0]["content"] += "\n\nCRITICAL: Your previous response contained non-Turkish characters. " \
                "Regenerate the ENTIRE response in Turkish ONLY."
            response = await self.llm_router.chat(messages, temperature=0.1, max_tokens=1024)

        # Store this interaction for future context
        self.memory.store(
            entry_id=f"chat_{int(datetime.now().timestamp())}",
            content=f"User: {user_input}\nUltron: {response.content[:500]}",
            entry_type="episodic",
            metadata={"type": "chat"},
        )

        return response.content

    def get_status(self) -> dict:
        """Get system status."""
        return {
            "running": self._running,
            "agents": {
                role.value: {
                    "status": agent.state.status.value,
                    "tasks_completed": agent.state.tasks_completed,
                    "tasks_failed": agent.state.tasks_failed,
                }
                for role, agent in self.agents.items()
            },
            "llm_providers": self.llm_router.get_status(),
            "memory": self.memory.stats(),
            "event_bus_events": len(self.event_bus.get_recent_events(100)),
            # AGI Core Systems
            "reasoning": self.reasoning.get_stats(),
            "planner": self.planner.get_stats(),
            "security": self.security.get_stats(),
            "self_improvement": self.self_improvement.get_stats(),
        }
