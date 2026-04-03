"""抖音 Playwright 上传器。"""

from videopub.core.config_loader import load_platform_config
from videopub.core.models import Platform, PlatformTask, UploadResult
from videopub.uploaders.base import BaseUploader
from videopub.uploaders.browser_base import BrowserManager


class DouyinUploader(BaseUploader):
    def __init__(self):
        self.config = load_platform_config("douyin")
        cookie_path = self.config.get("cookie_path", "~/.videopub/douyin_cookie.json")
        self.browser = BrowserManager(cookie_path)

    async def check_session(self) -> bool:
        """检查抖音 Cookie 是否有效。"""
        try:
            await self.browser.launch(headless=True)
            from videopub.uploaders.douyin.pages.login_page import DouyinLoginPage

            login_page = DouyinLoginPage(self.browser.page)
            return await login_page.is_logged_in()
        except Exception:
            return False
        finally:
            await self.browser.close()

    async def login(self) -> bool:
        """执行抖音登录。"""
        try:
            await self.browser.close()
            await self.browser.launch(headless=False)

            from videopub.uploaders.douyin.pages.login_page import DouyinLoginPage

            login_page = DouyinLoginPage(self.browser.page)
            success = await login_page.wait_for_qrcode_scan(timeout=120)

            if success:
                await self.browser.save_cookies()
            return success
        except Exception:
            return False
        finally:
            await self.browser.close()

    async def upload(self, task: PlatformTask) -> UploadResult:
        """上传视频到抖音。"""
        try:
            await self.browser.launch(headless=True)

            from videopub.uploaders.douyin.pages.upload_page import DouyinUploadPage

            upload_page = DouyinUploadPage(self.browser.page)
            meta = task.meta

            await upload_page.navigate()
            await upload_page.upload_video(str(task.video_path))
            await upload_page.fill_title(meta.title)

            if meta.description:
                await upload_page.fill_description(meta.description)
            if meta.tags:
                await upload_page.add_tags(meta.tags)
            if task.cover_path.exists():
                await upload_page.upload_cover(str(task.cover_path))
            if meta.scheduled_time:
                await upload_page.set_schedule(meta.scheduled_time)

            await upload_page.click_publish()
            await self.browser.save_cookies()

            return UploadResult(
                platform=Platform.DOUYIN,
                success=True,
            )
        except Exception as exc:
            screenshot = await self.browser.take_screenshot("douyin_error")
            await self.browser.save_page_html("douyin_error")
            return UploadResult(
                platform=Platform.DOUYIN,
                success=False,
                error=str(exc),
                screenshot_path=screenshot,
            )
        finally:
            await self.browser.close()

    async def post_comment(self, video_id: str, comment: str) -> bool:
        """在视频下发布首评。"""
        return False
