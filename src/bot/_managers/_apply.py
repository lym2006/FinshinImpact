# src/bot/_managers/_apply.py
"""配置应用

- 校验当前配置并决定是否重启引擎
"""

from typing import TYPE_CHECKING

from finshin_sdk.domain import ConfigKey, ConfigSection, FieldKey, PlatformMoment
from skin.messages import CheckMessage, DialogMessage
from system.profile_env import get_profile, read_token
from ui import gui_bridge
from utils import config_manager
from utils.init_files import save_persona_text
from utils.network import link_report
from utils.persona import applied_persona_text, load_persona_cache, save_applied_persona

from ..error_guard import error_guard

if TYPE_CHECKING:
    from ._manager import BotManager


class ConfigApplier:
    """配置应用器"""

    def __init__(self, host: "BotManager") -> None:
        self._host = host

        # 候选校验轮标记：内存已是候选值，本次跳过磁盘重载
        self.skip_reload = False

        # 最近一次生效并重启过引擎的参数指纹：一致则跳过重启防闪断
        self._last_applied: tuple[str, str] | None = None

        # 三级解析出的生效通道，引擎与指纹均以此为准
        self._resolved_proxy: str | None = None

        # 上次生效的对话身份：(主人 id, 生效正文)，任一项变化即清历史
        self._last_identity: tuple[str, str] | None = None

    @error_guard("配置校验")
    async def apply_config(self) -> None:
        """应用当前配置

        - 校验通过才重启服务，引擎只吃验过的值
        - 没过即把内存回退并交向导说话
        """
        host = self._host
        if host._shutdown:
            return

        # 重验期间先收回就绪，阻止 EDIT 弹窗读到半新半旧的配置
        gui_bridge.config_ready_changed.emit(False)

        # 候选轮的内存已装候选值，开头从盘重载会冲掉它
        from_candidate = self.skip_reload
        self.skip_reload = False
        if not from_candidate:
            await host._settings_manager.execute()
        if not await host._settings_manager.verify_connectivity():
            await self._settle_failure(from_candidate)
            return

        # 生效通道接引擎：配置不通时自动落到系统代理/直连
        self._resolved_proxy = host._settings_manager.resolved_proxy

        await self._reset_stale_identity()

        try:
            fingerprint = self.get_config_func()
        except Exception:  # 参数不可得：不做跳过优化，照常重启
            fingerprint = None
        if fingerprint is not None and self._last_applied == fingerprint:
            # 生效通道与引擎参数未变：验证通过即保持引擎运行，不闪断重启
            host._logger.info("配置验证通过，运行参数未变，跳过重启")
            await self._announce_config_ready()
            return

        # 只有换掉在跑的服务才叫重启：首次起服务由启动日志说话，不弹重启窗
        hot_restart = self._last_applied is not None
        if hot_restart:
            gui_bridge.service_restarting.emit(True)
        try:
            host.stop_service()
            await host._service_manager.execute()
            self._last_applied = fingerprint
            host._logger.info("配置验证通过，服务运行中")
        except Exception:
            if hot_restart:
                # 重启半路报错：收掉等待窗，结论交护栏那条路说
                gui_bridge.service_restarting.emit(False)
            raise

        # 配置已加载且引擎已就位，最后广播：结果由界面写进重启那只窗
        await self._announce_config_ready()

    async def _settle_failure(self, from_candidate: bool) -> None:
        """校验没过的收尾

        - 候选轮把内存退回盘上的可信值，非候选轮内存本就和盘一致
        - 代理不通作废断连周期，配置问题只由向导说话
        """
        host = self._host
        if from_candidate:
            await host._settings_manager.execute()
        if not host._settings_manager.link_verified:
            # 代理不通或没探成：引擎失败源于代理，作废链路账，断连窗不踩配置向导
            link_report.reset("配置校验没过")
        self._resolved_proxy = None

        errors = host._settings_manager.last_errors
        if self._is_token_fatal(errors):
            host._logger.error("Token 探测失败，弹窗引导退出")
            gui_bridge.request_notice.emit(CheckMessage.TOKEN_FATAL, True)
            return

        # 保持不就绪：数据修复完成前 EDIT 一律拦截
        self._request_setup(errors)

    async def _announce_config_ready(self) -> None:
        """向订阅了配置校验通过时机的件交代

        - 同时发就绪旗，界面据此收尾
        - 跳过重启与真重启两支都走这里，订阅侧不必自己分辨
        """
        gui_bridge.config_ready_changed.emit(True)
        hooks = self._host._service_manager.runs_for(PlatformMoment.CONFIG_VERIFIED)
        call = self._host._service_manager.capability_call()
        for hook in hooks:
            await hook(call)

    def _current_identity(self) -> tuple[str, str]:
        """取当前对话身份

        - 由主人 id 与生效正文两项构成
        """
        owner = config_manager.get(ConfigKey.OWNER.path(ConfigSection.CHORE), str)
        return (owner.strip(), applied_persona_text())

    async def commit_persona(self, text: str, source: str) -> None:
        """人设正文一次独立落盘

        - 文件与存档都写成才换正文
        - 正文与生效值相同即只结清文件，不动历史
        - 换了正文才清历史，清完把新身份记成基准
        - 来源词只写进换版那条，正文没变即无来源可报
        """
        # 写坏一次不能出现正文新、文件旧
        if not save_persona_text(text) or not save_applied_persona(text):
            gui_bridge.request_notice.emit(
                DialogMessage.SETUP_PERSONA_FILE_CREATE_FAIL, False
            )
            return
        changed = text != applied_persona_text()
        load_persona_cache()
        if changed:
            await self.reset_identity()
        tip = (
            DialogMessage.PERSONA_APPLIED_RESET.format(source=source)
            if changed
            else DialogMessage.PERSONA_APPLIED_KEPT
        )
        gui_bridge.request_persona_applied.emit(tip)

    async def reset_identity(self) -> bool:
        """清掉全部会话与落盘记录

        - 没件订阅「身份变了」即不清也不落基准，下一轮或读取侧对账补上
        """
        hooks = self._host._service_manager.runs_for(PlatformMoment.IDENTITY_CHANGED)
        if not hooks:
            return False
        call = self._host._service_manager.capability_call()
        for hook in hooks:
            await hook(call)
        self._last_identity = self._current_identity()
        return True

    async def _reset_stale_identity(self) -> None:
        """人设正文或主人变更后立即清掉对话历史

        - 首次应用只记基准，不动已有历史
        """
        identity = self._current_identity()
        if self._last_identity is not None and self._last_identity != identity:
            await self.reset_identity()
            return
        self._last_identity = identity

    def _request_setup(self, field_errors: dict[str, str] | None = None) -> None:
        """弹出强制配置向导"""
        self._host._logger.info("检测到配置有误，弹出配置向导...")
        gui_bridge.request_force_setup.emit(field_errors or {})

    def _is_token_fatal(self, errors: dict[str, str]) -> bool:
        """判定是否凭证致命错"""
        # 面板改不了凭证，拦在配置向导里出不去，故报错即致命
        return FieldKey.TOKEN in errors

    def get_config_func(self) -> tuple[str, str]:
        """读取 Token 与生效 Proxy

        - 供引擎与运行参数指纹读取
        - 校验通过后返回生效通道，未校验时返回配置原值
        """
        token, cfg = self.get_raw_config_func()
        if self._resolved_proxy is not None:
            return token, self._resolved_proxy
        return token, cfg

    @staticmethod
    def get_raw_config_func() -> tuple[str, str]:
        """读取校验专用的凭证与代理原值

        - 凭证从实例自描述文件读
        """
        return read_token(get_profile()), config_manager.get(
            ConfigKey.PROXY.path(ConfigSection.PROXY), str
        ).strip()
