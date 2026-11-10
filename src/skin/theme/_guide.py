# src/skin/theme/_guide.py
"""引导期视觉令牌

- 选窗、表单窗、插件面板、进度窗共用一套尺寸与间距
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PickerTheme:
    """实例选窗尺寸"""

    width: int = 840  # 默认宽度，容下六个按钮一行不挤
    height: int = 400  # 默认高度
    min_width: int = 760  # 最小宽度，按钮行不挤扁的下限
    min_height: int = 320  # 最小高度


@dataclass(frozen=True)
class FormTheme:
    """实例表单窗尺寸"""

    width: int = 460  # 默认宽度
    height: int = 320  # 默认高度
    min_width: int = 380  # 最小宽度
    min_height: int = 260  # 最小高度


@dataclass(frozen=True)
class PanelTheme:
    """插件面板尺寸"""

    width: int = 620  # 默认宽度
    height: int = 440  # 默认高度
    min_width: int = 560  # 最小宽度
    min_height: int = 340  # 最小高度
    row_pad_v: int = 6  # 插件行垂直内边距
    row_pad_h: int = 10  # 插件行水平内边距
    row_height: int = 44  # 插件行高
    check_width: int = 34  # 勾选位列宽，容下"必选"两字并与勾选框对齐
    conflict_box_w: int = 26  # 冲突色块宽，两字文案加左右各一格的余量
    conflict_box_h: int = 20  # 冲突色块高，与对勾方框同一档，上下各出一格
    name_width: int = 180  # 名称列固定宽
    status_width: int = 110  # 状态列固定宽
    command_width: int = 44  # 行尾看命令按钮的内容宽，一圈描边另算，宽度只由样式表给
    command_box_h: int = 24  # 看命令按钮高，比冲突色块高一档，容一圈描边
    col_gap: int = 12  # 列间距
    conflict_width: int = 420  # 冲突明细窗定宽，一句一行在这宽度里循环滚
    conflict_rows: int = 5  # 明细窗最多露几行，按整行给，条目再多走竖向滚动


@dataclass(frozen=True)
class GuideButtonTheme:
    """按钮尺寸"""

    min_width: int = 90  # 最小宽度
    height: int = 30  # 最小高度
    padding_v: int = 5  # 垂直内边距
    padding_h: int = 14  # 水平内边距
    start_width: int = 120  # 主操作启动钮定宽，视觉重心


@dataclass(frozen=True)
class LaunchTheme:
    """启动提示卡尺寸"""

    width: int = 430  # 默认宽度，图标与两行文案一行放平
    height: int = 118  # 默认高度
    gap: int = 16  # 图标与文案列间距
    icon_size: int = 44  # 应用图标边长
    text_gap: int = 6  # 正文与副注行距
