import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
import random

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.sync_api import sync_playwright, Page, Browser

from src.config import settings


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def _ensure_browsers():
    browsers_path = Path.home() / ".cache" / "ms-playwright"
    browsers_path.mkdir(parents=True, exist_ok=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
    has_chromium = (
        any("chromium" in d.name for d in browsers_path.iterdir() if d.is_dir())
        if browsers_path.exists()
        else False
    )
    if not has_chromium:
        try:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                timeout=180,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"[green-finder] playwright install failed (rc={e.returncode}): {e}", file=sys.stderr)
        except Exception as e:
            print(f"[green-finder] playwright install error: {e}", file=sys.stderr)


class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None

    def start(self):
        _ensure_browsers()
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=settings.headless,
            slow_mo=settings.slow_mo,
            proxy=settings.proxy_config,
            args=[
                f"--window-size={settings.viewport_width},{settings.viewport_height}",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
            ],
        )
        return self

    def new_page(self) -> Page:
        context = self._browser.new_context(
            viewport={
                "width": settings.viewport_width,
                "height": settings.viewport_height,
            },
            user_agent=random.choice(USER_AGENTS),
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            permissions=["geolocation"],
        )
        context.grant_permissions(["geolocation"])
        page = context.new_page()
        self._evade_detection(page)
        return page

    def _evade_detection(self, page: Page):
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru'] });
            window.chrome = { runtime: {} };
        """)

    def screenshot(self, page: Page, name: str) -> Path:
        path = settings.screenshots_path / f"{name}.png"
        page.screenshot(path=str(path), full_page=False)
        return path

    def stop(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
