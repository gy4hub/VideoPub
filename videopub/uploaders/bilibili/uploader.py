"""Bilibili 上传器，封装 biliup API"""

import asyncio
import json
from pathlib import Path

from videopub.core.config_loader import load_platform_config
from videopub.core.models import Platform, PlatformTask, UploadResult
from videopub.uploaders.base import BaseUploader


class BilibiliUploader(BaseUploader):
    def __init__(self):
        self.config = load_platform_config("bilibili")
        self._cookie_data = None

    def _cookie_path(self) -> Path:
        return Path(self.config.get("cookie_path", "~/.videopub/bilibili_cookie.json")).expanduser()

    def _load_cookie_file(self):
        """读取本地 cookie 文件"""
        cookie_path = self._cookie_path()
        if not cookie_path.exists():
            return None

        with cookie_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _build_client(self):
        """延迟导入 biliup 并构建客户端"""
        from biliup.plugins.bili_webup import BiliBili, Data

        return BiliBili(Data()), Data

    def _check_login_sync(self) -> bool:
        """同步检查 cookie 登录态"""
        cookie_data = self._load_cookie_file()
        if cookie_data is None:
            return False

        client, _ = self._build_client()
        client.login_by_cookie(cookie_data)
        if client.check_login():
            self._cookie_data = cookie_data
            return True
        return False

    async def check_session(self) -> bool:
        """检查 Bilibili cookie 是否有效"""
        try:
            return await asyncio.to_thread(self._check_login_sync)
        except Exception:
            return False

    async def login(self) -> bool:
        """执行 Bilibili 登录（扫码方式）"""
        try:
            client, _ = self._build_client()
            print("请打开 Bilibili APP 扫描二维码登录...")
            login_result = await asyncio.to_thread(client.login_by_qrcode)

            if not login_result:
                return False

            cookie_data = client.get_cookie()
            cookie_path = self._cookie_path()
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            cookie_path.write_text(
                json.dumps(cookie_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._cookie_data = cookie_data
            return True
        except Exception:
            return False

    async def upload(self, task: PlatformTask) -> UploadResult:
        """上传视频到 Bilibili"""
        try:
            client, data_cls = self._build_client()
            if self._cookie_data is None:
                self._cookie_data = self._load_cookie_file()
            client.login_by_cookie(self._cookie_data)

            meta = task.meta
            video_data = data_cls()
            video_data.title = meta.title
            video_data.desc = meta.description
            video_data.tag = ",".join(meta.tags)
            video_data.tid = int(meta.category or self.config.get("default_tid", 201))
            video_data.source = ""

            if task.cover_path.exists():
                video_data.cover = await asyncio.to_thread(client.cover_up, str(task.cover_path))

            file_info = await asyncio.to_thread(client.upload_file, str(task.video_path))
            video_data.append(file_info)

            result = await asyncio.to_thread(client.submit, video_data)
            video_id = str(result.get("data", {}).get("bvid", ""))

            return UploadResult(
                platform=Platform.BILIBILI,
                success=True,
                video_id=video_id,
                video_url=f"https://www.bilibili.com/video/{video_id}" if video_id else None,
            )
        except Exception as exc:
            return UploadResult(
                platform=Platform.BILIBILI,
                success=False,
                error=str(exc),
            )

    async def post_comment(self, video_id: str, comment: str) -> bool:
        """在视频下发布首评"""
        try:
            # biliup 暂不支持发评论，如果需要以后可以自己用 requests 调用 
            # https://api.bilibili.com/x/v2/reply/add 并带上 cookie(bili_jct)
            from loguru import logger
            logger.warning("[Bilibili] 暂不支持自动发首评")
            return False
        except Exception:
            return False
