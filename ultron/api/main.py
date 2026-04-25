"""Ultron v2.0 — FastAPI Backend Bridge."""
from __future__ import annotations
import asyncio
import logging
import os
import time
import warnings
from contextlib import asynccontextmanager
from typing import Optional

# Suppress verbose Torch and EasyOCR warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="torch.*|websockets.*|uvicorn.*")
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import StreamingResponse

START_TIME = time.time()
_orchestrator: Optional["Orchestrator"] = None

# Structured logging
try:
    import structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer() if os.getenv("DEBUG") else structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    logger = structlog.get_logger("ultron.api")
    _use_structlog = True
except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger("ultron.api")
    _use_structlog = False

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.gzip import GZipMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator
    if _use_structlog:
        logger.info("=" * 60)
        logger.info("ULTRON v2.0 API — Starting...")
        logger.info("=" * 60)
    else:
        logger.info("=" * 60)
        logger.info("ULTRON v2.0 API — Starting...")
        logger.info("=" * 60)
    load_dotenv()
    try:
        from ultron.v2.core.llm_router import LLMRouter
        from ultron.v2.memory.engine import MemoryEngine
        from ultron.v2.core.orchestrator import Orchestrator

        llm_model = os.getenv("ULTRON_MODEL", "qwen2.5:14b")
        llm = LLMRouter(ollama_model=llm_model)
        llm.enable_all_providers(dict(os.environ))
        memory = MemoryEngine(persist_dir="./data/memory_v2")
        _orchestrator = Orchestrator(llm_router=llm, memory=memory, work_dir="./workspace")
        await _orchestrator.start()  # Sets _running=True, starts all agents

        # Start background daemons
        try:
            from ultron.v2.core.auto_launchers import start_all_auto_launchers
            from ultron.v2.core.eternal_evolution import EternalEvolutionEngine
            
            await start_all_auto_launchers()

            # Optional: Eternal Evolution (DISABLED by default)
            if os.getenv("ULTRON_EVOLUTION_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on"):
                interval = int(os.getenv("ULTRON_EVOLUTION_INTERVAL_MINUTES", "15"))
                if interval <= 0:
                    raise ValueError("ULTRON_EVOLUTION_INTERVAL_MINUTES must be > 0")
                evolution_daemon = EternalEvolutionEngine(_orchestrator, sleep_interval_minutes=interval)
                asyncio.create_task(evolution_daemon.start_loop())
                if _use_structlog:
                    logger.info("eternal_daemon_started", interval_minutes=interval)
                else:
                    logger.info("Eternal Autonomous Evolution daemon enabled (interval=%dm).", interval)
        except Exception as e:
            if not _use_structlog:
                logger.warning(f"Failed to start background daemons: {e}")

        if _use_structlog:
            logger.info("llm_providers", providers=llm.get_healthy_providers())
            logger.info("agents_started", agents=list(_orchestrator.agents.keys()))
            if _orchestrator.mcp_manager.enabled:
                logger.info("mcp_enabled", servers=_orchestrator.mcp_manager.list_server_ids())
            else:
                logger.info("mcp_disabled")
        else:
            logger.info("LLM Providers: %s", llm.get_healthy_providers())
            logger.info("Agents started: %s", list(_orchestrator.agents.keys()))
            if _orchestrator.mcp_manager.enabled:
                logger.info("MCP Enabled. Active servers: %s", _orchestrator.mcp_manager.list_server_ids())
            else:
                logger.info("MCP is disabled or no servers configured.")
    except Exception as e:
        if _use_structlog:
            logger.error("startup_failed", error=str(e), exc_info=True)
        else:
            logger.error("Failed to initialize: %s", e, exc_info=True)
        _orchestrator = None

    # ── Ultron v3.0 Initialization ─────────────────────────────────────
    try:
        from ultron.v2.core.agent_registry import registry
        from ultron.v2.core.react_orchestrator import ReActOrchestrator
        from ultron.v2.core.event_bus import EventBus
        from ultron.v2.core.blackboard import Blackboard
        import ultron.v2.agents as agents_pkg
        
        # 1. Initialize v3 Core Components
        try:
            _llm_router = llm
        except NameError:
            _llm_router = LLMRouter()
            _llm_router.enable_all_providers(dict(os.environ))

        _event_bus = EventBus()
        _blackboard = Blackboard()

        # 2. Set shared resources for the registry
        registry.set_factory_provider("llm_router", _llm_router)
        registry.set_factory_provider("event_bus", _event_bus)
        registry.set_factory_provider("blackboard", _blackboard)

        # 3. Register Orchestrator
        if not registry.get_agent("ReActOrchestrator"):
            registry.register(ReActOrchestrator(memory=memory))
            
        # 4. Register all specialized agents lazily
        registered_count = 0
        for attr_name in agents_pkg.__all__:
            if attr_name in ("Agent", "BaseAgent"):
                continue
            
            try:
                agent_cls = getattr(agents_pkg, attr_name)
                desc = getattr(agent_cls, "agent_description", "Specialized Ultron Agent")
                registry.register_lazy(attr_name, desc, agent_cls)
                registered_count += 1
            except Exception as reg_e:
                logger.warning(f"Failed to register agent {attr_name}: {reg_e}")
            
        logger.info(f"Ultron v3.0 Infrastructure Ready. {registered_count} agents registered.")
    except Exception as e:
        logger.error(f"v3.0 Init Error: {e}", exc_info=True)

    yield
    if _use_structlog:
        logger.info("shutdown_started")
    else:
        logger.info("Shutting down...")
    if _orchestrator:
        await _orchestrator.stop()


