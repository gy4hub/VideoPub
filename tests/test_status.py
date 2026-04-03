"""status 模块测试"""

import json
from pathlib import Path

import pytest

from videopub.core.models import Platform
from videopub.core.status import (
    StatusState,
    read_status,
    read_status_detail,
    write_status,
)


class TestWriteStatus:
    def test_creates_status_dir(self, tmp_path):
        write_status(tmp_path, Platform.BILIBILI, StatusState.PENDING)
        assert (tmp_path / ".status").is_dir()

    def test_creates_json_file(self, tmp_path):
        write_status(tmp_path, Platform.BILIBILI, StatusState.PENDING)
        sf = tmp_path / ".status" / "bilibili.json"
        assert sf.exists()

    def test_json_content_state(self, tmp_path):
        write_status(tmp_path, Platform.YOUTUBE, StatusState.UPLOADING)
        data = json.loads((tmp_path / ".status" / "youtube.json").read_text())
        assert data["state"] == "uploading"
        assert data["platform"] == "youtube"
        assert "updated_at" in data

    def test_done_with_video_info(self, tmp_path):
        write_status(
            tmp_path,
            Platform.BILIBILI,
            StatusState.DONE,
            video_id="BV1xx",
            video_url="https://bilibili.com/video/BV1xx",
        )
        data = json.loads((tmp_path / ".status" / "bilibili.json").read_text())
        assert data["state"] == "done"
        assert data["video_id"] == "BV1xx"
        assert "bilibili.com" in data["video_url"]

    def test_error_with_message(self, tmp_path):
        write_status(tmp_path, Platform.DOUYIN, StatusState.ERROR, error="登录失败")
        data = json.loads((tmp_path / ".status" / "douyin.json").read_text())
        assert data["state"] == "error"
        assert data["error"] == "登录失败"

    def test_overwrites_existing(self, tmp_path):
        write_status(tmp_path, Platform.WECHAT, StatusState.UPLOADING)
        write_status(tmp_path, Platform.WECHAT, StatusState.DONE)
        assert read_status(tmp_path, Platform.WECHAT) == StatusState.DONE


class TestReadStatus:
    def test_returns_none_when_missing(self, tmp_path):
        assert read_status(tmp_path, Platform.BILIBILI) is None

    def test_reads_correct_state(self, tmp_path):
        write_status(tmp_path, Platform.YOUTUBE, StatusState.DONE)
        assert read_status(tmp_path, Platform.YOUTUBE) == StatusState.DONE

    def test_each_platform_independent(self, tmp_path):
        write_status(tmp_path, Platform.BILIBILI, StatusState.DONE)
        write_status(tmp_path, Platform.YOUTUBE, StatusState.ERROR)
        assert read_status(tmp_path, Platform.BILIBILI) == StatusState.DONE
        assert read_status(tmp_path, Platform.YOUTUBE) == StatusState.ERROR

    def test_read_detail(self, tmp_path):
        write_status(
            tmp_path,
            Platform.BILIBILI,
            StatusState.DONE,
            video_id="BV1xx",
        )
        detail = read_status_detail(tmp_path, Platform.BILIBILI)
        assert detail is not None
        assert detail["video_id"] == "BV1xx"

    def test_read_detail_missing(self, tmp_path):
        assert read_status_detail(tmp_path, Platform.DOUYIN) is None
