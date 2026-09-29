# src/bot/_managers/_settings/__init__.py
"""配置管理器（内部实现）

- 实现配置加载与连通性双重校验
- 提供字段级错误文案供向导标红
"""

import asyncio
import time
from collections.abc import Callable
from typing import cast

from gui.mediator import gui_bridge
from messages import CheckMessage
from utils import config_manager
from utils.config import (
    AppSchema,
    ensure_config,
    get_schema,
    load_config,
)
from utils.net_probe import (
    Channel,
    FieldKey,
    FrameKey,
    RowId,
    RowStatus,
    plan_channels,
    scan_proxy_ports,
    verify_plan,
)
from utils.system_proxy import detect_system_proxy
from utils.verify_flow import run_channels, run_local

from .._base import BaseManager
from ._connectivity import check_config

_VERIFY_TIMEOUT = 4.0  # 单次验证的硬超时：早于内层 3 秒探测＋握手余量

__all__ = ["SettingsManager"]


def _via_label(ch: Channel) -> str:
    """通道行的展示称谓：直连裸称，代理类一律带地址，与诊断域同款"""
    if not ch.url:
        return CheckMessage.VIA_DIRECT
    if ch.kind == RowId.CFG:
        return CheckMessage.VIA_CFG.format(proxy=ch.url)
    return CheckMessage.VIA_SYSTEM.format(proxy=ch.url)


def _label_of(schema: AppSchema, key: str) -> str:
    """字段键映射界面标题"""
    for tab in schema:
        for fld in tab.fields:
            if fld.key == key:
                return fld.label
    return key


