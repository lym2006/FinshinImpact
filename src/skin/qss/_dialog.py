"""通用弹窗 QSS 装配

- 用基础件拼出通知、版本变化、等待与平台组件四类成品串
- 退出确认与断连计时两窗配色自成一套
"""

from ..theme import (
    BODY,
    GLOBAL,
    LINK_DIALOG,
    PLATFORM_DIALOG,
    SETTINGS_DIALOG,
    SHUTDOWN_DIALOG,
    TOOLBAR,
    ObjectName,
)
from ._base import WAIT_QSS, Qss, with_dialog_base
from ._buttons import PLATFORM_PRIMARY_DISABLED_QSS, build_button_qss

# 退出确认窗窗口与文字
_SHUTDOWN_WINDOW_QSS = f"""\
QDialog {{
    background-color: {SHUTDOWN_DIALOG.bg_color};
}}

QLabel {{
    color: {SHUTDOWN_DIALOG.text_color};
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

# 版本变化窗正文区
_RELEASE_NOTES_VIEW_QSS = f"""\
QTextEdit#{ObjectName.RELEASE_NOTES_VIEW} {{
    background-color: {TOOLBAR.bg};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {SETTINGS_DIALOG.input_padding_v}px {SETTINGS_DIALOG.input_padding_h}px;
}}"""


# 平台组件窗的段名与组件块，块内留白由布局边距给
_PLATFORM_BLOCK_QSS = f"""\
QLabel#{ObjectName.PLATFORM_SECTION} {{
    font-size: {PLATFORM_DIALOG.name_font_size}px;
    font-weight: bold;
}}

QFrame#{ObjectName.PLATFORM_BLOCK} {{
    background-color: {TOOLBAR.bg};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
}}

QLabel#{ObjectName.PLATFORM_NAME} {{
    font-size: {PLATFORM_DIALOG.name_font_size}px;
    font-weight: bold;
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
    return Qss("\n\n".join([_SHUTDOWN_WINDOW_QSS, build_button_qss()]))


def build_link_dialog_qss() -> Qss:
    """构建断连计时弹窗 QSS"""
    return Qss("\n\n".join([_LINK_WINDOW_QSS, build_button_qss()]))


def build_platform_dialog_qss() -> Qss:
    """构建平台组件面板 QSS"""
    return with_dialog_base(_PLATFORM_BLOCK_QSS, PLATFORM_PRIMARY_DISABLED_QSS)
