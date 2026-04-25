"""Ultron Genesis — FastAPI Backend Bridge."""
from __future__ import annotations
import asyncio
import logging
import os
import time
import warnings
import hashlib
import io
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Suppress verbose warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="torch.*|websockets.*|uvicorn.*")
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

START_TIME = time.time()
_orchestrator = None
_tts_cache = {}

# Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ultron.api")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator
    logger.info("=" * 60)
    logger.info("ULTRON GENESIS API — Starting...")
    logger.info("=" * 60)
    
    load_dotenv()
    try:
        from ultron.core.llm_router import LLMRouter
        from ultron.memory.engine import MemoryEngine
        from ultron.core.orchestrator import Orchestrator
        from ultron.core.agent_registry import registry
        from ultron.core.react_orchestrator import ReActOrchestrator
        from ultron.core.event_bus import EventBus
        from ultron.core.blackboard import Blackboard
        import ultron.agents as agents_pkg

        # 1. Initialize Resources
        from ultron.core.llm_router import router as llm
        from ultron.core.event_bus import event_bus
        from ultron.core.blackboard import blackboard
        
        memory = MemoryEngine(persist_dir="./data/ultron_memory")

        # 2. Legacy Support (Orchestrator v2)
        _orchestrator = Orchestrator(llm_router=llm, memory=memory, work_dir="./workspace")
        await _orchestrator.start()

        # 3. Genesis Core (v3)
        registry.set_factory_provider("llm_router", llm)
        registry.set_factory_provider("event_bus", event_bus)
        registry.set_factory_provider("blackboard", blackboard)

        if not registry.get_agent("ReActOrchestrator"):
            registry.register(ReActOrchestrator(memory=memory))
            
        registered_count = 0
        for attr_name in agents_pkg.__all__:
            if attr_name in ("Agent", "BaseAgent"): continue
            try:
                agent_cls = getattr(agents_pkg, attr_name)
                desc = getattr(agent_cls, "agent_description", "Specialized Genesis Agent")
                registry.register_lazy(attr_name, desc, agent_cls)
                registered_count += 1
            except Exception as reg_e:
                logger.warning(f"Failed to register agent {attr_name}: {reg_e}")

        logger.info(f"[GENESIS] System Online. {registered_count} agents registered.")

        # 4. Background Services
        if os.getenv("ULTRON_EVOLUTION_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on"):
            interval = int(os.getenv("ULTRON_EVOLUTION_INTERVAL_MINUTES", "10"))
            from ultron.core.eternal_evolution import EternalEvolutionEngine
            evolution_daemon = EternalEvolutionEngine(sleep_interval_minutes=interval)
            
            async def delayed_start():
                await asyncio.sleep(5)
                await evolution_daemon.start_loop()
            
            asyncio.create_task(delayed_start())
            logger.info(f"[GENESIS] Eternal Evolution active (interval={interval}m).")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        _orchestrator = None

    yield
    logger.info("Ultron Genesis shutting down...")
    if _orchestrator:
        await _orchestrator.stop()

app = FastAPI(title="Ultron Genesis API", version="3.0.0", lifespan=lifespan)

# CORS
allowed_origins = os.getenv(
    "ULTRON_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"
).split(",")
ngrok_url = os.getenv("NGROK_URL", "").strip()
if ngrok_url:
    allowed_origins.extend([ngrok_url.rstrip("/"), ngrok_url.rstrip("/").replace("https://", "http://")])

app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RequestIDMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

async def _log_request_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration_ms:.2f}ms")
    return response

app.add_middleware(BaseHTTPMiddleware, dispatch=_log_request_middleware)

# Auth
ULTRON_API_KEY = os.getenv("ULTRON_API_KEY")
async def verify_api_key(request: Request):
    if not ULTRON_API_KEY: return
    api_key = request.headers.get("X-API-Key")
    import hmac
    if not api_key or not hmac.compare_digest(api_key, ULTRON_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API Key")

# Routes
from ultron.api.routes.chat import router as chat_router
from ultron.api.routes.agents import router as agents_router
from ultron.api.routes.status import router as status_router
from ultron.api.routes.training import router as training_router
from ultron.api.routes.conversations import router as conversations_router
from ultron.api.routes.composer import router as composer_router
from ultron.api.routes.voice import router as voice_router
from ultron.api.routes.v3_chat import router as v3_router

app.include_router(chat_router)
app.include_router(agents_router)
app.include_router(status_router)
app.include_router(training_router)
app.include_router(conversations_router)
app.include_router(composer_router)
app.include_router(voice_router)
app.include_router(v3_router)

@app.get("/")
async def root():
    return {"name": "Ultron Genesis API", "version": "3.0.0", "status": "active"}

@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    return {"status": "healthy", "uptime": round(time.time() - START_TIME, 1)}

# Unified TTS (EdgeTTS)
class TTSRequest(BaseModel):
    text: str
    language: str = "tr"
    voice: Optional[str] = None

@app.post("/api/v3/tts")
@app.post("/api/v2/tts")
@limiter.limit("60/minute")
async def text_to_speech(req: TTSRequest, request: Request):
    """Modern TTS with high-quality natural voices and caching."""
    try:
        import edge_tts
        voice = req.voice or ("tr-TR-AhmetNeural" if req.language == "tr" else "en-US-ChristopherNeural")
        
        # Ultron Tuning
        rate = "-5%"
        pitch = "-25Hz"
        
        cache_key = hashlib.md5(f"{req.text}:{voice}".encode()).hexdigest()
        if cache_key in _tts_cache:
            return StreamingResponse(io.BytesIO(_tts_cache[cache_key]), media_type="audio/mpeg", headers={"X-Cache": "HIT"})

        communicate = edge_tts.Communicate(req.text, voice, rate=rate, pitch=pitch)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": audio_bytes += chunk["data"]
        
        if len(_tts_cache) > 200: _tts_cache.pop(next(iter(_tts_cache)))
        _tts_cache[cache_key] = audio_bytes

        return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg", headers={"X-Voice": voice, "X-Engine": "EdgeTTS"})
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ultron.api.main:app", host="0.0.0.0", port=8000, reload=True,
                reload_excludes=["workspace/*", "data/*", ".venv/*"])
