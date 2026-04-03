"""YouTube Data API v3 上传器"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from videopub.core.config_loader import load_platform_config
from videopub.core.models import Platform, PlatformTask, UploadResult
from videopub.uploaders.base import BaseUploader

# 延迟导入 Google API 库（仅在实际使用时需要）
_google_imported = False
_build = None
_InstalledAppFlow = None
_Credentials = None
_MediaFileUpload = None
_Request = None


def _ensure_google_imports():
    global _google_imported, _build, _InstalledAppFlow, _Credentials, _MediaFileUpload, _Request
    if _google_imported:
        return

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    _build = build
    _InstalledAppFlow = InstalledAppFlow
    _Credentials = Credentials
    _MediaFileUpload = MediaFileUpload
    _Request = Request
    _google_imported = True


# OAuth 2.0 scope
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


class YouTubeUploader(BaseUploader):
    def __init__(self):
        self.config = load_platform_config("youtube")
        self.credentials = None
        self.service = None

    def _token_path(self) -> Path:
        return Path(self.config.get("token_path", "~/.videopub/youtube_token.json")).expanduser()

    def _client_secrets_path(self) -> Path:
        return Path(
            self.config.get("oauth_client_secrets", "~/.videopub/youtube_client_secrets.json")
        ).expanduser()

    def _load_credentials(self) -> bool:
        """同步检查并刷新 OAuth token"""
        _ensure_google_imports()

        token_path = self._token_path()
        if not token_path.exists():
            return False

        self.credentials = _Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(_Request())
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(self.credentials.to_json(), encoding="utf-8")

        return bool(self.credentials.valid)

    async def check_session(self) -> bool:
        """检查 OAuth token 是否有效"""
        try:
            return await asyncio.to_thread(self._load_credentials)
        except Exception:
            return False

    async def login(self) -> bool:
        """执行 OAuth 2.0 授权流程"""
        _ensure_google_imports()

        secrets_path = self._client_secrets_path()
        if not secrets_path.exists():
            raise FileNotFoundError(
                f"YouTube OAuth client secrets 文件不存在: {secrets_path}\n"
                "请从 Google Cloud Console 下载 OAuth 2.0 客户端密钥文件"
            )

        flow = _InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
        self.credentials = await asyncio.to_thread(flow.run_local_server, port=0)

        token_path = self._token_path()
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(self.credentials.to_json(), encoding="utf-8")
        return True

    def _get_service(self):
        """获取 YouTube API service 对象"""
        _ensure_google_imports()
        if self.service is None:
            self.service = _build("youtube", "v3", credentials=self.credentials)
        return self.service

    async def upload(self, task: PlatformTask) -> UploadResult:
        """上传视频到 YouTube"""
        _ensure_google_imports()

        try:
            service = self._get_service()
            meta = task.meta
            privacy = self.config.get("default_privacy", "unlisted")
            body = {
                "snippet": {
                    "title": meta.title,
                    "description": meta.description,
                    "tags": meta.tags,
                    "categoryId": meta.category or self.config.get("default_category", "28"),
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False,
                },
            }

            if meta.scheduled_time:
                # YouTube 要求 RFC 3339 格式（含时区），naive datetime 强制转为 UTC
                dt = meta.scheduled_time
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                body["status"]["privacyStatus"] = "private"
                body["status"]["publishAt"] = dt.isoformat()

            media = _MediaFileUpload(
                str(task.video_path),
                mimetype="video/*",
                resumable=True,
                chunksize=10 * 1024 * 1024,
            )

            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )
            response = await asyncio.to_thread(self._execute_upload, request)
            video_id = response["id"]

            if task.cover_path.exists():
                await self._upload_thumbnail(service, video_id, task.cover_path)

            return UploadResult(
                platform=Platform.YOUTUBE,
                success=True,
                video_id=video_id,
                video_url=f"https://www.youtube.com/watch?v={video_id}",
            )
        except Exception as exc:
            return UploadResult(
                platform=Platform.YOUTUBE,
                success=False,
                error=str(exc),
            )

    def _execute_upload(self, request):
        """执行 resumable upload，返回 response"""
        response = None
        while response is None:
            _, response = request.next_chunk()
        return response

    async def _upload_thumbnail(self, service, video_id: str, cover_path: Path):
        """上传视频封面"""
        _ensure_google_imports()
        media = _MediaFileUpload(str(cover_path), mimetype="image/*")
        request = service.thumbnails().set(videoId=video_id, media_body=media)
        await asyncio.to_thread(request.execute)

    async def post_comment(self, video_id: str, comment: str) -> bool:
        """发布首评"""
        try:
            service = self._get_service()
            body = {
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment,
                        }
                    },
                }
            }
            request = service.commentThreads().insert(part="snippet", body=body)
            await asyncio.to_thread(request.execute)
            return True
        except Exception:
            return False
