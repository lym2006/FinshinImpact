# src/skin/qss/_combo.py
"""下拉选择框 QSS"""

from ._base import Qss


def build_combo_qss(
    *,
    bg: str,
    fg: str,
    border_color: str,
    border_width: int,
    radius: int,
    pad_v: int,
    pad_h: int,
    accent_border: str,
    sel_bg: str,
    sel_color: str,
) -> Qss:
    """拼下拉选择框 QSS

    - 弹层与框体共用底色和文字色
    - 悬停与聚焦共用一条强调描边
    """
    return Qss(f"""\
QComboBox {{
    background-color: {bg};
    color: {fg};
    border: {border_width}px solid {border_color};
    border-radius: {radius}px;
    padding: {pad_v}px {pad_h}px;
}}

QComboBox:hover,
QComboBox:focus {{
    border: {border_width}px solid {accent_border};
}}

QComboBox QAbstractItemView {{
    background-color: {bg};
    color: {fg};
    selection-background-color: {sel_bg};
    selection-color: {sel_color};
    border: {border_width}px solid {border_color};
    outline: none;
}}""")
