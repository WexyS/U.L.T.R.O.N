"""Meeting Transcription Agent — Whisper ile canlı transkripsiyon + aksiyon çıkarma."""

from __future__ import annotations

import asyncio
import logging
import os
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional

from ultron.agents.base import Agent
from ultron.core.types import AgentRole, Task, TaskResult, TaskStatus
from ultron.core.event_bus import EventBus
from ultron.core.blackboard import Blackboard
from ultron.core.llm_router import LLMRouter

logger = logging.getLogger("ultron.agents.meeting_agent")

# Default directory for saved meetings
MEETINGS_DIR = Path("data") / "meetings"


class MeetingAgent(Agent):
    agent_name = "MeetingAgent"
    agent_description = "Meeting Agent — ses kaydını alır, Whisper ile transkribe eder,"

    """Meeting Agent — ses kaydını alır, Whisper ile transkribe eder,
    özet ve aksiyon maddeleri üretir."""

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
        system_prompt: Optional[str] = None,
        whisper_model: str = "base",
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        super().__init__(
            role=AgentRole.MEETING,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
            system_prompt=system_prompt,
        )
        self._whisper_model: str = whisper_model
        self._sample_rate: int = sample_rate
        self._channels: int = channels

        # State
        self._recording: bool = False
        self._audio_chunks: list[bytes] = []
        self._full_transcript: str = ""
        self._meeting_title: str = ""
        self._stream: object | None = None  # sounddevice.InputStream
        self._meeting_start_time: datetime | None = None

    # ── system prompt ──────────────────────────────────────────────────

    def _default_system_prompt(self) -> str:
        return (
            "You are Ultron Meeting Agent. "
            "You transcribe meetings using Whisper, generate concise summaries, "
            "and extract actionable items with assignees and deadlines when possible. "
            "Always respond in a structured markdown format."
        )

    # ── abstract / overrides ───────────────────────────────────────────

    async def _subscribe_events(self) -> None:
        self.event_bus.subscribe("meeting.start", self._on_meeting_start)
        self.event_bus.subscribe("meeting.stop", self._on_meeting_stop)
        self.event_bus.subscribe("meeting.summary_request", self._on_summary_request)
        logger.info("MeetingAgent subscribed to meeting events")

    async def execute(self, task: Task) -> TaskResult:
        """Execute a meeting-related task routed by intent."""
        self.state.status = AgentStatus.BUSY
        intent = task.intent.lower().strip()
        context = task.context

        try:
            handler_map = {
                "start": self._handle_start,
                "record": self._handle_start,
                "stop": self._handle_stop,
                "summary": self._handle_summary,
                "save": self._handle_save,
                "transcribe": self._handle_transcribe_file,
            }

            handler = handler_map.get(intent)
            if handler is None:
                return TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    error=f"Unknown meeting intent: {intent}",
                    metadata={"intent": intent},
                )

            result_text = await handler(context)

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.SUCCESS,
                output=result_text,
                metadata={"intent": intent},
            )

        except Exception as exc:
            logger.exception("MeetingAgent execute failed")
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(exc),
                metadata={"intent": intent},
            )
        finally:
            self.state.status = AgentStatus.IDLE

    # ── intent handlers ────────────────────────────────────────────────

    async def _handle_start(self, context: dict) -> str:
        """Start recording audio."""
        if self._recording:
            return "Already recording. Stop the current recording first."

        self._meeting_title = context.get("title", self._generate_title())
        await self.start_recording()
        await self._publish_event("meeting.recording_started", {"title": self._meeting_title})
        return f"Recording started: {self._meeting_title}"

    async def _handle_stop(self, context: dict) -> str:
        """Stop recording and transcribe."""
        if not self._recording:
            return "No active recording to stop."

        audio_path, transcript = await self.stop_recording()
        self._full_transcript = transcript

        await self._publish_event(
            "meeting.recording_stopped",
            {"transcript_length": len(transcript), "audio_path": str(audio_path)},
        )
        return (
            f"Recording stopped.\n"
            f"Audio saved to: {audio_path}\n"
            f"Transcript ({len(transcript)} chars):\n{transcript[:500]}..."
        )

    async def _handle_summary(self, context: dict) -> str:
        """Generate summary from transcript."""
        if not self._full_transcript:
            return "No transcript available. Record a meeting first."

        summary = await self.generate_summary(self._full_transcript)
        await self._publish_event("meeting.summary_generated", {"summary": summary})
        return summary

    async def _handle_save(self, context: dict) -> str:
        """Save meeting notes to disk."""
        if not self._full_transcript:
            return "No transcript to save. Record a meeting first."

        path = await self.save_meeting(self._full_transcript, context.get("summary", ""))
        await self._publish_event("meeting.saved", {"path": str(path)})
        return f"Meeting saved to: {path}"

    async def _handle_transcribe_file(self, context: dict) -> str:
        """Transcribe an existing audio file."""
        audio_path = context.get("audio_path")
        if not audio_path:
            return "No audio_path provided in context."

        path = Path(audio_path)
        if not path.exists():
            return f"Audio file not found: {audio_path}"

        transcript = await self.transcribe(path)
        self._full_transcript = transcript
        await self._publish_event("meeting.file_transcribed", {"path": str(path)})
        return transcript

    # ── recording ──────────────────────────────────────────────────────

    async def start_recording(self) -> None:
        """Start capturing audio from the default microphone."""
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            raise RuntimeError(
                "sounddevice and numpy are required for recording. "
                "Install them with: pip install sounddevice numpy",
            )

        self._recording = True
        self._audio_chunks = []
        self._full_transcript = ""
        self._meeting_start_time = datetime.now()
        logger.info("Starting recording (sr=%d, ch=%d)", self._sample_rate, self._channels)

        def audio_callback(indata, frames, time_info, status) -> None:
            """Callback fired by sounddevice for each audio chunk."""
            if status:
                logger.warning("Stream status: %s", status)
            if self._recording:
                # Convert float32 to int16 bytes
                samples = (indata * 32767).astype(np.int16)
                self._audio_chunks.append(samples.tobytes())

        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                callback=audio_callback,
            )
            self._stream.start()
        except Exception as exc:
            self._recording = False
            raise RuntimeError(f"Failed to start audio stream: {exc}") from exc

    async def stop_recording(self) -> tuple[Path, str]:
        """Stop recording, save WAV, and transcribe."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:
                logger.warning("Error closing audio stream: %s", exc)
            self._stream = None

        self._recording = False

        if not self._audio_chunks:
            raise RuntimeError("No audio data captured.")

        # Save raw chunks as WAV
        audio_path = MEETINGS_DIR / f"{self._meeting_title.replace(' ', '_')}.wav"
        await asyncio.to_thread(self._save_wav, audio_path)

        # Transcribe
        transcript = await self.transcribe(audio_path)
        logger.info("Transcription complete (%d chars)", len(transcript))
        return audio_path, transcript

    def _save_wav(self, path: Path) -> None:
        """Write accumulated audio chunks to a WAV file (sync)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        audio_data = b"".join(self._audio_chunks)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(self._channels)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(self._sample_rate)
            wf.writeframes(audio_data)
        logger.info("WAV saved: %s (%d bytes)", path, len(audio_data))

    # ── transcription ──────────────────────────────────────────────────

    async def transcribe(self, audio_path: Path) -> str:
        """Transcribe a WAV file using OpenAI Whisper."""
        try:
            import whisper
        except ImportError:
            raise RuntimeError(
                "openai-whisper is required for transcription. "
                "Install it with: pip install openai-whisper",
            )

        loop = asyncio.get_event_loop()

        def _transcribe() -> str:
            model = whisper.load_model(self._whisper_model)
            result = model.transcribe(str(audio_path), language="tr")
            return result.get("text", "").strip()

        try:
            transcript = await loop.run_in_executor(None, _transcribe)
        except Exception as exc:
            logger.exception("Whisper transcription failed")
            raise RuntimeError(f"Transcription failed: {exc}") from exc

        return transcript

    # ── summary generation ─────────────────────────────────────────────

    async def generate_summary(self, transcript: str) -> str:
        """Use LLM to summarise transcript and extract action items."""
        messages = self._build_messages(
            user_content=(
                "You are a professional meeting summarizer. Analyze the following meeting "
                "transcript and produce a structured summary.\n\n"
                "Include these sections:\n"
                "1. **Meeting Overview** — brief description of what was discussed\n"
                "2. **Key Points** — bullet list of main discussion topics\n"
                "3. **Decisions Made** — any decisions or conclusions\n"
                "4. **Action Items** — table with columns: Task | Assignee | Deadline\n"
                "5. **Follow-up** — items that need further discussion\n\n"
                f"Transcript:\n{transcript}"
            ),
        )

        response = await self._llm_chat(messages, temperature=0.3, max_tokens=2048)
        return response.content

    # ── saving ─────────────────────────────────────────────────────────

    async def save_meeting(
        self,
        transcript: str,
        summary: str = "",
    ) -> Path:
        """Save meeting transcript and summary as a markdown file."""
        MEETINGS_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = self._meeting_start_time or datetime.now()
        filename = timestamp.strftime("%Y-%m-%d_%H-%M.md")
        filepath = MEETINGS_DIR / filename

        title = self._meeting_title or "Untitled Meeting"
        duration = ""
        if self._meeting_start_time:
            delta = datetime.now() - self._meeting_start_time
            mins, secs = divmod(int(delta.total_seconds()), 60)
            duration = f"{mins}m {secs}s"

        content = (
            f"# {title}\n\n"
            f"**Date:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Duration:** {duration}\n\n"
            f"---\n\n"
            f"## Summary\n\n{summary or '*No summary generated.*'}\n\n"
            f"---\n\n"
            f"## Full Transcript\n\n{transcript}\n"
        )

        def _write() -> None:
            filepath.write_text(content, encoding="utf-8")

        await asyncio.to_thread(_write)
        logger.info("Meeting saved: %s", filepath)
        return filepath

    # ── event handlers ─────────────────────────────────────────────────

    async def _on_meeting_start(self, event) -> None:
        """Handle meeting start event."""
        try:
            title = event.data.get("title", "")
            ctx = {"title": title} if title else {}
            await self._handle_start(ctx)
        except Exception as exc:
            logger.error("Error on meeting.start: %s", exc)
            await self._publish_event("meeting.error", {"error": str(exc)})

    async def _on_meeting_stop(self, event) -> None:
        """Handle meeting stop event."""
        try:
            await self._handle_stop({})
        except Exception as exc:
            logger.error("Error on meeting.stop: %s", exc)
            await self._publish_event("meeting.error", {"error": str(exc)})

    async def _on_summary_request(self, event) -> None:
        """Handle summary request event."""
        try:
            if self._full_transcript:
                summary = await self.generate_summary(self._full_transcript)
                await self._publish_event("meeting.summary_result", {"summary": summary})
            else:
                await self._publish_event(
                    "meeting.summary_error",
                    {"error": "No transcript available"},
                )
        except Exception as exc:
            logger.error("Error on meeting.summary_request: %s", exc)
            await self._publish_event("meeting.summary_error", {"error": str(exc)})

    # ── helpers ────────────────────────────────────────────────────────

    def _generate_title(self) -> str:
        """Generate a title based on the current time."""
        now = datetime.now()
        return f"Meeting {now.strftime('%Y-%m-%d %H:%M')}"
