"""发布状态文件管理（.status/<platform>.json）"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path

from videopub.core.models import Platform


class StatusState(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    DONE = "done"
    ERROR = "error"


def _status_file(folder_path: Path, platform: Platform) -> Path:
    """返回 .status/<platform>.json 路径，自动建目录"""
    status_dir = folder_path / ".status"
    status_dir.mkdir(exist_ok=True)
    return status_dir / f"{platform.value}.json"


def _status_file_readonly(folder_path: Path, platform: Platform) -> Path:
    """返回 .status/<platform>.json 路径，不创建目录。"""
    return folder_path / ".status" / f"{platform.value}.json"


def write_status(
    folder_path: Path,
    platform: Platform,
    state: StatusState,
    *,
    video_id: str | None = None,
    video_url: str | None = None,
    error: str | None = None,
) -> None:
    """写入（或更新）.status/<platform>.json"""
    data: dict = {
        "platform": platform.value,
        "state": state.value,
        "updated_at": datetime.now().isoformat(),
    }
    if video_id is not None:
        data["video_id"] = video_id
    if video_url is not None:
        data["video_url"] = video_url
    if error is not None:
        data["error"] = error

    _status_file(folder_path, platform).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_status(folder_path: Path, platform: Platform) -> StatusState | None:
    """读取平台状态，文件不存在时返回 None"""
    sf = _status_file_readonly(folder_path, platform)
    if not sf.exists():
        return None
    try:
        data = json.loads(sf.read_text(encoding="utf-8"))
        return StatusState(data["state"])
    except Exception:
        return None


def read_status_detail(folder_path: Path, platform: Platform) -> dict | None:
    """读取平台状态的完整 JSON dict，文件不存在时返回 None"""
    sf = _status_file_readonly(folder_path, platform)
    if not sf.exists():
        return None
    try:
        return json.loads(sf.read_text(encoding="utf-8"))
    except Exception:
        return None
