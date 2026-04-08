"""MCP server helper tests."""

from videopub.core.models import Platform, PlatformMeta, PublishTask, UploadResult
from videopub.core.status import StatusState, write_status
from videopub.mcp_server import (
    _normalize_platforms,
    folder_status_impl,
    parse_folder_impl,
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
