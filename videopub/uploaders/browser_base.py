"""浏览器管理基类，支持 Playwright / Patchright。"""

import json
from datetime import datetime
from pathlib import Path

from loguru import logger

from videopub.core.config_loader import load_settings


async def _ensure_browser_driver(engine: str):
    """按需导入对应浏览器驱动。"""
    if engine == "patchright":
        from patchright.async_api import async_playwright

        return async_playwright

    from playwright.async_api import async_playwright

    return async_playwright


class BrowserManager:
    """管理浏览器实例、上下文与持久化状态。"""

    def __init__(
        self,
        cookie_path: Path | str,
        *,
        engine: str = "playwright",
        channel: str | None = None,
    ):
        self.cookie_path = Path(cookie_path).expanduser()
        self.engine = engine
        self.channel = channel
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

        async_playwright = await _ensure_browser_driver(self.engine)
        self._playwright = await async_playwright().start()
        launch_kwargs = {
            "headless": headless,
            "slow_mo": slow_mo,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if self.channel:
            launch_kwargs["channel"] = self.channel
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)

        if self.cookie_path.exists():
            try:
                self._context = await self._browser.new_context(
                    storage_state=str(self.cookie_path)
                )
            except Exception as exc:
                logger.warning(f"加载 storage state 失败，改用空白上下文: {exc}")
                self._context = await self._browser.new_context()
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

    async def take_screenshot(self, name: str = "screenshot") -> Path | None:
        """截图保存到日志目录。页面未就绪时返回 None。"""
        if not self.page:
            logger.warning("take_screenshot: page 未就绪，跳过截图")
            return None
        path = self._build_log_path(name, "png")
        try:
            await self.page.screenshot(path=str(path))
        except Exception as exc:
            logger.warning(f"take_screenshot 失败: {exc}")
            return None
        return path

    async def save_page_html(self, name: str = "page") -> Path | None:
        """保存页面 HTML 到日志目录。页面未就绪时返回 None。"""
        if not self.page:
            logger.warning("save_page_html: page 未就绪，跳过")
            return None
        path = self._build_log_path(name, "html")
        try:
            content = await self.page.content()
            path.write_text(content, encoding="utf-8")
        except Exception as exc:
            logger.warning(f"save_page_html 失败: {exc}")
            return None
        return path

    async def close(self):
        """关闭页面、上下文与浏览器（顺序：context → browser → playwright）。"""
        self.page = None
        try:
            if self._context:
                await self._context.close()
        except Exception as exc:
            logger.warning(f"关闭 context 失败: {exc}")
        finally:
            self._context = None

        try:
            if self._browser:
                await self._browser.close()
        except Exception as exc:
            logger.warning(f"关闭 browser 失败: {exc}")
        finally:
            self._browser = None

        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as exc:
            logger.warning(f"关闭 playwright 失败: {exc}")
        finally:
            self._playwright = None

    @staticmethod
    def _build_log_path(name: str, suffix: str) -> Path:
        settings = load_settings()
        log_dir = Path(settings.get("log_dir", "~/videopub/logs")).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return log_dir / f"{name}_{timestamp}.{suffix}"
