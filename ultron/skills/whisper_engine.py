import whisper
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("ultron.skills.whisper")

class WhisperManager:
    """Singleton Whisper Manager to avoid redundant model loading."""
    _instance = None
    _model = None
    _executor = ThreadPoolExecutor(max_workers=1)

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(WhisperManager, cls).__new__(cls)
        return cls._instance

    def load_model(self, model_name: str = "base"):
        """Load the model if not already loaded."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {model_name}...")
            self._model = whisper.load_model(model_name)
            logger.info("Whisper model loaded successfully.")

    async def transcribe(self, audio_path: str, language: str = "tr") -> str:
        """Transcribe audio file asynchronously."""
        if self._model is None:
            self.load_model()

        loop = asyncio.get_event_loop()
        # Transcribe in a thread pool to avoid blocking the event loop
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._model.transcribe(audio_path, language=language)
        )
        return result.get("text", "").strip()

# Global instance
whisper_engine = WhisperManager()
