# src/ui/_guide/_conflict.py
"""冲突明细窗

- 定宽小窗逐条列冲突，一行一句
- 句子仍宽过窗内那一列即在行内循环滚，横向一律不出滚动条
- 窗高跟着条数长，长到上限为止，多出的条目由竖向滚动条接住
- 挂宿主窗当父件，配色与字体随宿主的样式走
"""

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtWidgets import QListWidgetItem, QVBoxLayout, QWidget

from skin.theme import PANEL

from .._primitives import MarqueeLabel, ThemedList


def _fit_rows(rows: ThemedList) -> None:
    """把行宽改成视口实宽

    - 竖向滚动条一出现就吃掉一段宽度，行按实宽决定滚不滚
    """
    for index in range(rows.count()):
        item = rows.item(index)
        hint = item.sizeHint()
        hint.setWidth(rows.viewport().width())
        item.setSizeHint(hint)


def show_conflicts(parent: QWidget, anchor: QWidget, lines: list[str]) -> None:
    """贴着锚点弹出明细，屏幕下缘放不下即翻到上缘

    - 窗高随条数长到上限为止，装不下的条目由竖向滚动条接住
    """
    popup = QWidget(parent, Qt.WindowType.Popup)
    popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    popup.setFixedWidth(PANEL.conflict_width)
    popup.setMaximumHeight(PANEL.conflict_max_height)
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

    # 清单高度按条数给到上限，多出来的条目由竖向滚动条接住
    rows.setFixedHeight(min(len(lines) * PANEL.row_height, PANEL.conflict_max_height))
    layout.addWidget(rows)

    popup.adjustSize()
    area = anchor.screen().availableGeometry()
    top = anchor.mapToGlobal(QPoint(0, anchor.height()))
    if top.y() + popup.height() > area.bottom():
        top.setY(anchor.mapToGlobal(QPoint(0, 0)).y() - popup.height())
    top.setX(min(top.x(), area.right() - popup.width()))
    popup.move(top)
    popup.show()
    _fit_rows(rows)
