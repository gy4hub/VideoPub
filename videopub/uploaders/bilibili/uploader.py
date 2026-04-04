"""Bilibili 上传器，封装 biliup API"""

import html
import json
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any
from urllib.parse import quote

from videopub.core.config_loader import load_platform_config
from videopub.core.cover_utils import ensure_landscape_cover, ensure_portrait_safe_cover
from videopub.core.models import Platform, PlatformTask, UploadResult
from videopub.uploaders.base import BaseUploader


class BilibiliUploader(BaseUploader):
    def __init__(self):
        self.config = load_platform_config("bilibili")
        self._cookie_data = None

    def _cookie_path(self) -> Path:
        return Path(self.config.get("cookie_path", "~/.videopub/bilibili_cookie.json")).expanduser()

    def _qrcode_preview_path(self) -> Path:
        return Path("~/.videopub/bilibili_login_qrcode.html").expanduser()

    def _load_cookie_file(self):
        """读取本地 cookie 文件"""
        cookie_path = self._cookie_path()
        if not cookie_path.exists():
            return None

        with cookie_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save_cookie_file(self, cookie_data: dict[str, Any]):
        """写入本地 cookie 文件"""
        cookie_path = self._cookie_path()
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        cookie_path.write_text(
            json.dumps(cookie_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _normalize_cookie_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """兼容 biliup 新旧返回结构，统一提取 cookie payload"""
        if "cookie_info" in payload:
            return payload

        data = payload.get("data")
        if isinstance(data, dict) and "cookie_info" in data:
            return data

        raise ValueError("未找到有效的 cookie_info")

    def _write_qrcode_preview(self, login_url: str) -> Path:
        """生成本地二维码预览页，方便手机扫码"""
        preview_path = self._qrcode_preview_path()
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        qrcode_url = f"https://api.qrserver.com/v1/create-qr-code/?size=360x360&data={quote(login_url, safe='')}"
        preview_path.write_text(
            f"""<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>Bilibili 登录二维码</title>
<style>
body {{
  margin: 0;
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #f6f7fb;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
main {{
  width: min(92vw, 520px);
  padding: 24px;
  border-radius: 20px;
  background: white;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.12);
  text-align: center;
}}
img {{
  width: min(72vw, 360px);
  height: min(72vw, 360px);
}}
p {{
  color: #4b5563;
  line-height: 1.6;
}}
code {{
  word-break: break-all;
  font-size: 12px;
}}
</style>
<main>
  <h1>Bilibili 扫码登录</h1>
  <p>请用 Bilibili App 扫描下面的二维码，并在手机上确认登录。</p>
  <img src="{qrcode_url}" alt="Bilibili 登录二维码">
  <p><code>{html.escape(login_url)}</code></p>
</main>
</html>
""",
            encoding="utf-8",
        )
        return preview_path

    def _open_qrcode_preview(self, preview_path: Path):
        """尝试用默认浏览器打开二维码预览页"""
        try:
            webbrowser.open(preview_path.as_uri())
        except Exception:
            pass

    def _build_client(self, video_data=None):
        """延迟导入 biliup 并构建客户端"""
        from biliup.plugins.bili_webup import BiliBili, Data

        if video_data is None:
            video_data = Data()

        return BiliBili(video_data), Data

    def _resolve_tid(self, category: str | None) -> int:
        """解析 Bilibili 分区 ID，非数字时回退默认分区"""
        if category and str(category).strip().isdigit():
            return int(str(category).strip())
        return int(self.config.get("default_tid", 201))

    def _local_timezone(self):
        """返回当前机器的本地时区。"""
        return datetime.now().astimezone().tzinfo or timezone.utc

    def _resolve_scheduled_timestamp(self, scheduled_time) -> int:
        """解析 Bilibili 定时发布时间戳。B站要求至少晚于当前 2 小时。"""
        dt = scheduled_time
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self._local_timezone())

        publish_at = int(dt.timestamp())
        if publish_at - int(time.time()) <= 7200:
            raise ValueError("Bilibili 定时发布时间至少晚于当前 2 小时")
        return publish_at

    def _check_login_sync(self, cookie_data: dict[str, Any] | None = None) -> bool:
        """同步检查 cookie 登录态"""
        cookie_data = cookie_data or self._load_cookie_file()
        if cookie_data is None:
            return False

        client, _ = self._build_client()
        try:
            client.login_by_cookies(cookie_data)
            self._cookie_data = cookie_data
            return True
        except Exception:
            return False

    async def check_session(self) -> bool:
        """检查 Bilibili cookie 是否有效"""
        try:
            import asyncio

            return await asyncio.to_thread(self._check_login_sync)
        except Exception:
            return False

    async def login(self) -> bool:
        """执行 Bilibili 登录（扫码方式）"""
        try:
            client, _ = self._build_client()
            qrcode_value = client.get_qrcode()
            if not qrcode_value:
                return False

            print("请打开 Bilibili APP 扫描二维码登录...")
            print(qrcode_value["data"]["url"])
            preview_path = self._write_qrcode_preview(qrcode_value["data"]["url"])
            print(f"二维码预览页: {preview_path}")
            self._open_qrcode_preview(preview_path)
            login_result = await client.login_by_qrcode(qrcode_value)

            if not login_result:
                return False

            cookie_data = self._normalize_cookie_data(login_result)
            if not self._check_login_sync(cookie_data):
                return False

            self._save_cookie_file(cookie_data)
            self._cookie_data = cookie_data
            return True
        except Exception:
            return False

    async def upload(self, task: PlatformTask) -> UploadResult:
        """上传视频到 Bilibili"""
        try:
            import asyncio

            meta = task.meta
            _, data_cls = self._build_client()
            video_data = data_cls()
            client, data_cls = self._build_client(video_data)
            if self._cookie_data is None:
                self._cookie_data = self._load_cookie_file()
            client.login_by_cookies(self._cookie_data)

            video_data.title = meta.title
            video_data.desc = meta.description
            video_data.desc_v2 = [{"raw_text": meta.description, "biz_id": "", "type": 1}]
            video_data.tag = ",".join(meta.tags)
            video_data.tid = self._resolve_tid(meta.category)
            video_data.copyright = 1 if meta.is_original else 2
            video_data.source = "" if meta.is_original else str(meta.extra.get("source", ""))
            if meta.scheduled_time:
                video_data.delay_time(self._resolve_scheduled_timestamp(meta.scheduled_time))

            if task.cover_path.exists():
                cover_path = await asyncio.to_thread(ensure_portrait_safe_cover, task.cover_path)
                cover_path = await asyncio.to_thread(ensure_landscape_cover, cover_path)
                video_data.cover = await asyncio.to_thread(client.cover_up, str(cover_path))

            file_info = await asyncio.to_thread(client.upload_file, str(task.video_path))
            video_data.append(file_info)

            result = await asyncio.to_thread(client.submit)
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
