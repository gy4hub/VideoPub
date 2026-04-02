"""所有平台上传器的抽象基类"""

from abc import ABC, abstractmethod

from videopub.core.models import PlatformTask, UploadResult


class BaseUploader(ABC):
    """平台上传器统一接口。"""

    @abstractmethod
    async def check_session(self) -> bool:
        """检查登录态是否有效"""
        ...

    @abstractmethod
    async def login(self) -> bool:
        """执行登录（cookie 加载或交互式登录）"""
        ...

    @abstractmethod
    async def upload(self, task: PlatformTask) -> UploadResult:
        """上传视频并填写元数据"""
        ...

    @abstractmethod
    async def post_comment(self, video_id: str, comment: str) -> bool:
        """发布首评"""
        ...
