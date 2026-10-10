# src/bootstrap/_picker_form.py
"""实例表单窗

- 收 token 与备注名，新建与编辑共用同一表单
- 校验与落盘策略由各自子类实现
- 只依赖 Qt、profile_env 与 core.domain，不碰 utils 防路径提前冻结
"""

from typing import cast

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.domain import Platform, platform_of_profile
from messages import PickerMessage
from profile_env import read_token

from ._store import code_for_token, create_profile, update_profile

_FORM_WIDTH = 460
_FORM_HEIGHT = 320

# 平台下拉项，显示文案归 messages 单源
_PLATFORM_ITEMS = (
    (Platform.TELEGRAM, PickerMessage.NEW_PLATFORM_TELEGRAM),
    (Platform.QQ, PickerMessage.NEW_PLATFORM_QQ),
)

# 已接线的平台，未列入者在下拉里置灰仅作预告
_SUPPORTED_PLATFORMS = frozenset({Platform.TELEGRAM})


class _ProfileFormDialog(QDialog):
    """实例表单窗

    - 收 token 与备注名，token 提示常显于输入框下方
    - 新建与编辑共用此表单，校验落盘各自实现
    """

    def __init__(self, title: str) -> None:
        super().__init__()
        self.code = ""
        self._build(title)

    def _build(self, title: str) -> None:
        """装配控件"""
        self.setWindowTitle(title)
        self.resize(_FORM_WIDTH, _FORM_HEIGHT)

        form = QVBoxLayout(self)

        self._build_head(form)

        form.addWidget(QLabel(PickerMessage.FORM_TOKEN_LABEL))
        self._token = QLineEdit()
        form.addWidget(self._token)

        # 提示常显于输入框外，避免输入后被占位符遮住看不见
        hint = QLabel(PickerMessage.FORM_TOKEN_HINT)
        hint.setWordWrap(True)
        form.addWidget(hint)

        form.addWidget(QLabel(PickerMessage.FORM_REMARK_LABEL))
        self._remark = QLineEdit()
        form.addWidget(self._remark)

        form.addStretch()

        buttons = QHBoxLayout()
        ok = QPushButton(PickerMessage.BTN_OK)
        ok.clicked.connect(self._on_ok)
        cancel = QPushButton(PickerMessage.BTN_CANCEL)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        form.addLayout(buttons)

        self._token.setFocus()

    def _build_head(self, form: QVBoxLayout) -> None:
        """表单顶部扩展位，默认空，子类按需覆盖"""

    def _on_ok(self) -> None:
        """校验 token 并落盘，子类实现各自策略"""
        raise NotImplementedError

    def _warn(self, body: str) -> None:
        """表单内警告弹窗"""
        QMessageBox.warning(self, self.windowTitle(), body)


class NewProfileDialog(_ProfileFormDialog):
    """新建实例窗

    - token 结构合法即落盘，身份码由 token 推导
    """

    def __init__(self) -> None:
        super().__init__(PickerMessage.NEW_TITLE)

    def _build_head(self, form: QVBoxLayout) -> None:
        """平台下拉

        - 未接线平台置灰不可选，仅作未来支持的预告
        """
        form.addWidget(QLabel(PickerMessage.NEW_PLATFORM_LABEL))
        self._platform = QComboBox()
        for platform, label in _PLATFORM_ITEMS:
            self._platform.addItem(label, platform)
            if platform not in _SUPPORTED_PLATFORMS:
                # 存根把 model() 标成基类，实为 combo 自持的项模型，置灰只在子类有
                model = cast(QStandardItemModel, self._platform.model())
                model.item(self._platform.count() - 1).setEnabled(False)
        form.addWidget(self._platform)

    def _on_ok(self) -> None:
        """校验 token 并新建实例"""
        token = self._token.text().strip()

        # Qt userData 取出会退化成字符串，包回枚举让类型契约名副其实
        platform = Platform(self._platform.currentData())
        code = code_for_token(platform, token)
        if not code:
            self._warn(PickerMessage.FORM_TOKEN_INVALID)
            return

        create_profile(code, token, self._remark.text())
        self.code = code
        self.accept()


class EditProfileDialog(_ProfileFormDialog):
    """编辑实例窗

    - 回填既有 token 与备注名，就地改写
    - 换机器人导致身份码变化时拒绝，引导新建
    """

    def __init__(self, code: str, remark: str) -> None:
        self._code = code
        super().__init__(PickerMessage.EDIT_TITLE)
        self._token.setText(read_token(code))
        self._remark.setText(remark)

    def _on_ok(self) -> None:
        """校验身份码一致后就地改写"""
        token = self._token.text().strip()
        platform = platform_of_profile(self._code)
        if platform is None:
            self._warn(PickerMessage.EDIT_PLATFORM_UNKNOWN)
            return

        new_code = code_for_token(platform, token)
        if not new_code:
            self._warn(PickerMessage.FORM_TOKEN_INVALID)
            return

        # 身份码来自 bot_id，重生成 token 不变，换机器人才变
        if new_code != self._code:
            self._warn(
                PickerMessage.EDIT_TOKEN_CHANGED.format(old=self._code, new=new_code)
            )
            return

        update_profile(self._code, token, self._remark.text())
        self.code = self._code
        self.accept()
