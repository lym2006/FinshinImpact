# src/widgets/font.py
"""输出字体加载

- 注册并加载项目自带字体，返回可用 QFont 供输出内容显式使用
- 加载失败按 silent 决定回落系统等宽字体还是抛异常
"""

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

from exceptions import (
    FontError,
    FontFamilyError,
    FontLoadError,
    FontMissingError,
    FontRegisterError,
)

# 成功族名按路径缓存，全进程只注册一次
_FAMILY_CACHE: dict[str, str] = {}


def _fallback_font(size: int) -> QFont:
    """系统等宽兜底字体"""
    font = QFont("Consolas", size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


def _family_of(path: Path) -> str:
    """注册字体文件并返回族名

    - 命中缓存直接返回
    """
    key = str(path)
    if key in _FAMILY_CACHE:
        return _FAMILY_CACHE[key]

    if not path.is_file():
        raise FontMissingError(path)
    try:
        font_id = QFontDatabase.addApplicationFont(key)
        if font_id == -1:
            # Qt 无法加载字体文件
            raise FontLoadError(path)
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            # 字体文件无法获取家族
            raise FontFamilyError(path)
    except FontError:
        raise
    except Exception as e:
        # 注册字体失败
        raise FontRegisterError(path) from e

    _FAMILY_CACHE[key] = families[0]
    return families[0]


def load_font(path: Path, size: int, *, silent: bool = False) -> QFont:
    """注册字体文件并返回可用 QFont

    - silent 为真时加载失败回落系统等宽字体，不抛异常
    - silent 为假时抛字体异常族，由调用方处理
    """
    try:
        return QFont(_family_of(path), size)
    except FontError:
        if not silent:
            raise
        return _fallback_font(size)
