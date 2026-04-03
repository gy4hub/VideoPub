"""重试装饰器（从 settings.yaml 读取配置）"""

import asyncio
import functools

from loguru import logger

from videopub.core.config_loader import load_settings


def retry_on_failure(func):
    """异步重试装饰器。

    从 settings.yaml 的 retry 节读取：
      max_attempts: 最大尝试次数（含第一次），默认 3
      delay_seconds: 首次等待秒数，默认 30
      backoff_factor: 指数退避倍率，默认 2.0
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        cfg = load_settings().get("retry", {})
        max_attempts = int(cfg.get("max_attempts", 3))
        delay = float(cfg.get("delay_seconds", 30.0))
        backoff = float(cfg.get("backoff_factor", 2.0))

        last_exc: BaseException | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < max_attempts:
                    wait = delay * (backoff ** (attempt - 1))
                    logger.warning(
                        f"[retry] {func.__name__} 第 {attempt}/{max_attempts} 次失败: "
                        f"{exc}，{wait:.1f}s 后重试"
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        f"[retry] {func.__name__} 已达最大重试次数 {max_attempts}，放弃: {exc}"
                    )

        raise last_exc  # type: ignore[misc]

    return wrapper
