# src/bot/_managers/_settings/__init__.py
"""配置管理器（内部实现）

- 实现配置加载与连通性双重校验
- 提供字段级错误文案供向导标红
"""

import asyncio
import time
from collections.abc import Callable
from typing import cast

from utils import config_manager, detect_system_proxy, scan_proxy_ports
from utils.config import (
    AppSchema,
    ensure_config,
    get_schema,
    load_config,
    validate_types,
)

from .._base import BaseManager
from ._connectivity import check_config

# 单次验证的硬超时
_VERIFY_TIMEOUT = 7.0

__all__ = ["SettingsManager"]


def _label_of(schema: AppSchema, key: str) -> str:
    """字段键映射界面标题"""
    for tab in schema:
        for fld in tab.fields:
            if fld.key == key:
                return fld.label
    return key


def _build_candidates(configured: str, sys_proxy: str | None) -> list[str]:
    """组装三级通道候选

    配置代理 → 系统代理 → 直连；重复地址去重，直连恒为末位兜底。
    """
    candidates: list[str] = []
    if configured:
        candidates.append(configured)
    if sys_proxy and sys_proxy not in candidates:
        candidates.append(sys_proxy)
    candidates.append("")  # 直连兜底：OS 层 TUN 生效时此步即通
    return candidates


class SettingsManager(BaseManager):
    """配置加载与验证管理器

    加载配置、探测连通性；
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
        """按字段变化分流的连通校验

        仅 token 变时复用生效通道单点探测，不重跑候选链；
        其余情况配置代理 → 系统代理 → 直连，谁先通过谁生效；
        仅 token 错时不换道直接上报；三通道全挂再走本机端口扫描兜底。
        """
        schema = get_schema()
        prev_token, prev_cfg = self._net_state
        token, raw = self._get_config()
        configured = raw.strip()
        self._net_state = (token, configured)

        token_only = (
            self.resolved_proxy is not None
            and configured == prev_cfg
            and token != prev_token
        )
        if token_only:
            # 代理字段未动：通道已验证过，只对 token 单点复查
            candidates = [cast(str, self.resolved_proxy)]
        else:
            candidates = _build_candidates(configured, detect_system_proxy())

        resolved: str | None = None
        net_errors: dict[str, str] = {}
        start = time.monotonic()
        for proxy in candidates:
            probe_start = time.monotonic()
            resolved, net_errors = await self._attempt_channel(token, proxy)
            self.logger.debug(
                f"通道 {proxy or '直连'} 探测耗时"
                f" {time.monotonic() - probe_start:.1f}s"
            )
            if resolved is not None or (net_errors and "proxy" not in net_errors):
                break  # 通过，或通道已通仅 token 错：换道无意义

        # 三通道全挂才扫本机端口：仅探测复测，不自动采用、不写配置
        port_hint = ""
        if resolved is None and "proxy" in net_errors and not token_only:
            port_hint = await self._probe_ports(token)

        if resolved is None and "proxy" in net_errors:
            # 单候选（仅直连）保留原始错误；多候选聚合为一句引导
            base = (
                "配置代理 / 系统代理 / 直连均无法连通"
                if len(candidates) > 1
                else net_errors["proxy"]
            )
            if port_hint:
                self.logger.error(
                    f"检测到可用本地代理 {port_hint}，"
                    "请确认后填入代理配置，程序不会自动采用"
                )
                base += f"；检测到可用端口 {port_hint}，请确认后填入"
            elif len(candidates) > 1:
                base += "，请点「网络诊断」自查"
            net_errors = {"proxy": base}
        self.resolved_proxy = resolved
        if resolved is not None:
            via = (
                "直连"
                if not resolved
                else "配置代理"
                if resolved == configured
                else f"系统代理 {resolved}"
            )
            self.logger.info(
                f"连通校验通过：生效通道 {via}"
                f"（耗时 {time.monotonic() - start:.1f}s）"
            )
            self._warn_stale(configured, resolved)

        type_errors = validate_types(schema, config_manager.get_all())
        self.last_errors = {**net_errors, **type_errors}

        # 级别只有 info/error/debug；"未检测"项由词表标黄
        for key, text in self.last_errors.items():
            self.logger.error(f"[{_label_of(schema, key)}] {text}")
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
            attempt = {"proxy": f"验证超时（>{_VERIFY_TIMEOUT:.0f}s）"}
        if not attempt:
            return proxy, {}
        return None, attempt

    async def _probe_ports(self, token: str) -> str:
        """本机端口扫描复测

        返回首个 getMe 实测可通的 URL 供提示；TCP 存活不等于
        可出网，复测不过不提示。TCP 探活走线程池防卡事件循环。
        """
        urls = await asyncio.to_thread(scan_proxy_ports)
        for url in urls:
            resolved, _ = await self._attempt_channel(token, url)
            if resolved is not None:
                return url
        return ""

    def _warn_stale(self, raw: str, resolved: str) -> None:
        """配置值坏但被后续通道救活

        记错误提醒自改，不阻断启动
        """
        if raw and resolved != raw:
            via = f"系统代理 {resolved}" if resolved else "直连"
            self.logger.error(f"配置代理 {raw!r} 不可用，本次改用{via}，请自行修正")
