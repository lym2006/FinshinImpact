# src/ui/_guide/_panel.py
"""插件设置面板

- 勾选即启用、取消即禁用，保存只写状态与目录指纹
- 命令名被在场插件拿走的行不给勾选框，改挂冲突按钮写明被谁拿走
- 冲突明细里的插件名与命令名都按用户看得见的那份写
- 依赖与资源的安装由启动结算负责，禁用不删已装库
- 清库只走选窗「依赖管理」同步，面板保存无删除动作
"""

from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.domain import (
    BUNDLED_PLUGIN_PRIORITY,
    CommandTaken,
    HelpKey,
    ManifestKey,
    PluginClaim,
    StateKey,
    resolve_claims,
)
from services.env_setup.deps_manifest import (
    catalog_digest,
    load_manifests,
    load_state,
    plugins_roots,
    save_state,
)
from services.env_setup.subprocess_ops import is_pin_installed
from services.env_setup.toolchain import dev_mode
from skin.messages import PluginMessage
from skin.qss import build_bootstrap_qss
from skin.theme import GLOBAL, PANEL, ButtonStyle, ObjectName

from .._lifecycle import ensure_app
from .._primitives import ThemedList, TickedCheckBox, make_button

MODE_AUTO = "auto"  # 自动弹出：保存并启动
MODE_EDIT = "edit"  # 选窗按钮进入：保存回列表

# Qt 自定义数据角色，列表行挂清单 dict
_ROLE_MANIFEST = 0x0100


