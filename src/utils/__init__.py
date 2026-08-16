from aiogram.client.session.aiohttp import AiohttpSession

from .config_loader import CONFIG
from .logger_setup import setup_logger
from .middleware import AuthMiddleware, LoggingMiddleware
from .plugins_register import register_routers
from .root_dir import ROOT_DIR


class SafeSession(AiohttpSession):
    def __init__(self, proxy: str | None = None, **kwargs):
        super().__init__(proxy=proxy, **kwargs)
        self._connector_init["ssl"] = False


__all__ = [
    "ROOT_DIR",
    "CONFIG",
    "AuthMiddleware",
    "LoggingMiddleware",
    "SafeSession",
    "register_routers",
    "setup_logger",
]
