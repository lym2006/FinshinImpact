# src/gui/_qss/__init__.py
"""QSS 门面

- 非空门面：转发主窗口与弹窗七个样式构建函数
- 消费方按原路径 from ._qss import build_xxx_qss 直连不变
"""

from ._dialog import (
    build_change_dialog_qss,
    build_check_dialog_qss,
    build_notice_dialog_qss,
    build_settings_dialog_qss,
    build_settings_list_qss,
    build_wait_dialog_qss,
)
from ._global import build_global_qss

__all__ = [
    "build_change_dialog_qss",
    "build_check_dialog_qss",
    "build_global_qss",
    "build_notice_dialog_qss",
    "build_settings_dialog_qss",
    "build_settings_list_qss",
    "build_wait_dialog_qss",
]
