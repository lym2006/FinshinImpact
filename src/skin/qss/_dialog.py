# src/skin/qss/_dialog.py
"""通用弹窗 QSS 装配

- 用基础件拼出通知与等待两类成品串
- 退出确认窗配色自成一套，不套基础件
"""

from ..theme import BTN, GLOBAL, SHUTDOWN_DIALOG, ButtonStyle
from ._base import WAIT_QSS, Qss, with_dialog_base

# 退出确认窗窗口与文字
_SHUTDOWN_WINDOW_QSS = f"""\
QDialog {{
    background-color: {SHUTDOWN_DIALOG.bg_color};
}}

QLabel {{
    color: {SHUTDOWN_DIALOG.text_color};
}}"""

# 退出确认窗两颗按钮
# 尺寸显式取全局按钮令牌，否则无父窗时没人给尺寸（祖先样式表下渗不可依赖）
_SHUTDOWN_BUTTON_QSS = f"""\
QPushButton#{ButtonStyle.SECONDARY} {{
    background-color: {SHUTDOWN_DIALOG.cancel_bg};
    color: {SHUTDOWN_DIALOG.cancel_color};
    border-radius: {GLOBAL.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h}px;
    min-width: {BTN.min_width}px;
    min-height: {BTN.height}px;
}}

QPushButton#{ButtonStyle.DANGER} {{
    background-color: {SHUTDOWN_DIALOG.confirm_bg};
    color: {SHUTDOWN_DIALOG.confirm_color};
    border-radius: {GLOBAL.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h}px;
    min-width: {BTN.min_width}px;
    min-height: {BTN.height}px;
}}"""


def build_notice_dialog_qss() -> Qss:
    """构建通知弹窗 QSS"""
    return with_dialog_base()


def build_wait_dialog_qss() -> Qss:
    """构建忙碌等待弹窗 QSS"""
    return with_dialog_base(WAIT_QSS)


def build_shutdown_dialog_qss() -> Qss:
    """构建退出确认弹窗 QSS"""
    return Qss("\n\n".join([_SHUTDOWN_WINDOW_QSS, _SHUTDOWN_BUTTON_QSS]))
