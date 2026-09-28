# src/gui/dialogs/_table.py
"""五态行表格（内部实现）

- 网络诊断窗与连通校验窗共用的行渲染组件
- 状态符号与颜色由弹窗令牌注入，本组件不持有话术
"""

import html
from typing import Any

from PySide6.QtWidgets import QTextEdit, QWidget

from utils.net_probe import FrameKey, RowStatus

from .._theme import FiveStateDialogConfig

__all__ = ["RowTable"]


def _state_map(cfg: FiveStateDialogConfig) -> dict[str, tuple[str, str]]:
    """从弹窗令牌提取 {状态: (符号, 颜色)} 渲染表"""
    return {
        RowStatus.PENDING: (cfg.pending_mark, cfg.pending_color),
        RowStatus.CHECKING: (cfg.checking_mark, cfg.checking_color),
        RowStatus.OK: (cfg.ok_mark, cfg.ok_color),
        RowStatus.FAIL: (cfg.fail_mark, cfg.fail_color),
        RowStatus.SKIP: (cfg.skip_mark, cfg.skip_color),
    }


class RowTable(QTextEdit):
    """五态行表格：rows 帧整表重建，row 帧单行点亮"""

    def __init__(
        self, cfg: FiveStateDialogConfig, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._states = _state_map(cfg)
        self._margin = cfg.row_margin

        # {行id: [标题, 状态, 详情]}：渲染的唯一数据源
        self._rows: dict[str, list[str]] = {}
        self.setObjectName("row_view")
        self.setReadOnly(True)

    def reset(self, rows: list[dict[str, str]]) -> None:
        """按骨架行整表重建"""
        self._rows = {r["id"]: [r["title"], r["status"], r["detail"]] for r in rows}
        self._render()

    def apply(self, frame: dict[str, Any]) -> None:
        """消费一帧：rows 键整表重建，id 键单行点亮；未知 id 忽略"""
        if FrameKey.ROWS in frame:
            self.reset(frame[FrameKey.ROWS])
            return
        entry = self._rows.get(frame["id"])
        if entry is None:
            return
        entry[1] = frame.get("status", entry[1])
        entry[2] = frame.get("detail", entry[2])
        self._render()

    def _render(self) -> None:
        """按当前状态全量重绘 HTML"""
        lines: list[str] = []
        for title, status, detail in self._rows.values():
            mark, color = self._states[status]
            detail_html = (
                f"<span style='color: {color};'>{html.escape(detail)}</span>"
                if detail
                else ""
            )
            lines.append(
                f"<p style='margin:{self._margin}px;'>"
                f"<span style='color: {color};'>{mark} "
                f"<b>{html.escape(title)}</b></span>  {detail_html}</p>"
            )
        self.setHtml("".join(lines))
