# src/bot/_managers/_settings.py
"""配置管理器

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
from utils.connectivity import attempt_channel
from utils.net_probe import (
    Channel,
    FieldKey,
    FrameKey,
    RowId,
    RowStatus,
    plan_channels,
    scan_proxy_ports,
    verify_plan,
    via_label,
)
from utils.system_proxy import detect_system_proxy
from utils.verify_flow import local_row, run_channels

from ._base import BaseManager


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

        # 上次验证时的网络参数：(token, 配置代理)，变化判定基准
        self._net_state: tuple[str, str] = ("", "")

    # ==================== 配置加载与验证 ====================

    async def _execute(self) -> None:
        """加载配置进内存"""
        ensure_config()
        config_manager.load(load_config())

    async def verify_connectivity(self) -> bool:
        """按字段变化分流的连通校验

        - 通过则记录生效通道
        """
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
        sys_proxy = None if token_only else detect_system_proxy()
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
            channels = plan_channels(configured, sys_proxy)

        # 本地校验纯函数零耗时：先落定再发开局整表，网络在跑时本地已亮
        local_frame, type_errors = local_row(schema, config_manager.get_all())
        gui_bridge.verify_progress.emit(
            {
                FrameKey.ROWS: verify_plan(
                    channels,
                    reuse=token_only,
                    local_frame=local_frame,
                )
            }
        )

        # 并行调度交给公共核心：首成裁决，token 错不换道，成本日志留在探针闭包里
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

        outcome = await run_channels(
            channels,
            probe,
            gui_bridge.verify_progress.emit,
            via_label,
        )
        resolved = outcome.resolved
        net_errors = outcome.errors

        # 通道判通，port 行直接标跳过
        if outcome.passed:
            gui_bridge.verify_progress.emit(
                {
                    "id": RowId.PORT,
                    "status": RowStatus.SKIP,
                    "detail": CheckMessage.SKIP,
                }
            )

        # 全挂才扫本机端口：仅探测复测，不自动采用、不写配置
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
            # 单候选（仅直连）保留原始错误，多候选聚合为一句引导
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

        # 网络与本地两路错误合并，全绿才返回 True，收口认 advice
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

    async def _probe_ports(self, token: str) -> tuple[str, int]:
        """本机端口扫描复测

        - 返回 (首个 getMe 实测可通的 URL 或空串, 存活端口数)
        - TCP 存活不等于可出网，复测不过不提示
        - 全端口并发发射、按列表序收口：端口序即优先级，定案后剩余取消等落地
        """
        urls = await asyncio.to_thread(scan_proxy_ports)
        if not urls:
            return "", 0
        tasks = [asyncio.ensure_future(attempt_channel(token, url)) for url in urls]
        hit = ""
        try:
            # 按列表序逐个取结局：首个可通即定案，前面的已败不必再看
            for task in tasks:
                resolved, _ = await task
                if resolved is not None:
                    hit = resolved
                    break
        finally:
            # 定案/异常都清场：在途的掐掉并等落地，防 destroyed 噪声
            stragglers = [t for t in tasks if not t.done()]
            for task in stragglers:
                task.cancel()
            if stragglers:
                await asyncio.gather(*stragglers, return_exceptions=True)
        return hit, len(urls)

    def _warn_stale(self, raw: str, resolved: str) -> None:
        """配置值坏但被后续通道救活

        - 记错误提醒自改，不阻断启动
        """
        if raw and resolved != raw:
            via = (
                CheckMessage.VIA_DIRECT
                if not resolved
                else CheckMessage.VIA_SYSTEM.format(proxy=resolved)
            )
            self.logger.error(CheckMessage.STALE.format(raw=raw, via=via))
