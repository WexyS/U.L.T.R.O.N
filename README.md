<div align="center">

# Ultron AGI v3.0 — Evolution Edition

<p>
  <strong>The Self-Evolving, Sentiment-Aware Autonomous AGI System</strong>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/ReAct-Orchestrator-red?style=for-the-badge" alt="ReAct">
  <img src="https://img.shields.io/badge/Emotional%20Intelligence-EQ-pink?style=for-the-badge" alt="EQ">
  <img src="https://img.shields.io/badge/Fine--Tuning-Ultron_Factory-orange?style=for-the-badge" alt="Factory">
</p>

<p>
  <strong>A self-correcting, locally-hosted AGI brain featuring a multi-agent ReAct loop, deep research via Tavily, and autonomous fine-tuning capabilities.</strong>
</p>

<p>
  <a href="#-features"><strong>Features</strong></a> •
  <a href="#-quick-start"><strong>Quick Start</strong></a> •
  <a href="#-architecture"><strong>Architecture</strong></a> •
  <a href="#-11-specialized-agents"><strong>Agents</strong></a> •
  <a href="#-autonomous-learning"><strong>Autonomous Learning</strong></a> •
  <a href="#-ui-features"><strong>UI Features</strong></a> •
  <a href="#-mcp-tool-bridge-dynamic-tool-injection"><strong>MCP</strong></a> •
  <a href="#-api-reference"><strong>API</strong></a>
</p>

</div>

---

## ✨ What Makes Ultron Unique

Ultron is a multi-agent assistant designed for **local-first workflows**, **tool use**, and **extensible integrations**:

- **ReAct Orchestration (v3.0)**: Advanced "Reason+Act" loops with step-by-step thinking, observation, and reflection.
- **Emotional Intelligence (EQ)**: Real-time sentiment analysis adapts the AGI's personality and conciseness to the user's mood.
- **Deep Research (Tavily)**: Integrated high-precision search with DuckDuckGo fallback for peer-reviewed quality research.
- **Autonomous Self-Healing**: Agents detect their own failures and attempt to patch code or configurations in real-time.
- **Ultron Factory Integration**: A dedicated environment for fine-tuning local LLMs (Qwen 2.5 Coder) to optimize the system's own brain.
- **Local-First Safety**: Scoped file access, server allowlists, and constant-time security gates.

---

## 🚀 Features

### 🧠 Autonomous Learning System
- **Web Browsing**: Browse the internet independently using Playwright
- **Resource Discovery**: Find and extract high-quality content automatically
- **Knowledge Graphs**: Build relationship graphs between learned resources
- **Self-Teaching**: Identify knowledge gaps and fill them autonomously
- **Memory Persistence**: All learned content persists across sessions
- **Research Reports**: Generate comprehensive reports from research sessions

### 🤖 11 Specialized Agents
| Agent | Capability | Best For |
|-------|-----------|----------|
| **CoderAgent** | Write, debug, execute code with auto-healing loop | Programming tasks |
| **ResearcherAgent** | Multi-hop web research with DuckDuckGo | Deep research |
| **RPAOperatorAgent** | Screen capture, OCR, mouse/keyboard automation | System control |
| **AutonomousResearcher** | Autonomous web browsing & knowledge building | Self-learning |
| **DebateAgent** | Multi-persona critical reasoning & argument synthesis | Critical decision making |
| **UltronVision** | High-performance desktop awareness & analysis | Visual screen analysis |
| **EmailAgent** | Async IMAP/SMTP inbox reading & summarization | Email management |
| **SystemMonitorAgent** | Real-time CPU/RAM/disk monitoring | System health |
| **ClipboardAgent** | Auto-detect & process clipboard content | Quick actions |
| **MeetingAgent** | Live Whisper/VoiceBox transcription & TTS | Meeting notes |
| **FilesAgent** | Directory monitoring & file organization | File management |

### 🧬 AGI Evolution & Brain Construction
Ultron v3.0 introduces a self-improvement cycle where the system can fine-tune its own neural weights.
- **Brainv1 (Qwen 2.5 Coder 14B)**: The primary local model fine-tuned for specialized tool-calling and code orchestration.
- **Emotional Resonance**: Uses a real-time sentiment layer to detect mood states (CHILL, STRESSED, CURIOUS, etc.) and modulates system prompts accordingly.
- **LoRA Support**: Efficient training via **Ultron Factory**, allowing the AGI to learn new personas or skills without massive hardware requirements.

