# src/ui/_windows/_controllers/_save.py
"""保存与落盘

- 面板的保存请求在这里算变更、起校验轮并暂存候选
- 候选先只进内存，校验通过那一次才写磁盘
- 对话身份是否变动记在这里，收尾文案由面板侧取用
"""

from typing import TYPE_CHECKING

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
from utils.init_files import drop_persona_pending, save_persona_text
from utils.persona import (
    applied_persona_text,
    apply_draft_persona,
    draft_persona_text,
    pending_persona,
    revert_persona_cache,
)

from ..._bridge import gui_bridge
from ..._dialogs import ChangeConfirmDialog, ConfigMode, NoticeDialog, SettingsDialog

if TYPE_CHECKING:
    from ._settings import SettingsController


class SaveCoordinator:
    """保存流程协调器

    - 与 SettingsController 一对一绑定，读它的面板、模式与就绪缓存
    - 落盘失败只解锁面板，候选与草稿原样留着待下次保存
    """

    def __init__(self, host: "SettingsController") -> None:
        self._host = host

        # 本次保存是否动过对话身份，面板收尾据此选文案
        self.identity_changed: bool = False

    def requested(self, dialog: SettingsDialog | None) -> None:
        """处理面板保存请求

        - 校验通过才关窗
        - 取消路径面板与已填内容原样保留
        """
        host = self._host
        if dialog is None:
            return

        new_config = dialog.get_modified_config()

        # 人设取面板草稿，旧值取生效正文，两者不同才算改过
        persona_old = applied_persona_text()
        persona_new = draft_persona_text()
        persona_changed = persona_new != persona_old

        # 重载按钮落下的取用记录，本次保存才把它写进文件
        pending = pending_persona()

        # 只有取用记录、正文没动的这一次也要落盘，不然文件永远追不上生效值
        file_needed = persona_changed or pending is not None

        changes, logs = compare_configs(
            config_manager.schema, config_manager.get_all(), new_config
        )

        # 对话身份由人设正文与主人构成，动过任一项都要起一轮清历史，配置未就绪时不报清空
        self.identity_changed = host._config_ready and (
            persona_changed
            or ConfigKey.OWNER in (changes.get(ConfigSection.CHORE) or {})
        )

        # 向导态或有任何改动都要起校验轮，通道没变时 Manager 只跑本地校验
        in_setup = host._current_mode == ConfigMode.SETUP
        if not changes and not file_needed:
            if not in_setup:
                NoticeDialog.notify(NOTICE_DIALOG.not_changed, parent=dialog)
                host.logger.debug("配置未修改")
                return
            self.start_recheck(dialog)
            return

        # 二次确认以面板为父级，取消后面板仍在
        persona: tuple[str, str] | None = None
        if persona_changed:
            persona = (persona_old, persona_new)
        elif pending is not None:
            persona = (pending.disk, pending.applied)
        if not ChangeConfirmDialog.confirm(logs, persona=persona, parent=dialog):
            return

        self.log_changes(logs, file_needed)

        # 先验后存，候选只进内存，通过才落盘，取消即回退
        self.start_verify(dialog, new_config, persona_new if persona_changed else None)

    def start_recheck(self, dialog: SettingsDialog) -> None:
        """向导态下未改动仍保存，起一轮纯复验

        - 复验不落盘，通过后只收检测窗
        """
        verify = self._host._verify
        if verify.validating:
            return
        verify.validating = True
        dialog.set_busy(True)
        self._host.logger.debug(
            CheckMessage.VERIFY_START.format(reason=CheckMessage.REASON_RECHECK)
        )
        if not verify.start_round(aborts=True):
            verify.validating = False
            dialog.set_busy(False)
            return

        # 复验走候选通道：校验对象必须是面板上屏值，禁走磁盘重载
        gui_bridge.config_candidate.emit()

    def start_verify(
        self, dialog: SettingsDialog, new_config: AppConfigData, persona: str | None
    ) -> None:
        """候选进内存并起保存校验轮

        - 人设草稿在校验前顶替生效缓存，身份判定才看得到新正文，历史本轮即清
        - 起轮失败即撤候选与待落盘标记，面板解除忙碌
        """
        verify = self._host._verify
        verify.pending_candidate = new_config
        verify.pending_persona = persona
        verify.save_pending = True
        dialog.set_busy(True)
        self._host.logger.debug(
            CheckMessage.VERIFY_START.format(reason=CheckMessage.REASON_SAVE)
        )
        if not verify.start_round(aborts=True):
            verify.pending_candidate = None
            verify.pending_persona = None
            verify.save_pending = False
            dialog.set_busy(False)
            return
        if persona is not None:
            apply_draft_persona()
        config_manager.load(new_config)
        gui_bridge.config_candidate.emit()

    def write_pending(self, candidate: AppConfigData) -> bool:
        """落盘本次校验通过的候选

        - 先验后存的落盘时刻：内存早已就位，磁盘只给验证过的内容
        - 正文写成功即重装生效缓存并抹掉取用记录
        - 写不进时动过缓存的退回文件内容，取用记录留着等下次重新拍板
        """
        verify = self._host._verify
        persona = verify.pending_persona
        pending = pending_persona()
        verify.pending_candidate = None
        verify.pending_persona = None
        try:
            save_config(candidate)
            self._host.logger.info(CheckMessage.WRITTEN)
        except ConfigOutputError as e:
            return self.write_failed(CheckMessage.WRITE_FAILED.format(err=e))

        # 没动正文只留过取用记录，这次写进文件的就是生效那一份
        text = persona
        if text is None and pending is not None:
            text = applied_persona_text()
        if text is None:
            return True
        if save_persona_text(text):
            drop_persona_pending()
            return True
        if persona is not None:
            revert_persona_cache()
        return self.write_failed(SETTINGS_DIALOG.persona_file_create_fail, True)

    def write_failed(self, reason: str, notice: bool = False) -> bool:
        """落盘失败收尾

        - 记错误、按需弹提示、解除面板忙碌，恒交未落盘
        """
        panel = self._host._panel
        self._host.logger.error(reason)
        if notice:
            NoticeDialog.notify(reason, parent=panel or self._host.gui)
        if panel is not None:
            panel.set_busy(False)
        return False

    def log_changes(self, logs: list, file_needed: bool) -> None:
        """分级记录变更日志

        - 人设正文不进逐行比对，只在变更清单里占一项
        - 只留过取用记录这一项也算动过正文，文件确实被换了一份内容
        """
        names = [name for name, _, _ in logs]
        if file_needed:
            names.append(SETTINGS_DIALOG.persona_label)
        joined = "、".join(names)
        self._host.logger.info(f"保存 {len(names)} 项配置: {joined}")
        if not logs:
            return
        detail = "".join(
            f"\n配置项：{key}\n原: {ori}\n新: {mod}" for key, ori, mod in logs
        )
        self._host.logger.debug(detail)