class _PluginPanelDialog(QDialog):
    """插件选择弹窗"""

    def __init__(self, code: str, *, mode: str = MODE_AUTO) -> None:
        """按实例与来源装配面板"""
        # code 为实例身份码，全程显式传参不读冻结值
        super().__init__()
        self._code = code
        self._mode = mode
        self._manifests: list[dict[str, Any]] = []
        self._items: dict[str, QListWidgetItem] = {}
        self._conflicted: dict[str, tuple[CommandTaken, ...]] = {}
        self._titles: dict[str, str] = {}
        self._build()

    def _build(self) -> None:
        """装配标题、列表与底栏按钮"""
        self.setWindowTitle(PluginMessage.TITLE.format(code=self._code))
        self.setStyleSheet(build_bootstrap_qss())
        self.resize(PANEL.width, PANEL.height)
        self.setMinimumSize(PANEL.min_width, PANEL.min_height)

        layout = QVBoxLayout(self)

        self._list = ThemedList()
        self._build_rows()
        layout.addWidget(self._list)

        buttons = QHBoxLayout()
        save_btn = make_button(
            PluginMessage.BTN_SAVE_START
            if self._mode == MODE_AUTO
            else PluginMessage.BTN_SAVE,
            ButtonStyle.PRIMARY,
        )
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)

        buttons.addStretch()
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

    def _build_rows(self) -> None:
        """按清单与实例状态填充插件行

        - 首屏就按抢占结果定勾选位形态，同一行只拼一遍
        """
        self._list.clear()
        self._manifests = []
        self._items = {}
        self._conflicted = {}
        self._titles = {}
        roots = plugins_roots()
        if not roots:
            return

        enabled = set(load_state(self._code).get(StateKey.ENABLED, []))
        self._manifests = load_manifests(roots)
        self._titles = {
            manifest[ManifestKey.NAME]: manifest[ManifestKey.TITLE]
            or manifest[ManifestKey.NAME]
            for manifest in self._manifests
        }
        _, conflicts = resolve_claims(self._claims(), frozenset(enabled))
        for manifest in self._manifests:
            name = manifest[ManifestKey.NAME]
            taken = conflicts.get(name, ())
            item = QListWidgetItem()

            # item 默认高 25，行 widget 高 44，不显式对齐则选中高亮画在错位矩形上
            item.setSizeHint(QSize(0, PANEL.row_height))
            item.setData(_ROLE_MANIFEST, manifest)
            self._list.addItem(item)
            self._list.setItemWidget(
                item, self._make_row(manifest, name in enabled, taken)
            )
            self._items[name] = item
            self._conflicted[name] = taken

    def _make_row(
        self, manifest: dict[str, Any], checked: bool, taken: tuple[CommandTaken, ...]
    ) -> QWidget:
        """拼插件单行三列控件"""
        bundled = manifest[ManifestKey.NAME] in BUNDLED_PLUGIN_PRIORITY
        title = manifest[ManifestKey.TITLE] or manifest[ManifestKey.NAME]
        middle = manifest[ManifestKey.SUMMARY]

        row = QWidget()
        row.setFixedHeight(PANEL.row_height)
        row.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(
            PANEL.row_pad_h, PANEL.row_pad_v, PANEL.row_pad_h, PANEL.row_pad_v
        )
        row_layout.setSpacing(PANEL.col_gap)

        name_label = QLabel(title)
        name_label.setFixedWidth(PANEL.name_width)
        desc_label = QLabel(middle)
        status = QLabel(self._status_label(manifest))
        status.setFixedWidth(PANEL.status_width)
        status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if bundled:
            # 随包插件无勾选框，勾选位以"必选"文字占宽对齐
            slot: QWidget = QLabel(PluginMessage.ROW_BUNDLED)
            slot.setObjectName(ObjectName.ROW_BUNDLED_MARK)
        elif taken:
            slot = self._make_conflict_button(taken)
        else:
            check = TickedCheckBox(GLOBAL.check_size, PANEL.col_gap)
            check.setChecked(checked)
            check.clicked.connect(self._apply_clashes)
            slot = check
        slot.setFixedWidth(PANEL.check_width)

        row_layout.addWidget(slot, alignment=Qt.AlignmentFlag.AlignVCenter)
        row_layout.addWidget(name_label)
        row_layout.addWidget(desc_label, stretch=1)
        row_layout.addWidget(status)
        return row

    def _make_conflict_button(self, taken: tuple[CommandTaken, ...]) -> QPushButton:
        """勾选位换成冲突按钮，点开即列出每条命令名被谁拿走

        - 抢走那一只报这一行显示的名字，不报目录名
        """
        button = make_button(PluginMessage.BTN_CONFLICT, ButtonStyle.CONFLICT)
        menu = QMenu(button)
        for one in taken:
            action = QAction(
                PluginMessage.CONFLICT_TAKEN.format(
                    cmd=one.cmd, owner=self._titles[one.owner]
                ),
                menu,
            )
            action.setEnabled(False)
            menu.addAction(action)
        button.setMenu(menu)
        return button

    def _claims(self) -> list[PluginClaim]:
        """按清单行交出命令名抢占的入参"""
        return [
            PluginClaim(
                name=manifest[ManifestKey.NAME],
                commands=manifest[HelpKey.COMMANDS],
            )
            for manifest in self._manifests
        ]

    def _apply_clashes(self) -> None:
        """按当前勾选重算命令名抢占

        - 只重拼勾选位或冲突明细有变的行，行数与行高不动，滚动位置不变
        """
        _, conflicts = resolve_claims(self._claims(), frozenset(self._checked_names()))
        for manifest in self._manifests:
            name = manifest[ManifestKey.NAME]
            if name in BUNDLED_PLUGIN_PRIORITY:
                continue
            taken = conflicts.get(name, ())
            if taken == self._conflicted[name]:
                continue
            item = self._items[name]
            self._list.setItemWidget(
                item, self._make_row(manifest, self._row_checked(item), taken)
            )
            self._conflicted[name] = taken

    def _status_label(self, manifest: dict[str, Any]) -> str:
        """计算单插件状态标签"""
        missing = sum(
            1 for pin in manifest[ManifestKey.DEPS] if not is_pin_installed(pin)
        )
        if not missing:
            return PluginMessage.STATUS_INSTALLED
        if dev_mode():
            return PluginMessage.STATUS_DEV_SKIP
        return PluginMessage.STATUS_MISSING.format(count=missing)

    def _row_checked(self, item: QListWidgetItem) -> bool:
        """取列表项所在行的复选框勾选态"""
        widget = self._list.itemWidget(item)
        check = widget.findChild(QCheckBox) if widget else None
        return bool(check and check.isChecked())

    def _checked_names(self) -> list[str]:
        """取当前勾选的表外插件名"""
        names: list[str] = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            manifest = item.data(_ROLE_MANIFEST)
            if (
                not isinstance(manifest, dict)
                or manifest[ManifestKey.NAME] in BUNDLED_PLUGIN_PRIORITY
            ):
                continue
            if self._row_checked(item):
                names.append(manifest[ManifestKey.NAME])
        return names

    def _on_save(self) -> None:
        """保存启用集与目录指纹"""
        enabled = self._checked_names()
        roots = plugins_roots()
        catalog = catalog_digest(load_manifests(roots)) if roots else ""
        save_state(self._code, enabled, catalog)
        self.accept()


def open_panel(code: str, *, mode: str = MODE_AUTO) -> bool:
    """打开面板并返回是否保存

    - 空身份码直接拒绝，不打开面板
    """
    if not code:
        raise ValueError(PluginMessage.PANEL_NEED_CODE)
    ensure_app()
    dialog = _PluginPanelDialog(code, mode=mode)
    return bool(dialog.exec())
