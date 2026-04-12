# J.A.R.V.I.S v2.1 — User Guide

Personal, locally-hosted multi-agent AI assistant. FastAPI + React GUI + 13 AI providers.

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for GUI)
- Ollama (local LLM runtime)

### Steps

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Install Playwright Chromium (for workspace cloning)
playwright install chromium

# 4. Download Ollama model
ollama pull qwen2.5:14b

# 5. Create .env file
cp .env.example .env
# Edit .env with your API keys (optional)

# 6. Start backend
python -m uvicorn jarvis.api.main:app --host 127.0.0.1 --port 8000

# 7. Start GUI (optional, in another terminal)
cd jarvis-desktop && npm install && npm run dev
```

### Quick Start

```bash
# One-click launch (Windows)
start-jarvis-desktop.bat
```

---

## Agents and Commands

### Available Agents

| Agent | Description | Example Commands |
|-------|-------------|------------------|
| **CoderAgent** | Code writing, debugging, execution | "Write fibonacci in Python" |
| **ResearcherAgent** | Web research, synthesis | "What is quantum computing?" |
| **RPAOperatorAgent** | Computer control (screen, OCR, input) | "Open Chrome" |
| **EmailAgent** | Email reading, summarization, sending | "Summarize my emails" |
| **SystemMonitorAgent** | CPU/RAM/disk monitoring | "What's the system status?" |
| **ClipboardAgent** | Clipboard content analysis | "Analyze the code in clipboard" |
| **MeetingAgent** | Meeting recording and transcription | "Start recording meeting" |
| **FileOrganizerAgent** | File organization, duplicate detection | "Organize my desktop" |

### Email Agent
```
"read my emails"           → List last 10 emails
"morning briefing"         → Summarize top 5 important emails
"write this to ahmet"      → Draft email
"send"                    → Send the draft
```

### Meeting Agent
```
"start recording"          → Start microphone recording
"stop meeting"            → Stop recording and transcribe
"summarize"               → Generate summary + action items
```

### File Organizer
```
"organize desktop"        → Categorize desktop files
"find duplicates"         → Detect duplicate files
"organize downloads"      → Sort the Downloads folder
```

---

## Memory System

Jarvis uses a 3-layer unified memory architecture:

### 1. Working Memory (Short-Term)
- Holds last 20 messages (deque)
- Token limit: 4000 tokens
- Auto-summarizes when exceeded

### 2. Long-Term Memory
- **SQLite + FTS5**: Full-text lexical search
- **ChromaDB**: Vector-based semantic search
- **Hybrid search**: Combined via Reciprocal Rank Fusion (RRF)
- **Decay**: Unimportant memories older than 90 days fade away
- **Consolidation**: Auto-consolidation at 03:00 nightly

### 3. Procedural Memory (Strategies)
- Successful task completion patterns
- Exponential moving average success rates
- Recommends best strategy for similar tasks

---

## Configuration

### config/agents.yaml
Each agent's settings are defined here:

```yaml
agents:
  email:
    check_interval_minutes: 30
    max_emails_summary: 5
  sysmon:
    poll_interval_seconds: 5
    alert_thresholds:
      cpu_percent: 85
  meeting:
    whisper_model: "base"
    language: "en"
```

### .env Variables
```
JARVIS_EMAIL_USER=your@email.com
JARVIS_EMAIL_PASS=your_app_password
JARVIS_API_KEY=optional_api_key     # For API protection
OLLAMA_BASE_URL=http://localhost:11434
```

### Optional API Keys
All supported LLM providers are listed in `.env.example`.
None are required — Ollama is the default and only mandatory provider.

---

## AI Providers

Jarvis supports **13 AI providers** with smart routing and automatic fallback:

| # | Provider | Type | Cost |
|---|----------|------|------|
| 1 | Ollama | Local | Free |
| 2 | Groq | Cloud | Free |
| 3 | DeepSeek | Cloud | ~$0.14/M tokens |
| 4 | Anthropic | Cloud | Paid |
| 5 | OpenRouter | Cloud | Free + Paid |
| 6 | Gemini | Cloud | Free |
| 7 | Mistral | Cloud | Paid |
| 8 | Fireworks | Cloud | Paid |
| 9 | Cloudflare | Cloud | Free (10K/day) |
| 10 | Together | Cloud | Free ($25 credit) |
| 11 | Cohere | Cloud | Paid |
| 12 | HuggingFace | Cloud | Free tier |
| 13 | OpenAI | Cloud | Paid |

Providers are selected automatically based on task type (fast, code, long, cheap, creative, private) with fallback chain if any provider fails.

---

## Workspace + RAG

Clone websites, generate apps from ideas, synthesize from templates.

### Clone a Website
```bash
curl -X POST http://localhost:8000/api/v2/workspace/clone \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Generate an App
```bash
curl -X POST http://localhost:8000/api/v2/workspace/generate \
  -H "Content-Type: application/json" \
  -d '{"idea": "Todo app with dark theme"}'
```

### RAG Synthesis
```bash
curl -X POST http://localhost:8000/api/v2/workspace/synthesize \
  -H "Content-Type: application/json" \
  -d '{"user_command": "Dark dashboard with charts", "target_project": "my-dash"}'
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/` | GET | API info |
| `/chat` | POST | Chat endpoint |
| `/api/v2/chat` | POST | Multi-provider chat with routing |
| `/api/v2/providers/status` | GET | Provider availability |
| `/agents` | GET | Agent list |
| `/status` | GET | System status |
| `/api/v2/workspace/*` | Various | Workspace operations |

### Rate Limiting
- `/health`: 60 requests/minute
- `/api/v2/chat`: 30 requests/minute
- `/api/v2/workspace/clone`: 5 requests/minute
- Returns `429 Too Many Requests` when exceeded

### API Key Protection (Optional)
If `JARVIS_API_KEY` is set in `.env`:
```
X-API-Key: your_secret_key
```
header is required for all requests.

---

## Running Tests

```bash
pytest tests/ -v --cov=jarvis
```

---

## License

MIT License — Copyright (c) 2025-2026 WexyS
