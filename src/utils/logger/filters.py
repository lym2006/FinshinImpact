# src/utils/logger/handler.py
"""
第三方库日志噪音屏蔽模块

提供：
- 批量将指定第三方库的日志级别设为 CRITICAL 并切断冒泡
"""

import logging

# 需要屏蔽噪音的第三方库列表
NOISY_LIBS = (
    "aiogram",
    "aiohttp",
    "httpx",
    "selenium",
    "urllib3",
    "pydub",
    "cv2",
    "asyncio",
    "PIL",
)


def suppress_third_party_logs(lib_names: tuple[str, ...] | None = None) -> None:
    """屏蔽指定第三方库的日志输出（非 CRITICAL 级别全部静默 + 切断冒泡）"""
    targets = lib_names if lib_names is not None else NOISY_LIBS
    for name in targets:
        lib_logger = logging.getLogger(name)
        lib_logger.setLevel(logging.CRITICAL)
        lib_logger.propagate = False
