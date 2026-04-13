"""
Qwen ↔ Gemini İşbirliği Test Suite

Bu script, iki AI'nin otonom iletişimini test eder:
1. Qwen → Gemini: Mimari danışmanlık
2. Gemini → Qwen: Kod önerisi uygulama

Kullanım:
    python scripts/test_qwen_gemini_collab.py
"""

import os
import sys
from pathlib import Path

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from ultron.actions.ask_architect import run, ask_and_apply


def test_consult_mode():
    """Test 1: Gemini'ye mimari danışmanlık sorusu sor"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Mimari Danışmanlık (consult mode)")
    print("="*60)
    
    result = run({
        "question": "Ultron'da 8 agent var. Bunlar arası iletişim için event-based mi yoksa shared blackboard mu daha iyi? Neden?",
        "mode": "consult"
    })
    
    print(f"\n✅ Yanıt:\n{result}\n")
    return "❌ Hata" not in result


def test_debug_mode():
    """Test 2: Gemini'ye bug danışma"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Bug Debugging (consult mode)")
    print("="*60)
    
    code_context = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total
    
# Hata: KeyError: 'quantity' bazı item'larda yok
"""
    
    result = run({
        "question": "Bu fonksiyon KeyError veriyor çünkü bazı item'larda 'quantity' eksik. Nasıl düzeltebilirim?",
        "code_context": code_context,
        "mode": "consult"
    })
    
    print(f"\n✅ Yanıt:\n{result}\n")
    return "❌ Hata" not in result


def test_implementation_mode():
    """Test 3: Gemini'den kod önerisi al"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Kod Önerisi (implement mode)")
    print("="*60)
    
    code_context = """
class MemoryEngine:
    def __init__(self):
        self.memories = []
    
    def add_memory(self, memory):
        self.memories.append(memory)
    
    def search(self, query):
        # TODO: Implement hybrid search (vector + FTS5)
        pass
"""
    
    result = run({
        "question": "search metodunu hybrid search (vector similarity + keyword FTS5) ile implement et",
        "code_context": code_context,
        "mode": "implement"
    })
    
    print(f"\n✅ Yanıt:\n{result}\n")
    return "❌ Hata" not in result


def test_auto_apply():
    """Test 4: Gemini'nin önerisini otomatik uygula"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Otomatik Kod Uygulama")
    print("="*60)
    
    # Test dosyası oluştur
    test_file = Path("test_gemini_apply.py")
    test_file.write_text(
        "# Test dosyası - Gemini bunu düzeltecek\n"
        "def broken_function():\n"
        "    # TODO: Implement this\n"
        "    pass\n",
        encoding="utf-8"
    )
    
    print(f"📝 Test dosyası oluşturuldu: {test_file}")
    
    result = ask_and_apply(
        question="bu fonksiyonu implement et: 'Hello World' döndürsün",
        file_path=str(test_file)
    )
    
    print(f"\n✅ Sonuç:\n{result}\n")
    
    # Temizlik
    backup_file = Path("test_gemini_apply.py.backup")
    if test_file.exists():
        print(f"\n📄 Güncellenmiş dosya içeriği:")
        print(test_file.read_text(encoding="utf-8"))
        test_file.unlink()
    
    if backup_file.exists():
        backup_file.unlink()
    
    return "❌ Hata" not in result


def main():
    """Tüm testleri çalıştır"""
    print("\n" + "🔥"*30)
    print("🚀 QWEN ↔ GEMINI İŞBİRLİĞİ TEST SUITE")
    print("🔥"*30)
    
    # API key kontrolü
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("\n❌ OPENROUTER_API_KEY bulunamadı!")
        print("Lütfen .env dosyasına ekleyin veya:")
        print("  set OPENROUTER_API_KEY=sk-or-v1-...")
        return False
    
    tests = [
        ("Mimari Danışmanlık", test_consult_mode),
        ("Bug Debugging", test_debug_mode),
        ("Kod Önerisi", test_implementation_mode),
        ("Otomatik Uygulama", test_auto_apply),
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
        status = "✅ BAŞARILI" if success else "❌ BAŞARISIZ"
        print(f"{status}: {name}")
    
    print(f"\n📈 Toplam: {passed}/{total} test başarılı")
    
    if passed == total:
        print("\n🎉 TÜM TESTLER BAŞARILI! Qwen ↔ Gemini işbirliği hazır!")
        return True
    else:
        print(f"\n⚠️ {total - passed} test başarısız. API key'i veya bağlantıyı kontrol edin.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
