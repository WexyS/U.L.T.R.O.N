"""Clipboard Agent — Panodaki içeriği anlar ve işler."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from ultron.agents.base import Agent
from ultron.core.types import AgentRole, Task, TaskResult, TaskStatus
from ultron.core.event_bus import EventBus
from ultron.core.blackboard import Blackboard
from ultron.core.llm_router import LLMRouter

logger = logging.getLogger("ultron.agents.clipboard_agent")

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"]+|www\.[^\s<>\"]+",
)

CODE_KEYWORDS = {
    "def ", "async def ", "function ", "import ", "from ", "class ",
    "const ", "let ", "var ", "fn ", "pub fn ", "impl ", "struct ",
    "interface ", "type ", "package ", "func ", "return ", "lambda ",
    "#include", "#include <", "#include \"", "using namespace",
    "<?php", "<script", "<style", "defmain(", "SELECT ", "CREATE TABLE",
}


class ClipboardAgent(Agent):
    agent_name = "ClipboardAgent"
    agent_description = "Clipboard Agent — panodaki içeriği otomatik algılar, özetler, çevirir,"

    """Clipboard Agent — panodaki içeriği otomatik algılar, özetler, çevirir,
    kod analizi yapar ve URL içeriklerini getirir."""

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            role=AgentRole.CLIPBOARD,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
            system_prompt=system_prompt,
        )
        self._supported_intents = {
            "summarize",
            "translate",
            "analyze_code",
            "fetch_url",
            "explain",
            "reformat",
        }

    # ── system prompt ──────────────────────────────────────────────────

    def _default_system_prompt(self) -> str:
        return (
            "You are Ultron Clipboard Agent. "
            "You analyse clipboard content — URLs, code snippets, or plain text — "
            "and respond concisely. Always detect the content type first. "
            "If the content is code, focus on structure, potential bugs, and best practices. "
            "If it is a URL, summarise the page content. "
            "If it is plain text, summarise or translate as requested. "
            "Respond in the same language as the input unless told otherwise."
        )

    # ── abstract / overrides ───────────────────────────────────────────

    async def _subscribe_events(self) -> None:
        self.event_bus.subscribe("clipboard.changed", self._on_clipboard_change)
        self.event_bus.subscribe("clipboard.request_summarize", self._on_request_summarize)
        self.event_bus.subscribe("clipboard.request_translate", self._on_request_translate)
        logger.info("ClipboardAgent subscribed to clipboard events")

    async def execute(self, task: Task) -> TaskResult:
        """Execute a clipboard-related task routed by intent."""
        self.state.status = AgentStatus.BUSY
        intent = task.intent.lower().strip()

        try:
            # Allow explicit content override via context
            content = task.context.get("content") or await self._get_clipboard_content()

            if not content or not content.strip():
                return TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    error="Clipboard is empty.",
                    metadata={"intent": intent},
                )

            content_type = self._detect_content_type(content)
            logger.info(
                "ClipboardAgent: intent=%s type=%s",
                intent,
                content_type,
            )

            # Intent dispatch
            handler_map = {
                "summarize": self._handle_summarize,
                "summary": self._handle_summarize,
                "translate": self._handle_translate,
                "analyze_code": self._handle_analyze_code,
                "code_review": self._handle_analyze_code,
                "fetch_url": self._handle_fetch_url,
                "explain": self._handle_explain,
                "reformat": self._handle_reformat,
            }

            handler = handler_map.get(intent)
            if handler is None:
                # Default: try to infer from content type
                if content_type == "url":
                    handler = self._handle_fetch_url
                elif content_type == "code":
                    handler = self._handle_analyze_code
                else:
                    handler = self._handle_summarize

            result_text = await handler(content, content_type, task.context)

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.SUCCESS,
                output=result_text,
                metadata={
                    "intent": intent,
                    "content_type": content_type,
                },
            )

        except Exception as exc:
            logger.exception("ClipboardAgent execute failed")
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(exc),
                metadata={"intent": intent},
            )
        finally:
            self.state.status = AgentStatus.IDLE

    # ── clipboard helpers ──────────────────────────────────────────────

    async def _get_clipboard_content(self) -> str:
        """Read text from the system clipboard."""
        try:
            import pyperclip
            content = await asyncio.to_thread(pyperclip.paste)
            return content if isinstance(content, str) else str(content)
        except ImportError:
            logger.error("pyperclip is not installed")
            raise RuntimeError(
                "pyperclip package is required for clipboard access. "
                "Install it with: pip install pyperclip",
            )
        except Exception as exc:
            logger.warning("Failed to read clipboard: %s", exc)
            raise

    async def _set_clipboard(self, result: str) -> None:
        """Copy *result* to the system clipboard."""
        try:
            import pyperclip
            await asyncio.to_thread(pyperclip.copy, result)
            logger.info("Result copied to clipboard (%d chars)", len(result))
        except ImportError:
            logger.error("pyperclip is not installed")
        except Exception as exc:
            logger.warning("Failed to write clipboard: %s", exc)

    @staticmethod
    def _detect_content_type(content: str) -> str:
        """Detect whether *content* is a URL, code, or plain text."""
        stripped = content.strip()

        # URL check
        if URL_PATTERN.match(stripped):
            return "url"

        # Short text is unlikely to be code
        if len(stripped) < 20:
            return "text"

        # Code keyword heuristic
        lower = stripped.lower()
        if any(kw.lower() in lower for kw in CODE_KEYWORDS):
            return "code"

        # Indentation / braces heuristic
        if (
            stripped.count("    ") > 2
            or ("{" in stripped and "}" in stripped and ";" in stripped)
            or ("def " in lower and ":" in stripped)
        ):
            return "code"

        return "text"

    # ── intent handlers ────────────────────────────────────────────────

    async def _handle_summarize(
        self,
        content: str,
        content_type: str,
        context: dict,
    ) -> str:
        """Produce a concise summary of the content."""
        if content_type == "url":
            return await self._handle_fetch_url(content, content_type, context)

        target_lang = context.get("language", "same as input")

        messages = self._build_messages(
            user_content=(
                f"Summarize the following content in {target_lang}. "
                f"Provide key points in bullet form if applicable.\n\n"
                f"```\n{content}\n```"
            ),
        )

        response = await self._llm_chat(messages, temperature=0.3, max_tokens=1024)
        summary = response.content
        await self._set_clipboard(summary)
        await self._publish_event("clipboard.summarized", {"summary": summary})
        return summary

    async def _handle_translate(
        self,
        content: str,
        content_type: str,
        context: dict,
    ) -> str:
        """Translate content to the target language."""
        target_lang = context.get("language", "English")

        messages = self._build_messages(
            user_content=(
                f"Translate the following content to {target_lang}. "
                f"Preserve formatting and code blocks if present.\n\n"
                f"```\n{content}\n```"
            ),
        )

        response = await self._llm_chat(messages, temperature=0.2, max_tokens=2048)
        translated = response.content
        await self._set_clipboard(translated)
        await self._publish_event(
            "clipboard.translated",
            {"target_language": target_lang, "translated": translated},
        )
        return translated

    async def _handle_analyze_code(
        self,
        content: str,
        content_type: str,
        context: dict,
    ) -> str:
        """Review code and provide suggestions."""
        messages = self._build_messages(
            user_content=(
                "Review the following code. Provide:\n"
                "1. A brief explanation of what the code does\n"
                "2. Potential bugs or issues\n"
                "3. Performance improvements\n"
                "4. Security concerns\n"
                "5. Best practice recommendations\n\n"
                f"```\n{content}\n```"
            ),
        )

        response = await self._llm_chat(messages, temperature=0.2, max_tokens=2048)
        review = response.content
        await self._set_clipboard(review)
        await self._publish_event("clipboard.code_reviewed", {"review": review})
        return review

    async def _handle_fetch_url(
        self,
        content: str,
        content_type: str,
        context: dict,
    ) -> str:
        """Fetch URL content and summarize it."""
        url = self._extract_url(content)
        if not url:
            return "No valid URL found in clipboard content."

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            import httpx
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Ultron/2.0"
                    ),
                },
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                page_text = resp.text
        except Exception as exc:
            logger.warning("Failed to fetch URL %s: %s", url, exc)
            return f"Failed to fetch URL: {exc}"

        # Strip HTML tags (simple approach)
        page_text = re.sub(r"<[^>]+>", " ", page_text)
        page_text = re.sub(r"\s+", " ", page_text).strip()
        page_text = page_text[:8000]  # truncate to avoid token overflow

        messages = self._build_messages(
            user_content=(
                f"Summarize the following web page content from {url}:\n\n"
                f"{page_text}"
            ),
        )

        response = await self._llm_chat(messages, temperature=0.3, max_tokens=1024)
        summary = response.content
        await self._set_clipboard(summary)
        await self._publish_event("clipboard.url_fetched", {"url": url, "summary": summary})
        return summary

    async def _handle_explain(
        self,
        content: str,
        content_type: str,
        context: dict,
    ) -> str:
        """Explain the content in simple terms."""
        messages = self._build_messages(
            user_content=(
                "Explain the following content in simple, clear terms. "
                "If it's code, explain line by line. "
                "If it's text, explain the main concepts.\n\n"
                f"```\n{content}\n```"
            ),
        )

        response = await self._llm_chat(messages, temperature=0.2, max_tokens=2048)
        explanation = response.content
        await self._set_clipboard(explanation)
        await self._publish_event("clipboard.explained", {"explanation": explanation})
        return explanation

    async def _handle_reformat(
        self,
        content: str,
        content_type: str,
        context: dict,
    ) -> str:
        """Reformat content (e.g., code formatting, text restructuring)."""
        messages = self._build_messages(
            user_content=(
                "Reformat the following content. Improve readability, "
                "fix indentation, and follow standard conventions.\n\n"
                f"```\n{content}\n```"
            ),
        )

        response = await self._llm_chat(messages, temperature=0.1, max_tokens=2048)
        reformatted = response.content
        await self._set_clipboard(reformatted)
        await self._publish_event("clipboard.reformatted", {"reformatted": reformatted})
        return reformatted

    # ── event handlers ─────────────────────────────────────────────────

    async def _on_clipboard_change(self, event) -> None:
        """Handle clipboard change notification."""
        try:
            content = event.data.get("content", "")
            if content:
                content_type = self._detect_content_type(content)
                await self.store_context(
                    f"clipboard.last_{content_type}",
                    content,
                    ttl=300,
                )
                logger.info("Clipboard content detected as %s", content_type)
        except Exception as exc:
            logger.error("Error handling clipboard change: %s", exc)

    async def _on_request_summarize(self, event) -> None:
        """Handle summarize request event."""
        try:
            content = event.data.get("content") or await self._get_clipboard_content()
            if content:
                result = await self._handle_summarize(content, self._detect_content_type(content), {})
                await self._publish_event("clipboard.summarize_result", {"result": result})
        except Exception as exc:
            logger.error("Error handling summarize request: %s", exc)
            await self._publish_event("clipboard.summarize_error", {"error": str(exc)})

    async def _on_request_translate(self, event) -> None:
        """Handle translate request event."""
        try:
            content = event.data.get("content") or await self._get_clipboard_content()
            language = event.data.get("language", "English")
            if content:
                result = await self._handle_translate(
                    content,
                    self._detect_content_type(content),
                    {"language": language},
                )
                await self._publish_event("clipboard.translate_result", {"result": result})
        except Exception as exc:
            logger.error("Error handling translate request: %s", exc)
            await self._publish_event("clipboard.translate_error", {"error": str(exc)})

    # ── static helpers ─────────────────────────────────────────────────

    @staticmethod
    def _extract_url(text: str) -> str:
        """Extract the first URL from *text*."""
        match = URL_PATTERN.search(text)
        if match:
            return match.group(0).strip()
        return ""
