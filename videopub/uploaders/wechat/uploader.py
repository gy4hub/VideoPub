"""视频号 Playwright 上传器。"""

from videopub.core.config_loader import load_platform_config
from videopub.core.models import Platform, PlatformTask, UploadResult
from videopub.uploaders.base import BaseUploader
from videopub.uploaders.browser_base import BrowserManager


class WeChatUploader(BaseUploader):
    def __init__(self):
        self.config = load_platform_config("wechat")
        cookie_path = self.config.get("cookie_path", "~/.videopub/wechat_cookie.json")
        self.browser = BrowserManager(cookie_path)
        self._login_timeout = int(self.config.get("login_timeout", 120))

    async def check_session(self) -> bool:
        """检查视频号 Cookie 是否有效。"""
        try:
            await self.browser.launch(headless=True)
            from videopub.uploaders.wechat.pages.login_page import WeChatLoginPage

            login_page = WeChatLoginPage(self.browser.page)
            return await login_page.is_logged_in()
        except Exception:
            return False
        finally:
            await self.browser.close()

    async def login(self) -> bool:
        """执行视频号扫码登录。"""
        try:
            await self.browser.close()
            await self.browser.launch(headless=False)

            from videopub.uploaders.wechat.pages.login_page import WeChatLoginPage

            login_page = WeChatLoginPage(self.browser.page)
            success = await login_page.wait_for_qrcode_scan(timeout=self._login_timeout)

            if success:
                await self.browser.save_cookies()
            return success
        except Exception:
            return False
        finally:
            await self.browser.close()

    async def upload(self, task: PlatformTask) -> UploadResult:
        """上传视频到视频号。"""
        try:
            await self.browser.launch(headless=True)

            from videopub.uploaders.wechat.pages.upload_page import WeChatUploadPage

            upload_page = WeChatUploadPage(self.browser.page)
            meta = task.meta

            await upload_page.navigate()
            await upload_page.upload_video(str(task.video_path))
            await upload_page.fill_title(meta.title)

            if meta.description:
                await upload_page.fill_description(meta.description)
            if meta.tags:
                await upload_page.add_tags(meta.tags)
            if meta.short_title:
                await upload_page.fill_short_title(meta.short_title)

            default_original = self.config.get("default_original", True)
            is_original = meta.is_original if meta.is_original is not None else default_original
            if is_original:
                await upload_page.set_original(True)

            if task.cover_path.exists():
                await upload_page.upload_cover(str(task.cover_path))
            if meta.scheduled_time:
                await upload_page.set_schedule(meta.scheduled_time)

            await upload_page.click_publish()
            await self.browser.save_cookies()

            return UploadResult(
                platform=Platform.WECHAT,
                success=True,
            )
        except Exception as exc:
            screenshot = await self.browser.take_screenshot("wechat_error")
            await self.browser.save_page_html("wechat_error")
            return UploadResult(
                platform=Platform.WECHAT,
                success=False,
                error=str(exc),
                screenshot_path=screenshot,
            )
        finally:
            await self.browser.close()

    async def post_comment(self, video_id: str, comment: str) -> bool:
        """在视频下发布首评。"""
        return False
