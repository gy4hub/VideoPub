"""核心数据模型"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class Platform(str, Enum):
    """支持的发布平台"""

    WECHAT = "wechat"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"


class PlatformMeta(BaseModel):
    """单个平台的元数据"""

    platform: Platform
    title: str
    short_title: str | None = None
    description: str
    tags: list[str] = Field(default_factory=list)
    first_comment: str | None = None
    is_original: bool = True
    scheduled_time: datetime | None = None
    category: str | None = None
    extra: dict = Field(default_factory=dict)


class PlatformTask(BaseModel):
    """单个平台的上传任务（传给 uploader.upload()）"""

    video_path: Path
    cover_path: Path
    meta: PlatformMeta


class PublishTask(BaseModel):
    """完整的发布任务（包含所有平台）"""

    video_path: Path
    cover_path: Path
    platforms: list[PlatformMeta]


class UploadResult(BaseModel):
    """上传结果"""

    platform: Platform
    success: bool
    video_id: str | None = None
    video_url: str | None = None
    error: str | None = None
    screenshot_path: Path | None = None
