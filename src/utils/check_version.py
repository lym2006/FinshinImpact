# src/utils/check_version.py
"""
版本检查工具

提供：
- 读取本地与远程版本号
- 启动前自动校验版本一致性
"""

import logging
import tomllib

from .base_client import BaseClient
from .root_dir import ROOT_DIR

logger = logging.getLogger("Bot.Version")

BASE_URL = "https://lym2006.github.io"
REQUEST_PATH = "/TelegramBot/pyproject.toml"
HEADER = {"User-Agent": "Python-Script"}


# ==================== 1. 内部辅助函数 ====================
def _get_local_version() -> str | None:
    """读取本地 pyproject.toml 中的版本号"""
    try:
        pyproject_path = ROOT_DIR / "pyproject.toml"
        if not pyproject_path.exists():
            return None
        with open(pyproject_path, "rb") as f:
            content = tomllib.load(f)
        local_version = content["project"]["version"]
        return local_version if local_version else None
    except Exception as e:
        logger.error(f"❌ 读取本地版本失败: {e}")


async def _get_remote_version() -> str | None:
    """通过 BaseClient 读取远程版本号"""
    try:
        text = await BaseClient.get_text(
            base_url=BASE_URL, request_path=REQUEST_PATH, headers=HEADER
        )
        data = tomllib.loads(text)
        return data.get("project", {}).get("version", None)
    except Exception as e:
        logger.error(f"❌ 读取远程版本失败: {e}")
        return


# ==================== 2. 核心版本检查逻辑 ====================
async def check_updates() -> bool:
    """
    检查是否为最新版本

    Returns:
        True 表示版本一致或检查失败（放行启动），False 表示发现新版本（阻止启动）
    """
    local_version = _get_local_version()
    remote_version = await _get_remote_version()
    if local_version is None or remote_version is None:
        logger.warning("🚨 版本获取失败，无法完成检查，继续启动机器人")
        return True
    if local_version == remote_version:
        logger.info(f"✅ 当前已是最新版本: {local_version}")
        return True
    else:
        logger.warning("发现新版本")
        logger.warning(f"当前版本: {local_version}")
        logger.warning(f"最新版本: {remote_version}")
        logger.warning("请运行 update.bat 更新后重启机器人！")
        return False
