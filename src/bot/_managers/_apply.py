# src/bot/_managers/_apply.py
"""配置应用

- 校验当前配置并决定是否重启引擎
- 持有候选轮标记、生效通道与运行参数指纹
"""

from typing import TYPE_CHECKING

from gui.mediator import gui_bridge
from messages import CheckMessage
from profile_env import get_profile, read_token
from utils import config_manager
from utils.net_probe import FieldKey

from ..error_guard import error_guard

if TYPE_CHECKING:
    from . import BotManager


class ConfigApplier:
    """配置应用器

    - 与 BotManager 一对一绑定，启停与子管理器由 host 持有
    - 生效通道与指纹归本器，供引擎读取与跳过重启判定
    """

    def __init__(self, host: "BotManager") -> None:
        self._host = host

        # 候选校验轮标记：内存已是候选值，本轮跳过磁盘重载
        self.skip_reload = False

        # 最近一次生效并重启过引擎的参数指纹：一致则跳过重启防闪断
        self._last_applied: tuple[str, str, float] | None = None

        # 三级解析出的生效通道，引擎与指纹均以此为准
        self._resolved_proxy: str | None = None

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

        # 配置已加载且验证通过（数据先就位，最后广播）
        gui_bridge.config_ready_changed.emit(True)
        try:
            token, proxy = self.get_config_func()
            fingerprint = (
                token,
                proxy,
                config_manager.get("global.network_timeout", float),
            )
        except Exception:  # 参数不可得：不做跳过优化，照常重启
            fingerprint = None
        if fingerprint is not None and self._last_applied == fingerprint:
            # 生效通道与引擎参数未变：验证通过即复用，不闪断重启
            host._logger.info("配置验证通过，运行参数未变，跳过重启")
            return
        host.stop_service()
        await host._service_manager.execute()
        self._last_applied = fingerprint
        host._logger.info("配置验证通过，服务运行中")

    def _request_setup(self, field_errors: dict[str, str] | None = None) -> None:
        """弹出强制配置向导"""
        self._host._logger.info("检测到配置有误，弹出配置向导...")
        gui_bridge.request_force_setup.emit(field_errors or {})

    def _is_token_fatal(self, errors: dict[str, str]) -> bool:
        """判定是否 token 致命错

        - proxy 已通而 token 仍错才是致命，token 已不在面板改不了
        - proxy 不通时 token 被标"暂未检测"，此时归代理故障走向导，不误退
        """
        return FieldKey.TOKEN in errors and FieldKey.PROXY not in errors

    def get_config_func(self) -> tuple[str, str]:
        """读取 Token 与生效 Proxy

        - 引擎与指纹专用
        - 三级解析通过后引擎走 resolved 通道
        - 未校验时退回配置原值
        """
        token, cfg = self.get_raw_config_func()
        if self._resolved_proxy is not None:
            return token, self._resolved_proxy
        return token, cfg

    @staticmethod
    def get_raw_config_func() -> tuple[str, str]:
        """读取校验专用的凭证与代理原值

        - token 从实例自描述文件读，配置里不再存 token
        """
        return read_token(get_profile()), config_manager.get("basic.proxy", str).strip()
