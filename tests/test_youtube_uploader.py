"""YouTube uploader tests."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

from videopub.core.models import Platform, PlatformMeta, PlatformTask
from videopub.uploaders.youtube.uploader import YouTubeUploader


def _make_task(scheduled_time=None):
    return PlatformTask(
        video_path=Path("/tmp/video.mp4"),
        cover_path=Path("/tmp/cover.jpg"),
        meta=PlatformMeta(
            platform=Platform.YOUTUBE,
            title="测试标题",
            description="测试简介",
            tags=["health", "demo"],
            category="28",
            scheduled_time=scheduled_time,
        ),
    )


def test_build_video_body_without_schedule():
    uploader = YouTubeUploader()

    body = uploader._build_video_body(_make_task())

    assert body["snippet"]["title"] == "测试标题"
    assert body["snippet"]["description"] == "测试简介"
    assert body["snippet"]["tags"] == ["health", "demo"]
    assert body["snippet"]["categoryId"] == "28"
    assert body["status"]["privacyStatus"] == uploader.config.get("default_privacy", "unlisted")
    assert "publishAt" not in body["status"]


def test_build_video_body_falls_back_for_non_numeric_category():
    uploader = YouTubeUploader()
    task = PlatformTask(
        video_path=Path("/tmp/video.mp4"),
        cover_path=Path("/tmp/cover.jpg"),
        meta=PlatformMeta(
            platform=Platform.YOUTUBE,
            title="测试标题",
            description="测试简介",
            tags=["health"],
            category="家庭健康避坑",
        ),
    )

    body = uploader._build_video_body(task)

    assert body["snippet"]["categoryId"] == uploader.config.get("default_category", "28")


def test_build_video_body_uses_local_timezone_for_naive_datetime(monkeypatch):
    uploader = YouTubeUploader()
    local_tz = timezone(timedelta(hours=8))
    monkeypatch.setattr(uploader, "_local_timezone", lambda: local_tz)

    body = uploader._build_video_body(_make_task(datetime(2026, 4, 3, 20, 0)))

    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["publishAt"] == "2026-04-03T20:00:00+08:00"


def test_build_video_body_preserves_aware_datetime():
    uploader = YouTubeUploader()
    aware_dt = datetime(2026, 4, 3, 20, 0, tzinfo=timezone(timedelta(hours=-4)))

    body = uploader._build_video_body(_make_task(aware_dt))

    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["publishAt"] == "2026-04-03T20:00:00-04:00"


def test_guess_mimetype_from_extension(tmp_path):
    uploader = YouTubeUploader()

    assert uploader._guess_mimetype(tmp_path / "cover.jpg", "image/jpeg") == "image/jpeg"
    assert uploader._guess_mimetype(tmp_path / "video.mp4", "video/mp4") == "video/mp4"


async def test_upload_succeeds_when_thumbnail_upload_fails(tmp_path, monkeypatch):
    uploader = YouTubeUploader()
    uploader.credentials = object()

    video_path = tmp_path / "video.mp4"
    cover_path = tmp_path / "cover.jpg"
    video_path.write_bytes(b"video")
    cover_path.write_bytes(b"cover")

    class FakeInsertRequest:
        def __init__(self):
            self.calls = 0

        def next_chunk(self):
            self.calls += 1
            if self.calls == 1:
                return None, None
            return None, {"id": "yt123"}

    class FakeVideos:
        def insert(self, **kwargs):
            return FakeInsertRequest()

    class FakeService:
        def videos(self):
            return FakeVideos()

    monkeypatch.setattr(uploader, "_get_service", lambda: FakeService())
    monkeypatch.setattr(
        "videopub.uploaders.youtube.uploader._MediaFileUpload",
        lambda *args, **kwargs: {"args": args, "kwargs": kwargs},
    )
    monkeypatch.setattr(uploader, "_upload_thumbnail", AsyncMock(side_effect=RuntimeError("thumb failed")))

    result = await uploader.upload(
        PlatformTask(
            video_path=video_path,
            cover_path=cover_path,
            meta=PlatformMeta(
                platform=Platform.YOUTUBE,
                title="测试标题",
                description="测试简介",
                tags=["tag"],
            ),
        )
    )

    assert result.success is True
    assert result.video_id == "yt123"
    assert result.video_url == "https://www.youtube.com/watch?v=yt123"
