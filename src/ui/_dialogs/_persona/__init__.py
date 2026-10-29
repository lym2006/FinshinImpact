# src/ui/_dialogs/_persona/__init__.py
"""人设弹窗

- 代发面板入口行、正文编辑、两份正文拍板与默认模板更新提示
"""

from ._panel import PersonaPreviewRow
from ._resolve import PersonaResolveDialog
from ._sync import PersonaSyncDialog

__all__ = [
    # 面板入口行
    "PersonaPreviewRow",
    # 正文弹窗
    "PersonaResolveDialog",
    "PersonaSyncDialog",
]
