"""orchestrator 测试（Mock 上传器）"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from videopub.core.models import Platform, UploadResult
from videopub.core.orchestrator import process_folder
from videopub.core.status import StatusState, read_status


# ── 工具：构造测试文件夹 ──────────────────────────────────────────────────────

def make_publish_folder(tmp_path: Path, platforms: list[str] | None = None) -> Path:
    """创建包含视频、封面和 metadata.json 的测试文件夹"""
    (tmp_path / "video.mp4").write_bytes(b"fake")
    (tmp_path / "cover.jpg").write_bytes(b"fake")

    plats = platforms or ["bilibili", "youtube"]
    metadata = {
        "platforms": [
            {
                "platform": p,
                "title": f"标题 {p}",
                "description": f"简介 {p}",
                "tags": ["tag"],
                "first_comment": f"首评 {p}",
            }
            for p in plats
        ]
    }
    (tmp_path / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False),
        encoding="utf-8",
    )
    return tmp_path


def _mock_uploader(success: bool = True, video_id: str = "V001", platform: Platform = Platform.BILIBILI):
    """返回一个 Mock 上传器"""
    uploader = AsyncMock()
    uploader.check_session.return_value = True
    uploader.login.return_value = True
    uploader.upload.return_value = UploadResult(
        platform=platform,
        success=success,
        video_id=video_id if success else None,
        video_url=f"https://example.com/{video_id}" if success else None,
        error=None if success else "上传失败",
    )
    uploader.post_comment.return_value = True
    return uploader


# ── 测试 ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_folder_success(tmp_path):
    """正常上传，状态变为 DONE"""
    folder = make_publish_folder(tmp_path, ["bilibili"])

    mock_up = _mock_uploader(platform=Platform.BILIBILI)
    with patch("videopub.core.orchestrator._get_uploader", return_value=mock_up):
        results = await process_folder(folder)

    assert len(results) == 1
    assert results[0].success is True
    assert read_status(folder, Platform.BILIBILI) == StatusState.DONE


@pytest.mark.asyncio
async def test_process_folder_failure(tmp_path):
    """上传失败，状态变为 ERROR"""
    folder = make_publish_folder(tmp_path, ["bilibili"])

    mock_up = _mock_uploader(success=False, platform=Platform.BILIBILI)
    with patch("videopub.core.orchestrator._get_uploader", return_value=mock_up):
        results = await process_folder(folder)

    assert results[0].success is False
    assert read_status(folder, Platform.BILIBILI) == StatusState.ERROR


@pytest.mark.asyncio
async def test_process_folder_skips_done(tmp_path):
    """已 DONE 的平台不重复上传"""
    from videopub.core.status import write_status

    folder = make_publish_folder(tmp_path, ["bilibili"])
    write_status(folder, Platform.BILIBILI, StatusState.DONE)

    mock_up = _mock_uploader(platform=Platform.BILIBILI)
    with patch("videopub.core.orchestrator._get_uploader", return_value=mock_up):
        results = await process_folder(folder)

    # 已完成，不应调用 upload
    mock_up.upload.assert_not_called()
    assert results == []


@pytest.mark.asyncio
async def test_process_folder_platform_filter(tmp_path):
    """platforms 过滤参数生效"""
    folder = make_publish_folder(tmp_path, ["bilibili", "youtube"])

    mock_up = _mock_uploader(platform=Platform.BILIBILI)
    with patch("videopub.core.orchestrator._get_uploader", return_value=mock_up):
        results = await process_folder(folder, platforms=["bilibili"])

    assert len(results) == 1
    assert results[0].platform == Platform.BILIBILI


@pytest.mark.asyncio
async def test_process_folder_login_failure(tmp_path):
    """登录失败时状态应为 ERROR"""
    folder = make_publish_folder(tmp_path, ["bilibili"])

    mock_up = AsyncMock()
    mock_up.check_session.return_value = False
    mock_up.login.return_value = False

    with patch("videopub.core.orchestrator._get_uploader", return_value=mock_up):
        results = await process_folder(folder)

    assert results[0].success is False
    assert read_status(folder, Platform.BILIBILI) == StatusState.ERROR


@pytest.mark.asyncio
async def test_process_folder_post_comment_called(tmp_path):
    """上传成功且有首评时，应调用 post_comment"""
    folder = make_publish_folder(tmp_path, ["bilibili"])

    mock_up = _mock_uploader(platform=Platform.BILIBILI, video_id="BV1xx")
    with patch("videopub.core.orchestrator._get_uploader", return_value=mock_up):
        await process_folder(folder)

    mock_up.post_comment.assert_called_once_with("BV1xx", "首评 bilibili")


@pytest.mark.asyncio
async def test_process_folder_status_uploading_then_done(tmp_path):
    """upload 期间状态为 UPLOADING，完成后为 DONE"""
    from videopub.core.status import write_status as ws

    folder = make_publish_folder(tmp_path, ["bilibili"])
    states_seen = []

    original_upload = None

    async def fake_upload(task):
        # 检查进入 upload 前状态已设置为 UPLOADING
        states_seen.append(read_status(folder, Platform.BILIBILI))
        return UploadResult(platform=Platform.BILIBILI, success=True)

    mock_up = AsyncMock()
    mock_up.check_session.return_value = True
    mock_up.login.return_value = True
    mock_up.upload.side_effect = fake_upload
    mock_up.post_comment.return_value = True

    with patch("videopub.core.orchestrator._get_uploader", return_value=mock_up):
        await process_folder(folder)

    assert StatusState.UPLOADING in states_seen
    assert read_status(folder, Platform.BILIBILI) == StatusState.DONE
