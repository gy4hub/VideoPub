"""发布调度器：解析元数据 → 分发到各上传器 → 首评 → 状态更新"""

import asyncio
from pathlib import Path

from loguru import logger

from videopub.core.config_loader import load_settings
from videopub.core.metadata_parser import parse
from videopub.core.models import Platform, PlatformTask, UploadResult
from videopub.core.status import StatusState, read_status, write_status


async def process_folder(
    folder_path: Path,
    platforms: list[str] | None = None,
) -> list[UploadResult]:
    """处理一个发布文件夹：解析元数据 → 分发到各上传器 → 返回结果

    Args:
        folder_path: 包含视频、封面和元数据文件的文件夹
        platforms: 要发布的平台列表（如 ["bilibili", "youtube"]）；
                   None 表示发布元数据中所有平台
    """
    folder_path = Path(folder_path)
    logger.info(f"开始处理: {folder_path.name}")

    task = parse(folder_path)

    # 按平台过滤
    selected = {p.lower() for p in platforms} if platforms else None
    platform_metas = [
        pm for pm in task.platforms
        if selected is None or pm.platform.value in selected
    ]

    if not platform_metas:
        logger.warning("没有匹配的平台元数据")
        return []

    results: list[UploadResult] = []

    settings = load_settings()
    upload_timeout = float(settings.get("upload_timeout", 600))

    for platform_meta in platform_metas:
        platform = platform_meta.platform
        try:
            result = await _process_one_platform(
                folder_path, platform_meta, task, upload_timeout
            )
        except Exception as exc:
            logger.error(f"[{platform.value}] 未预期异常: {exc}")
            write_status(folder_path, platform, StatusState.ERROR, error=str(exc))
            result = UploadResult(platform=platform, success=False, error=str(exc))

        if result is not None:
            results.append(result)

    return results


async def _process_one_platform(
    folder_path: Path,
    platform_meta,
    task,
    upload_timeout: float,
) -> UploadResult | None:
    """处理单个平台，返回 UploadResult 或 None（跳过时）"""
    platform = platform_meta.platform

    # 已完成的平台跳过（幂等）
    current_state = read_status(folder_path, platform)
    if current_state == StatusState.DONE:
        logger.info(f"[{platform.value}] 已完成，跳过")
        return None

    write_status(folder_path, platform, StatusState.UPLOADING)
    logger.info(f"[{platform.value}] 开始上传...")

    uploader = _get_uploader(platform)
    if uploader is None:
        err = f"未找到平台 {platform.value} 的上传器"
        logger.error(err)
        write_status(folder_path, platform, StatusState.ERROR, error=err)
        return UploadResult(platform=platform, success=False, error=err)

    # 检查登录态
    if not await uploader.check_session():
        logger.warning(f"[{platform.value}] 登录态无效，尝试登录...")
        if not await uploader.login():
            err = "登录失败"
            logger.error(f"[{platform.value}] {err}")
            write_status(folder_path, platform, StatusState.ERROR, error=err)
            return UploadResult(platform=platform, success=False, error=err)

    # 上传（带超时保护）
    try:
        result = await asyncio.wait_for(
            uploader.upload(
                PlatformTask(
                    video_path=task.video_path,
                    cover_path=task.cover_path,
                    meta=platform_meta,
                )
            ),
            timeout=upload_timeout,
        )
    except asyncio.TimeoutError:
        err = f"上传超时（>{upload_timeout:.0f}s）"
        logger.error(f"[{platform.value}] {err}")
        write_status(folder_path, platform, StatusState.ERROR, error=err)
        return UploadResult(platform=platform, success=False, error=err)

    if result.success:
        # 发首评
        if platform_meta.first_comment and result.video_id:
            comment_ok = await uploader.post_comment(
                result.video_id, platform_meta.first_comment
            )
            if comment_ok:
                logger.success(f"[{platform.value}] 首评发布成功")
            else:
                logger.warning(f"[{platform.value}] 首评发布失败")

        write_status(
            folder_path,
            platform,
            StatusState.DONE,
            video_id=result.video_id,
            video_url=result.video_url,
        )
        logger.success(
            f"[{platform.value}] 上传成功"
            + (f": {result.video_url}" if result.video_url else "")
        )
    else:
        write_status(
            folder_path,
            platform,
            StatusState.ERROR,
            error=result.error or "未知错误",
        )
        logger.error(f"[{platform.value}] 上传失败: {result.error}")

    return result


def _get_uploader(platform: Platform):
    """按需初始化并返回对应平台的上传器"""
    if platform == Platform.YOUTUBE:
        from videopub.uploaders.youtube.uploader import YouTubeUploader
        return YouTubeUploader()
    if platform == Platform.BILIBILI:
        from videopub.uploaders.bilibili.uploader import BilibiliUploader
        return BilibiliUploader()
    if platform == Platform.DOUYIN:
        from videopub.uploaders.douyin.uploader import DouyinUploader
        return DouyinUploader()
    if platform == Platform.WECHAT:
        from videopub.uploaders.wechat.uploader import WeChatUploader
        return WeChatUploader()
    return None
