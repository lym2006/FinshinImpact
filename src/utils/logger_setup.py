import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger():
    logger=logging.getLogger("Bot")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter=logging.Formatter(
        fmt="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s\r",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    #控制台
    ch=logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    #文件
    log_path=Path("logs/bot.log")
    log_path.parent.mkdir(parents=True,exist_ok=True)
    fh=RotatingFileHandler(
        log_path, 
        maxBytes=10*1024*1024,# 10MB自动清理
        backupCount=2,#保留3个（2旧1新）
        encoding='utf-8'
    )
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    logger.propagate=True

    #噪音屏蔽（按需）
    noisy_libs=[
        "aiogram","aiohttp","httpx",
        "selenium","urllib3",
        "pydub","cv2",
        "asyncio","PIL","pillow"
    ]
    for lib in noisy_libs:
        lib_logger=logging.getLogger(lib)
        lib_logger.setLevel(logging.WARNING)
        lib_logger.propagate=False

    _enhance_logger()
    
    return logger

def _enhance_logger():#为日志器增强 error 方法
    original_error=logging.Logger.error
    def _enhanced_error(self,msg,*args,**kwargs):
        if 'exc_info' not in kwargs:
            if sys.exc_info()[0] is not None:
                kwargs['exc_info']=True
        return original_error(self,msg,*args,**kwargs)
    logging.Logger.error=_enhanced_error