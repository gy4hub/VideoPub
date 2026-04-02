"""VideoPub CLI 入口"""

from pathlib import Path

import click

from videopub import __version__


@click.group()
@click.version_option(version=__version__, prog_name="videopub")
def cli():
    """VideoPub - 多平台视频发布自动化工具"""


@cli.command()
@click.argument("folder", type=click.Path(exists=True))
@click.option(
    "--platform",
    "-p",
    multiple=True,
    type=click.Choice(["wechat", "douyin", "bilibili", "youtube"], case_sensitive=False),
    help="只上传到指定平台（可多选）",
)
def upload(folder, platform):
    """上传指定文件夹中的视频到各平台

    FOLDER: 包含视频、封面和元数据的文件夹路径
    """
    import asyncio

    from videopub.core.metadata_parser import parse

    try:
        task = parse(Path(folder))
    except (FileNotFoundError, ValueError) as exc:
        click.echo(f"错误: {exc}", err=True)
        raise SystemExit(1) from exc

    selected = {item.lower() for item in platform} if platform else None
    filtered_platforms = [
        platform_meta
        for platform_meta in task.platforms
        if selected is None or platform_meta.platform.value in selected
    ]

    if not filtered_platforms:
        click.echo("没有匹配的平台元数据", err=True)
        raise SystemExit(1)

    click.echo(f"视频: {task.video_path.name}")
    click.echo(f"封面: {task.cover_path.name}")
    click.echo(f"平台: {', '.join(platform_meta.platform.value for platform_meta in filtered_platforms)}")

    asyncio.run(_do_upload(task, filtered_platforms))


async def _do_upload(task, platforms):
    """执行上传"""
    from videopub.core.models import Platform, PlatformTask

    # 按需初始化上传器（延迟导入避免依赖缺失时的 import 错误）
    uploaders = {}

    for platform_meta in platforms:
        if platform_meta.platform == Platform.YOUTUBE:
            from videopub.uploaders.youtube.uploader import YouTubeUploader

            uploaders[platform_meta.platform] = YouTubeUploader()
        elif platform_meta.platform == Platform.BILIBILI:
            from videopub.uploaders.bilibili.uploader import BilibiliUploader

            uploaders[platform_meta.platform] = BilibiliUploader()
        else:
            click.echo(f"  {platform_meta.platform.value}: 跳过（Sprint 2 中实现）")
            continue

    for platform_meta in platforms:
        uploader = uploaders.get(platform_meta.platform)
        if uploader is None:
            continue

        click.echo(f"\n--- {platform_meta.platform.value} ---")

        # 检查登录态
        if not await uploader.check_session():
            click.echo("  登录态无效，尝试登录...")
            if not await uploader.login():
                click.echo("  登录失败，跳过此平台")
                continue

        click.echo("  正在上传...")
        result = await uploader.upload(
            PlatformTask(
                video_path=task.video_path,
                cover_path=task.cover_path,
                meta=platform_meta,
            )
        )

        if result.success:
            click.echo(f"  上传成功! ID: {result.video_id}")
            if result.video_url:
                click.echo(f"  URL: {result.video_url}")
            if platform_meta.first_comment and result.video_id:
                comment_ok = await uploader.post_comment(result.video_id, platform_meta.first_comment)
                click.echo(f"  首评: {'成功' if comment_ok else '失败'}")
        else:
            click.echo(f"  上传失败: {result.error}")


@cli.command()
@click.argument("folder", type=click.Path(exists=True), default=".")
def watch(folder):
    """启动文件夹监控，自动发布新增视频

    FOLDER: 要监控的文件夹路径（默认当前目录）
    """
    click.echo(f"监控文件夹: {folder}")
    click.echo("（监控功能将在 Sprint 3 中实现）")


@cli.command()
@click.argument(
    "platform",
    type=click.Choice(["wechat", "douyin", "bilibili", "youtube"], case_sensitive=False),
)
def login(platform):
    """登录指定平台（生成/刷新 Cookie）

    PLATFORM: 平台名称
    """
    click.echo(f"登录平台: {platform}")
    click.echo("（登录功能将在 Sprint 1-2 中实现）")


@cli.command()
def status():
    """检查各平台的登录状态"""
    click.echo("各平台登录状态：")
    for platform in ["wechat", "douyin", "bilibili", "youtube"]:
        click.echo(f"  {platform}: 未配置")
    click.echo("（状态检查将在 Sprint 1-2 中实现）")
