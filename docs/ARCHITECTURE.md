# J.A.R.V.I.S Architecture

## Overview

Jarvis is a **locally-hosted, multi-agent AI assistant** with 13 AI providers, workspace RAG system, and a modern 3-panel GUI.

## System Diagram

```
User
  │
  ├─► GUI (React + Framer Motion) ──► FastAPI (19 routes)
  │                                    │
  │                                    ├─► Orchestrator (8 agents)
  │                                    ├─► ProviderRouter (13 providers)
  │                                    ├─► MemoryEngine (3 layers)
  │                                    ├─► WorkspaceManager (clone/generate/synthesize)
  │                                    └─► n8n webhooks (3 workflows)
```

## Provider Routing

13 providers routed by **task type** with automatic fallback:

```
default: ollama → groq → deepseek → anthropic → openrouter → gemini →
         mistral → fireworks → cloudflare → together → cohere → hf → openai
```

Each provider checks health before use. Failed providers get a 5-minute cooldown before retry.

## Workspace + RAG

1. **Clone**: Playwright → headless Chromium → render JS → extract components → save
2. **Generate**: Ollama prompt → parse code → save to `workspace/generated_apps/`
3. **Synthesize**: ChromaDB search → load top-3 templates → LLM synthesis → save

All items tracked in `workspace/workspace_index.db` (SQLite) + ChromaDB embeddings.

## Memory System

3 layers unified:
- **Working**: deque, 20 messages, ~4000 tokens
- **Long-Term**: SQLite (FTS5) + ChromaDB (vector), hybrid RRF search
- **Procedural**: SQLite, learned strategies from successful tasks

## Data Flow

```
User message → WebSocket → Orchestrator → Intent classification
  → Route to agent(s) → Execute → Stream response → Store in memory
  → Update workspace (if applicable) → Return to GUI
```

## Security

- CORS scoped to `localhost:5173` only
- Optional API key (`X-API-Key` header)
- Rate limiting via slowapi
- Playwright runs in headless mode with content sanitization
