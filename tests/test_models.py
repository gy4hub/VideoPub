"""Pydantic 模型验证测试"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from videopub.core.models import (
    Platform,
    PlatformMeta,
    PlatformTask,
    PublishTask,
    UploadResult,
)


class TestPlatformEnum:
    def test_all_platforms_exist(self):
        assert Platform.WECHAT == "wechat"
        assert Platform.DOUYIN == "douyin"
        assert Platform.BILIBILI == "bilibili"
        assert Platform.YOUTUBE == "youtube"

    def test_platform_from_string(self):
        assert Platform("wechat") == Platform.WECHAT


class TestPlatformMeta:
    def test_minimal_creation(self):
        meta = PlatformMeta(
            platform=Platform.DOUYIN,
            title="测试标题",
            description="测试简介",
            tags=["tag1", "tag2"],
        )
        assert meta.platform == Platform.DOUYIN
        assert meta.title == "测试标题"
        assert meta.is_original is True
        assert meta.short_title is None
        assert meta.first_comment is None
        assert meta.scheduled_time is None
        assert meta.category is None
        assert meta.extra == {}

    def test_full_creation(self):
        scheduled = datetime(2026, 4, 3, 20, 0, tzinfo=timezone(timedelta(hours=8)))
        meta = PlatformMeta(
            platform=Platform.WECHAT,
            title="磁珠纯化技术的三大误区",
            short_title="磁珠纯化误区",
            description="很多实验室还在用传统的磁珠纯化方法...",
            tags=["磁珠", "纯化", "实验室"],
            first_comment="你们实验室用的什么品牌的磁珠？",
            is_original=True,
            scheduled_time=scheduled,
        )
        assert meta.short_title == "磁珠纯化误区"
        assert meta.scheduled_time == scheduled

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            PlatformMeta(
                platform=Platform.DOUYIN,
                title="只有标题",
            )


class TestPlatformTask:
    def test_creation(self):
        meta = PlatformMeta(
            platform=Platform.YOUTUBE,
            title="Test",
            description="Desc",
            tags=["t"],
        )
        task = PlatformTask(
            video_path=Path("/tmp/video.mp4"),
            cover_path=Path("/tmp/cover.jpg"),
            meta=meta,
        )
        assert task.video_path == Path("/tmp/video.mp4")
        assert task.meta.platform == Platform.YOUTUBE


class TestPublishTask:
    def test_multi_platform(self):
        platforms = [
            PlatformMeta(
                platform=Platform.WECHAT,
                title="视频号标题",
                description="简介",
                tags=["tag"],
            ),
            PlatformMeta(
                platform=Platform.DOUYIN,
                title="抖音标题",
                description="简介",
                tags=["tag"],
            ),
        ]
        task = PublishTask(
            video_path=Path("/tmp/video.mp4"),
            cover_path=Path("/tmp/cover.jpg"),
            platforms=platforms,
        )
        assert len(task.platforms) == 2
        assert task.platforms[0].platform == Platform.WECHAT
        assert task.platforms[1].platform == Platform.DOUYIN


class TestUploadResult:
    def test_success_result(self):
        result = UploadResult(
            platform=Platform.BILIBILI,
            success=True,
            video_id="BV1xx411c7XY",
            video_url="https://bilibili.com/video/BV1xx411c7XY",
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        result = UploadResult(
            platform=Platform.DOUYIN,
            success=False,
            error="登录失败",
            screenshot_path=Path("/tmp/logs/screenshot.png"),
        )
        assert result.success is False
        assert result.video_id is None
        assert "登录失败" in result.error
