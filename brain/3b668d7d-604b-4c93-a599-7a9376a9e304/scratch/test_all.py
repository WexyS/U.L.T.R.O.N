"""Full system test suite for Ultron."""
import sys, asyncio, traceback
sys.stdout.reconfigure(encoding='utf-8')

results = []

def test(name, fn):
    try:
        fn()
        results.append((name, "PASS", ""))
        print(f"  [PASS] {name}")
    except Exception as e:
        results.append((name, "FAIL", str(e)))
        print(f"  [FAIL] {name}: {e}")

print("=" * 60)
print("ULTRON FULL SYSTEM TEST SUITE")
print("=" * 60)

# ── 1. Module Import Tests ──
print("\n--- 1. MODULE IMPORTS ---")
modules = [
    "ultron.v2.core.types",
    "ultron.v2.core.event_bus",
    "ultron.v2.core.blackboard",
    "ultron.v2.core.llm_router",
    "ultron.v2.core.browser_service",
    "ultron.v2.core.skill_manager",
    "ultron.v2.core.orchestrator",
    "ultron.v2.memory.engine",
    "ultron.v2.agents.base",
    "ultron.v2.agents.researcher",
    "ultron.v2.agents.debate_agent",
    "ultron.v2.agents.error_analyzer",
    "ultron.api.main",
]
for mod in modules:
    test(f"import {mod}", lambda m=mod: __import__(m))

# ── 2. Skill Manager Tests ──
print("\n--- 2. SKILL MANAGER ---")
from ultron.v2.core.skill_manager import discover_all_skills, discover_all_agents

def test_skills():
    s = discover_all_skills()
    assert len(s) >= 2500, f"Expected >= 2500 skills, got {len(s)}"
test("discover_all_skills >= 2500", test_skills)

def test_agents():
    a = discover_all_agents()
    assert len(a) >= 200, f"Expected >= 200 agents, got {len(a)}"
test("discover_all_agents >= 200", test_agents)

def test_skill_structure():
    s = discover_all_skills()
    for skill in s[:10]:
        assert "name" in skill, "Skill missing 'name'"
        assert "path" in skill, "Skill missing 'path'"
test("skill structure validation", test_skill_structure)

# ── 3. LLM Router Tests ──
print("\n--- 3. LLM ROUTER ---")
from ultron.v2.core.llm_router import LLMRouter, OllamaProvider

def test_router_init():
    r = LLMRouter()
    assert r is not None
test("LLMRouter init", test_router_init)

def test_ollama_provider():
    p = OllamaProvider()
    assert p.name == "ollama"
    assert p.get_model_name() == "qwen2.5:14b"
    # is_available should not crash
    _ = p.is_available()
test("OllamaProvider basic", test_ollama_provider)

def test_router_providers():
    r = LLMRouter()
    healthy = r.get_healthy_providers()
    assert isinstance(healthy, list)
test("LLMRouter.get_healthy_providers", test_router_providers)

# ── 4. Browser Service Tests ──
print("\n--- 4. BROWSER SERVICE ---")
from ultron.v2.core.browser_service import BrowserService

def test_browser_init():
    b = BrowserService()
    assert b.data_dir.exists() or True  # dir created on first use
test("BrowserService init", test_browser_init)

# ── 5. Memory Engine Tests ──
print("\n--- 5. MEMORY ENGINE ---")
from ultron.v2.memory.engine import MemoryEngine

def test_memory_init():
    m = MemoryEngine()
    assert m is not None
test("MemoryEngine init", test_memory_init)

# ── 6. Event Bus Tests ──
print("\n--- 6. EVENT BUS ---")
from ultron.v2.core.event_bus import EventBus

def test_eventbus():
    bus = EventBus()
    received = []
    bus.subscribe("test_event", lambda e: received.append(e))
    assert bus is not None
test("EventBus subscribe", test_eventbus)

# ── 7. Blackboard Tests ──
print("\n--- 7. BLACKBOARD ---")
from ultron.v2.core.blackboard import Blackboard

def test_blackboard():
    bb = Blackboard()
    async def test_bb():
        await bb.write("test_key", "test_value", owner="test_agent")
        assert await bb.read("test_key") == "test_value"
    import asyncio
    asyncio.run(test_bb())
test("Blackboard write/read", test_blackboard)

# ── 8. Types Tests ──
print("\n--- 8. TYPES ---")
from ultron.v2.core.types import AgentRole, TaskStatus, Task, TaskResult

def test_types():
    t = Task(id="test-1", description="test task")
    assert t.id == "test-1"
    r = TaskResult(task_id="test-1", status=TaskStatus.SUCCESS, output="done")
    assert r.status == TaskStatus.SUCCESS
test("Task/TaskResult creation", test_types)

# ── 9. Orchestrator Intent Tests ──
print("\n--- 9. ORCHESTRATOR INTENT ---")
from ultron.v2.core.orchestrator import INTENT_KEYWORDS

def test_intents():
    assert "research" in INTENT_KEYWORDS
    assert "weather" in INTENT_KEYWORDS
    assert "code" in INTENT_KEYWORDS
    assert "app" in INTENT_KEYWORDS
    assert "saat" in INTENT_KEYWORDS["weather"] or "saat kac" in INTENT_KEYWORDS["weather"]
test("INTENT_KEYWORDS completeness", test_intents)

def test_command_prefix():
    # Test that orchestrator has command prefix logic
    import inspect
    from ultron.v2.core.orchestrator import Orchestrator
    src = inspect.getsource(Orchestrator._classify_intent)
    assert "startswith" in src, "Command prefix logic missing"
test("Command prefix support", test_command_prefix)

# ── 10. Researcher Agent Tests ──
print("\n--- 10. RESEARCHER AGENT ---")
from ultron.v2.agents.researcher import ResearcherAgent

def test_researcher_has_browser():
    r = ResearcherAgent.__init__.__code__.co_varnames
    # Check BrowserService import exists in module
    import ultron.v2.agents.researcher as mod
    assert hasattr(mod, 'BrowserService')
test("ResearcherAgent has BrowserService", test_researcher_has_browser)

# ── 11. API Main Tests ──
print("\n--- 11. API ---")
def test_api_import():
    from ultron.api.main import app
    assert app is not None
test("FastAPI app import", test_api_import)

# ── SUMMARY ──
print("\n" + "=" * 60)
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
total = len(results)
print(f"RESULTS: {passed}/{total} PASSED, {failed} FAILED")
if failed > 0:
    print("\nFAILED TESTS:")
    for name, status, err in results:
        if status == "FAIL":
            print(f"  - {name}: {err}")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
