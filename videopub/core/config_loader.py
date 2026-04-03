"""配置文件加载"""

import functools
from pathlib import Path

import yaml


# 配置文件搜索路径
_CONFIG_DIR = Path(__file__).parent.parent / "config"


@functools.lru_cache(maxsize=None)
def load_settings() -> dict:
    """加载全局配置 settings.yaml（带缓存）"""
    settings_file = _CONFIG_DIR / "settings.yaml"
    if not settings_file.exists():
        return {}

    with settings_file.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


@functools.lru_cache(maxsize=None)
def load_platform_config(platform: str) -> dict:
    """加载指定平台的配置文件（带缓存）"""
    config_file = _CONFIG_DIR / "platforms" / f"{platform}.yaml"
    if not config_file.exists():
        return {}

    with config_file.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}
