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
            elif action == "list_apps":
                result = await self._list_installed_apps(task)
            elif action == "media_control":
                result = await self._media_control(task)
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

    async def _get_screenshot_base64(self, task: Task) -> str:
        """Capture screenshot and return as base64 string."""
        import mss
        import mss.tools
        import base64
        from io import BytesIO
        from PIL import Image

        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[1]) # Primary monitor
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')

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
        "not defteri": "notepad",
        "steam": "steam://open/main",
        "epic": "com.epicgames.launcher://",
        "epic games": "com.epicgames.launcher://",
        "cs2": "steam://rungameid/730",
        "cs 2": "steam://rungameid/730",
        "counter strike": "steam://rungameid/730",
        "counter-strike 2": "steam://rungameid/730",
        "dota": "steam://rungameid/570",
        "pubg": "steam://rungameid/578080",
        "valorant": "valorant",
        "league of legends": "leagueClient",
        "lol": "leagueClient",
        "obs": "obs64",
        "zoom": "zoom",
        "vlc": "vlc",
        "chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "notepad": "notepad",
        "calculator": "calc",
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

    async def _list_installed_apps(self, task: Task) -> TaskResult:
        """Scan Windows registry and common paths for installed software."""
        import winreg
        import os

        apps = set()
        
        # 1. Check Registry (Uninstalls)
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hive, path in registry_paths:
            try:
                with winreg.OpenKey(hive, path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                apps.add(name)
                        except: continue
            except: continue

        # 2. Add Steam Games
        steam_games = self._list_steam_games()
        for game in steam_games:
            apps.add(f"Steam: {game}")

        sorted_apps = sorted(list(apps))
        
        # Store in blackboard for other agents
        await self.blackboard.set("installed_apps", sorted_apps)

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"✅ {len(sorted_apps)} uygulama bulundu.\n\n" + "\n".join(sorted_apps[:50]) + ("\n..." if len(sorted_apps) > 50 else "")
        )

    async def _media_control(self, task: Task) -> TaskResult:
        """Control media playback (Play, Pause, Volume)."""
        import pyautogui
        action = task.context.get("media_action", "").lower()
        
        if "dur" in action or "pause" in action or "stop" in action:
            pyautogui.press('playpause')
            output = "⏸️ Medya durduruldu."
        elif "başlat" in action or "play" in action or "devam" in action:
            pyautogui.press('playpause')
            output = "▶️ Medya başlatıldı."
        elif "ses" in action and "aç" in action:
            for _ in range(5): pyautogui.press('volumeup')
            output = "🔊 Ses artırıldı."
        elif "ses" in action and "kıs" in action:
            for _ in range(5): pyautogui.press('volumedown')
            output = "🔉 Ses azaltıldı."
        else:
            # Try spacebar as fallback for focused video players
            pyautogui.press('space')
            output = "⌨️ Boşluk tuşu gönderildi (Play/Pause fallback)."

        return TaskResult(task_id=task.id, status=TaskStatus.SUCCESS, output=output)

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
        except Exception as e:
            logger.error("Error launching %s: %s", exe_name, e)
            return False

    def _list_steam_games(self) -> list[str]:
        """Read Steam manifest files to list installed games."""
        import os
        import re
        
        steam_paths = [
            r"C:\Program Files (x86)\Steam\steamapps",
            r"D:\SteamLibrary\steamapps",
            r"E:\SteamLibrary\steamapps",
        ]
        
        games = []
        for path in steam_paths:
            if not os.path.exists(path):
                continue
                
            for file in os.listdir(path):
                if file.startswith("appmanifest_") and file.endswith(".acf"):
                    try:
                        with open(os.path.join(path, file), "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            name_match = re.search(r'"name"\s+"([^"]+)"', content)
                            if name_match:
                                games.append(name_match.group(1))
                    except Exception:
                        continue
        return sorted(list(set(games)))

    def _resolve_app_name(self, description: str, task_context: dict = None) -> tuple[str | None, str | None]:
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

        # Check memory lessons for learned aliases
        if not resolved_exe and not resolved_url:
            lesson_context = task_context.get("lesson_context", "") if task_context else ""
            if lesson_context:
                import re
                # Look for patterns like "X is actually Y" or "X refers to Y" or "X = Y"
                alias_match = re.search(rf"\b{re.escape(desc_lower)}\b\s+(?:is|refers to|actually|yani|=)\s+([\w\s.-]+)", lesson_context, re.IGNORECASE)
                if alias_match:
                    learned_name = alias_match.group(1).strip().lower()
                    logger.info(f"Memory alias found: {desc_lower} -> {learned_name}")
                    # Re-check with the learned name
                    for app, exe in self.SAFE_APP_MAP.items():
                        if app in learned_name:
                            resolved_exe = exe
                    for site, url in self.SAFE_SITE_MAP.items():
                        if site in learned_name:
                            resolved_url = url

        return resolved_exe, resolved_url

    async def _launch_app(self, task: Task) -> TaskResult:
        """Launch an app or open a website — whitelist-based, no shell injection."""
        import webbrowser

        app_name = task.context.get("app_name", "") or task.description
        resolved_exe, resolved_url = self._resolve_app_name(app_name, task_context=task.context)

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

        # 2. Use Vision LLM to identify coordinates
        image_b64 = await self._get_screenshot_base64(task)
        prompt = (
            f"Find the exact X, Y coordinates for the following element: '{task.description}'\n"
            f"Return ONLY a raw JSON object: {{\"x\": number, \"y\": number, \"confidence\": number}}"
        )
        response = await self.llm_router.vision_chat(prompt, image_b64)
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

        # Check for open/close keywords
        open_keywords = ["aç", "ac", "open", "başlat", "baslat", "launch",
                         "çalıştır", "calistir", "run", "git", "go to", "site"]
        close_keywords = ["kapat", "cik", "çık", "close", "exit", "kill", "sonlandır", "durdur"]
        
        is_open_task = any(kw in desc for kw in open_keywords)
        is_close_task = any(kw in desc for kw in close_keywords)
        is_list_task = any(kw in desc for kw in ["listele", "göster", "neler var", "list", "show"])
        
        # Steam Library Special Path
        if "steam" in desc and is_list_task:
            games = self._list_steam_games()
            if games:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    output=f"Steam Kütüphanesi:\n" + "\n".join(f"- {g}" for g in games)
                )
            else:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    output="Steam kütüphanesinde yüklü oyun bulunamadı veya Steam yolu saptanamadı."
                )

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
                
                # Special handling for YouTube search queries
                if site == "youtube" or site == "youtube.com":
                    # Remove open/play keywords and 'youtube' from the description to get the query
                    import re
                    from urllib.parse import quote_plus
                    
                    query = desc
                    for kw in open_keywords + ["youtube", "youtube.com", "lütfen", "aç", "oynat", "play"]:
                        query = re.sub(rf"\b{kw}\b", "", query, flags=re.IGNORECASE)
                    
                    query = query.strip()
                    if query and len(query) > 1:
                        # Auto-fetch first video ID to play it directly instead of just searching
                        try:
                            import urllib.request
                            import re
                            search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                            headers = {'User-Agent': 'Mozilla/5.0'}
                            req = urllib.request.Request(search_url, headers=headers)
                            with urllib.request.urlopen(req) as response:
                                html = response.read().decode()
                                video_ids = re.findall(r"watch\?v=(\S{11})", html)
                                if video_ids:
                                    website_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                                    logger.info(f"YouTube auto-play found video ID: {video_ids[0]}")
                                else:
                                    website_url = search_url
                        except Exception as e:
                            logger.warning(f"YouTube auto-play search failed: {e}")
                            website_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                
                break

        if app_to_open and (is_open_task or website_url):
            steps.append(f"Fast path: Opening {app_to_open}")
            try:
                # SECURITY: Use the whitelist-based resolver
                resolved_exe, resolved_url = self._resolve_app_name(desc, task_context=task.context)

                # Override with detected website_url if available
                if website_url:
                    resolved_url = website_url

                # Step 1: Handle Close Task
                if is_close_task:
                    import subprocess
                    if resolved_exe:
                        # SECURITY: Whitelist-only taskkill
                        exe_base = resolved_exe.split(".")[0]
                        subprocess.run(["taskkill", "/F", "/IM", f"{exe_base}.exe"], 
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        steps.append(f"✅ {app_to_open} kapatıldı")
                        return TaskResult(
                            task_id=task.id,
                            status=TaskStatus.SUCCESS,
                            output="\n".join(steps),
                        )

                # Step 2: Open URL if we have one (Open task)
                if resolved_url and is_open_task:
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

                    # Wait for app to appear and focus
                    import time
                    time.sleep(2)
                    
                    # Optional: Type text if requested in description
                    type_text = task.context.get("type_text") or task.context.get("text")
                    if not type_text:
                        import re
                        # Pattern 1: [Keyword] [Text] (e.g., "yaz Merhaba")
                        write_match = re.search(r"(?:yaz|yazısı|not al|type|mesajı)\s+[:'\" ]?(.+?)['\"]?$", desc, re.IGNORECASE)
                        if write_match:
                            type_text = write_match.group(1)
                        else:
                            # Pattern 2: [Text] [Keyword] (e.g., "Merhaba yaz")
                            write_match_rev = re.search(r"['\"]?(.+?)['\"]?\s+(?:yaz|yazısı|yazmasını|yazdır|not al)\b", desc, re.IGNORECASE)
                            if write_match_rev:
                                type_text = write_match_rev.group(1)
                    
                    if success and type_text:
                        # Intelligent Expansion: If the text to type looks like a question or instruction, expand it via LLM
                        if any(kw in type_text.lower() for kw in ["sorusunun", "hakkında", "nedir", "cevap", "answer", "about"]):
                            logger.info(f"Expanding type_text via LLM: {type_text}")
                            try:
                                prompt = f"Kullanıcı bilgisayarda bir yere şunu yazmanı istiyor: '{type_text}'. Lütfen sadece yazılması gereken asıl içeriği üret. Kısa ve öz ol."
                                response = await self.llm_router.chat([{"role": "user", "content": prompt}])
                                type_text = response.content.strip().replace('"', '')
                                logger.info(f"Expanded text: {type_text}")
                            except Exception as e:
                                logger.warning(f"LLM expansion failed, typing original text: {e}")

                        import pyautogui
                        pyautogui.typewrite(type_text, interval=0.01)
                        steps.append(f"⌨️ Metin yazıldı: {type_text[:50]}...")

                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.SUCCESS if success else TaskStatus.FAILED,
                        output="\n".join(steps),
                    )

                steps.append(f"⚠️ {app_to_open} whitelist'te bulunamadı")
            except Exception as e:
                steps.append(f"❌ Fast path failed: {e}")
                # Fall through to full RPA loop

        # ─── MULTIMODAL VISION PATH ───
        try:
            image_b64 = await self._get_screenshot_base64(task)
            
            vision_prompt = (
                f"Senden bir bilgisayar otomasyonu görevi yapmanı istiyorum.\n"
                f"GÖREV: {task.description}\n\n"
                f"Ekran görüntüsüne bakarak şunları yap:\n"
                f"1. Gerekli buton, metin kutusu veya simgeleri tespit et.\n"
                f"2. Bunların yaklaşık X, Y koordinatlarını belirle (Ekran çözünürlüğü tam boyuttur).\n"
                f"3. Görevi tamamlamak için gereken adım listesini JSON formatında üret.\n\n"
                f"Eylemler: mouse_click(x,y), type_text(text), hotkey(keys), launch_app(name)\n\n"
                f"SADECE ham JSON dizisi döndür (Markdown ```json blokları OLMASIN)."
            )
            
            vision_res = await self.llm_router.vision_chat(vision_prompt, image_b64)
            plan_text = vision_res.content.strip()
            
            # Clean JSON
            import re
            plan_text = re.sub(r"```json\s*|\s*```", "", plan_text)
            actions = json.loads(plan_text)
            
            for act in actions:
                name = act.get("action")
                params = act.get("params", {})
                
                if name == "mouse_click":
                    pyautogui.click(params.get("x"), params.get("y"))
                elif name == "type_text":
                    pyautogui.typewrite(params.get("text"), interval=0.01)
                elif name == "hotkey":
                    pyautogui.hotkey(*params.get("keys"))
                elif name == "launch_app":
                    self._safe_launch_executable(params.get("name"))
                
                steps.append(f"Vision Action: {name} ({params})")
                await asyncio.sleep(1)

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output="\n".join(steps),
            )
        except Exception as e:
            logger.warning(f"Vision path failed, falling back to OCR: {e}")
            steps.append(f"Vision Error: {e} - Falling back to OCR")

        # ─── FALLBACK PATH: OCR → Plan → Execute ───
        try:
            ocr_result = await self._ocr_read(task)
            screen_text = ocr_result.output[:1000]
        except Exception as e:
            screen_text = f"OCR failed: {e}"

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
