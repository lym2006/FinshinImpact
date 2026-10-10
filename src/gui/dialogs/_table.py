# src/gui/dialogs/_table.py
"""五态行表格

- 网络诊断窗与连通校验窗共用的行渲染组件
- 状态符号与颜色由弹窗令牌注入，本组件不持有话术
"""

import html
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QTextEdit, QWidget

from utils.net_probe import FrameKey, RowStatus

from .._theme import FiveStateDialogConfig

_CLOCK_MS = 1000  # 倒计时步进：一秒一跳，与探测预算的秒刻度对齐


def _state_map(cfg: FiveStateDialogConfig) -> dict[str, tuple[str, str]]:
    """按弹窗令牌拼状态到符号颜色的渲染表"""
    return {
        RowStatus.PENDING: (cfg.pending_mark, cfg.pending_color),
        RowStatus.CHECKING: (cfg.checking_mark, cfg.checking_color),
        RowStatus.OK: (cfg.ok_mark, cfg.ok_color),
        RowStatus.FAIL: (cfg.fail_mark, cfg.fail_color),
        RowStatus.SKIP: (cfg.skip_mark, cfg.skip_color),
    }


class RowTable(QTextEdit):
    """五态行表格

    - rows 帧整表重建，row 帧单行点亮，进行中行独立倒计时
    """

    def __init__(
        self, cfg: FiveStateDialogConfig, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._states = _state_map(cfg)
        self._margin = cfg.row_margin
        self._countdown = cfg.countdown

        # {行id: [标题, 状态, 详情]}：渲染的唯一数据源
        self._rows: dict[str, list[str]] = {}

        # {行id: 预算秒}：开局帧携带，仅通道行有
        self._budgets: dict[str, int] = {}

        # {行id: 已测秒}：在场行进 checking 起跳，定案即摘
        self._elapsed: dict[str, int] = {}
        self.setObjectName("row_view")
        self.setReadOnly(True)

        self._clock = QTimer(self)
        self._clock.setInterval(_CLOCK_MS)
        self._clock.timeout.connect(self._advance_clock)

    def reset(self, rows: list[dict[str, Any]]) -> None:
        """按骨架行整表重建

        - 随行重挂预算与计时起点
        """
        self._rows = {r["id"]: [r["title"], r["status"], r["detail"]] for r in rows}
        self._budgets = {r["id"]: int(r["budget"]) for r in rows if "budget" in r}
        self._elapsed = {
            rid: 0 for rid in self._budgets if self._rows[rid][1] == RowStatus.CHECKING
        }
        self._sync_clock()
        self._render()

    def apply(self, frame: dict[str, Any]) -> None:
        """消费一帧

        - rows 键整表重建，id 键单行点亮
        - 未知 id 与已定案行忽略
        - 定案行拒改是并行版的迟到帧闸门：被取消探测的线程结果后到也不许翻案
        """
        if FrameKey.ROWS in frame:
            self.reset(frame[FrameKey.ROWS])
            return
        entry = self._rows.get(frame["id"])
        if entry is None or entry[1] not in (RowStatus.PENDING, RowStatus.CHECKING):
            return
        entry[1] = frame.get("status", entry[1])
        entry[2] = frame.get("detail", entry[2])
        rid = frame["id"]
        if entry[1] == RowStatus.CHECKING and rid in self._budgets:
            self._elapsed.setdefault(rid, 0)
        else:
            self._elapsed.pop(rid, None)
        self._sync_clock()
        self._render()

    def _sync_clock(self) -> None:
        """有在数行开钟"""
        if self._elapsed and not self._clock.isActive():
            self._clock.start()
        elif not self._elapsed:
            # 数完自动停
            self._clock.stop()

    def _advance_clock(self) -> None:
        """在数行进一秒"""
        for rid in list(self._elapsed):
            if self._rows.get(rid, ["", ""])[1] != RowStatus.CHECKING:
                self._elapsed.pop(rid)
                continue
            self._elapsed[rid] += 1
        self._sync_clock()
        self._render()

    def _render(self) -> None:
        """按当前状态全量重绘行表格 HTML

        - 进行中行追加计时后缀
        - 重绘后控件高度收紧到内容
        """
        lines: list[str] = []
        for rid, (title, status, detail) in self._rows.items():
            mark, color = self._states[status]
            text = detail
            if rid in self._elapsed and status == RowStatus.CHECKING:
                tick = self._countdown.format(
                    n=self._elapsed[rid], budget=self._budgets[rid]
                )
                text = f"{text} {tick}" if text else tick
            detail_html = (
                f"<span style='color: {color};'>{html.escape(text)}</span>"
                if text
                else ""
            )
            lines.append(
                f"<p style='margin:{self._margin}px;'>"
                f"<span style='color: {color};'>{mark} "
                f"<b>{html.escape(title)}</b></span>  {detail_html}</p>"
            )
        self.setHtml("".join(lines))
        self._fit_height()

    def _fit_height(self) -> None:
        """固定高度为文档实际高

        - 窗随行数与换行自动收紧，不出滚动条
        """
        doc = self.document()
        doc.setTextWidth(self.viewport().width())
        height = (
            int(doc.size().height())
            + 2 * int(doc.documentMargin())
            + 2 * self.frameWidth()
            + 2
        )
        self.setFixedHeight(height)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        """宽度变化时改变换行并重算高度"""
        super().resizeEvent(event)
        self._fit_height()
