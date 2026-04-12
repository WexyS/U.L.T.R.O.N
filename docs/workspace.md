# Workspace + RAG Guide

## Overview

Workspace lets you clone websites, generate apps from ideas, and synthesize new apps using RAG.

## Features

### 1. Clone Websites
Uses Playwright to fully render and clone websites including JS-rendered content.

```bash
curl -X POST http://localhost:8000/api/v2/workspace/clone \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**What it does:**
1. Opens URL in headless Chromium
2. Waits for network idle + JS execution
3. Extracts clean HTML (removes trackers)
4. Detects UI components (navbar, hero, cards, etc.)
5. Generates summary via Ollama
6. Saves to `workspace/cloned_templates/`

### 2. Generate Apps from Ideas
Uses Ollama to write complete apps from natural language descriptions.

```bash
curl -X POST http://localhost:8000/api/v2/workspace/generate \
  -H "Content-Type: application/json" \
  -d '{"idea": "Todo app with dark theme"}'
```

**Tech stacks supported:**
- `html-css-js` (default) — single HTML file
- `react` — React app structure
- `vue` — Vue app structure
- `fastapi` — Python backend

### 3. RAG Synthesis
Finds relevant templates via ChromaDB, synthesizes new app.

```bash
curl -X POST http://localhost:8000/api/v2/workspace/synthesize \
  -H "Content-Type: application/json" \
  -d '{"user_command": "Dark dashboard with charts", "target_project": "my-dash"}'
```

## n8n Integration

3 webhook workflows ready to import:
1. **Clone Trigger** — Webhook → Jarvis Clone API
2. **Generate Trigger** — Webhook → Jarvis Generate API
3. **Synthesize Trigger** — Webhook → Jarvis Synthesize API

Enable in `.env`:
```
N8N_WEBHOOK_BASE_URL=http://localhost:5678
N8N_ENABLED=true
```

## Memory Safety

- Max 2 parallel clones (Semaphore)
- HTML truncated at 5MB for processing
- Templates limited to 6KB each for RAG
- `gc.collect()` after embeddings
