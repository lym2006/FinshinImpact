# src/ui/_guide/_conflict.py
"""冲突明细窗

- 定宽小窗逐条列冲突，一行一句
- 句子仍宽过窗内那一列即在行内循环滚，横向一律不出滚动条
- 窗高跟着条数长到最多露的那几行，多出的条目由竖向滚动条接住
- 挂宿主窗当父件，配色与字体随宿主的样式走
- 点开明细的按钮与明细行文案都从这里交出，两类明细走同一只窗
"""

from typing import Any

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtWidgets import (
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.domain import CommandTaken, HelpKey, ManifestKey, PluginClaim
from skin.messages import PluginMessage
from skin.theme import PANEL, ButtonStyle

from .._primitives import MarqueeLabel, ThemedList, make_button


def _fit_rows(rows: ThemedList) -> None:
    """把行宽定成视口实宽

    - 竖向滚动条一出现就吃掉一段宽度，行按实宽决定滚不滚
    """
    for index in range(rows.count()):
        item = rows.item(index)
        hint = item.sizeHint()
        hint.setWidth(rows.viewport().width())
        item.setSizeHint(hint)


def _show_conflicts(parent: QWidget, anchor: QWidget, lines: list[str]) -> None:
    """贴着锚点弹出明细，屏幕下缘放不下即翻到上缘

    - 窗高随条数长到最多露的那几行，装不下的条目由竖向滚动条接住
    """
    popup = QWidget(parent, Qt.WindowType.Popup)
    popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    popup.setFixedWidth(PANEL.conflict_width)
    layout = QVBoxLayout(popup)
    layout.setContentsMargins(0, 0, 0, 0)

    rows = ThemedList()
    rows.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    rows.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    for line in lines:
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setSizeHint(QSize(PANEL.conflict_width, PANEL.row_height))
        rows.addItem(item)
        rows.setItemWidget(item, MarqueeLabel(line))

    # 清单高度按整行给到最多露的那几行，多出来的条目由竖向滚动条接住
    # 视口凑不满整行就露半条再加一条空带，窗框那圈边另加
    height = min(len(lines), PANEL.conflict_rows) * PANEL.row_height
    height += 2 * rows.frameWidth()
    rows.setFixedHeight(height)
    popup.setFixedHeight(height)
    layout.addWidget(rows)

    area = anchor.screen().availableGeometry()
    top = anchor.mapToGlobal(QPoint(0, anchor.height()))
    if top.y() + popup.height() > area.bottom():
        top.setY(anchor.mapToGlobal(QPoint(0, 0)).y() - popup.height())
    top.setX(min(top.x(), area.right() - popup.width()))
    popup.move(top)
    popup.show()
    _fit_rows(rows)


def clash_lines(taken: tuple[CommandTaken, ...], titles: dict[str, str]) -> list[str]:
    """逐条写成一句冲突明细，抢走那一只报显示名，不报目录名"""
    return [
        PluginMessage.CONFLICT_TAKEN.format(cmd=one.cmd, owner=titles[one.owner])
        for one in taken
    ]


def claims_of(manifests: list[dict[str, Any]]) -> list[PluginClaim]:
    """按清单行交出命令名抢占的入参"""
    return [
        PluginClaim(
            name=manifest[ManifestKey.NAME],
            commands=tuple(cmd for cmd, _ in manifest[HelpKey.COMMANDS]),
        )
        for manifest in manifests
    ]


def _command_lines(manifest: dict[str, Any]) -> list[str]:
    """逐条写成一行命令明细，一条都没声明时交一句说明"""
    lines = [
        PluginMessage.COMMAND_LINE.format(cmd=cmd, desc=desc)
        for cmd, desc in manifest[HelpKey.COMMANDS]
    ]
    return lines or [PluginMessage.COMMAND_NONE]


def make_clash_button(parent: QWidget, lines: list[str], label: str) -> QPushButton:
    """勾选位是一颗写明冲突类型的按钮，点开逐条列出被谁拿走"""
    button = make_button(label, ButtonStyle.CONFLICT)
    button.clicked.connect(lambda: _show_conflicts(parent, button, lines))
    return button


def make_command_button(parent: QWidget, manifest: dict[str, Any]) -> QPushButton:
    """行尾一只看命令的按钮，点开逐条列出这份清单声明的命令名与说明

    - 宽度只由样式表给，代码再定一次会被描边顶掉
    """
    button = make_button(PluginMessage.BTN_COMMAND, ButtonStyle.COMMAND)
    lines = _command_lines(manifest)
    button.clicked.connect(lambda: _show_conflicts(parent, button, lines))
    return button
