from .plugins_register import register_routers
from .logger_setup import setup_logger
from .config_loader import CONFIG
from .middleware import LoggingMiddleware,AuthMiddleware

from aiogram.client.session.aiohttp import AiohttpSession
class SafeSession(AiohttpSession):
    def __init__(self,proxy:str|None=None,**kwargs):
        super().__init__(proxy=proxy,**kwargs)
        self._connector_init["ssl"]=False

__all__=[
    "register_routers","setup_logger","CONFIG",
    "LoggingMiddleware","AuthMiddleware","SafeSession"
]