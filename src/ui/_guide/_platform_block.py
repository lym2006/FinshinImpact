"""平台组件面板的组件块

- 一只组件一块，块内按来源、版本、接口包要求与动作四行摆
- 动作栏只摆做得到的动作，置灰那颗旁边跟一句下一步
- 按钮点了交回面板重灌读数
"""

from collections.abc import Callable, Sequence

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.env_setup.platform_rows import (
    ComponentBucket,
    ComponentRow,
    ComponentSource,
)
from services.env_setup.platform_state import deps_text, install_blocked
from skin.messages import PlatformMessage
from skin.theme import PLATFORM_DIALOG, ButtonStyle, ObjectName

from .._primitives import make_button, set_margins
from ._platform_flow import install_flow, uninstall_flow

# 来源取值给人看的那句
_SOURCE_TEXT = {
    ComponentSource.TREE: PlatformMessage.SOURCE_TREE,
    ComponentSource.INSTALLED: PlatformMessage.SOURCE_INSTALLED,
    ComponentSource.NONE: PlatformMessage.SOURCE_NONE,
}


def build_block(
    host: QWidget,
    row: ComponentRow,
    rows: Sequence[ComponentRow],
    on_done: Callable[[], None],
) -> QFrame:
    """一只组件一块，行按栏名逐条摆

    - rows 是同一份完整读数，挡装要按接口包那一行判
    """
    block = QFrame(parent=host)
    block.setObjectName(ObjectName.PLATFORM_BLOCK)
    lines = QVBoxLayout(block)
    set_margins(lines, PLATFORM_DIALOG.block_pad)

    head = QLabel(_name_of(row), parent=block)
    head.setObjectName(ObjectName.PLATFORM_NAME)
    lines.addWidget(head)
    for label, value in _fields_of(host, block, row, rows, on_done):
        if isinstance(value, str):
            lines.addWidget(QLabel(f"{label}：{value}", parent=block))
            continue
        pair = QHBoxLayout()
        pair.addWidget(QLabel(f"{label}：", parent=block))
        pair.addWidget(value)
        pair.addStretch()
        lines.addLayout(pair)

    return block


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


def _fields_of(
    host: QWidget,
    block: QFrame,
    row: ComponentRow,
    rows: Sequence[ComponentRow],
    on_done: Callable[[], None],
) -> list[tuple[str, str | QWidget]]:
    """一块之内的行，有目录行的末尾多一条可点的动作行"""
    fields: list[tuple[str, str | QWidget]] = [
        (PlatformMessage.LABEL_SOURCE, _SOURCE_TEXT[row.source]),
        (PlatformMessage.LABEL_VERSION, _version_text(row)),
    ]
    requires = deps_text(row)
    if requires:
        fields.append((PlatformMessage.LABEL_DEPS, requires))

    actions = _actions_of(host, block, row, rows, on_done)
    if actions is not None:
        fields.append((PlatformMessage.LABEL_ACTION, actions))

    return fields


def _actions_of(
    host: QWidget,
    block: QFrame,
    row: ComponentRow,
    rows: Sequence[ComponentRow],
    on_done: Callable[[], None],
) -> QWidget | None:
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
        note = install_blocked(rows, row)
        todo.setEnabled(not note)
        todo.clicked.connect(lambda: install_flow(on_done, [release]))
        buttons.append(todo)
    if bool(row.platform) and row.source == ComponentSource.INSTALLED:
        drop = make_button(PlatformMessage.BTN_UNINSTALL, ButtonStyle.DANGER)
        drop.clicked.connect(lambda: uninstall_flow(host, on_done, row.platform))
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