app = FastAPI(title="Ultron v2.0 API", version="2.1.0", lifespan=lifespan)

# ── Security: CORS — scoped origins, not "*" ──────────────────────────
allowed_origins = os.getenv(
    "ULTRON_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"
).split(",")

# Add Ngrok URL if present
ngrok_url = os.getenv("NGROK_URL", "").strip()
if ngrok_url:
    if ngrok_url.endswith("/"):
        ngrok_url = ngrok_url[:-1]
    allowed_origins.append(ngrok_url)
    allowed_origins.append(ngrok_url.replace("https://", "http://"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security: API Key authentication (optional) ───────────────────────
ULTRON_API_KEY = os.getenv("ULTRON_API_KEY")

async def verify_api_key(request: Request):
    if not ULTRON_API_KEY:
        return  # No key configured, skip auth
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")
    # SECURITY FIX: Use constant-time comparison to prevent timing attacks
    import hmac
    if not hmac.compare_digest(api_key, ULTRON_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")

# ── Request logging middleware ────────────────────────────────────────
app.add_middleware(RequestIDMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

async def _log_request_middleware(request: Request, call_next):
    """Middleware for structured request logging."""
    start = time.time()
    request_id = getattr(request.state, "request_id", "unknown")
    response = None
    try:
        response = await call_next(request)
    finally:
        duration_ms = (time.time() - start) * 1000
        if _use_structlog:
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                request_id=request_id,
                duration_ms=round(duration_ms, 2),
                status_code=getattr(response, "status_code", None) if response else None,
            )
        else:
            logger.info(
                "[%s] %s %s — %dms — %s",
                request_id,
                request.method,
                request.url.path,
                round(duration_ms, 2),
                getattr(response, "status_code", None) if response else "?",
            )
    return response

app.add_middleware(BaseHTTPMiddleware, dispatch=_log_request_middleware)

from ultron.api.routes.chat import router as chat_router
from ultron.api.routes.agents import router as agents_router
from ultron.api.routes.status import router as status_router
from ultron.api.routes.training import router as training_router
from ultron.api.routes.conversations import router as conversations_router
from ultron.api.routes.composer import router as composer_router
from ultron.api.routes.voice import router as voice_router

app.include_router(chat_router)
app.include_router(agents_router)
app.include_router(status_router)
app.include_router(training_router)
app.include_router(conversations_router)
app.include_router(composer_router)
app.include_router(voice_router)
from ultron.api.routes.v3_chat import router as v3_router
app.include_router(v3_router)

# ── Config API ────────────────────────────────────────────────────────
class ConfigUpdateRequest(BaseModel):
    model: Optional[str] = None
    search_depth: Optional[int] = None
    autonomous_evolution: Optional[bool] = None

@app.post("/api/v2/config/update")
async def update_config(req: ConfigUpdateRequest):
    orch = await get_orchestrator()
    if not orch:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    
    if req.model:
        orch.llm_router.update_config(model=req.model)
    
    if req.search_depth:
        # Map search depth (1-5) to reasoning steps (4-20)
        steps = req.search_depth * 4
        orch.reasoning.max_reasoning_steps = steps
        logger.info("Config: Updated reasoning max_steps to %d", steps)
        
    return {"status": "success", "message": "Configuration updated successfully"}

# Workspace models — needed for endpoint type hints
from ultron.v2.workspace.models import CloneRequest, GenerateRequest, SynthesizeRequest, OpenFolderRequest

# Workspace manager — lazy init to avoid heavy imports at startup

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    if _use_structlog:
        logger.error("unhandled_error", error=str(exc), exc_info=True)
    else:
        logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc)})

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded", "detail": str(exc)},
    )

