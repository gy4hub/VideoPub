"""VideoPub CLI 入口"""

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
    platforms = platform if platform else ("wechat", "douyin", "bilibili", "youtube")
    click.echo(f"上传文件夹: {folder}")
    click.echo(f"目标平台: {', '.join(platforms)}")
    click.echo("（上传功能将在 Sprint 1-2 中实现）")


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
