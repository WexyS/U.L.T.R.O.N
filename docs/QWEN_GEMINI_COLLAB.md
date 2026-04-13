# 🤝 Qwen ↔ Gemini İşbirliği Kılavuzu

## 🎯 Nedir Bu?

Ultron (Qwen - yerel LLM) ile Gemini (bulut LLM) arasında **çift yönlü otonom iletişim** kurmanızı sağlayan sistem.

---

## 🚀 Hızlı Başlangıç

### 1. API Key Kurulumu

```bash
# .env dosyasına ekleyin:
OPENROUTER_API_KEY=sk-or-v1-...
```

> 🔑 **OpenRouter**: https://openrouter.ai/ - Ücretsiz kredi verir

### 2. Test Suite Çalıştır

```bash
python scripts/test_qwen_gemini_collab.py
```

---

## 📖 Kullanım Örnekleri

### Senaryo 1: Mimari Danışmanlık

Qwen çıkmaza girdiğinde Gemini'ye danışır:

```python
from ultron.actions.ask_architect import run

result = run({
    "question": "Microservice mi yoksa monolith mi kullanmalıyım? 10M kullanıcı hedefliyorum.",
    "mode": "consult"
})
print(result)
```

**Yanıt Formatı:**
```
🏗️ [Kıdemli Mimarın Yanıtı] (mode=consult)

📊 Analiz: 10M kullanıcı için...
💡 Öneri: Microservice kullan çünkü...

📊 Token Kullanımı: 234 (input) → 567 (output)
```

---

### Senaryo 2: Bug Debugging

İnatçı bug'larda Gemini'ye sor:

```python
result = run({
    "question": "Bu kod neden NoneType hatası veriyor?",
    "code_context": """
def get_user(id):
    user = db.query(id)
    return user.name  # ❌ AttributeError: 'NoneType' has no attribute 'name'
""",
    "mode": "consult"
})
```

---

### Senaryo 3: Kod Önerisi + Otomatik Uygulama

Gemini kod yazsın ve otomatik uygulasın:

```python
from ultron.actions.ask_architect import ask_and_apply

result = ask_and_apply(
    question="Bu fonksiyonu async yap ve error handling ekle",
    file_path="ultron/v2/memory/engine.py"
)
```

**Ne Yapar:**
1. ✅ Mevcut kodu okur
2. ✅ Gemini'ye danışır
3. ✅ Yedek oluşturur (`engine.py.backup`)
4. ✅ Yeni kodu uygular
5. ✅ Rapor döner

---

## 🔧 Modlar

| Mod | Amaç | Temperature | Kullanım |
|-----|------|-------------|----------|
| `consult` | Mimari danışmanlık | 0.3 | Karar alma, analiz |
| `implement` | Kod implementasyonu | 0.2 | Somut kod önerisi |

---

## 📊 Token Maliyetleri

OpenRouter üzerinden Gemini kullanımı:

| Model | Fiyat |
|-------|-------|
| `google/gemini-2.0-flash-exp:free` | 🆓 Ücretsiz |
| `google/gemini-2.5-flash` | 💰 ~$0.10/1M token |

**Ortalama Sorgu:**
- Input: ~500-1000 token
- Output: ~500-2000 token
- **Toplam maliyet**: ~$0.0001-0.0003/sorgu

---

## 🛡️ Güvenlik Notları

1. ✅ **Yedekleme**: `ask_and_apply` otomatik yedek oluşturur
2. ✅ **API Key**: Sadece `.env` dosyasında, git'e push etmeyin
3. ✅ **Rate Limit**: OpenRouter'da 10 req/min (free tier)
4. ⚠️ **Dikkat**: Otomatik uygulama modunu kullanmadan önce Git commit yapın

---

## 🔄 Gelişmiş Kullanım: Qwen ↔ Gemini Döngüsü

```python
from ultron.actions.ask_architect import run, ask_and_apply

# 1. Qwen problem tespit eder
problem = "Memory search yavaş, 2s sürüyor"

# 2. Gemini'ye danış
advice = run({
    "question": f"Bu sorunu nasıl optimize ederim?\n{problem}",
    "code_context": open("ultron/v2/memory/engine.py").read(),
    "mode": "consult"
})

# 3. Gemini'nin önerisini uygula
result = ask_and_apply(
    question="Bu optimizasyonu uygula",
    file_path="ultron/v2/memory/engine.py"
)

# 4. Qwen sonucu test eder
# (tests/ klasöründe test çalıştır)
```

---

## 🐛 Sorun Giderme

### "OPENROUTER_API_KEY bulunamadı"
```bash
# Windows
set OPENROUTER_API_KEY=sk-or-v1-...

# Linux/macOS
export OPENROUTER_API_KEY=sk-or-v1-...
```

### "Timeout hatası"
- İnternet bağlantınızı kontrol edin
- OpenRouter API status: https://status.openrouter.ai

### "Kod bloğu bulunamadı"
- Gemini'nin yanıtını manuel kontrol edin
- Temperature'ü düşürün (daha deterministik yanıt için)

---

## 🎓 Örnek İş Akışları

### Workflow 1: Feature Development
```
User Request → Qwen Analiz → Gemini Mimari Onay → Qwen Implement → Test
```

### Workflow 2: Bug Fix
```
Bug Report → Qwen Debug → Gemini Root Cause → Qwen Fix → Test
```

### Workflow 3: Code Review
```
Qwen Code Review → Gemini Best Practices → Qwen Refactor → Lint
```

---

## 📚 Daha Fazlası

- 📖 OpenRouter Docs: https://openrouter.ai/docs
- 🧠 Gemini Docs: https://ai.google.dev/docs
- 🤖 Ultron Wiki: `docs/` klasörü

---

<div align="center">

**🔥 İki AI, bir beyin: Qwen + Gemini = Ultron v2.1**

</div>
