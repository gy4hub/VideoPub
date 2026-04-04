"""抖音上传页 Page Object。"""

import hashlib
import time
from difflib import SequenceMatcher


class DouyinUploadPage:
    """抖音创作者中心上传页面操作。"""

    SELECTORS = {
        "upload_url": "https://creator.douyin.com/creator-micro/content/upload",
        "home_url": "https://creator.douyin.com/creator-micro/home",
        "file_input": "input[type='file']",
        "new_publish_entry": "text=发布视频",
        "intro_modal_ack": "text=我知道了",
        "title_input": "input[type='text']",
        "description_editor": ".zone-container[contenteditable='true']",
        "cover_button": "text=选择封面",
        "cover_upload_button": "text=上传封面",
        "cover_upload_input": ".semi-upload-hidden-input, .semi-upload-hidden-input-replace",
        "schedule_radio": "label:has-text('定时发布'), label:has(input[value='1']), [class^='radio']:has-text('定时发布')",
        "schedule_datetime_input": "input[placeholder*='日期和时间'], input[placeholder*='日期'], input[placeholder*='时间']",
        "publish_button": "button:has-text('发布')",
        "upload_progress": "[class*='progress']",
        "upload_complete": "text=上传完成",
        "cover_confirm_button": "button:has-text('保存'), button:has-text('完成'), button:has-text('确认')",
    }

    def __init__(self, page):
        self.page = page

    async def navigate(self):
        """打开上传页面。"""
        await self.page.goto(self.SELECTORS["upload_url"], wait_until="domcontentloaded")
        await self.page.wait_for_timeout(2000)

        await self._dismiss_intro_modal()
        await self._resolve_unfinished_draft(prefer_continue=False)
        if await self._is_upload_ready():
            return

        await self.page.goto(self.SELECTORS["home_url"], wait_until="domcontentloaded")
        await self.page.wait_for_timeout(2000)
        await self._dismiss_intro_modal()
        await self._resolve_unfinished_draft(prefer_continue=False)

        publish_entry = self.page.get_by_text("发布视频", exact=True).first
        await publish_entry.click()
        await self._resolve_unfinished_draft(prefer_continue=False)
        await self.page.wait_for_url("**/creator-micro/content/upload", timeout=15_000)
        await self.page.wait_for_timeout(2000)
        await self._dismiss_intro_modal()
        await self.page.wait_for_selector(self.SELECTORS["file_input"], timeout=15_000)

    async def upload_video(self, video_path: str):
        """上传视频文件。"""
        file_input = self.page.locator(self.SELECTORS["file_input"]).first
        await file_input.set_input_files(video_path, timeout=120_000)

        try:
            # 放宽/跳过对上传进度的强制文字识别，交给最后按键保护
            await self.page.wait_for_selector(
                "text=上传成功 >> visible=true",
                timeout=5000,
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
        await self._focus_editor_end()
        await self.page.keyboard.type(description)

    async def add_tags(self, tags: list[str]):
        """添加话题标签。"""
        if not tags:
            return

        await self._focus_editor_end()
        await self.page.keyboard.type(self._build_tag_text(tags))
        await self.page.wait_for_timeout(500)

    async def upload_cover(self, cover_path: str, landscape_cover_path: str | None = None):
        """按平台真实路径上传竖封面，再设置横封面。"""
        cover_button = await self._find_visible_cover_button()
        if cover_button is None:
            raise RuntimeError("抖音未找到封面按钮")

        await cover_button.click()
        await self.page.wait_for_timeout(1000)

        await self._upload_cover_via_editor(cover_path, variant_label="竖封面3:4")
        await self._switch_to_horizontal_cover_editor()
        await self.page.wait_for_timeout(1200)
        if landscape_cover_path:
            await self._upload_cover_via_editor(
                landscape_cover_path,
                variant_label="横封面4:3",
            )

        await self._complete_cover_editor("封面编辑器")
        await self._wait_for_cover_cards_ready()

    async def fill_collection(self, collection: str):
        """选择抖音合集。"""
        if not collection:
            return

        trigger_groups = [
            self.page.locator(
                "xpath=(//*[normalize-space(.)='添加合集'])[last()]"
                "/following::*[contains(normalize-space(.), '请选择合集')][1]"
            ),
            self.page.get_by_text("请选择合集", exact=True),
            self.page.get_by_text("请选择合集"),
        ]

        trigger = None
        for group in trigger_groups:
            try:
                count = await group.count()
            except Exception:
                continue
            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    if await candidate.is_visible():
                        trigger = candidate
                        break
                except Exception:
                    continue
            if trigger is not None:
                break

        if trigger is None:
            raise RuntimeError("抖音未找到合集选择入口")

        try:
            await trigger.click()
        except Exception:
            await trigger.click(force=True)
        await self.page.wait_for_timeout(800)

        option_groups = [
            self.page.get_by_role("option", name=collection, exact=True),
            self.page.get_by_text(collection, exact=True),
            self.page.get_by_text(collection),
        ]
        option = None
        for group in option_groups:
            try:
                count = await group.count()
            except Exception:
                continue
            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    if await candidate.is_visible():
                        option = candidate
                        break
                except Exception:
                    continue
            if option is not None:
                break

        if option is None:
            best_match = await self._find_best_visible_text_match(
                target=collection,
                threshold=0.45,
                excluded={
                    "添加合集",
                    "请选择合集",
                    "合集",
                    "继续添加",
                    "共创身份",
                    "位置",
                    "带货模式",
                    "输入地理位置",
                },
            )
            if best_match:
                option = self.page.get_by_text(best_match, exact=True)

        if option is None:
            raise RuntimeError(f"抖音未找到合集选项: {collection}")

        try:
            await option.click()
        except Exception:
            await option.click(force=True)
        await self.page.wait_for_timeout(800)

        selected_text = await self._read_selected_collection_text()
        if collection not in selected_text:
            raise RuntimeError(
                f"抖音合集未正确选中，期望 {collection}，实际 {selected_text or '空'}"
            )

    async def set_schedule(self, scheduled_time):
        """设置定时发布。"""
        if scheduled_time is None:
            return

        await self._finalize_cover_editors()

        expected = scheduled_time.strftime("%Y-%m-%d %H:%M")
        if not await self._activate_schedule_mode():
            raise RuntimeError("抖音未找到定时发布控件，已停止自动发布")

        datetime_input = await self._find_schedule_datetime_input()
        if datetime_input is None:
            raise RuntimeError("抖音未找到定时发布时间输入框，已停止自动发布")

        try:
            await datetime_input.click()
        except Exception:
            await self._finalize_cover_editors()
            await datetime_input.click(force=True)
        await datetime_input.fill(expected)
        await datetime_input.press("Enter")
        await self.page.wait_for_timeout(500)
        await self.page.wait_for_timeout(800)

        value = await self._read_input_value(datetime_input)
        if expected not in value:
            raise RuntimeError(
                f"抖音定时发布时间未生效，期望 {expected}，实际 {value or '空'}"
            )
        if not await self._is_publish_form_page():
            raise RuntimeError("抖音设置定时后跳离发布页，已停止自动发布")

    async def click_publish(self):
        """点击发布按钮。"""
        if not await self._is_publish_form_page():
            raise RuntimeError("抖音当前不在发布页，未执行发布")

        await self._wait_for_publish_ready(timeout_ms=600_000)
        await self._dismiss_intro_modal()
        await self._scroll_to_publish_footer()

        publish = await self._find_visible_publish_button()
        try:
            await publish.scroll_into_view_if_needed()
        except Exception:
            pass

        await publish.click(timeout=600_000)
        if await self._wait_for_publish_outcome(timeout_ms=180_000):
            return

        if await self._resolve_unfinished_draft(prefer_continue=True):
            publish = await self._find_visible_publish_button()
            await publish.click(timeout=30_000)
            if await self._wait_for_publish_outcome(timeout_ms=180_000):
                return

        raise RuntimeError("抖音点击发布后仍停留在发布页，未确认发布成功")

    async def _dismiss_intro_modal(self):
        """关闭首页可能出现的引导弹窗。"""
        try:
            ack = self.page.locator(self.SELECTORS["intro_modal_ack"]).first
            if await ack.count() > 0 and await ack.is_visible():
                await ack.click()
                await self.page.wait_for_timeout(500)
        except Exception:
            pass

    async def _is_upload_ready(self) -> bool:
        """判断当前是否已经处于上传页。"""
        try:
            return (
                "creator-micro/content/upload" in self.page.url
                and await self.page.locator(self.SELECTORS["file_input"]).count() > 0
            )
        except Exception:
            return False

    async def _activate_schedule_mode(self) -> bool:
        """尝试切换到定时发布模式。"""
        if await self._is_schedule_mode_active():
            return True

        toggle_label = await self._find_schedule_toggle_label()
        toggle_input = await self._find_schedule_toggle_input()
        actions = []

        if toggle_label is not None:
            actions.extend(
                [
                    lambda: toggle_label.click(timeout=3_000),
                    lambda: toggle_label.click(timeout=3_000, force=True),
                    lambda: toggle_label.evaluate("node => node.click()"),
                ]
            )

        if toggle_input is not None:
            actions.extend(
                [
                    lambda: toggle_input.check(timeout=3_000),
                    lambda: toggle_input.click(timeout=3_000, force=True),
                    lambda: toggle_input.evaluate("node => node.click()"),
                ]
            )

        actions.extend(
            [
                lambda: self.page.get_by_text("定时发布", exact=True).last.click(timeout=3_000),
                lambda: self.page.locator(self.SELECTORS["schedule_radio"]).last.click(timeout=3_000),
                lambda: self.page.get_by_role("checkbox", name="定时发布", exact=True).check(timeout=3_000),
                lambda: self.page.get_by_role("radio", name="定时发布", exact=True).check(timeout=3_000),
            ]
        )

        for action in actions:
            try:
                await action()
                await self.page.wait_for_timeout(800)
                if await self._is_schedule_mode_active():
                    return True
            except Exception:
                continue
        return False

    async def _is_schedule_mode_active(self) -> bool:
        """判断当前是否已经切到定时发布。"""
        checkbox = await self._find_schedule_toggle_input()
        if checkbox is None:
            checkbox = self.page.locator("input[value='1']").last
        try:
            if await checkbox.count() > 0 and await checkbox.is_checked():
                return True
        except Exception:
            pass

        try:
            if await self._find_schedule_datetime_input() is not None:
                return True
        except Exception:
            pass

        return False

    async def _find_schedule_datetime_input(self):
        """查找发布时间输入框，优先定位在定时发布区域附近。"""
        schedule_section = self._schedule_section()
        candidate_groups = [
            schedule_section.locator(
                "input:not([type='checkbox']):not([type='file']):not([type='hidden'])"
            ),
            self.page.locator(
                "xpath=(//label[contains(normalize-space(.), '定时发布')])[last()]"
                "/following::input[not(@type='checkbox') and not(@type='file')][1]"
            ),
            self.page.locator(
                "xpath=(//*[contains(normalize-space(.), '发布时间')])[last()]"
                "/following::input[not(@type='checkbox') and not(@type='file')][1]"
            ),
            self.page.locator(self.SELECTORS["schedule_datetime_input"]),
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
                    input_type = (await candidate.get_attribute("type") or "").lower()
                    if input_type in {"checkbox", "file", "hidden"}:
                        continue
                    return candidate
                except Exception:
                    continue

        return None

    async def _read_selected_collection_text(self) -> str:
        """读取添加合集区域当前已显示的合集文本。"""
        candidate_groups = [
            self.page.locator(
                "xpath=(//*[normalize-space(.)='添加合集'])[last()]/following::*[1]"
            ),
            self.page.locator(
                "xpath=(//*[normalize-space(.)='添加合集'])[last()]/following::div[contains(., '第')][1]"
            ),
            self.page.locator(
                "xpath=(//*[normalize-space(.)='添加合集'])[last()]"
                "/following::*[contains(normalize-space(.), '请选择合集') or string-length(normalize-space(.)) > 0][1]"
            ),
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
                    text = " ".join((await candidate.inner_text()).split())
                    if text:
                        return text
                except Exception:
                    continue

        return ""

    def _schedule_section(self):
        """返回发布时间区块，避免误操作其他 checkbox。"""
        return self.page.locator(
            "xpath=(//*[normalize-space(.)='发布时间'])[last()]"
            "/ancestor::div[contains(@class, 'content-obt4oA')][1]"
        )

    async def _find_schedule_toggle_label(self):
        """定位发布时间区块中的“定时发布”标签。"""
        candidate_groups = [
            self._schedule_section().locator("label").filter(has_text="定时发布"),
            self.page.locator("xpath=(//label[contains(normalize-space(.), '定时发布')])[last()]"),
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

    async def _find_schedule_toggle_input(self):
        """定位发布时间区块中的定时发布 checkbox。"""
        candidate_groups = [
            self._schedule_section().locator("input[value='1']"),
            self.page.locator(
                "xpath=(//label[contains(normalize-space(.), '定时发布')])[last()]//input[@value='1']"
            ),
        ]

        for group in candidate_groups:
            try:
                count = await group.count()
            except Exception:
                continue

            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    disabled = await candidate.is_disabled()
                    if not disabled:
                        return candidate
                except Exception:
                    continue

        return None

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

    async def _find_visible_publish_button(self):
        """优先返回当前页面中真正可见的发布按钮。"""
        candidate_groups = [
            self.page.locator(
                ".content-confirm-container-Wp91G7 button.button-dhlUZE.primary-cECiOJ.fixed-J9O8Yw"
            ),
            self.page.locator(
                "xpath=(//*[normalize-space(.)='发布设置'])[last()]"
                "/following::button[normalize-space(.)='发布'][1]"
            ),
            self.page.get_by_role("button", name="发布", exact=True),
            self.page.get_by_role("button", name="发布"),
            self.page.locator(self.SELECTORS["publish_button"]),
            self.page.locator(".button-dhlUZE.primary-cECiOJ.fixed-J9O8Yw"),
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

        return self.page.get_by_role("button", name="发布", exact=True).first

    async def _focus_editor_end(self):
        """把光标稳定移动到描述编辑器末尾。"""
        editor = self.page.locator(self.SELECTORS["description_editor"]).first
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
        """返回主页面中竖封面卡片上的“选择封面”按钮。"""
        candidate_groups = [
            self.page.locator(".coverControl-CjlzqC").filter(has_text="竖封面3:4").get_by_text(
                "选择封面",
                exact=True,
            ),
            self.page.locator(
                "xpath=(//*[contains(normalize-space(.), '竖封面3:4')])[last()]"
                "/ancestor::div[contains(@class, 'coverControl')][1]"
            ),
            self.page.get_by_role("button", name="选择封面", exact=True),
            self.page.get_by_text("选择封面", exact=True),
            self.page.locator(self.SELECTORS["cover_button"]),
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

    async def _find_visible_cover_confirm_button(self):
        """返回当前可见的封面保存/确认按钮。"""
        candidate_groups = [
            self.page.get_by_role("button", name="保存", exact=True),
            self.page.get_by_role("button", name="完成", exact=True),
            self.page.get_by_role("button", name="确认", exact=True),
            self.page.locator(self.SELECTORS["cover_confirm_button"]),
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

    async def _upload_cover_via_editor(self, cover_path: str, variant_label: str):
        """在当前封面编辑器中点击上传封面并完成内层保存。"""
        before_hash = await self._capture_cover_editor_preview_hash()
        await self._upload_cover_file_in_modal(cover_path, before_hash)
        confirm = await self._find_inner_cover_confirm_button()
        if confirm is not None:
            await self._save_inner_cover_modal(variant_label)
        await self._wait_for_cover_editor_preview_applied(before_hash, variant_label)

    async def _click_editor_upload_button(self):
        """点击编辑器里的“上传封面”按钮，确保走平台真实交互。"""
        upload_button = await self._find_visible_text_button("上传封面")
        if upload_button is None:
            return

        try:
            await upload_button.click()
        except Exception:
            try:
                await upload_button.click(force=True)
            except Exception:
                await upload_button.evaluate("node => node.click()")
        await self.page.wait_for_timeout(500)

    async def _upload_cover_file_in_modal(
        self,
        cover_path: str,
        before_hash: str | None,
    ):
        """在当前封面弹窗中上传图片。"""
        candidate_groups = [
            self.page.locator(".container-XzaV9h.upload-ZOJTUA input[type='file']"),
            self.page.locator(".selectArea-BCIYQD input[type='file']"),
            self.page.locator(".main-DAkOod input[type='file']"),
            self.page.locator(".upload-ZOJTUA input[type='file']"),
            self.page.locator("input.upload-btn-input-UY_qeY[type='file']"),
            self.page.locator(
                ".upload-ZOJTUA input[type='file'], "
                ".semi-upload input[type='file'], "
                "input[type='file']"
            ),
        ]

        for group in candidate_groups:
            try:
                count = await group.count()
            except Exception:
                count = 0

            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    accept = (await candidate.get_attribute("accept") or "").lower()
                    if "video" in accept:
                        continue

                    await candidate.set_input_files(cover_path)
                    await self.page.wait_for_timeout(1800)

                    if await self._find_inner_cover_confirm_button() is not None:
                        return
                    if await self._cover_editor_preview_changed(before_hash):
                        return
                except Exception:
                    continue

        raise RuntimeError("抖音未找到正确的封面图片上传输入框")

    async def _wait_for_cover_editor_preview_applied(
        self,
        before_hash: str | None,
        variant_label: str,
        timeout_seconds: int = 12,
    ):
        """等待外层封面编辑器主预览视觉上发生变化。"""
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if await self._cover_editor_preview_changed(before_hash):
                return
            await self.page.wait_for_timeout(400)

        raise RuntimeError(f"抖音{variant_label}上传后主预览未发生变化")

    async def _capture_cover_editor_preview_hash(self) -> str | None:
        """对封面编辑器主预览区域截图取 hash，用视觉变化判断是否应用成功。"""
        candidate_groups = [
            self.page.locator(".main-DAkOod"),
            self.page.locator(".container-qVqwfQ"),
            self.page.locator(".preview-gZLFIG"),
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
                    box = await candidate.bounding_box()
                    if not box or box["width"] * box["height"] < 40_000:
                        continue
                    screenshot = await candidate.screenshot(type="png")
                    return hashlib.sha1(screenshot).hexdigest()
                except Exception:
                    continue

        return None

    async def _cover_editor_preview_changed(self, before_hash: str | None) -> bool:
        """判断主预览截图 hash 是否发生变化。"""
        try:
            current_hash = await self._capture_cover_editor_preview_hash()
        except Exception:
            return False

        if current_hash is None:
            return False
        if before_hash is None:
            return True
        return current_hash != before_hash

    async def _switch_to_horizontal_cover_editor(self):
        """在大编辑器中切换到设置横封面。"""
        switch_button = await self._wait_for_cover_footer_button("设置横封面")
        if switch_button is None:
            raise RuntimeError("抖音未找到设置横封面按钮")

        try:
            await switch_button.click()
        except Exception:
            try:
                await switch_button.click(force=True)
            except Exception:
                await switch_button.evaluate("node => node.click()")
        await self.page.wait_for_timeout(1200)

    async def _save_inner_cover_modal(self, variant_label: str):
        """处理上传图片后出现的小保存弹窗。"""
        for _ in range(3):
            confirm = await self._find_inner_cover_confirm_button()
            if confirm is None:
                raise RuntimeError(f"抖音未找到 {variant_label} 内层保存按钮")

            try:
                await confirm.click()
            except Exception:
                try:
                    await confirm.click(force=True)
                except Exception:
                    await confirm.evaluate("node => node.click()")

            if await self._wait_for_inner_cover_modal_to_close(timeout_seconds=6):
                await self.page.wait_for_timeout(1200)
                return
            await self.page.wait_for_timeout(800)

        raise RuntimeError(f"抖音{variant_label}保存后内层弹窗未关闭")

    async def _complete_cover_editor(self, variant_label: str):
        """在大封面编辑器中点击完成。"""
        done_button = await self._wait_for_cover_footer_button("完成")
        if done_button is None:
            raise RuntimeError(f"抖音未找到 {variant_label} 完成按钮")

        try:
            await done_button.click()
        except Exception:
            try:
                await done_button.click(force=True)
            except Exception:
                await done_button.evaluate("node => node.click()")
        await self.page.wait_for_timeout(1200)
        await self._wait_for_cover_modal_to_close()

    async def _wait_for_cover_modal_to_close(self):
        """等待设置封面弹窗关闭。"""
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if not await self._is_cover_modal_visible():
                return
            await self.page.wait_for_timeout(300)

        raise RuntimeError("抖音封面保存后弹窗未关闭")

    async def _wait_for_inner_cover_modal_to_close(self, timeout_seconds: int = 15) -> bool:
        """等待小号“设置封面”保存弹窗关闭，避免误把完成当成保存完成。"""
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            save_button = await self._find_inner_cover_confirm_button()
            confirm_button = await self._find_visible_text_button("确认")
            if save_button is None and confirm_button is None:
                await self.page.wait_for_timeout(500)
                return True
            await self.page.wait_for_timeout(300)

        return False

    async def _is_cover_modal_visible(self) -> bool:
        """判断设置封面弹窗是否仍然可见。"""
        candidate_groups = [
            self.page.locator("div[role='modal'].semi-modal-wrap"),
            self.page.locator(".semi-modal-wrap"),
            self.page.locator(".dy-creator-content-portal"),
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
                        return True
                except Exception:
                    continue

        return False

    async def _finalize_cover_editors(self):
        """在继续填写发布表单前，主动收掉仍然存在的封面编辑器。"""
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if not await self._is_cover_modal_visible():
                return

            done_button = None
            for label in ("完成", "保存", "确认"):
                done_button = await self._find_visible_text_button(label)
                if done_button is not None:
                    break

            if done_button is None:
                close_icon = self.page.locator(
                    ".semi-modal-close, button[aria-label='关闭'], svg.close-ksT2V8"
                ).first
                try:
                    if await close_icon.count() > 0 and await close_icon.is_visible():
                        await close_icon.click()
                        await self.page.wait_for_timeout(600)
                        continue
                except Exception:
                    pass
                return

            try:
                await done_button.click()
            except Exception:
                try:
                    await done_button.click(force=True)
                except Exception:
                    await done_button.evaluate("node => node.click()")
            await self.page.wait_for_timeout(800)

    async def _wait_for_cover_cards_ready(self):
        """等待主页面竖封面/横封面卡片都真正生成，避免仍在转圈时误判成功。"""
        portrait_card = self.page.locator(".coverControl-CjlzqC").filter(has_text="竖封面3:4").first
        landscape_card = self.page.locator(".coverControl-CjlzqC").filter(has_text="横封面4:3").first
        deadline = time.monotonic() + 20

        while time.monotonic() < deadline:
            portrait_ready = await self._cover_card_ready(portrait_card)
            landscape_ready = await self._cover_card_ready(landscape_card)
            if portrait_ready and landscape_ready:
                return
            await self.page.wait_for_timeout(500)

        raise RuntimeError("抖音封面卡片未生成完成，已停止自动发布")

    async def _cover_card_ready(self, card) -> bool:
        """判断单个封面卡片是否已替换为真实缩略图。"""
        try:
            if await card.count() == 0 or not await card.is_visible():
                return False
        except Exception:
            return False

        try:
            choose = card.get_by_text("选择封面", exact=True)
            if await choose.count() > 0 and await choose.is_visible():
                return False
        except Exception:
            pass

        try:
            edit = card.get_by_text("编辑", exact=True)
            replace = card.get_by_text("替换", exact=True)
            if await edit.count() > 0 and await edit.is_visible():
                return True
            if await replace.count() > 0 and await replace.is_visible():
                return True
        except Exception:
            pass

        thumbnail_groups = [
            card.locator("img"),
            card.locator("canvas"),
            card.locator("[style*='background-image']"),
        ]
        for group in thumbnail_groups:
            try:
                count = await group.count()
            except Exception:
                continue

            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    if await candidate.is_visible():
                        return True
                except Exception:
                    continue

        return False

    async def _scroll_to_publish_footer(self):
        """发布前滚到页面底部，命中真实底部发布按钮。"""
        try:
            await self.page.evaluate(
                "() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' })"
            )
        except Exception:
            pass
        await self.page.wait_for_timeout(500)

    async def _resolve_unfinished_draft(self, prefer_continue: bool) -> bool:
        """处理“上次未发布的视频”提示。"""
        body = self.page.locator("body")
        try:
            body_text = await body.inner_text()
        except Exception:
            return False

        if "你还有上次未发布的视频" not in body_text:
            return False

        primary_label = "继续编辑" if prefer_continue else "放弃"
        secondary_label = "放弃" if prefer_continue else "继续编辑"

        for label in (primary_label, secondary_label):
            button = await self._find_visible_text_button(label)
            if button is None:
                continue
            try:
                await button.click()
                await self.page.wait_for_timeout(1500)
                return True
            except Exception:
                continue

        return False

    async def _find_visible_text_button(self, text: str):
        """查找页面上可见的指定文案按钮/链接。"""
        candidate_groups = [
            self.page.get_by_role("button", name=text, exact=True),
            self.page.get_by_text(text, exact=True),
            self.page.locator(f"button:has-text('{text}')"),
            self.page.locator(f"a:has-text('{text}')"),
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

    async def _find_cover_footer_button(self, text: str):
        """在大封面编辑器底部区域查找动作按钮。"""
        candidate_groups = [
            self.page.locator(".semi-modal-wrap .semi-modal-footer").get_by_role("button", name=text),
            self.page.locator(".semi-modal-wrap .semi-modal-footer").get_by_text(text, exact=True),
            self.page.locator(".semi-modal-wrap").get_by_role("button", name=text, exact=True),
            self.page.locator(".semi-modal-wrap").get_by_text(text, exact=True),
            self.page.get_by_role("button", name=text, exact=True),
            self.page.get_by_text(text, exact=True),
        ]

        best_candidate = None
        best_y = -1.0
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
                    box = await candidate.bounding_box()
                    y = box["y"] if box else -1.0
                    if y > best_y:
                        best_candidate = candidate
                        best_y = y
                except Exception:
                    continue

        return best_candidate

    async def _wait_for_cover_footer_button(self, text: str, timeout_seconds: int = 10):
        """等待大封面编辑器底部动作按钮出现。"""
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            candidate = await self._find_cover_footer_button(text)
            if candidate is not None:
                return candidate
            await self.page.wait_for_timeout(300)
        return None

    async def _find_inner_cover_confirm_button(self):
        """优先在当前小号“设置封面”弹窗内查找保存按钮。"""
        candidate_groups = [
            self.page.locator(".semi-modal-wrap").filter(has_text="设置封面").get_by_role(
                "button",
                name="保存",
                exact=True,
            ),
            self.page.locator(".semi-modal-wrap").filter(has_text="设置封面").locator(
                "button:has-text('保存')"
            ),
            self.page.get_by_role("button", name="保存", exact=True),
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

    async def _select_uploaded_cover_thumbnail(self, variant_label: str):
        """保存后主动选中刚上传的自定义封面缩略图。"""
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            thumbnail = await self._find_uploaded_cover_thumbnail()
            if thumbnail is not None:
                try:
                    await thumbnail.click()
                except Exception:
                    try:
                        await thumbnail.click(force=True)
                    except Exception:
                        await thumbnail.evaluate("node => node.click()")
                await self.page.wait_for_timeout(800)
                return
            await self.page.wait_for_timeout(300)

        raise RuntimeError(f"抖音{variant_label}上传后未找到自定义封面缩略图")

    async def _find_uploaded_cover_thumbnail(self):
        """定位上传后生成的 blob 自定义封面缩略图。"""
        candidate_groups = [
            self.page.locator(".semi-modal-wrap [style*='blob:']"),
            self.page.locator(".semi-modal-wrap img[src^='blob:']"),
        ]

        best_candidate = None
        best_area = -1.0
        for group in candidate_groups:
            try:
                count = await group.count()
            except Exception:
                continue

            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    clickable = candidate.locator("xpath=ancestor-or-self::*[self::div or self::button][1]")
                    if not await clickable.is_visible():
                        continue
                    box = await clickable.bounding_box()
                    if not box:
                        continue
                    area = box["width"] * box["height"]
                    if area > best_area:
                        best_candidate = clickable
                        best_area = area
                except Exception:
                    continue

        if best_candidate is not None:
            return best_candidate

        upload_button = await self._find_visible_text_button("上传封面")
        upload_box = None
        if upload_button is not None:
            try:
                upload_box = await upload_button.bounding_box()
            except Exception:
                upload_box = None

        fallback_groups = [
            self.page.locator(".semi-modal-wrap img"),
            self.page.locator(".semi-modal-wrap [style*='background-image']"),
            self.page.locator(".semi-modal-wrap canvas"),
        ]

        best_candidate = None
        best_x = -1.0
        for group in fallback_groups:
            try:
                count = await group.count()
            except Exception:
                continue

            for idx in range(count):
                candidate = group.nth(idx)
                try:
                    clickable = candidate.locator("xpath=ancestor-or-self::*[self::div or self::button][1]")
                    if not await clickable.is_visible():
                        continue
                    box = await clickable.bounding_box()
                    if not box:
                        continue
                    if box["width"] < 20 or box["height"] < 20:
                        continue
                    if upload_box is not None and box["x"] >= upload_box["x"]:
                        continue
                    if upload_box is not None and abs(box["y"] - upload_box["y"]) > 120:
                        continue
                    if box["x"] > best_x:
                        best_candidate = clickable
                        best_x = box["x"]
                except Exception:
                    continue

        return best_candidate

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

    async def _wait_for_publish_ready(self, timeout_ms: int):
        """等待上传完成且发布按钮可用。"""
        deadline = time.monotonic() + timeout_ms / 1000

        while time.monotonic() < deadline:
            try:
                publish = await self._find_visible_publish_button()
                if (
                    await self._is_publish_form_page()
                    and await publish.is_enabled()
                    and await self._video_upload_is_complete()
                ):
                    return
            except Exception:
                pass
            await self.page.wait_for_timeout(1000)

        raise RuntimeError("抖音上传长时间未完成，未执行发布")

    async def _wait_for_publish_outcome(self, timeout_ms: int) -> bool:
        """等待发布结果：成功、草稿回退、或短信验证码人工确认。"""
        deadline = time.monotonic() + timeout_ms / 1000

        while time.monotonic() < deadline:
            body_text = await self.page.locator("body").inner_text()
            if self._body_indicates_sms_verification(body_text):
                await self._wait_for_sms_verification(timeout_ms=180_000)
                continue

            if self._body_indicates_publish_success(body_text):
                return True

            if self._url_indicates_publish_success(self.page.url):
                return True

            if self._url_indicates_draft_fallback(self.page.url) and not await self._is_publish_form_page():
                raise RuntimeError("抖音点击发布后跳回草稿页，视频实际未发布")

            await self.page.wait_for_timeout(1000)

        return False

    async def _wait_for_sms_verification(self, timeout_ms: int):
        """等待用户手动完成短信验证码验证。"""
        deadline = time.monotonic() + timeout_ms / 1000

        while time.monotonic() < deadline:
            body_text = await self.page.locator("body").inner_text()
            if not self._body_indicates_sms_verification(body_text):
                return
            if self._url_indicates_publish_success(self.page.url):
                return
            if self._body_indicates_publish_success(body_text):
                return
            await self.page.wait_for_timeout(1000)

        raise RuntimeError("抖音发布需要短信验证码，请在浏览器中完成验证后重试")

    async def _is_publish_form_page(self) -> bool:
        """确认当前仍在抖音作品发布表单，而不是首页或草稿提示页。"""
        try:
            body_text = await self.page.locator("body").inner_text()
        except Exception:
            return False

        if "新的创作" in body_text and "发布视频" in body_text:
            return False

        form_markers = (
            "发布设置",
            "作品描述",
            "设置封面",
        )
        return any(marker in body_text for marker in form_markers)

    async def _video_upload_is_complete(self) -> bool:
        """判断右侧视频上传是否已经结束，避免上传中误点发布。"""
        visible_text_checks = (
            "上传过程中请不要删除/移动文件",
            "剩余时间",
            "取消上传",
            "点击上传",
            "或直接将视频文件拖入此区域",
        )
        for text in visible_text_checks:
            try:
                locator = self.page.get_by_text(text, exact=False).first
                if await locator.count() > 0 and await locator.is_visible():
                    return False
            except Exception:
                continue

        try:
            success = self.page.get_by_text("上传成功", exact=False).first
            if await success.count() > 0 and await success.is_visible():
                return True
        except Exception:
            pass

        try:
            body_text = await self.page.locator("body").inner_text()
        except Exception:
            return False

        uploading_markers = (
            "上传过程中请不要删除/移动文件",
            "剩余时间",
            "取消上传",
            "点击上传",
        )
        return not any(marker in body_text for marker in uploading_markers)

    @staticmethod
    def _body_indicates_publish_success(body_text: str) -> bool:
        """只接受真正的成功信号，避免侧边栏文案造成假成功。"""
        success_markers = (
            "发布成功",
            "作品发布成功",
            "查看作品",
        )
        return any(marker in body_text for marker in success_markers)

    @staticmethod
    def _body_indicates_sms_verification(body_text: str) -> bool:
        """识别发布后触发的短信验证码验证。"""
        verification_markers = (
            "短信验证码",
            "获取验证码",
            "选择其他验证方式",
            "为确保是本人操作抖音账号",
        )
        return any(marker in body_text for marker in verification_markers)

    @staticmethod
    def _url_indicates_publish_success(url: str) -> bool:
        """URL 层面的成功信号。"""
        return any(
            marker in url
            for marker in (
                "/creator-micro/content/manage",
                "/creator-micro/content?tab=",
            )
        )

    @staticmethod
    def _url_indicates_draft_fallback(url: str) -> bool:
        """URL 层面的失败信号：跳回草稿/继续编辑页。"""
        return (
            "/creator-micro/content/post/video" in url
            or "enter_from=draft" in url
        )

    @staticmethod
    def _build_tag_text(tags: list[str]) -> str:
        """生成带换行的话题文本，避免紧贴正文。"""
        visible_tags = [tag.strip() for tag in tags if tag and tag.strip()]
        return "\n" + " ".join(f"#{tag}" for tag in visible_tags) + " "
