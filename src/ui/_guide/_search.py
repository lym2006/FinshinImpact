# src/ui/_guide/_search.py
"""插件行的搜索件

- 一只输入框配一档筛选，每敲一个字符当场筛一次
- 只切每行显隐，不动勾选也不动行序，清空即全显
- 一只都没命中时在清单下方顶一句提示
"""

from typing import Any

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from finshin_sdk.domain import HelpKey, ManifestKey
from skin.messages import PluginMessage

from .._primitives import ThemedList, make_combo

# 筛选档，决定比哪一列
_SCOPE_ALL = "all"
_SCOPE_NAME = "name"
_SCOPE_CMD = "cmd"

# 行上挂最小清单的数据角色
ROLE_MANIFEST = 0x0100

# 命令名的两种写法，面板上带斜杠显示，输入时带不带都要命中
_CMD_MARKS = ("", "/")


def _matches(manifest: dict[str, Any], query: str, scope: str) -> bool:
    """判这一行留不留

    - 不分大小写，子串命中即留
    - 名字一列比的是面板上看得见的显示名，没填标题即目录名
    """
    display = (manifest[ManifestKey.TITLE] or manifest[ManifestKey.NAME]).lower()
    name_ok = scope != _SCOPE_CMD and query in display
    cmd_ok = scope != _SCOPE_NAME and any(query in one for one in _cmd_forms(manifest))
    return name_ok or cmd_ok


def _cmd_forms(manifest: dict[str, Any]) -> list[str]:
    """交出每条命令名的带斜杠与不带斜杠两种写法"""
    return [
        f"{mark}{cmd}".lower()
        for cmd, _ in manifest[HelpKey.COMMANDS]
        for mark in _CMD_MARKS
    ]


class _PluginSearch(QWidget):
    """搜索输入框、筛选档与空命中提示三件"""

    def __init__(self, rows: ThemedList) -> None:
        """接上要筛的清单，行上的最小清单按 ROLE_MANIFEST 取

        - 清单由装配入口创建，本件只切每行的显隐
        """
        super().__init__()
        self._rows = rows
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(PluginMessage.SEARCH_PLACEHOLDER)
        self._edit.setClearButtonEnabled(True)
        self._scope = make_combo(
            [
                (_SCOPE_ALL, PluginMessage.SEARCH_SCOPE_ALL),
                (_SCOPE_NAME, PluginMessage.SEARCH_SCOPE_NAME),
                (_SCOPE_CMD, PluginMessage.SEARCH_SCOPE_CMD),
            ]
        )
        self._tip = QLabel(PluginMessage.SEARCH_EMPTY)
        self._tip.setVisible(False)

        line = QHBoxLayout(self)
        line.addWidget(self._edit)
        line.addWidget(self._scope)
        self._edit.textChanged.connect(self.refresh)
        self._scope.currentIndexChanged.connect(self.refresh)

    def mount(self, layout: QVBoxLayout) -> None:
        """把搜索行插到清单上方、空命中提示接到清单下方"""
        index = layout.indexOf(self._rows)
        layout.insertWidget(index, self)
        layout.insertWidget(index + 2, self._tip)

    def refresh(self) -> None:
        """按输入串与档位切每行显隐

        - 空串即整表恢复显示，勾选态本就没动过
        - 隐藏行仍算在启用集里，保存按整张表提交
        - 行上挂的控件跟着行一起隐，只隐行会盖住顶行
        """
        query = self._edit.text().strip().lower()
        scope = self._scope.currentData()
        hits = 0
        for index in range(self._rows.count()):
            item = self._rows.item(index)
            keep = not query or _matches(item.data(ROLE_MANIFEST), query, scope)
            item.setHidden(not keep)
            widget = self._rows.itemWidget(item)
            if widget is not None:
                widget.setHidden(not keep)
            hits += int(keep)
        self._tip.setVisible(hits == 0)


def build_searchable_list(layout: QVBoxLayout) -> tuple[ThemedList, _PluginSearch]:
    """装配可搜索的插件清单，交出清单与搜索件

    - 清单、搜索行与空命中提示按这个顺序进布局
    - 行内容仍由调用方填，重拼行之后要叫搜索件补筛一次
    """
    rows = ThemedList()
    layout.addWidget(rows)
    search = _PluginSearch(rows)
    search.mount(layout)
    return rows, search
