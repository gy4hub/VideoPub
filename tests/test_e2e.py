"""端到端测试：4 平台 Mock 全流程"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from videopub.core.models import Platform, UploadResult
from videopub.core.orchestrator import process_folder
from videopub.core.status import StatusState, read_status, read_status_detail


# ── 测试夹具 ──────────────────────────────────────────────────────────────────

@pytest.fixture
def four_platform_folder(tmp_path):
    """创建包含全部 4 个平台的发布文件夹"""
    (tmp_path / "lecture.mp4").write_bytes(b"fake video")
    (tmp_path / "cover.jpg").write_bytes(b"fake cover")

    metadata = {
        "platforms": [
            {
                "platform": "bilibili",
                "title": "【科研干货】磁珠纯化误区",
                "description": "磁珠纯化三大坑详解",
                "tags": ["磁珠", "纯化", "科研"],
                "category": "201",
                "first_comment": "你们用什么品牌的磁珠？",
            },
            {
                "platform": "youtube",
                "title": "3 Mistakes in Magnetic Bead Purification",
                "description": "We cover the three most common pitfalls.",
                "tags": ["magnetic beads", "purification"],
                "first_comment": "Subscribe for more lab tips!",
            },
            {
                "platform": "douyin",
                "title": "磁珠纯化的三大误区",
                "description": "手把手讲解三个坑",
                "tags": ["磁珠", "实验技巧"],
                "first_comment": "关注获取更多科研干货！",
            },
            {
                "platform": "wechat",
                "title": "磁珠纯化常见误区详解",
                "short_title": "磁珠纯化误区",
                "description": "详细讲解视频...",
                "tags": ["磁珠纯化"],
                "is_original": True,
            },
        ]
    }
    (tmp_path / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


def _make_uploader(platform: Platform, video_id: str = "VID001") -> AsyncMock:
    """构造成功的 Mock 上传器"""
    up = AsyncMock()
    up.check_session.return_value = True
    up.login.return_value = True
    up.upload.return_value = UploadResult(
        platform=platform,
        success=True,
        video_id=video_id,
        video_url=f"https://example.com/{platform.value}/{video_id}",
    )
    up.post_comment.return_value = True
    return up


# ── 4 平台全成功测试 ──────────────────────────────────────────────────────────

async def test_e2e_all_platforms_success(four_platform_folder):
    """全部 4 个平台上传成功，状态均为 DONE"""
    mock_uploaders = {
        Platform.BILIBILI: _make_uploader(Platform.BILIBILI, "BV1xx"),
        Platform.YOUTUBE: _make_uploader(Platform.YOUTUBE, "dQw4w9"),
        Platform.DOUYIN: _make_uploader(Platform.DOUYIN, "DY001"),
        Platform.WECHAT: _make_uploader(Platform.WECHAT, "WX001"),
    }

    def fake_get_uploader(platform):
        return mock_uploaders.get(platform)

    with patch("videopub.core.orchestrator._get_uploader", side_effect=fake_get_uploader):
        results = await process_folder(four_platform_folder)

    assert len(results) == 4
    assert all(r.success for r in results)

    for platform in Platform:
        assert read_status(four_platform_folder, platform) == StatusState.DONE


async def test_e2e_status_files_contain_video_info(four_platform_folder):
    """DONE 状态文件中包含 video_id 和 video_url"""
    mock_uploaders = {p: _make_uploader(p, f"ID_{p.value}") for p in Platform}

    with patch("videopub.core.orchestrator._get_uploader",
               side_effect=lambda p: mock_uploaders.get(p)):
        await process_folder(four_platform_folder)

    detail = read_status_detail(four_platform_folder, Platform.BILIBILI)
    assert detail is not None
    assert detail["video_id"] == "ID_bilibili"
    assert "bilibili" in detail["video_url"]


async def test_e2e_first_comment_sent_for_all(four_platform_folder):
    """所有有首评的平台都调用了 post_comment"""
    mock_uploaders = {p: _make_uploader(p, f"V_{p.value}") for p in Platform}

    with patch("videopub.core.orchestrator._get_uploader",
               side_effect=lambda p: mock_uploaders.get(p)):
        await process_folder(four_platform_folder)

    # bilibili, youtube, douyin 均有 first_comment
    mock_uploaders[Platform.BILIBILI].post_comment.assert_called_once()
    mock_uploaders[Platform.YOUTUBE].post_comment.assert_called_once()
    mock_uploaders[Platform.DOUYIN].post_comment.assert_called_once()
    # wechat 没有 first_comment，不应调用
    mock_uploaders[Platform.WECHAT].post_comment.assert_not_called()


# ── 部分失败测试 ───────────────────────────────────────────────────────────────

async def test_e2e_partial_failure(four_platform_folder):
    """YouTube 失败，其他平台不受影响"""
    mock_uploaders = {p: _make_uploader(p) for p in Platform}
    mock_uploaders[Platform.YOUTUBE].upload.return_value = UploadResult(
        platform=Platform.YOUTUBE,
        success=False,
        error="配额超限",
    )

    with patch("videopub.core.orchestrator._get_uploader",
               side_effect=lambda p: mock_uploaders.get(p)):
        results = await process_folder(four_platform_folder)

    yt_result = next(r for r in results if r.platform == Platform.YOUTUBE)
    assert yt_result.success is False
    assert read_status(four_platform_folder, Platform.YOUTUBE) == StatusState.ERROR

    # 其余平台应成功
    for platform in [Platform.BILIBILI, Platform.DOUYIN, Platform.WECHAT]:
        assert read_status(four_platform_folder, platform) == StatusState.DONE


# ── 幂等性测试 ────────────────────────────────────────────────────────────────

async def test_e2e_idempotent_rerun(four_platform_folder):
    """第一次运行后，重复运行不会重复上传"""
    mock_uploaders = {p: _make_uploader(p) for p in Platform}

    with patch("videopub.core.orchestrator._get_uploader",
               side_effect=lambda p: mock_uploaders.get(p)):
        await process_folder(four_platform_folder)
        # 第二次运行
        results = await process_folder(four_platform_folder)

    # 第二次没有任何平台需要上传
    assert results == []
    # 每个上传器的 upload 只被调用了一次
    for up in mock_uploaders.values():
        up.upload.assert_called_once()


# ── 平台过滤测试 ───────────────────────────────────────────────────────────────

async def test_e2e_platform_filter(four_platform_folder):
    """只发布到 bilibili 和 youtube"""
    mock_uploaders = {p: _make_uploader(p) for p in Platform}

    with patch("videopub.core.orchestrator._get_uploader",
               side_effect=lambda p: mock_uploaders.get(p)):
        results = await process_folder(
            four_platform_folder, platforms=["bilibili", "youtube"]
        )

    assert len(results) == 2
    platforms_published = {r.platform for r in results}
    assert Platform.BILIBILI in platforms_published
    assert Platform.YOUTUBE in platforms_published

    # 抖音/微信不应被调用
    mock_uploaders[Platform.DOUYIN].upload.assert_not_called()
    mock_uploaders[Platform.WECHAT].upload.assert_not_called()


# ── 登录失败测试 ───────────────────────────────────────────────────────────────

async def test_e2e_login_required_and_fails(four_platform_folder):
    """Cookie 过期且登录失败时，状态为 ERROR，其余平台继续"""
    mock_uploaders = {p: _make_uploader(p) for p in Platform}
    mock_uploaders[Platform.DOUYIN].check_session.return_value = False
    mock_uploaders[Platform.DOUYIN].login.return_value = False

    with patch("videopub.core.orchestrator._get_uploader",
               side_effect=lambda p: mock_uploaders.get(p)):
        results = await process_folder(four_platform_folder)

    douyin_result = next(r for r in results if r.platform == Platform.DOUYIN)
    assert douyin_result.success is False
    assert read_status(four_platform_folder, Platform.DOUYIN) == StatusState.ERROR

    # 其余平台正常
    assert read_status(four_platform_folder, Platform.BILIBILI) == StatusState.DONE
