"""视频号上传页 Page Object。"""

import hashlib
from difflib import SequenceMatcher
import time


class WeChatUploadPage:
    """微信视频号上传页面操作。"""

    SELECTORS = {
        "upload_url": "https://channels.weixin.qq.com/platform/post/create",
        "file_input": "input[type='file']",
        "title_editor": "div.input-editor, div[contenteditable='true']",
        "short_title_label": "text=短标题",
        "short_title_input": "input[placeholder*='概括视频主要内容'], input[placeholder*='主要内容']",
        "collection_trigger": "text=选择合集",
        "original_checkbox": "div.declare-original-checkbox input.ant-checkbox-input",
        "original_agree_label": "text=我已阅读并同意",
        "original_confirm_button": "button:has-text('声明原创')",
        "cover_button": "text=选择封面",
        "cover_upload_button": "text=上传封面",
        "cover_upload_input": "input[type='file'][accept*='image']",
        "schedule_datetime_input": "input[placeholder='请选择发表时间']",
        "publish_button": "button:has-text('发表')",
        "upload_complete": "text=上传成功",
        "cover_confirm_button": "button:has-text('完成'), button:has-text('确认'), button:has-text('确定')",
        "upload_cancel_button": "text=取消上传",
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
            # 兼容：等待“上传成功”、“替换”、“重新上传”等出现，或者仅仅是进度条元素
            # 无论怎样，都加上容错时间而不是死等 10 分钟。有些UI变动很快，
            # 只要把表单填完，发文的时候拦截检测也行。
            await self.page.wait_for_selector(
                "text=上传成功 >> visible=true",
                timeout=5000,  # 稍微等一下，如果在 5 秒内没看到，就不强求，去填字
            )
        except Exception:
            pass
        await self.page.wait_for_timeout(3000)

    async def fill_title(self, title: str):
        """填写标题。"""
        await self._focus_editor_end()
        await self.page.keyboard.type(title)

    async def fill_description(self, description: str):
        """填写描述 (追加在标题后面)"""
        await self._focus_editor_end()
        await self.page.keyboard.type("\n" + description)

    async def add_tags(self, tags: list[str]):
        """添加话题标签。"""
        if not tags:
            return

        await self._focus_editor_end()
        await self.page.keyboard.type(self._build_tag_text(tags))
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

                agree_label = self.page.locator("text=我已阅读并同意").first
                if await agree_label.count() > 0:
                    await agree_label.click()

                await self.page.wait_for_timeout(500)

                confirm_button = self.page.locator(".weui-desktop-dialog__ft button:has-text('声明原创'), .weui-desktop-dialog__ft .weui-desktop-btn:has-text('声明原创')").first
                if await confirm_button.count() == 0:
                    # Fallback
                    confirm_button = self.page.locator("button:has-text('声明原创') >> visible=true").last
                
                if await confirm_button.count() > 0:
                    await confirm_button.click()

                await self.page.wait_for_timeout(1000)
        except Exception:
            pass

    async def fill_collection(self, collection: str):
        """选择合集。"""
        if not collection:
            return

        try:
            trigger = self.page.locator(self.SELECTORS["collection_trigger"]).first
            if await trigger.count() == 0:
                return

            await trigger.click()
            await self.page.wait_for_timeout(500)

            option = self.page.get_by_text(collection, exact=True)
            if await option.count() == 0:
                option = self.page.get_by_text(collection)
            if await option.count() == 0:
                best_match = await self._find_best_visible_text_match(
                    target=collection,
                    threshold=0.45,
                    excluded={
                        "添加到合集",
                        "选择合集",
                        "创建新合集",
                        "位置",
                        "链接",
                        "活动",
                        "定时发表",
                        "短标题",
                        "声明原创",
                    },
                )
                if best_match:
                    option = self.page.get_by_text(best_match, exact=True)
            if await option.count() > 0:
                await option.last.click()
        except Exception:
            pass

    async def upload_cover(self, cover_path: str):
        """上传自定义封面。"""
        before_hash = await self._capture_cover_preview_hash()
        await self._wait_for_cover_preview_ready()
        await self._open_cover_editor()

        cover_input = await self._find_cover_upload_input()
        if cover_input is None:
            raise RuntimeError("视频号未找到封面上传输入框")

        await cover_input.set_input_files(cover_path)
        await self.page.wait_for_timeout(1500)

        confirm = await self._wait_for_cover_confirm_button()
        try:
            await confirm.click()
        except Exception:
            try:
                await confirm.click(force=True)
            except Exception:
                await confirm.evaluate("node => node.click()")

        await self._wait_for_cover_dialog_close()
        await self.page.wait_for_timeout(1000)

        if await self._cover_preview_changed(before_hash):
            return

        raise RuntimeError("视频号封面上传后未确认生效")

    async def set_schedule(self, scheduled_time):
        """设置定时发布。"""
        if scheduled_time is None:
            return

        expected = scheduled_time.strftime("%Y-%m-%d %H:%M")

        if not await self._activate_schedule_mode():
            raise RuntimeError("视频号未找到定时发布控件，已停止自动发布")

        datetime_input = self.page.locator(self.SELECTORS["schedule_datetime_input"]).first
        if await datetime_input.count() == 0:
            raise RuntimeError("视频号未找到定时发布时间输入框，已停止自动发布")

        await datetime_input.click()
        panel = self.page.locator(".weui-desktop-picker__panel").first
        if await panel.count() == 0:
            raise RuntimeError("视频号未打开定时日期面板，已停止自动发布")

        header_text = await panel.locator(".weui-desktop-picker__panel__hd").first.inner_text()
        target_header = f"{scheduled_time.year}年 {scheduled_time.month:02d}月"
        if target_header not in header_text.replace("\n", " "):
            raise RuntimeError(
                f"视频号日期面板月份不匹配，期望 {target_header}，实际 {header_text.strip()}"
            )

        await self._select_picker_day(panel, scheduled_time.day)
        await self._set_picker_time(scheduled_time.strftime("%H:%M"))
        await self._confirm_picker_selection(panel)

        value = await self._read_input_value(datetime_input)
        if expected not in value:
            raise RuntimeError(
                f"视频号定时发布时间未生效，期望 {expected}，实际 {value or '空'}"
            )

    async def click_publish(self):
        """点击发表按钮。"""
        await self._wait_for_upload_to_finish(timeout_ms=600_000)

        publish = await self._find_visible_publish_button()
        await publish.scroll_into_view_if_needed()

        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            try:
                if await publish.is_enabled():
                    break
            except Exception:
                pass
            await self.page.wait_for_timeout(1000)

        await publish.click(timeout=30_000)
        try:
            await self.page.wait_for_url(
                lambda url: "/platform/post/create" not in url,
                timeout=30_000,
            )
            return
        except Exception:
            await self.page.wait_for_timeout(3000)

        if "/platform/post/create" in self.page.url:
            raise RuntimeError("视频号点击发表后仍停留在发布页，未确认发布成功")

    async def _find_visible_publish_button(self):
        """优先返回当前页面中真正可见的发表按钮。"""
        candidate_groups = [
            self.page.get_by_role("button", name="发表", exact=True),
            self.page.get_by_role("button", name="发表"),
            self.page.locator(self.SELECTORS["publish_button"]),
        ]

        for group in candidate_groups:
            count = await group.count()
            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    if await candidate.is_visible():
                        return candidate
                except Exception:
                    pass

        return self.page.locator(self.SELECTORS["publish_button"]).last

    async def _focus_editor_end(self):
        """把光标稳定移动到标题编辑器末尾。"""
        editor = self.page.locator(self.SELECTORS["title_editor"]).first
        await editor.click()
        try:
            await editor.evaluate(
                """node => {
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(node);
                    range.collapse(false);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    node.focus();
                }"""
            )
        except Exception:
            try:
                await self.page.keyboard.press("End")
            except Exception:
                pass
        return editor

    async def _find_visible_cover_button(self):
        """优先返回当前页面中真正能打开编辑器的封面预览节点。"""
        candidate_groups = [
            self.page.locator("img.cover-img-vertical"),
            self.page.locator("[class*='cover-img-vertical']"),
            self.page.locator("[class*='cover-img']"),
        ]

        for group in candidate_groups:
            try:
                count = await group.count()
            except Exception:
                continue

            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    if await candidate.is_visible():
                        return candidate
                except Exception:
                    continue

        return None

    async def _wait_for_cover_preview_ready(self):
        """等待主表单右侧封面预览生成到可点击状态。"""
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            button = await self._find_visible_cover_button()
            if button is not None:
                return
            await self.page.wait_for_timeout(500)
        raise RuntimeError("视频号封面预览未生成，无法进入编辑封面")

    async def _open_cover_editor(self):
        """打开封面编辑弹层。"""
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if await self._cover_dialog_is_open():
                return

            cover_button = await self._find_visible_cover_button()
            if cover_button is None:
                await self.page.wait_for_timeout(500)
                continue

            try:
                await cover_button.scroll_into_view_if_needed()
            except Exception:
                pass

            clicked = False
            for action in (
                lambda: cover_button.click(timeout=2_000),
                lambda: cover_button.click(force=True, timeout=2_000),
                lambda: cover_button.evaluate(
                    """node => {
                        const target = node.closest('[class*="cover"]') || node.parentElement || node;
                        target.click();
                    }"""
                ),
            ):
                try:
                    await action()
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                await self.page.wait_for_timeout(500)
                continue

            await self.page.wait_for_timeout(1200)
            if await self._cover_dialog_is_open():
                return

        raise RuntimeError("视频号未能打开封面编辑弹层")

    async def _find_visible_cover_dialog(self):
        """返回当前真正可见的“编辑封面”弹层。"""
        wrappers = self.page.locator(".weui-desktop-dialog__wrp")
        count = await wrappers.count()

        for idx in range(count):
            wrapper = wrappers.nth(idx)
            try:
                if not await wrapper.is_visible():
                    continue
                if await wrapper.locator(".cover-set-wrap, .single-cover-uploader-wrap").count() > 0:
                    return wrapper
                text = (await wrapper.inner_text()).strip()
                if "编辑封面" in text or "上传封面" in text:
                    return wrapper
            except Exception:
                continue

        dialogs = self.page.locator(".weui-desktop-dialog")
        count = await dialogs.count()
        for idx in range(count):
            dialog = dialogs.nth(idx)
            try:
                if not await dialog.is_visible():
                    continue
                if await dialog.locator(".cover-set-wrap, .single-cover-uploader-wrap").count() > 0:
                    return dialog
                text = (await dialog.inner_text()).strip()
                if "编辑封面" in text or "上传封面" in text:
                    return dialog
            except Exception:
                continue

        return None

    async def _cover_dialog_is_open(self) -> bool:
        """判断封面编辑弹层是否已打开。"""
        dialog = await self._find_visible_cover_dialog()
        return dialog is not None

    async def _find_cover_upload_input(self):
        """查找页面中的封面上传 input。"""
        dialog = await self._find_visible_cover_dialog()
        if dialog is None:
            return None

        inputs = [
            dialog.locator(".single-cover-uploader-wrap input[type='file']").first,
            dialog.locator("input[type='file'][accept*='image']").first,
            dialog.locator("input[type='file'][accept*='.jpg']").first,
            dialog.locator("input[type='file'][accept*='.png']").first,
            dialog.locator("input[type='file']").first,
        ]

        for locator in inputs:
            try:
                if await locator.count() > 0:
                    return locator
            except Exception:
                continue

        return None

    async def _find_visible_cover_confirm_button(self):
        """只返回当前可见的封面确认按钮。"""
        dialog = await self._find_visible_cover_dialog()
        if dialog is None:
            return None

        candidate_groups = [
            dialog.get_by_role("button", name="确认", exact=True),
            dialog.get_by_role("button", name="完成", exact=True),
            dialog.get_by_role("button", name="确定", exact=True),
            dialog.locator(".weui-desktop-dialog__ft button:has-text('确认')"),
            dialog.locator(".weui-desktop-dialog__ft button:has-text('完成')"),
            dialog.locator(".weui-desktop-dialog__ft button:has-text('确定')"),
            dialog.locator(self.SELECTORS["cover_confirm_button"]),
        ]

        for group in candidate_groups:
            try:
                count = await group.count()
            except Exception:
                continue
            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    if await candidate.is_visible():
                        return candidate
                except Exception:
                    continue

        return None

    async def _wait_for_cover_confirm_button(self):
        """等待弹层底部确认按钮真正出现。"""
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            confirm = await self._find_visible_cover_confirm_button()
            if confirm is not None:
                return confirm
            await self.page.wait_for_timeout(500)
        raise RuntimeError("视频号未找到封面确认按钮")

    async def _wait_for_cover_dialog_close(self):
        """等待封面编辑弹层关闭。"""
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if not await self._cover_dialog_is_open():
                return
            await self.page.wait_for_timeout(500)
        raise RuntimeError("视频号封面确认后弹层未关闭")

    async def _capture_cover_preview_hash(self) -> str | None:
        """对主表单封面预览区截图取 hash，用真实视觉变化判断是否应用成功。"""
        candidate_groups = [
            self.page.locator("img.cover-img-vertical").last,
            self.page.locator("[class*='cover-img-vertical']").last,
            self.page.locator("[class*='cover-img']").last,
        ]

        for group in candidate_groups:
            try:
                count = await group.count()
            except Exception:
                continue
            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    if not await candidate.is_visible():
                        continue
                    screenshot = await candidate.screenshot(type="png")
                    return hashlib.sha1(screenshot).hexdigest()
                except Exception:
                    continue

        return None

    async def _cover_preview_changed(self, before_hash: str | None) -> bool:
        """判断主表单封面预览图是否真的变了。"""
        current_hash = await self._capture_cover_preview_hash()
        if current_hash is None:
            return False
        if before_hash is None:
            return True
        return current_hash != before_hash

    @staticmethod
    def _build_tag_text(tags: list[str]) -> str:
        """生成带换行的话题文本，避免紧贴正文。"""
        visible_tags = [tag.strip() for tag in tags if tag and tag.strip()]
        return "\n" + " ".join(f"#{tag}" for tag in visible_tags) + " "

    async def _wait_for_upload_to_finish(self, timeout_ms: int):
        """等待上传过程结束，避免在上传中提前点击发表。"""
        cancel_button = self.page.locator(self.SELECTORS["upload_cancel_button"]).first
        deadline = time.monotonic() + timeout_ms / 1000

        while time.monotonic() < deadline:
            try:
                if await cancel_button.count() == 0 or not await cancel_button.is_visible():
                    return
            except Exception:
                return
            await self.page.wait_for_timeout(1000)

    async def _activate_schedule_mode(self) -> bool:
        """尝试切换到定时发布模式。"""
        actions = [
            lambda: self.page.get_by_role("radio", name="定时发表", exact=True).check(timeout=3_000),
            lambda: self.page.get_by_role("radio", name="定时", exact=True).check(timeout=3_000),
            lambda: self.page.locator("input[type='radio']").nth(1).check(force=True, timeout=3_000),
            lambda: self.page.get_by_text("定时发表", exact=True).last.click(timeout=3_000),
            lambda: self.page.get_by_text("定时", exact=True).last.click(timeout=3_000),
        ]

        for action in actions:
            try:
                await action()
                await self.page.wait_for_timeout(500)
                if await self.page.locator(self.SELECTORS["schedule_datetime_input"]).count() > 0:
                    return True
            except Exception:
                continue
        return False

    async def _read_input_value(self, locator) -> str:
        """读取 input 当前值。"""
        try:
            value = await locator.input_value()
            if value:
                return value
        except Exception:
            pass

        try:
            return await locator.get_attribute("value") or ""
        except Exception:
            return ""

    async def _set_input_value(self, locator, value: str):
        """给 input 写值，并触发前端监听。"""
        await locator.evaluate(
            """(node, nextValue) => {
                const descriptor = Object.getOwnPropertyDescriptor(
                  HTMLInputElement.prototype,
                  'value',
                );
                descriptor.set.call(node, nextValue);
                node.dispatchEvent(new Event('input', { bubbles: true }));
                node.dispatchEvent(new Event('change', { bubbles: true }));
                node.dispatchEvent(new Event('blur', { bubbles: true }));
            }""",
            value,
        )

    async def _select_picker_day(self, panel, day: int):
        """在日期面板中选择具体日期。"""
        day_text = str(day)
        candidates = panel.get_by_text(day_text, exact=True)
        count = await candidates.count()

        for idx in range(count):
            candidate = candidates.nth(idx)
            try:
                if not await candidate.is_visible():
                    continue
                class_name = await candidate.get_attribute("class") or ""
                if any(flag in class_name for flag in ("disabled", "other", "out", "gray")):
                    continue
                await candidate.click()
                return
            except Exception:
                continue

        raise RuntimeError(f"视频号日期面板未找到可点击的 {day} 号")

    async def _set_picker_time(self, time_value: str):
        """设置日期面板中的时间输入。"""
        time_input = self.page.locator("input[placeholder='请选择时间']").first
        if await time_input.count() == 0:
            raise RuntimeError("视频号日期面板未找到时间输入框")

        await time_input.click()
        try:
            await time_input.press("Meta+A")
        except Exception:
            try:
                await time_input.press("Control+A")
            except Exception:
                pass
        try:
            await time_input.press("Backspace")
            await time_input.type(time_value, delay=80)
        except Exception:
            await self._set_input_value(time_input, time_value)
        await self.page.keyboard.press("Enter")
        await self.page.wait_for_timeout(500)

    async def _confirm_picker_selection(self, panel):
        """滚动日期面板到底部并点击确认按钮。"""
        confirm_candidates = [
            panel.get_by_text("确定", exact=True),
            panel.get_by_text("确认", exact=True),
            panel.get_by_text("完成", exact=True),
            panel.get_by_role("button", name="确定", exact=True),
            panel.get_by_role("button", name="确认", exact=True),
            panel.get_by_role("button", name="完成", exact=True),
            self.page.get_by_text("确定", exact=True),
            self.page.get_by_text("确认", exact=True),
            self.page.get_by_text("完成", exact=True),
            self.page.get_by_role("button", name="确定", exact=True),
            self.page.get_by_role("button", name="确认", exact=True),
            self.page.get_by_role("button", name="完成", exact=True),
            panel.locator("button:has-text('确定')"),
            panel.locator("button:has-text('确认')"),
            panel.locator("button:has-text('完成')"),
            panel.locator(":text('确定')"),
            panel.locator(":text('确认')"),
            panel.locator(":text('完成')"),
        ]

        for _ in range(3):
            try:
                await self.page.mouse.wheel(0, 400)
                await self.page.wait_for_timeout(250)
            except Exception:
                break

        scroll_targets = [
            panel,
            panel.locator(".weui-desktop-picker"),
            panel.locator(".weui-desktop-picker__bd"),
            panel.locator(".weui-desktop-picker__panel__bd"),
        ]

        for target in scroll_targets:
            try:
                if await target.count() == 0:
                    continue
                await target.evaluate(
                    """node => {
                        node.scrollTop = node.scrollHeight;
                        node.dispatchEvent(new Event('scroll', { bubbles: true }));
                    }"""
                )
                await self.page.wait_for_timeout(300)
            except Exception:
                continue

        for candidate_group in confirm_candidates:
            try:
                count = await candidate_group.count()
            except Exception:
                continue

            for idx in range(count):
                candidate = candidate_group.nth(idx)
                try:
                    if not await candidate.is_visible():
                        continue
                    await candidate.scroll_into_view_if_needed()
                    await candidate.click()
                    await self.page.wait_for_timeout(800)
                    return
                except Exception:
                    continue

        for x, y in ((420, 220), (520, 280), (640, 240)):
            try:
                await self.page.mouse.click(x, y)
                await self.page.wait_for_timeout(600)
                return
            except Exception:
                continue

    async def _find_best_visible_text_match(
        self,
        *,
        target: str,
        threshold: float,
        excluded: set[str],
    ) -> str | None:
        """从当前页面可见文本中找最接近 target 的候选项。"""
        body_text = await self.page.locator("body").inner_text()
        best_text = None
        best_score = threshold

        for raw_line in body_text.splitlines():
            line = raw_line.strip()
            if (
                not line
                or line in excluded
                or len(line) > 20
                or line.startswith("共")
            ):
                continue

            score = SequenceMatcher(None, target, line).ratio()
            if score > best_score:
                best_text = line
                best_score = score

        return best_text
