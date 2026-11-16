"""平台组件面板的组件块

- 一只组件一块，块内按来源、版本、接口包要求与动作四行摆
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
    ComponentOrigin,
    VersionLine,
    WheelLine,
    deps_text,
    install_blocked,
    local_wheels,
    older_versions,
    source_origin,
)
from skin.messages import PlatformMessage
from skin.theme import PLATFORM_DIALOG, ButtonStyle, ObjectName

from .._primitives import clear_layout, make_button, set_margins
from ._platform_flow import install_flow, uninstall_flow

# 来源取值给人看的那句
_SOURCE_TEXT = {
    ComponentSource.TREE_INSTALLED: PlatformMessage.SOURCE_TREE_INSTALLED,
    ComponentSource.TREE_ONLY: PlatformMessage.SOURCE_TREE_ONLY,
    ComponentSource.INSTALLED: PlatformMessage.LOCAL_INSTALLED,
    ComponentSource.NONE: PlatformMessage.SOURCE_NONE,
}

# 来路取值给人看的那句，没得取的档位不进表
_ORIGIN_TEXT = {
    ComponentOrigin.WHEEL: PlatformMessage.ORIGIN_WHEEL,
    ComponentOrigin.CATALOG: PlatformMessage.ORIGIN_CATALOG,
    ComponentOrigin.TREE: PlatformMessage.ORIGIN_TREE,
}


class _BlockMode(StrEnum):
    """一块当前展开到哪一层

    - FOLDED 只出四行读数
    - HISTORY 版本清单那一层
    - WHEELS 盘上件那一层
    """

    FOLDED = "folded"
    HISTORY = "history"
    WHEELS = "wheels"


class ComponentBlock(QFrame):
    """一只组件一块

    - 装卸跑完面板整片重灌，块跟着重建即收起
    - rows 是同一份完整读数，挡装要按接口包那一行判
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
        self._note = install_blocked(rows, row)
        self.setObjectName(ObjectName.PLATFORM_BLOCK)
        self._lines = QVBoxLayout(self)
        set_margins(self._lines, PLATFORM_DIALOG.block_pad)
        self._rebuild()

    def _rebuild(self) -> None:
        """按当前展开层重摆块内的行"""
        clear_layout(self._lines)
        head = QLabel(_name_of(self._row), parent=self)
        head.setObjectName(ObjectName.PLATFORM_NAME)
        self._lines.addWidget(head)
        self._add_text(
            f"{PlatformMessage.LABEL_SOURCE}：{_SOURCE_TEXT[self._row.source]}"
        )
        origin = source_origin(self._row)
        if origin in _ORIGIN_TEXT:
            self._add_text(f"{PlatformMessage.LABEL_ORIGIN}：{_ORIGIN_TEXT[origin]}")
        self._add_text(f"{PlatformMessage.LABEL_VERSION}：{_version_text(self._row)}")
        self._add_layer()

        requires = deps_text(self._row)
        if requires:
            self._add_text(f"{PlatformMessage.LABEL_DEPS}：{requires}")
        self._add_actions()

    def _add_layer(self) -> None:
        """展开层的那几行，没展开即不出"""
        if self._mode == _BlockMode.HISTORY:
            self._add_versions(older_versions(self._row))
        elif self._mode == _BlockMode.WHEELS:
            for line in local_wheels(self._row):
                self._add_text(_wheel_text(line))

    def _add_versions(self, lines: Sequence[VersionLine]) -> None:
        """版本清单的那几版，逐版给一颗装它那版的钮

        - 本机已装那一版不给按钮
        - 挡着装的那句在整层末尾只报一次
        """
        for line in lines:
            text = _version_line_text(line)
            if line.installed:
                self._add_text(text)
                continue
            self._add_pair(
                text,
                self._install_button(line.release, PlatformMessage.BTN_INSTALL_VERSION),
            )
        if self._note:
            self._add_text(self._note)

    def _add_actions(self) -> None:
        """动作栏的按钮，只摆做得到的动作

        - 更新或安装那颗只在有得装时出，置灰时旁边跟一句下一步
        - 已装包的再多一颗卸载，可展开的层再多两颗
        - 一颗都没有即整行不出
        """
        release = self._row.release
        installable = release is not None and self._row.bucket != ComponentBucket.LOCAL
        wanted = (
            PlatformMessage.BTN_INSTALL
            if not self._row.installed
            else PlatformMessage.BTN_APPLY
        )
        buttons: list[QPushButton] = []
        if installable and release is not None:
            buttons.append(self._install_button(release, wanted))
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
        """展开两层的那两颗，没内容可展开即不出"""
        buttons: list[QPushButton] = []
        if self._row.release is not None and len(self._row.release.versions) > 1:
            buttons.append(
                self._toggle(_BlockMode.HISTORY, PlatformMessage.BTN_HISTORY)
            )
        if local_wheels(self._row):
            buttons.append(self._toggle(_BlockMode.WHEELS, PlatformMessage.BTN_WHEELS))

        return buttons

    def _toggle(self, mode: _BlockMode, text: str) -> QPushButton:
        """展开那一层的那颗钮，已展开即写成收起"""
        button = make_button(
            PlatformMessage.BTN_FOLD if self._mode == mode else text,
            ButtonStyle.SECONDARY,
        )
        button.clicked.connect(lambda: self._fold(mode))

        return button

    def _fold(self, mode: _BlockMode) -> None:
        """同一颗再点即收起"""
        self._mode = _BlockMode.FOLDED if self._mode == mode else mode
        self._rebuild()

    def _install_button(self, release: ReleaseRow, text: str) -> QPushButton:
        """装那一版的那颗，接口包挡着即置灰"""
        button = make_button(text, ButtonStyle.PRIMARY)
        button.setEnabled(not self._note)
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


def _version_line_text(line: VersionLine) -> str:
    """版本清单里那一版的一行，版本号后面跟本机来路"""
    note = ""
    if line.installed:
        note = PlatformMessage.LOCAL_INSTALLED
    elif line.cached:
        note = PlatformMessage.WHEEL_CACHED

    return " ".join(part for part in (line.release.version, note) if part)


def _wheel_text(line: WheelLine) -> str:
    """盘上那一份件的一行，对不上目录任何一版即没有权威指纹可核"""
    template = (
        PlatformMessage.WHEEL_LISTED if line.listed else PlatformMessage.WHEEL_STRAY
    )
    return template.format(name=line.file_name)
