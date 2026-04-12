"""PlaywrightAgent — URL'den tam site klonlama (headless Chromium)."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    async_playwright = None  # type: ignore
    PlaywrightTimeout = TimeoutError = Exception  # type: ignore

_SEMAPHORE = asyncio.Semaphore(2)  # max 2 eş zamanlı klonlama — 32 GB RAM koruma


class PlaywrightAgent:
    def __init__(self, workspace_root: str = "workspace/cloned_templates"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def clone(self, url: str, site_name: Optional[str] = None) -> dict:
        """Ana klonlama metodu. WorkspaceManager tarafından çağrılır."""
        async with _SEMAPHORE:
            return await self._do_clone(url, site_name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    async def _do_clone(self, url: str, site_name: Optional[str]) -> dict:
        if async_playwright is None:
            return {
                "success": False,
                "error": "Playwright kurulu değil. 'playwright install chromium' çalıştır.",
            }

        if not site_name:
            domain = urlparse(url).netloc.replace("www.", "")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            site_name = f"{domain}_{ts}"

        target_dir = self.workspace_root / site_name
        target_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = target_dir / "assets"
        assets_dir.mkdir(exist_ok=True)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (compatible; JarvisBot/2.0)",
                )
                page = await context.new_page()

                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(2000)  # JS animasyonları bekle

                    # Ham HTML
                    raw_html = await page.content()
                    (target_dir / "raw.html").write_text(raw_html, encoding="utf-8")

                    # Temizlenmiş HTML
                    clean_html = self._clean_html(raw_html)
                    (target_dir / "index.html").write_text(clean_html, encoding="utf-8")

                    # Meta veriler
                    title = await page.title()
                    desc_el = await page.query_selector('meta[name="description"]')
                    description = ""
                    if desc_el:
                        description = await desc_el.get_attribute("content") or ""

                    # Bileşen analizi
                    components = await self._extract_components(page)

                    # LLM özet
                    summary = await self._summarize_with_llm(
                        title=title,
                        description=description,
                        components=components,
                        url=url,
                    )

                    metadata = {
                        "site_name": site_name,
                        "url": url,
                        "title": title,
                        "description": description,
                        "components": components,
                        "summary": summary,
                        "cloned_at": datetime.now().isoformat(),
                        "file_path": str(target_dir),
                    }
                    (target_dir / "metadata.json").write_text(
                        json.dumps(metadata, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )

                    return {"path": str(target_dir), "metadata": metadata, "success": True}

                except (PlaywrightTimeout, TimeoutError):
                    return {"success": False, "error": f"Timeout: {url} 30 saniyede yüklenemedi"}
                except Exception as e:
                    return {"success": False, "error": str(e)}
                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            return {"success": False, "error": f"Browser launch failed: {e}"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _extract_components(self, page) -> list:
        """Sayfadaki UI bileşenlerini tespit et."""
        components: list[str] = []
        checks = {
            "navbar": "nav, [class*='navbar'], [class*='header']",
            "hero": "[class*='hero'], [class*='banner'], [class*='jumbotron']",
            "search_bar": "input[type='search'], [class*='search']",
            "cards": "[class*='card'], [class*='tile']",
            "footer": "footer, [class*='footer']",
            "modal": "[class*='modal'], [role='dialog']",
            "sidebar": "aside, [class*='sidebar']",
            "form": "form",
            "table": "table",
        }

        for name, selector in checks.items():
            el = await page.query_selector(selector)
            if el:
                components.append(name)

        # Karanlık tema tespiti
        bg_color = await page.evaluate(
            "() => getComputedStyle(document.body).backgroundColor"
        )
        if bg_color:
            r, g, b = self._parse_rgb(bg_color)
            if (r + g + b) / 3 < 128:
                components.append("dark_theme")

        return components

    @staticmethod
    def _clean_html(html: str) -> str:
        """Zararlı script ve tracker'ları temizle."""
        html = re.sub(
            r'<script[^>]*google-analytics[^>]*>.*?</script>',
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html = re.sub(
            r'<script[^>]*facebook[^>]*>.*?</script>',
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return html

    @staticmethod
    def _parse_rgb(rgb_str: str):
        match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", rgb_str)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
        return 128, 128, 128

    @staticmethod
    async def _summarize_with_llm(
        title: str, description: str, components: list, url: str
    ) -> str:
        """Ollama ile kısa özet oluştur."""
        try:
            prompt = (
                f"Bu web sitesini 2 cümlede özetle:\n"
                f"URL: {url}\nBaşlık: {title}\nAçıklama: {description}\n"
                f"Bileşenler: {', '.join(components)}\n"
                f"Tasarım ve amaç hakkında kısa bilgi ver."
            )
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "qwen2.5:14b", "prompt": prompt, "stream": False},
                )
                return resp.json().get("response", "Özet oluşturulamadı.")
        except Exception:
            return f"{title} — {description}"
