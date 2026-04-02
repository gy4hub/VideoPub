"""配置读取工具。"""

from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent
PLATFORMS_DIR = CONFIG_DIR / "platforms"


def load_settings() -> dict[str, Any]:
    """读取全局配置模板。"""
    with (CONFIG_DIR / "settings.yaml").open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_platform_settings(platform: str) -> dict[str, Any]:
    """读取平台配置模板。"""
    with (PLATFORMS_DIR / f"{platform}.yaml").open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}
