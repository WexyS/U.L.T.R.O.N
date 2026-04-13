# 🧠 Ultron Context Yönetim Sistemi

## Sorun
Qwen (LLM) ile uzun konuşmalar yaptığımızda context window dolar ve:
- ❌ Önceki konuşmaları unutur
- ❌ Dosya içeriklerini kaybeder
- ❌ AI bridge isteklerini işleyemez

## Çözüm: File-Based Context System

### 📂 Context Dosyaları

| Dosya | Amaç | Ne Zaman Güncellenir |
|-------|------|---------------------|
| `context/active_session.md` | Aktif konuşma özeti | Her mesaj sonrası |
| `context/project_state.md` | Proje durumu | Her değişiklik sonrası |
| `context/gemini_pending.md` | İşlenmemiş Gemini istekleri | Yeni istek gelince |
| `context/gemini_responded.md` | Yanıtlanan Gemini istekleri | Yanıt yazılınca |
| `context/task_queue.md` | Bekleyen görevler | Görev gelince |

### 🔄 Context Yenileme İş Akışı

```
1. Kullanıcı mesaj gönderir
2. Qwen:
   a. context/active_session.md okur (hatırlama)
   b. gemini_requests.md okur (yeni istekler)
   c. Görevleri işler
   d. context/active_session.md günceller (özet)
   e. Yanıt verir
```

### 💡 Context Compression

Her 10 mesajda bir:
- Uzun konuşmayı özetle
- Sadece önemli kararları kaydet
- Gereksiz detayları sil

## Şu Anki Context

```yaml
session_start: "2026-04-13 15:30"
last_update: "2026-04-13 16:45"
active_topics:
  - "AI Bridge (Qwen ↔ Gemini köprüsü)"
  - "Autonomous Evolution (3 mod: manual/semi/full)"
  - "Multi-Agent Orchestrator (planlama aşaması)"
  - "Memory optimization (SQLite + ChromaDB)"

pending_gemini_requests:
  - "İstek #2: Multi-Agent Task Orchestrator mimarisi"
  - "İstek #3: Memory Engine optimizasyonu"

completed:
  - "İstek #1: Evolution güvenlik kontrolleri ✅"
  - "AI Bridge Monitor kurulumu ✅"
  - "Context management sistemi ✅"

project_status:
  version: "2.1"
  agents: 8
  providers: 13
  new_features:
    - "AI Bridge Monitor (aktif)"
    - "Context Management (yeni)"
```

## Nasıl Kullanılır

### Qwen İçin (Her oturum başında):

```markdown
1. context/active_session.md oku
2. context/project_state.md oku
3. gemini_requests.md kontrol et
4. task_queue.md kontrol et
5. Görevleri işle
6. Context dosyalarını güncelle
```

### Kullanıcı İçin:

Sadece mesaj yazmaya devam et. Ben:
- ✅ Otomatik context yüklerim
- ✅ Önceki konuşmaları hatırlarım
- ✅ Gemini isteklerini işlerim
- ✅ Context dolunca özet çıkarırım
