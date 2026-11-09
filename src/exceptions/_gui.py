# src/exceptions/_gui.py
"""GUI 异常族

- 定义界面操作相关异常
"""

from pathlib import Path

from ._base import BotError


class GUIError(BotError):
    """GUI 异常基类"""


class DashboardWriteError(GUIError):
    """仪表盘写入异常"""


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
    FontError: "字体文件出问题：{path}",
    FontMissingError: "找不到字体文件：{path}",
    FontLoadError: "字体文件读不出来：{path}",
    FontFamilyError: "字体文件里没有可用的家族名：{path}",
    FontRegisterError: "字体注册失败：{path}",
    DashboardWriteError: "仪表盘写入失败",
}
