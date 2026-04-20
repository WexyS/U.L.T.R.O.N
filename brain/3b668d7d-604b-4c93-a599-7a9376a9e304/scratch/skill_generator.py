"""Bulk Skill & Agent Generator for Ultron — generates high-quality SKILL.md files."""
import os
from pathlib import Path

SKILLS_DIR = Path("C:/Users/nemes/.qwen/skills")
AGENTS_DIR = Path("C:/Users/nemes/.qwen/agents")
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
AGENTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── TECHNOLOGY SKILLS ───
TECH_SKILLS = {
    # Docker SDK
    "docker-container-management": {"cat": "DevOps", "desc": "Manage Docker containers: create, start, stop, restart, remove. Use docker SDK for Python.", "triggers": ["docker", "container", "deploy"]},
    "docker-image-builder": {"cat": "DevOps", "desc": "Build Docker images from Dockerfiles programmatically using docker SDK.", "triggers": ["docker build", "image", "dockerfile"]},
    "docker-compose-orchestrator": {"cat": "DevOps", "desc": "Manage multi-container apps with docker-compose via Python SDK.", "triggers": ["compose", "multi-container"]},
    "docker-volume-network": {"cat": "DevOps", "desc": "Create and manage Docker volumes and networks for persistent storage.", "triggers": ["volume", "network", "storage"]},
    # E2B Jupyter
    "e2b-jupyter-sandbox": {"cat": "AI/ML", "desc": "Run Python code in isolated E2B Jupyter sandboxes for safe execution.", "triggers": ["sandbox", "jupyter", "e2b", "safe execution"]},
    "e2b-data-analysis": {"cat": "AI/ML", "desc": "Execute data analysis pipelines in E2B cloud Jupyter environments.", "triggers": ["data analysis", "pandas", "notebook"]},
    # NetworkX + Neo4j
    "networkx-graph-analysis": {"cat": "Data Science", "desc": "Build and analyze graphs with NetworkX: centrality, shortest path, community detection.", "triggers": ["graph", "networkx", "network analysis"]},
    "neo4j-knowledge-graph": {"cat": "Database", "desc": "Store and query knowledge graphs in Neo4j using Cypher queries.", "triggers": ["neo4j", "cypher", "knowledge graph"]},
    "neo4j-rag-integration": {"cat": "AI/ML", "desc": "Use Neo4j as a vector + graph store for Retrieval Augmented Generation.", "triggers": ["rag", "neo4j", "retrieval"]},
    # Mem0
    "mem0-memory-layer": {"cat": "AI/ML", "desc": "Add persistent memory to AI agents using Mem0 memory layer.", "triggers": ["mem0", "memory", "remember"]},
    "mem0-user-preferences": {"cat": "AI/ML", "desc": "Store and retrieve user preferences across sessions with Mem0.", "triggers": ["preferences", "personalization"]},
    # OmniParser
    "omniparser-screen-understanding": {"cat": "Vision", "desc": "Parse and understand screen content using OmniParser for GUI automation.", "triggers": ["screen", "omniparser", "gui parse"]},
    "omniparser-element-detection": {"cat": "Vision", "desc": "Detect UI elements (buttons, text fields, icons) from screenshots.", "triggers": ["element detection", "ui elements"]},
    # EasyOCR / PaddleOCR
    "easyocr-text-extraction": {"cat": "Vision", "desc": "Extract text from images using EasyOCR with 80+ language support.", "triggers": ["ocr", "text extraction", "easyocr"]},
    "paddleocr-document-scan": {"cat": "Vision", "desc": "High-accuracy document scanning and text recognition with PaddleOCR.", "triggers": ["paddleocr", "document scan", "receipt"]},
    "ocr-table-extraction": {"cat": "Vision", "desc": "Extract tabular data from images and PDFs using OCR pipelines.", "triggers": ["table extraction", "pdf table"]},
    # PyAutoGUI / PyDirectInput
    "pyautogui-desktop-automation": {"cat": "RPA", "desc": "Automate mouse clicks, keyboard input, and screen interaction with PyAutoGUI.", "triggers": ["pyautogui", "mouse", "keyboard", "click"]},
    "pyautogui-screenshot-locate": {"cat": "RPA", "desc": "Locate UI elements on screen by image matching with PyAutoGUI.", "triggers": ["locate", "screen match", "find button"]},
    "pydirectinput-gaming": {"cat": "RPA", "desc": "Send direct input to games and full-screen apps using PyDirectInput.", "triggers": ["game input", "pydirectinput", "gaming"]},
    # Browser-use
    "browser-use-web-agent": {"cat": "Browser", "desc": "Control web browsers autonomously using browser-use framework for AI agents.", "triggers": ["browser-use", "web agent", "browse"]},
    "browser-use-form-filling": {"cat": "Browser", "desc": "Automatically fill web forms and submit data using browser-use.", "triggers": ["form fill", "submit", "web form"]},
    "browser-use-data-extraction": {"cat": "Browser", "desc": "Extract structured data from websites using browser-use automation.", "triggers": ["extract data", "scrape", "web data"]},
    # Crawl4AI
    "crawl4ai-web-crawler": {"cat": "Data", "desc": "Crawl websites and extract clean markdown content with Crawl4AI.", "triggers": ["crawl4ai", "crawl", "web crawler"]},
    "crawl4ai-structured-extraction": {"cat": "Data", "desc": "Extract structured JSON data from web pages using Crawl4AI schemas.", "triggers": ["structured extraction", "json extract"]},
    "crawl4ai-async-batch": {"cat": "Data", "desc": "Batch crawl hundreds of URLs asynchronously with Crawl4AI.", "triggers": ["batch crawl", "async crawl", "mass scrape"]},
    # SmolAgents (HuggingFace)
    "smolagents-tool-calling": {"cat": "AI/ML", "desc": "Build lightweight AI agents with tool-calling using HuggingFace SmolAgents.", "triggers": ["smolagents", "huggingface agent", "tool calling"]},
    "smolagents-code-agent": {"cat": "AI/ML", "desc": "Create code-generating agents that write and execute Python with SmolAgents.", "triggers": ["code agent", "code generation"]},
    "smolagents-multi-agent": {"cat": "AI/ML", "desc": "Orchestrate multiple SmolAgents for complex multi-step reasoning.", "triggers": ["multi-agent", "orchestrate"]},
    # PydanticAI
    "pydanticai-structured-output": {"cat": "AI/ML", "desc": "Build type-safe AI agents with structured outputs using PydanticAI.", "triggers": ["pydanticai", "structured output", "type-safe"]},
    "pydanticai-dependency-injection": {"cat": "AI/ML", "desc": "Use PydanticAI dependency injection for testable, modular agents.", "triggers": ["dependency injection", "modular agent"]},
    "pydanticai-streaming": {"cat": "AI/ML", "desc": "Stream structured responses from LLMs using PydanticAI streaming.", "triggers": ["streaming", "real-time response"]},
    # LangGraph
    "langgraph-state-machine": {"cat": "AI/ML", "desc": "Build stateful agent workflows as graphs using LangGraph.", "triggers": ["langgraph", "state machine", "workflow"]},
    "langgraph-human-in-loop": {"cat": "AI/ML", "desc": "Add human-in-the-loop checkpoints to LangGraph agent flows.", "triggers": ["human in loop", "checkpoint", "approval"]},
    "langgraph-multi-agent-supervisor": {"cat": "AI/ML", "desc": "Create supervisor agents that delegate to specialized sub-agents in LangGraph.", "triggers": ["supervisor", "delegation", "sub-agent"]},
    # Security
    "semgrep-code-scan": {"cat": "Security", "desc": "Scan code for vulnerabilities using Semgrep static analysis rules.", "triggers": ["semgrep", "vulnerability", "security scan"]},
    "bandit-python-security": {"cat": "Security", "desc": "Audit Python code for common security issues with Bandit.", "triggers": ["bandit", "python security"]},
    "dependency-audit": {"cat": "Security", "desc": "Check project dependencies for known CVEs using pip-audit or npm audit.", "triggers": ["dependency audit", "cve", "vulnerability check"]},
    # Database
    "sqlite-local-db": {"cat": "Database", "desc": "Create and query SQLite databases for local data storage.", "triggers": ["sqlite", "local database"]},
    "chromadb-vector-store": {"cat": "Database", "desc": "Store and query vector embeddings using ChromaDB for semantic search.", "triggers": ["chromadb", "vector", "embedding"]},
    "redis-cache-session": {"cat": "Database", "desc": "Use Redis for caching, sessions, and pub/sub messaging.", "triggers": ["redis", "cache", "session"]},
    "postgresql-advanced": {"cat": "Database", "desc": "Advanced PostgreSQL: CTEs, window functions, JSONB, full-text search.", "triggers": ["postgresql", "advanced sql", "jsonb"]},
    # Web Frameworks
    "fastapi-rest-api": {"cat": "Web", "desc": "Build high-performance REST APIs with FastAPI, async support, and auto-docs.", "triggers": ["fastapi", "rest api", "api endpoint"]},
    "nextjs-full-stack": {"cat": "Web", "desc": "Build full-stack React apps with Next.js App Router and Server Components.", "triggers": ["nextjs", "react", "full-stack"]},
    "flask-microservice": {"cat": "Web", "desc": "Create lightweight microservices with Flask and Blueprint architecture.", "triggers": ["flask", "microservice"]},
    # Data Processing
    "pandas-data-wrangling": {"cat": "Data Science", "desc": "Clean, transform, and analyze data with Pandas DataFrames.", "triggers": ["pandas", "dataframe", "data cleaning"]},
    "polars-fast-analytics": {"cat": "Data Science", "desc": "High-performance data analytics using Polars lazy evaluation.", "triggers": ["polars", "fast analytics", "lazy"]},
    "apache-arrow-interop": {"cat": "Data Science", "desc": "Zero-copy data interchange between Python libraries using Apache Arrow.", "triggers": ["arrow", "interop", "zero-copy"]},
    # ML/AI
    "transformers-inference": {"cat": "AI/ML", "desc": "Run transformer model inference with HuggingFace Transformers library.", "triggers": ["transformers", "inference", "bert", "gpt"]},
    "sentence-transformers-embeddings": {"cat": "AI/ML", "desc": "Generate text embeddings for semantic search using sentence-transformers.", "triggers": ["embeddings", "semantic search", "sentence-transformers"]},
    "ollama-local-llm": {"cat": "AI/ML", "desc": "Run and manage local LLMs using Ollama for private AI inference.", "triggers": ["ollama", "local llm", "private ai"]},
    "vllm-serving": {"cat": "AI/ML", "desc": "High-throughput LLM serving with vLLM for production deployments.", "triggers": ["vllm", "serving", "throughput"]},
    "lora-fine-tuning": {"cat": "AI/ML", "desc": "Fine-tune LLMs efficiently using LoRA/QLoRA adapters.", "triggers": ["lora", "fine-tune", "qlora", "adapter"]},
    "gguf-quantization": {"cat": "AI/ML", "desc": "Quantize models to GGUF format for efficient local inference.", "triggers": ["gguf", "quantize", "llama.cpp"]},
    # Monitoring & Observability
    "prometheus-metrics": {"cat": "DevOps", "desc": "Instrument Python apps with Prometheus metrics for monitoring.", "triggers": ["prometheus", "metrics", "monitoring"]},
    "opentelemetry-tracing": {"cat": "DevOps", "desc": "Add distributed tracing to microservices with OpenTelemetry.", "triggers": ["opentelemetry", "tracing", "observability"]},
    # Testing
    "pytest-testing": {"cat": "Testing", "desc": "Write and run comprehensive test suites with pytest fixtures and parametrize.", "triggers": ["pytest", "unit test", "testing"]},
    "playwright-e2e-testing": {"cat": "Testing", "desc": "End-to-end browser testing with Playwright for web applications.", "triggers": ["playwright", "e2e", "browser test"]},
    # CLI & Automation
    "typer-cli-builder": {"cat": "CLI", "desc": "Build beautiful CLI applications with Typer and Rich output.", "triggers": ["typer", "cli", "command line"]},
    "rich-terminal-ui": {"cat": "CLI", "desc": "Create rich terminal UIs with tables, progress bars, and syntax highlighting.", "triggers": ["rich", "terminal ui", "pretty print"]},
    # Cloud
    "aws-boto3-s3": {"cat": "Cloud", "desc": "Manage AWS S3 buckets and objects using boto3 SDK.", "triggers": ["aws", "s3", "boto3"]},
    "gcp-cloud-functions": {"cat": "Cloud", "desc": "Deploy serverless functions on Google Cloud Platform.", "triggers": ["gcp", "cloud functions", "serverless"]},
    "azure-cognitive-services": {"cat": "Cloud", "desc": "Use Azure Cognitive Services for vision, speech, and language AI.", "triggers": ["azure", "cognitive", "vision api"]},
    # Communication
    "slack-bot-builder": {"cat": "Communication", "desc": "Build Slack bots with slash commands, modals, and event handling.", "triggers": ["slack", "bot", "slash command"]},
    "discord-bot-builder": {"cat": "Communication", "desc": "Create Discord bots with commands, embeds, and voice support.", "triggers": ["discord", "bot", "commands"]},
    "telegram-bot-api": {"cat": "Communication", "desc": "Build Telegram bots with inline keyboards and webhook support.", "triggers": ["telegram", "bot", "webhook"]},
    "twilio-sms-voice": {"cat": "Communication", "desc": "Send SMS and make voice calls programmatically with Twilio.", "triggers": ["twilio", "sms", "voice call"]},
    # Image/Video
    "pillow-image-processing": {"cat": "Media", "desc": "Process images: resize, crop, filter, watermark using Pillow.", "triggers": ["pillow", "image", "resize"]},
    "opencv-computer-vision": {"cat": "Vision", "desc": "Computer vision with OpenCV: face detection, object tracking, image analysis.", "triggers": ["opencv", "computer vision", "face detection"]},
    "ffmpeg-video-processing": {"cat": "Media", "desc": "Transcode, trim, merge, and process video files with FFmpeg.", "triggers": ["ffmpeg", "video", "transcode"]},
    "stable-diffusion-generation": {"cat": "AI/ML", "desc": "Generate images from text using Stable Diffusion with diffusers library.", "triggers": ["stable diffusion", "image generation", "diffusers"]},
    # MCP Skills (from mcpservers.org)
    "mcp-filesystem-server": {"cat": "MCP", "desc": "Read, write, and manage files through MCP filesystem server.", "triggers": ["mcp", "filesystem", "file access"]},
    "mcp-sqlite-server": {"cat": "MCP", "desc": "Query and manage SQLite databases through MCP server protocol.", "triggers": ["mcp sqlite", "database mcp"]},
    "mcp-git-server": {"cat": "MCP", "desc": "Perform git operations (commit, branch, diff) via MCP server.", "triggers": ["mcp git", "version control"]},
    "mcp-fetch-server": {"cat": "MCP", "desc": "Fetch web content and APIs through MCP fetch server.", "triggers": ["mcp fetch", "web fetch"]},
    "mcp-puppeteer-browser": {"cat": "MCP", "desc": "Control headless Chrome for web automation via MCP Puppeteer.", "triggers": ["mcp puppeteer", "headless chrome"]},
    # Robotics & Physical AI (from Medium article)
    "robotics-motion-planning": {"cat": "Robotics", "desc": "Plan robot motion paths with collision avoidance algorithms.", "triggers": ["motion planning", "robot", "path planning"]},
    "robotics-sensor-fusion": {"cat": "Robotics", "desc": "Fuse data from multiple sensors (LIDAR, camera, IMU) for robot perception.", "triggers": ["sensor fusion", "lidar", "imu"]},
    "robotics-manipulation": {"cat": "Robotics", "desc": "Program robotic arm manipulation tasks: pick, place, grasp planning.", "triggers": ["manipulation", "robotic arm", "grasp"]},
    "physical-ai-sim2real": {"cat": "Robotics", "desc": "Transfer learned behaviors from simulation to real robots (sim2real).", "triggers": ["sim2real", "simulation", "transfer"]},
    # Additional AI Agent Skills
    "agent-memory-management": {"cat": "AI/ML", "desc": "Implement working, episodic, and semantic memory for AI agents.", "triggers": ["agent memory", "episodic", "semantic"]},
    "agent-tool-use": {"cat": "AI/ML", "desc": "Enable AI agents to discover, select, and use tools dynamically.", "triggers": ["tool use", "function calling", "tool selection"]},
    "agent-reflection": {"cat": "AI/ML", "desc": "Add self-reflection and self-critique capabilities to AI agents.", "triggers": ["reflection", "self-critique", "metacognition"]},
    "agent-planning": {"cat": "AI/ML", "desc": "Implement hierarchical task planning and decomposition for agents.", "triggers": ["planning", "task decomposition", "hierarchical"]},
    "rag-advanced-retrieval": {"cat": "AI/ML", "desc": "Advanced RAG: re-ranking, hybrid search, contextual compression.", "triggers": ["rag", "retrieval", "re-ranking"]},
    "rag-document-chunking": {"cat": "AI/ML", "desc": "Smart document chunking strategies for RAG: semantic, recursive, agentic.", "triggers": ["chunking", "document split", "recursive"]},
    "prompt-engineering": {"cat": "AI/ML", "desc": "Advanced prompt engineering: chain-of-thought, few-shot, self-consistency.", "triggers": ["prompt", "chain of thought", "few-shot"]},
    "llm-evaluation": {"cat": "AI/ML", "desc": "Evaluate LLM outputs with automated metrics: BLEU, ROUGE, LLM-as-judge.", "triggers": ["evaluation", "benchmark", "llm judge"]},
    "guardrails-safety": {"cat": "AI/ML", "desc": "Add safety guardrails to LLM outputs: content filtering, PII detection.", "triggers": ["guardrails", "safety", "content filter"]},
    # Web Scraping
    "beautifulsoup-parsing": {"cat": "Data", "desc": "Parse HTML/XML documents with BeautifulSoup for data extraction.", "triggers": ["beautifulsoup", "html parse", "soup"]},
    "scrapy-spider": {"cat": "Data", "desc": "Build production web scrapers with Scrapy framework.", "triggers": ["scrapy", "spider", "web scraper"]},
    "selenium-automation": {"cat": "Browser", "desc": "Automate browsers with Selenium WebDriver for testing and scraping.", "triggers": ["selenium", "webdriver", "automate browser"]},
    # DevOps
    "github-actions-ci": {"cat": "DevOps", "desc": "Create GitHub Actions workflows for CI/CD pipelines.", "triggers": ["github actions", "ci/cd", "workflow"]},
    "terraform-iac": {"cat": "DevOps", "desc": "Infrastructure as Code with Terraform for cloud resource management.", "triggers": ["terraform", "infrastructure", "iac"]},
    "kubernetes-deployment": {"cat": "DevOps", "desc": "Deploy and manage containerized apps on Kubernetes clusters.", "triggers": ["kubernetes", "k8s", "deployment"]},
    # Misc
    "pdf-generation": {"cat": "Document", "desc": "Generate professional PDF documents with reportlab and WeasyPrint.", "triggers": ["pdf", "generate pdf", "report"]},
    "excel-automation": {"cat": "Document", "desc": "Read, write, and automate Excel files with openpyxl.", "triggers": ["excel", "xlsx", "spreadsheet"]},
    "email-automation": {"cat": "Communication", "desc": "Send automated emails with attachments using smtplib and email.", "triggers": ["email", "smtp", "send mail"]},
    "websocket-realtime": {"cat": "Web", "desc": "Build real-time apps with WebSocket connections and message streaming.", "triggers": ["websocket", "real-time", "streaming"]},
    "graphql-api": {"cat": "Web", "desc": "Build and query GraphQL APIs with Strawberry or Ariadne.", "triggers": ["graphql", "query", "mutation"]},
    "grpc-microservices": {"cat": "Web", "desc": "Build high-performance microservices with gRPC and Protocol Buffers.", "triggers": ["grpc", "protobuf", "microservice"]},
    "celery-task-queue": {"cat": "DevOps", "desc": "Run background tasks and distributed job queues with Celery.", "triggers": ["celery", "background task", "queue"]},
    "asyncio-concurrency": {"cat": "Python", "desc": "Master Python asyncio for concurrent I/O-bound operations.", "triggers": ["asyncio", "async", "concurrent"]},
    "regex-pattern-matching": {"cat": "Python", "desc": "Advanced regex patterns for text parsing, validation, and extraction.", "triggers": ["regex", "pattern", "regular expression"]},
    "cryptography-encryption": {"cat": "Security", "desc": "Encrypt, decrypt, hash, and sign data with Python cryptography library.", "triggers": ["encrypt", "decrypt", "hash", "cryptography"]},
    "jwt-authentication": {"cat": "Security", "desc": "Implement JWT-based authentication and authorization flows.", "triggers": ["jwt", "token", "authentication"]},
    "oauth2-integration": {"cat": "Security", "desc": "Integrate OAuth2 login flows with Google, GitHub, Microsoft providers.", "triggers": ["oauth2", "login", "social auth"]},
    "numpy-scientific": {"cat": "Data Science", "desc": "Scientific computing with NumPy: linear algebra, FFT, random sampling.", "triggers": ["numpy", "scientific", "linear algebra"]},
    "matplotlib-visualization": {"cat": "Data Science", "desc": "Create publication-quality plots and charts with Matplotlib.", "triggers": ["matplotlib", "plot", "chart", "visualization"]},
    "plotly-interactive-charts": {"cat": "Data Science", "desc": "Build interactive dashboards and charts with Plotly and Dash.", "triggers": ["plotly", "dashboard", "interactive chart"]},
}

