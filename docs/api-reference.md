# API Reference

Base URL: `http://127.0.0.1:8000`

## Core

### `GET /health`
Health check. Returns status and uptime.

**Response:**
```json
{"status": "ok", "version": "2.1.0", "uptime_seconds": 123.4}
```

### `GET /status`
System status — agents, providers, memory, uptime.

### `GET /`
API info with link to `/docs`.

---

## AI Providers

### `POST /api/v2/chat`
Multi-provider chat with smart routing.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Merhaba!"}
  ],
  "task_type": "fast",
  "preferred_provider": "groq",
  "model": null,
  "stream": false
}
```

**Response:**
```json
{
  "success": true,
  "content": "Merhaba! Nasıl yardımcı olabilirim?",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "tokens_used": 24,
  "latency_ms": 312
}
```

**Task Types:**
| Type | Use Case |
|------|----------|
| `fast` | Quick answers, short responses |
| `code` | Code generation, debugging |
| `long` | Document analysis, long context |
| `cheap` | Cost-sensitive batch tasks |
| `creative` | Writing, brainstorming |
| `private` | Privacy-sensitive (local-first) |
| `default` | General purpose |

### `GET /api/v2/providers/status`
Returns all provider availability and latency.

---

## Workspace

### `POST /api/v2/workspace/clone`
Clone a website via Playwright.

**Request:**
```json
{"url": "https://example.com", "site_name": "example", "extract_components": true}
```

### `POST /api/v2/workspace/generate`
Generate an app from an idea.

**Request:**
```json
{"idea": "Todo app", "project_name": "my-todo", "tech_stack": "html-css-js", "use_template": null}
```

### `POST /api/v2/workspace/synthesize`
RAG synthesis from existing templates.

**Request:**
```json
{"user_command": "Dark dashboard", "target_project": "my-dash", "source_templates": null}
```

### `GET /api/v2/workspace/list`
List all workspace items.

### `GET /api/v2/workspace/search?q=...&top_k=5`
Semantic search via ChromaDB.

---

## WebSocket

### `WS /ws/chat`
Real-time streaming chat.

Send:
```json
{"message": "Hello", "agent": null}
```

Receive (streaming tokens):
```json
{"type": "token", "content": "Hello"}
{"type": "token", "content": " there"}
{"type": "done"}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/health` | 60/min |
| `/api/v2/chat` | 30/min |
| `/api/v2/workspace/clone` | 5/min |
| `/api/v2/workspace/generate` | 10/min |
| `/api/v2/workspace/synthesize` | 10/min |
