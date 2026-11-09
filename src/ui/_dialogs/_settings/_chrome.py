# src/ui/_dialogs/_settings/_chrome.py
"""骨架装配

- 构建根布局、左侧大类列表、上排页签与底部按钮条
- 承载 EDIT 与 SETUP 两模式的原地拆装
"""

from collections.abc import Callable

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from finshin_sdk.domain import ConfigGroup, ConfigKey, ConfigSection
from skin.theme import GLOBAL, SETTINGS_DIALOG, ButtonStyle, ObjectName
from utils.config.models import AppSchema, TabSchema
from utils.network import uses_configured_proxy

from ..._primitives import make_button
from .._persona import PersonaPreviewRow
from ._field import FieldBuilder


def _clear_layout(layout: QHBoxLayout) -> None:
    """清空按钮条

    - 逐项移除控件交给垃圾回收
    """
    # 容器自身由调用方 removeItem
    while layout.count():
        item = layout.takeAt(0)
        if item and (widget := item.widget()):
            widget.deleteLater()


class ChromeBuilder:
    """骨架装配器

    - 持有根布局、大类导航、按钮条引用，供弹窗跨模式续用
    - 页签标题与大类文案按出错段原地挂 ⚠
    """

    def __init__(
        self,
        host: QWidget,
        fields: FieldBuilder,
        errors: dict[str, str],
        error_qss: str,
        error_font: QFont,
        on_exit: Callable[[], None],
        on_cancel: Callable[[], None],
        on_save: Callable[[], None],
    ) -> None:
        self._host = host
        self._fields = fields
        self._errors = errors
        self._error_qss = error_qss
        self._error_font = error_font
        self._on_exit = on_exit
        self._on_cancel = on_cancel
        self._on_save = on_save

        # 根布局/按钮条/提示行引用：原地切模式只拆可再生部件，表单永不重建
        self.root_layout: QVBoxLayout | None = None
        self.bottom_layout: QHBoxLayout | None = None
        self.tip_labels: list[QLabel] = []

        # 导航引用：复验结果原地刷新用（免关窗重开的闪烁）
        # 页段 -> (大类, 页签序号, 无标记标题)，大类 -> (列表项, 无标记文案)
        self._group_tabs: dict[ConfigGroup, QTabWidget] = {}
        self._tab_refs: dict[str, tuple[ConfigGroup, int, str]] = {}
        self._category_items: dict[ConfigGroup, tuple[QListWidgetItem, str]] = {}
        self._categories = QListWidget()
        self._pages = QStackedWidget()
        self.save_btn: QPushButton | None = None
        self.save_text: str = ""
        self.proxy_row: QWidget | None = None

    def build(
        self, schema: AppSchema, is_setup: bool, error_sections: set[str]
    ) -> None:
        """构建界面"""
        root_layout = QVBoxLayout(self._host)
        self.root_layout = root_layout
        root_layout.setContentsMargins(
            *([SETTINGS_DIALOG.input_padding_h, SETTINGS_DIALOG.input_padding_v] * 2)
        )
        root_layout.setSpacing(SETTINGS_DIALOG.tab_spacing)

        # SETUP 提示：出错标签页带 ⚠，出错字段标题标红
        if is_setup:
            self.tip_labels = self._make_tips()
            for tip in self.tip_labels:
                root_layout.addWidget(tip)

        root_layout.addLayout(self._build_nav(schema), stretch=1)
        self.set_error_marks(error_sections)
        self.bottom_layout = self._build_bottom_buttons(is_setup)
        root_layout.addLayout(self.bottom_layout)

    def rebuild(self, is_setup: bool) -> None:
        """拆建提示行与底部按钮条"""
        if self.root_layout is None:
            return
        for tip in self.tip_labels:
            self.root_layout.removeWidget(tip)
            tip.deleteLater()
        self.tip_labels.clear()
        if self.bottom_layout is not None:
            self.root_layout.removeItem(self.bottom_layout)
            _clear_layout(self.bottom_layout)
        if is_setup:
            self.tip_labels = self._make_tips()
            self.root_layout.insertWidget(0, self.tip_labels[0])
            self.root_layout.insertWidget(1, self.tip_labels[1])
        self.bottom_layout = self._build_bottom_buttons(is_setup)
        self.root_layout.addLayout(self.bottom_layout)

    def _build_nav(self, schema: AppSchema) -> QHBoxLayout:
        """装配左侧大类与右侧上排页签

        - 段按 domain 表顺序归组，大类首次出现即定列表行序
        - 一个大类一本页签，切大类只换堆叠页，已填内容不重建
        """
        groups: dict[ConfigGroup, list[TabSchema]] = {}
        for tab in schema:
            groups.setdefault(tab.group, []).append(tab)

        self._categories.setObjectName(ObjectName.CATEGORY_LIST)
        self._categories.setFixedWidth(SETTINGS_DIALOG.category_width)

        for group, tabs in groups.items():
            title = tabs[0].group_title
            item = QListWidgetItem(title)
            self._categories.addItem(item)
            self._category_items[group] = (item, title)

            group_tabs = QTabWidget()
            for index, tab in enumerate(tabs):
                group_tabs.addTab(self._create_tab(tab), tab.title)
                self._tab_refs[tab.section] = (group, index, tab.title)
            self._group_tabs[group] = group_tabs
            self._pages.addWidget(group_tabs)

        self._categories.currentRowChanged.connect(self._pages.setCurrentIndex)
        self._categories.setCurrentRow(0)

        nav = QHBoxLayout()
        nav.setSpacing(SETTINGS_DIALOG.category_spacing)
        nav.addWidget(self._categories)
        nav.addWidget(self._pages, stretch=1)
        return nav

    def set_error_marks(self, error_sections: set[str]) -> None:
        """按出错段增撤 ⚠ 标记

        - 出错页签挂标记，其所属大类跟着挂
        - 只换标题文字，控件与已填内容不动
        """
        bad_groups: set[ConfigGroup] = set()
        for section, (group, index, title) in self._tab_refs.items():
            marked = section in error_sections
            if marked:
                bad_groups.add(group)
            self._group_tabs[group].setTabText(
                index, f"{'⚠ ' if marked else ''}{title}"
            )
        for group, (item, title) in self._category_items.items():
            mark = "⚠ " if group in bad_groups else ""
            item.setText(f"{mark}{title}")

    def lock_nav(self, locked: bool) -> None:
        """校验期间锁住两级导航，防换页重入"""
        self._categories.setEnabled(not locked)
        for group_tabs in self._group_tabs.values():
            group_tabs.setEnabled(not locked)

    def _make_tips(self) -> list[QLabel]:
        """构造 SETUP 模式的两行提示"""
        tip_label = QLabel(SETTINGS_DIALOG.setup_tip)
        tip_label.setStyleSheet(self._error_qss)
        tip_label.setFont(self._error_font)
        hint_label = QLabel(SETTINGS_DIALOG.setup_hint)
        hint_label.setStyleSheet(self._error_qss)
        return [tip_label, hint_label]

    def _create_tab(self, tab_schema: TabSchema) -> QWidget:
        """创建一个 Tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAutoFillBackground(False)
        container = QWidget()
        container.setObjectName(ObjectName.TAB_CONTAINER)
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(SETTINGS_DIALOG.tab_spacing)
        label_width = self._fields.label_width_of(tab_schema.fields)
        rows: dict[str, QWidget] = {}
        for field in tab_schema.fields:
            row = self._fields.build(
                field, tab_schema.section, self._errors, label_width
            )
            rows[field.key] = row
            main_layout.addWidget(row)
        self._mount_persona_row(tab_schema.section, main_layout, label_width)
        self._mount_proxy_mode_lock(tab_schema.section, rows)
        main_layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _mount_proxy_mode_lock(self, section: str, rows: dict[str, QWidget]) -> None:
        """代理项随模式显隐

        - 仅系统代理与仅直连两档用不到代理项，整行隐藏
        - 标题、输入框与恢复钮同消，值保留在控件里切回即现
        - 两个控件缺一即不接线，缺件说明字段表已改键
        """
        if section != ConfigSection.PROXY:
            return
        inputs = self._fields.inputs
        mode_combo = inputs.get(ConfigKey.PROXY_MODE)
        proxy_row = rows.get(ConfigKey.PROXY)
        if not isinstance(mode_combo, QComboBox) or proxy_row is None:
            return
        self.proxy_row = proxy_row

        def sync(mode_value: object) -> None:
            proxy_row.setVisible(uses_configured_proxy(str(mode_value)))

            # 切换即重估全部恢复钮，否则按钮显隐停在开窗时的旧值
            self._fields.refresh_resets()

        mode_combo.currentIndexChanged.connect(lambda: sync(mode_combo.currentData()))
        sync(mode_combo.currentData())

    def _mount_persona_row(
        self,
        section: str,
        layout: QVBoxLayout,
        label_width: int,
    ) -> None:
        """人设入口行挂载

        - 主人输入行取不到或控件类型不符即不挂载，缺件说明字段表已改键
        """
        if section != ConfigSection.CHORE:
            return
        owner = self._fields.inputs.get(ConfigKey.OWNER)
        if owner is None:
            return

        row = PersonaPreviewRow(label_width)
        if not row.bind(owner):
            return
        layout.addWidget(row)

    def _build_bottom_buttons(self, is_setup: bool) -> QHBoxLayout:
        """按模式构建底部按钮"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(GLOBAL.radius)
        btn_layout.addStretch()

        if is_setup:
            btn_exit = QPushButton(SETTINGS_DIALOG.exit_text)
            btn_exit.clicked.connect(self._on_exit)
            btn_finish = make_button(SETTINGS_DIALOG.finish_text, ButtonStyle.PRIMARY)
            btn_finish.setMinimumWidth(SETTINGS_DIALOG.finish_btn_min_width)

            # 发信号而非 accept：校验通过才关窗，失败则原窗保留已填内容
            btn_finish.clicked.connect(self._on_save)
            self.save_btn, self.save_text = btn_finish, SETTINGS_DIALOG.finish_text
            btn_layout.addWidget(btn_exit)
            btn_layout.addWidget(btn_finish)
            return btn_layout

        btn_cancel = QPushButton(SETTINGS_DIALOG.cancel_text)
        btn_cancel.clicked.connect(self._on_cancel)
        btn_save = make_button(SETTINGS_DIALOG.save_text, ButtonStyle.PRIMARY)
        btn_save.clicked.connect(self._on_save)
        self.save_btn, self.save_text = btn_save, SETTINGS_DIALOG.save_text
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        return btn_layout
