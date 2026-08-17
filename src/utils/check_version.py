import logging
import tomllib
from urllib import request

from .root_dir import ROOT_DIR

logger = logging.getLogger("Bot.Version")


def check_updates(proxy: str) -> bool:
    _local_version = _get_local_version()
    _remote_version = _get_remote_version(proxy)
    if not _local_version or not _remote_version:
        logger.warning("🚨 版本获取失败，无法完成检查，继续启动机器人")
        return True
    if _local_version == _remote_version:
        logger.info(f"✅ 当前已是最新版本: {_local_version}")
        return True
    else:
        logger.warning("发现新版本")
        logger.warning(f"当前版本: {_local_version}")
        logger.warning(f"最新版本: {_remote_version}")
        logger.warning("请运行 update.bat 更新后重启机器人！")
        return False


def _get_local_version() -> str | None:
    try:
        _pyproject_path = ROOT_DIR / "pyproject.toml"
        if not _pyproject_path.exists():
            return None
        with open(_pyproject_path, "rb") as f:
            _content = tomllib.load(f)
        _local_version = _content["project"]["version"]
        return _local_version if _local_version else None
    except Exception as e:
        logger.error(f"❌ 读取本地版本失败: {e}")


def _get_remote_version(proxy: str) -> str | None:
    _url = "https://lym2006.github.io/TelegramBot/pyproject.toml"
    try:
        _proxy_handler = request.ProxyHandler({"http": proxy, "https": proxy})
        _opener = request.build_opener(_proxy_handler)
        _req = request.Request(_url, headers={"User-Agent": "Python-Script"})
        with _opener.open(_req, timeout=30) as r:
            _content = tomllib.load(r)
        _remote_version = _content["project"]["version"]
        return _remote_version if _remote_version else None
    except Exception as e:
        logger.error(f"❌ 读取最新版本失败: {e}")
