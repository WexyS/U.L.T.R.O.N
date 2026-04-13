"""File Organizer Agent — Akıllı dosya yönetimi."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, Task, TaskResult, TaskStatus
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter

logger = logging.getLogger("ultron.v2.agents.files_agent")

# Extension → category mapping
EXTENSION_MAP: dict[str, str] = {
    # Documents
    ".pdf": "document",
    ".doc": "document",
    ".docx": "document",
    ".txt": "document",
    ".rtf": "document",
    ".odt": "document",
    ".md": "document",
    ".tex": "document",
    ".pages": "document",
    # Images
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".bmp": "image",
    ".svg": "image",
    ".webp": "image",
    ".tiff": "image",
    ".ico": "image",
    ".raw": "image",
    # Code
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".jsx": "code",
    ".tsx": "code",
    ".java": "code",
    ".c": "code",
    ".cpp": "code",
    ".h": "code",
    ".hpp": "code",
    ".cs": "code",
    ".go": "code",
    ".rs": "code",
    ".rb": "code",
    ".php": "code",
    ".swift": "code",
    ".kt": "code",
    ".sh": "code",
    ".bash": "code",
    ".zsh": "code",
    ".ps1": "code",
    ".bat": "code",
    ".cmd": "code",
    ".html": "code",
    ".css": "code",
    ".scss": "code",
    ".sql": "code",
    ".json": "code",
    ".xml": "code",
    ".yaml": "code",
    ".yml": "code",
    ".toml": "code",
    ".ini": "code",
    ".cfg": "code",
    ".conf": "code",
    ".ipynb": "code",
    ".dart": "code",
    ".lua": "code",
    ".r": "code",
    ".m": "code",
    # Archives
    ".zip": "archive",
    ".rar": "archive",
    ".7z": "archive",
    ".tar": "archive",
    ".gz": "archive",
    ".bz2": "archive",
    ".xz": "archive",
    ".tar.gz": "archive",
    ".tgz": "archive",
    # Media
    ".mp3": "media",
    ".wav": "media",
    ".flac": "media",
    ".aac": "media",
    ".ogg": "media",
    ".wma": "media",
    ".mp4": "media",
    ".avi": "media",
    ".mkv": "media",
    ".mov": "media",
    ".wmv": "media",
    ".flv": "media",
    ".webm": "media",
    # Spreadsheets
    ".xls": "spreadsheet",
    ".xlsx": "spreadsheet",
    ".csv": "spreadsheet",
    ".ods": "spreadsheet",
    ".numbers": "spreadsheet",
}


class FileOrganizerHandler:
    """Watchdog event handler that auto-classifies new files."""

    def __init__(self, files_agent: "FilesAgent") -> None:
        self._agent = files_agent

    def on_created(self, event) -> None:
        """Handle file creation event."""
        if event.is_directory:
            return
        try:
            path = Path(event.src_path)
            category = self._agent._classify_file(path)
            logger.info(
                "Watchdog: new file %s → category %s",
                path.name,
                category,
            )
            # Fire-and-forget: schedule async on event loop
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.create_task(
                self._agent._publish_event(
                    "file.detected",
                    {"path": str(path), "category": category},
                ),
            )
        except Exception as exc:
            logger.error("Watchdog on_created error: %s", exc)

    def on_moved(self, event) -> None:
        """Handle file move event."""
        if event.is_directory:
            return
        logger.info("Watchdog: file moved %s → %s", event.src_path, event.dest_path)

    def on_deleted(self, event) -> None:
        """Handle file deletion event."""
        if event.is_directory:
            return
        logger.info("Watchdog: file deleted %s", event.src_path)


class FilesAgent(Agent):
    """Files Agent — akıllı dosya organizasyonu, duplicate tespiti ve
    dizin izleme."""

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            role=AgentRole.FILES,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
            system_prompt=system_prompt,
        )
        self._observer: object | None = None
        self._watching: bool = False
        self._watched_paths: list[Path] = []

    # ── system prompt ──────────────────────────────────────────────────

    def _default_system_prompt(self) -> str:
        return (
            "You are Ultron File Organizer Agent. "
            "You help organize files by classifying them into categories, "
            "detecting duplicates, and maintaining clean directory structures. "
            "Always operate safely — never delete files, only move them. "
            "Provide clear reports of all actions taken."
        )

    # ── abstract / overrides ───────────────────────────────────────────

    async def _subscribe_events(self) -> None:
        self.event_bus.subscribe("file.organize_request", self._on_organize_request)
        self.event_bus.subscribe("file.duplicates_request", self._on_duplicates_request)
        self.event_bus.subscribe("file.cleanup_request", self._on_cleanup_request)
        logger.info("FilesAgent subscribed to file events")

    async def execute(self, task: Task) -> TaskResult:
        """Execute a file-related task routed by intent."""
        self.state.status = AgentStatus.BUSY
        intent = task.intent.lower().strip()
        context = task.context

        try:
            handler_map = {
                "organize": self._handle_organize,
                "duplicates": self._handle_duplicates,
                "watch": self._handle_watch,
                "stop_watch": self._handle_stop_watch,
                "cleanup": self._handle_cleanup,
                "classify": self._handle_classify,
                "search": self._handle_search,
            }

            handler = handler_map.get(intent)
            if handler is None:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=f"Unknown file intent: {intent}",
                    metadata={"intent": intent},
                )

            result_text = await handler(context)

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output=result_text,
                metadata={"intent": intent},
            )

        except Exception as exc:
            logger.exception("FilesAgent execute failed")
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(exc),
                metadata={"intent": intent},
            )
        finally:
            self.state.status = AgentStatus.IDLE

    # ── intent handlers ────────────────────────────────────────────────

    async def _handle_organize(self, context: dict) -> str:
        """Organize a directory by categorizing files into subfolders."""
        path_str = context.get("path", ".")
        path = Path(path_str).resolve()
        if not path.exists():
            return f"Path does not exist: {path}"
        if not path.is_dir():
            return f"Path is not a directory: {path}"

        report = await self.organize_directory(path)
        return report

    async def _handle_duplicates(self, context: dict) -> str:
        """Find duplicate files in a directory."""
        path_str = context.get("path", ".")
        path = Path(path_str).resolve()
        if not path.exists():
            return f"Path does not exist: {path}"
        if not path.is_dir():
            return f"Path is not a directory: {path}"

        report = await self.find_duplicates(path)
        return report

    async def _handle_watch(self, context: dict) -> str:
        """Start watching a directory for new files."""
        path_str = context.get("path", ".")
        path = Path(path_str).resolve()
        if not path.exists():
            return f"Path does not exist: {path}"

        await self.start_watching(path)
        return f"Watching directory: {path}"

    async def _handle_stop_watch(self, context: dict) -> str:
        """Stop watching directories."""
        await self.stop_watching()
        return "File watching stopped."

    async def _handle_cleanup(self, context: dict) -> str:
        """Clean up and organize the Desktop directory."""
        report = await self.cleanup_desktop()
        return report

    async def _handle_classify(self, context: dict) -> str:
        """Classify a single file."""
        file_path = context.get("file_path")
        if not file_path:
            return "No file_path provided in context."

        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"

        category = self._classify_file(path)
        content_preview = ""
        try:
            content_preview = await self._read_file_content(path)
            content_preview = content_preview[:200]
        except Exception:
            content_preview = "(could not read content)"

        return f"File: {path.name}\nCategory: {category}\nPreview: {content_preview}"

    async def _handle_search(self, context: dict) -> str:
        """Search for files by name or extension in a directory."""
        path_str = context.get("path", ".")
        query = context.get("query", "")
        path = Path(path_str).resolve()

        if not path.exists():
            return f"Path does not exist: {path}"

        results: list[str] = []
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if query.lower() in fname.lower():
                    results.append(os.path.join(root, fname))

        if not results:
            return f"No files matching '{query}' found in {path}"

        report = f"Found {len(results)} file(s) matching '{query}':\n"
        for r in results[:50]:
            report += f"  - {r}\n"
        if len(results) > 50:
            report += f"  ... and {len(results) - 50} more\n"
        return report

    # ── file classification ────────────────────────────────────────────

    def _classify_file(self, file_path: Path) -> str:
        """Classify a file based on its extension."""
        ext = file_path.suffix.lower()

        # Handle compound extensions like .tar.gz
        if ext == ".gz":
            stem = file_path.stem.lower()
            if stem.endswith(".tar"):
                return "archive"

        return EXTENSION_MAP.get(ext, "other")

    async def _read_file_content(self, file_path: Path) -> str:
        """Read file content — text files directly, PDFs/images with OCR."""
        ext = file_path.suffix.lower()

        # Text-based files
        text_extensions = {
            ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
            ".xml", ".html", ".css", ".csv", ".sh", ".bash", ".bat", ".cmd",
            ".ini", ".cfg", ".conf", ".toml", ".sql", ".log", ".rst",
            ".c", ".cpp", ".h", ".hpp", ".java", ".cs", ".go", ".rs", ".rb",
            ".php", ".swift", ".kt", ".dart", ".lua", ".r",
        }
        if ext in text_extensions:
            return await asyncio.to_thread(self._read_text_file, file_path)

        # PDF
        if ext == ".pdf":
            return await self._read_pdf(file_path)

        # Images
        image_extensions = {
            ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp",
        }
        if ext in image_extensions:
            return await self._read_image(file_path)

        return "(binary file — content preview not available)"

    @staticmethod
    def _read_text_file(file_path: Path) -> str:
        """Read a text file."""
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Could not read text file %s: %s", file_path, exc)
            return f"(read error: {exc})"

    async def _read_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using available libraries."""
        # Try PyMuPDF first
        try:
            import fitz  # PyMuPDF
            def _extract() -> str:
                doc = fitz.open(str(file_path))
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())
                doc.close()
                return "\n".join(text_parts)
            return await asyncio.to_thread(_extract)
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("PyMuPDF failed for %s: %s", file_path, exc)

        # Try pdfplumber
        try:
            import pdfplumber
            def _extract() -> str:
                text_parts = []
                with pdfplumber.open(str(file_path)) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text_parts.append(t)
                return "\n".join(text_parts)
            return await asyncio.to_thread(_extract)
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("pdfplumber failed for %s: %s", file_path, exc)

        # Try easyocr as last resort
        try:
            import easyocr
            from PIL import Image
            import io

            def _ocr() -> str:
                reader = easyocr.Reader(["en", "tr"], gpu=False)
                # Render first page as image
                import fitz
                doc = fitz.open(str(file_path))
                page = doc[0]
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                doc.close()

                result = reader.readtext(img_data)
                return " ".join([text for _, text, _ in result])

            return await asyncio.to_thread(_ocr)
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("easyocr failed for %s: %s", file_path, exc)

        return "(could not extract PDF text — no suitable library available)"

    async def _read_image(self, file_path: Path) -> str:
        """Extract text from image using OCR."""
        try:
            import easyocr
            reader = easyocr.Reader(["en", "tr"], gpu=False)

            def _ocr() -> str:
                result = reader.readtext(str(file_path))
                return " ".join([text for _, text, _ in result])

            return await asyncio.to_thread(_ocr)
        except ImportError:
            return "(easyocr not installed — cannot perform OCR)"
        except Exception as exc:
            logger.warning("OCR failed for %s: %s", file_path, exc)
            return f"(OCR error: {exc})"

    # ── organize ───────────────────────────────────────────────────────

    async def organize_directory(self, path: Path) -> str:
        """Scan directory, create subfolders by category, move files."""
        moved: dict[str, list[str]] = defaultdict(list)
        errors: list[str] = []

        # Collect all files (non-recursive for safety, only top-level)
        files_to_process = []
        for item in path.iterdir():
            if item.is_file() and not item.name.startswith("."):
                files_to_process.append(item)

        for file_path in files_to_process:
            try:
                category = self._classify_file(file_path)
                category_dir = path / category
                category_dir.mkdir(exist_ok=True)

                dest = category_dir / file_path.name

                # Handle name collisions
                if dest.exists():
                    stem = file_path.stem
                    suffix = file_path.suffix
                    counter = 1
                    while dest.exists():
                        dest = category_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                await asyncio.to_thread(shutil.move, str(file_path), str(dest))
                moved[category].append(dest.name)
                logger.info("Moved %s → %s/", file_path.name, category)
            except Exception as exc:
                errors.append(f"{file_path.name}: {exc}")
                logger.warning("Failed to move %s: %s", file_path.name, exc)

        # Build report
        report_lines = [f"Organized: {path}", ""]
        total_moved = 0
        for category, files in sorted(moved.items()):
            report_lines.append(f"  {category}/ ({len(files)} files)")
            for f in files[:10]:
                report_lines.append(f"    - {f}")
            if len(files) > 10:
                report_lines.append(f"    ... and {len(files) - 10} more")
            total_moved += len(files)

        report_lines.append(f"\nTotal moved: {total_moved}")
        if errors:
            report_lines.append(f"\nErrors ({len(errors)}):")
            for e in errors[:10]:
                report_lines.append(f"  - {e}")

        await self._publish_event("file.organized", {
            "path": str(path),
            "total_moved": total_moved,
            "categories": list(moved.keys()),
        })

        return "\n".join(report_lines)

    # ── duplicates ─────────────────────────────────────────────────────

    async def find_duplicates(self, path: Path) -> str:
        """Find duplicate files by MD5 hash."""
        hash_map: dict[str, list[Path]] = defaultdict(list)
        scanned = 0
        errors: list[str] = []

        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                fpath = Path(root) / fname
                try:
                    file_hash = await self._hash_file(fpath)
                    hash_map[file_hash].append(fpath)
                    scanned += 1
                except Exception as exc:
                    errors.append(f"{fpath}: {exc}")
                    logger.warning("Failed to hash %s: %s", fpath, exc)

        # Filter to only duplicates
        duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}

        if not duplicates:
            return f"No duplicates found in {path} (scanned {scanned} files)."

        report_lines = [f"Duplicate files in {path}:", ""]
        total_wasted = 0
        group_num = 0
        for file_hash, paths in duplicates.items():
            group_num += 1
            try:
                file_size = paths[0].stat().st_size
            except OSError:
                file_size = 0
            wasted = file_size * (len(paths) - 1)
            total_wasted += wasted

            report_lines.append(f"Group {group_num} ({len(paths)} files, {self._human_size(file_size)} each):")
            for p in paths:
                report_lines.append(f"  - {p}")
            report_lines.append("")

        report_lines.append(f"Total duplicates: {sum(len(p) for p in duplicates.values())} files in {len(duplicates)} groups")
        report_lines.append(f"Potential space savings: {self._human_size(total_wasted)}")

        await self._publish_event("file.duplicates_found", {
            "path": str(path),
            "groups": len(duplicates),
            "total_duplicates": sum(len(p) for p in duplicates.values()),
        })

        return "\n".join(report_lines)

    @staticmethod
    async def _hash_file(file_path: Path) -> str:
        """Compute MD5 hash of a file."""
        h = hashlib.md5()
        def _read() -> bytes:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.digest()

        await asyncio.to_thread(_read)
        return h.hexdigest()

    @staticmethod
    def _human_size(nbytes: int) -> str:
        """Format bytes into human-readable size."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if nbytes < 1024:
                return f"{nbytes:.1f} {unit}"
            nbytes /= 1024
        return f"{nbytes:.1f} PB"

    # ── cleanup desktop ────────────────────────────────────────────────

    async def cleanup_desktop(self) -> str:
        """Organize files on the user's Desktop into category folders."""
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            # Try Turkish "Masaüstü"
            desktop = Path.home() / "Masaüstü"
            if not desktop.exists():
                return "Desktop directory not found."

        # Also clean OneDrive desktop if present
        onedrive_desktop = Path.home() / "OneDrive" / "Desktop"
        paths_to_clean = [desktop]
        if onedrive_desktop.exists():
            paths_to_clean.append(onedrive_desktop)

        all_reports: list[str] = []
        for p in paths_to_clean:
            report = await self.organize_directory(p)
            all_reports.append(report)

        return "\n\n".join(all_reports)

    # ── watchdog ───────────────────────────────────────────────────────

    async def start_watching(self, path: Path) -> None:
        """Start watching a directory for file changes."""
        try:
            from watchdog.observers import Observer
        except ImportError:
            raise RuntimeError(
                "watchdog is required for file watching. "
                "Install it with: pip install watchdog",
            )

        if self._watching:
            await self.stop_watching()

        handler = FileOrganizerHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(path), recursive=True)
        self._observer.start()
        self._watching = True
        self._watched_paths.append(path)
        logger.info("Watching directory: %s", path)

    async def stop_watching(self) -> None:
        """Stop watching directories."""
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=5)
            except Exception as exc:
                logger.warning("Error stopping observer: %s", exc)
            self._observer = None
        self._watching = False
        self._watched_paths.clear()
        logger.info("File watching stopped")

    # ── event handlers ─────────────────────────────────────────────────

    async def _on_organize_request(self, event) -> None:
        """Handle organize request event."""
        try:
            path_str = event.data.get("path", ".")
            path = Path(path_str).resolve()
            if path.exists() and path.is_dir():
                report = await self.organize_directory(path)
                await self._publish_event("file.organize_result", {"report": report})
            else:
                await self._publish_event(
                    "file.organize_error",
                    {"error": f"Invalid path: {path_str}"},
                )
        except Exception as exc:
            logger.error("Error on file.organize_request: %s", exc)
            await self._publish_event("file.organize_error", {"error": str(exc)})

    async def _on_duplicates_request(self, event) -> None:
        """Handle duplicates request event."""
        try:
            path_str = event.data.get("path", ".")
            path = Path(path_str).resolve()
            if path.exists() and path.is_dir():
                report = await self.find_duplicates(path)
                await self._publish_event("file.duplicates_result", {"report": report})
            else:
                await self._publish_event(
                    "file.duplicates_error",
                    {"error": f"Invalid path: {path_str}"},
                )
        except Exception as exc:
            logger.error("Error on file.duplicates_request: %s", exc)
            await self._publish_event("file.duplicates_error", {"error": str(exc)})

    async def _on_cleanup_request(self, event) -> None:
        """Handle cleanup request event."""
        try:
            report = await self.cleanup_desktop()
            await self._publish_event("file.cleanup_result", {"report": report})
        except Exception as exc:
            logger.error("Error on file.cleanup_request: %s", exc)
            await self._publish_event("file.cleanup_error", {"error": str(exc)})
