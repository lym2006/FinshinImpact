# src/utils/logger/_enhancer.py
"""双轨日志器

- 面向用户与开发者双轨输出
- 调用链由调用处点名要，默认只落单行
"""

import logging


class BotLogger(logging.Logger):
    """Bot 专属的增强型日志器"""

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)

    def send_error(self, msg: str, e: BaseException) -> None:
        """写入报错日志

        - 分层 GUI 和文件
        - 异常本体与调用链走调试日志，本体自带的那段链在 except 之外也取得到
        """
        self.error(msg)
        self.debug(e, exc_info=e)
