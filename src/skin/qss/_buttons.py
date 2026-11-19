"""按钮规则唯一出处

- 通用按钮按用途词与尺寸档查表生成，窗样式只拼这一段不另写
- 固定形状词自带尺寸与边距，不随尺寸档换名
- 平台组件窗的禁用主按钮另出一段，仍由窗样式显式取用
"""

from dataclasses import dataclass, replace

from ..theme import (
    LIST_DIALOG,
    PALETTE,
    PANEL,
    SETTINGS_DIALOG,
    TOOLBAR,
    ButtonSize,
    ButtonStyle,
    button_object_name,
)

# 描边宽度，描边态与方形按钮共用一处
_BORDER_WIDTH = 1


@dataclass(frozen=True)
class _Metrics:
    """单档尺寸的留白与下限"""

    padding_v: int
    padding_h: int
    min_width: int
    min_height: int = 0
    bold: bool = False


@dataclass(frozen=True)
class _Look:
    """单个词与档的配色

    - 空串表示该态不另立规则
    """

    bg: str
    fg: str
    border: str = "none"
    hover_bg: str = ""
    hover_fg: str = ""
    hover_border: str = ""
    pressed_bg: str = ""
    disabled_bg: str = ""
    disabled_fg: str = ""
    disabled_border: str = ""


_METRICS = {
    ButtonSize.SMALL: _Metrics(padding_v=4, padding_h=12, min_width=70),
    ButtonSize.STANDARD: _Metrics(6, 16, 90, 30),
    ButtonSize.LARGE: _Metrics(6, 16, 120, 30, bold=True),
    ButtonSize.COMPACT: _Metrics(6, 14, 60, 32, bold=True),
}

_SOLID_PRIMARY = _Look(
    bg=PALETTE.sel_bg,
    fg=PALETTE.sel_color,
    hover_bg=PALETTE.primary_hover_bg,
    pressed_bg=PALETTE.primary_pressed_bg,
)

_SOLID_DANGER = _Look(
    bg=PALETTE.danger_bg,
    fg=PALETTE.sel_color,
    hover_bg=PALETTE.danger_hover_bg,
    pressed_bg=PALETTE.danger_pressed_bg,
    disabled_bg=PALETTE.bg,
    disabled_fg=PALETTE.disabled_color,
)

_SOLID_NEUTRAL = _Look(bg=PALETTE.neutral_bg, fg=PALETTE.sel_color)

# 工具栏用的小档
_COMPACT_NEUTRAL = _Look(
    bg=PALETTE.list_bg,
    fg=PALETTE.color,
    hover_bg=PALETTE.hover_lift_bg,
    hover_fg=PALETTE.hover_color,
    pressed_bg=PALETTE.pressed_bg,
)

_COMPACT_DANGER = _Look(
    bg=PALETTE.danger_bg,
    fg=PALETTE.color,
    hover_bg=PALETTE.danger_hover_bg,
    hover_fg=PALETTE.hover_color,
    pressed_bg=PALETTE.danger_pressed_bg,
)

_OUTLINE = _Look(
    bg="transparent",
    fg=PALETTE.color,
    border=f"{_BORDER_WIDTH}px solid {PALETTE.border_color}",
    hover_bg=PALETTE.hover_bg,
    hover_fg=PALETTE.hover_color,
    hover_border=f"{_BORDER_WIDTH}px solid {PALETTE.sel_bg}",
    disabled_fg=PALETTE.disabled_color,
    disabled_border="none",
)

_DELETE = _Look(
    bg="transparent",
    fg=LIST_DIALOG.secondary_color,
    border=f"{_BORDER_WIDTH}px solid {LIST_DIALOG.secondary_border_color}",
    hover_bg=LIST_DIALOG.secondary_hover_bg,
    hover_fg=LIST_DIALOG.secondary_hover_color,
    hover_border=f"{_BORDER_WIDTH}px solid {LIST_DIALOG.secondary_hover_border_color}",
)

# 实际用到的词与档组合，新增组合在此加一行
_COMBOS = (
    (ButtonStyle.PRIMARY, ButtonSize.SMALL, _SOLID_PRIMARY),
    (ButtonStyle.PRIMARY, ButtonSize.STANDARD, _SOLID_PRIMARY),
    (
        ButtonStyle.PRIMARY,
        ButtonSize.LARGE,
        replace(
            _SOLID_PRIMARY,
            disabled_bg=PALETTE.bg,
            disabled_fg=PALETTE.disabled_color,
        ),
    ),
    (ButtonStyle.DANGER, ButtonSize.STANDARD, _SOLID_DANGER),
    (ButtonStyle.NEUTRAL, ButtonSize.STANDARD, _SOLID_NEUTRAL),
    (ButtonStyle.NEUTRAL, ButtonSize.COMPACT, _COMPACT_NEUTRAL),
    (ButtonStyle.DANGER, ButtonSize.COMPACT, _COMPACT_DANGER),
    (ButtonStyle.OUTLINE, ButtonSize.STANDARD, _OUTLINE),
    (ButtonStyle.DELETE, ButtonSize.SMALL, _DELETE),
)

