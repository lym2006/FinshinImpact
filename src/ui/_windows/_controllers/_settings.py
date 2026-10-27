# src/ui/_windows/_controllers/_settings.py
"""配置控制器

- 实现向导调度、二次确认与热重载
- 面板全程非模态：EDIT/SETUP 同实例原地切换
- 校验轮驱动进程级唯一 CheckDialog，交 VerifyCoordinator 协调
"""

from core.domain import ConfigKey, ConfigSection
from exceptions import ConfigOutputError
from skin.messages import CheckMessage
from skin.theme import NOTICE_DIALOG, SETTINGS_DIALOG
from utils import config_manager
from utils.config import (
    AppConfigData,
    compare_configs,
    save_config,
)
from utils.persona import reload_persona_cache

from ..._bridge import gui_bridge
from ..._dialogs import (
    ChangeConfirmDialog,
    ConfigMode,
    NoticeDialog,
    SettingsDialog,
    current_check_window,
)
from ..._lifecycle import Ticker
from ._base import BaseController
from ._verify import VerifyCoordinator

_STARTUP_WAIT_DELAY = 1200  # 启动校验迟滞弹窗阈值（毫秒）


class SettingsController(BaseController):
    """配置控制器"""

    # 契约声明
    LOGGER_NAME = "GUI.Settings"
    BTN_KEY = "settings"

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

        self._identity_changed: bool = False

        # 校验轮协调器：持有在途标志、待落盘候选与迟滞帧缓存
        self._verify = VerifyCoordinator(self)

        # 信号携带最新状态，经 Queued 投递后在本线程写入私有字段
        gui_bridge.config_ready_changed.connect(
            self._on_config_ready_changed, "配置就绪", queued=True
        )
        gui_bridge.verify_progress.connect(
            self._verify.on_frame, "校验进度", queued=True
        )

    def _on_config_ready_changed(self, ready: bool) -> None:
        """更新就绪缓存

        - 校验通过自动关闭进度窗，失败保留窗口供查看
        """
        self._config_ready = ready
        if not ready:
            # 裸启动无面板无窗：1.2 秒后校验未完才弹等待窗，快路径不闪窗
            if not (self._panel or current_check_window()):
                Ticker.after(_STARTUP_WAIT_DELAY, self._verify.open_startup_wait)
            return
        was_validating = self._verify.validating
        was_pending = self._verify.save_pending
        self._verify.validating = False
        self._verify.save_pending = False
        wait = self._verify.window()
        if wait is not None:
            wait.accept()  # 通过即全绿：结果无保留价值，静默收窗
        if was_pending and self._verify.pending_candidate is not None:
            # 先验后存的落盘时刻：内存早已就位，磁盘只给验证过的配置
            candidate = self._verify.pending_candidate
            self._verify.pending_candidate = None
            try:
                save_config(candidate)
                self.logger.info(CheckMessage.WRITTEN)
            except ConfigOutputError as e:
                self.logger.error(f"配置写入失败: {e}")
                if self._panel is not None:
                    self._panel.set_busy(False)
                return
        if self._panel is not None:
            if was_pending or was_validating:
                self._close_panel_verified(
                    SETTINGS_DIALOG.history_reset
                    if self._identity_changed
                    else SETTINGS_DIALOG.verified_ok
                )
            else:
                # 取消回退引发的重验轮：与本次编辑无关，解除忙碌即可
                self._panel.set_busy(False)
        elif was_pending:
            self._is_dialog_open = False  # 面板已被用户关掉：复位防卡死

    def _close_panel_verified(self, text: str = SETTINGS_DIALOG.verified_ok) -> None:
        """关闭面板并弹一条结果提示

        - 先关窗再提示，标红残留随窗消失
        """
        if self._panel is None:
            return
        self._panel.accept()
        NoticeDialog.notify(text, parent=self.gui)

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

        - 面板已打开则原地切换为 SETUP 模式
        """
        # 关闭流程进行中，跳过强制配置向导
        if gui_bridge.is_shutdown_pending():
            self.logger.info("关闭流程进行中，跳过强制配置向导")
            return

        self._field_errors = dict(field_errors or {})

        # 面板在前台（EDIT 或 SETUP）：原地刷标红，检测窗继续浮顶
        if self._panel is not None:
            self._verify.validating = False
            self._verify.save_pending = False
            self._verify.pending_candidate = None
            self._panel.set_busy(False)
            if self._current_mode == ConfigMode.EDIT:
                self._current_mode = ConfigMode.SETUP
                self._panel.switch_to_setup(self._field_errors)
                self.logger.info("校验未过，面板已原地转强制向导")
            else:
                self._panel.apply_errors(self._field_errors)
                self.logger.debug("强制向导已打开，原地刷新校验结果")
            self._verify.attach_transient()
            return

        self._current_mode = ConfigMode.SETUP
        self._show_dialog()

    def _show_dialog(self) -> None:
        """打开配置弹窗"""
        # EDIT/SETUP 统一非模态 show，可拖动看日志
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
        self._verify.attach_transient()

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

        - 校验通过才关窗
        - 取消路径面板与已填内容原样保留
        """
        if dialog is None:
            return

        new_config = dialog.get_modified_config()

        # 人设正文以磁盘副本为准，改文件不算改配置项
        persona_changed = reload_persona_cache()

        changes, logs = compare_configs(
            config_manager.schema, config_manager.get_all(), new_config
        )

        # 对话身份由人设正文与主人构成，动过任一项都要起一轮清历史，配置未就绪时不报清空
        self._identity_changed = self._config_ready and (
            persona_changed
            or ConfigKey.OWNER in (changes.get(ConfigSection.CHORE) or {})
        )

        # 向导态或有任何改动都要起校验轮，通道没变时 Manager 只跑本地校验
        in_setup = self._current_mode == ConfigMode.SETUP
        if not changes and not in_setup:
            if not persona_changed:
                NoticeDialog.notify(NOTICE_DIALOG.not_changed, parent=dialog)
                self.logger.info("配置未修改")
                return
            self.logger.info("人设正文已按文件刷新")
        if not changes:
            if self._verify.validating:
                return
            self._verify.validating = True
            dialog.set_busy(True)
            self.logger.info(
                CheckMessage.VERIFY_START.format(reason=CheckMessage.REASON_RECHECK)
            )
            if not self._verify.start_round(aborts=True):
                self._verify.validating = False
                dialog.set_busy(False)
                return

            # 复验走候选通道：校验对象必须是面板上屏值，禁走磁盘重载
            gui_bridge.config_candidate.emit()
            return

        # 二次确认以面板为父级，取消后面板仍在
        if not ChangeConfirmDialog.confirm(logs, parent=dialog):
            return

        self._log_changes(logs)

        # 先验后存，候选只进内存，通过才落盘，取消即回退
        self._start_save_verify(dialog, new_config)

    def _start_save_verify(
        self, dialog: SettingsDialog, new_config: AppConfigData
    ) -> None:
        """候选进内存并起保存校验轮

        - 起轮失败即撤候选与待落盘标记，面板解除忙碌
        """
        self._verify.pending_candidate = new_config
        self._verify.save_pending = True
        dialog.set_busy(True)
        self.logger.info(
            CheckMessage.VERIFY_START.format(reason=CheckMessage.REASON_SAVE)
        )
        if not self._verify.start_round(aborts=True):
            self._verify.pending_candidate = None
            self._verify.save_pending = False
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

            # 校验在途时关面板即放弃本次操作，候选与后台轮一并掐掉
            self._verify.abort_pending()
        self._panel.deleteLater()
        self._panel = None
        self._is_dialog_open = False

    def _log_changes(self, logs: list) -> None:
        """分级记录变更日志"""
        names = "、".join(name for name, _, _ in logs)
        self.logger.info(f"保存 {len(logs)} 项配置: {names}")
        msg = ""
        for key, ori, mod in logs:
            msg += f"\n配置项：{key}\n原: {ori}\n新: {mod}"
        self.logger.debug(msg)
