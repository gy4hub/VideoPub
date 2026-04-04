"""Bilibili uploader tests."""

from datetime import datetime, timedelta, timezone
import json

from videopub.core.models import Platform, PlatformMeta, PlatformTask
from videopub.uploaders.bilibili.uploader import BilibiliUploader


class FakeData:
    def __init__(self):
        self.items = []
        self.title = ""
        self.desc = ""
        self.tag = ""
        self.tid = 0
        self.source = ""
        self.cover = None
        self.dtime = None

    def append(self, item):
        self.items.append(item)

    def delay_time(self, dtime):
        self.dtime = dtime


def _cookie_payload():
    return {
        "cookie_info": {
            "cookies": [
                {"name": "SESSDATA", "value": "sess"},
                {"name": "bili_jct", "value": "csrf"},
            ]
        },
        "token_info": {
            "access_token": "token",
            "refresh_token": "refresh",
        },
    }


async def test_check_session_uses_saved_cookie(tmp_path, monkeypatch):
    uploader = BilibiliUploader()
    cookie_path = tmp_path / "bilibili_cookie.json"
    uploader.config["cookie_path"] = str(cookie_path)
    cookie_path.write_text(json.dumps(_cookie_payload(), ensure_ascii=False), encoding="utf-8")

    seen = {}

    class FakeClient:
        def login_by_cookies(self, cookie):
            seen["cookie"] = cookie

    monkeypatch.setattr(uploader, "_build_client", lambda: (FakeClient(), FakeData))

    assert await uploader.check_session() is True
    assert seen["cookie"] == _cookie_payload()
    assert uploader._cookie_data == _cookie_payload()


def test_resolve_tid_falls_back_for_non_numeric_category():
    uploader = BilibiliUploader()

    assert uploader._resolve_tid("201") == 201
    assert uploader._resolve_tid(" 家庭健康避坑 ") == int(uploader.config.get("default_tid", 201))


def test_resolve_scheduled_timestamp_uses_local_timezone(monkeypatch):
    uploader = BilibiliUploader()
    local_tz = timezone(timedelta(hours=8))
    monkeypatch.setattr(uploader, "_local_timezone", lambda: local_tz)

    ts = uploader._resolve_scheduled_timestamp(datetime(2026, 4, 8, 21, 0))

    assert ts == int(datetime(2026, 4, 8, 21, 0, tzinfo=local_tz).timestamp())


async def test_login_saves_qrcode_cookie_payload(tmp_path, monkeypatch):
    uploader = BilibiliUploader()
    cookie_path = tmp_path / "bilibili_cookie.json"
    preview_path = tmp_path / "bilibili_qrcode.html"
    uploader.config["cookie_path"] = str(cookie_path)
    payload = _cookie_payload()

    class FakeClient:
        def get_qrcode(self):
            return {
                "data": {
                    "url": "https://passport.bilibili.com/example",
                    "auth_code": "auth-code",
                }
            }

        async def login_by_qrcode(self, value):
            assert value["data"]["auth_code"] == "auth-code"
            return {"data": payload}

        def login_by_cookies(self, cookie):
            assert cookie == payload

    monkeypatch.setattr(uploader, "_build_client", lambda: (FakeClient(), FakeData))
    monkeypatch.setattr(uploader, "_qrcode_preview_path", lambda: preview_path)
    monkeypatch.setattr(uploader, "_open_qrcode_preview", lambda path: None)

    assert await uploader.login() is True
    assert json.loads(cookie_path.read_text(encoding="utf-8")) == payload
    assert uploader._cookie_data == payload
    assert preview_path.exists()


async def test_upload_submits_video_with_cookie_login(tmp_path, monkeypatch):
    uploader = BilibiliUploader()
    payload = _cookie_payload()
    uploader._cookie_data = payload

    video_path = tmp_path / "video.mp4"
    cover_path = tmp_path / "cover.jpg"
    video_path.write_bytes(b"video")
    cover_path.write_bytes(b"cover")

    seen = {}

    class FakeClient:
        def __init__(self, video_data):
            seen["bound_video_data"] = video_data

        def login_by_cookies(self, cookie):
            seen["cookie"] = cookie

        def cover_up(self, cover):
            seen["cover_path"] = cover
            return "cover-token"

        def upload_file(self, video):
            seen["video_path"] = video
            return {"filename": "video.mp4"}

        def submit(self):
            seen["video_data"] = seen["bound_video_data"]
            return {"data": {"bvid": "BV1xx411c7XY"}}

    def fake_build_client(video_data=None):
        if video_data is None:
            video_data = FakeData()
        return FakeClient(video_data), FakeData

    monkeypatch.setattr(uploader, "_build_client", fake_build_client)

    result = await uploader.upload(
        PlatformTask(
            video_path=video_path,
            cover_path=cover_path,
            meta=PlatformMeta(
                platform=Platform.BILIBILI,
                title="测试标题",
                description="测试描述",
                tags=["标签1", "标签2"],
                category="201",
            ),
        )
    )

    assert result.success is True
    assert result.video_id == "BV1xx411c7XY"
    assert result.video_url == "https://www.bilibili.com/video/BV1xx411c7XY"
    assert seen["cookie"] == payload
    assert seen["cover_path"] == str(cover_path)
    assert seen["video_path"] == str(video_path)
    assert seen["video_data"].title == "测试标题"
    assert seen["video_data"].desc == "测试描述"
    assert seen["video_data"].tag == "标签1,标签2"
    assert seen["video_data"].tid == 201
    assert seen["video_data"].copyright == 1
    assert seen["video_data"].cover == "cover-token"
    assert seen["video_data"].items == [{"filename": "video.mp4"}]


async def test_upload_sets_bilibili_schedule(tmp_path, monkeypatch):
    uploader = BilibiliUploader()
    payload = _cookie_payload()
    uploader._cookie_data = payload

    video_path = tmp_path / "video.mp4"
    cover_path = tmp_path / "cover.jpg"
    video_path.write_bytes(b"video")
    cover_path.write_bytes(b"cover")

    seen = {}

    class FakeClient:
        def __init__(self, video_data):
            seen["bound_video_data"] = video_data

        def login_by_cookies(self, cookie):
            seen["cookie"] = cookie

        def cover_up(self, cover):
            return "cover-token"

        def upload_file(self, video):
            return {"filename": "video.mp4"}

        def submit(self):
            seen["video_data"] = seen["bound_video_data"]
            return {"data": {"bvid": "BV1schedule"}}

    def fake_build_client(video_data=None):
        if video_data is None:
            video_data = FakeData()
        return FakeClient(video_data), FakeData

    monkeypatch.setattr(uploader, "_build_client", fake_build_client)
    monkeypatch.setattr(uploader, "_resolve_scheduled_timestamp", lambda dt: 1_800_000_000)

    result = await uploader.upload(
        PlatformTask(
            video_path=video_path,
            cover_path=cover_path,
            meta=PlatformMeta(
                platform=Platform.BILIBILI,
                title="测试标题",
                description="测试描述",
                tags=["标签1"],
                scheduled_time=datetime(2026, 4, 8, 21, 0, tzinfo=timezone.utc),
            ),
        )
    )

    assert result.success is True
    assert seen["video_data"].dtime == 1_800_000_000
