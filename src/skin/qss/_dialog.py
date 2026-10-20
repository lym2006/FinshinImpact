# src/skin/qss/_dialog.py
"""通用弹窗 QSS 装配

- 用基础件拼出通知、版本变化与等待三类成品串
- 退出确认与断连计时两窗配色自成一套，不套基础件
"""

from ..theme import (
    BODY,
    BTN,
    GLOBAL,
    LINK_DIALOG,
    SETTINGS_DIALOG,
    SHUTDOWN_DIALOG,
    TOOLBAR,
    ButtonStyle,
    ObjectName,
)
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

# 断连计时窗窗口与三行文字
_LINK_WINDOW_QSS = f"""\
QDialog {{
    background-color: {LINK_DIALOG.bg_color};
}}

QLabel#{ObjectName.LINK_HEAD},
QLabel#{ObjectName.LINK_RETRIES} {{
    color: {LINK_DIALOG.text_color};
}}

QLabel#{ObjectName.LINK_TIMER} {{
    color: {LINK_DIALOG.timer_color};
}}"""

# 断连计时窗按钮
# 尺寸显式取全局按钮令牌，否则无父窗时没人给尺寸（祖先样式表下渗不可依赖）
_LINK_BUTTON_QSS = f"""\
QPushButton#{ButtonStyle.SECONDARY} {{
    background-color: {LINK_DIALOG.mute_bg};
    color: {LINK_DIALOG.btn_color};
    border-radius: {GLOBAL.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h}px;
    min-width: {BTN.min_width}px;
    min-height: {BTN.height}px;
}}"""


# 版本变化窗正文区
_RELEASE_NOTES_VIEW_QSS = f"""\
QTextEdit#{ObjectName.RELEASE_NOTES_VIEW} {{
    background-color: {TOOLBAR.bg};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {SETTINGS_DIALOG.input_padding_v}px {SETTINGS_DIALOG.input_padding_h}px;
}}"""


def build_notice_dialog_qss() -> Qss:
    """构建通知弹窗 QSS"""
    return with_dialog_base()


def build_release_notes_dialog_qss() -> Qss:
    """构建版本变化弹窗 QSS"""
    return with_dialog_base(_RELEASE_NOTES_VIEW_QSS)


def build_wait_dialog_qss() -> Qss:
    """构建忙碌等待弹窗 QSS"""
    return with_dialog_base(WAIT_QSS)


def build_shutdown_dialog_qss() -> Qss:
    """构建退出确认弹窗 QSS"""
    return Qss("\n\n".join([_SHUTDOWN_WINDOW_QSS, _SHUTDOWN_BUTTON_QSS]))


def build_link_dialog_qss() -> Qss:
    """构建断连计时弹窗 QSS"""
    return Qss("\n\n".join([_LINK_WINDOW_QSS, _LINK_BUTTON_QSS]))
