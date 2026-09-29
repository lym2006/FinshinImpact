# src/gui/controllers/_settings.py
"""配置控制器（内部实现）

- 实现向导调度、二次确认与热重载
- 面板全程非模态：EDIT/SETUP 同实例原地切换
- 校验轮驱动进程级唯一 CheckDialog，与他轮互斥不并发
"""

from PySide6.QtCore import QTimer

from exceptions import ConfigOutputError
from messages import CheckMessage
from utils import config_manager
from utils.config import (
    AppConfigData,
    compare_configs,
    save_config,
)
from utils.net_probe import verify_skeleton

from .._theme import NOTICE_DIALOG, SETTINGS_DIALOG
from ..dialogs import (
    ChangeConfirmDialog,
    CheckDialog,
    ConfigMode,
    NoticeDialog,
    Round,
    SettingsDialog,
    current_check_window,
    open_check_window,
)
from ..mediator import gui_bridge
from ._base import BaseController

_STARTUP_WAIT_DELAY = 1200  # 启动校验迟滞弹窗阈值（毫秒）


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

        # 当前打开的面板实例（EDIT/SETUP 同实例切换，防 GC 销毁 C++ 窗口）
        self._panel: SettingsDialog | None = None

        # 配置就绪缓存：仅在 Qt 线程由信号回调更新，默认未就绪
        self._config_ready: bool = False

        # 复验在途标记：无落盘动作，通过只收检测窗
        self._validating: bool = False

        # 保存在途标记：本轮通过时由 Qt 侧落盘候选
        self._save_pending: bool = False

        # 待落盘候选：校验通过才写入磁盘，关面板/取消即弃
        self._pending_candidate: AppConfigData | None = None

        # 迟滞开窗前的帧缓存：启动轮后台先跑，计划帧先到窗未开，开轮后补播
        self._pre_frames: list[dict] = []

        # 信号携带最新状态，经 Queued 投递后在本线程写入私有字段
        gui_bridge.config_ready_changed.connect(
            self._on_config_ready_changed, "配置就绪", queued=True
        )
        gui_bridge.verify_progress.connect(
            self._on_verify_frame, "校验进度", queued=True
        )

    # ==================== 状态同步 ====================

    def _on_config_ready_changed(self, ready: bool) -> None:
        """更新就绪缓存（Qt 线程）

        收窗铁律：校验通过检测窗一律自动收，失败驻留等读结果
        """
        # 未就绪事件不得清 _validating：否则已就绪到达时无人解除 busy 转圈
        self._config_ready = ready
        if not ready:
            # 裸启动无面板无窗：1.2 秒后校验未完才弹等待窗，快路径不闪窗
            if not (self._panel or current_check_window()):
                QTimer.singleShot(_STARTUP_WAIT_DELAY, self._open_startup_wait)
            return
        was_validating = self._validating
        was_pending = self._save_pending
        self._validating = False
        self._save_pending = False
        wait = self._verify_window()
        if wait is not None:
            wait.accept()  # 通过即全绿：结果无保留价值，静默收窗
        if was_pending and self._pending_candidate is not None:
            # 先验后存的落盘时刻：内存早已就位，磁盘只给验证过的配置
            candidate = self._pending_candidate
            self._pending_candidate = None
            try:
                save_config(candidate)
                # 文案避"配置"与结果词：域词表 ⚙️ 在前，写盘动作应归 💾
                self.logger.info(CheckMessage.WRITTEN)
            except ConfigOutputError as e:
                self.logger.error(f"配置写入失败: {e}")
                if self._panel is not None:
                    self._panel.set_busy(False)
                return
        if self._panel is not None:
            if was_pending or was_validating:
                self._close_panel_verified()
            else:
                # 取消回退引发的重验轮：与本次编辑无关，解除忙碌即可
                self._panel.set_busy(False)
        elif was_pending:
            self._is_dialog_open = False  # 面板已被用户关掉：复位防卡死

    def _close_panel_verified(self) -> None:
        """通过统一收面板：先关窗再弹一条已验证提示

        向导与 EDIT 同路，SETUP 的标红残留随窗消失，无需分模式。
        """
        if self._panel is None:
            return
        self._panel.accept()
        NoticeDialog.notify(SETTINGS_DIALOG.verified_ok, parent=self.gui)

    # ==================== 业务逻辑实现 ====================

    def _execute(self) -> None:
        """用户点击按钮进入编辑模式"""
        # 重验期间禁编辑：半新配置一旦保存会覆盖用户真实配置
        if not self._config_ready:
            self.logger.info(CheckMessage.NOT_READY)
            return

        self._current_mode = ConfigMode.EDIT
        self._field_errors = {}
        self._show_dialog()

    def show_setup_dialog(self, field_errors: dict | None = None) -> None:
        """外部信号启动强制向导

        面板在前台则原地变身 SETUP，绝无关窗重开。
        """
        # 关闭流程进行中，不再打开弹窗
        if gui_bridge.is_shutdown_pending():
            self.logger.info("关闭流程进行中，跳过强制配置向导")
            return

        self._field_errors = dict(field_errors or {})

        # 面板在前台（EDIT 或 SETUP）：原地刷标红，检测窗继续浮顶
        if self._panel is not None:
            self._validating = False
            self._save_pending = False
            self._pending_candidate = None
            self._panel.set_busy(False)
            if self._current_mode == ConfigMode.EDIT:
                self._current_mode = ConfigMode.SETUP
                self._panel.switch_to_setup(self._field_errors)
                self.logger.info("校验未过，面板已原地转强制向导")
            else:
                self._panel.apply_errors(self._field_errors)
                self.logger.debug("强制向导已打开，原地刷新校验结果")
            self._attach_transient()
            return

        self._current_mode = ConfigMode.SETUP
        self._show_dialog()

    # ==================== 校验进度窗（唯一实例） ====================

    def _verify_window(self) -> CheckDialog | None:
        """取当前校验轮窗口：非校验轮或无窗均返 None"""
        win = current_check_window()
        return win if win is not None and win.round == Round.VERIFY else None

    def _start_verify_wait(self, aborts: bool) -> bool:
        """在唯一窗上开校验轮；他轮在途则日志拦截

        返回是否真正开轮，调用方据此决定是否唤醒后台。
        """
        busy = current_check_window()
        if busy is not None and busy.is_running:
            self.logger.info(CheckMessage.CHECK_BUSY)
            self._validating = False
            self._save_pending = False
            if self._panel is not None:
                self._panel.set_busy(False)
            return False

        wait = open_check_window(self.gui)
        wait.begin_round(
            Round.VERIFY, aborts, verify_skeleton(), self._on_verify_closed
        )
        # 补播迟滞期缓存的帧：计划帧带缺席结论重建表格，逐行帧按序点亮
        for frame in self._pre_frames:
            wait.apply(frame)
        self._pre_frames = []
        self._attach_transient()
        return True

    def _on_verify_closed(self, result: int) -> None:
        """唯一窗收场：仅校验轮的进行中 reject 才是真停

        不可中断轮进行中无按钮且屏蔽 Esc，只会以 accept 收场，不动后台。
        """
        wait = self._verify_window()
        if (
            wait is not None
            and result == wait.DialogCode.Rejected
            and not wait.settled
            and wait.aborts
        ):
            self._abort_pending_verify()

    def _abort_pending_verify(self) -> None:
        """真停：按钮文案即行为——中止校验、弃候选、当场解锁面板

        保存在途走 abort 通道（Bot 中止任务并回退内存）；复验在途无候选，
        只弃在途标志，被中断的校验轮收尾必发 ready，面板届时解除忙碌。
        """
        if self._save_pending:
            self._pending_candidate = None
            self._save_pending = False
            self.logger.info(CheckMessage.VERIFY_ABORTED)
            gui_bridge.config_abort.emit()
            return
        if self._validating:
            self._validating = False
            if self._panel is not None:
                self._panel.set_busy(False)
            self.logger.info(CheckMessage.VERIFY_STOPPED)
            gui_bridge.config_abort.emit()

    def _attach_transient(self) -> None:
        """校验窗浮在当前面板之上：面板换装/新开后重新跟随

        本绑定无 QWidget 级接口，下到 QWindow 挂关系；句柄需 winId 强制具象。
        """
        wait = self._verify_window()
        if wait is None:
            return
        owner = self._panel or self.gui
        wait.winId()
        owner.winId()
        wait.windowHandle().setTransientParent(owner.windowHandle())

    def _on_verify_frame(self, frame: dict) -> None:
        """进度帧转发：窗未开先缓存（开轮补播），他轮占用则静默丢弃"""
        wait = self._verify_window()
        if wait is not None:
            wait.apply(frame)
        elif current_check_window() is None:
            self._pre_frames.append(frame)

    def _open_startup_wait(self) -> None:
        """启动校验迟滞弹窗（快路径不闪窗，他轮占用则静默让位）

        后台校验照跑不误，播报让路即可；抢弹提示是骚扰不是反馈。
        """
        if self._config_ready or self._panel is not None:
            return
        busy = current_check_window()
        if busy is not None and busy.is_running:
            return
        self.logger.info(
            CheckMessage.VERIFY_START.format(reason=CheckMessage.REASON_STARTUP)
        )
        self._start_verify_wait(aborts=False)

    # ==================== 内部弹窗逻辑 ====

    def _show_dialog(self) -> None:
        """打开配置弹窗（EDIT/SETUP 统一非模态 show，可拖动看日志）"""
        if self._is_dialog_open:
            # 面板已在前台时再点按钮应聚焦它而不是无响应
            if self._panel is not None:
                self._panel.raise_()
                self._panel.activateWindow()
                self.logger.info("配置面板已打开，置前显示")
            return
        self._is_dialog_open = True
        self.logger.info("正在打开配置面板...")

        self._panel = self._create_dialog()
        dialog = self._panel
        dialog.save_requested.connect(lambda: self._on_save_requested(dialog))
        dialog.finished.connect(self._on_panel_finished)
        self._panel.show()
        # 先面板后跟随窗：面板后出场会反压检测窗，顺序不可颠倒
        self._attach_transient()

    def _create_dialog(self) -> SettingsDialog:
        """按当前模式构造配置弹窗"""
        return SettingsDialog(
            schema=config_manager.schema,
            current_config=config_manager.get_all(),
            mode=self._current_mode,
            parent=self.gui,
            field_errors=self._field_errors,
        )

    def _on_save_requested(self, dialog: SettingsDialog | None) -> None:
        """处理面板保存请求

        校验通过才关窗；取消路径面板与已填内容原样保留。
        """
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
            NoticeDialog.notify(NOTICE_DIALOG.not_changed, parent=dialog)
            self.logger.info("配置未修改")
            return
        if not changes:
            if self._validating:
                return
            self._validating = True
            dialog.set_busy(True)
            self.logger.info(
                CheckMessage.VERIFY_START.format(reason=CheckMessage.REASON_RECHECK)
            )
            if not self._start_verify_wait(aborts=True):
                self._validating = False
                dialog.set_busy(False)
                return
            # 复验走候选通道：校验对象必须是面板上屏值，禁走磁盘重载
            gui_bridge.config_candidate.emit()
            return

        # 二次确认以面板为父级：取消后面板仍在，无需重建
        if not ChangeConfirmDialog.confirm(logs, parent=dialog):
            return

        self._log_changes(logs)
        # 先验后存：候选只进内存，通过才落盘；取消即回退，磁盘从未见过坏值
        self._pending_candidate = new_config
        self._save_pending = True
        dialog.set_busy(True)
        self.logger.info(
            CheckMessage.VERIFY_START.format(reason=CheckMessage.REASON_SAVE)
        )
        if not self._start_verify_wait(aborts=True):
            self._pending_candidate = None
            self._save_pending = False
            dialog.set_busy(False)
            return
        config_manager.load(new_config)
        gui_bridge.config_candidate.emit()

    def _on_panel_finished(self, result: int) -> None:
        """面板关闭后复位状态并交还窗口对象"""
        if self._panel is None:
            return
        if result == self._panel.DialogCode.Rejected:
            self.logger.info("用户取消了配置修改")
            # 校验在途时关面板=放弃本次操作：候选与后台轮一并掐掉
            self._abort_pending_verify()
        self._panel.deleteLater()
        self._panel = None
        self._is_dialog_open = False

    # ==================== 内部保存逻辑 ====================

    def _log_changes(self, logs: list) -> None:
        """分级记录变更日志"""
        names = "、".join(name for name, _, _ in logs)
        self.logger.info(f"保存 {len(logs)} 项配置: {names}")
        msg = ""
        for key, ori, mod in logs:
            msg += f"\n配置项：{key}\n原: {ori}\n新: {mod}"
        self.logger.debug(msg)
