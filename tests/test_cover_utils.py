from pathlib import Path

from PIL import Image

from videopub.core.cover_utils import (
    DOUYIN_LANDSCAPE_SIZE,
    DOUYIN_PORTRAIT_SIZE,
    LANDSCAPE_SIZE,
    ensure_douyin_landscape_cover,
    ensure_douyin_portrait_cover,
    ensure_landscape_cover,
    ensure_portrait_safe_cover,
    ensure_wechat_cover,
)


def test_landscape_cover_returns_original(tmp_path: Path):
    cover = tmp_path / "cover.jpg"
    Image.new("RGB", (1920, 1080), color=(30, 60, 90)).save(cover)

    result = ensure_landscape_cover(cover)

    assert result == cover


def test_portrait_cover_generates_blurred_landscape(tmp_path: Path):
    cover = tmp_path / "cover.jpg"
    Image.new("RGB", (1080, 1920), color=(220, 120, 80)).save(cover)

    result = ensure_landscape_cover(cover)

    assert result != cover
    assert result.name == "cover__landscape.jpg"
    assert result.parent == tmp_path
    assert result.exists()

    with Image.open(result) as generated:
        assert generated.size == LANDSCAPE_SIZE


def test_portrait_cover_generates_safe_portrait_version(tmp_path: Path):
    cover = tmp_path / "cover.jpg"
    Image.new("RGB", (1080, 1920), color=(80, 120, 220)).save(cover)

    result = ensure_portrait_safe_cover(cover)

    assert result != cover
    assert result.name == "cover__portrait_safe.jpg"
    assert result.parent == tmp_path
    assert result.exists()

    with Image.open(result) as generated:
        assert generated.size == (1080, 1920)


def test_landscape_name_stays_clean_after_portrait_safe_step(tmp_path: Path):
    cover = tmp_path / "cover.jpg"
    Image.new("RGB", (1080, 1920), color=(60, 80, 120)).save(cover)

    portrait_safe = ensure_portrait_safe_cover(cover)
    landscape = ensure_landscape_cover(portrait_safe)

    assert portrait_safe.name == "cover__portrait_safe.jpg"
    assert landscape.name == "cover__landscape.jpg"


def test_wechat_cover_generates_3x4_version(tmp_path: Path):
    cover = tmp_path / "cover.jpg"
    Image.new("RGB", (1080, 1920), color=(40, 120, 180)).save(cover)

    result = ensure_wechat_cover(cover)

    assert result.name == "cover__wechat_3x4.jpg"
    assert result.parent == tmp_path
    assert result.exists()

    with Image.open(result) as generated:
        assert generated.size == (1080, 1440)


def test_douyin_portrait_cover_generates_3x4_version(tmp_path: Path):
    cover = tmp_path / "cover.jpg"
    Image.new("RGB", (1080, 1920), color=(40, 120, 180)).save(cover)

    result = ensure_douyin_portrait_cover(cover)

    assert result.name == "cover__douyin_3x4.jpg"
    assert result.parent == tmp_path
    assert result.exists()

    with Image.open(result) as generated:
        assert generated.size == DOUYIN_PORTRAIT_SIZE


def test_douyin_landscape_cover_generates_4x3_version(tmp_path: Path):
    cover = tmp_path / "cover.jpg"
    Image.new("RGB", (1080, 1920), color=(40, 120, 180)).save(cover)

    result = ensure_douyin_landscape_cover(cover)

    assert result.name == "cover__douyin_4x3.jpg"
    assert result.parent == tmp_path
    assert result.exists()

    with Image.open(result) as generated:
        assert generated.size == DOUYIN_LANDSCAPE_SIZE
