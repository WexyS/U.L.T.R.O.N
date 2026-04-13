<div align="center">

# Ultron v2.1

> An Advanced, Autonomous AI Assistant System

<p>
  <a href="#features"><strong>Features</strong></a> •
  <a href="#quick-start"><strong>Quick Start</strong></a> •
  <a href="#architecture"><strong>Architecture</strong></a> •
  <a href="#agents"><strong>Agents</strong></a> •
  <a href="#13-ai-providers"><strong>13 AI Providers</strong></a> •
  <a href="#workspace--rag"><strong>Workspace</strong></a> •
  <a href="#memory-system"><strong>Memory</strong></a> •
  <a href="#api-reference"><strong>API</strong></a> •
  <a href="#qwen--gemini-collab"><strong>AI Collaboration</strong></a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/Ollama-Local%20LLM-FF6F00?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama">
  <img src="https://img.shields.io/badge/13%20Providers-Multi--AI-purple?style=for-the-badge" alt="Providers">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

**Personal, locally-hosted, multi-agent AI assistant with 13 AI providers, workspace RAG, and a modern 3-panel GUI.**

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Multi-Agent Architecture** | 8 specialized agents — coder, researcher, RPA, email, sysmon, clipboard, meeting, files |
| 🌐 **13 AI Providers** | Ollama, Groq, DeepSeek, Anthropic, OpenRouter, Gemini, Mistral, Fireworks, Cloudflare, Together, Cohere, HuggingFace, OpenAI — with smart routing + auto-fallback |
| 💼 **Workspace + RAG** | Clone websites, generate apps from ideas, synthesize new apps from existing templates via ChromaDB semantic search |
| 🧩 **3-Layer Memory** | Working → Long-Term (SQLite + ChromaDB) → Procedural — with decay & consolidation |
| 💻 **RPA Capabilities** | Screen capture, OCR, mouse/keyboard automation via pyautogui + mss + EasyOCR |
| 📧 **Email Assistant** | IMAP/SMTP async inbox reading, smart summarization, draft creation & sending |
| 🖥️ **System Monitor** | Real-time CPU/RAM/disk monitoring with proactive threshold alerts |
| 📋 **Clipboard Intelligence** | Auto-detects text/URL/code in clipboard — summarizes, translates, or reviews |
| 🎙️ **Meeting Transcription** | Live Whisper-based transcription with action item extraction |
| 📁 **File Organizer** | Watchdog-powered directory monitoring, content-based classification, duplicate detection |
| 🎨 **Modern 3-Panel GUI** | React + Framer Motion + Tailwind — sidebar, chat/workspace toggle, inspector panel |
| 🔌 **n8n Integration** | 3 ready-to-import webhook workflows (clone, generate, synthesize) |
| 🔒 **Security First** | Scoped CORS, optional API key auth, rate limiting, structured logging |
| 🧬 **Autonomous Evolution** | Self-improving system — researches new tools, consults Gemini, auto-integrates with human approval |

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.10+ | Backend runtime |
| **Node.js** | 18+ | GUI build toolchain |
| **Ollama** | Latest | Local LLM runtime |

### One-Command Launch

```bash
# Windows — double-click or run:
start-ultron-desktop.bat
```

That's it. The script:
1. ✅ Activates the virtual environment
2. 🚀 Starts the FastAPI backend (`:8000`)
3. ⏳ Waits for health check (auto-retry loop)
4. 🎨 Launches the React frontend (`:5173`)

### Manual Setup

