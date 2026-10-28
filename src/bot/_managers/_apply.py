# src/bot/_managers/_apply.py
"""配置应用

- 校验当前配置并决定是否重启引擎
- 持有候选轮标记、生效通道、运行参数指纹与对话身份标记
"""

from typing import TYPE_CHECKING

from core.domain import ConfigKey, ConfigSection, FieldKey
from skin.messages import CheckMessage
from system.profile_env import get_profile, read_token
from ui import gui_bridge
from utils import config_manager
from utils.persona import applied_persona_text

from ..error_guard import error_guard

if TYPE_CHECKING:
    from ._manager import BotManager


class ConfigApplier:
    """配置应用器

    - 与 BotManager 一对一绑定，启停与子管理器由 host 持有
    - 持有生效通道与运行参数指纹，供引擎读取与跳过重启判定
    """

    def __init__(self, host: "BotManager") -> None:
        self._host = host

        # 候选校验轮标记：内存已是候选值，本次跳过磁盘重载
        self.skip_reload = False

        # 最近一次生效并重启过引擎的参数指纹：一致则跳过重启防闪断
        self._last_applied: tuple[str, str, float] | None = None

        # 三级解析出的生效通道，引擎与指纹均以此为准
        self._resolved_proxy: str | None = None

        # 上次生效的对话身份：(主人 id, 生效正文)，任一项变化即清历史
        self._last_identity: tuple[str, str] | None = None

    @error_guard("配置校验")
    async def apply_config(self) -> None:
        """应用当前配置

        - 失败弹向导等待再次保存，通过则重启服务
        """
        host = self._host
        if host._shutdown:
            return

        # 重验期间先收回就绪，阻止 EDIT 弹窗读到半新半旧的配置
        gui_bridge.config_ready_changed.emit(False)
        if self.skip_reload:
            # 候选轮：内存已是候选值，从盘重载会把它冲掉
            self.skip_reload = False
        else:
            await host._settings_manager.execute()
        if not await host._settings_manager.verify_connectivity():
            self._resolved_proxy = None

            errors = host._settings_manager.last_errors
            if self._is_token_fatal(errors):
                host._logger.error("Token 探测失败，弹窗引导退出")
                gui_bridge.request_notice.emit(CheckMessage.TOKEN_FATAL, True)
                return

            # 保持不就绪：数据修复完成前 EDIT 一律拦截
            self._request_setup(errors)
            return

        # 生效通道接引擎：配置不通时自动落到系统代理/直连
        self._resolved_proxy = host._settings_manager.resolved_proxy

        await self._reset_stale_identity()

        # 配置已加载且验证通过（数据先就位，最后广播）
        gui_bridge.config_ready_changed.emit(True)
        try:
            token, proxy = self.get_config_func()
            fingerprint = (
                token,
                proxy,
                config_manager.get(
                    ConfigKey.NETWORK_TIMEOUT.path(ConfigSection.GLOBAL), float
                ),
            )
        except Exception:  # 参数不可得：不做跳过优化，照常重启
            fingerprint = None
        if fingerprint is not None and self._last_applied == fingerprint:
            # 生效通道与引擎参数未变：验证通过即保持引擎运行，不闪断重启
            host._logger.info("配置验证通过，运行参数未变，跳过重启")
            return
        host.stop_service()
        await host._service_manager.execute()
        self._last_applied = fingerprint
        host._logger.info("配置验证通过，服务运行中")

    def _current_identity(self) -> tuple[str, str]:
        """取当前对话身份

        - 由主人 id 与生效正文两项构成
        """
        owner = config_manager.get(ConfigKey.OWNER.path(ConfigSection.CHORE), str)
        return (owner.strip(), applied_persona_text())

    async def reset_identity(self) -> bool:
        """清掉全部会话与落盘记录并把当前身份记成基准

        - 清理入口由插件声明，本层只按身份变化调用
        - 入口为空即不清也不落基准，下一轮或读取侧对账补上
        """
        resets = self._host._service_manager.history_resets
        if not resets:
            return False
        for reset in resets:
            await reset()
        self._last_identity = self._current_identity()
        self._host._logger.info("人设或主人已变更，全部对话历史与落盘记录已清空")
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
        """判定是否 token 致命错

        - token 报错即致命：面板改不了 token，只会拦在配置向导里出不去
        """
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

        - token 只从实例自描述文件读
        """
        return read_token(get_profile()), config_manager.get(
            ConfigKey.PROXY.path(ConfigSection.PROXY), str
        ).strip()
