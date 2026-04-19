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
warnings.filterwarnings("ignore", category=UserWarning, module="torch.*|easyocr.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="torch.*|websockets.*")

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

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

def _log_request_middleware(request: Request, call_next):
    """Middleware for structured request logging."""
    start = time.time()
    response = None
    try:
        response = call_next(request)
    finally:
        duration_ms = (time.time() - start) * 1000
        if _use_structlog:
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                status_code=getattr(response, "status_code", None) if response else None,
            )
        else:
            logger.info(
                "%s %s — %dms — %s",
                request.method,
                request.url.path,
                round(duration_ms, 2),
                getattr(response, "status_code", None) if response else "?",
            )
    return response


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

        llm = LLMRouter(ollama_model="qwen2.5:14b")
        llm.enable_all_providers(dict(os.environ))
        memory = MemoryEngine(persist_dir="./data/memory_v2")
        _orchestrator = Orchestrator(llm_router=llm, memory=memory, work_dir="./workspace")
        await _orchestrator.start()  # Sets _running=True, starts all agents

        # Start background daemons
        try:
            from ultron.v2.core.auto_launchers import start_all_auto_launchers
            from ultron.v2.core.eternal_evolution import EternalEvolutionEngine
            import asyncio
            import os
            
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
        else:
            logger.info("LLM Providers: %s", llm.get_healthy_providers())
            logger.info("Agents started: %s", list(_orchestrator.agents.keys()))
    except Exception as e:
        if _use_structlog:
            logger.error("startup_failed", error=str(e), exc_info=True)
        else:
            logger.error("Failed to initialize: %s", e, exc_info=True)
        _orchestrator = None
    yield
    if _use_structlog:
        logger.info("shutdown_started")
    else:
        logger.info("Shutting down...")
    if _orchestrator:
        await _orchestrator.stop()


app = FastAPI(title="Ultron v2.0 API", version="2.1.0", lifespan=lifespan)

# ── Security: CORS — scoped origins, not "*" ──────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ULTRON_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
from starlette.middleware.base import BaseHTTPMiddleware
app.add_middleware(BaseHTTPMiddleware, dispatch=_log_request_middleware)

from ultron.api.routes.chat import router as chat_router
from ultron.api.routes.agents import router as agents_router
from ultron.api.routes.status import router as status_router
from ultron.api.routes.training import router as training_router
from ultron.api.routes.conversations import router as conversations_router

app.include_router(chat_router)
app.include_router(agents_router)
app.include_router(status_router)
app.include_router(training_router)
app.include_router(conversations_router)

# Workspace models — needed for endpoint type hints
from ultron.v2.workspace.models import CloneRequest, GenerateRequest, SynthesizeRequest

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
    """Health check endpoint for startup scripts and load balancers."""
    uptime = time.time() - START_TIME
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok" if _orchestrator else "degraded",
            "version": "2.1.0",
            "uptime_seconds": round(uptime, 1),
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
            
        agent = _orchestrator.agents.get(AgentRole.OPENGUIDER_BRIDGE)
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
# TTS Endpoint — Text-to-Speech via edge-tts
# ──────────────────────────────────────────────────────────────────────

@app.post("/api/v2/tts")
@limiter.limit("60/minute")
async def text_to_speech(req: TTSRequest, request: Request):
    """Convert text to speech. Returns audio stream. Uses VoiceBox with EdgeTTS fallback."""
    try:
        import httpx
        import io

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
                    return StreamingResponse(
                        io.BytesIO(resp.content),
                        media_type="audio/mpeg",
                        headers={
                            "Content-Disposition": 'inline; filename="tts.mp3"',
                            "X-TTS-Engine": "VoiceBox",
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
        # Auto-select voice based on language
        voice = req.voice
        if not voice:
            if req.language == "tr":
                voice = "tr-TR-EmelNeural"
            else:
                voice = "en-US-JennyNeural"

        # Stream audio chunks directly
        communicate = edge_tts.Communicate(req.text, voice)

        async def audio_stream():
            """Async generator that yields audio chunks as they arrive."""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        return StreamingResponse(
            audio_stream(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": 'inline; filename="tts.mp3"',
                "X-Voice": voice,
                "X-TTS-Engine": "EdgeTTS"
            }
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

async def get_orchestrator():
    return _orchestrator

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ultron.api.main:app", host="0.0.0.0", port=8000, reload=True,
                reload_excludes=["workspace/*", "data/*", ".venv/*"])
