"""VideoPub MCP server.

Expose the existing VideoPub workflow as MCP tools over stdio.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from videopub import __version__
from videopub.core.config_loader import load_platform_config, load_settings
from videopub.core.metadata_parser import (
    _find_cover_file,
    _find_metadata_file,
    _find_video_file,
    _parse_platform,
    parse,
)
from videopub.core.models import Platform, PlatformMeta, PublishTask, UploadResult
from videopub.core.orchestrator import process_folder
from videopub.core.status import read_status_detail

mcp = FastMCP("VideoPub", json_response=True)


def _as_path(folder: str) -> Path:
    path = Path(folder).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"路径不存在: {path}")
    if not path.is_dir():
        raise ValueError(f"不是文件夹: {path}")
    return path


def _normalize_platforms(platforms: list[str] | None) -> list[str] | None:
    if not platforms:
        return None
    normalized: list[str] = []
    for platform in platforms:
        try:
            normalized.append(_parse_platform(platform).value)
        except ValueError as exc:
            raise ValueError(
                f"不支持的平台: {platform}，支持: wechat/视频号, douyin/抖音, bilibili/b站, youtube"
            ) from exc
    return normalized


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _serialize_platform_meta(meta: PlatformMeta) -> dict[str, Any]:
    return {
        "platform": meta.platform.value,
        "title": meta.title,
        "short_title": meta.short_title,
        "description": meta.description,
        "tags": list(meta.tags),
        "first_comment": meta.first_comment,
        "is_original": meta.is_original,
        "scheduled_time": _serialize_datetime(meta.scheduled_time),
        "category": meta.category,
        "collection": meta.collection,
        "extra": dict(meta.extra),
    }


def _serialize_publish_task(task: PublishTask) -> dict[str, Any]:
    return {
        "video_path": str(task.video_path),
        "cover_path": str(task.cover_path),
        "platforms": [_serialize_platform_meta(meta) for meta in task.platforms],
    }


def _serialize_upload_result(result: UploadResult) -> dict[str, Any]:
    return {
        "platform": result.platform.value,
        "success": result.success,
        "video_id": result.video_id,
        "video_url": result.video_url,
        "error": result.error,
        "screenshot_path": str(result.screenshot_path) if result.screenshot_path else None,
    }


def _has_publishable_assets(folder: Path) -> bool:
    try:
        task = parse(folder)
        return bool(task.platforms)
    except (FileNotFoundError, ValueError):
        return False


def _serialize_settings(data: dict[str, Any]) -> dict[str, Any]:
    return dict(data)


def parse_folder_impl(folder: str) -> dict[str, Any]:
    path = _as_path(folder)
    task = parse(path)
    return {
        "folder": str(path),
        "task": _serialize_publish_task(task),
    }


def validate_folder_impl(folder: str) -> dict[str, Any]:
    path = _as_path(folder)
    result: dict[str, Any] = {
        "folder": str(path),
        "ok": False,
        "metadata_file": None,
        "video_file": None,
        "cover_file": None,
        "platforms": [],
        "errors": [],
    }

    try:
        metadata_file = _find_metadata_file(path)
        result["metadata_file"] = str(metadata_file)
    except FileNotFoundError as exc:
        result["errors"].append(str(exc))
        return result

    try:
        task = parse(path)
        result["video_file"] = str(task.video_path)
        result["cover_file"] = str(task.cover_path)
        result["platforms"] = [meta.platform.value for meta in task.platforms]
        if not task.platforms:
            result["errors"].append("元数据已解析，但未找到任何平台段")
            return result
        result["ok"] = True
        return result
    except FileNotFoundError as exc:
        result["errors"].append(str(exc))
    except Exception as exc:
        result["errors"].append(str(exc))

    try:
        result["video_file"] = str(_find_video_file(path))
    except FileNotFoundError:
        pass
    try:
        result["cover_file"] = str(_find_cover_file(path))
    except FileNotFoundError:
        pass
    return result


async def upload_folder_impl(
    folder: str,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    path = _as_path(folder)
    normalized_platforms = _normalize_platforms(platforms)
    results = await process_folder(path, platforms=normalized_platforms)
    return {
        "folder": str(path),
        "platforms": normalized_platforms or [p.value for p in Platform],
        "results": [_serialize_upload_result(result) for result in results],
    }


async def login_platform_impl(platform: str) -> dict[str, Any]:
    from videopub.cli import _build_uploader

    normalized = _normalize_platforms([platform])[0]
    uploader = _build_uploader(Platform(normalized))
    success = await uploader.login()
    return {
        "platform": normalized,
        "success": success,
    }


async def login_status_impl() -> dict[str, Any]:
    from videopub.cli import _build_uploader

    statuses: dict[str, Any] = {}
    for platform in Platform:
        try:
            uploader = _build_uploader(platform)
            statuses[platform.value] = {
                "logged_in": bool(await uploader.check_session()),
                "error": None,
            }
        except Exception as exc:  # pragma: no cover - defensive, depends on env
            statuses[platform.value] = {
                "logged_in": False,
                "error": str(exc),
            }
    return statuses


def folder_status_impl(folder: str) -> dict[str, Any]:
    path = _as_path(folder)
    statuses = {
        platform.value: read_status_detail(path, platform)
        for platform in Platform
    }
    return {
        "folder": str(path),
        "statuses": statuses,
    }


def list_publishable_folders_impl(
    root: str,
    recursive: bool = False,
) -> dict[str, Any]:
    root_path = _as_path(root)
    pattern = "**/*" if recursive else "*"
    folders: list[dict[str, Any]] = []

    for candidate in sorted(root_path.glob(pattern)):
        if not candidate.is_dir() or candidate.name.startswith("."):
            continue
        if _has_publishable_assets(candidate):
            folders.append(
                {
                    "folder": str(candidate),
                    "metadata_file": str(_find_metadata_file(candidate)),
                    "video_file": str(_find_video_file(candidate)),
                }
            )

    return {
        "root": str(root_path),
        "recursive": recursive,
        "folders": folders,
    }


def settings_impl() -> dict[str, Any]:
    return _serialize_settings(load_settings())


def platform_config_impl(platform: str) -> dict[str, Any]:
    normalized = _normalize_platforms([platform])[0]
    return {
        "platform": normalized,
        "config": _serialize_settings(load_platform_config(normalized)),
    }


def _configure_server(
    *,
    transport: str,
    host: str,
    port: int,
    mount_path: str,
    streamable_http_path: str,
) -> None:
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.mount_path = mount_path
    mcp.settings.streamable_http_path = streamable_http_path
    mcp.run(transport=transport, mount_path=mount_path if transport == "sse" else None)


@mcp.tool()
def get_version() -> dict[str, str]:
    """Get the installed VideoPub version."""
    return {"version": __version__}


@mcp.tool()
def get_supported_platforms() -> list[str]:
    """List platforms supported by VideoPub."""
    return [platform.value for platform in Platform]


@mcp.tool()
def parse_folder(folder: str) -> dict[str, Any]:
    """Parse one publish folder and return the normalized task payload."""
    return parse_folder_impl(folder)


@mcp.tool()
def validate_folder(folder: str) -> dict[str, Any]:
    """Validate whether one folder is publishable and show resolved assets."""
    return validate_folder_impl(folder)


@mcp.tool()
def list_publishable_folders(root: str, recursive: bool = False) -> dict[str, Any]:
    """List child folders that contain both metadata and video files."""
    return list_publishable_folders_impl(root, recursive=recursive)


@mcp.tool()
async def upload_folder(
    folder: str,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Upload a publish folder to one or more platforms."""
    return await upload_folder_impl(folder, platforms=platforms)


