# src/exceptions/_gui.py
"""GUI 异常族（内部实现）

- 定义界面操作相关异常
"""

from pathlib import Path

from ._base import BotError


class GUIError(BotError):
    """GUI 异常基类"""


class DashboardWriteError(GUIError):
    """仪表盘写入异常"""


# ==================== 字体异常 ====================


class FontError(GUIError):
    """字体异常基类"""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__()


class FontMissingError(FontError):
    """字体文件缺失异常"""


class FontLoadError(FontError):
    """字体文件加载异常"""


class FontRegisterError(FontError):
    """字体文件注册异常"""


class FontFamilyError(FontError):
    """字体家族名获取异常"""


GUI_MAP = {
    DashboardWriteError: "GUI 写入日志错误",
    "Font": {
        FontMissingError: "字体缺失：{path}",
        FontLoadError: "字体加载异常：{path}",
        FontRegisterError: "字体注册异常：{path}",
        FontFamilyError: "字体家族名获取异常：{path}",
    },
}
