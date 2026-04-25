"""AirLLM 405B Integration Test

Bu script AirLLM provider'ının doğru çalıştığını test eder.

Testler:
1. Provider import
2. Provider initialization
3. Model info
4. Configuration loading
5. Router integration

Kullanım:
    python scripts/test_airllm_405b.py
"""

import os
import sys
from pathlib import Path

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import():
    """Test 1: Import"""
    print("\n" + "="*60)
    print("🧪 TEST 1: AirLLM Provider Import")
    print("="*60)
    
    try:
        from ultron.providers.airllm_provider import AirLLMProvider, create_provider
        print("✅ AirLLMProvider imported successfully")
        print("✅ create_provider factory imported")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_initialization():
    """Test 2: Provider initialization"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Provider Initialization")
    print("="*60)
    
    try:
        from ultron.providers.airllm_provider import AirLLMProvider
        
        provider = AirLLMProvider(
            model_name="meta-llama/Llama-3.1-405B-Instruct",
            compression="4bit",
            prefetching=True
        )
        
        print(f"✅ Provider initialized")
        print(f"   Model: {provider.model_name}")
        print(f"   Compression: {provider.compression}")
        print(f"   Prefetching: {provider.prefetching}")
        
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


def test_model_info():
    """Test 3: Model info"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Model Info")
    print("="*60)
    
    try:
        from ultron.providers.airllm_provider import AirLLMProvider
        
        provider = AirLLMProvider(
            model_name="meta-llama/Llama-3.1-405B-Instruct",
            compression="4bit"
        )
        
        info = provider.get_model_info()
        
        print(f"✅ Model info retrieved:")
        for key, value in info.items():
            print(f"   {key}: {value}")
        
        return True
    except Exception as e:
        print(f"❌ Model info failed: {e}")
        return False


def test_factory():
    """Test 4: Factory function"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Factory Function")
    print("="*60)
    
    try:
        from ultron.providers.airllm_provider import create_provider
        
        config = {
            "model_name": "meta-llama/Llama-3.1-405B-Instruct",
            "compression": "4bit",
            "prefetching": True
        }
        
        provider = create_provider(config)
        
        print(f"✅ Factory created provider")
        print(f"   Model: {provider.model_name}")
        print(f"   Compression: {provider.compression}")
        
        return True
    except Exception as e:
        print(f"❌ Factory failed: {e}")
        return False


def test_router_integration():
    """Test 5: Router integration"""
    print("\n" + "="*60)
    print("🧪 TEST 5: Router Integration")
    print("="*60)
    
    try:
        from ultron.providers.router import ProviderRouter, TASK_ROUTES
        
        print(f"✅ ProviderRouter imported")
        print(f"✅ TASK_ROUTES available")
        
        # deep_analysis route kontrol
        if "deep_analysis" in TASK_ROUTES:
            print(f"   deep_analysis route: {TASK_ROUTES['deep_analysis']}")
        else:
            print(f"   ⚠️ deep_analysis route yok!")
        
        # sleep_mode route kontrol
        if "sleep_mode" in TASK_ROUTES:
            print(f"   sleep_mode route: {TASK_ROUTES['sleep_mode']}")
        else:
            print(f"   ⚠️ sleep_mode route yok!")
        
        return True
    except Exception as e:
        print(f"❌ Router integration failed: {e}")
        return False


def test_config():
    """Test 6: Configuration"""
    print("\n" + "="*60)
    print("🧪 TEST 6: Environment Configuration")
    print("="*60)
    
    airllm_model = os.environ.get("AIRLLM_MODEL", "meta-llama/Llama-3.1-405B-Instruct")
    airllm_compression = os.environ.get("AIRLLM_COMPRESSION", "4bit")
    airllm_prefetching = os.environ.get("AIRLLM_PREFETCHING", "true")
    
    print(f"✅ Environment variables:")
    print(f"   AIRLLM_MODEL: {airllm_model}")
    print(f"   AIRLLM_COMPRESSION: {airllm_compression}")
    print(f"   AIRLLM_PREFETCHING: {airllm_prefetching}")
    
    # .env file kontrol
    from pathlib import Path
    env_file = Path(".env")
    if env_file.exists():
        print(f"   .env file: ✅ EXISTS")
    else:
        print(f"   .env file: ⚠️ NOT FOUND (copy .env.example to .env)")
    
    return True


def main():
    """Tüm testleri çalıştır"""
    print("\n" + "🔥"*30)
    print("🚀 AIRLLM 405B INTEGRATION TEST")
    print("🔥"*30)
    
    tests = [
        ("Import", test_import),
        ("Initialization", test_initialization),
        ("Model Info", test_model_info),
        ("Factory", test_factory),
        ("Router Integration", test_router_integration),
        ("Configuration", test_config),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Test sırasında hata: {e}")
            results.append((name, False))
    
    # Özet
    print("\n" + "="*60)
    print("📊 TEST ÖZETİ")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\n📈 Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! AirLLM 405B integration ready!")
        return True
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
