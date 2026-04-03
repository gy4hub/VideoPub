"""VideoPub CLI 入口"""

import asyncio
import importlib
from pathlib import Path

import click

from videopub import __version__


# ── 主命令组 ─────────────────────────────────────────────────────────────────

@click.group()
@click.version_option(version=__version__, prog_name="videopub")
@click.option("--verbose", "-v", is_flag=True, default=False, help="显示 DEBUG 日志")
@click.pass_context
def cli(ctx, verbose):
    """VideoPub - 多平台视频发布自动化工具"""
    from videopub.logging_config import setup_logging

    setup_logging(verbose=verbose)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


# ── upload 命令 ───────────────────────────────────────────────────────────────

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
    from videopub.core.orchestrator import process_folder

    selected = list(platform) if platform else None
    results = asyncio.run(process_folder(Path(folder), platforms=selected))

    if not results:
        click.echo("没有需要上传的平台（可能已全部完成）")
        return

    click.echo("\n── 上传结果 ──")
    for r in results:
        icon = "✅" if r.success else "❌"
        line = f"  {icon} {r.platform.value}"
        if r.success and r.video_url:
            line += f"  {r.video_url}"
        elif not r.success and r.error:
            line += f"  {r.error}"
        click.echo(line)


# ── watch 命令 ────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("folder", type=click.Path(exists=True), default=".")
@click.option(
    "--platform",
    "-p",
    multiple=True,
    type=click.Choice(["wechat", "douyin", "bilibili", "youtube"], case_sensitive=False),
    help="只监控指定平台（可多选）",
)
def watch(folder, platform):
    """监控文件夹，自动发布新增的视频

    FOLDER: 要监控的根目录（默认当前目录）。
    当检测到子目录中出现元数据文件时，自动触发上传。
    """
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        click.echo("需要安装 watchdog: pip install watchdog", err=True)
        raise SystemExit(1)

    from loguru import logger

    selected = list(platform) if platform else None
    watch_path = Path(folder).expanduser().resolve()
    logger.info(f"监控中: {watch_path}")
    if selected:
        logger.info(f"平台过滤: {', '.join(selected)}")

    click.echo(f"👀 监控中: {watch_path}  (Ctrl+C 停止)")

    # 已处理过的文件夹（避免重复触发）
    processed: set[Path] = set()

    def _trigger(event_path: str):
        p = Path(event_path)
        try:
            rel = p.relative_to(watch_path)
        except ValueError:
            return
        parts = rel.parts
        if len(parts) < 1:
            return
        sub_dir = watch_path / parts[0]
        if not sub_dir.is_dir() or sub_dir in processed:
            return

        has_meta = any(
            list(sub_dir.glob(f"metadata{ext}")) for ext in (".json", ".docx", ".pdf")
        ) or bool(list(sub_dir.glob("*.json")))
        has_video = any(
            list(sub_dir.glob(f"*{ext}")) for ext in (".mp4", ".mov", ".avi", ".mkv")
        )

        if has_meta and has_video:
            processed.add(sub_dir)
            logger.info(f"检测到新文件夹: {sub_dir.name}")
            click.echo(f"📂 触发上传: {sub_dir.name}")
            asyncio.run(_watch_upload(sub_dir, selected))

    class Handler(FileSystemEventHandler):
        def on_created(self, event):
            _trigger(event.src_path)

        def on_modified(self, event):
            _trigger(event.src_path)

    observer = Observer()
    observer.schedule(Handler(), str(watch_path), recursive=True)
    observer.start()
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        click.echo("\n监控已停止")
    observer.join()


async def _watch_upload(folder: Path, platforms: list[str] | None):
    """监控模式下触发上传"""
    from videopub.core.orchestrator import process_folder

    results = await process_folder(folder, platforms=platforms)
    for r in results:
        icon = "✅" if r.success else "❌"
        click.echo(
            f"  {icon} {r.platform.value}"
            + (f"  {r.video_url}" if r.success and r.video_url else "")
            + (f"  {r.error}" if not r.success and r.error else "")
        )


# ── login 命令 ────────────────────────────────────────────────────────────────

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
    asyncio.run(_do_login(platform))


async def _do_login(platform_name: str):
    from videopub.core.models import Platform

    platform_map = {
        "youtube": Platform.YOUTUBE,
        "bilibili": Platform.BILIBILI,
        "douyin": Platform.DOUYIN,
        "wechat": Platform.WECHAT,
    }
    uploader = _build_uploader(platform_map[platform_name.lower()])
    success = await uploader.login()
    if success:
        click.echo(f"  {platform_name} 登录成功!")
    else:
        click.echo(f"  {platform_name} 登录失败")


# ── status 命令 ───────────────────────────────────────────────────────────────

@cli.command()
def status():
    """检查各平台的登录状态"""
    click.echo("各平台登录状态：")
    asyncio.run(_check_status())


async def _check_status():
    from videopub.core.models import Platform

    for platform in Platform:
        try:
            uploader = _build_uploader(platform)
            valid = await uploader.check_session()
            status_text = "✅ 已登录" if valid else "❌ 未登录/已过期"
        except Exception:
            status_text = "⚠️  检查失败"
        click.echo(f"  {platform.value}: {status_text}")


# ── 共用工具 ──────────────────────────────────────────────────────────────────

def _build_uploader(platform):
    from videopub.core.models import Platform

    mod_map = {
        Platform.YOUTUBE: ("videopub.uploaders.youtube.uploader", "YouTubeUploader"),
        Platform.BILIBILI: ("videopub.uploaders.bilibili.uploader", "BilibiliUploader"),
        Platform.DOUYIN: ("videopub.uploaders.douyin.uploader", "DouyinUploader"),
        Platform.WECHAT: ("videopub.uploaders.wechat.uploader", "WeChatUploader"),
    }
    module_path, class_name = mod_map[platform]
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()
