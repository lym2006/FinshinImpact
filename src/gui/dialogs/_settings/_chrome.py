# src/gui/dialogs/_settings/_chrome.py
"""骨架装配

- 构建根布局、标签页与底部按钮条
- 承载 EDIT 与 SETUP 两模式的原地拆装
"""

from collections.abc import Callable

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils.config.models import AppSchema, PersonaKey, TabSchema

from ..._theme import GLOBAL, SETTINGS_DIALOG
from ._field import FieldBuilder
from ._persona import PersonaPreviewRow


def _clear_layout(layout: QHBoxLayout) -> None:
    """腾空按钮条

    - 逐项摘控件交还 GC
    """
    # 容器自身由调用方 removeItem
    while layout.count():
        item = layout.takeAt(0)
        if item and (widget := item.widget()):
            widget.deleteLater()


class ChromeBuilder:
    """骨架装配器

    - 持有根布局、页签与按钮条引用，供弹窗跨模式复用
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

        # 页签与按钮引用：复验结果原地刷新用（免关窗重开的闪烁）
        self.tabs: QTabWidget | None = None
        self.tab_titles: dict[str, tuple[int, str]] = {}
        self.save_btn: QPushButton | None = None
        self.save_text: str = ""

    def build(
        self, schema: AppSchema, is_setup: bool, error_namespaces: set[str]
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

        tabs = QTabWidget()
        for index, tab_schema in enumerate(schema):
            tabs.addTab(
                self._create_tab(tab_schema),
                self._tab_title(tab_schema, error_namespaces),
            )
            self.tab_titles[tab_schema.namespace] = (index, tab_schema.title)
        self.tabs = tabs
        root_layout.addWidget(tabs)
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

    @staticmethod
    def _tab_title(tab_schema: TabSchema, error_namespaces: set[str]) -> str:
        """页签标题

        - 出错页前缀 ⚠
        """
        mark = "⚠ " if tab_schema.namespace in error_namespaces else ""
        return f"{mark}{tab_schema.title}"

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
        container.setObjectName(SETTINGS_DIALOG.tab_container_name)
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(SETTINGS_DIALOG.tab_spacing)
        label_width = self._fields.label_width_of(tab_schema.fields)
        rows: dict[str, QWidget] = {}
        for field in tab_schema.fields:
            row = self._fields.build(
                field, tab_schema.namespace, self._errors, label_width
            )
            rows[field.key] = row
            main_layout.addWidget(row)
        self._mount_persona_preview(
            tab_schema.namespace, main_layout, label_width, rows
        )
        main_layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _mount_persona_preview(
        self,
        namespace: str,
        layout: QVBoxLayout,
        label_width: int,
        rows: dict[str, QWidget],
    ) -> None:
        """人设预览挂载

        - 三个联动控件缺一不挂，缺件说明模板已改键
        - 人设输入行与预览按钮行共槽堆叠，切换勾选态整页等高不跳动
        """
        if namespace != PersonaKey.NAMESPACE:
            return
        inputs = self._fields.inputs
        use_file = inputs.get(PersonaKey.USE_FILE)
        personality = inputs.get(PersonaKey.PERSONALITY)
        owner = inputs.get(PersonaKey.OWNER)
        personality_row = rows.get(PersonaKey.PERSONALITY)
        if use_file is None or personality is None or owner is None:
            return
        if personality_row is None:
            return

        index = layout.indexOf(personality_row)
        layout.removeWidget(personality_row)
        slot = QStackedWidget()
        slot.addWidget(personality_row)
        row = PersonaPreviewRow(label_width)
        slot.addWidget(row)

        if not row.bind(use_file, personality, owner, slot):
            # 控件类型不符撤堆叠，输入行原位放回
            slot.removeWidget(row)
            slot.removeWidget(personality_row)
            layout.insertWidget(index, personality_row)
            return

        layout.insertWidget(index, slot)
        row.sync()

    def _build_bottom_buttons(self, is_setup: bool) -> QHBoxLayout:
        """按模式构建底部按钮"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(GLOBAL.radius)
        btn_layout.addStretch()

        if is_setup:
            btn_exit = QPushButton(SETTINGS_DIALOG.exit_text)
            btn_exit.clicked.connect(self._on_exit)
            btn_finish = QPushButton(SETTINGS_DIALOG.finish_text)
            btn_finish.setObjectName("btn_primary")
            btn_finish.setMinimumWidth(SETTINGS_DIALOG.finish_btn_min_width)

            # 发信号而非 accept：校验通过才关窗，失败则原窗保留已填内容
            btn_finish.clicked.connect(self._on_save)
            self.save_btn, self.save_text = btn_finish, SETTINGS_DIALOG.finish_text
            btn_layout.addWidget(btn_exit)
            btn_layout.addWidget(btn_finish)
            return btn_layout

        btn_cancel = QPushButton(SETTINGS_DIALOG.cancel_text)
        btn_cancel.clicked.connect(self._on_cancel)
        btn_save = QPushButton(SETTINGS_DIALOG.save_text)
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._on_save)
        self.save_btn, self.save_text = btn_save, SETTINGS_DIALOG.save_text
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        return btn_layout
