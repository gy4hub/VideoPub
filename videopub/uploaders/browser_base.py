"""Playwright 浏览器管理基类。"""

import json
from datetime import datetime
from pathlib import Path

from videopub.core.config_loader import load_settings


async def _ensure_playwright():
    """延迟导入 playwright。"""
    from playwright.async_api import async_playwright

    return async_playwright


class BrowserManager:
    """管理 Playwright 浏览器实例、上下文与持久化状态。"""

    def __init__(self, cookie_path: Path | str):
        self.cookie_path = Path(cookie_path).expanduser()
        self._playwright = None
        self._browser = None
        self._context = None
        self.page = None

    async def launch(self, headless: bool | None = None):
        """启动浏览器并创建页面。"""
        settings = load_settings()
        browser_config = settings.get("browser", {})

        if headless is None:
            headless = browser_config.get("headless", True)
        slow_mo = browser_config.get("slow_mo", 100)

        async_playwright = await _ensure_playwright()
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=["--disable-blink-features=AutomationControlled"],
        )

        if self.cookie_path.exists():
            self._context = await self._browser.new_context(storage_state=str(self.cookie_path))
        else:
            self._context = await self._browser.new_context()

        self.page = await self._context.new_page()

    async def save_cookies(self):
        """保存当前 storage state。"""
        if not self._context:
            return

        self.cookie_path.parent.mkdir(parents=True, exist_ok=True)
        storage = await self._context.storage_state()
        with self.cookie_path.open("w", encoding="utf-8") as file:
            json.dump(storage, file, ensure_ascii=False, indent=2)

    async def take_screenshot(self, name: str = "screenshot") -> Path:
        """截图保存到日志目录。"""
        path = self._build_log_path(name, "png")
        if self.page:
            await self.page.screenshot(path=str(path))
        return path

    async def save_page_html(self, name: str = "page") -> Path:
        """保存页面 HTML 到日志目录。"""
        path = self._build_log_path(name, "html")
        if self.page:
            content = await self.page.content()
            path.write_text(content, encoding="utf-8")
        return path

    async def close(self):
        """关闭页面、上下文与浏览器。"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._context = None
        self._browser = None
        self._playwright = None
        self.page = None

    @staticmethod
    def _build_log_path(name: str, suffix: str) -> Path:
        settings = load_settings()
        log_dir = Path(settings.get("log_dir", "~/videopub/logs")).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return log_dir / f"{name}_{timestamp}.{suffix}"
