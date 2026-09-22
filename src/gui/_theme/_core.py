# src/gui/_theme/_core.py
"""全局视觉令牌（内部实现）

- 定义窗口、字体、配色与通用控件令牌
"""

from dataclasses import dataclass
from pathlib import Path

from utils import ROOT_DIR

# ==================== 窗口配置 ====================


@dataclass(frozen=True)
class WindowConfig:
    """窗口基础属性配置"""

    title: str = "Bot Manager"  # 窗口标题
    width: int = 1200  # 窗口默认宽度
    height: int = 600  # 窗口默认高度
    min_width: int = 520  # 窗口最小宽度
    min_height: int = 400  # 窗口最小高度


# ==================== 全局/Reset ====================


@dataclass(frozen=True)
class GlobalConfig:
    """全局基础配置

    仅存放整个 App 共享的视觉基因
    """

    radius: int = 4  # 全局默认圆角


# ==================== 字体配置 ====================


@dataclass(frozen=True)
class FontConfig:
    """字体配置"""

    font_path: Path = ROOT_DIR / "assets/font.ttf"  # 主字体路径
    emoji_path: Path = ROOT_DIR / "assets/seguiemj.ttf"  # emoji 字体路径
    font_size: int = 11  # 全局字体大小


# ==================== Body（主窗口/中央容器） ====================


@dataclass(frozen=True)
class BodyConfig:
    """主窗口与中央容器配置"""

    bg: str = "#1E1E1E"  # 背景色
    color: str = "#D4D4D4"  # 文字色
    hover_bg: str = "#3A3A3A"  # 悬停背景色
    hover_color: str = "#FFFFFF"  # 悬停文字色
    selection_bg: str = "#264F78"  # 选中背景色
    selection_color: str = "#FFFFFF"  # 选中文字色
    padding: int = 8  # 仪表盘内边距


# ==================== Toolbar（顶部工具栏） ====================


@dataclass(frozen=True)
class ToolbarConfig:
    """工具栏配置"""

    bg: str = "#2D2D2D"  # 背景色
    height: int = 50  # 高度
    border_width: int = 1  # 底部分割线宽度
    border_color: str = "#444444"  # 底部分割线颜色


# ==================== Button（按钮） ====================


@dataclass(frozen=True)
class ButtonConfig:
    """按钮配置"""

    bg: str = "#3C3C3C"  # 默认背景色
    hover_bg: str = "#505050"  # 悬停背景色
    pressed_bg: str = "#2A2A2A"  # 按下背景色
    min_width: int = 100  # 最小宽度
    height: int = 32  # 高度
    padding_v: int = 6  # 垂直内边距
    padding_h: int = 16  # 水平内边距


# ==================== Button Danger（危险按钮） ====================


@dataclass(frozen=True)
class ButtonDangerConfig:
    """危险操作按钮配置"""

    bg: str = "#D32F2F"  # 背景色
    hover_bg: str = "#B71C1C"  # 悬停色
    pressed_bg: str = "#9A0007"  # 按下色


# ==================== Scrollbar（滚动条） ====================


@dataclass(frozen=True)
class ScrollbarConfig:
    """滚动条配置"""

    bg: str = "#1E1E1E"  # 轨道背景色
    handle_bg: str = "#555555"  # 滑块背景色
    handle_hover_bg: str = "#777777"  # 滑块悬停色
    width: int = 10  # 宽度
    min_handle_height: int = 20  # 滑块最小高度
    margin: int = 0  # 外边距（清除默认间隙）
    arrow_height: int = 0  # 箭头高度（隐藏默认箭头）
