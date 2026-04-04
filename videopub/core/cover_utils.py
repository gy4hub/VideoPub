"""封面图处理工具。"""

from pathlib import Path


LANDSCAPE_SIZE = (1920, 1080)
DOUYIN_PORTRAIT_SIZE = (1080, 1440)
DOUYIN_LANDSCAPE_SIZE = (1440, 1080)
WECHAT_COVER_SIZE = (1080, 1440)
PORTRAIT_SAFE_WIDTH_RATIO = 0.9
PORTRAIT_SAFE_HEIGHT_RATIO = 0.9
LANDSCAPE_SAFE_WIDTH_RATIO = 0.82
LANDSCAPE_SAFE_HEIGHT_RATIO = 0.88
YOUTUBE_LANDSCAPE_SAFE_WIDTH_RATIO = 1.0
YOUTUBE_LANDSCAPE_SAFE_HEIGHT_RATIO = 1.0
DOUYIN_PORTRAIT_SAFE_WIDTH_RATIO = 1.0
DOUYIN_PORTRAIT_SAFE_HEIGHT_RATIO = 1.0
DOUYIN_LANDSCAPE_SAFE_WIDTH_RATIO = 1.0
DOUYIN_LANDSCAPE_SAFE_HEIGHT_RATIO = 1.0
WECHAT_SAFE_WIDTH_RATIO = 1.0
WECHAT_SAFE_HEIGHT_RATIO = 1.0
WECHAT_FOREGROUND_OFFSET_Y_RATIO = 0.0


def ensure_portrait_safe_cover(
    cover_path: Path,
    *,
    output_dir: Path | None = None,
) -> Path:
    """确保竖版封面留出安全边距，避免平台二次裁切截掉文字。"""
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise ImportError("需要 Pillow 才能自动生成安全封面") from exc

    cover_path = Path(cover_path)
    try:
        with Image.open(cover_path) as src:
            image = ImageOps.exif_transpose(src).convert("RGB")
            if image.width >= image.height:
                return cover_path

            output_root = output_dir or cover_path.parent
            output_root.mkdir(parents=True, exist_ok=True)
            output_path = _derived_output_path(cover_path, output_root, "__portrait_safe.jpg")
            return _build_safe_cover(
                image=image,
                output_path=output_path,
                target_size=image.size,
                width_ratio=PORTRAIT_SAFE_WIDTH_RATIO,
                height_ratio=PORTRAIT_SAFE_HEIGHT_RATIO,
            )
    except UnidentifiedImageError:
        return cover_path


def ensure_wechat_cover(
    cover_path: Path,
    *,
    output_dir: Path | None = None,
    target_size: tuple[int, int] = WECHAT_COVER_SIZE,
) -> Path:
    """生成适合视频号 3:4 预览卡片的封面图。"""
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise ImportError("需要 Pillow 才能自动生成视频号封面") from exc

    cover_path = Path(cover_path)
    try:
        with Image.open(cover_path) as src:
            image = ImageOps.exif_transpose(src).convert("RGB")
            output_root = output_dir or cover_path.parent
            output_root.mkdir(parents=True, exist_ok=True)
            output_path = _derived_output_path(cover_path, output_root, "__wechat_3x4.jpg")
            return _build_safe_cover(
                image=image,
                output_path=output_path,
                target_size=target_size,
                width_ratio=WECHAT_SAFE_WIDTH_RATIO,
                height_ratio=WECHAT_SAFE_HEIGHT_RATIO,
                offset_y_ratio=WECHAT_FOREGROUND_OFFSET_Y_RATIO,
            )
    except UnidentifiedImageError:
        return cover_path


def ensure_douyin_portrait_cover(
    cover_path: Path,
    *,
    output_dir: Path | None = None,
    target_size: tuple[int, int] = DOUYIN_PORTRAIT_SIZE,
) -> Path:
    """生成适合抖音竖封面 3:4 的专用封面图。"""
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise ImportError("需要 Pillow 才能自动生成抖音竖封面") from exc

    cover_path = Path(cover_path)
    try:
        with Image.open(cover_path) as src:
            image = ImageOps.exif_transpose(src).convert("RGB")
            output_root = output_dir or cover_path.parent
            output_root.mkdir(parents=True, exist_ok=True)
            output_path = _derived_output_path(cover_path, output_root, "__douyin_3x4.jpg")
            return _build_safe_cover(
                image=image,
                output_path=output_path,
                target_size=target_size,
                width_ratio=DOUYIN_PORTRAIT_SAFE_WIDTH_RATIO,
                height_ratio=DOUYIN_PORTRAIT_SAFE_HEIGHT_RATIO,
            )
    except UnidentifiedImageError:
        return cover_path


