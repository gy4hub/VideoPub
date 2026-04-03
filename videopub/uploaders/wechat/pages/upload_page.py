"""视频号上传页 Page Object。"""


class WeChatUploadPage:
    """微信视频号上传页面操作。"""

    SELECTORS = {
        "upload_url": "https://channels.weixin.qq.com/platform/post/create",
        "file_input": "input[type='file']",
        "title_editor": "div.input-editor",
        "short_title_label": "text=短标题",
        "short_title_input": "span input[type='text']",
        "original_checkbox": "div.declare-original-checkbox input.ant-checkbox-input",
        "original_confirm_checkbox": "input.ant-checkbox-input:visible",
        "original_confirm_button": "button:has-text('声明原创')",
        "cover_button": "text=选择封面",
        "cover_upload_input": "input[type='file'][accept*='image']",
        "schedule_label": "label:has-text('定时')",
        "schedule_date_input": "input[placeholder='请选择发表时间']",
        "schedule_time_input": "input[placeholder='请选择时间']",
        "publish_button": "div.form-btns button:has-text('发表')",
        "upload_complete": "text=上传成功",
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
        file_input = self.page.locator(self.SELECTORS["file_input"]).first
        await file_input.set_input_files(video_path)

        try:
            await self.page.wait_for_selector(
                self.SELECTORS["upload_complete"],
                timeout=600_000,
            )
        except Exception:
            pass
        await self.page.wait_for_timeout(3000)

    async def fill_title(self, title: str):
        """填写标题。"""
        editor = self.page.locator(self.SELECTORS["title_editor"]).first
        await editor.click()
        await self.page.keyboard.type(title)

    async def add_tags(self, tags: list[str]):
        """添加话题标签。"""
        editor = self.page.locator(self.SELECTORS["title_editor"]).first
        await editor.click()
        for tag in tags:
            await self.page.keyboard.type(f"#{tag} ")
            await self.page.wait_for_timeout(500)

    async def fill_short_title(self, short_title: str):
        """填写短标题。"""
        if not short_title:
            return

        try:
            label = self.page.locator(self.SELECTORS["short_title_label"])
            if await label.count() > 0:
                input_field = self.page.locator(self.SELECTORS["short_title_input"]).first
                await input_field.click()
                await input_field.fill(short_title)
        except Exception:
            pass

    async def set_original(self, is_original: bool):
        """勾选原创声明。"""
        if not is_original:
            return

        try:
            checkbox = self.page.locator(self.SELECTORS["original_checkbox"])
            if await checkbox.count() > 0:
                await checkbox.click()
                await self.page.wait_for_timeout(1000)

                confirm_checkbox = self.page.locator(self.SELECTORS["original_confirm_checkbox"])
                if await confirm_checkbox.count() > 0:
                    await confirm_checkbox.first.click()

                confirm_button = self.page.locator(self.SELECTORS["original_confirm_button"])
                if await confirm_button.count() > 0:
                    await confirm_button.first.click()

                await self.page.wait_for_timeout(500)
        except Exception:
            pass

    async def upload_cover(self, cover_path: str):
        """上传自定义封面。"""
        try:
            cover_button = self.page.locator(self.SELECTORS["cover_button"])
            if await cover_button.count() > 0:
                await cover_button.click()
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
            schedule_label = self.page.locator(self.SELECTORS["schedule_label"]).nth(1)
            await schedule_label.click()
            await self.page.wait_for_timeout(500)

            date_input = self.page.locator(self.SELECTORS["schedule_date_input"])
            await date_input.click()
            await date_input.fill(scheduled_time.strftime("%Y-%m-%d"))
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(500)

            time_input = self.page.locator(self.SELECTORS["schedule_time_input"])
            await time_input.click()
            await time_input.fill(scheduled_time.strftime("%H:%M"))
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(500)
        except Exception:
            pass

    async def click_publish(self):
        """点击发表按钮。"""
        publish = self.page.locator(self.SELECTORS["publish_button"])
        await publish.click()
        await self.page.wait_for_timeout(3000)
