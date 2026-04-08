"""MCP server helper tests."""

from videopub.core.models import Platform, PlatformMeta, PublishTask, UploadResult
from videopub.core.status import StatusState, write_status
from videopub.mcp_server import (
    _configure_server,
    _normalize_platforms,
    folder_status_impl,
    list_publishable_folders_impl,
    platform_config_impl,
    parse_folder_impl,
    settings_impl,
    validate_folder_impl,
    _serialize_platform_meta,
    _serialize_publish_task,
    _serialize_upload_result,
)


def test_normalize_platforms():
    assert _normalize_platforms(["WeChat", "youtube"]) == ["wechat", "youtube"]
    assert _normalize_platforms(["视频号", "抖音", "b站"]) == ["wechat", "douyin", "bilibili"]


def test_serialize_platform_meta():
    meta = PlatformMeta(
        platform=Platform.WECHAT,
        title="标题",
        description="描述",
        tags=["a", "b"],
        collection="合集A",
    )
    data = _serialize_platform_meta(meta)
    assert data["platform"] == "wechat"
    assert data["collection"] == "合集A"
    assert data["tags"] == ["a", "b"]


def test_serialize_publish_task(tmp_path):
    video = tmp_path / "video.mp4"
    cover = tmp_path / "cover.jpg"
    video.write_bytes(b"v")
    cover.write_bytes(b"c")
    task = PublishTask(
        video_path=video,
        cover_path=cover,
        platforms=[
            PlatformMeta(
                platform=Platform.BILIBILI,
                title="标题",
                description="描述",
                tags=["测试"],
            )
        ],
    )
    data = _serialize_publish_task(task)
    assert data["video_path"] == str(video)
    assert data["platforms"][0]["platform"] == "bilibili"


def test_serialize_upload_result():
    result = UploadResult(
        platform=Platform.YOUTUBE,
        success=True,
        video_id="abc",
        video_url="https://example.com",
    )
    data = _serialize_upload_result(result)
    assert data["platform"] == "youtube"
    assert data["success"] is True


def test_parse_folder_impl(tmp_path):
    (tmp_path / "video.mp4").write_bytes(b"video")
    (tmp_path / "cover.jpg").write_bytes(b"cover")
    (tmp_path / "metadata.txt").write_text(
        "[bilibili]\n标题: 纯文本\n描述: 用 txt 跑\n标签: #测试 #mcp",
        encoding="utf-8",
    )

    parsed = parse_folder_impl(str(tmp_path))
    assert parsed["task"]["platforms"][0]["title"] == "纯文本"
    assert parsed["task"]["platforms"][0]["tags"] == ["测试", "mcp"]


def test_folder_status_impl(tmp_path):
    write_status(
        tmp_path,
        Platform.DOUYIN,
        StatusState.DONE,
        video_id="123",
        video_url="https://example.com/123",
    )

    result = folder_status_impl(str(tmp_path))
    assert result["statuses"]["douyin"]["state"] == "done"
    assert result["statuses"]["douyin"]["video_id"] == "123"


def test_folder_status_impl_does_not_create_status_dir(tmp_path):
    result = folder_status_impl(str(tmp_path))
    assert result["statuses"]["wechat"] is None
    assert not (tmp_path / ".status").exists()


def test_validate_folder_impl(tmp_path):
    (tmp_path / "video.mp4").write_bytes(b"video")
    (tmp_path / "cover.jpg").write_bytes(b"cover")
    (tmp_path / "metadata.md").write_text(
        "[wechat]\n标题: 校验\n描述: desc\n标签: #测试",
        encoding="utf-8",
    )

    result = validate_folder_impl(str(tmp_path))
    assert result["ok"] is True
    assert result["platforms"] == ["wechat"]
    assert result["metadata_file"].endswith("metadata.md")


def test_validate_folder_impl_returns_errors(tmp_path):
    result = validate_folder_impl(str(tmp_path))
    assert result["ok"] is False
    assert result["errors"]


def test_validate_folder_impl_rejects_empty_platforms(tmp_path):
    (tmp_path / "video.mp4").write_bytes(b"video")
    (tmp_path / "cover.jpg").write_bytes(b"cover")
    (tmp_path / "metadata.txt").write_text(
        "视频路径: video.mp4\n封面路径: cover.jpg\n",
        encoding="utf-8",
    )

    result = validate_folder_impl(str(tmp_path))
    assert result["ok"] is False
    assert result["platforms"] == []
    assert any("未找到任何平台段" in msg for msg in result["errors"])


def test_list_publishable_folders_impl(tmp_path):
    good = tmp_path / "good"
    good.mkdir()
    (good / "video.mp4").write_bytes(b"video")
    (good / "cover.jpg").write_bytes(b"cover")
    (good / "metadata.txt").write_text(
        "[bilibili]\n标题: 可发布\n描述: desc\n标签: #测试",
        encoding="utf-8",
    )
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "video.mp4").write_bytes(b"video")

    result = list_publishable_folders_impl(str(tmp_path))
    assert len(result["folders"]) == 1
    assert result["folders"][0]["folder"].endswith("/good")


def test_list_publishable_folders_impl_skips_empty_platforms(tmp_path):
    empty_meta = tmp_path / "empty-meta"
    empty_meta.mkdir()
    (empty_meta / "video.mp4").write_bytes(b"video")
    (empty_meta / "cover.jpg").write_bytes(b"cover")
    (empty_meta / "metadata.txt").write_text(
        "视频路径: video.mp4\n封面路径: cover.jpg\n",
        encoding="utf-8",
    )

    result = list_publishable_folders_impl(str(tmp_path))
    assert result["folders"] == []


def test_settings_impl():
    result = settings_impl()
    assert "upload_timeout" in result


def test_platform_config_impl_accepts_alias():
    result = platform_config_impl("视频号")
    assert result["platform"] == "wechat"
    assert isinstance(result["config"], dict)


def test_configure_server_updates_settings(monkeypatch):
    calls = {}

    def fake_run(*, transport, mount_path=None):
        calls["transport"] = transport
        calls["mount_path"] = mount_path

    from videopub import mcp_server

    monkeypatch.setattr(mcp_server.mcp, "run", fake_run)
    _configure_server(
        transport="streamable-http",
        host="0.0.0.0",
        port=9000,
        mount_path="/sse-root",
        streamable_http_path="/vp",
    )
    assert mcp_server.mcp.settings.host == "0.0.0.0"
    assert mcp_server.mcp.settings.port == 9000
    assert mcp_server.mcp.settings.streamable_http_path == "/vp"
    assert calls == {"transport": "streamable-http", "mount_path": None}
