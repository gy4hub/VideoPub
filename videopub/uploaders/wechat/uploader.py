"""视频号上传器（待实现）"""

from videopub.core.models import PlatformTask, UploadResult
from videopub.uploaders.base import BaseUploader


class WeChatUploader(BaseUploader):
    async def check_session(self) -> bool:
        raise NotImplementedError("WeChatUploader.check_session() 将在 Sprint 1-2 中实现")

    async def login(self) -> bool:
        raise NotImplementedError("WeChatUploader.login() 将在 Sprint 1-2 中实现")

    async def upload(self, task: PlatformTask) -> UploadResult:
        raise NotImplementedError("WeChatUploader.upload() 将在 Sprint 1-2 中实现")

    async def post_comment(self, video_id: str, comment: str) -> bool:
        raise NotImplementedError("WeChatUploader.post_comment() 将在 Sprint 1-2 中实现")
