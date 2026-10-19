# src/gui/controllers/_settings.py
"""配置控制器（内部实现）

- 实现向导调度、二次确认与热重载
"""

from PySide6.QtCore import QTimer

from exceptions import ConfigOutputError
from utils import config_manager
from utils.config import (
    AppConfigData,
    compare_configs,
    save_config,
)

from .._theme import SETTINGS_DIALOG as DIALOG_TEXTS
from .._theme import WAIT_DIALOG as PD
from ..dialogs import (
    ChangeConfirmDialog,
    ConfigMode,
    NotChangedDialog,
    SettingsDialog,
    WaitDialog,
)
from ..mediator import gui_bridge
from ._base import BaseController


class SettingsController(BaseController):
    """配置控制器"""

    # ==================== 契约声明 ====================

    LOGGER_NAME = "GUI.Settings"
    BTN_KEY = "settings"

    # ==================== 初始化 ====================

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # 记录当前打开弹窗的原因（默认为正常编辑）
        self._current_mode: ConfigMode = ConfigMode.EDIT

        # 用于标记弹窗是否已打开（防重入）
        self._is_dialog_open: bool = False

        # 上次验证失败的字段级错误：{配置键: 文案}（强制向导标注用）
        self._field_errors: dict[str, str] = {}

        # SETUP 向导实例（非模态期间防 GC）
        self._setup_dialog: SettingsDialog | None = None

        # 配置就绪缓存：仅在 Qt 线程由信号回调更新，默认未就绪
        self._config_ready: bool = False

        # EDIT 校验失败切向导标记：区分主动取消与被动关闭
        self._switching: bool = False

        # 无修改复验进行中标志：防重复触发校验
        self._validating: bool = False

        # 当前打开的面板引用（EDIT/SETUP 共用）：复验结果原地刷新
        self._panel: SettingsDialog | None = None

        # 校验进行中的等待弹窗：转圈 + 秒级计时，结果到达即收口
        self._verify_wait: WaitDialog | None = None
        self._verify_secs: int = 0
        self._verify_timer: QTimer | None = None

        # 启动路径持有的等待窗：结果到达自动关闭，无需点击
        self._startup_wait: bool = False

        # 信号携带最新状态，经 Queued 投递后在本线程写入私有字段
        gui_bridge.config_ready_changed.connect(
            self._on_config_ready_changed, "配置就绪", queued=True
        )

    # ==================== 状态同步 ====================

    def _on_config_ready_changed(self, ready: bool) -> None:
        """更新就绪缓存（Qt 线程）

        向导通过关窗，EDIT 通过弹提示
        """
        # 未就绪事件不得清 _validating：否则已就绪到达时无人解除 busy 转圈
        self._config_ready = ready
        if not ready:
            # 裸启动无面板：1.2 秒后校验未完才弹等待窗，快路径不闪窗
            if not (self._panel or self._setup_dialog or self._verify_wait):
                QTimer.singleShot(1200, self._open_startup_wait)
            return
        was_validating = self._validating
        self._validating = False
        if self._startup_wait:
            self._close_verify_wait()  # 启动校验通过：静默收窗
        else:
            self._finish_verify_wait(PD.verified, True)
        gui_bridge.config_verified.emit()
        if self._setup_dialog is not None:
            self._setup_dialog.accept()
        elif self._panel is not None and was_validating:
            self._panel.set_busy(False)
            NotChangedDialog.show(
                parent=self._panel,
                text=DIALOG_TEXTS.verified_ok,
            )

    # ==================== 业务逻辑实现 ====================

    def _execute(self) -> None:
        """用户点击按钮进入编辑模式"""
        # 重验期间禁编辑：半新配置一旦保存会覆盖用户真实配置
        if not self._config_ready:
            self.logger.info("配置尚未就绪，稍后再试")
            return

        self._current_mode = ConfigMode.EDIT
        self._field_errors = {}
        self.logger.info("正在打开配置面板...")
        self._show_dialog()

    def show_setup_dialog(self, field_errors: dict | None = None) -> None:
        """外部信号启动强制向导"""
        # 关闭流程进行中，不再打开弹窗
        if gui_bridge.is_shutdown_pending():
            self.logger.info("关闭流程进行中，跳过强制配置向导")
            return

        self._field_errors = dict(field_errors or {})
        first_err = next(iter(self._field_errors.values()), "校验未通过")
        if self._startup_wait:
            self._close_verify_wait()  # 启动失败：等待窗让位标红向导
        else:
            self._finish_verify_wait(first_err, False)

        # 复验结果回来且向导在前台：原地刷新标红，避免关窗重开的闪烁
        if self._setup_dialog is not None:
            self._validating = False
            self._setup_dialog.set_busy(False)
            self._setup_dialog.apply_errors(self._field_errors)
            self.logger.debug("强制向导已打开，原地刷新校验结果")
            return

        # EDIT 面板在前台：先关模态再切 SETUP 向导，失败结果带进新窗标红
        if self._panel is not None:
            self._switching = True
            self._validating = False
            panel = self._panel
            if self._verify_wait is not None:
                # 等待窗挂将在关闭的面板下：改挂主窗防连带隐藏
                self._verify_wait.setParent(self.gui)
                self._verify_wait.show()
            QTimer.singleShot(0, self._open_setup_after_edit)
            panel.reject()
            return

        self._current_mode = ConfigMode.SETUP
        self._show_dialog()

    def _open_setup_after_edit(self) -> None:
        """EDIT 关闭后打开强制向导（切换链后半段）"""
        self._current_mode = ConfigMode.SETUP
        self._show_dialog()

    # ==================== 校验等待窗 ====================

    def _start_verify_wait(self) -> None:
        """弹出转圈等待窗并启动秒级计时（重复调用只保留一个）"""
        if self._verify_wait is not None:
            return
        self._verify_secs = 0

        # 父级优先当前面板：EDIT 模态期间兄弟窗会被挡输入，子窗可用
        parent = self._panel or self.gui
        self._verify_wait = WaitDialog(PD.verify_text, parent=parent)
        self._verify_timer = QTimer(self._verify_wait)
        self._verify_timer.setInterval(1000)
        self._verify_timer.timeout.connect(self._tick_verify_wait)
        self._verify_timer.start()
        self._verify_wait.show()

    def _open_startup_wait(self) -> None:
        """启动校验迟滞弹窗（快路径不闪窗，面板出现则让位）"""
        if self._config_ready or self._verify_wait is not None:
            return
        if self._panel is not None or self._setup_dialog is not None:
            return
        self._startup_wait = True
        self._start_verify_wait()

    def _close_verify_wait(self) -> None:
        """启动路径自动收窗：停计时、直接关闭"""
        self._startup_wait = False
        if self._verify_timer is not None:
            self._verify_timer.stop()
            self._verify_timer = None
        if self._verify_wait is not None:
            self._verify_wait.accept()
            self._verify_wait = None

    def _tick_verify_wait(self) -> None:
        """每秒刷新等待文案"""
        if self._verify_wait is None:
            return
        self._verify_secs += 1
        self._verify_wait.set_text(PD.verify_format.format(n=self._verify_secs))

    def _finish_verify_wait(self, text: str, passed: bool) -> None:
        """结果到达：停计时、亮按钮；无窗口则静默跳过"""
        if self._verify_wait is None:
            return
        if self._verify_timer is not None:
            self._verify_timer.stop()
            self._verify_timer = None
        wait = self._verify_wait
        self._verify_wait = None
        wait.finish(text, passed)

    # ==================== 内部弹窗逻辑 ====

    def _show_dialog(self) -> None:
        """打开配置弹窗

        EDIT 模态 exec；SETUP 非模态 show，可拖动看日志。
        """
        if self._is_dialog_open:
            # 向导已在前台排队/显示时，再点按钮应聚焦它而不是无响应
            if self._setup_dialog is not None:
                self._setup_dialog.raise_()
                self._setup_dialog.activateWindow()
                self.logger.info("强制向导已打开，置前显示")
                return
            self.logger.info("配置面板已打开，忽略重复点击")
            return
        self._is_dialog_open = True

        if self._current_mode == ConfigMode.EDIT:
            try:
                self._run_dialog_once()
            finally:
                self._is_dialog_open = False
            return

        # SETUP：对话框实例挂在控制器上，防 Python GC 销毁 C++ 窗口
        self._setup_dialog = self._create_dialog()
        self._panel = self._setup_dialog
        self._setup_dialog.save_requested.connect(self._on_save_requested)
        self._setup_dialog.finished.connect(self._on_setup_finished)
        self._setup_dialog.show()

    def _create_dialog(self) -> SettingsDialog:
        """按当前模式构造配置弹窗"""
        return SettingsDialog(
            schema=config_manager.schema,
            current_config=config_manager.get_all(),
            mode=self._current_mode,
            parent=self.gui,
            field_errors=self._field_errors,
        )

    def _on_save_requested(self, dialog: SettingsDialog | None = None) -> None:
        """处理面板保存请求

        校验通过才关窗；取消路径面板与已填内容原样保留。
        """
        dialog = dialog or self._setup_dialog
        if dialog is None:
            return

        new_config = dialog.get_modified_config()
        changes, logs = compare_configs(
            config_manager.schema, config_manager.get_all(), new_config
        )

        # 有风险（向导态/代理留空）或有任何改动都要复验；通道没变时 Manager 跳重启
        risky = (
            self._current_mode == ConfigMode.SETUP
            or not str(config_manager.get("basic.proxy", str) or "").strip()
        )
        if not changes and not risky:
            NotChangedDialog.show(parent=dialog)
            self.logger.info("配置未修改")
            return
        if not changes:
            if self._validating:
                return
            self._validating = True
            dialog.set_busy(True)
            self.logger.info("配置未修改，重新校验连通性...")
            self._start_verify_wait()
            gui_bridge.config_saved.emit()
            return

        # 二次确认以向导为父级：取消后向导仍在，无需重建
        if not ChangeConfirmDialog.confirm(logs, parent=dialog):
            return

        self._log_changes(logs)
        if self._handle_save(new_config):
            dialog.accept()  # 写入成功才关窗，校验失败由信号驱动转强制向导
            self._start_verify_wait()  # 面板已关，等待窗顶上校验反馈

    def _on_setup_finished(self, _result: int) -> None:
        """向导关闭后复位状态"""
        if self._setup_dialog is None:
            return

        self._setup_dialog = None
        self._panel = None
        self._is_dialog_open = False
        self._switching = False

    def _run_dialog_once(self) -> None:
        """EDIT 模态弹窗流程"""
        dialog = self._create_dialog()
        self._panel = dialog
        dialog.save_requested.connect(lambda: self._on_save_requested(dialog))
        if dialog.exec() != dialog.DialogCode.Accepted:
            if self._switching:
                self.logger.info("校验未通过，已切换强制配置向导")
            else:
                self.logger.info("用户取消了配置修改")
        self._panel = None

    # ==================== 内部保存逻辑 ====================

    def _log_changes(self, logs: list) -> None:
        """分级记录变更日志"""
        names = "、".join(name for name, _, _ in logs)
        self.logger.info(f"保存 {len(logs)} 项配置: {names}")
        msg = ""
        for key, ori, mod in logs:
            msg += f"\n配置项：{key}\n原: {ori}\n新: {mod}"
        self.logger.debug(msg)

    def _handle_save(self, new_config: AppConfigData) -> bool:
        """保存配置并广播

        返回是否成功，供调用方决定关窗。
        """
        try:
            save_config(new_config)
            config_manager.load(new_config)
            gui_bridge.config_saved.emit()
            return True
        except ConfigOutputError as e:
            self.logger.error(f"配置写入失败: {e}")
            return False