```bash
# 1. Create & activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Install Playwright Chromium (for workspace cloning)
playwright install chromium

# 4. Install & run Ollama
ollama pull qwen2.5:14b          # Download model
ollama serve                     # Start server

# 5. Start backend
python -m uvicorn ultron.api.main:app --host 127.0.0.1 --port 8000

# 6. Start frontend (in another terminal)
cd ultron-desktop && npm install && npm run dev
```

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Ultron v2.1                                     │
├────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐              ┌──────────────────────────┐    │
│  │  React + Vite GUI   │◄────────────►│   FastAPI Backend        │    │
│  │  (port 5173)        │   HTTP/WS    │   (port 8000)            │    │
│  │                     │              │                          │    │
│  │  ┌───────────────┐  │              │  /ws/chat  (streaming)   │    │
│  │  │ Sidebar (240) │  │              │  /status  (agents/LLMs)  │    │
│  │  │ Chat/Workspace│  │              │  /api/v2/chat (router)   │    │
│  │  │ Inspector(300)│  │              │  /api/v2/workspace/*     │    │
│  │  └───────────────┘  │              │  /api/v2/providers/status│    │
│  └─────────────────────┘              └────────────┬─────────────┘    │
│                                                    │                   │
│                                 ┌──────────────────▼──────────────┐    │
│                                 │        Orchestrator             │    │
│                                 │  (Intent Classification + Plan)  │    │
│                                 └──────────────────┬──────────────┘    │
│                                                    │                   │
│     ┌────────────┬────────────┬────────┬───────────┼────────┬───────┐  │
│     │            │            │        │           │        │       │  │
│  ┌──▼──┐ ┌─────▼───┐ ┌─────▼────┐ ┌──▼──┐ ┌───▼────┐│┌─────▼──────┐│  │
│  │Coder│ │Researcher│ │  RPA     │ │Email│ │SysMon  │ │Clipboard  │  │
│  │Agent│ │ Agent    │ │ Operator │ │Agent│ │ Agent  │ │ Agent     │  │
│  └─────┘ └──────────┘ └──────────┘ └─────┘ └────────┘ └───────────┘  │
│  ┌───────────┐ ┌───────────┐                                          │
│  │ Meeting   │ │  File     │                                          │
│  │ Agent     │ │ Organizer │                                          │
│  └───────────┘ └───────────┘                                          │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    Memory System                                │    │
│  │  Working (20 msgs) → Long-Term (SQLite+ChromaDB) → Procedural  │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │              13 AI Providers (Smart Router + Fallback)          │    │
│  │                                                                │    │
│  │  1. Ollama (local)  →  2. Groq  →  3. DeepSeek                │    │
│  │  4. Anthropic       →  5. OpenRouter  →  6. Gemini            │    │
│  │  7. Mistral         →  8. Fireworks  →  9. Cloudflare         │    │
│  │  10. Together       →  11. Cohere  →  12. HuggingFace         │    │
│  │  13. OpenAI (paid fallback)                                    │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                  Workspace + RAG System                         │    │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐  │    │
│  │  │ Playwright│  │ CodeGenerator│  │ RAG Synthesizer           │  │    │
│  │  │  Clone    │  │  (Ollama)    │  │  (ChromaDB + LLM)        │  │    │
│  │  └──────────┘  └──────────────┘  └──────────────────────────┘  │    │
│  │  SQLite manifest  +  ChromaDB embeddings  +  Workspace grid    │    │
│  └────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agents

### 1. CoderAgent 💻
Writes, debugs, and executes code with an auto-healing loop (up to 5 iterations).

```
"Write a fibonacci function in Python"
"Fix this bug"
```

### 2. ResearcherAgent 🔍
Multi-hop web research via DuckDuckGo + URL scraping + LLM synthesis with citations.

```
"What is quantum computing?"
"Research the best Rust frameworks"
```

### 3. RPAOperatorAgent 🖱️
Computer-use agent — screenshot, OCR, mouse click, keyboard input, app launching.

```
"Open Chrome"
"Open YouTube"
```

### 4. EmailAgent 📧
Async IMAP/SMTP inbox reading, smart summarization, draft creation & sending.

```
"Summarize my emails"            → Top 5 important emails
"Morning briefing"               → Morning briefing
"Draft an email to John"         → Draft email
```

### 5. SystemMonitorAgent 🖥️
Real-time CPU/RAM/disk monitoring with proactive threshold alerts.

```
"System status"                  → Full metrics
"Top RAM-consuming processes"    → Top processes
```

### 6. ClipboardAgent 📋
Auto-detects clipboard content type (text/URL/code) and processes accordingly.

```
"Analyze code in clipboard"     → Code review
"Translate clipboard text"      → Translation
"Summarize clipboard URL"       → Fetch + summarize
```

### 7. MeetingAgent 🎙️
Live Whisper-based transcription with action item extraction.

```
"Start recording"               → Start recording
"Stop meeting"                  → Stop & transcribe
"Summarize"                     → Summary + action items
```

Output: `data/meetings/YYYY-MM-DD_HH-MM.md`

### 8. FileOrganizerAgent 📁
Content-based file classification, duplicate detection, desktop cleanup.

```
"Organize desktop"              → Organize desktop
"Find duplicates"               → Find duplicates
"Organize downloads"            → Organize downloads
```

---

## 🌐 13 AI Providers

Ultron routes to **13 AI providers** with task-aware selection and automatic fallback:

| # | Provider | Type | Cost | Best For |
|---|----------|------|------|----------|
| 1 | **Ollama** | Local | 🆓 Free | Privacy, code generation |
| 2 | **Groq** | Cloud | 🆓 Free | Speed (500 tok/s) |
| 3 | **DeepSeek** | Cloud | 💰 Cheap ($0.14/M tok) | Code, reasoning |
| 4 | **Anthropic** | Cloud | 💳 Paid | Understanding, analysis |
| 5 | **OpenRouter** | Cloud | 🆓+💳 Mixed | 200+ models, variety |
| 6 | **Gemini** | Cloud | 🆓 Free | Long context (1M) |
| 7 | **Mistral** | Cloud | 💳 Paid | GDPR compliance |
| 8 | **Fireworks** | Cloud | 💳 Paid | Fast inference |
| 9 | **Cloudflare** | Cloud | 🆓 Free (10K/day) | Reliable fallback |
| 10 | **Together** | Cloud | 💳 Free ($25 credit) | YLlama models |
| 11 | **Cohere** | Cloud | 💳 Paid | RAG reranking |
| 12 | **HuggingFace** | Cloud | 🆓 Free tier | Last free fallback |
| 13 | **OpenAI** | Cloud | 💳 Paid | Ultimate fallback |

### Smart Task Routing

| Task Type | Priority Order |
|-----------|---------------|
| `fast` | Groq → DeepSeek → Fireworks → Ollama → Cloudflare → OpenRouter |
| `code` | Ollama → DeepSeek → Anthropic → OpenRouter → Groq → Together |
| `long` | Gemini → OpenRouter → Anthropic → Ollama |
| `cheap` | Ollama → DeepSeek → Cloudflare → HuggingFace → Groq |
| `creative` | Anthropic → OpenRouter → Mistral → Ollama → Gemini |
| `private` | Ollama → Mistral → Cohere |
| `default` | All 13 in priority order |

### Setup

Copy `.env.example` to `.env` and add your keys:

```bash
cp .env.example .env
```

> 🔑 **No API keys are required.** Ollama runs locally. All cloud providers are optional fallbacks.

---

## 💼 Workspace + RAG

### Clone a Website

```bash
curl -X POST http://localhost:8000/api/v2/workspace/clone \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "extract_components": true}'
```

Downloads the full rendered HTML (via Playwright), detects UI components (navbar, hero, cards, footer), and saves to `workspace/cloned_templates/`.

### Generate an App from an Idea

```bash
curl -X POST http://localhost:8000/api/v2/workspace/generate \
  -H "Content-Type: application/json" \
  -d '{"idea": "Todo list application", "tech_stack": "html-css-js"}'
```

Ollama writes a complete, working app saved to `workspace/generated_apps/`.

### RAG Synthesis

```bash
curl -X POST http://localhost:8000/api/v2/workspace/synthesize \
  -H "Content-Type: application/json" \
  -d '{"user_command": "Create a dark-themed dashboard", "target_project": "my-dashboard"}'
```

ChromaDB finds the most relevant templates semantically, then LLM synthesizes a new app from them.

### Workspace Structure

```
workspace/
├── cloned_templates/
│   └── example.com_20260412/
│       ├── index.html
│       ├── raw.html
│       ├── metadata.json          ← components, summary, URL
│       └── assets/
├── generated_apps/
│   └── project_20260412/
│       ├── index.html
│       └── generation_log.json
└── workspace_index.db             ← SQLite manifest
```

---

## 🧠 Memory System

### 3-Layer Unified Architecture

| Layer | Storage | Capacity | Purpose |
|-------|---------|----------|---------|
| **Working Memory** | In-memory (deque) | 20 messages / 4000 tokens | Active conversation context |
| **Long-Term Memory** | SQLite + FTS5 + ChromaDB | Unlimited | Episodic + semantic recall with hybrid search (RRF fusion) |
| **Procedural Memory** | SQLite | Unlimited | Learned strategies & patterns from successful task completions |

**Key features:**
- 🔥 **Decay**: Old/unimportant memories fade (`importance *= exp(-days / 90)`)
- 🌙 **Nightly Consolidation**: Auto-runs at 03:00 — clusters similar episodes, merges, cleans up
- 🔍 **Hybrid Search**: FTS5 lexical + ChromaDB vector search combined via Reciprocal Rank Fusion
- 📊 **Importance Scoring**: Heuristic-based (length, questions, keywords, dates) — only important memories persist

---

## 🔌 API Reference

### Core Endpoints

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/` | `GET` | — | API info |
| `/health` | `GET` | 60/min | Health check — status + uptime |
| `/docs` | `GET` | — | Interactive Swagger UI |
| `/status` | `GET` | — | System, agents & providers status |

### AI Provider Endpoints

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `POST /api/v2/chat` | `POST` | 30/min | Multi-provider chat with smart routing |
| `GET /api/v2/providers/status` | `GET` | — | All providers availability + latency |

### Workspace Endpoints

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `POST /api/v2/workspace/clone` | `POST` | 5/min | Clone a website URL |
| `POST /api/v2/workspace/generate` | `POST` | 10/min | Generate app from idea |
| `POST /api/v2/workspace/synthesize` | `POST` | 10/min | RAG synthesis from templates |
| `GET /api/v2/workspace/list` | `GET` | — | List all workspace items |
| `GET /api/v2/workspace/search?q=...` | `GET` | — | Semantic search via ChromaDB |

### Example: Multi-Provider Chat

```bash
curl -X POST http://localhost:8000/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Merhaba!"}],
    "task_type": "fast",
    "preferred_provider": "groq"
  }'
```

Response:
```json
{
  "success": true,
  "content": "Merhaba! Size nasıl yardımcı olabilirim?",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "tokens_used": 24,
  "latency_ms": 312
}
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```env
# Email (optional)
ULTRON_EMAIL_USER=your@email.com
ULTRON_EMAIL_PASS=your_app_password

# API Key Protection (optional)
ULTRON_API_KEY=your_secret_key

# Ollama (default: local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b

# Cloud AI Providers (optional fallbacks)
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIzaSyD...
OPENROUTER_API_KEY=sk-or-v1-...
CLOUDFLARE_API_KEY=cfut_...
CLOUDFLARE_ACCOUNT_ID=...
TOGETHER_API_KEY=tgp_v1_...
HF_API_KEY=hf_...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
MISTRAL_API_KEY=...
COHERE_API_KEY=...
FIREWORKS_API_KEY=fw_...

# n8n Integration
N8N_WEBHOOK_BASE_URL=http://localhost:5678
N8N_ENABLED=true
```

> 🔑 **No API keys are required.** All optional providers serve as fallbacks when Ollama is unavailable.

### Agent Configuration (`config/agents.yaml`)

```yaml
agents:
  email:
    check_interval_minutes: 30
    max_emails_summary: 5
  sysmon:
    poll_interval_seconds: 5
    alert_thresholds:
      cpu_percent: 85
      ram_percent: 90
      disk_percent: 95
  meeting:
    whisper_model: "base"
    language: "tr"
  files:
    watch_dirs:
      - "~/Downloads"
      - "~/Desktop"
```

---

## 🎙️ Voice & Language

Ultron supports **voice input and output** with multi-language support:

| Component | English | Turkish |
|-----------|---------|---------|
| **STT (Speech-to-Text)** | Google Web Speech API (en-US) + Whisper fallback | Google Web Speech API (tr-TR) + Whisper fallback |
| **TTS (Text-to-Speech)** | edge-tts `en-US-JennyNeural` | edge-tts `tr-TR-EmelNeural` |
| **VAD (Voice Activity)** | Silero VAD (universal) | Silero VAD (universal) |

### Setup Voice

```bash
# 1. Install voice dependencies
pip install SpeechRecognition openai-whisper torch edge-tts pygame sounddevice silero-vad

# 2. Set language in .env
ULTRON_LANGUAGE=en    # or "tr" for Turkish
```

### Voice Pipeline Flow

```
Microphone → Silero VAD → Google STT → Ollama LLM → edge-tts → Speaker
                            ↓ (fallback)
                        Whisper STT
```

- **Barge-in**: Ultron stops speaking when you start talking
- **Auto-detection**: Language is set via `ULTRON_LANGUAGE` in `.env`
- **Offline option**: Whisper STT works entirely offline

---

## 🛠️ Development

### Run Tests

```bash
pytest tests/ -v --cov=ultron
```

### Project Structure

```
Ultron/
├── config/                         # YAML configurations
├── ultron/
│   ├── api/                        # FastAPI backend
│   │   ├── main.py                 # App entry + 19 routes
│   │   └── routes/                 # chat, agents, status
│   ├── v2/                         # Core v2 system
│   │   ├── core/                   # Orchestrator, LLM router, Hermes TAO
│   │   ├── agents/                 # 8 specialized agents
│   │   ├── memory/                 # 3-layer unified memory
│   │   ├── providers/              # 13 AI providers + router + fallback
│   │   └── workspace/              # Playwright clone, code gen, RAG
│   └── actions/                    # Local tools
├── ultron-desktop/                 # React + Vite GUI
│   ├── src/
│   │   ├── App.tsx                 # 3-panel layout
│   │   ├── components/
│   │   │   ├── InspectorPanel.tsx  # 5-tab inspector
│   │   │   ├── WorkspacePanel.tsx  # Clone/Generate/Synthesize
│   │   │   └── Sidebar.tsx         # Agent status + panel switch
│   │   └── hooks/useUltron.ts      # WebSocket streaming
│   └── package.json
├── workspace/                      # Generated/cloned projects
├── data/                           # Memory, ChromaDB, meetings
├── tests/                          # Pytest test suite
├── pyproject.toml                  # Project metadata + deps
└── start-ultron-desktop.bat        # One-click launcher
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **LLM** | Ollama, LangChain, tiktoken |
| **Providers** | 13 providers with smart routing + auto-fallback |
| **Memory** | ChromaDB, SQLite + FTS5, sentence-transformers |
| **Workspace** | Playwright, ChromaDB, CodeGenerator, RAG Synthesizer |
| **Agents** | Custom multi-agent framework with event bus + blackboard |
| **RPA** | pyautogui, mss, EasyOCR, OpenCV |
| **Voice** | Whisper, SpeechRecognition, edge-tts |
| **Frontend** | React 18, TypeScript, Vite 5, Tailwind CSS, Framer Motion |
| **Desktop** | Tauri |

---

## 🤝 Qwen ↔ Gemini Collaboration

Ultron artık **çift yönlü AI işbirliği** destekliyor! Yerel Qwen LLM'iniz ile bulut Gemini arasında otonom iletişim kurun.

### ✨ Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🧠 **Mimari Danışmanlık** | Qwen çıkmaza girdiğinde Gemini'ye danışır |
| 🐛 **Debug Asistanı** | İnatçı bug'larda Gemini root cause analizi yapar |
| 💻 **Kod Önerisi** | Gemini kod yazar, Qwen otomatik uygular |
| 🔄 **Otomatik İş Akışı** | Qwen → Gemini → Qwen döngüsü |

### 🚀 Hızlı Başlangıç

```bash
# 1. API Key ekle (.env dosyasına)
OPENROUTER_API_KEY=sk-or-v1-...

# 2. Test suite çalıştır
python scripts/test_qwen_gemini_collab.py

# 3. Kullanım (Python kodunda)
from ultron.actions.ask_architect import run, ask_and_apply

# Danışmanlık modu
result = run({
    "question": "Microservice mi monolith mi?",
    "mode": "consult"
})

# Otomatik kod uygulama
result = ask_and_apply(
    question="Bu fonksiyonu async yap",
    file_path="ultron/v2/memory/engine.py"
)
```

### 📖 Detaylı Kılavuz

Bkz: [docs/QWEN_GEMINI_COLLAB.md](docs/QWEN_GEMINI_COLLAB.md)

### 💰 Maliyet

- **Ücretsiz**: `google/gemini-2.0-flash-exp:free` (OpenRouter free tier)
- **Ucuz**: `google/gemini-2.5-flash` (~$0.10/1M token)
- **Ortalama**: ~$0.0001-0.0003/sorgu

### 🔧 Kullanım Senaryoları

```
Workflow 1: Feature Development
User Request → Qwen Analiz → Gemini Mimari Onay → Qwen Implement → Test

Workflow 2: Bug Fix
Bug Report → Qwen Debug → Gemini Root Cause → Qwen Fix → Test

Workflow 3: Code Review
Qwen Code Review → Gemini Best Practices → Qwen Refactor → Lint
```

---

## 📜 License

[MIT License](LICENSE) — Copyright (c) 2025–2026 WexyS

Free to use, modify, and distribute. No warranty.

---

<div align="center">

**Built with ❤️ and local compute. 13 AI providers, 8 agents, infinite possibilities.**

</div>
