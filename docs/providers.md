# 13 AI Providers Guide

## Provider Priority Order

| # | Provider | Priority | Type | Cost | Best For |
|---|----------|----------|------|------|----------|
| 1 | Ollama | 1 | Local | Free | Privacy, code gen |
| 2 | Groq | 2 | Cloud | Free | Speed (500 tok/s) |
| 3 | DeepSeek | 2 | Cloud | $0.14/M tok | Code, reasoning |
| 4 | Anthropic | 2 | Cloud | Paid | Understanding |
| 5 | OpenRouter | 3 | Cloud | Free+Paid | 200+ models |
| 6 | Gemini | 3 | Cloud | Free | 1M context |
| 7 | Mistral | 3 | Cloud | Paid | GDPR |
| 8 | Fireworks | 3 | Cloud | Paid | Speed |
| 9 | Cloudflare | 4 | Cloud | Free 10K/day | Fallback |
| 10 | Together | 5 | Cloud | Free $25 | Llama models |
| 11 | Cohere | 4 | Cloud | Paid | RAG rerank |
| 12 | HuggingFace | 6 | Cloud | Free tier | Last free |
| 13 | OpenAI | 8 | Cloud | Paid | Last resort |

## Setup

1. Copy `.env.example` to `.env`
2. Add API keys for providers you want
3. Providers without keyss are skipped automatically

## Task Routing

- **fast**: Groq → DeepSeek → Fireworks → Ollama → Cloudflare → OpenRouter
- **code**: Ollama → DeepSeek → Anthropic → OpenRouter → Groq → Together
- **long**: Gemini → OpenRouter → Anthropic → Ollama
- **cheap**: Ollama → DeepSeek → Cloudflare → HuggingFace → Groq
- **creative**: Anthropic → OpenRouter → Mistral → Ollama → Gemini
- **private**: Ollama → Mistral → Cohere

## Fallback Chain

If a provider fails:
1. Mark it as failed with timestamp
2. Try next provider in priority order
3. Failed providers recover after 5 minutes
4. If ALL fail → raise RuntimeError

## Health Check

Each provider checks:
- `is_configured()`: API key present in .env
- `is_available()`: API responds to health check

## Adding New Providers

1. Create file in `jarvis/v2/providers/`
2. Extend `BaseProvider`
3. Add to `router.py` `_load_providers()`
4. Add to `TASK_PRIORITY` dict
5. Add key to `.env.example`