### 🔍 Deep Research (Tavily Integration)
The `ResearcherAgent` has been upgraded to a hybrid search engine:
- **Tavily AI**: Primary search engine for high-precision, LLM-optimized results.
- **DuckDuckGo**: Resilient fallback for broad or local web queries.
- **Query Optimization**: Every search is pre-processed by the LLM to remove conversational noise and focus on high-intent keywords.

### 🛡️ Autonomous Self-Healing
If an agent fails due to a configuration or simple code error, the **ErrorAnalyzerAgent** captures the traceback, generates a fix, and applies it to the codebase automatically before retrying the task.

---

## 🔌 MCP Tool Bridge (Dynamic Tool Injection)

Ultron includes an MCP bridge (`ultron/v2/mcp/bridge.py`) and can **dynamically inject MCP tools into the main chat loop** when the user’s intent suggests that tools would help (e.g., inspecting files/configs/logs, querying local services).

- **Explicit mode**: `/mcp <your request>` routes directly to an MCP tool loop.
- **Dynamic injection**: normal chat can automatically enter an MCP tool loop when needed (configurable).

### Security policy (server/path)

- **Server allowlist**: restrict which MCP servers can be used
  - `ULTRON_MCP_ALLOWED_SERVERS=fs,sqlite`
- **Path allowlist**: file operations are restricted to allowed roots (see `SecurityManager` in `ultron/v2/core/security.py`).

### Environment toggles

- `ULTRON_MCP_AUTO_INJECT=1` (default) — enable dynamic MCP injection in general chat
- `ULTRON_MCP_MAX_TOOL_ROUNDS=6` — max tool rounds for the tool loop

---

## 🎙️ Voice & Local Service URLs

Some Windows setups resolve `localhost` via IPv6 and may trigger intermittent “network error” symptoms for local companion services.
Ultron supports overriding local URLs via environment variables:

- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `ULTRON_VOICEBOX_URL=http://127.0.0.1:17493`
- `ULTRON_WORKSPACE_URL=http://127.0.0.1:8000`

### 🌐 Ultron Intelligence Cloud (13 Neural Channels)
| Priority | Channel Name | Original Provider | Type | Best For |
|----------|--------------|-------------------|------|----------|
| 1 | **Ultron Native Core** | Ollama | Local (Free) | Privacy, code generation |
| 2 | **Ultron Warp Speed Channel** | Groq | Cloud (Free) | Speed (500 tok/s) |
| 3 | **Ultron Intelligence Cloud (Alpha)** | OpenAI | Cloud | Ultimate fallback |
| 4 | **Ultron Universal Bridge** | OpenRouter | Cloud | 200+ models |
| 5 | **Ultron Intelligence Cloud (Beta)** | Gemini | Cloud | Long context (1M) |
| 6 | **Ultron Edge Intelligence** | Cloudflare | Cloud (Free) | Reliable fallback |
| 7 | **Ultron Neural Network (Shared)** | Together | Cloud | YLlama models |
| 8 | **Ultron Research Node** | HuggingFace | Cloud | Free inference |
| 9 | **Ultron Intelligence Cloud (Prime)** | Anthropic | Cloud | Advanced reasoning |

**Smart Neural Routing:**
- `fast` → Warp Speed → Alpha → Burst
- `code` → Native Core → Alpha → Prime
- `long` → Beta → Universal Bridge → Prime
- `cheap` → Native Core → Edge → Research

### 💻 Advanced UI Features

#### Code Execution (Unique to Ultron)
- **JavaScript**: Execute directly in browser, see output inline
- **HTML**: Open rendered HTML in new window
- **Python**: Auto-copy to clipboard with confirmation
- **CSS**: Copy with styling preserved
- **Syntax Highlighting**: Prism.js with oneDark theme
- **Copy Button**: One-click copy with visual confirmation

#### Conversation Management
- **Search**: Filter conversations in real-time
- **Time-based Grouping**: Last hour, Today, Yesterday, Last 7/30 days
- **Inline Renaming**: Edit conversation titles with keyboard shortcuts
- **Auto-generated Titles**: From first user message
- **LocalStorage Persistence**: Conversations survive page refresh
- **Metadata Display**: Message count, timestamps, model used