@app.get("/")
async def root():
    return {
        "name": "Ultron v2.0 API",
        "version": "2.1.0",
        "status": "running" if _orchestrator else "initializing",
        "docs": "/docs",
    }

@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    """Health check endpoint with sub-system details."""
    uptime = time.time() - START_TIME
    
    # Sub-system checks
    checks = {
        "api": "ok",
        "orchestrator": "ok" if _orchestrator else "initializing",
    }
    
    # Check Providers
    try:
        from ultron.v2.providers.router import ProviderRouter
        router = ProviderRouter()
        status = await router.provider_status()
        checks["providers_healthy"] = sum(1 for p in status.values() if p["available"])
    except:
        checks["providers"] = "error"

    all_ok = all(v != "error" and v != "degraded" for v in checks.values())
    
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "healthy" if all_ok else "degraded",
            "version": "2.1.0",
            "uptime_seconds": round(uptime, 1),
            "checks": checks
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# Workspace API Endpoints (FAZ 2 — Master Workspace + Agentic RAG)
# ═══════════════════════════════════════════════════════════════════════

_workspace_mgr = None

async def get_workspace_mgr():
    global _workspace_mgr
    if _workspace_mgr is None:
        try:
            from ultron.v2.workspace.workspace_manager import WorkspaceManager
            _workspace_mgr = WorkspaceManager()
            await _workspace_mgr.init_db()
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Workspace dependency missing: {e}. Install with: pip install aiosqlite playwright"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Workspace init failed: {e}"
            )
    return _workspace_mgr


