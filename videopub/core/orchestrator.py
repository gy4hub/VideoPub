"""发布调度器"""

from pathlib import Path

from videopub.core.models import UploadResult


async def process_folder(folder_path: Path) -> list[UploadResult]:
    """处理一个发布文件夹：解析元数据 → 分发到各上传器 → 返回结果"""
    raise NotImplementedError("orchestrator.process_folder() 将在 Sprint 3 中实现")
