"""平台组件面板

- 开窗先出等待读数并按秒正计时，在线目录取到才按三档摆读数
- 面板只摆读数与发起动作
- 取数失败只在屏上留一行原因，装卸才走进度窗
"""

import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from services.adapter_catalog import Catalog
from services.env_setup.platform_rows import (
    ComponentBucket,
    ComponentRow,
    component_rows,
)
from services.env_setup.platform_state import update_targets
from skin.messages import PlatformMessage
from skin.qss import build_platform_dialog_qss
from skin.theme import GLOBAL, PLATFORM_DIALOG, ButtonStyle, ObjectName

from .._lifecycle import Ticker, ensure_app
from .._primitives import clear_layout, make_button, make_scroller, set_margins
from ._catalog_task import CatalogTask
from ._platform_block import ComponentBlock
from ._platform_flow import install_flow

# 三档的先后次序与段名
_SECTIONS = (
    (ComponentBucket.LOCAL, PlatformMessage.HEAD_LOCAL),
    (ComponentBucket.UPGRADABLE, PlatformMessage.HEAD_UPGRADABLE),
    (ComponentBucket.ONLINE, PlatformMessage.HEAD_ONLINE),
)

# 关窗时仍在跑的取数线程，跑完自摘
# 线程跟着窗一起销毁会让 Qt 当场终止进程，引导段没有现成的第二选择
_RUNNING: set[CatalogTask] = set()


class _PlatformDialog(QDialog):
    """平台组件面板

    - 动作按钮就地起装卸，跑完按最新读数重灌
    - 在线目录缺位时只出本机已有那一档
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._catalog: Catalog | None = None
        self._note = ""
        self._reading = True
        self._start = time.monotonic()
        self._wait_label: QLabel | None = None
        self.setWindowTitle(PLATFORM_DIALOG.title)
        self.setStyleSheet(build_platform_dialog_qss())

        layout = QVBoxLayout(self)
        set_margins(layout, PLATFORM_DIALOG.pad)
        layout.setSpacing(PLATFORM_DIALOG.spacing)

        # 组件块逐只往下堆，读不完的部分交给滚动条接住
        self._body = QVBoxLayout()
        host = QWidget(parent=self)
        host.setLayout(self._body)
        layout.addWidget(make_scroller(host), 1)

        self._all = make_button(PlatformMessage.BTN_UPDATE_ALL, ButtonStyle.PRIMARY)
        self._all.clicked.connect(
            lambda: install_flow(self._render, update_targets(self._rows()))
        )
        layout.addWidget(self._all, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setFixedSize(PLATFORM_DIALOG.width, PLATFORM_DIALOG.height)
        self._render()

        self._ticker = Ticker(self, GLOBAL.tick_ms, self._advance)
        self._ticker.start()

        self._task = CatalogTask()
        self._task.reported.connect(self._on_reported)
        self._task.start()

    def _advance(self) -> None:
        """等待读数跳秒"""
        if not self._reading:
            self._ticker.stop()
            return
        if self._wait_label is not None:
            self._wait_label.setText(self._waiting_text())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """关窗时取数未回则把线程交给模块级集合持有"""
        if self._task.isRunning():
            task = self._task
            _RUNNING.add(task)
            task.finished.connect(lambda: _RUNNING.discard(task))
        super().closeEvent(event)

    def _on_reported(self, catalog: object, note: str) -> None:
        """取数回来后重灌读数

        - 同时停掉正计时，目录与失败原因各摆一处
        """
        self._catalog = catalog if isinstance(catalog, Catalog) else None
        self._note = note
        self._reading = False
        self._ticker.stop()
        self._render()

    def _rows(self) -> tuple[ComponentRow, ...]:
        """当前读数"""
        return component_rows(self._catalog)

    def _waiting_text(self) -> str:
        """等待读数正文

        - 带起窗至今的秒数
        - 取数期间正文只出这一行
        """
        return PlatformMessage.WAIT_CATALOG.format(
            seconds=int(time.monotonic() - self._start)
        )

    def _render(self) -> None:
        """按三档重建组件块

        - 段内没行即整段不出
        - 失败原因行与拒收条目照样摆出
        - 没有可更新项即藏掉全部更新按钮
        """
        self._clear_body()
        self._all.setVisible(False)
        if self._reading:
            self._wait_label = QLabel(self._waiting_text(), parent=self)
            self._body.addWidget(self._wait_label)
            self._body.addStretch()
            return

        rows = self._rows()
        if self._note:
            self._body.addWidget(QLabel(self._note, parent=self))

        for bucket, text in _SECTIONS:
            block = [row for row in rows if row.bucket == bucket]
            if not block:
                continue
            head = QLabel(text, parent=self)
            head.setObjectName(ObjectName.PLATFORM_SECTION)
            self._body.addWidget(head)
            for row in block:
                self._body.addWidget(ComponentBlock(self, row, rows, self._render))

        rejects = () if self._catalog is None else self._catalog.rejects
        if rejects:
            self._body.addWidget(QLabel(PlatformMessage.REJECTS_HEAD, parent=self))
            for note in rejects:
                self._body.addWidget(QLabel(note, parent=self))

        self._all.setVisible(bool(update_targets(rows)))
        self._body.addStretch()

    def _clear_body(self) -> None:
        """丢掉等待读数的引用再拆控件"""
        self._wait_label = None
        clear_layout(self._body)


def open_platform_dialog(parent: QWidget | None = None) -> None:
    """打开平台组件面板

    - 在线目录在窗内后台取
    """
    ensure_app()
    _PlatformDialog(parent).exec()
