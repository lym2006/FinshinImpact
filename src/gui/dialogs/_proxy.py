# src/gui/dialogs/_proxy.py
"""网络诊断弹窗（内部实现）

- 打开即渲染等待骨架，后台线程逐项刷新
- 每行四态流转：灰等待 → 白检测 → 绿/红结果
"""

import html

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QPushButton, QTextEdit, QVBoxLayout

from utils import diagnose_plan, iter_diagnose

from .._qss import build_proxy_dialog_qss
from .._theme import PROXY_DIALOG as PD
from ..mediator import gui_bridge
from ._base import BaseDialog

_STATE = {
    "pending": (PD.pending_mark, PD.pending_color),
    "checking": (PD.checking_mark, PD.checking_color),
    "ok": (PD.ok_mark, PD.ok_color),
    "fail": (PD.fail_mark, PD.fail_color),
}


class _DiagWorker(QThread):
    """诊断线程

    网络探测有秒级阻塞，不占 GUI 线程。
    生成器每产出一条就发一帧，界面逐行点亮。
    """

    row_update = Signal(dict)

    def __init__(self, configured_proxy: str, parent=None) -> None:
        super().__init__(parent)
        self._proxy = configured_proxy

    def run(self) -> None:
        try:
            for row in iter_diagnose(self._proxy):
                if self.isInterruptionRequested():
                    return
                self.row_update.emit(row)
        except Exception as e:  # 诊断自身异常也变成一行结果
            self.row_update.emit(
                {"id": "advice", "status": "fail", "detail": f"诊断异常: {e}"}
            )


class ProxyDialog(BaseDialog):
    """诊断结果展示窗（非模态，可与向导并排对照）"""

    def __init__(self, configured_proxy: str = "", parent=None) -> None:
        super().__init__(parent=parent, title=PD.title)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._configured = configured_proxy
        self._worker: _DiagWorker | None = None
        # 运行中的探测线程集合：finished 前禁止被 GC
        self._workers: set[_DiagWorker] = set()
        # {行id: [标题, 状态, 详情]}：渲染的唯一数据源
        self._rows: dict[str, list] = {}

        self.setStyleSheet(build_proxy_dialog_qss())
        self.resize(PD.width, PD.height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[PD.pad] * 4)

        self._view = QTextEdit()
        self._view.setObjectName("proxy_view")
        self._view.setReadOnly(True)
        layout.addWidget(self._view)

        self._btn = QPushButton(PD.btn_text)
        self._btn.setObjectName("btn_primary")
        self._btn.clicked.connect(self.start_diagnose)
        layout.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignRight)

        # 打开即见全灰骨架：先填充等待态数据源再渲染
        self._rows = {
            r["id"]: [r["title"], r["status"], r["detail"]] for r in diagnose_plan()
        }
        self._render()

        # 配置验证通过 → 通道行原地转绿（验证本身即探测证据）
        gui_bridge.config_verified.connect(self._on_verified, "诊断刷新", queued=True)

    # ==================== 诊断流程 ====================

    def _on_verified(self) -> None:
        """把"当前生效通道/结论"直接刷成可达，不重新探测"""
        changed = False
        cur = self._rows.get("current")
        if cur and cur[1] != "ok":
            cur[1] = "ok"
            cur[2] = "可达（配置验证刚刚通过）"
            changed = True
        adv = self._rows.get("advice")
        if adv and adv[1] != "ok":
            adv[1] = "ok"
            adv[2] = "当前配置可达 Telegram，无需修改"
            changed = True
        if changed:
            self._render()

    def start_diagnose(self) -> None:
        """重跑一遍

        先复位骨架，再启动后台线程
        """
        if any(w.isRunning() for w in self._workers):
            return
        self._btn.setEnabled(False)
        self._btn.setText(PD.running_text)
        self._rows = {
            r["id"]: [r["title"], r["status"], r["detail"]] for r in diagnose_plan()
        }
        self._render()

        self._worker = _DiagWorker(self._configured, parent=self)
        self._worker.row_update.connect(self._on_row)
        self._worker.finished.connect(lambda w=self._worker: self._workers.discard(w))
        self._workers.add(self._worker)
        self._worker.start()

    def _on_row(self, row: dict) -> None:
        """单帧刷新

        只改变化的那一行
        """
        entry = self._rows.get(row["id"])
        if entry is not None:
            entry[1] = row["status"]
            entry[2] = row["detail"]
        self._render()
        # advice 有两帧（checking+结果），复位与拉向导只认结果帧
        if row["id"] == "advice" and row["status"] != "checking":
            self._btn.setEnabled(True)
            self._btn.setText(PD.retry_text)
            # 线程对象由 finished 统一出集合；此处仅解除当前代引用
            self._worker = None
            # 当前生效通道不通：拉起强制向导并标红代理项
            if row.get("broken"):
                gui_bridge.request_force_setup.emit({"proxy": row["detail"]})

    def _render(self) -> None:
        """按当前状态全量重绘 HTML（行少，成本可忽略）"""
        lines = []
        for title, status, detail in self._rows.values():
            mark, color = _STATE[status]
            detail_html = (
                f"<span style='color: {color};'>{html.escape(detail)}</span>"
                if detail
                else ""
            )
            lines.append(
                f"<p style='margin:{PD.row_margin}px;'>"
                f"<span style='color: {color};'>{mark} "
                f"<b>{html.escape(title)}</b></span>  {detail_html}</p>"
            )
        self._view.setHtml("".join(lines))

    # ==================== 关闭收尾 ====================

    def reject(self):
        """关窗前等待检测线程收尾"""
        gui_bridge.config_verified.disconnect("诊断刷新")
        self._join_workers()
        return super().reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        # 中断全部在跑线程并逐个等待：finished 前集合持有，防析构崩溃
        for worker in self._workers:
            worker.requestInterruption()
        self._join_workers()
        gui_bridge.config_verified.disconnect("诊断刷新")
        super().closeEvent(event)

    def _join_workers(self) -> None:
        for worker in set(self._workers):
            if worker.isRunning():
                worker.wait(12000)
