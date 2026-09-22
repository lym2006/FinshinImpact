# src/gui/dialogs/_settings/__init__.py
"""配置向导（内部实现）

- 实现多标签页表单与错误标红
- 提供变更二次确认与未保存提示
"""

import difflib
import html
from enum import Enum, auto

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QFont, QFontMetrics, QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.config import PENDING_MARK
from utils.config.models import (
    AppConfigData,
    AppSchema,
    ConfigValue,
    FieldSchema,
    TabData,
    TabSchema,
)

from ..._qss import build_change_dialog_qss, build_settings_dialog_qss
from ..._theme import CHANGE_DIALOG as CHANGE
from ..._theme import GLOBAL
from ..._theme import HINT_DIALOG as HINT
from ..._theme import SETTINGS_DIALOG as DIALOG
from ...mediator import gui_bridge
from .._base import BaseDialog
from .._hint import HintDialog
from ._list_widget import ConfigListWidget

__all__ = [
    "ChangeConfirmDialog",
    "ConfigMode",
    "NotChangedDialog",
    "SettingsDialog",
]

_ERROR_QSS = f"color: {DIALOG.error_color};"
_PENDING_QSS = f"color: {DIALOG.pending_color};"
_ERROR_FONT = QFont("Microsoft YaHei", DIALOG.error_font_size)


class ConfigMode(Enum):
    """配置弹窗的工作模式"""

    EDIT = auto()  # 正常编辑（用户主动点击）
    SETUP = auto()  # 缺失引导（验证失败强制弹出）


class NotChangedDialog:
    """配置未修改提示弹窗"""

    @staticmethod
    def show(parent=None, text: str = HINT.not_changed) -> None:
        """家族化模态展示"""
        HintDialog.notify(text, parent=parent)


# ==================== diff 渲染辅助 ====================

_DIFF_STYLE = {
    "same": "",
    "del": f"color: {CHANGE.diff_del}; text-decoration: line-through;",
    "add": f"color: {CHANGE.diff_add}; font-weight: bold;",
}

# 一行内的 (类型, 文本) 分段序列
_Line = list[tuple[str, str]]


def _to_lines(value: object) -> list[str]:
    """配置值拆行

    list 逐元素，标量按文本行。
    """
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return str(value).splitlines() or [""]


def _char_diff(old: str, new: str) -> tuple[_Line, _Line]:
    """行内字符级比对

    旧/新各输出 (类型, 文本) 分段，公共部分白色。
    """
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    left: _Line = []
    right: _Line = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            left.append(("same", old[i1:i2]))
            right.append(("same", new[j1:j2]))
        else:
            if old[i1:i2]:
                left.append(("del", old[i1:i2]))
            if new[j1:j2]:
                right.append(("add", new[j1:j2]))
    return left, right


def _split_diff(old: list[str], new: list[str]) -> tuple[list[_Line], list[_Line]]:
    """行级对齐 + 配对行字符级细化

    改词只亮改动处，多出的行整行删除/新增。
    """
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    left: list[_Line] = []
    right: list[_Line] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            lines = old[i1:i2]
            left += [[("same", ln)] for ln in lines]
            right += [[("same", ln)] for ln in lines]
        elif tag == "delete":
            left += [[("del", ln)] for ln in old[i1:i2]]
        elif tag == "insert":
            right += [[("add", ln)] for ln in new[j1:j2]]
        else:  # replace：等长部分逐行字符级，多余部分整行
            old_lines, new_lines = old[i1:i2], new[j1:j2]
            pairs = min(len(old_lines), len(new_lines))
            for a, b in zip(old_lines[:pairs], new_lines[:pairs], strict=False):
                la, rb = _char_diff(a, b)
                left.append(la)
                right.append(rb)
            left += [[("del", ln)] for ln in old_lines[pairs:]]
            right += [[("add", ln)] for ln in new_lines[pairs:]]
    return left, right


def _make_diff_cell(lines: list[_Line], mono: str) -> QTextEdit:
    """只读 diff 单元格

    超行高自动出滚动条。
    """
    body = (
        "".join(
            "<div>"
            + (
                "".join(
                    f"<span style='{_DIFF_STYLE[kind]}'>"
                    f"{html.escape(text) or '&nbsp;'}</span>"
                    for kind, text in seg
                )
                or "&nbsp;"
            )
            + "</div>"
            for seg in lines
        )
        or "&nbsp;"
    )
    view = QTextEdit()
    view.setObjectName("change_cell")
    view.setReadOnly(True)
    view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    view.setHtml(f"<div style=\"font-family: '{mono}';\">{body}</div>")
    return view


