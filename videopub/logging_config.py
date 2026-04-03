"""日志初始化（loguru：控制台 + 按日轮转文件）"""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(verbose: bool = False, log_dir: Path | str | None = None) -> None:
    """配置 loguru 日志。

    Args:
        verbose: True 时控制台显示 DEBUG 级别；False 时显示 INFO 及以上
        log_dir: 日志文件目录；None 时从 settings.yaml 读取（默认 ~/videopub/logs）
    """
    # 移除默认 handler
    logger.remove()

    # ── 控制台 handler ────────────────────────────────────────────────────────
    console_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=console_level,
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "{message}"
        ),
    )

    # ── 文件 handler（按日轮转，保留 30 天）──────────────────────────────────
    if log_dir is None:
        try:
            from videopub.core.config_loader import load_settings

            settings = load_settings()
            log_dir = Path(settings.get("log_dir", "~/videopub/logs")).expanduser()
        except Exception:
            log_dir = Path("~/videopub/logs").expanduser()

    log_dir = Path(log_dir).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "videopub_{time:YYYY-MM-DD}.log",
        rotation="00:00",          # 每天零点轮转
        retention="30 days",       # 保留 30 天
        encoding="utf-8",
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        enqueue=True,              # 线程安全
    )
