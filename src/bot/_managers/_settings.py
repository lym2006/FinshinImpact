# src/bot/_managers/_settings.py
"""配置管理器

- 实现配置加载与连通性双重校验
- 提供字段级错误文案供向导标红
"""

import time
from collections.abc import Awaitable, Callable
from typing import cast

from core.domain import ConfigKey, ConfigSection, ProxyMode
from skin.messages import CheckMessage
from ui import gui_bridge
from utils import config_manager
from utils.check import (
    ChannelOutcome,
    TelegramFieldKey,
    attempt_channel,
    local_row,
    run_channels,
)
from utils.config import (
    AppSchema,
    FieldErrors,
    ensure_config,
    get_schema,
    load_config,
)
from utils.network import (
    Channel,
    FrameKey,
    RowId,
    RowStatus,
    detect_system_proxy,
    plan_channels,
    sys_deduped,
    verify_plan,
    via_label,
)
from utils.network.probe import is_flap_hit, single_row_of

from ._base import BaseManager
from ._port_probe import verify_port_row


def _label_of(schema: AppSchema, key: str) -> str:
    """字段键映射界面标题"""
    for tab in schema:
        for fld in tab.fields:
            if fld.key == key:
                return fld.label
    return key


class SettingsManager(BaseManager):
    """配置加载与验证管理器

    - 加载配置、探测连通性
    - 致命错误弹窗终止，可恢复错误进 last_errors 供向导标注
    """

    LOGGER_NAME = "Settings"

    def __init__(self, get_config_func: Callable[[], tuple[str, str]]) -> None:
        """初始化配置管理器"""
        super().__init__()
        self._get_config = get_config_func

        # 最近一次验证失败：{配置键: 错误文案}，供向导标注字段
        self.last_errors: dict[str, str] = {}

        # 三级解析出的生效通道，未通过为 None，空串表示直连
        self.resolved_proxy: str | None = None

        # 上次验证时的网络参数：(token, 配置代理, 代理模式, 超时)，变化判定基准
        self._net_state: tuple[str, str, str, float] = ("", "", "", 0.0)

    async def _execute(self) -> None:
        """加载配置进内存"""
        ensure_config()
        config_manager.load(load_config())

    async def verify_connectivity(self) -> bool:
        """按字段变化分流的连通校验

        - 网络参数与 token 全未变且已连通过时只跑本地校验
        - 通过则记录生效通道
        - 单路模式只测选定通道，缺席不发探测
        - 自动模式全挂先原地重检一轮再报失败
        - 端口复测命中本次已探测端点即按抖动采用该通道
        """
        t0 = time.monotonic()
        schema = get_schema()
        prev_state = self._net_state
        prev_token, prev_cfg, _, _ = prev_state
        state = self._read_net_state()
        self._net_state = state
        token, configured, mode, _ = state

        if state == prev_state and self.resolved_proxy is not None:
            return self._local_round(schema, t0)

        channels, token_only, sys_dedup = self._plan_channels(
            token, configured, prev_token, prev_cfg, mode
        )

        # token 单独重跑时通道未变，通道行保持全行标生效，不按模式裁
        single = None if token_only else single_row_of(mode)
        type_errors = self._emit_opening(
            channels, token_only, sys_dedup, single, schema
        )
        if single is not None and not channels:
            # 单路选路缺地址：代理行被联动隐藏，缺席句标红落在可见的模式行上
            type_errors = {**type_errors, ConfigKey.PROXY_MODE: single[2]}
            self.resolved_proxy = None
            self.last_errors = cast("dict[str, str]", type_errors)
            self.logger.info(CheckMessage.ROUND_COST.format(cost=time.monotonic() - t0))
            return self._emit_advice(schema)

        probe = self._make_probe(token)
        emit = gui_bridge.verify_progress.emit
        outcome = await run_channels(channels, probe, emit, via_label)
        if not outcome.passed and mode == ProxyMode.AUTO and not token_only:
            # 首轮全挂多为冷启动握手慢：趁热连接原地重检一轮再定性
            self.logger.info(CheckMessage.RETRY_HEAD)

            # 重发整表清场：已定案的行不吃单行帧，不重建则首轮的红行盖不掉
            self._emit_opening(
                channels,
                token_only,
                sys_dedup,
                single,
                schema,
                head=CheckMessage.RETRY_HEAD,
            )
            outcome = await run_channels(channels, probe, emit, via_label)
        if single is not None:
            port_hint = ""
        else:
            port_hint = await verify_port_row(outcome, token, token_only)
        net_errors = self._aggregate_errors(outcome, channels, port_hint)
        if not outcome.passed and port_hint and is_flap_hit(channels, port_hint):
            # 复测用的正是刚判失败那条通道：同地址重探即通属抖动，不推荐重填
            outcome.passed = True
            outcome.resolved = configured
            net_errors.pop(TelegramFieldKey.PROXY, None)

        self._settle(outcome.resolved, configured, mode == ProxyMode.AUTO)
        self.last_errors = {**net_errors, **type_errors}
        self.logger.info(CheckMessage.ROUND_COST.format(cost=time.monotonic() - t0))
        return self._emit_advice(schema)

    def _read_net_state(self) -> tuple[str, str, str, float]:
        """读取连通校验用的网络参数

        - token、配置代理串、代理模式与超时四项
        """
        token, raw = self._get_config()
        proxy = config_manager.get_all().get(ConfigSection.PROXY) or {}
        return (
            token,
            raw.strip(),
            str(proxy.get(ConfigKey.PROXY_MODE, ProxyMode.AUTO)).strip(),
            config_manager.get(
                ConfigKey.NETWORK_TIMEOUT.path(ConfigSection.GLOBAL), float
            ),
        )

    def _local_round(self, schema: AppSchema, started: float) -> bool:
        """只跑本地校验的免测轮

        - 通道行整表标复用，生效通道原样保留
        """
        type_errors = self._emit_opening([], True, False, None, schema)
        self.last_errors = cast("dict[str, str]", type_errors)
        self.logger.info(
            CheckMessage.ROUND_COST.format(cost=time.monotonic() - started)
        )
        return self._emit_advice(schema)

    def _plan_channels(
        self,
        token: str,
        configured: str,
        prev_token: str,
        prev_cfg: str,
        mode: str,
    ) -> tuple[list[Channel], bool, bool]:
        """规划候选通道

        - 仅 token 变则直接采用生效通道，不重跑候选链
        - 返回 (通道表, token 复查标志, 系统代理去重标志)
        """
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
            return [Channel(kind, reuse)], True, False
        detected = detect_system_proxy()
        return (
            plan_channels(configured, detected, mode),
            False,
            sys_deduped(configured, detected),
        )

    def _emit_opening(
        self,
        channels: list[Channel],
        token_only: bool,
        sys_dedup: bool,
        single: tuple[str, str, str] | None,
        schema: AppSchema,
        *,
        head: str = "",
    ) -> FieldErrors:
        """发送首帧进度整表

        - 本地校验结果随首帧先行显示，不等网络探测
        - head 非空即同时给出弹窗头部提示
        - 返回本地类型错误供后续结论合并
        """
        local_frame, type_errors = local_row(schema, config_manager.get_all())
        frame: dict = {
            FrameKey.ROWS: verify_plan(
                channels,
                reuse=token_only,
                local_frame=local_frame,
                sys_dedup=sys_dedup,
                single=single,
            )
        }
        if head:
            frame[FrameKey.HEAD] = head
        gui_bridge.verify_progress.emit(frame)
        return type_errors

    def _make_probe(
        self, token: str
    ) -> Callable[[Channel], Awaitable[tuple[str | None, dict[str, str], str]]]:
        """构造单通道探针

        - token 错误时不换代理重试
        """

        async def probe(ch: Channel) -> tuple[str | None, dict[str, str], str]:
            start = time.monotonic()
            resolved, errors = await attempt_channel(token, ch.url)
            self.logger.debug(
                CheckMessage.COST.format(
                    via=via_label(ch), cost=time.monotonic() - start
                )
            )

            # 表格句留空由核心统一拼"称谓：可达/不可用"，errors 长句留给字段标红
            return resolved, errors, ""

        return probe

    def _aggregate_errors(
        self, outcome: ChannelOutcome, channels: list[Channel], port_hint: str
    ) -> dict[str, str]:
        """聚合代理错误

        - 仅直连单候选时保留原始错误，多候选聚合为一句引导
        """
        errors = dict(outcome.errors)
        if outcome.resolved is None and TelegramFieldKey.PROXY in errors:
            base = (
                CheckMessage.ALL_FAIL
                if len(channels) > 1
                else errors[TelegramFieldKey.PROXY]
            )
            if port_hint:
                base += f"\n{CheckMessage.PORT_HOVER.format(url=port_hint)}"
            elif len(channels) > 1:
                base += f"\n{CheckMessage.DIAGNOSE}"
            errors = {TelegramFieldKey.PROXY: base}
        return errors

    def _settle(self, resolved: str | None, configured: str, warn_stale: bool) -> None:
        """记录生效通道

        - 单路模式本路不通即失败，不发跨路降级告警
        """
        self.resolved_proxy = resolved
        if resolved is None:
            return
        via = (
            CheckMessage.VIA_DIRECT
            if not resolved
            else CheckMessage.VIA_CFG.format(proxy=resolved)
            if resolved == configured
            else CheckMessage.VIA_SYSTEM.format(proxy=resolved)
        )
        self.logger.info(CheckMessage.PASS.format(via=via))
        if warn_stale:
            self._warn_stale(configured, resolved)

    def _emit_advice(self, schema: AppSchema) -> bool:
        """发送结论帧

        - 失败只报数量，明细由字段标红与悬浮提示显示
        """
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
            self.logger.error(CheckMessage.FAIL.format(fields=fields))
        return passed

    def _warn_stale(self, raw: str, resolved: str) -> None:
        """记录配置代理失效但其他通道可用的告警

        - 提醒用户自行修改，不阻断启动
        """
        if raw and resolved != raw:
            via = (
                CheckMessage.VIA_DIRECT
                if not resolved
                else CheckMessage.VIA_SYSTEM.format(proxy=resolved)
            )
            self.logger.error(CheckMessage.STALE.format(raw=raw, via=via))
