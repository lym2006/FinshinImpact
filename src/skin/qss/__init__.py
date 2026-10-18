# src/skin/qss/__init__.py
"""QSS 拼接门面

- 导出各控件与窗面拼好的 QSS 串
"""

from ._combo import build_combo_qss

__all__ = ["build_combo_qss"]