# ─── AGENT DEFINITIONS ───
AGENT_DEFS = {
    "docker-ops-agent": {"role": "DevOps Engineer", "desc": "Manages Docker containers, images, networks, and compose stacks.", "tools": ["docker SDK", "docker-compose"]},
    "data-scientist-agent": {"role": "Data Scientist", "desc": "Analyzes data, builds ML models, creates visualizations.", "tools": ["pandas", "scikit-learn", "matplotlib"]},
    "web-scraper-agent": {"role": "Web Scraper", "desc": "Crawls websites, extracts structured data, handles pagination.", "tools": ["crawl4ai", "beautifulsoup", "playwright"]},
    "security-auditor-agent": {"role": "Security Auditor", "desc": "Scans code for vulnerabilities, audits dependencies, checks configs.", "tools": ["semgrep", "bandit", "pip-audit"]},
    "database-admin-agent": {"role": "Database Administrator", "desc": "Designs schemas, optimizes queries, manages migrations.", "tools": ["SQLAlchemy", "Alembic", "psycopg2"]},
    "api-builder-agent": {"role": "API Developer", "desc": "Builds REST and GraphQL APIs with authentication and docs.", "tools": ["FastAPI", "Strawberry", "Pydantic"]},
    "ml-engineer-agent": {"role": "ML Engineer", "desc": "Trains, fine-tunes, and deploys machine learning models.", "tools": ["transformers", "PEFT", "vLLM"]},
    "robotics-agent": {"role": "Robotics Engineer", "desc": "Programs robotic systems: motion planning, perception, manipulation.", "tools": ["ROS2", "OpenCV", "PyBullet"]},
    "devops-agent": {"role": "DevOps Engineer", "desc": "Manages CI/CD pipelines, infrastructure, and deployments.", "tools": ["GitHub Actions", "Terraform", "Kubernetes"]},
    "document-processor-agent": {"role": "Document Processor", "desc": "Extracts, generates, and transforms documents (PDF, DOCX, XLSX).", "tools": ["reportlab", "python-docx", "openpyxl"]},
    "communication-agent": {"role": "Communication Manager", "desc": "Manages messaging across Slack, Discord, Telegram, and email.", "tools": ["slack-sdk", "discord.py", "python-telegram-bot"]},
    "browser-automation-agent": {"role": "Browser Automation", "desc": "Controls browsers for testing, form filling, and data extraction.", "tools": ["browser-use", "playwright", "selenium"]},
    "ocr-vision-agent": {"role": "OCR & Vision Specialist", "desc": "Extracts text from images, analyzes visual content.", "tools": ["EasyOCR", "PaddleOCR", "OpenCV"]},
    "knowledge-graph-agent": {"role": "Knowledge Engineer", "desc": "Builds and queries knowledge graphs for structured reasoning.", "tools": ["Neo4j", "NetworkX", "RDFLib"]},
    "memory-agent": {"role": "Memory Manager", "desc": "Manages agent memory: working, episodic, semantic, and procedural.", "tools": ["Mem0", "ChromaDB", "Redis"]},
    "prompt-engineer-agent": {"role": "Prompt Engineer", "desc": "Designs, tests, and optimizes prompts for LLM applications.", "tools": ["DSPy", "LangSmith", "promptfoo"]},
    "testing-qa-agent": {"role": "QA Engineer", "desc": "Writes and runs tests: unit, integration, e2e, load testing.", "tools": ["pytest", "playwright", "locust"]},
    "cloud-architect-agent": {"role": "Cloud Architect", "desc": "Designs cloud infrastructure across AWS, GCP, and Azure.", "tools": ["boto3", "google-cloud", "azure-sdk"]},
    "gui-rpa-agent": {"role": "Desktop Automation", "desc": "Automates desktop apps with mouse/keyboard and screen recognition.", "tools": ["PyAutoGUI", "OmniParser", "PyDirectInput"]},
    "sandbox-execution-agent": {"role": "Sandbox Executor", "desc": "Safely executes code in isolated E2B/Docker sandboxes.", "tools": ["E2B", "Docker SDK", "subprocess"]},
}