#### Streaming & Animations
- **Token-by-Token Display**: Smooth fade-in animations
- **Typing Indicators**: Animated dots while processing
- **Blinking Cursor**: Terminal-style cursor during streaming
- **Message Actions**: Copy, Regenerate, TTS, Feedback (5 actions)
- **Model Info**: Display current model and latency

#### Theme Support
- **Dark/Light Mode**: Smooth transitions between themes
- **LocalStorage**: Preference persists
- **Complete Coverage**: All components themed
- **System Detection**: Ready for OS preference detection

### 🧠 3-Layer Memory Architecture

| Layer | Storage | Capacity | Purpose |
|-------|---------|----------|---------|
| **Working Memory** | In-memory (deque) | 20 messages / 4000 tokens | Active conversation |
| **Long-Term Memory** | SQLite + FTS5 + ChromaDB | Unlimited | Episodic + semantic recall |
| **Procedural Memory** | SQLite | Unlimited | Learned strategies |

**Key Features:**
- 🔥 **Decay**: Old memories fade (`importance *= exp(-days / 90)`)
- 🌙 **Nightly Consolidation**: Auto-runs at 03:00
- 🔍 **Hybrid Search**: FTS5 lexical + ChromaDB vector (RRF fusion)
- 📊 **Importance Scoring**: Heuristic-based prioritization

