"""元数据解析测试"""

import json

import pytest

from videopub.core.metadata_parser import _find_metadata_file, parse
from videopub.core.models import Platform


@pytest.fixture
def sample_folder(tmp_path):
    """创建一个包含视频、封面和 metadata.json 的测试文件夹"""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake video content")

    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"fake cover content")

    metadata = {
        "video_path": "video.mp4",
        "cover_path": "cover.jpg",
        "platforms": [
            {
                "platform": "bilibili",
                "title": "【科研干货】磁珠纯化的三大常见误区",
                "description": "本期视频详细讲解磁珠纯化技术中最容易踩的三个坑",
                "tags": ["磁珠", "纯化技术", "科研"],
                "category": "科学科普",
            },
            {
                "platform": "youtube",
                "title": "3 Common Mistakes in Magnetic Bead Purification",
                "description": "In this video, we cover the three most common pitfalls",
                "tags": ["magnetic beads", "purification", "laboratory"],
                "category": "Science & Technology",
                "scheduled_time": "2026-04-03T08:00:00Z",
            },
        ],
    }
    meta_file = tmp_path / "metadata.json"
    meta_file.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    return tmp_path


@pytest.fixture
def minimal_folder(tmp_path):
    """最小化文件夹：只有一个平台"""
    (tmp_path / "test.mp4").write_bytes(b"video")
    (tmp_path / "thumb.png").write_bytes(b"cover")
    metadata = {
        "platforms": [
            {
                "platform": "bilibili",
                "title": "测试",
                "description": "测试简介",
                "tags": ["test"],
            }
        ]
    }
    (tmp_path / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False),
        encoding="utf-8",
    )
    return tmp_path


class TestParseJSON:
    def test_parse_multi_platform(self, sample_folder):
        task = parse(sample_folder)
        assert len(task.platforms) == 2
        assert task.platforms[0].platform == Platform.BILIBILI
        assert task.platforms[1].platform == Platform.YOUTUBE
        assert task.video_path.exists()
        assert task.cover_path.exists()

    def test_parse_bilibili_fields(self, sample_folder):
        task = parse(sample_folder)
        bili = task.platforms[0]
        assert bili.title == "【科研干货】磁珠纯化的三大常见误区"
        assert bili.category == "科学科普"
        assert "磁珠" in bili.tags

    def test_parse_youtube_scheduled(self, sample_folder):
        task = parse(sample_folder)
        yt = task.platforms[1]
        assert yt.scheduled_time is not None
        assert yt.category == "Science & Technology"

    def test_parse_minimal(self, minimal_folder):
        task = parse(minimal_folder)
        assert len(task.platforms) == 1
        assert task.platforms[0].platform == Platform.BILIBILI
        assert task.video_path.exists()

    def test_parse_auto_find_video(self, minimal_folder):
        """当 video_path 不在 JSON 中时，自动查找"""
        task = parse(minimal_folder)
        assert task.video_path.name == "test.mp4"

    def test_parse_missing_metadata_raises(self, tmp_path):
        """文件夹中没有元数据文件时应报错"""
        with pytest.raises(FileNotFoundError, match="未找到元数据文件"):
            parse(tmp_path)

    def test_parse_not_a_directory_raises(self, tmp_path):
        """传入文件路径而非文件夹时应报错"""
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("hello")
        with pytest.raises(ValueError, match="不是文件夹"):
            parse(file_path)


class TestFindMetadataFile:
    def test_finds_json(self, tmp_path):
        (tmp_path / "metadata.json").write_text("{}")
        result = _find_metadata_file(tmp_path)
        assert result.name == "metadata.json"

    def test_json_priority_over_docx(self, tmp_path):
        (tmp_path / "metadata.json").write_text("{}")
        (tmp_path / "metadata.docx").write_bytes(b"")
        result = _find_metadata_file(tmp_path)
        assert result.suffix == ".json"
