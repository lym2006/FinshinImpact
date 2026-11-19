"""平台组件面板的组件块

- 一只组件一块，块内按来源、来路、版本、接口包要求与动作逐行摆
- 历史版本与本机安装包各展开一层，展开哪一层记在本块身上
- 动作栏只摆做得到的动作，置灰那颗旁边跟一句下一步
"""

from collections.abc import Callable, Sequence
from enum import StrEnum

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.adapter_catalog import ReleaseRow
from services.env_setup.platform_rows import (
    ComponentBucket,
    ComponentRow,
    ComponentSource,
)
from services.env_setup.platform_state import (
    VersionLine,
    deps_text,
    local_wheels,
    older_versions,
    source_origin,
    update_target,
)
from skin.messages import PlatformMessage
from skin.theme import PLATFORM_DIALOG, ButtonStyle, ObjectName

from .._primitives import clear_layout, make_button, set_margins
from ._platform_flow import install_flow, uninstall_flow
from ._platform_text import (
    action_text,
    name_text,
    origin_text,
    row_note,
    source_text,
    version_line_text,
    version_text,
    wheel_text,
)


class _BlockMode(StrEnum):
    """一块当前展开到哪一层

    - FOLDED 只出读数行
    - HISTORY 展开版本清单
    - WHEELS 展开盘上安装包
    """

    FOLDED = "folded"
    HISTORY = "history"
    WHEELS = "wheels"


class ComponentBlock(QFrame):
    """一只组件一块

    - 装卸跑完面板整片重灌，块跟着重建即收起
    """

    def __init__(
        self,
        host: QWidget,
        row: ComponentRow,
        rows: Sequence[ComponentRow],
        on_done: Callable[[], None],
    ) -> None:
        super().__init__(host)
        self._row = row
        self._rows = rows
        self._on_done = on_done
        self._mode = _BlockMode.FOLDED
        self._target = update_target(rows, row)
        self._note = row_note(rows, row, self._target)
        self.setObjectName(ObjectName.PLATFORM_BLOCK)
        self._lines = QVBoxLayout(self)
        set_margins(self._lines, PLATFORM_DIALOG.block_pad)
        self._rebuild()

    def _rebuild(self) -> None:
        """按当前展开层重摆块内的行

        - 来路那一行只在本机有得取的内容时出，点名取的是哪一版
        """
        clear_layout(self._lines)
        head = QLabel(name_text(self._row), parent=self)
        head.setObjectName(ObjectName.PLATFORM_NAME)
        self._lines.addWidget(head)
        self._add_text(f"{PlatformMessage.LABEL_SOURCE}：{source_text(self._row)}")
        version = self._target.version if self._target is not None else ""
        origin = origin_text(source_origin(self._rows, self._row), version)
        if origin:
            self._add_text(f"{PlatformMessage.LABEL_ORIGIN}：{origin}")
        self._add_text(f"{PlatformMessage.LABEL_VERSION}：{version_text(self._row)}")
        self._add_layer()

        requires = deps_text(self._row)
        if requires:
            self._add_text(f"{PlatformMessage.LABEL_DEPS}：{requires}")
        self._add_actions()

    def _add_layer(self) -> None:
        """摆当前展开层的那几行"""
        if self._mode == _BlockMode.HISTORY:
            self._add_versions(older_versions(self._rows, self._row))
        elif self._mode == _BlockMode.WHEELS:
            for line in local_wheels(self._rows, self._row):
                self._add_target(
                    wheel_text(line, line.blocked, self._note),
                    line.release,
                    line.blocked,
                )

    def _add_versions(self, lines: Sequence[VersionLine]) -> None:
        """逐版摆一行

        - 配一颗装这一版的按钮
        - 本机已装那一版不给按钮
        """
        for line in lines:
            text = version_line_text(line, line.blocked, self._note)
            if line.installed:
                self._add_text(text)
                continue
            self._add_target(text, line.release, line.blocked)

    def _add_actions(self) -> None:
        """动作栏按钮

        - 只摆做得到的动作
        - 更新或安装那颗只在有得装时出，置灰时旁边跟一句下一步
        - 已装包的多一颗卸载，可展开的层各多一颗展开钮
        - 一颗都没有即整行不出
        """
        installable = (
            self._row.release is not None and self._row.bucket != ComponentBucket.LOCAL
        )
        buttons: list[QPushButton] = []
        if installable:
            buttons.append(
                self._install_button(self._target, action_text(self._row), self._note)
            )
        if bool(self._row.platform) and self._row.source == ComponentSource.INSTALLED:
            buttons.append(self._uninstall_button())
        buttons.extend(self._fold_buttons())
        if not buttons:
            return

        holder = QWidget(parent=self)
        pair = QHBoxLayout(holder)
        pair.setContentsMargins(0, 0, 0, 0)
        for button in buttons:
            pair.addWidget(button)
        if installable and self._note:
            pair.addWidget(QLabel(self._note, parent=holder))
        pair.addStretch()
        self._add_pair(f"{PlatformMessage.LABEL_ACTION}：", holder)

    def _fold_buttons(self) -> list[QPushButton]:
        """两层展开按钮

        - 没内容可展开即不出
        """
        buttons: list[QPushButton] = []
        if self._row.release is not None and len(self._row.release.versions) > 1:
            buttons.append(
                self._toggle(_BlockMode.HISTORY, PlatformMessage.BTN_HISTORY)
            )
        if local_wheels(self._rows, self._row):
            buttons.append(self._toggle(_BlockMode.WHEELS, PlatformMessage.BTN_WHEELS))

        return buttons

    def _toggle(self, mode: _BlockMode, text: str) -> QPushButton:
        """一层展开与收起的按钮"""
        button = make_button(
            PlatformMessage.BTN_FOLD if self._mode == mode else text,
            ButtonStyle.OUTLINE,
        )

        def flip() -> None:
            self._mode = _BlockMode.FOLDED if self._mode == mode else mode
            self._rebuild()

        button.clicked.connect(flip)

        return button

    def _add_target(self, text: str, release: ReleaseRow | None, blocked: str) -> None:
        """摆一版可装件

        - 没得装即只摆文本
        """
        if release is None:
            self._add_text(text)
            return

        self._add_pair(
            text,
            self._install_button(release, PlatformMessage.BTN_INSTALL_VERSION, blocked),
        )

    def _install_button(
        self, release: ReleaseRow | None, text: str, blocked: str
    ) -> QPushButton:
        """装这一版的按钮

        - 挡住即置灰，没有这一版即不接动作
        """
        button = make_button(text, ButtonStyle.PRIMARY)
        button.setEnabled(release is not None and not blocked)
        if release is not None:
            button.clicked.connect(lambda: install_flow(self._on_done, [release]))

        return button

    def _uninstall_button(self) -> QPushButton:
        """卸掉这只适配器的那颗"""
        button = make_button(PlatformMessage.BTN_UNINSTALL, ButtonStyle.DANGER)
        button.clicked.connect(
            lambda: uninstall_flow(self.window(), self._on_done, self._row.platform)
        )

        return button

    def _add_text(self, text: str) -> None:
        """整行只有一句文本"""
        self._lines.addWidget(QLabel(text, parent=self))

    def _add_pair(self, text: str, value: QWidget) -> None:
        """一行文本后面跟一只控件"""
        holder = QWidget(parent=self)
        pair = QHBoxLayout(holder)
        pair.setContentsMargins(0, 0, 0, 0)
        pair.addWidget(QLabel(text, parent=holder))
        pair.addWidget(value)
        pair.addStretch()
        self._lines.addWidget(holder)