# 重置钮的方形尺寸
_RESET_QSS = f"""\
QPushButton#{ButtonStyle.RESET} {{
    background-color: transparent;
    color: {LIST_DIALOG.secondary_color};
    border: {_BORDER_WIDTH}px solid {LIST_DIALOG.secondary_border_color};
    border-radius: {PALETTE.radius}px;
    padding: 0;
    min-width: {SETTINGS_DIALOG.reset_btn_size}px;
    max-width: {SETTINGS_DIALOG.reset_btn_size}px;
    min-height: {SETTINGS_DIALOG.reset_btn_size}px;
    max-height: {SETTINGS_DIALOG.reset_btn_size}px;
    font-size: {SETTINGS_DIALOG.reset_btn_font}px;
}}

QPushButton#{ButtonStyle.RESET}:hover {{
    background-color: {PALETTE.hover_lift_bg};
    color: {PALETTE.hover_color};
    border-color: {PALETTE.hover_lift_bg};
}}

QPushButton#{ButtonStyle.RESET}:pressed {{
    background-color: {PALETTE.pressed_bg};
}}"""

# 冲突标记与命令格
_SHAPED_QSS = f"""\
QPushButton#{ButtonStyle.CONFLICT} {{
    background-color: transparent;
    color: {PALETTE.danger_bg};
    border: none;
    border-radius: {PALETTE.radius}px;
    padding: 0; margin: 6px {PANEL.check_width - PANEL.conflict_box_w}px 6px 0;
    min-width: {PANEL.conflict_box_w}px; min-height: {PANEL.conflict_box_h}px;
}}

QPushButton#{ButtonStyle.CONFLICT}::menu-indicator {{
    image: none;
    width: 0;
}}

QPushButton#{ButtonStyle.CONFLICT}:hover {{
    background-color: {PALETTE.danger_bg};
    color: {PALETTE.sel_color};
}}

QPushButton#{ButtonStyle.COMMAND} {{
    background-color: transparent;
    color: {PALETTE.color};
    border: {_BORDER_WIDTH}px solid {PALETTE.border_color};
    border-radius: {PALETTE.radius}px;
    padding: 0; margin: 4px 0;
    min-width: {PANEL.command_width}px; min-height: {PANEL.command_box_h}px;
}}

QPushButton#{ButtonStyle.COMMAND}:hover {{
    background-color: {PALETTE.hover_bg};
    border: {_BORDER_WIDTH}px solid {PALETTE.sel_bg};
    color: {PALETTE.hover_color};
}}"""

# 平台组件窗的已装态主按钮
PLATFORM_PRIMARY_DISABLED_QSS = f"""\
QPushButton#{ButtonStyle.PRIMARY}:disabled {{
    background-color: {TOOLBAR.bg};
    color: {PALETTE.disabled_color};
}}"""


def _base_block(name: str, look: _Look, metrics: _Metrics) -> str:
    """单组合的常态规则"""
    lines = [
        f"QPushButton#{name} {{",
        f"    background-color: {look.bg};",
        f"    color: {look.fg};",
        f"    border: {look.border};",
        f"    border-radius: {PALETTE.radius}px;",
        f"    padding: {metrics.padding_v}px {metrics.padding_h}px;",
        f"    min-width: {metrics.min_width}px;",
    ]
    if metrics.min_height:
        lines.append(f"    min-height: {metrics.min_height}px;")
    if metrics.bold:
        lines.append("    font-weight: bold;")
    lines.append("}")
    return "\n".join(lines)


def _state_block(name: str, state: str, props: list[str]) -> str:
    """单组合的单态规则"""
    body = "\n".join(f"    {prop};" for prop in props)
    return f"QPushButton#{name}:{state} {{\n{body}\n}}"


def _combo_qss(style: ButtonStyle, size: ButtonSize, look: _Look) -> str:
    """单组合的常态、悬停、按下与禁用规则"""
    name = button_object_name(style, size)
    metrics = _METRICS[size]
    blocks = [_base_block(name, look, metrics)]
    if look.hover_bg:
        props = [f"background-color: {look.hover_bg}"]
        if look.hover_fg:
            props.append(f"color: {look.hover_fg}")
        if look.hover_border:
            props.append(f"border: {look.hover_border}")
        blocks.append(_state_block(name, "hover", props))
    if look.pressed_bg:
        blocks.append(
            _state_block(name, "pressed", [f"background-color: {look.pressed_bg}"])
        )
    if look.disabled_bg or look.disabled_fg:
        props = []
        if look.disabled_bg:
            props.append(f"background-color: {look.disabled_bg}")
        if look.disabled_fg:
            props.append(f"color: {look.disabled_fg}")
        if look.disabled_border:
            props.append(f"border: {look.disabled_border}")
        if metrics.bold:
            props.append("font-weight: normal")
        blocks.append(_state_block(name, "disabled", props))
    return "\n\n".join(blocks)


def build_button_qss() -> str:
    """构建全部按钮规则"""
    blocks = [_combo_qss(*combo) for combo in _COMBOS]
    blocks += [_RESET_QSS, _SHAPED_QSS]
    return "\n\n".join(blocks)
