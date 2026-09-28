# src/utils/verify_flow.py
"""连通校验公共核心

- 通道阶梯调度单源：逐通道探测、前级已通短路跳过、同款进度帧
- 探测方式由调用方以探针注入，本模块不关心 token 与网络栈细节
- 端口复测与结论聚合留各调用方：诊断与校验在此两处语义本就不同
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from messages import CheckMessage

from .config import AppConfigData, AppSchema, validate_types
from .net_probe import Channel, FieldKey, RowId, RowStatus

# 探针契约：返回 (生效地址或 None, 错误字典)，与 _attempt_channel 同形
_Probe = Callable[[Channel], Awaitable[tuple[str | None, dict[str, str]]]]
_Emit = Callable[[dict], None]
_StopCheck = Callable[[], bool]
_ViaLabel = Callable[[Channel], str]

__all__ = ["ChannelOutcome", "run_channels", "run_local"]


@dataclass
class ChannelOutcome:
    """一轮通道阶梯调度的收口"""

    resolved: str | None = None
    errors: dict[str, str] = field(default_factory=dict)
    passed: bool = False  # 有任一通道判 OK（含"通道通仅 token 错"）即短路成功


def _never_stop() -> bool:
    """默认停止回调：永不中断"""
    return False


# ==================== 核心业务逻辑 ====================


async def run_channels(
    channels: Sequence[Channel],
    probe: _Probe,
    emit: _Emit,
    via_label: _ViaLabel,
    stop_check: _StopCheck | None = None,
) -> ChannelOutcome:
    """逐通道走阶梯，每行先 checking 再结果，与两窗同款帧协议

    探针返回 None 且错误含 proxy 键即通道不通；"通道通仅 token 错"判 OK 不换道。
    首个 OK 后剩余通道整行标跳过并短路收尾，stop_check 置真则中途静默返回。
    """
    stop = stop_check or _never_stop
    outcome = ChannelOutcome()
    for idx, ch in enumerate(channels):
        if stop():
            return outcome
        emit({"id": ch.kind, "status": RowStatus.CHECKING, "detail": ""})
        resolved, errors = await probe(ch)
        outcome.errors = errors
        ch_ok = resolved is not None or bool(errors and FieldKey.PROXY not in errors)
        detail = (
            CheckMessage.REACH.format(via=via_label(ch), state=CheckMessage.REACH_OK)
            if ch_ok
            else errors.get(FieldKey.PROXY, CheckMessage.REACH_FAIL)
        )
        emit(
            {
                "id": ch.kind,
                "status": RowStatus.OK if ch_ok else RowStatus.FAIL,
                "detail": detail,
            }
        )
        if ch_ok:
            outcome.resolved = resolved
            outcome.passed = True
            for rest in channels[idx + 1 :]:
                emit(
                    {
                        "id": rest.kind,
                        "status": RowStatus.SKIP,
                        "detail": CheckMessage.SKIP,
                    }
                )
            break
    return outcome


def run_local(
    schema: AppSchema,
    config: AppConfigData,
    emit: _Emit,
) -> dict[str, str]:
    """本地配置校验：产出 local 行两帧，返回类型错误字典

    与网络探针并列的第三类检查，纯函数零阻塞，仅校验轮渲染本地配置行。
    """
    emit({"id": RowId.LOCAL, "status": RowStatus.CHECKING, "detail": ""})
    errors = validate_types(schema, config)
    emit(
        {
            "id": RowId.LOCAL,
            "status": RowStatus.OK if not errors else RowStatus.FAIL,
            "detail": (
                CheckMessage.VERIFY_LOCAL_OK
                if not errors
                else CheckMessage.VERIFY_LOCAL_FAIL.format(n=len(errors))
            ),
        }
    )
    return errors
