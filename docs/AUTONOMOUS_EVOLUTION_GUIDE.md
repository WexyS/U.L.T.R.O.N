# 🧬 Autonomous Evolution - Güvenlik ve Kullanım Kılavuzu

## ⚠️ ÖNEMLİ GÜVENLİK UYARISI

Bu sistem **güçlü otonom yeteneklere** sahiptir. Dikkatli kullanın!

---

## 📋 İçindekiler

1. [Güvenlik Seviyeleri](#güvenlik-seviyeleri)
2. [Hızlı Başlangıç](#hızlı-başlangıç)
3. [Nasıl Çalışır](#nasıl-çalışır)
4. [Güvenlik Önlemleri](#güvenlik-önlemleri)
5. [Best Practices](#best-practices)

---

## 🔐 Güvenlik Seviyeleri

### 1. MANUAL_ONBOARDING (ÖNERİLEN)

```bash
python scripts/autonomous_evolution.py --mode manual
```

**Davranış:**
- ✅ Her entegrasyonda insan onayı bekler
- ✅ Gemini'nin önerisini gösterir
- ✅ "Evet/Hayır" sorar
- ✅ Git push öncesi onay alır

**Kullanım:** Production sistemler, ilk testler

---

### 2. SEMI_AUTONOMOUS

```bash
python scripts/autonomous_evolution.py --mode semi
```

**Davranış:**
- ✅ Düşük/Orta karmaşıklık: Otomatik
- ⚠️ Yüksek karmaşıklık: İnsan onayı
- ✅ Git push öncesi onay

**Kullanım:** Geliştirme ortamı, güven arttıktan sonra

---

### 3. FULLY_AUTONOMOUS (RİSKLİ!)

```bash
python scripts/autonomous_evolution.py --mode full
```

**Davranış:**
- ❌ HİÇ insan onayı beklemez
- ❌ Tüm değişiklikleri otomatik uygular
- ❌ Otomatik git push yapar
- ⚠️ API rate limit'e dikkat!

**Kullanım:** SADECE izlenmiş test ortamı

---

## 🚀 Hızlı Başlangıç

### 1. İlk Test (Manual)

```bash
# API key kontrol
set OPENROUTER_API_KEY=sk-or-v1-...

# Manual modda çalıştır
python scripts/autonomous_evolution.py --mode manual
```

**Ne Olacak:**
1. 🔍 3 yeni AI aracı bulacak (simulated)
2. 🧠 Her biri için Gemini'ye danışacak
3. ⏸️ Sizden onay isteyecek
4. ✅ Onaylarsanız entegre edecek
5. 📦 Git commit + push yapacak

---

### 2. Sürekli Evrim

```bash
# Her 24 saatte bir çalış
python scripts/autonomous_evolution.py --mode manual --continuous --interval 24
```

---

## 🔄 Nasıl Çalışır

### Evolution Döngüsü

```
┌─────────────────────────────────────┐
│  1. RESEARCH                        │
│  Yeni AI araçları bul               │
│  (web_search, GitHub, papers)       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  2. CONSULT ARCHITECT (Gemini)     │
│  "Bu aracı nasıl entegre edeyım?"  │
│  → Mimari öneri al                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. IMPLEMENT (Onaylı)             │
│  - Bağımlılık ekle                  │
│  - Agent/Skill kodu yaz             │
│  - Testleri güncelle                │
│  - Test çalıştır                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  4. COMMIT & PUSH                   │
│  - git add .                        │
│  - git commit                       │
│  - git push (opsiyonel)             │
└──────────────┬──────────────────────┘
               │
               ▼
        [Döngü başa dön]
```

---

## 🛡️ Güvenlik Önlemleri

### Otomatik Olarak Uygulanan

1. ✅ **API Rate Limiting**: 10 saniye bekleme her sorgu arası
2. ✅ **Evolution Log**: Tüm değişiklikler `data/evolution_log.json`'da
3. ✅ **Error Handling**: Her hata yakalanır ve loglanır
4. ✅ **Mode System**: İnsan onayı gerektiren seviyeler

### Manuel Olarak Eklenmesi Gerekenler

1. ⚠️ **Git Branch Protection**: Production branch'i koruyun
2. ⚠️ **CI/CD Pipeline**: Otomatik testler şart
3. ⚠️ **Backup Strategy**: Her değişiklik öncesi yedek
4. ⚠️ **Rollback Planı**: `git revert` hazır olsun

---

## 📚 Best Practices

### ✅ DO (Yap)

- ✅ **Manual modda başla**: İlk birkaç hafta sadece manual
- ✅ **Logları incele**: `data/evolution_log.json`'u takip et
- ✅ **Test çalıştır**: Her entegrasyon sonrası `pytest`
- ✅ **Code review**: Gemini'nin önerisini dikkatlice oku
- ✅ **Branch kullan**: `git checkout -b evolution-test` gibi

### ❌ DON'T (Yapma)

- ❌ **Full autonomous ile başlama**: En az 1 ay manual/semi kullan
- ❌ **Production'da test etme**: Sadece development branch
- ❌ **Logları silme**: `evolution_log.json` önemli
- ❌ **API limit'i görmezden gel**: Rate limit var,尊重 et

---

## 🐛 Sorun Giderme

### "OPENROUTER_API_KEY bulunamadı"

```bash
# Windows
set OPENROUTER_API_KEY=sk-or-v1-...

# Linux/macOS
export OPENROUTER_API_KEY=sk-or-v1-...
```

### "Web search entegrasyonu yok"

Şu anda `research_new_tools()` manuel öneriler döndürüyor. Gerçek web_search için:

```python
# scripts/autonomous_evolution.py içinde:
from ultron.actions.web_search import run as web_search

# research_new_tools() fonksiyonunu güncelle:
results = web_search({"query": "new AI tools 2025"})
```

### "Git push başarısız"

```bash
# Git remote kontrol
git remote -v

# Authentication kontrol
gh auth status  # GitHub CLI varsa
```

---

## 📊 Evolution Geçmişi

Her entegrasyon `data/evolution_log.json`'a kaydedilir:

```json
[
  {
    "tool": "LangGraph",
    "action": "integrated",
    "timestamp": "2025-04-13T15:30:00",
    "mode": "manual",
    "advice_length": 1250
  },
  {
    "tool": "CrewAI",
    "action": "rejected_by_human",
    "timestamp": "2025-04-13T15:35:00",
    "reason": "Human did not approve"
  }
]
```

**Analiz:**
```bash
# Kaç entegrasyon yapılmış?
python -c "import json; data=json.load(open('data/evolution_log.json')); print(f'{len(data)} evolution')"

# Hangi tool'lar reddedilmiş?
python -c "import json; data=json.load(open('data/evolution_log.json')); print([d['tool'] for d in data if 'rejected' in d['action']])"
```

---

## 🎯 Gelecek Geliştirmeler

- [ ] Gerçek web_search entegrasyonu
- [ ] Otomatik test yazma
- [ ] CI/CD pipeline entegrasyonu
- [ ] Rollback otomasyonu
- [ ] Smart prioritization (AI-driven)
- [ ] Multi-agent research (parallel)
- [ ] A/B testing framework

---

<div align="center">

**🧬 Ultron kendi kendini geliştiriyor - Ama güvenli!**

</div>
