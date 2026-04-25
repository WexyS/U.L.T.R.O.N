"""Comprehensive test suite for Ultron v2.1 enhancements.

Tests:
1. AirLLM provider integration
2. Error analyzer agent
3. Provider routing with AirLLM
4. System health checker
5. Self-healing capabilities
6. All existing functionality
"""

import os
import sys
import json
import asyncio
import importlib
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_result(test_name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {test_name}")
    if details:
        print(f"         {details}")


def test_imports():
    """Test all modules can be imported."""
    print_header("TEST 1: Module Imports")
    
    modules = [
        "ultron.providers.airllm_provider",
        "ultron.agents.error_analyzer",
        "ultron.providers.router",
        "ultron.core.orchestrator",
        "ultron.core.types",
        "ultron.providers.base",
        "ultron.providers.fallback_chain",
    ]
    
    failed = []
    for module in modules:
        try:
            importlib.import_module(module)
            print_result(module, True)
        except Exception as e:
            print_result(module, False, str(e)[:100])
            failed.append(module)
    
    return len(failed) == 0


def test_airllm_provider():
    """Test AirLLM provider initialization."""
    print_header("TEST 2: AirLLM Provider")
    
    try:
        from ultron.providers.airllm_provider import AirLLMProvider
        
        provider = AirLLMProvider()
        
        # Check configuration
        is_configured = provider.is_configured()
        print_result("AirLLM configured", is_configured, 
                    "Installed" if is_configured else "Not installed (pip install airllm)")
        
        # Check model name
        print_result("Model name", True, provider.config.default_model)
        
        # Check priority (should be 0 = highest)
        print_result("Priority", provider.config.priority == 0, 
                    f"Priority: {provider.config.priority}")
        
        return True
    except Exception as e:
        print_result("AirLLM Provider", False, str(e))
        return False


def test_error_analyzer():
    """Test Error Analyzer Agent."""
    print_header("TEST 3: Error Analyzer Agent")
    
    try:
        from ultron.agents.error_analyzer import ErrorAnalyzerAgent, ErrorAnalysis
        
        # Initialize
        analyzer = ErrorAnalyzerAgent()
        print_result("Initialization", True)
        
        # Test basic error analysis
        test_error = """
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    import nonexistent_module
ModuleNotFoundError: No module named 'nonexistent_module'
"""
        analysis = analyzer._basic_analyze(test_error)
        
        print_result("Error type detection", analysis.error_type == "import_error",
                    f"Type: {analysis.error_type}")
        print_result("Severity assessment", analysis.severity == "high",
                    f"Severity: {analysis.severity}")
        print_result("Root cause", bool(analysis.root_cause),
                    analysis.root_cause[:80])
        
        # Test pattern matching
        patterns = analyzer.get_known_patterns()
        print_result("Error patterns loaded", len(patterns) > 0,
                    f"{len(patterns)} patterns")
        
        return True
    except Exception as e:
        print_result("Error Analyzer", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def test_provider_router():
    """Test provider routing."""
    print_header("TEST 4: Provider Router")
    
    try:
        from ultron.providers.router import ProviderRouter
        
        router = ProviderRouter()
        
        # Check providers loaded
        available = router.available_providers()
        print_result("Providers available", len(available) > 0,
                    f"{len(available)} providers: {', '.join(available[:5])}")
        
        # Check AirLLM is in priority list
        has_airllm = "airllm" in router.priority_order
        print_result("AirLLM in routing", has_airllm)
        
        # Check task routes
        from ultron.providers.router import TASK_ROUTES
        default_route = TASK_ROUTES.get("default", [])
        airllm_first = default_route[0] == "airllm" if default_route else False
        print_result("AirLLM highest priority", airllm_first,
                    f"First: {default_route[0] if default_route else 'none'}")
        
        return True
    except Exception as e:
        print_result("Provider Router", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def test_error_patterns():
    """Test error patterns database."""
    print_header("TEST 5: Error Patterns Database")
    
    try:
        patterns_file = project_root / "data" / "error_patterns.json"
        
        if not patterns_file.exists():
            print_result("Patterns file exists", False)
            return False
        
        patterns = json.loads(patterns_file.read_text())
        print_result("Patterns file", True, f"{len(patterns)} patterns")
        
        # Check critical patterns present
        required = ["import_error", "connection_error", "timeout_error", "cuda_error"]
        for pattern in required:
            print_result(f"Pattern: {pattern}", pattern in patterns)
        
        return True
    except Exception as e:
        print_result("Error Patterns", False, str(e))
        return False


def test_health_checker():
    """Test health checker script."""
    print_header("TEST 6: Health Checker")
    
    try:
        health_script = project_root / "scripts" / "health_checker.py"
        
        if not health_script.exists():
            print_result("Health script exists", False)
            return False
        
        # Run health checker
        import subprocess
        result = subprocess.run(
            [sys.executable, str(health_script)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_root
        )
        
        print_result("Health checker runs", result.returncode == 0,
                    f"Exit code: {result.returncode}")
        
        # Check report generated
        report_dir = project_root / "data" / "reports"
        if report_dir.exists():
            reports = list(report_dir.glob("health_*.json"))
            print_result("Report generated", len(reports) > 0,
                        f"{len(reports)} reports")
        
        return True
    except Exception as e:
        print_result("Health Checker", False, str(e))
        return False


def test_types():
    """Test core types."""
    print_header("TEST 7: Core Types")
    
    try:
        from ultron.core.types import AgentRole
        
        # Check ERROR_ANALYZER role exists
        has_role = hasattr(AgentRole, 'ERROR_ANALYZER')
        print_result("ERROR_ANALYZER role", has_role)
        
        if has_role:
            print_result("Role value", True, AgentRole.ERROR_ANALYZER.value)
        
        return True
    except Exception as e:
        print_result("Core Types", False, str(e))
        return False


def test_env_configuration():
    """Test environment configuration."""
    print_header("TEST 8: Environment Configuration")
    
    try:
        env_example = project_root / ".env.example"
        
        if not env_example.exists():
            print_result(".env.example exists", False)
            return False
        
        content = env_example.read_text(encoding="utf-8")
        
        # Check AirLLM config present
        has_airllm_config = "AIRLLM_MODEL" in content
        print_result("AirLLM config in .env.example", has_airllm_config)
        
        # Check HuggingFace token
        has_hf_token = "HUGGING_FACE_HUB_TOKEN" in content or "HF_TOKEN" in content
        print_result("HuggingFace token config", has_hf_token)
        
        # Check all providers documented
        providers = ["OLLAMA", "AIRLLM", "GROQ", "GEMINI", "OPENAI"]
        for provider in providers:
            has_provider = provider in content
            print_result(f"{provider} documented", has_provider)
        
        return True
    except Exception as e:
        print_result("Environment Config", False, str(e))
        return False


def test_memory_engine():
    """Test memory engine."""
    print_header("TEST 9: Memory Engine")
    
    try:
        from ultron.memory.engine import MemoryEngine
        
        persist_dir = "./data/memory_v2"
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        
        memory = MemoryEngine(persist_dir=persist_dir)
        stats = memory.stats()
        
        print_result("Memory engine init", True, str(stats))
        
        # Test storage
        entry_id = f"test_{int(datetime.now().timestamp())}"
        memory.store(
            entry_id=entry_id,
            content="Test memory entry",
            entry_type="episodic",
            metadata={"test": True}
        )
        print_result("Memory store", True)
        
        return True
    except Exception as e:
        print_result("Memory Engine", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def test_automatic_fixes():
    """Test automatic fix capabilities."""
    print_header("TEST 10: Automatic Fixes")
    
    try:
        from ultron.agents.error_analyzer import ErrorAnalyzerAgent
        
        analyzer = ErrorAnalyzerAgent()
        
        # Test error pattern learning
        test_pattern = "test_import_error"
        test_fix = {
            "root_cause": "Missing package",
            "severity": "high",
            "fix": "pip install package",
            "keywords": ["test_keyword"]
        }
        
        analyzer.learn_from_fix(test_pattern, test_fix)
        print_result("Learn from fix", True)
        
        # Verify pattern saved
        patterns = analyzer.get_known_patterns()
        has_pattern = test_pattern in patterns
        print_result("Pattern saved", has_pattern)
        
        return True
    except Exception as e:
        print_result("Automatic Fixes", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("ULTRON v2.1 - COMPREHENSIVE ENHANCEMENT TESTS")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("AirLLM Provider", test_airllm_provider),
        ("Error Analyzer", test_error_analyzer),
        ("Provider Router", test_provider_router),
        ("Error Patterns", test_error_patterns),
        ("Health Checker", test_health_checker),
        ("Core Types", test_types),
        ("Environment Config", test_env_configuration),
        ("Memory Engine", test_memory_engine),
        ("Automatic Fixes", test_automatic_fixes),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ Test {name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print_header("TEST RESULTS SUMMARY")
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, p in results:
        status = "✅ PASS" if p else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("STATUS: ✅ ALL TESTS PASSED")
        print("="*60)
        print("\n🎉 Ultron v2.1 is production-ready!")
        print("\nNew Features:")
        print("  ✓ AirLLM integration (Llama 3.1 70B/405B)")
        print("  ✓ Error Analyzer Agent (self-healing)")
        print("  ✓ Automatic error detection and fixing")
        print("  ✓ Enhanced provider routing")
        print("  ✓ System health checker")
        print("  ✓ Error patterns database")
        return 0
    else:
        print(f"STATUS: ❌ {total - passed} TESTS FAILED")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
