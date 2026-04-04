"""Word (.docx) 和 PDF 元数据解析测试"""

import json
import textwrap
from pathlib import Path

import pytest

from videopub.core.metadata_parser import _parse_kv_text, parse
from videopub.core.models import Platform


# ── 工具：构造包含视频/封面的文件夹 ──────────────────────────────────────────

def make_folder(tmp_path: Path, meta_text: str, suffix: str = ".docx") -> Path:
    """在 tmp_path 下创建包含视频/封面/元数据的文件夹"""
    (tmp_path / "video.mp4").write_bytes(b"fake")
    (tmp_path / "cover.jpg").write_bytes(b"fake")
    meta_file = tmp_path / f"metadata{suffix}"
    meta_file.write_text(meta_text, encoding="utf-8")
    return tmp_path


# ── _parse_kv_text 单元测试 ───────────────────────────────────────────────────

KV_SAMPLE = textwrap.dedent("""\
    视频路径: video.mp4
    封面路径: cover.jpg

    [bilibili]
    标题: 磁珠纯化误区
    简介: 详细讲解三个坑
    标签: 磁珠, 纯化, 科研
    分类: 201

    [youtube]
    标题: Bead Mistakes
    描述: In this video
    标签: bead, purification
    定时发布: 2026-04-03 20:00
""")


class TestParseKvText:
    def test_two_platforms(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")
        task = _parse_kv_text(KV_SAMPLE, tmp_path)
        assert len(task.platforms) == 2

    def test_bilibili_fields(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")
        task = _parse_kv_text(KV_SAMPLE, tmp_path)
        bili = next(p for p in task.platforms if p.platform == Platform.BILIBILI)
        assert bili.title == "磁珠纯化误区"
        assert bili.description == "详细讲解三个坑"
        assert "磁珠" in bili.tags
        assert bili.category == "201"

    def test_youtube_scheduled_time(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")
        task = _parse_kv_text(KV_SAMPLE, tmp_path)
        yt = next(p for p in task.platforms if p.platform == Platform.YOUTUBE)
        assert yt.scheduled_time is not None
        assert yt.scheduled_time.hour == 20

    def test_chinese_platform_alias(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")
        text = "[抖音]\n标题: 抖音测试\n描述: desc\n标签: tag"
        task = _parse_kv_text(text, tmp_path)
        assert task.platforms[0].platform == Platform.DOUYIN

    def test_tags_split_comma(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")
        text = "[bilibili]\n标题: t\n描述: d\n标签: a,b，c、d"
        task = _parse_kv_text(text, tmp_path)
        assert task.platforms[0].tags == ["a", "b", "c", "d"]

    def test_tags_split_hashtag_style(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")
        text = "[微信视频号]\n标题: t\n描述: d\n标签: #血压计 #高血压 #健康"
        task = _parse_kv_text(text, tmp_path)
        assert task.platforms[0].tags == ["血压计", "高血压", "健康"]

    def test_is_original_false(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")
        text = "[bilibili]\n标题: t\n描述: d\n标签: x\n是否原创: 否"
        task = _parse_kv_text(text, tmp_path)
        assert task.platforms[0].is_original is False

    def test_fullwidth_colon_and_wechat_collection_fallback(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")
        text = "[微信视频号]\n标题: t\n短标题：短标题\n描述: d\n分类：家庭健康避坑\n定时发布：2026-04-05 21:00"
        task = _parse_kv_text(text, tmp_path)
        wechat = task.platforms[0]
        assert wechat.short_title == "短标题"
        assert wechat.collection == "家庭健康避坑"
        assert wechat.scheduled_time is not None
        assert wechat.scheduled_time.hour == 21

    def test_video_auto_find_when_no_path(self, tmp_path):
        (tmp_path / "my_video.mp4").write_bytes(b"x")
        (tmp_path / "cover.jpg").write_bytes(b"x")
        text = "[bilibili]\n标题: t\n描述: d\n标签: x"
        task = _parse_kv_text(text, tmp_path)
        assert task.video_path.suffix == ".mp4"


# ── Word 解析（通过 python-docx 构造文件）────────────────────────────────────

class TestParseDocx:
    @pytest.fixture
    def docx_folder(self, tmp_path):
        """创建真实 docx 文件（用 python-docx 写入）"""
        pytest.importorskip("docx", reason="python-docx 未安装，跳过")
        import docx as docx_mod

        (tmp_path / "video.mp4").write_bytes(b"fake")
        (tmp_path / "cover.jpg").write_bytes(b"fake")

        doc = docx_mod.Document()
        for line in KV_SAMPLE.strip().splitlines():
            doc.add_paragraph(line)
        doc.save(str(tmp_path / "metadata.docx"))
        return tmp_path

    def test_parse_docx_two_platforms(self, docx_folder):
        task = parse(docx_folder)
        assert len(task.platforms) == 2

    def test_parse_docx_bilibili_title(self, docx_folder):
        task = parse(docx_folder)
        bili = next(p for p in task.platforms if p.platform == Platform.BILIBILI)
        assert bili.title == "磁珠纯化误区"

    def test_parse_docx_youtube_scheduled(self, docx_folder):
        task = parse(docx_folder)
        yt = next(p for p in task.platforms if p.platform == Platform.YOUTUBE)
        assert yt.scheduled_time is not None


# ── PDF 解析（通过 reportlab 构造文件）──────────────────────────────────────

class TestParsePdf:
    @pytest.fixture
    def pdf_folder(self, tmp_path):
        """创建真实 PDF（用 reportlab 写入，pdfplumber 读取）"""
        pytest.importorskip("pdfplumber", reason="pdfplumber 未安装，跳过")
        reportlab = pytest.importorskip("reportlab", reason="reportlab 未安装，跳过 PDF 创建")

        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as rl_canvas

        (tmp_path / "video.mp4").write_bytes(b"fake")
        (tmp_path / "cover.jpg").write_bytes(b"fake")

        pdf_path = tmp_path / "metadata.pdf"
        c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
        y = 800
        for line in KV_SAMPLE.strip().splitlines():
            c.drawString(50, y, line)
            y -= 20
        c.save()
        return tmp_path

    def test_parse_pdf_two_platforms(self, pdf_folder):
        task = parse(pdf_folder)
        assert len(task.platforms) == 2