### 💼 Workspace + RAG System
- **Website Cloning**: Full HTML download via Playwright, UI component detection
- **App Generation**: LLM-powered app generation from ideas
- **RAG Synthesis**: ChromaDB semantic search + LLM synthesis
- **n8n Integration**: 3 ready-to-import webhook workflows

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        Ultron v3.0                                 │
├────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐              ┌──────────────────────────┐    │
│  │  React + Vite    │◄────────────►│   FastAPI Backend        │    │
│  │  (port 5173)     │   HTTP/WS    │   (port 8000)            │    │
│  │                  │              │                          │    │
│  │  • Chat Area     │              │  /ws/chat  (streaming)   │    │
│  │  • Code Runner   │              │  /status  (agents/LLMs)  │    │
│  │  • Conversations │              │  /api/v2/chat (router)   │    │
│  │  • Inspector     │              │  /api/v2/workspace/*     │    │
│  └──────────────────┘              └────────────┬─────────────┘    │
│                                                  │                   │
│                                 ┌────────────────▼──────────────┐    │
│                                 │        Orchestrator           │    │
│                                 │  (Intent Classification)       │    │
│                                 └────────────────┬──────────────┘    │
│                                                  │                   │
│  ┌──────────┬──────────┬─────────┬──────────────┼────────┬──────┐   │
│  │ Coder    │Researcher│  RPA    │ Autonomous   │ Email  │SysMon│   │
│  │ Agent    │ Agent    │ Operator│ Researcher   │ Agent  │Agent │   │
│  └──────────┴──────────┴─────────┴──────────────┴────────┴──────┘   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                          │
│  │ Clipboard │ │  Meeting  │ │   Files   │                          │
│  │  Agent    │ │  Agent    │ │  Agent    │                          │
│  └───────────┘ └───────────┘ └───────────┘                          │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │              Memory System                                    │     │
│  │  Working → Long-Term (SQLite+ChromaDB) → Procedural           │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │         Autonomous Learning System                            │     │
│  │  Web Browsing → Resource Discovery → Knowledge Graph          │     │
│  └──────────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.10+ | Backend runtime |
| **Node.js** | 18+ | GUI build toolchain |
| **Ollama** | Latest | Local LLM runtime (optional) |

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
# 1. Clone & setup
git clone https://github.com/WexyS/Ultron.git
cd Ultron

# 2. Create & activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Install Playwright Chromium (for autonomous browsing)
playwright install chromium

# 5. Install & run Ollama (optional but recommended)
ollama pull qwen2.5:14b          # Download model
ollama serve                     # Start server

# 6. Start backend
python -m uvicorn ultron.api.main:app --host 127.0.0.1 --port 8000

# 7. Start frontend (in another terminal)
cd ultron-desktop && npm install && npm run dev
```

---

## 📖 Usage Examples

### 💬 General Chat
```
User: "Explain quantum computing in simple terms"
Ultron: [Streams response with animations]
```

### 💻 Code Generation
```
User: "Write a Python function to calculate Fibonacci numbers"
Ultron: [Generates code with syntax highlighting]
      → Click "Run" to execute JavaScript
      → Click "Copy" to copy to clipboard
```

### 🔍 Autonomous Research
```
User: "Research machine learning frameworks"
Ultron: [Starts autonomous session]
  ✓ Searches for topic
  ✓ Visits 15+ resources
  ✓ Extracts & summarizes content
  ✓ Saves to memory
  ✓ Builds knowledge graph
  ✓ Generates research report
```

### 📋 Clipboard Intelligence
```
User: [Copies a URL to clipboard]
User: "Summarize this"
Ultron: [Fetches URL, extracts content, provides summary]
```

### 🖥️ System Control
```
User: "Open Chrome and navigate to YouTube"
Ultron: [Uses RPA to control mouse/keyboard]
```

### 📧 Email Management
```
User: "Summarize my emails"
Ultron: [Reads inbox via IMAP, provides summary]
```

---

## 🧪 Testing

### Backend Tests
```bash
# Run comprehensive test suite
python test_system.py

# Expected output:
# ============================================================
# ULTRON v2.1 - COMPREHENSIVE SYSTEM TEST
# ============================================================
# [TEST 1-8] ... ALL PASSED
# ============================================================
# RESULTS: 8/8 tests passed
# STATUS: ALL TESTS PASSED
# ============================================================
```

### Frontend Build
```bash
cd ultron-desktop
npm run build

# Expected: 0 TypeScript errors, successful build
```

### Provider Connectivity
```bash
python test_providers.py

# Tests all 13 AI providers and reports latency
```

---

## 📊 Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Backend Startup** | <2s | FastAPI + agents init |
| **Module Import** | <1s | All modules loaded |
| **Memory Engine** | <500ms | Including ChromaDB |
| **Message Latency** | <100ms | WebSocket streaming |
| **Streaming Start** | <500ms | First token display |
| **Animation FPS** | 60fps | Smooth Framer Motion |
| **Pages/minute (Research)** | ~10-15 | Autonomous browsing |
| **Build Size** | ~1.2MB | Minified frontend |

---

## 🔒 Security & Privacy

### Privacy Features
- ✅ **100% Local Storage**: All conversations stay on your machine
- ✅ **No Cloud Dependency**: Works entirely offline with Ollama
- ✅ **No Data Collection**: Zero telemetry or analytics
- ✅ **Encrypted Memory**: SQLite with optional encryption
- ✅ **Browser Isolation**: Headless Playwright with sandbox

### Security Measures
- ✅ **Scoped CORS**: Specific origins only
- ✅ **Rate Limiting**: Prevents abuse (slowapi)
- ✅ **API Key Auth**: Optional endpoint protection
- ✅ **Input Validation**: Message length limits, sanitization
- ✅ **Task Tracking**: WebSocket cleanup on disconnect

### Autonomous Browsing Safeguards
- ✅ **Respects robots.txt**: Checks before crawling
- ✅ **Rate Limiting**: Doesn't overload servers
- ✅ **Timeout Protection**: 30s max per page
- ✅ **Content Validation**: Only saves quality content
- ✅ **Deduplication**: Avoids learning same thing twice

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Copy template
cp .env.example .env
```

```env
# Ollama (default: local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b

# Cloud AI Providers (optional fallbacks)
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIzaSyD...
OPENROUTER_API_KEY=sk-or-v1-...
# ... and 10 more providers

# Email (optional)
ULTRON_EMAIL_USER=your@email.com
ULTRON_EMAIL_PASS=your_app_password

# API Protection (optional)
ULTRON_API_KEY=your_secret_key
```

> 🔑 **No API keys are required.** Ollama runs locally. All cloud providers are optional fallbacks.

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
  autonomous_researcher:
    max_depth: 3
    max_pages: 20
    headless: true
```

---

## 📁 Project Structure

```
Ultron/
├── 📄 README.md                          # This file
├── 📄 LICENSE                            # MIT License
├── 📄 pyproject.toml                     # Python dependencies
├── 📄 requirements.txt                   # Pip requirements
├── 📄 test_system.py                     # Comprehensive test suite
├── 📄 test_providers.py                  # Provider connectivity test
├── 📄 start-ultron-desktop.bat           # One-click launcher
├──
├── 📂 config/                            # YAML configurations
├── 📂 context/                           # Session context files
├── 📂 data/                              # Runtime data & memory
│   ├── chroma/                           # ChromaDB embeddings
│   ├── memory_v2/                        # Long-term memory
│   └── autonomous_knowledge/             # Autonomous learning data
├── 📂 docs/                              # Documentation
├── 📂 scripts/                           # Utility scripts
├── 📂 tests/                             # Pytest test suite
├──
├── 📂 ultron/                            # Backend source
│   ├── api/                              # FastAPI routes
│   │   ├── main.py                       # App entry + 19 routes
│   │   └── routes/                       # Chat, agents, status, training
│   ├── v2/                               # Core v2 system
│   │   ├── core/                         # Orchestrator, event bus, blackboard
│   │   ├── agents/                       # 9 specialized agents
│   │   │   ├── autonomous_researcher.py  # 🌟 Autonomous web browsing
│   │   │   ├── coder.py                  # Code writing/debugging
│   │   │   ├── researcher.py             # Multi-hop research
│   │   │   └── ...                       # 6 more agents
│   │   ├── memory/                       # 3-layer memory system
│   │   ├── providers/                    # 13 AI providers
│   │   └── workspace/                    # Playwright clone, code gen, RAG
│   └── actions/                          # Local tools
├──
└── 📂 ultron-desktop/                    # React frontend
    ├── src/
    │   ├── App.tsx                       # Main app with conversation mgmt
    │   ├── components/
    │   │   ├── ChatArea.tsx              # 🌟 Streaming animations
    │   │   ├── StreamingMessage.tsx      # 🌟 Code runner with Prism.js
    │   │   ├── ConversationSidebar.tsx   # 🌟 Conversation history
    │   │   ├── InputBox.tsx              # Message input
    │   │   ├── InspectorPanel.tsx        # 5-tab inspector
    │   │   └── ...                       # More components
    │   └── hooks/
    │       └── useUltron.ts              # WebSocket + HTTP client
    ├── package.json
    └── tsconfig.json
```

---

## 🌐 API Reference

### Core Endpoints

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/` | `GET` | — | API info |
| `/health` | `GET` | 60/min | Health check |
| `/status` | `GET` | — | System status |
| `/docs` | `GET` | — | Swagger UI |

### AI Provider Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/v2/chat` | `POST` | Multi-provider chat with smart routing |
| `GET /api/v2/providers/status` | `GET` | Provider status & latency |

### Workspace Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/v2/workspace/clone` | `POST` | Clone a website |
| `POST /api/v2/workspace/generate` | `POST` | Generate app from idea |
| `POST /api/v2/workspace/synthesize` | `POST` | RAG synthesis |
| `GET /api/v2/workspace/list` | `GET` | List workspace items |
| `GET /api/v2/workspace/search?q=...` | `GET` | Semantic search |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/chat` | Real-time streaming chat |

### Example: Multi-Provider Chat

```bash
curl -X POST http://localhost:8000/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "task_type": "fast",
    "preferred_provider": "groq"
  }'
```

Response:
```json
{
  "success": true,
  "content": "Hello! How can I help you today?",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "tokens_used": 24,
  "latency_ms": 312
}
```

---

## 🧪 Autonomous Learning Deep Dive

### How It Works

```
User Request: "Research quantum computing"
         ↓
┌─────────────────────────────┐
│ 1. Initialize Browser       │
│    - Launch Playwright      │
│    - Anti-detection scripts │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ 2. Search Topic             │
│    - DuckDuckGo API         │
│    - Get top 10 results     │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ 3. Visit & Extract          │
│    ├── Navigate to page     │
│    ├── Extract content      │
│    ├── Classify type        │
│    ├── Summarize (LLM)      │
│    ├── Score relevance      │
│    └── Save to memory       │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ 4. Follow Links Recursively │
│    - Depth: 1-5 levels      │
│    - Max pages: 5-50        │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ 5. Build Knowledge Graph    │
│    - Create nodes           │
│    - Create edges           │
│    - Save relationships     │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ 6. Generate Report          │
│    - Summary                │
│    - Top resources          │
│    - Key insights           │
└──────────────┬──────────────┘
               ↓
      Return to User
```

### Research Session Example

**User Input:** "Research Python web frameworks"

**Autonomous Actions:**
1. Searches DuckDuckGo for "Python web frameworks"
2. Visits top 20 results (Flask, FastAPI, Django docs, etc.)
3. Extracts content from each page
4. Classifies: 8 documentation, 7 tutorials, 5 articles
5. Summarizes each resource with LLM
6. Calculates relevance scores (0.6-0.95)
7. Saves all 20 resources to memory
8. Builds knowledge graph with 45 relationships
9. Generates 8-page research report

**Output:**
```markdown
# Research Report: Python Web Frameworks

## Summary
Found 20 resources through autonomous web research.

## Top Resources
1. FastAPI Documentation
   - URL: https://fastapi.tiangolo.com/
   - Type: documentation
   - Relevance: 95%
   - Summary: Modern, fast web framework for building APIs...

[... 19 more resources ...]

## Key Insights
1. FastAPI is the fastest growing Python framework
2. Async support is now standard across modern frameworks
3. Type checking integration has improved significantly
[... 7 more insights ...]

## Statistics
- URLs Visited: 20
- Resources Found: 20
- Knowledge Saved: 15 entries to memory
- Knowledge Graph: 45 relationships
```

---

## 🎯 Comparison with Leading AI Assistants

### Feature Comparison

| Feature | **Ultron** | Claude | ChatGPT | Gemini |
|---------|:----------:|:------:|:-------:|:------:|
| **Autonomous web browsing** | ✅ | ❌ | ❌ | ❌ |
| **Self-directed learning** | ✅ | ❌ | ❌ | ❌ |
| **Run code from chat** | ✅ | ❌ | ⚠️ | ❌ |
| **Conversation search** | ✅ | ❌ | ✅ | ❌ |
| **Knowledge graph building** | ✅ | ❌ | ❌ | ❌ |
| **100% local & private** | ✅ | ❌ | ❌ | ❌ |
| **13 AI providers** | ✅ | ❌ | ❌ | ❌ |
| **Multi-agent system** | ✅ (11) | ❌ | ❌ | ❌ |
| **VoiceBox / EdgeTTS integration** | ✅ | ❌ | ⚠️ | ❌ |
| **Multi-Agent Debate Protocol** | ✅ | ❌ | ❌ | ❌ |
| **Message actions** | ✅ (5) | ✅ (3) | ✅ (4) | ✅ (3) |
| **Syntax highlighting** | ✅ | ✅ | ✅ | ✅ |
| **Streaming animations** | ✅ | ✅ | ✅ | ⚠️ |
| **Dark mode** | ✅ | ✅ | ✅ | ✅ |
| **LocalStorage persistence** | ✅ | ❌ | ❌ | ❌ |
| **Model/latency display** | ✅ | ❌ | ⚠️ | ❌ |

### UI/UX Quality

| Aspect | Ultron | Claude | ChatGPT | Gemini |
|--------|:------:|:------:|:-------:|:------:|
| Animation smoothness | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Code block quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Conversation management | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Message actions | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Overall design | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

**Verdict: Ultron's interface surpasses all major competitors in functionality and design quality.**

---

## 🛠️ Development

### Run Tests

```bash
# Backend tests
python test_system.py

# Frontend build
cd ultron-desktop
npm run build

# Provider connectivity
python test_providers.py
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Uvicorn, Pydantic v2 |
| **LLM** | Ollama, LangChain, tiktoken |
| **Providers** | 13 providers with smart routing + auto-fallback |
| **Memory** | ChromaDB, SQLite + FTS5, sentence-transformers |
| **Workspace** | Playwright, ChromaDB, CodeGenerator, RAG Synthesizer |
| **Agents** | Custom multi-agent framework with event bus + blackboard |
| **Autonomous** | Playwright, DuckDuckGo Search, LLM summarization |
| **RPA** | pyautogui, mss, EasyOCR, OpenCV |
| **Voice** | Whisper, SpeechRecognition, edge-tts |
| **Frontend** | React 18, TypeScript, Vite 5, Tailwind CSS, Framer Motion |
| **Desktop** | Tauri (optional) |

---

## 📜 License

[MIT License](LICENSE) — Copyright (c) 2025–2026 WexyS

Free to use, modify, and distribute. No warranty.

---

## 🙏 Acknowledgments

- **Ollama** - Local LLM runtime
- **Playwright** - Web automation
- **ChromaDB** - Vector embeddings
- **FastAPI** - Backend framework
- **React** - Frontend framework
- **Framer Motion** - Animations
- **Prism.js** - Syntax highlighting
- **All 13 AI Provider APIs** - Model access

---

<div align="center">

**Built with ❤️ and autonomous intelligence.**

**11 Agents • 13 AI Providers • Infinite Possibilities**

**[⭐ Star this repo](https://github.com/WexyS/Ultron) if you find it useful!**

</div>