class ChangeConfirmDialog(BaseDialog):
    """配置变更二次确认弹窗"""

    def __init__(
        self,
        logs: list[tuple[str, ConfigValue, ConfigValue]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent, title="确认变更")
        self.setStyleSheet(build_change_dialog_qss())
        self.setMinimumSize(CHANGE.min_width, CHANGE.min_height)
        self._build_ui(logs)

    @staticmethod
    def confirm(
        logs: list[tuple[str, ConfigValue, ConfigValue]],
        parent: QWidget | None = None,
    ) -> bool:
        """模态展示

        返回是否确认保存。
        """
        dialog = ChangeConfirmDialog(logs, parent=parent)
        return dialog.exec() == dialog.DialogCode.Accepted

    def _build_ui(self, logs: list[tuple[str, ConfigValue, ConfigValue]]) -> None:
        """构建表格与按钮区"""
        layout = QVBoxLayout(self)
        layout.setSpacing(DIALOG.tab_spacing)

        tip = QLabel(CHANGE.tip_text)
        layout.addWidget(tip)

        table = QTableWidget(len(logs), 3)
        table.setObjectName("change_table")
        table.setHorizontalHeaderLabels(
            [CHANGE.col_key, CHANGE.col_ori, CHANGE.col_mod]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        mono = CHANGE.mono_family
        line_h = QFontMetrics(QFont(mono, CHANGE.mono_font_size)).height()
        for row, (key, ori, mod) in enumerate(logs):
            left, right = _split_diff(_to_lines(ori), _to_lines(mod))
            name_cell = QTableWidgetItem(str(key))
            name_cell.setToolTip(name_cell.text())
            table.setItem(row, 0, name_cell)
            table.setCellWidget(row, 1, _make_diff_cell(left, mono))
            table.setCellWidget(row, 2, _make_diff_cell(right, mono))
            shown = min(
                max(len(left), len(right), CHANGE.row_min_lines),
                CHANGE.row_max_lines,
            )
            table.setRowHeight(row, shown * line_h + CHANGE.row_pad)
        layout.addWidget(table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(CHANGE.cancel_text)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton(CHANGE.confirm_text)
        btn_ok.setObjectName("btn_primary")
        btn_ok.clicked.connect(self.accept)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)


class SettingsDialog(BaseDialog):
    """配置面板弹窗"""

    # SETUP 模式请求保存：由控制器校验并决定是否关窗，窗口自身不 accept
    save_requested = Signal()

    def __init__(
        self,
        schema: AppSchema,
        current_config: AppConfigData,
        mode: ConfigMode = ConfigMode.EDIT,
        parent: QWidget | None = None,
        field_errors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(parent=parent, title="修改配置")

        # SETUP 模式字段级错误：{字段键: 悬浮文案}
        self._field_errors: dict[str, str] = dict(field_errors or {})
        # 出错字段所在 namespace，用于标红对应标签页
        self._error_namespaces = self._resolve_error_namespaces(schema)

        self.setStyleSheet(build_settings_dialog_qss())

        self._schema = schema
        self._current = current_config
        self._mode = mode

        # 输入控件表：{"field_key": widget}
        self._inputs: dict[
            str,
            ConfigListWidget | QLineEdit | QTextEdit | QCheckBox,
        ] = {}

        # 标签/页签/按钮引用：复验结果原地刷新用（免关窗重开的闪烁）
        self._labels: dict[str, tuple[QLabel, str]] = {}
        self._tab_titles: dict[str, tuple[int, str]] = {}
        self._tabs: QTabWidget | None = None
        self._save_btn: QPushButton | None = None
        self._save_text: str = ""

        # SETUP 模式：非模态可拖动，与主窗口同级可见日志；
        # 去掉原生关闭按钮（保留标题栏与边框），避免"点了没反应"的错觉；
        # 任务栏/Alt+F4 仍由 closeEvent 统一拦截
        if mode == ConfigMode.SETUP:
            self.setWindowModality(Qt.WindowModality.NonModal)
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
            )

        self.setMinimumSize(DIALOG.min_width, DIALOG.min_height)
        self._build_ui()

    # ==================== 关闭与退出 ====================

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """SETUP 模式拦截自身关闭"""
        if self._mode == ConfigMode.SETUP:
            event.ignore()
        else:
            super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """SETUP 屏蔽 Esc

        防绕过不可关闭约束。
        """
        if self._mode == ConfigMode.SETUP and event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_exit_clicked(self) -> None:
        """退出程序

        保留本窗请求退出
        确认框取消时本窗与已填内容原样保留。
        """
        gui_bridge.request_exit.emit(self)

    # ==================== 错误标注 ====================

    def _resolve_error_namespaces(self, schema: AppSchema) -> set[str]:
        """定位出错字段所在页"""
        bad: set[str] = set()
        for tab in schema:
            if any(f.key in self._field_errors for f in tab.fields):
                bad.add(tab.namespace)
        return bad

    def apply_errors(self, field_errors: dict[str, str] | None) -> None:
        """原地刷新校验结果

        字段标红/清除、标签页 ⚠ 增撤
        """
        self._field_errors = dict(field_errors or {})
        bad = self._resolve_error_namespaces(self._schema)
        for key, (label, title) in self._labels.items():
            err = self._field_errors.get(key)
            if err and err.startswith(PENDING_MARK):
                label.setText(f"❔ {title}")
                label.setStyleSheet(_PENDING_QSS)
            elif err:
                label.setText(title)
                label.setStyleSheet(_ERROR_QSS)
            else:
                label.setText(title)
                label.setStyleSheet("")
            label.setToolTip(err or "")
        for ns, (index, title) in self._tab_titles.items():
            mark = "⚠ " if ns in bad else ""
            self._tabs.setTabText(index, f"{mark}{title}")

    def set_busy(self, busy: bool) -> None:
        """校验进行中的防重入

        禁用保存按钮并改文案提示
        """
        if self._save_btn is None:
            return
        self._save_btn.setEnabled(not busy)
        self._save_btn.setText(DIALOG.validating_text if busy else self._save_text)

    # ==================== 渲染 ====

    def _create_field(
        self, field: FieldSchema, namespace: str, label_width: int = 0
    ) -> QWidget:
        """渲染表单控件"""
        container = QWidget()
        form = QFormLayout(container)
        form.setSpacing(GLOBAL.radius)
        form.setContentsMargins(*[DIALOG.margin] * 3 + [DIALOG.tab_spacing])

        ns_config = self._current.get(namespace)
        current_value = (
            ns_config[field.key]
            if ns_config and field.key in ns_config
            else field.default
        )

        # 标签：出错字段标红
        label_widget = QLabel(field.label)
        label_widget.setMinimumWidth(label_width)
        label_widget.setWordWrap(True)
        label_widget.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if err := self._field_errors.get(field.key):
            if err.startswith(PENDING_MARK):
                # 前置项失败导致的"暂未检测"：黄字 ❔，不算本项错误
                label_widget.setText(f"❔ {field.label}")
                label_widget.setStyleSheet(_PENDING_QSS)
            else:
                label_widget.setStyleSheet(_ERROR_QSS)
            label_widget.setToolTip(err)
        self._labels[field.key] = (label_widget, field.label)

        # 列表型字段
        if isinstance(field.default, list):
            list_widget = ConfigListWidget(
                items=current_value if isinstance(current_value, list) else [],
                description=field.desc,
            )
            self._inputs[field.key] = list_widget
            form.addRow(label_widget, list_widget)
            return container

        # bool 配置项 → 勾选行（通用机制，避免 True/False 一行丑字）
        checkbox: QCheckBox | None = None
        input_widget: QWidget
        if isinstance(field.default, bool):
            bool_box = QCheckBox(field.label)
            bool_box.setChecked(bool(current_value))
            self._inputs[field.key] = bool_box
            form.addRow(field.label, bool_box)
            return container
        if isinstance(current_value, str) and "\n" in current_value:
            input_widget = QTextEdit()
            input_widget.setPlainText(current_value)
        else:
            display = str(current_value) if current_value is not None else ""
            input_widget = QLineEdit(display)

        self._inputs[field.key] = input_widget

        # 右侧区域：输入框 + 说明文字
        right_wrapper = QWidget()
        v_layout = QVBoxLayout(right_wrapper)
        v_layout.setContentsMargins(*[DIALOG.margin] * 4)
        v_layout.setSpacing(DIALOG.desc_spacing)
        v_layout.addWidget(input_widget)
        if checkbox is not None:
            v_layout.addWidget(checkbox)
        if field.desc:
            v_layout.addWidget(self._build_desc(field.desc))

        form.addRow(label_widget, right_wrapper)
        return container

    def _calc_label_width(self, fields: list[FieldSchema]) -> int:
        """计算标签统一列宽"""
        metrics = QFontMetrics(self.font())
        max_width = max((metrics.horizontalAdvance(f.label) for f in fields), default=0)
        limit = metrics.horizontalAdvance("M") * 8
        return min(max_width, limit)

    def _build_desc(self, text: str) -> QLabel:
        """说明文字标签"""
        label = QLabel(text)
        label.setWordWrap(True)
        return label

    # ==================== 数据提取 ====================

    def get_modified_config(self) -> AppConfigData:
        """从输入控件提取配置字典"""
        modified: AppConfigData = {}

        for tab in self._schema:
            tab_data: TabData = {}

            for field in tab.fields:
                widget = self._inputs.get(field.key)
                value: ConfigValue = None

                if widget:
                    if isinstance(widget, ConfigListWidget):
                        value = widget.get_values()
                    elif isinstance(widget, QTextEdit):
                        value = widget.toPlainText().strip()
                    elif isinstance(widget, QCheckBox):
                        value = widget.isChecked()
                    elif isinstance(widget, QLineEdit):
                        text = widget.text().strip()
                        if isinstance(field.default, float):
                            try:
                                value = float(text)
                            except ValueError:
                                value = text  # 保持原样，交给类型校验器报错
                        else:
                            value = text

                tab_data[field.key] = value
            modified[tab.namespace] = tab_data
        return modified

    # ==================== 骨架 ====================

    def _build_ui(self) -> None:
        """构建界面"""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            *([DIALOG.input_padding_h, DIALOG.input_padding_v] * 2)
        )
        root_layout.setSpacing(DIALOG.tab_spacing)

        # SETUP 提示：出错标签页带 ⚠，出错字段标题标红
        if self._mode == ConfigMode.SETUP:
            tip_label = QLabel(DIALOG.setup_tip)
            tip_label.setStyleSheet(_ERROR_QSS)
            tip_label.setFont(_ERROR_FONT)
            hint_label = QLabel(DIALOG.setup_hint)
            hint_label.setStyleSheet(_ERROR_QSS)
            root_layout.addWidget(tip_label)
            root_layout.addWidget(hint_label)

        tabs = QTabWidget()
        for index, tab_schema in enumerate(self._schema):
            tab_widget = self._create_tab(tab_schema)
            mark = "⚠ " if tab_schema.namespace in self._error_namespaces else ""
            tabs.addTab(tab_widget, f"{mark}{tab_schema.title}")
            self._tab_titles[tab_schema.namespace] = (index, tab_schema.title)
        self._tabs = tabs

        root_layout.addWidget(tabs)
        root_layout.addLayout(self._build_bottom_buttons())

    def _create_tab(self, tab_schema: TabSchema) -> QWidget:
        """创建一个 Tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAutoFillBackground(False)

        container = QWidget()
        container.setStyleSheet(f"background-color: {DIALOG.tab_bg};")
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(DIALOG.tab_spacing)

        label_width = self._calc_label_width(tab_schema.fields)
        for field in tab_schema.fields:
            main_layout.addWidget(
                self._create_field(field, tab_schema.namespace, label_width)
            )
        main_layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _build_bottom_buttons(self) -> QHBoxLayout:
        """按模式构建底部按钮"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(GLOBAL.radius)
        btn_layout.addStretch()

        match self._mode:
            case ConfigMode.EDIT:
                btn_cancel = QPushButton(DIALOG.cancel_text)
                btn_cancel.clicked.connect(self.reject)
                btn_save = QPushButton(DIALOG.save_text)
                btn_save.setObjectName("btn_primary")
                btn_save.clicked.connect(self.save_requested.emit)
                self._save_btn, self._save_text = btn_save, DIALOG.save_text
                btn_layout.addWidget(btn_cancel)
                btn_layout.addWidget(btn_save)
            case ConfigMode.SETUP:
                btn_exit = QPushButton(DIALOG.exit_text)
                btn_exit.clicked.connect(self._on_exit_clicked)
                btn_finish = QPushButton(DIALOG.finish_text)
                btn_finish.setObjectName("btn_primary")
                btn_finish.setMinimumWidth(DIALOG.finish_btn_min_width)
                # 发信号而非 accept：校验通过才关窗，失败则原窗保留已填内容
                btn_finish.clicked.connect(self.save_requested.emit)
                self._save_btn, self._save_text = btn_finish, DIALOG.finish_text
                btn_layout.addWidget(btn_exit)
                btn_layout.addWidget(btn_finish)

        return btn_layout