def gen_skill_md(name, info):
    return f"""---
name: {name}
category: {info['cat']}
version: 1.0.0
triggers: {info['triggers']}
---

# Skill: {name}

## Description
{info['desc']}

## Category
{info['cat']}

## When to Use
Use this skill when the user's request involves: {', '.join(info['triggers'])}.

## Implementation Notes
- This skill is part of the Ultron AGI skill library.
- It integrates with the Orchestrator's intent classification system.
- Compatible with all Ultron LLM providers (Groq, Gemini, Ollama).
"""

def gen_agent_md(name, info):
    return f"""---
name: {name}
role: {info['role']}
version: 1.0.0
---

# Agent: {name}

## Role
{info['role']}

## Description
{info['desc']}

## Tools
{chr(10).join(f'- {t}' for t in info['tools'])}

## Capabilities
This agent specializes in {info['role'].lower()} tasks within the Ultron AGI system.
It can be invoked by the Orchestrator when user intent matches its domain.
"""

def main():
    created_skills = 0
    created_agents = 0
    
    for name, info in TECH_SKILLS.items():
        path = SKILLS_DIR / name
        path.mkdir(exist_ok=True)
        skill_file = path / "SKILL.md"
        if not skill_file.exists():
            skill_file.write_text(gen_skill_md(name, info), encoding="utf-8")
            created_skills += 1
    
    for name, info in AGENT_DEFS.items():
        path = AGENTS_DIR / name
        path.mkdir(exist_ok=True)
        agent_file = path / "AGENT.md"
        if not agent_file.exists():
            agent_file.write_text(gen_agent_md(name, info), encoding="utf-8")
            created_agents += 1
    
    # Count totals
    total_skills = sum(1 for _ in SKILLS_DIR.rglob("SKILL.md")) + sum(1 for f in SKILLS_DIR.glob("*.md") if f.name != "SKILL.md")
    total_agents = sum(1 for _ in AGENTS_DIR.rglob("AGENT.md")) + sum(1 for f in AGENTS_DIR.glob("*.md") if f.name != "AGENT.md")
    
    print(f"Created {created_skills} new skills, {created_agents} new agents")
    print(f"TOTAL SKILLS: {total_skills}")
    print(f"TOTAL AGENTS: {total_agents}")

if __name__ == "__main__":
    main()
