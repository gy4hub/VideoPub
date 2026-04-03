"""抖音上传页 Page Object。"""


class DouyinUploadPage:
    """抖音创作者中心上传页面操作。"""

    SELECTORS = {
        "upload_url": "https://creator.douyin.com/creator-micro/content/upload",
        "file_input": "input[type='file'][accept*='video']",
        "title_input": "input[type='text']",
        "description_editor": ".zone-container[contenteditable='true']",
        "cover_button": "text=选择封面",
        "cover_upload_input": "div[class*='cover'] input[type='file']",
        "schedule_radio": "[class^='radio']:has-text('定时发布')",
        "schedule_datetime_input": ".semi-input[placeholder='日期和时间']",
        "publish_button": "button:has-text('发布')",
        "upload_progress": "[class*='progress']",
        "upload_complete": "text=上传完成",
        "cover_confirm_button": "button:has-text('完成')",
    }

    def __init__(self, page):
        self.page = page

    async def navigate(self):
        """打开上传页面。"""
        await self.page.goto(self.SELECTORS["upload_url"], wait_until="domcontentloaded")
        await self.page.wait_for_timeout(2000)

    async def upload_video(self, video_path: str):
        """上传视频文件。"""
        file_input = self.page.locator(self.SELECTORS["file_input"])
        await file_input.set_input_files(video_path)

        try:
            await self.page.wait_for_selector(
                self.SELECTORS["upload_complete"],
                timeout=600_000,
            )
        except Exception:
            pass
        await self.page.wait_for_timeout(2000)

    async def fill_title(self, title: str):
        """填写标题。"""
        title_input = self.page.locator(self.SELECTORS["title_input"]).first
        await title_input.click()
        await title_input.fill("")
        await title_input.fill(title)

    async def fill_description(self, description: str):
        """填写描述。"""
        editor = self.page.locator(self.SELECTORS["description_editor"]).first
        await editor.click()
        await self.page.keyboard.type(description)

    async def add_tags(self, tags: list[str]):
        """添加话题标签。"""
        editor = self.page.locator(self.SELECTORS["description_editor"]).first
        await editor.click()
        for tag in tags:
            await self.page.keyboard.type(f"#{tag} ")
            await self.page.wait_for_timeout(500)

    async def upload_cover(self, cover_path: str):
        """上传封面图。"""
        try:
            await self.page.locator(self.SELECTORS["cover_button"]).click()
            await self.page.wait_for_timeout(1000)

            cover_input = self.page.locator(self.SELECTORS["cover_upload_input"])
            await cover_input.set_input_files(cover_path)
            await self.page.wait_for_timeout(2000)

            confirm = self.page.locator(self.SELECTORS["cover_confirm_button"])
            if await confirm.count() > 0:
                await confirm.first.click()
        except Exception:
            pass

    async def set_schedule(self, scheduled_time):
        """设置定时发布。"""
        if scheduled_time is None:
            return

        try:
            await self.page.locator(self.SELECTORS["schedule_radio"]).click()
            await self.page.wait_for_timeout(500)

            datetime_input = self.page.locator(self.SELECTORS["schedule_datetime_input"])
            await datetime_input.click()
            await datetime_input.fill(scheduled_time.strftime("%Y-%m-%d %H:%M"))
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(500)
        except Exception:
            pass

    async def click_publish(self):
        """点击发布按钮。"""
        publish = self.page.locator(self.SELECTORS["publish_button"])
        await publish.click()
        await self.page.wait_for_timeout(3000)
