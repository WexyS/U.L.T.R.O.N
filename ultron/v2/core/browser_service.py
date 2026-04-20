"""Unified Browser Service — Centralized Playwright management."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class BrowserService:
    """Manages Playwright browser instances for agents."""

    def __init__(self, data_dir: str = "./data/browser"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._browser = None
        self._playwright = None
        self._context = None

    async def _init_playwright(self):
        """Initialize Playwright and Chromium."""
        if self._playwright is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            self._context = await self._browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a URL and return content + metadata."""
        try:
            await self._init_playwright()
            page = await self._context.new_page()
            
            # Anti-bot: Stealth wait
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2) # Let JS load
            
            title = await page.title()
            content = await page.evaluate("() => document.body.innerText")
            
            # Optional: Screenshot
            screenshot_name = f"scrape_{hash(url)}_{int(datetime.now().timestamp())}.png"
            screenshot_path = self.data_dir / screenshot_name
            await page.screenshot(path=str(screenshot_path))
            
            await page.close()
            
            return {
                "url": url,
                "title": title,
                "content": content,
                "screenshot": str(screenshot_path),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error("BrowserService scrape failed for %s: %s", url, e)
            return {"url": url, "error": str(e)}

    async def screenshot(self, url: str) -> Optional[str]:
        """Capture a screenshot of a URL."""
        data = await self.scrape_url(url)
        return data.get("screenshot")

    async def close(self):
        """Cleanup resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
