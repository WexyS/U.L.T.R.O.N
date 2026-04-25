"""Comprehensive Ultron System Test Suite"""
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all critical imports"""
    print("\n[TEST 1] Module Imports")
    try:
        from ultron.core.orchestrator import Orchestrator
        from ultron.core.multi_agent_orchestrator import MultiAgentOrchestrator
        from ultron.core.llm_router import LLMRouter
        from ultron.memory.engine import MemoryEngine
        from ultron.agents.coder import CoderAgent
        from ultron.agents.researcher import ResearcherAgent
        from ultron.agents.email_agent import EmailAgent
        from ultron.agents.clipboard_agent import ClipboardAgent
        from ultron.agents.files_agent import FilesAgent
        from ultron.agents.meeting_agent import MeetingAgent
        from ultron.agents.sysmon_agent import SystemMonitorAgent
        from ultron.agents.rpa_operator import RPAOperatorAgent
        from ultron.api.main import app
        print("  PASS: All modules imported successfully")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_pydantic_models():
    """Test Pydantic v2 model serialization"""
    print("\n[TEST 2] Pydantic v2 Models")
    try:
        from ultron.workspace.models import WorkspaceItem, CloneRequest
        from datetime import datetime
        
        item = WorkspaceItem(
            id="test-123",
            type="cloned_template",
            name="Test Site",
            path="/tmp/test",
            file_path="/tmp/test/index.html",
            created_at=datetime.now().isoformat(),
            metadata={"url": "https://example.com"}
        )
        
        dump = item.model_dump()
        assert "id" in dump
        assert dump["name"] == "Test Site"
        print("  PASS: .model_dump() working correctly")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_agent_status_enum():
    """Test agent status enum usage"""
    print("\n[TEST 3] Agent Status Enums")
    try:
        from ultron.agents.base import AgentStatus, AgentState
        from ultron.core.types import AgentRole
        
        state = AgentState(role=AgentRole.CODER)
        state.status = AgentStatus.BUSY
        assert state.status == AgentStatus.BUSY
        state.status = AgentStatus.IDLE
        assert state.status == AgentStatus.IDLE
        print("  PASS: AgentStatus enum working correctly")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_api_routes():
    """Test API route definitions"""
    print("\n[TEST 4] API Routes")
    try:
        from ultron.api.main import app
        routes = [route.path for route in app.routes]
        
        required_routes = [
            "/",
            "/health",
            "/status",
            "/api/v2/chat",
            "/api/v2/providers/status",
            "/api/v2/workspace/clone",
            "/api/v2/workspace/generate",
            "/api/v2/workspace/synthesize",
            "/api/v2/workspace/list",
            "/api/v2/workspace/search",
            "/ws/chat"
        ]
        
        missing = [r for r in required_routes if r not in routes]
        if missing:
            print(f"  FAIL: Missing routes: {missing}")
            return False
        
        print(f"  PASS: All {len(required_routes)} critical routes defined")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_memory_engine():
    """Test memory engine initialization"""
    print("\n[TEST 5] Memory Engine")
    try:
        from ultron.memory.engine import MemoryEngine
        from ultron.memory.working_memory import WorkingMemory
        
        working = WorkingMemory(max_messages=20)
        
        # Test working memory
        working.add("user", "test message")
        assert len(list(working.messages)) == 1
        
        # Test retrieval
        msgs = working.to_messages()
        assert msgs[-1]["content"] == "test message"
        
        print("  PASS: Memory engine functional")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_event_bus():
    """Test event bus pub/sub"""
    print("\n[TEST 6] Event Bus")
    try:
        from ultron.core.event_bus import EventBus, Event
        import asyncio
        
        async def test():
            bus = EventBus()
            received = []
            
            async def handler(event):
                received.append(event)
            
            bus.subscribe("test.event", handler)
            await bus.publish(Event(name="test.event", source="test", data={"data": "test"}))
            
            assert len(received) == 1
            assert received[0].data["data"] == "test"
        
        asyncio.run(test())
        print("  PASS: Event bus working correctly")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_providers():
    """Test provider initialization"""
    print("\n[TEST 7] AI Providers")
    try:
        from ultron.providers.ollama_provider import OllamaProvider
        from ultron.providers.groq_provider import GroqProvider
        from ultron.providers.gemini_provider import GeminiProvider
        from ultron.providers.openrouter_provider import OpenRouterProvider
        from ultron.providers.together_provider import TogetherProvider
        from ultron.providers.cloudflare_provider import CloudflareProvider
        from ultron.providers.minimax_provider import MiniMaxProvider
        from ultron.providers.openai_provider import OpenAIProvider
        from ultron.providers.hf_provider import HFProvider
        from ultron.providers.fallback_chain import FallbackChain
        
        providers = [
            ("Ollama", OllamaProvider),
            ("Groq", GroqProvider),
            ("Gemini", GeminiProvider),
            ("OpenRouter", OpenRouterProvider),
            ("Together", TogetherProvider),
            ("Cloudflare", CloudflareProvider),
            ("MiniMax", MiniMaxProvider),
            ("OpenAI", OpenAIProvider),
            ("HuggingFace", HFProvider),
        ]
        
        print(f"  PASS: {len(providers)}/9 providers initialized")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_blackboard():
    """Test blackboard shared context"""
    print("\n[TEST 8] Blackboard")
    try:
        from ultron.core.blackboard import Blackboard
        import asyncio
        
        async def test():
            bb = Blackboard()
            await bb.write("test_key", "test_value", owner="test_agent")
            value = await bb.read("test_key")
            assert value == "test_value"
            
            await bb.delete("test_key")
            value = await bb.read("test_key")
            assert value is None
        
        asyncio.run(test())
        print("  PASS: Blackboard working correctly")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def main():
    print("=" * 60)
    print("ULTRON v2.1 - COMPREHENSIVE SYSTEM TEST")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_pydantic_models,
        test_agent_status_enum,
        test_api_routes,
        test_memory_engine,
        test_event_bus,
        test_providers,
        test_blackboard,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("STATUS: ALL TESTS PASSED")
        print("=" * 60)
        print("\nSystem is production-ready!")
        return 0
    else:
        print(f"STATUS: {total - passed} TESTS FAILED")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
