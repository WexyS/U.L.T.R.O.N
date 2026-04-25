# AGENTS.md

This document provides essential context and commands for AI agents working in the `Ultron` repository.
The goal is to enable efficient and mistake-free development by highlighting non-obvious facts and common pitfalls.

## Repository Overview

Ultron is an advanced, autonomous, locally-hosted, multi-agent AI assistant system.
It features a FastAPI backend, a React/Vite frontend, and integrates with numerous AI providers and specialized agents.

**Monorepo Structure:**
- **`Ultron/` (root):** Main project, containing the FastAPI backend (`ultron/`), React frontend (`ultron-desktop/`), and shared configurations/scripts.
- **`Ultron Factory/`:** A separate Python project for fine-tuning large language models. It has its own build, test, and run commands.
- **`autonomous-skills/` & `advanced-workflows/`:** These directories contain specialized agent skills and advanced meta-methodologies. They are core skill providers for Ultron agents.

## Core Development Commands (Ultron Project)

### Setup & Launch
- **Windows One-Command Launch:**
  ```bash
  start-ultron-desktop.bat
  ```
  (This script handles virtual environment activation, backend, and frontend launch.)
- **Manual Setup (Cross-Platform):**
  1.  **Clone:** `git clone https://github.com/WexyS/Ultron.git && cd Ultron`
  2.  **Virtual Env:** `python -m venv .venv` (then activate)
  3.  **Install Python Deps:** `pip install -e ".[dev]"`
  4.  **Install Playwright:** `playwright install chromium`
  5.  **Install & Run Ollama (Optional):** `ollama pull qwen2.5:14b && ollama serve`
  6.  **Start Backend (in one terminal):** `python -m uvicorn ultron.api.main:app --host 127.0.0.1 --port 8000`
  7.  **Start Frontend (in another terminal):`cd ultron-desktop && npm install && npm run dev`**

### Testing
- **Backend Tests:** `python test_system.py`
- **Frontend Build (compiles frontend, checks TypeScript):**
  ```bash
  cd ultron-desktop
  npm run build
  ```
- **AI Provider Connectivity Test:** `python test_providers.py`

## Architecture Notes (Ultron Project)

- **Backend (`ultron/`):** FastAPI based. Main entry: `ultron.api.main:app`.
- **Frontend (`ultron-desktop/`):** React/TypeScript/Vite.
- **Agents (`ultron/v2/agents/`)**: 11 specialized agents. Task routing is now handled by the **ReActOrchestrator (v3.0)**.
- **ReActOrchestrator (v3.0)**: The central AGI brain. Uses Reason+Act loops, Chain-of-Thought (CoT), and real-time reflection to coordinate agents.
- **Emotional Intelligence (EQ)**: A dedicated sentiment analysis layer that adapts responses based on user mood (CHILL, STRESSED, etc.).
- **Memory (`ultron/v2/memory/`)**: 3-layer system (Working, Long-Term, Procedural) + **UserProfileManager** for persistent relationship tracking.
- **Event Bus (`ultron/v2/core/event_bus.py`)**: Unified bridge for cross-agent communication and frontend real-time updates.
- **MCP Tool Bridge (`ultron/v2/mcp/bridge.py`)**: Enables dynamic tool injection. Use `ULTRON_MCP_ALLOWED_SERVERS` and `ultron/v2/core/security.py` for path/server allowlists.
- **AI Providers**: Configured via `.env`. Smart routing for `fast`, `code`, `long`, `cheap` task types. Ollama is default local LLM.
- **Configuration**: `.env` for API keys and URLs; `config/agents.yaml` for agent-specific settings.

## Ultron Factory Project Guidelines

This is a separate Python project within the monorepo for LLM fine-tuning.

### Commands (from `Ultron Factory/` directory)
- **Code Style (auto-fix):** `make style`
- **Code Quality Check:** `make quality`
- **Run All Tests:** `make test` (Note: most training tests require GPU hardware)
- **Run Single Test File:** `WANDB_DISABLED=true pytest -vv --import-mode=importlib tests/path/to/test_file.py`
- **Build Package:** `make build`
- **Quickstart Training/Inference/Export:**
  ```bash
  Ultron Factory-cli train examples/train_lora/qwen3_lora_sft.yaml
  Ultron Factory-cli chat examples/inference/qwen3_lora_sft.yaml
  Ultron Factory-cli export examples/merge_lora/qwen3_lora_sft.yaml
  ```
- **Launch Web UI:** `Ultron Factory-cli webui`

### Architecture (Ultron Factory)
- **Versions:** `v0` (default) and `v1` (experimental, in `src/Ultron Factory/v1/`). Most development is in `v0`.
- **CLI Entry:** `Ultron Factory-cli` or `lmf` (`src/Ultron Factory/cli.py:main()`).
- **Configuration:** All training parameters are set via YAML/JSON config files.
- **Code Style:** Uses Ruff (line length 119, Google-style docstrings), Python 3.11+, double quotes, Apache 2.0 license headers.
- **Testing:** `WANDB_DISABLED=true` should always be set when running tests.

## General Agent Guidelines for this Repository

- **File Paths:** Always use absolute paths for file operations (`read`, `write`, `edit`).
- **Autonomous & Advanced Skill Repos:** The `advanced-workflows/` and `autonomous-skills/` directories are essential skill providers for the Genesis engine.
- **Environment Variables:** Use `.env` file (copy `.env.example`) to configure API keys, URLs, and other settings.
- **Python Virtual Environment:** Always activate `.venv` before running Python commands.
