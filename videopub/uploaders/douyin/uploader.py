"""抖音上传器（待实现）"""

from videopub.core.models import PlatformTask, UploadResult
from videopub.uploaders.base import BaseUploader


class DouyinUploader(BaseUploader):
    async def check_session(self) -> bool:
        raise NotImplementedError("DouyinUploader.check_session() 将在 Sprint 1-2 中实现")

    async def login(self) -> bool:
        raise NotImplementedError("DouyinUploader.login() 将在 Sprint 1-2 中实现")

    async def upload(self, task: PlatformTask) -> UploadResult:
        raise NotImplementedError("DouyinUploader.upload() 将在 Sprint 1-2 中实现")

    async def post_comment(self, video_id: str, comment: str) -> bool:
        raise NotImplementedError("DouyinUploader.post_comment() 将在 Sprint 1-2 中实现")
