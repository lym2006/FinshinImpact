"""平台组件面板

- 开窗先出等待读数并按秒正计时，在线目录取到才按三档摆读数
- 逐只组件一块，块内按栏名逐行摆，动作栏只摆做得到的动作
- 面板只摆读数与发起动作，读数与装卸全在 services 那侧
- 取数失败只在屏上留一行原因，装卸才走进度窗
"""

import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.adapter_catalog import Catalog
from services.env_setup.platform_state import (
    ComponentBucket,
    ComponentRow,
    ComponentSource,
    component_rows,
    deps_text,
    install_blocked,
    update_targets,
)
from skin.messages import PlatformMessage
from skin.qss import build_platform_dialog_qss
from skin.theme import GLOBAL, PLATFORM_DIALOG, ButtonStyle, ObjectName

from .._lifecycle import Ticker, ensure_app
from .._primitives import clear_layout, make_button, make_scroller, set_margins
from ._catalog_task import CatalogTask
from ._platform_flow import install_flow, uninstall_flow

# 三档的先后次序与段名
_SECTIONS = (
    (ComponentBucket.LOCAL, PlatformMessage.HEAD_LOCAL),
    (ComponentBucket.UPGRADABLE, PlatformMessage.HEAD_UPGRADABLE),
    (ComponentBucket.ONLINE, PlatformMessage.HEAD_ONLINE),
)

# 来源取值给人看的那句
_SOURCE_TEXT = {
    ComponentSource.TREE: PlatformMessage.SOURCE_TREE,
    ComponentSource.INSTALLED: PlatformMessage.SOURCE_INSTALLED,
    ComponentSource.NONE: PlatformMessage.SOURCE_NONE,
}

# 关窗时仍在跑的取数线程，跑完自摘
# 线程跟着窗一起销毁会让 Qt 当场终止进程，引导段没有现成的第二选择
_RUNNING: set[CatalogTask] = set()


def _name_of(row: ComponentRow) -> str:
    """块首行的组件名，两类都接各自声明的发行件名"""
    template = (
        PlatformMessage.NAME_SDK if not row.platform else PlatformMessage.NAME_ADAPTER
    )
    return template.format(name=row.distribution)


def _version_text(row: ComponentRow) -> str:
    """版本行的正文，本机与在线各说各的"""
    if row.release is None:
        return row.installed or PlatformMessage.LINE_ABSENT
    if not row.installed:
        return PlatformMessage.LINE_VERSIONS_ABSENT.format(
            available=row.release.version
        )

    return PlatformMessage.LINE_VERSIONS.format(
        installed=row.installed, available=row.release.version
    )


def _action_text(row: ComponentRow) -> str:
    """动作栏的按钮文案，本机没装过即安装"""
    return (
        PlatformMessage.BTN_INSTALL if not row.installed else PlatformMessage.BTN_APPLY
    )


class _PlatformDialog(QDialog):
    """平台组件面板

    - 在线目录取回来之前只出等待读数，取到才按三档摆
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
        """等待读数跳秒，取数回来即停泵"""
        if not self._reading:
            self._ticker.stop()
            return
        if self._wait_label is not None:
            self._wait_label.setText(self._waiting_text())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """关窗时取数还没回来即把线程交给模块持有"""
        if self._task.isRunning():
            task = self._task
            _RUNNING.add(task)
            task.finished.connect(lambda: _RUNNING.discard(task))
        super().closeEvent(event)

    def _on_reported(self, catalog: object, note: str) -> None:
        """取数回来即停正计时，目录与原因各摆各的，重灌读数"""
        self._catalog = catalog if isinstance(catalog, Catalog) else None
        self._note = note
        self._reading = False
        self._ticker.stop()
        self._render()

    def _rows(self) -> tuple[ComponentRow, ...]:
        """当前读数，目录没在场即只有本机那一档"""
        return component_rows(self._catalog)

    def _waiting_text(self) -> str:
        """等待读数的正文，取数期间只出这一行"""
        return PlatformMessage.WAIT_CATALOG.format(
            seconds=int(time.monotonic() - self._start)
        )

    def _render(self) -> None:
        """按三档重建组件块，段内没行即整段不出，没得更新即一键不出"""
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
                self._body.addWidget(self._block(row))

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

    def _block(self, row: ComponentRow) -> QFrame:
        """一只组件一块，行按栏名逐条摆"""
        block = QFrame(parent=self)
        block.setObjectName(ObjectName.PLATFORM_BLOCK)
        lines = QVBoxLayout(block)
        set_margins(lines, PLATFORM_DIALOG.block_pad)

        head = QLabel(_name_of(row), parent=block)
        head.setObjectName(ObjectName.PLATFORM_NAME)
        lines.addWidget(head)
        for label, value in self._fields_of(block, row):
            if isinstance(value, str):
                lines.addWidget(QLabel(f"{label}：{value}", parent=block))
                continue
            pair = QHBoxLayout()
            pair.addWidget(QLabel(f"{label}：", parent=block))
            pair.addWidget(value)
            pair.addStretch()
            lines.addLayout(pair)

        return block

    def _fields_of(
        self, block: QFrame, row: ComponentRow
    ) -> list[tuple[str, str | QWidget]]:
        """一块之内的行，有目录行的末尾多一条可点的动作行"""
        fields: list[tuple[str, str | QWidget]] = [
            (PlatformMessage.LABEL_SOURCE, _SOURCE_TEXT[row.source]),
            (PlatformMessage.LABEL_VERSION, _version_text(row)),
        ]
        floor = deps_text(row)
        if floor:
            fields.append((PlatformMessage.LABEL_DEPS, floor))

        actions = self._actions_of(block, row)
        if actions is not None:
            fields.append((PlatformMessage.LABEL_ACTION, actions))

        return fields

    def _actions_of(self, block: QFrame, row: ComponentRow) -> QWidget | None:
        """动作栏的按钮，只摆真做得到的动作

        - 本机已有又没得更动的颗都没有，一颗都没有即整行不出
        - 已装包的再多一颗卸载
        - 适配器那颗点不动时，旁边跟一句下一步
        """
        buttons: list[QPushButton] = []
        note = ""
        release = row.release
        if release is not None and row.bucket != ComponentBucket.LOCAL:
            todo = make_button(_action_text(row), ButtonStyle.PRIMARY)
            note = install_blocked(self._rows(), row)
            todo.setEnabled(not note)
            todo.clicked.connect(lambda: install_flow(self._render, [release]))
            buttons.append(todo)
        if bool(row.platform) and row.source == ComponentSource.INSTALLED:
            drop = make_button(PlatformMessage.BTN_UNINSTALL, ButtonStyle.DANGER)
            drop.clicked.connect(
                lambda: uninstall_flow(self, self._render, row.platform)
            )
            buttons.append(drop)
        if not buttons:
            return None

        holder = QWidget(parent=block)
        pair = QHBoxLayout(holder)
        pair.setContentsMargins(0, 0, 0, 0)
        for button in buttons:
            pair.addWidget(button)
        if note:
            pair.addWidget(QLabel(note, parent=holder))
        pair.addStretch()

        return holder


def open_platform_dialog(parent: QWidget | None = None) -> None:
    """打开平台组件面板，在线目录在窗内后台取"""
    ensure_app()
    _PlatformDialog(parent).exec()
