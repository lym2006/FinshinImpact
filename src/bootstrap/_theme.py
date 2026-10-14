# src/bootstrap/_theme.py
"""引导期视觉令牌

- 选窗、表单窗、插件面板、进度窗共用一套尺寸与间距
- 颜色取自公共调色板，本层只定义尺寸
"""

from dataclasses import dataclass

from theme import PALETTE

SURFACE = PALETTE


@dataclass(frozen=True)
class _PickerConfig:
    """实例选窗尺寸"""

    width: int = 840  # 默认宽度，容下六个按钮一行不挤
    height: int = 400  # 默认高度
    min_width: int = 760  # 最小宽度，按钮行不挤扁的下限
    min_height: int = 320  # 最小高度


@dataclass(frozen=True)
class _FormConfig:
    """实例表单窗尺寸"""

    width: int = 460  # 默认宽度
    height: int = 320  # 默认高度
    min_width: int = 380  # 最小宽度
    min_height: int = 260  # 最小高度


@dataclass(frozen=True)
class _PanelConfig:
    """插件面板尺寸"""

    width: int = 620  # 默认宽度
    height: int = 440  # 默认高度
    min_width: int = 560  # 最小宽度
    min_height: int = 340  # 最小高度
    row_pad_v: int = 6  # 插件行垂直内边距
    row_pad_h: int = 10  # 插件行水平内边距
    row_height: int = 44  # 插件行高
    check_size: int = 18  # 勾选框指示器边长
    check_width: int = 34  # 勾选位列宽，容下"必选"两字并与勾选框对齐
    name_width: int = 180  # 名称列固定宽
    status_width: int = 110  # 状态列固定宽
    col_gap: int = 12  # 列间距


@dataclass(frozen=True)
class _ButtonConfig:
    """按钮尺寸"""

    min_width: int = 90  # 最小宽度
    height: int = 30  # 最小高度
    padding_v: int = 5  # 垂直内边距
    padding_h: int = 14  # 水平内边距
    start_width: int = 120  # 主操作启动钮定宽，视觉重心


@dataclass(frozen=True)
class _LaunchConfig:
    """启动提示卡尺寸"""

    width: int = 430  # 默认宽度，图标与两行文案一行放平
    height: int = 118  # 默认高度
    gap: int = 16  # 图标与文案列间距
    icon_size: int = 44  # 应用图标边长
    text_gap: int = 6  # 正文与副注行距


# 实例单例
PICKER = _PickerConfig()
FORM = _FormConfig()
PANEL = _PanelConfig()
BTN = _ButtonConfig()
LAUNCH = _LaunchConfig()
