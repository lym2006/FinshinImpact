# src/skin/qss/_dialog.py
"""通用弹窗 QSS 装配

- 用基础件拼出通知与等待两类成品串
"""

from ._base import WAIT_QSS, Qss, with_dialog_base


def build_notice_dialog_qss() -> Qss:
    """构建通知弹窗 QSS"""
    return with_dialog_base()


def build_wait_dialog_qss() -> Qss:
    """构建忙碌等待弹窗 QSS"""
    return with_dialog_base(WAIT_QSS)
