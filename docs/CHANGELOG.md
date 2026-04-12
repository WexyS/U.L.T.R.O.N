# Changelog

All notable changes to J.A.R.V.I.S.

## [2.1.0] — 2026-04-12

### Added
- **13 AI Providers**: Ollama, Groq, DeepSeek, Anthropic, OpenRouter, Gemini, Mistral, Fireworks, Cloudflare, Together, Cohere, HuggingFace, OpenAI
- **Smart Provider Routing**: Task-type aware (fast/code/long/cheap/creative/private) with automatic fallback chain
- **Workspace + RAG System**: Clone websites, generate apps from ideas, synthesize from templates
- **Playwright Agent**: Full website cloning with JS rendering, component detection, content sanitization
- **Code Generator**: Ollama-powered app generation from natural language ideas
- **RAG Synthesizer**: ChromaDB semantic search + LLM synthesis from existing templates
- **3-Panel GUI**: Sidebar (240px), Chat/Workspace (flexible), Inspector (300px)
- **Framer Motion Animations**: Smooth transitions, modal animations, streaming effects
- **Workspace Panel**: 3 action modals (Clone, Generate, Synthesize) with progress indicators
- **Inspector Panel**: 5 tabs (Memory, Workspace, Agents, Logs, System)
- **n8n Integration**: 3 ready-to-import webhook workflows
- **New Providers**: Anthropic (Claude), DeepSeek, Mistral, Cohere, Fireworks

### Changed
- Provider router with 5-minute cooldown for failed providers
- Workspace manager with SQLite manifest + ChromaDB embeddings
- GUI color palette: cyan (#00d4ff), purple (#7c3aed), green (#10b981)
- Tailwind theme with glassmorphism effects
- README updated with full architecture, provider list, API reference

### Fixed
- `sentence_transformers` import error on startup
- Workspace API endpoints with proper Pydantic model imports
- Provider lazy loading — only configured providers initialized

---

## [2.0.0] — Previous Release

- Multi-agent architecture (8 agents)
- 3-layer memory system
- LLM router with 7 providers
- React GUI
- RPA capabilities
