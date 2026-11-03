# src/bot/_managers/_settings.py
"""配置管理器

- 配置加载与连通性双重校验
- 字段级错误文案供向导标红
"""

import time
from collections.abc import Awaitable, Callable
from typing import cast

from core.domain import ConfigKey, ConfigSection, FieldKey, ProxyMode
from skin.messages import CheckMessage
from ui import gui_bridge
from utils import config_manager
from utils.check import ChannelOutcome, local_row, run_probe_round
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
    fault_row_of,
    link_report,
    plan_channels,
    sys_deduped,
    uses_system_proxy,
    verify_plan,
    via_label,
)
from utils.network.probe import single_row_of
from utils.paths import PLATFORM

from .._registry import entry_for
from ._base import BaseManager

# 实例平台冻结的单通道探测入口
_CHANNEL_PROBE = entry_for(PLATFORM).channel_probe


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

        # 最近一轮网络探测的连通结论，与本地校验错身分开记
        self.link_verified = False

        # 上次验证时的网络参数：(配置代理, 代理模式, 系统代理)，变化判定基准
        self._net_state: tuple[str, str, str] = ("", "", "")

    async def _execute(self) -> None:
        """加载配置进内存"""
        ensure_config()
        config_manager.load(load_config())

    async def verify_connectivity(self) -> bool:
        """按字段变化分流的连通校验

        - 网络参数全未变、上轮连通通过且引擎不在断连周期时只跑本地校验
        - 通过则记录生效通道与连通结论
        - 单路模式只测选定通道，缺席不发探测
        - 每种模式首轮全挂都等待预热后重检一轮
        """
        t0 = time.monotonic()
        schema = get_schema()
        token, raw = self._get_config()
        detected = detect_system_proxy()
        state = self._read_net_state(raw, detected)
        configured, mode = state[:2]

        # 免测只认连通结论：系统代理一变旧结论就不作数，引擎正断线时更得重探
        down = link_report.snapshot().down
        if state == self._net_state and self.link_verified and not down:
            return self._local_round(schema)
        self._net_state = state

        # 起联网重探前先清旧结论：探测中途异常不该留下过时的连通账
        self.link_verified = False
        channels = plan_channels(configured, detected, mode=mode)
        sys_dedup = sys_deduped(configured, detected)
        single = single_row_of(mode)
        type_errors = self._emit_opening(channels, sys_dedup, single, schema)
        if single is not None and not channels:
            # 缺席的选路填不上地址：红点落在看得见的那一行
            net_errors: dict[str, str] = {fault_row_of(mode): single[2]}
            resolved: str | None = None
        else:
            probe = self._make_probe(token)
            outcome = await run_probe_round(
                channels,
                probe,
                gui_bridge.verify_progress.emit,
                via_label,
                lambda: self._emit_opening(
                    channels, sys_dedup, single, schema, head=CheckMessage.RETRY_HEAD
                ),
            )
            net_errors = self._aggregate_errors(outcome, channels, mode)
            resolved = outcome.resolved

        self._settle(resolved, configured, mode == ProxyMode.AUTO)

        # 连通判据独立记：探到可用通道才算通，本地类型错不参与
        self.link_verified = resolved is not None
        self.last_errors = {**net_errors, **type_errors}
        self.logger.info(CheckMessage.ROUND_COST.format(cost=time.monotonic() - t0))
        return self._emit_advice(schema)

    def _read_net_state(
        self, configured: str, sys_proxy: str | None
    ) -> tuple[str, str, str]:
        """读取连通校验用的网络参数

        - 配置代理串、代理模式与系统代理地址三项
        - 用得到系统代理的档位才计入它，另两档的开关变化与连通校验无关
        """
        proxy = config_manager.get_all().get(ConfigSection.PROXY) or {}
        mode = str(proxy.get(ConfigKey.PROXY_MODE, ProxyMode.AUTO)).strip()
        return (
            configured.strip(),
            mode,
            (sys_proxy or "") if uses_system_proxy(mode) else "",
        )

    def _local_round(self, schema: AppSchema) -> bool:
        """只跑本地校验的免测轮

        - 不发进度帧，秒过的轮次不占等待窗
        - 一个探测包都没发，只报免测不报用时
        """
        _, type_errors = local_row(schema, config_manager.get_all())
        self.last_errors = cast("dict[str, str]", type_errors)
        self.logger.info(CheckMessage.LOCAL_ONLY)
        return self._emit_advice(schema)

    def _emit_opening(
        self,
        channels: list[Channel],
        sys_dedup: bool,
        single: tuple[str, str, str] | None,
        schema: AppSchema,
        *,
        head: str = "",
    ) -> FieldErrors:
        """发送首帧进度整表

        - 本地校验结果随首帧先行显示，不等网络探测
        - head 非空即重发整表清场，已定案的红行不吃单行帧
        - 返回本地类型错误供后续结论合并
        """
        local_frame, type_errors = local_row(schema, config_manager.get_all())
        frame: dict = {
            FrameKey.ROWS: verify_plan(
                channels,
                local_frame=local_frame,
                sys_dedup=sys_dedup,
                single=single,
            )
        }
        if head:
            frame[FrameKey.HEAD] = head
            self.logger.debug(head)
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
            resolved, errors = await _CHANNEL_PROBE(token, ch.url)
            self.logger.debug(
                CheckMessage.COST.format(
                    via=via_label(ch), cost=time.monotonic() - start
                )
            )

            # 表格句留空由核心统一拼"称谓：可达/不可用"，errors 长句留给字段标红
            return resolved, errors, ""

        return probe

    def _aggregate_errors(
        self, outcome: ChannelOutcome, channels: list[Channel], mode: str
    ) -> dict[str, str]:
        """聚合代理错误

        - 多候选聚合为一句引导，单候选保留原始错误
        - 尾句指引用户自查代理软件
        - 红点行由档位单源判据给出
        """
        errors = dict(outcome.errors)
        if outcome.resolved is None and FieldKey.PROXY in errors:
            base = (
                CheckMessage.ALL_FAIL if len(channels) > 1 else errors[FieldKey.PROXY]
            )
            errors = {
                fault_row_of(mode): f"{base}\n{CheckMessage.PROXY_GUIDE}",
            }
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
