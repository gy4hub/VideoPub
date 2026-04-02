"""元数据解析（JSON → PublishTask，Word/PDF 在 Sprint 3 中实现）"""

import json
from pathlib import Path

from videopub.core.models import Platform, PlatformMeta, PublishTask


# 平台名称映射（中文/英文 → Platform enum）
PLATFORM_ALIASES: dict[str, Platform] = {
    "wechat": Platform.WECHAT,
    "视频号": Platform.WECHAT,
    "douyin": Platform.DOUYIN,
    "抖音": Platform.DOUYIN,
    "bilibili": Platform.BILIBILI,
    "youtube": Platform.YOUTUBE,
}


def _find_metadata_file(folder_path: Path) -> Path:
    """在文件夹中查找元数据文件，优先级: .json > .docx > .pdf"""
    for ext in (".json", ".docx", ".pdf"):
        candidates = sorted(folder_path.glob(f"metadata{ext}"))
        if candidates:
            return candidates[0]

    # 也支持任意名字的 json 文件
    json_files = sorted(folder_path.glob("*.json"))
    if json_files:
        return json_files[0]

    raise FileNotFoundError(f"在 {folder_path} 中未找到元数据文件 (metadata.json/.docx/.pdf)")


def _find_video_file(folder_path: Path) -> Path:
    """在文件夹中查找视频文件"""
    for ext in (".mp4", ".mov", ".avi", ".mkv"):
        candidates = sorted(folder_path.glob(f"*{ext}"))
        if candidates:
            return candidates[0]

    raise FileNotFoundError(f"在 {folder_path} 中未找到视频文件")


def _find_cover_file(folder_path: Path) -> Path:
    """在文件夹中查找封面图"""
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidates = sorted(folder_path.glob(f"*{ext}"))
        if candidates:
            return candidates[0]

    raise FileNotFoundError(f"在 {folder_path} 中未找到封面图")


def _parse_platform(platform_value: str) -> Platform:
    """将平台字符串解析为 Platform enum"""
    normalized = platform_value.strip().lower()
    alias_platform = PLATFORM_ALIASES.get(normalized)
    if alias_platform is not None:
        return alias_platform
    return Platform(normalized)


def _resolve_asset_path(
    folder_path: Path,
    raw_path: str | None,
    fallback_finder,
) -> Path:
    """解析资源文件路径，不存在时回退到自动查找"""
    if raw_path:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = folder_path / candidate
        if candidate.exists():
            return candidate

    return fallback_finder(folder_path)


def _parse_json(file_path: Path, folder_path: Path) -> PublishTask:
    """解析 JSON 格式的元数据文件"""
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    # 视频和封面路径：支持绝对路径和相对路径
    video_path = _resolve_asset_path(folder_path, data.get("video_path"), _find_video_file)
    cover_path = _resolve_asset_path(folder_path, data.get("cover_path"), _find_cover_file)

    # 解析各平台元数据
    platforms: list[PlatformMeta] = []
    for platform_data in data.get("platforms", []):
        platform_meta = PlatformMeta(
            platform=_parse_platform(platform_data["platform"]),
            title=platform_data["title"],
            short_title=platform_data.get("short_title"),
            description=platform_data["description"],
            tags=platform_data.get("tags", []),
            first_comment=platform_data.get("first_comment"),
            is_original=platform_data.get("is_original", True),
            scheduled_time=platform_data.get("scheduled_time"),
            category=platform_data.get("category"),
            extra=platform_data.get("extra", {}),
        )
        platforms.append(platform_meta)

    return PublishTask(
        video_path=video_path,
        cover_path=cover_path,
        platforms=platforms,
    )


def parse(folder_path: Path) -> PublishTask:
    """解析文件夹中的元数据文件，返回 PublishTask

    当前支持: JSON
    Sprint 3 将增加: Word (.docx), PDF
    """
    folder_path = Path(folder_path)
    if not folder_path.is_dir():
        raise ValueError(f"路径不是文件夹: {folder_path}")

    meta_file = _find_metadata_file(folder_path)

    if meta_file.suffix == ".json":
        return _parse_json(meta_file, folder_path)
    if meta_file.suffix == ".docx":
        raise NotImplementedError("Word 格式解析将在 Sprint 3 中实现")
    if meta_file.suffix == ".pdf":
        raise NotImplementedError("PDF 格式解析将在 Sprint 3 中实现")
    raise ValueError(f"不支持的元数据格式: {meta_file.suffix}")
