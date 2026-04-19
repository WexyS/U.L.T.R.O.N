"""RPA Operator Agent — computer use via mouse, keyboard, and screen control."""

import base64
import logging
import webbrowser
from pathlib import Path

from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus, ToolCall
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class RPAOperatorAgent(Agent):
    """Autonomous computer use agent.

    Capabilities:
    - Screen capture and OCR reading
    - Mouse movement, clicking, drag-drop
    - Keyboard input and shortcuts
    - Window management
    - Application launching
    - UI element detection and interaction
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
        screenshot_dir: str = "./data/screenshots",
    ) -> None:
        super().__init__(
            role=AgentRole.RPA_OPERATOR,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
        )
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._pyautogui = None
        self._mss = None
        self._easyocr = None

    def _default_system_prompt(self) -> str:
        return (
            "You are a computer automation expert that can control a computer like a human.\n"
            "You can:\n"
            "1. Take screenshots and read text from the screen (OCR)\n"
            "2. Move the mouse and click on elements\n"
            "3. Type text on the keyboard\n"
            "4. Use keyboard shortcuts (Ctrl+C, Ctrl+V, Alt+Tab, etc.)\n"
            "5. Open applications and navigate their UI\n"
            "6. Find buttons, text fields, and other UI elements\n\n"
            "When given a task, describe what you see and what actions you take.\n"
            "Be precise with coordinates. Report what you observe after each action.\n"
            "If an action fails, try an alternative approach."
        )

    async def _subscribe_events(self) -> None:
        async def on_rpa_request(event) -> None:
            if not self._running:
                return
            task = Task(
                id=event.data.get("task_id"),
                description=event.data.get("description", ""),
                context=event.data.get("context", {}),
            )
            result = await self.execute(task)
            await self._publish_event("rpa_result", {
                "task_id": task.id,
                "output": result.output,
                "error": result.error,
                "success": result.status == TaskStatus.SUCCESS,
            })

        self.event_bus.subscribe("rpa_request", on_rpa_request)

    def _init_pyautogui(self):
        if self._pyautogui is None:
            import pyautogui
            pyautogui.FAILSAFE = True  # Move mouse to corner to abort
            pyautogui.PAUSE = 0.5  # Small delay between actions
            self._pyautogui = pyautogui
        return self._pyautogui

    def _init_mss(self):
        """Deprecated — use context manager in _screenshot instead."""
        pass

    def _init_easyocr(self):
        if self._easyocr is None:
            try:
                import easyocr
                # Initialize once (loading is slow)
                self._easyocr = easyocr.Reader(["en", "tr"], gpu=True)
                logger.info("EasyOCR initialized (GPU enabled)")
            except Exception as e:
                logger.warning(f"EasyOCR initialization failed, falling back to None. Error: {e}")
                self._easyocr = None
        return self._easyocr

    async def execute(self, task: Task) -> TaskResult:
        """Execute an RPA task."""
        self.state.status = AgentStatus.BUSY
        self.state.current_task = task.id

        try:
            action = task.context.get("action", "auto")
            tool_calls = []

            if action == "screenshot":
                result = await self._screenshot(task)
            elif action == "ocr":
                result = await self._ocr_read(task)
            elif action == "mouse_click":
                result = await self._mouse_click(task)
            elif action == "mouse_move":
                result = await self._mouse_move(task)
            elif action == "type_text":
                result = await self._type_text(task)
            elif action == "hotkey":
                result = await self._hotkey(task)
            elif action == "drag_drop":
                result = await self._drag_drop(task)
            elif action == "launch_app":
                result = await self._launch_app(task)
            elif action == "find_element":
                result = await self._find_ui_element(task)
            elif action == "weather":
                result = await self._weather_report(task)
            elif action == "alt_tab":
                import pyautogui
                import time
                pyautogui.hotkey('alt', 'tab')
                time.sleep(1)
                result = TaskResult(task_id=task.id, status=TaskStatus.SUCCESS,
                                   output="✅ alt+tab sent — window switched")
            elif action == "auto":
                # Autonomous: describe screen, plan, and execute
                result = await self._autonomous_action(task)
            else:
                result = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=f"Unknown RPA action: {action}",
                )

            return result
        finally:
            self.state.status = AgentStatus.IDLE
            self.state.current_task = None

    async def _screenshot(self, task: Task) -> TaskResult:
        """Take a screenshot and save it."""
        import time
        import mss
        import mss.tools

        region = task.context.get("region")

        # Context manager — fixes '_thread._local' Windows threading bug
        with mss.mss() as sct:
            if region:
                sct_img = sct.grab(region)
            else:
                sct_img = sct.grab(sct.monitors[1])  # Full screen

        filename = task.context.get("filename", f"screenshot_{int(time.time())}.png")
        filepath = self.screenshot_dir / filename
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(filepath))

        with open(filepath, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        await self.store_context(f"screen_{task.id}", {
            "filepath": str(filepath),
            "image_b64": img_b64,
            "size": sct_img.size,
        })

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Screenshot saved to {filepath} ({sct_img.size[0]}x{sct_img.size[1]})",
            tool_calls=[ToolCall(name="screenshot", arguments={"region": region}, success=True)],
        )

    async def _ocr_read(self, task: Task) -> TaskResult:
        """Read text from screen using OCR."""
        # Take screenshot first
        ss_result = await self._screenshot(task)
        if ss_result.status != TaskStatus.SUCCESS:
            return ss_result

        filepath = self.screenshot_dir / f"screenshot_{ss_result.output.split('screenshot_')[1].split(' ')[0]}"

        # Find the actual screenshot file
        screenshots = list(self.screenshot_dir.glob("screenshot_*.png"))
        if not screenshots:
            return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error="No screenshot found")

        filepath = screenshots[-1]
        reader = self._init_easyocr()
        if reader is None:
            return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error="EasyOCR could not be initialized.")
        results = reader.readtext(str(filepath))

        # Extract text
        texts = [text for _, text, confidence in results]
        full_text = "\n".join(texts)

        # Filter if query provided
        query = task.context.get("query")
        if query:
            matching = [t for t in texts if query.lower() in t.lower()]
            if matching:
                full_text = "\n".join(matching)

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=full_text,
            tool_calls=[ToolCall(name="ocr", arguments={"filepath": str(filepath)}, success=True)],
        )

    async def _mouse_click(self, task: Task) -> TaskResult:
        """Click at specified coordinates or on described element."""
        import pyautogui

        x = task.context.get("x")
        y = task.context.get("y")

        if x is not None and y is not None:
            pyautogui.click(x, y)
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output=f"Clicked at ({x}, {y})",
                tool_calls=[ToolCall(name="mouse_click", arguments={"x": x, "y": y}, success=True)],
            )
        else:
            # Find element by description using LLM + OCR
            return await self._find_and_click_by_description(task)

    async def _mouse_move(self, task: Task) -> TaskResult:
        """Move mouse to coordinates."""
        import pyautogui

        x = task.context.get("x", 0)
        y = task.context.get("y", 0)
        duration = task.context.get("duration", 0.5)

        pyautogui.moveTo(x, y, duration=duration)
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Mouse moved to ({x}, {y})",
            tool_calls=[ToolCall(name="mouse_move", arguments={"x": x, "y": y}, success=True)],
        )

    async def _type_text(self, task: Task) -> TaskResult:
        """Type text via keyboard."""
        import pyautogui

        text = task.context.get("text", "")
        interval = task.context.get("interval", 0.05)  # Delay between keystrokes

        pyautogui.typewrite(text, interval=interval)
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}",
            tool_calls=[ToolCall(name="type_text", arguments={"text": text[:100]}, success=True)],
        )

    async def _hotkey(self, task: Task) -> TaskResult:
        """Press keyboard shortcut."""
        import pyautogui

        keys = task.context.get("keys", [])
        if isinstance(keys, str):
            keys = keys.split("+")

        keys = [k.strip().lower() for k in keys]
        pyautogui.hotkey(*keys)

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Pressed hotkey: {'+'.join(keys)}",
            tool_calls=[ToolCall(name="hotkey", arguments={"keys": keys}, success=True)],
        )

    async def _drag_drop(self, task: Task) -> TaskResult:
        """Drag from one position to another."""
        import pyautogui

        x1 = task.context.get("x1", 0)
        y1 = task.context.get("y1", 0)
        x2 = task.context.get("x2", 0)
        y2 = task.context.get("y2", 0)
        duration = task.context.get("duration", 1.0)

        pyautogui.drag(x2 - x1, y2 - y1, duration=duration)
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Dragged from ({x1},{y1}) to ({x2},{y2})",
            tool_calls=[ToolCall(name="drag_drop", arguments={"from": [x1, y1], "to": [x2, y2]}, success=True)],
        )

    # SECURITY: Whitelist of allowed executables — prevents shell injection
    SAFE_APP_MAP: dict[str, str] = {
        "steam": "steam",
        "chrome": "chrome",
        "google chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "opera": "opera",
        "spotify": "spotify",
        "discord": "discord",
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "task manager": "taskmgr",
        "paint": "mspaint",
        "explorer": "explorer",
        "cmd": "cmd",
        "terminal": "wt",
        "vscode": "code",
        "visual studio code": "code",
        "pycharm": "pycharm",
        "intellij": "idea",
        "word": "winword",
        "excel": "excel",
        "powerpoint": "powerpnt",
        "outlook": "outlook",
        "teams": "teams",
        "mail": "outlook",
    }

    SAFE_SITE_MAP: dict[str, str] = {
        "youtube": "https://youtube.com",
        "youtube.com": "https://youtube.com",
        "twitter": "https://x.com",
        "x.com": "https://x.com",
        "x": "https://x.com",
        "reddit": "https://reddit.com",
        "github": "https://github.com",
        "gmail": "https://mail.google.com",
        "google": "https://google.com",
        "sozluk": "https://sozluk.gov.tr",
        "sozluk.gov.tr": "https://sozluk.gov.tr",
        "tdk": "https://sozluk.gov.tr",
        "netflix": "https://netflix.com",
        "amazon": "https://amazon.com",
    }

    def _safe_launch_executable(self, exe_name: str) -> bool:
        """Launch a whitelisted executable safely — NO shell=True, NO user input in cmd."""
        import subprocess
        import shutil

        # Validate: exe_name must be in our whitelist values
        allowed_exes = set(self.SAFE_APP_MAP.values())
        if exe_name not in allowed_exes:
            logger.warning("BLOCKED: Attempted to launch non-whitelisted executable: %s", exe_name)
            return False

        # Find the executable on PATH
        exe_path = shutil.which(exe_name)
        if exe_path:
            # SECURITY: shell=False, direct executable path, no user input
            subprocess.Popen([exe_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True

        # Fallback: use os.startfile on Windows for known apps
        import os
        try:
            os.startfile(exe_name)
            return True
        except Exception:
            return False

    def _resolve_app_name(self, description: str) -> tuple[str | None, str | None]:
        """Resolve a natural language description to a safe exe name and/or URL.

        Returns (exe_name_or_None, url_or_None).
        """
        desc_lower = description.lower()
        resolved_exe = None
        resolved_url = None

        # Check websites first
        for site, url in self.SAFE_SITE_MAP.items():
            if site in desc_lower:
                resolved_url = url
                break

        # Check apps
        for app, exe in self.SAFE_APP_MAP.items():
            if app in desc_lower:
                resolved_exe = exe
                break

        return resolved_exe, resolved_url

    async def _launch_app(self, task: Task) -> TaskResult:
        """Launch an app or open a website — whitelist-based, no shell injection."""
        import webbrowser

        app_name = task.context.get("app_name", "") or task.description
        resolved_exe, resolved_url = self._resolve_app_name(app_name)

        # Try website first
        if resolved_url:
            try:
                webbrowser.open(resolved_url)
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    output=f"✅ {resolved_url} tarayıcıda açıldı.",
                    tool_calls=[ToolCall(name="launch_app", arguments={"url": resolved_url}, success=True)],
                )
            except Exception as e:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=f"Tarayıcı açılamadı: {e}",
                )

        # Try safe app launch
        if resolved_exe:
            success = self._safe_launch_executable(resolved_exe)
            if success:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    output=f"✅ {resolved_exe} açıldı.",
                    tool_calls=[ToolCall(name="launch_app", arguments={"app": resolved_exe}, success=True)],
                )

        # Unknown app — refuse to launch
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.FAILED,
            error=f"🔒 Güvenlik: '{app_name}' tanınmayan bir uygulama. Yalnızca bilinen uygulamalar başlatılabilir.",
        )

    async def _find_and_click_by_description(self, task: Task) -> TaskResult:
        """Find a UI element by natural language description and click it."""
        import pyautogui

        # 1. Take screenshot
        await self._screenshot(task)

        # 2. Use LLM to identify coordinates
        messages = self._build_messages(
            f"I need to find and click on: '{task.description}'\n\n"
            f"Describe the exact coordinates where I should click. "
            f"Return ONLY a JSON object with x and y coordinates.\n"
            f"Format: {{\"x\": 123, \"y\": 456, \"confidence\": 0.9}}"
        )

        response = await self._llm_chat(messages)
        import json
        import re

        json_match = re.search(r'\{[^}]+\}', response.content, re.DOTALL)
        if json_match:
            coords = json.loads(json_match.group())
            x, y = coords.get("x", 0), coords.get("y", 0)
            pyautogui.click(x, y)
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output=f"Found and clicked '{task.description}' at ({x}, {y})",
                tool_calls=[ToolCall(name="find_and_click", arguments={"description": task.description, "coords": [x, y]}, success=True)],
            )
        else:
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=f"Could not determine coordinates for: {task.description}",
            )

    async def _find_ui_element(self, task: Task) -> TaskResult:
        """Find a UI element by text or description."""
        return await self._find_and_click_by_description(task)

    async def _autonomous_action(self, task: Task) -> TaskResult:
        """Autonomously complete a task — with window focus verification."""
        import re
        import json
        import subprocess
        desc = task.description.lower()
        steps = []

        # ─── FAST PATH: Direct app launching + URL opening ───────────────
        app_names = [
            "steam", "chrome", "google chrome", "firefox", "edge", "opera",
            "spotify", "discord", "notepad", "calculator", "calc",
            "task manager", "paint", "explorer", "cmd", "terminal",
            "vscode", "visual studio code", "pycharm", "intellij",
            "word", "excel", "powerpoint", "outlook", "teams",
            "youtube", "twitter", "x.com", "reddit", "github",
            "mail", "posta", "gmail", "outlook",
        ]

        # Try to extract app name
        app_to_open = None
        for app in app_names:
            if app in desc:
                app_to_open = app.title()
                break

        # Check for open keywords
        open_keywords = ["aç", "ac", "open", "başlat", "baslat", "launch",
                         "çalıştır", "calistir", "run", "git", "go to", "site"]
        is_open_task = any(kw in desc for kw in open_keywords)

        # Website detection
        site_map = {
            "youtube": "https://youtube.com",
            "youtube.com": "https://youtube.com",
            "twitter": "https://x.com",
            "x.com": "https://x.com",
            "reddit": "https://reddit.com",
            "github": "https://github.com",
            "gmail": "https://mail.google.com",
            "google": "https://google.com",
            "sozluk": "https://sozluk.gov.tr",
            "sozluk.gov.tr": "https://sozluk.gov.tr",
            "tdk": "https://sozluk.gov.tr",
        }
        website_url = None
        for site, url in site_map.items():
            if site in desc:
                website_url = url
                if not app_to_open:
                    app_to_open = site.title()
                break

        if app_to_open and (is_open_task or website_url):
            steps.append(f"Fast path: Opening {app_to_open}")
            try:
                # SECURITY: Use the whitelist-based resolver
                resolved_exe, resolved_url = self._resolve_app_name(desc)

                # Override with detected website_url if available
                if website_url:
                    resolved_url = website_url

                # Step 1: Open URL if we have one
                if resolved_url:
                    import webbrowser
                    webbrowser.open(resolved_url)
                    steps.append(f"✅ {resolved_url} tarayıcıda açıldı")
                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.SUCCESS,
                        output="\n".join(steps),
                    )

                # Step 2: Launch the app via safe whitelist
                if resolved_exe:
                    success = self._safe_launch_executable(resolved_exe)
                    if success:
                        steps.append(f"✅ {app_to_open} başlatıldı")
                    else:
                        steps.append(f"❌ {app_to_open} başlatılamadı")

                    # Wait for app to appear
                    import time
                    time.sleep(2)

                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.SUCCESS if success else TaskStatus.FAILED,
                        output="\n".join(steps),
                    )

                steps.append(f"⚠️ {app_to_open} whitelist'te bulunamadı")
            except Exception as e:
                steps.append(f"❌ Fast path failed: {e}")
                # Fall through to full RPA loop

        # ─── FULL PATH: Screenshot → OCR → Plan → Execute with Verification ───
        try:
            ss_result = await self._screenshot(task)
            steps.append(f"Observation: {ss_result.output}")
            ocr_result = await self._ocr_read(task)
            screen_text = ocr_result.output[:500]
        except (RuntimeError, Exception) as e:
            if "mss" in str(e).lower() or "screenshot" in str(e).lower():
                steps.append(f"Observation: SKIPPED ({e})")
                screen_text = "(Ekran görüntüsü alınamadı)"
            else:
                steps.append(f"Observation ERROR: {e}")
                screen_text = "(Hata oluştu)"

        steps.append(f"Screen text (first 500 chars):\n{screen_text}")

        # Check if we're still on Ultron GUI (localhost) — switch away if so
        if "localhost" in screen_text.lower() or "127.0.0.1" in screen_text.lower() or "517" in screen_text:
            steps.append("⚠️ Detected Ultron GUI — switching away with alt+tab")
            import pyautogui
            import time
            pyautogui.hotkey('alt', 'tab')
            time.sleep(1)
            # Verify switch
            try:
                ss2 = await self._screenshot(task)
                ocr2 = await self._ocr_read(task)
                screen_text = ocr2.output[:500]
                steps.append(f"After alt+tab: {screen_text[:200]}")
            except Exception:
                pass

        # Plan actions using LLM
        messages = self._build_messages(
            f"Task: {task.description}\n\n"
            f"Current screen content:\n{screen_text}\n\n"
            f"Plan the exact steps to complete this task. "
            f"CRITICAL RULES:\n"
            f"1. BEFORE sending any hotkey (ctrl+l, ctrl+t, enter, etc.), first verify the correct app is in focus.\n"
            f"   If you see 'localhost' or 'ultron' on screen, do alt+tab FIRST.\n"
            f"2. After typing a URL and pressing Enter, take a new screenshot to verify the page loaded.\n"
            f"3. If you still see the wrong page, do alt+tab or click the browser taskbar.\n"
            f"4. Return ONLY a raw JSON array. NO markdown, NO ```json.\n"
            f"\nAvailable actions: screenshot, ocr, mouse_click (x,y), mouse_move (x,y), "
            f"type_text (text), hotkey (keys), drag_drop (x1,y1,x2,y2), launch_app (name), "
            f"alt_tab (switch window)\n\n"
            f'Example: [{{"action": "hotkey", "params": {{"keys": ["alt", "tab"]}}}}, '
            f'{{"action": "type_text", "params": {{"text": "sozluk.gov.tr"}}}}, '
            f'{{"action": "hotkey", "params": {{"keys": ["enter"]}}}}]'
        )

        try:
            response = await self._llm_chat(messages, max_tokens=2048)

            # Strip markdown code blocks
            cleaned = response.content.strip()
            if "```" in cleaned:
                parts = cleaned.split("```")
                for part in parts:
                    stripped = part.strip()
                    if stripped.startswith("json"):
                        stripped = stripped[4:]
                    if stripped.startswith("["):
                        cleaned = stripped
                        break

            json_match = re.search(r'\[[\s\S]*\]', cleaned)
            if not json_match:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=f"LLM did not return valid JSON plan. Response: {cleaned[:300]}",
                )
            plan = json.loads(json_match.group())
        except (json.JSONDecodeError, Exception) as e:
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=f"Failed to parse action plan: {e}",
            )

        # Execute plan with verification loop
        max_steps = len(plan) + 5  # Allow extra steps for verification
        step_idx = 0
        while step_idx < len(plan) and step_idx < max_steps:
            step = plan[step_idx]
            step_idx += 1
            action = step.get("action", "")
            params = step.get("params", {})
            steps.append(f"Step {step_idx}: {action} {params}")

            # Handle alt_tab action
            if action == "alt_tab":
                import pyautogui
                import time
                pyautogui.hotkey('alt', 'tab')
                time.sleep(1)
                steps.append(f"Step {step_idx}: ✅ alt+tab sent")
                # Verify after switch
                try:
                    await self._screenshot(task)
                    ocr_verify = await self._ocr_read(task)
                    verify_text = ocr_verify.output[:200]
                    steps.append(f"Verification: {verify_text}")
                except Exception as ve:
                    steps.append(f"Verification failed: {ve}")
                continue

            # Skip screenshot if mss is not available
            if action == "screenshot":
                try:
                    self._init_mss()
                except RuntimeError:
                    steps.append(f"Step {step_idx}: SKIPPED (mss not installed)")
                    continue

            sub_task = Task(
                id=f"{task.id}_step_{step_idx}",
                description=f"Execute: {action}",
                context={"action": action, **params},
            )

            try:
                result = await self.execute(sub_task)
                steps.append(f"Result: {result.output or result.error}")
                if result.status == TaskStatus.FAILED:
                    steps.append(f"FAILED at step {step_idx}, stopping")
                    break
            except Exception as e:
                steps.append(f"ERROR at step {step_idx}: {e}")
                break

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output="\n".join(steps),
        )

    async def _weather_report(self, task: Task) -> TaskResult:
        """Open weather report for a city in the browser."""
        import webbrowser
        from urllib.parse import quote_plus

        city = task.context.get("city", "") or task.description
        if not city:
            return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error="Şehir belirtilmedi.")

        # Extract city name from description if needed
        import re
        city_match = re.search(r"(?:hava\s+durumu|weather)\s+(?:nedir\s+)?(?:([^,]+?))?\s*$", city, re.IGNORECASE)
        if city_match and city_match.group(1):
            city = city_match.group(1).strip()

        query = f"weather in {city}"
        url = f"https://www.google.com/search?q={quote_plus(query)}"

        try:
            webbrowser.open(url)
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output=f"🌤 {city} için hava durumu tarayıcıda açıldı.",
                tool_calls=[ToolCall(name="weather_report", arguments={"city": city}, success=True)],
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=f"Tarayıcı açılamadı: {e}",
            )