class SettingsManager(BaseManager):
    """配置加载与验证管理器

    加载配置、探测连通性。
    致命错误弹窗终止，可恢复错误进 last_errors 供向导标注。
    """

    LOGGER_NAME = "Settings"

    def __init__(self, get_config_func: Callable[[], tuple[str, str]]) -> None:
        """初始化配置管理器"""
        super().__init__()
        self._get_config = get_config_func

        # 最近一次验证失败：{配置键: 错误文案}，供向导标注字段
        self.last_errors: dict[str, str] = {}

        # 三级解析出的生效通道，未通过为 None；空串表示直连
        self.resolved_proxy: str | None = None

        # 上次验证时的网络参数：(token, 配置代理)，变化判定基准
        self._net_state: tuple[str, str] = ("", "")

    # ==================== 配置加载与验证 ====================

    async def _execute(self) -> None:
        """加载配置进内存"""
        ensure_config()
        config_manager.load(load_config())

    async def verify_connectivity(self) -> bool:
        """按字段变化分流的连通校验，通过则记录生效通道"""
        schema = get_schema()
        prev_token, prev_cfg = self._net_state
        token, raw = self._get_config()
        configured = raw.strip()
        self._net_state = (token, configured)

        # 分流判定：仅 token 变则复用生效通道，不重跑候选链
        token_only = (
            self.resolved_proxy is not None
            and configured == prev_cfg
            and token != prev_token
        )
        if token_only:
            # 代理字段未动：通道已验证过，只对 token 单点复查
            reuse = cast(str, self.resolved_proxy)
            kind = (
                RowId.DIRECT
                if not reuse
                else (RowId.CFG if reuse == configured else RowId.SYS)
            )
            channels = [Channel(kind, reuse)]
        else:
            channels = plan_channels(configured, detect_system_proxy())

        gui_bridge.verify_progress.emit(
            {FrameKey.ROWS: verify_plan(channels, reuse=token_only)}
        )

        # 逐通道调度交给公共核心：先通者生效，token 错不换道，成本日志留在探针闭包里
        async def probe(ch: Channel) -> tuple[str | None, dict[str, str], str]:
            start = time.monotonic()
            resolved, errors = await self._attempt_channel(token, ch.url)
            self.logger.debug(
                CheckMessage.COST.format(
                    via=_via_label(ch), cost=time.monotonic() - start
                )
            )
            # 表格句留空由核心统一拼"称谓：可达/不可达"；errors 长句留给字段标红
            return resolved, errors, ""

        outcome = await run_channels(
            channels,
            probe,
            gui_bridge.verify_progress.emit,
            _via_label,
        )
        resolved = outcome.resolved
        net_errors = outcome.errors

        # 通道判通即 port 行无戏可唱：直接标跳过
        if outcome.passed:
            gui_bridge.verify_progress.emit(
                {
                    "id": RowId.PORT,
                    "status": RowStatus.SKIP,
                    "detail": CheckMessage.SKIP,
                }
            )

        # 三通道全挂才扫本机端口：仅探测复测，不自动采用、不写配置
        port_hint = ""
        if not outcome.passed and FieldKey.PROXY in net_errors and not token_only:
            gui_bridge.verify_progress.emit(
                {"id": RowId.PORT, "status": RowStatus.CHECKING, "detail": ""}
            )
            port_hint, alive = await self._probe_ports(token)
            if port_hint:
                status, port_detail = (
                    RowStatus.OK,
                    CheckMessage.VERIFY_PORT_HIT.format(url=port_hint),
                )
            elif not alive:
                status, port_detail = (
                    RowStatus.FAIL,
                    CheckMessage.VERIFY_PORT_EMPTY,
                )
            else:
                status, port_detail = (
                    RowStatus.FAIL,
                    CheckMessage.VERIFY_PORT_NONE,
                )
            gui_bridge.verify_progress.emit(
                {"id": RowId.PORT, "status": status, "detail": port_detail}
            )

        if resolved is None and FieldKey.PROXY in net_errors:
            # 单候选（仅直连）保留原始错误；多候选聚合为一句引导
            base = (
                CheckMessage.ALL_FAIL
                if len(channels) > 1
                else net_errors[FieldKey.PROXY]
            )
            if port_hint:
                base += f"\n{CheckMessage.PORT_HOVER.format(url=port_hint)}"
            elif len(channels) > 1:
                base += f"\n{CheckMessage.DIAGNOSE}"
            net_errors = {FieldKey.PROXY: base}

        # 结果落地：聚合错误，或标注生效通道
        self.resolved_proxy = resolved
        if resolved is not None:
            via = (
                CheckMessage.VIA_DIRECT
                if not resolved
                else CheckMessage.VIA_CFG.format(proxy=resolved)
                if resolved == configured
                else CheckMessage.VIA_SYSTEM.format(proxy=resolved)
            )
            self.logger.info(CheckMessage.PASS.format(via=via))
            self._warn_stale(configured, resolved)

        # 并入本地类型校验，全绿才返回 True；local 先 advice 后，收口认 advice
        type_errors = run_local(
            schema, config_manager.get_all(), gui_bridge.verify_progress.emit
        )
        self.last_errors = {**net_errors, **type_errors}

        # 结论帧收口：表格 HTML 吞换行，失败只报计数，明细由字段标红与悬浮承载
        passed = not self.last_errors
        gui_bridge.verify_progress.emit(
            {
                "id": RowId.ADVICE,
                "status": RowStatus.OK if passed else RowStatus.FAIL,
                "detail": (
                    CheckMessage.ADVICE_OK
                    if passed
                    else CheckMessage.VERIFY_ADVICE_FAIL.format(n=len(self.last_errors))
                ),
            }
        )

        if self.last_errors:
            fields = "、".join(_label_of(schema, k) for k in self.last_errors)
            self.logger.error(CheckMessage.CHECK_FAIL.format(fields=fields))
        return not self.last_errors

    async def _attempt_channel(
        self, token: str, proxy: str
    ) -> tuple[str | None, dict[str, str]]:
        """单通道探测一次

        返回 (生效通道或 None, 错误字典)；空错误即该通道通过。
        """
        try:
            attempt = await asyncio.wait_for(
                check_config(token, proxy), timeout=_VERIFY_TIMEOUT
            )
        except TimeoutError:
            attempt = {FieldKey.PROXY: CheckMessage.TIMEOUT}
        if not attempt:
            return proxy, {}
        return None, attempt

    async def _probe_ports(self, token: str) -> tuple[str, int]:
        """本机端口扫描复测

        返回 (首个 getMe 实测可通的 URL 或空串, 存活端口数)。
        TCP 存活不等于可出网，复测不过不提示。
        TCP 探活走线程池防卡事件循环。
        """
        urls = await asyncio.to_thread(scan_proxy_ports)
        for url in urls:
            resolved, _ = await self._attempt_channel(token, url)
            if resolved is not None:
                return url, len(urls)
        return "", len(urls)

    def _warn_stale(self, raw: str, resolved: str) -> None:
        """配置值坏但被后续通道救活

        记错误提醒自改，不阻断启动
        """
        if raw and resolved != raw:
            via = (
                CheckMessage.VIA_DIRECT
                if not resolved
                else CheckMessage.VIA_SYSTEM.format(proxy=resolved)
            )
            self.logger.error(CheckMessage.STALE.format(raw=raw, via=via))