def ensure_douyin_landscape_cover(
    cover_path: Path,
    *,
    output_dir: Path | None = None,
    target_size: tuple[int, int] = DOUYIN_LANDSCAPE_SIZE,
) -> Path:
    """生成适合抖音横封面 4:3 的专用封面图。"""
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise ImportError("需要 Pillow 才能自动生成抖音横封面") from exc

    cover_path = Path(cover_path)
    try:
        with Image.open(cover_path) as src:
            image = ImageOps.exif_transpose(src).convert("RGB")
            output_root = output_dir or cover_path.parent
            output_root.mkdir(parents=True, exist_ok=True)
            output_path = _derived_output_path(cover_path, output_root, "__douyin_4x3.jpg")
            return _build_safe_cover(
                image=image,
                output_path=output_path,
                target_size=target_size,
                width_ratio=DOUYIN_LANDSCAPE_SAFE_WIDTH_RATIO,
                height_ratio=DOUYIN_LANDSCAPE_SAFE_HEIGHT_RATIO,
            )
    except UnidentifiedImageError:
        return cover_path


def ensure_landscape_cover(
    cover_path: Path,
    *,
    output_dir: Path | None = None,
    target_size: tuple[int, int] = LANDSCAPE_SIZE,
) -> Path:
    """确保封面为横版；竖版时自动生成模糊背景横版图。"""
    try:
        from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise ImportError("需要 Pillow 才能自动生成横版封面") from exc

    cover_path = Path(cover_path)
    try:
        with Image.open(cover_path) as src:
            image = ImageOps.exif_transpose(src).convert("RGB")
            if image.width >= image.height:
                return cover_path

            output_root = output_dir or cover_path.parent
            output_root.mkdir(parents=True, exist_ok=True)
            output_path = _derived_output_path(cover_path, output_root, "__landscape.jpg")

            return _build_safe_cover(
                image=image,
                output_path=output_path,
                target_size=target_size,
                width_ratio=LANDSCAPE_SAFE_WIDTH_RATIO,
                height_ratio=LANDSCAPE_SAFE_HEIGHT_RATIO,
            )
    except UnidentifiedImageError:
        return cover_path


def ensure_youtube_cover(
    cover_path: Path,
    *,
    output_dir: Path | None = None,
    target_size: tuple[int, int] = LANDSCAPE_SIZE,
) -> Path:
    """生成适合 YouTube 的横版封面，不额外缩小前景。"""
    try:
        from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise ImportError("需要 Pillow 才能自动生成 YouTube 封面") from exc

    cover_path = Path(cover_path)
    try:
        with Image.open(cover_path) as src:
            image = ImageOps.exif_transpose(src).convert("RGB")
            if image.width >= image.height:
                return cover_path

            output_root = output_dir or cover_path.parent
            output_root.mkdir(parents=True, exist_ok=True)
            output_path = _derived_output_path(cover_path, output_root, "__youtube_landscape.jpg")

            return _build_safe_cover(
                image=image,
                output_path=output_path,
                target_size=target_size,
                width_ratio=YOUTUBE_LANDSCAPE_SAFE_WIDTH_RATIO,
                height_ratio=YOUTUBE_LANDSCAPE_SAFE_HEIGHT_RATIO,
            )
    except UnidentifiedImageError:
        return cover_path


def _build_safe_cover(
    *,
    image,
    output_path: Path,
    target_size: tuple[int, int],
    width_ratio: float,
    height_ratio: float,
    offset_y_ratio: float = 0.0,
) -> Path:
    """生成带模糊背景和安全边距的封面。"""
    from PIL import Image, ImageFilter, ImageOps

    background = ImageOps.fit(image, target_size, method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(radius=36))

    foreground = image.copy()
    safe_size = (
        max(1, int(target_size[0] * width_ratio)),
        max(1, int(target_size[1] * height_ratio)),
    )
    foreground.thumbnail(safe_size, Image.Resampling.LANCZOS)

    canvas = background.copy()
    centered_y = (target_size[1] - foreground.height) // 2
    offset_y = centered_y + int(target_size[1] * offset_y_ratio)
    max_offset_y = max(0, target_size[1] - foreground.height)
    offset_y = min(max(0, offset_y), max_offset_y)
    offset = (
        (target_size[0] - foreground.width) // 2,
        offset_y,
    )
    canvas.paste(foreground, offset)
    canvas.save(output_path, format="JPEG", quality=95)
    return output_path


def _derived_output_path(source_path: Path, output_root: Path, suffix: str) -> Path:
    """生成稳定的输出文件名，避免重复叠加中间后缀。"""
    stem = source_path.stem
    for extra_suffix in (
        "__portrait_safe",
        "__landscape",
        "__youtube_landscape",
        "__wechat_3x4",
        "__douyin_3x4",
        "__douyin_4x3",
    ):
        if stem.endswith(extra_suffix):
            stem = stem[: -len(extra_suffix)]
    return output_root / f"{stem}{suffix}"
