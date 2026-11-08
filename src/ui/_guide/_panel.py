# src/ui/_guide/_panel.py
"""插件设置面板

- 勾选即启用、取消即禁用，保存只写状态与目录指纹
- 命令名被在场插件拿走的行不给勾选框，改挂冲突按钮写明被谁拿走
- 名字撞上先读到的那份插件即整只不装载，面板上单开一行写明被谁顶掉
- 冲突明细窗定宽，一行一句，放不下即在行内循环滚
- 冲突明细里的插件名与命令名都按用户看得见的那份写
- 依赖与资源的安装由启动结算负责，禁用不删已装库
- 清库只走选窗「依赖管理」同步，面板保存无删除动作
"""

from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
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
    shadowed_manifests,
)
from services.env_setup.subprocess_ops import is_pin_installed
from services.env_setup.toolchain import dev_mode
from skin.messages import PluginMessage
from skin.qss import build_bootstrap_qss
from skin.theme import GLOBAL, PANEL, ButtonStyle, ObjectName

from .._lifecycle import ensure_app
from .._primitives import MarqueeLabel, TickedCheckBox, make_button
from ._conflict import show_conflicts
from ._search import ROLE_MANIFEST, build_searchable_list

MODE_AUTO = "auto"  # 自动弹出：保存并启动
MODE_EDIT = "edit"  # 选窗按钮进入：保存回列表

# Qt 自定义数据角色，行上挂冲突明细与顶掉它的那份插件名
_ROLE_LINES = 0x0101
_ROLE_NAME_TAKEN = 0x0102


def _status_label(manifest: dict[str, Any]) -> str:
    """算一行行尾的状态标签

    - 缺库数按这份清单声明的依赖逐条查已装
    - 开发模式只报话不动环境
    """
    missing = sum(1 for pin in manifest[ManifestKey.DEPS] if not is_pin_installed(pin))
    if not missing:
        return PluginMessage.STATUS_INSTALLED
    if dev_mode():
        return PluginMessage.STATUS_DEV_SKIP
    return PluginMessage.STATUS_MISSING.format(count=missing)


class _PluginPanelDialog(QDialog):
    """插件选择弹窗"""

    def __init__(self, code: str, *, mode: str = MODE_AUTO) -> None:
        """按实例与来源装配面板"""
        # code 为实例身份码，全程显式传参不读冻结值
        super().__init__()
        self._code = code
        self._mode = mode
        self._manifests: list[dict[str, Any]] = []
        self._titles: dict[str, str] = {}
        self._build()

    def _build(self) -> None:
        """装配标题、列表与底栏按钮"""
        self.setWindowTitle(PluginMessage.TITLE.format(code=self._code))
        self.setStyleSheet(build_bootstrap_qss())
        self.resize(PANEL.width, PANEL.height)
        self.setMinimumSize(PANEL.min_width, PANEL.min_height)

        layout = QVBoxLayout(self)

        self._list, self._search = build_searchable_list(layout)
        self._build_rows()

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
        - 被同名顶掉的那一份排在整张清单末尾
        """
        self._list.clear()
        self._manifests = []
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
            lines = self._lines(conflicts.get(name, ()))
            self._add_row(manifest, name in enabled, lines)
        for loser, winner in shadowed_manifests(roots):
            clash = [PluginMessage.CONFLICT_NAME.format(owner=self._titles[winner])]
            self._add_row(loser, False, clash, winner, PluginMessage.BTN_DUP_NAME)

    def _add_row(
        self,
        manifest: dict[str, Any],
        checked: bool,
        lines: list[str],
        taken_by: str = "",
        label: str = PluginMessage.BTN_CONFLICT,
    ) -> None:
        """拼一行挂进清单，冲突明细、按钮名与顶掉它的那份插件名都随行走"""
        item = QListWidgetItem()

        # item 默认高 25，行 widget 高 44，不显式对齐则选中高亮画在错位矩形上
        item.setSizeHint(QSize(0, PANEL.row_height))
        item.setData(ROLE_MANIFEST, manifest)
        item.setData(_ROLE_LINES, lines)
        item.setData(_ROLE_NAME_TAKEN, taken_by)
        self._list.addItem(item)
        self._list.setItemWidget(item, self._make_row(manifest, checked, lines, label))

    def _make_row(
        self,
        manifest: dict[str, Any],
        checked: bool,
        lines: list[str],
        label: str = PluginMessage.BTN_CONFLICT,
    ) -> QWidget:
        """拼插件单行三列控件

        - 名称与说明由插件作者自写，宽度放不下即循环滚，全文挂悬浮提示
        """
        bundled = manifest[ManifestKey.NAME] in BUNDLED_PLUGIN_PRIORITY
        title = manifest[ManifestKey.TITLE] or manifest[ManifestKey.NAME]

        row = QWidget()
        row.setFixedHeight(PANEL.row_height)
        row.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(
            PANEL.row_pad_h, PANEL.row_pad_v, PANEL.row_pad_h, PANEL.row_pad_v
        )
        row_layout.setSpacing(PANEL.col_gap)

        name_label = MarqueeLabel(title)
        name_label.setFixedWidth(PANEL.name_width)
        desc_label = MarqueeLabel(manifest[ManifestKey.SUMMARY])
        status = QLabel(_status_label(manifest))
        status.setFixedWidth(PANEL.status_width)
        status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if lines:
            slot: QWidget = self._make_conflict_button(lines, label)
        elif bundled:
            # 随包插件无勾选框，勾选位以"必选"文字占宽对齐
            slot = QLabel(PluginMessage.ROW_BUNDLED)
            slot.setObjectName(ObjectName.ROW_BUNDLED_MARK)
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

    def _make_conflict_button(self, lines: list[str], label: str) -> QPushButton:
        """勾选位是一颗写明冲突类型的按钮，点开逐条列出被谁拿走"""
        button = make_button(label, ButtonStyle.CONFLICT)
        button.clicked.connect(lambda: show_conflicts(self, button, lines))
        return button

    def _lines(self, taken: tuple[CommandTaken, ...]) -> list[str]:
        """逐条写成一句明细，抢走那一只报这一行显示的名字，不报目录名"""
        return [
            PluginMessage.CONFLICT_TAKEN.format(
                cmd=one.cmd, owner=self._titles[one.owner]
            )
            for one in taken
        ]

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

        - 只重拼明细有变的行，行数与行高不动，滚动位置不变
        - 随包行与名字顶掉的行不参与重算，两种都不跟勾选走
        - 重拼会把行上那件换成新控件，交搜索件按当前输入补一次筛
        """
        _, conflicts = resolve_claims(self._claims(), frozenset(self._checked_names()))
        for row in range(self._list.count()):
            item = self._list.item(row)
            manifest = item.data(ROLE_MANIFEST)
            name = manifest[ManifestKey.NAME]
            if item.data(_ROLE_NAME_TAKEN) or name in BUNDLED_PLUGIN_PRIORITY:
                continue
            lines = self._lines(conflicts.get(name, ()))
            if lines == item.data(_ROLE_LINES):
                continue
            self._list.setItemWidget(
                item, self._make_row(manifest, self._row_checked(item), lines)
            )
            item.setData(_ROLE_LINES, lines)
        self._search.refresh()

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
            manifest = item.data(ROLE_MANIFEST)
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