@app.post("/api/v2/workspace/clone", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def clone_site(req: CloneRequest, request: Request):
    """n8n veya frontend tarafından çağrılır. URL'yi klonlar."""
    try:
        mgr = await get_workspace_mgr()
        item = await mgr.clone_site(req)
        return {"success": True, "item": item.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/workspace/generate", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def generate_app(req: GenerateRequest, request: Request):
    """Fikir metninden sıfırdan uygulama üretir."""
    try:
        mgr = await get_workspace_mgr()
        item = await mgr.generate_app(req)
        return {"success": True, "item": item.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/workspace/synthesize", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def synthesize(req: SynthesizeRequest, request: Request):
    """Mevcut şablonlardan yeni uygulama sentezler."""
    try:
        mgr = await get_workspace_mgr()
        item = await mgr.synthesize(req)
        return {"success": True, "item": item.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/status", tags=["System"])
async def get_status():
    orch = await get_orchestrator()
    if not orch:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orch.get_status()

@app.get("/api/v2/status/evolution", tags=["System"])
async def get_evolution_status():
    """Get statistics from the self-improvement and evolution engines."""
    orch = await get_orchestrator()
    if not orch:
        return {"error": "Orchestrator not ready"}
        
    stats = {}
    if hasattr(orch, 'self_improvement'):
        stats["self_improvement"] = orch.self_improvement.get_stats()
    
    # Check if eternal evolution is active
    import os
    stats["eternal_evolution"] = {
        "enabled": os.getenv("ULTRON_EVOLUTION_ENABLED", "0") in ("1", "true", "yes", "on"),
        "allow_git": os.getenv("ULTRON_EVOLUTION_ALLOW_GIT", "0") in ("1", "true", "yes", "on"),
    }
    return stats

@app.post("/api/v2/workspace/evolve", tags=["Workspace"])
async def trigger_evolution():
    """Manually trigger the autonomous evolution cycle."""
    orch = await get_orchestrator()
    if not orch:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
    if not hasattr(orch, 'evolution'):
        from ultron.v2.core.eternal_evolution import EternalEvolutionEngine
        orch.evolution = EternalEvolutionEngine(orch)
        
    asyncio.create_task(orch.evolution.evolution_cycle())
    return {"status": "Evolution cycle triggered", "message": "Ultron is brainstorming and evolving..."}


@app.get("/api/v2/workspace/list")
async def list_workspace():
    mgr = await get_workspace_mgr()
    items = await mgr.list_workspace()
    return {"items": [i.model_dump() for i in items]}


@app.get("/api/v2/workspace/search")
async def search_workspace(q: str, top_k: int = 5):
    mgr = await get_workspace_mgr()
    results = await mgr.search_templates(q, top_k)
    return {"results": results}


@app.post("/api/v2/workspace/open-folder", dependencies=[Depends(verify_api_key)])
async def open_workspace_folder(req: OpenFolderRequest, request: Request):
    """Opens the folder in the local OS file explorer."""
    logger.info("open_workspace_folder_called", item_id=req.id)
    try:
        mgr = await get_workspace_mgr()
        success = await mgr.open_folder(req.id)
        if not success:
            logger.warning("open_folder_failed", item_id=req.id)
        return {"success": success}
    except Exception as e:
        logger.error("open_folder_error", error=str(e), item_id=req.id)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# Provider Router API — Multi-provider chat + status
# ═══════════════════════════════════════════════════════════════════════

_provider_router = None


def _get_provider_router():
    global _provider_router
    if _provider_router is None:
        from ultron.v2.providers.router import ProviderRouter
        _provider_router = ProviderRouter()
    return _provider_router


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    task_type: str = "default"
    preferred_provider: Optional[str] = None
    model: Optional[str] = None
    stream: bool = False


class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    voice: Optional[str] = None


@app.post("/api/v2/chat")
@limiter.limit("30/minute")
async def provider_chat(req: ChatRequest, request: Request):
    """Multi-provider chat with smart routing + fallback."""
    try:
        from ultron.v2.providers.base import Message as ProviderMessage

        router = _get_provider_router()
        messages = [ProviderMessage(role=m.role, content=m.content) for m in req.messages]
        result = await router.route(
            messages,
            task_type=req.task_type,
            preferred_provider=req.preferred_provider,
            model=req.model,
            stream=req.stream,
        )
        return {
            "success": True,
            "content": result.content,
            "provider": result.provider,
            "model": result.model,
            "tokens_used": result.tokens_used,
            "latency_ms": result.latency_ms,
        }
    except RuntimeError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/v2/providers/status")
async def providers_status():
    """Show which providers are active and their latency."""
    try:
        router = _get_provider_router()
        status = await router.provider_status()
        return {
            "available": router.available_providers(),
            "details": status,
        }
    except Exception as e:
        return {"error": str(e)}


class OpenGuiderRequest(BaseModel):
    message: str
    image_b64: Optional[str] = None

@app.post("/api/v2/openguider/chat")
@limiter.limit("30/minute")
async def openguider_chat(req: OpenGuiderRequest, request: Request):
    """Endpoint for OpenGuider to interact with Ultron."""
    try:
        from ultron.v2.core.types import AgentRole, Task
        if not _orchestrator:
            return JSONResponse(status_code=503, content={"error": "Orchestrator not ready yet."})
            
        agent = _orchestrator.agents.get(AgentRole.VISION)
        if not agent:
            # Fallback to standard process if bridge not registered
            result = await _orchestrator.process(req.message)
            return {"success": True, "response": result}

        # Submit task to OpenGuiderBridgeAgent
        task = Task(
            description=req.message,
            context={"action": "process_screen" if req.image_b64 else "chat", "image_b64": req.image_b64}
        )
        task_result = await agent.execute(task)
        return {"success": task_result.status == "success", "response": task_result.output, "error": task_result.error}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ──────────────────────────────────────────────────────────────────────
# TTS Endpoint — Text-to-Speech via edge-tts with Cache
# ──────────────────────────────────────────────────────────────────────

import hashlib
_tts_cache = {}  # In-memory cache: hash(text+voice) -> audio_bytes

@app.post("/api/v2/tts")
@limiter.limit("60/minute")
async def text_to_speech(req: TTSRequest, request: Request):
    """Convert text to speech. Returns audio stream. Uses VoiceBox with EdgeTTS fallback."""
    try:
        import httpx
        import io

        # 0. Check Cache
        voice = req.voice
        if not voice:
            voice = "tr-TR-AhmetNeural" if req.language == "tr" else "en-GB-RyanNeural"
            
        cache_key = hashlib.md5(f"{req.text}:{voice}".encode()).hexdigest()
        if cache_key in _tts_cache:
            if _use_structlog: logger.info("tts_cache_hit", text=req.text[:20])
            return StreamingResponse(
                io.BytesIO(_tts_cache[cache_key]),
                media_type="audio/mpeg",
                headers={"X-TTS-Cache": "HIT"}
            )

        # 1. Try Local VoiceBox API
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Assuming VoiceBox takes simple JSON and returns audio stream
                payload = {
                    "text": req.text,
                    "language": req.language, 
                }
                if req.voice:
                    payload["profile_id"] = req.voice

                resp = await client.post("http://localhost:17493/generate", json=payload)
                if resp.status_code == 200:
                    _tts_cache[cache_key] = resp.content # Save to cache
                    return StreamingResponse(
                        io.BytesIO(resp.content),
                        media_type="audio/mpeg",
                        headers={
                            "Content-Disposition": 'inline; filename="tts.mp3"',
                            "X-TTS-Engine": "VoiceBox",
                            "X-TTS-Cache": "MISS"
                        }
                    )
                else:
                    if _use_structlog:
                        logger.warning("voicebox_failed", status_code=resp.status_code, content=resp.text)
                    else:
                        logger.warning(f"VoiceBox failed: {resp.status_code}")
        except Exception as vb_error:
            if _use_structlog:
                logger.debug("voicebox_unavailable", error=str(vb_error))
            else:
                logger.debug(f"VoiceBox unavailable: {vb_error}")

        # 2. Fallback to EdgeTTS
        import edge_tts
        
        # Stream and collect for caching
        communicate = edge_tts.Communicate(req.text, voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        
        # Save to cache (limit size to 100 entries)
        if len(_tts_cache) > 100:
            _tts_cache.pop(next(iter(_tts_cache)))
        _tts_cache[cache_key] = audio_bytes

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": 'inline; filename="tts.mp3"',
                "X-Voice": voice,
                "X-TTS-Engine": "EdgeTTS",
                "X-TTS-Cache": "MISS"
            }
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

async def get_orchestrator():
    return _orchestrator

@app.get("/api/v3/agents")
async def get_all_agents():
    """Returns status and metadata for all registered agents (v3.0 compatible)."""
    from ultron.v2.core.agent_registry import registry
    agents = []
    for agent_info in registry.list_agents():
        agent = registry.get_agent(agent_info["name"])
        if agent:
            agents.append(agent.get_status())
    return agents

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ultron.api.main:app", host="0.0.0.0", port=8000, reload=True,
                reload_excludes=["workspace/*", "data/*", ".venv/*"])