@mcp.tool()
async def login_platform(platform: str) -> dict[str, Any]:
    """Login one platform and refresh its local session."""
    return await login_platform_impl(platform)


@mcp.tool()
async def get_login_status() -> dict[str, Any]:
    """Check login status for all supported platforms."""
    return await login_status_impl()


@mcp.tool()
def get_folder_status(folder: str) -> dict[str, Any]:
    """Read .status/<platform>.json details for one publish folder."""
    return folder_status_impl(folder)


@mcp.tool()
def get_settings() -> dict[str, Any]:
    """Read global VideoPub settings.yaml."""
    return settings_impl()


@mcp.tool()
def get_platform_config(platform: str) -> dict[str, Any]:
    """Read one platform config file."""
    return platform_config_impl(platform)


@mcp.resource("videopub://version")
def version_resource() -> str:
    """Return the installed VideoPub version."""
    return __version__


@mcp.resource("videopub://platforms")
def platforms_resource() -> str:
    """Return the supported platform list."""
    return ", ".join(platform.value for platform in Platform)


@mcp.resource("videopub://settings")
def settings_resource() -> dict[str, Any]:
    """Return global VideoPub settings."""
    return settings_impl()


def main() -> None:
    """Run the VideoPub MCP server."""
    parser = argparse.ArgumentParser(description="Run the VideoPub MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport，默认 stdio",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP transport host，默认 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP transport port，默认 8000",
    )
    parser.add_argument(
        "--mount-path",
        default="/",
        help="SSE transport mount path，默认 /",
    )
    parser.add_argument(
        "--streamable-http-path",
        default="/mcp",
        help="streamable-http path，默认 /mcp",
    )
    args = parser.parse_args()
    _configure_server(
        transport=args.transport,
        host=args.host,
        port=args.port,
        mount_path=args.mount_path,
        streamable_http_path=args.streamable_http_path,
    )


if __name__ == "__main__":
    main()
