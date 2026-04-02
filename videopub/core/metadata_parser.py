"""元数据解析（Word/PDF/JSON → PublishTask）"""

from pathlib import Path

from videopub.core.models import PublishTask


def parse(folder_path: Path) -> PublishTask:
    """解析文件夹中的元数据文件，返回 PublishTask"""
    raise NotImplementedError("metadata_parser.parse() 将在 Sprint 1 中实现")
