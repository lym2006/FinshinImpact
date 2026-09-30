# src/utils/verify_flow.py
"""连通校验公共核心

- 通道并行调度单源：全通道同时发射、按阶梯顺序首成裁决、同款进度帧
- 探测方式由调用方以探针注入，本模块不关心 token 与网络栈细节
- 超时预算归探针自持；端口复测与结论聚合留各调用方：两处语义本就不同
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from messages import CheckMessage

from .config import AppConfigData, AppSchema, validate_types
from .net_probe import Channel, FieldKey, RowId, RowStatus

# 探针契约：返回 (生效地址或 None, 字段错误字典, 表格展示句)
# 表格展示句留空时由核心按"称谓：可达/不可达"统一拼装；缺席句等特例才显式覆盖
_Probe = Callable[[Channel], Awaitable[tuple[str | None, dict[str, str], str]]]
_Emit = Callable[[dict], None]
_StopCheck = Callable[[], bool]
_ViaLabel = Callable[[Channel], str]

# 探针裁决：(通道可走, 生效地址, 字段错误, 表格展示句)
_Verdict = tuple[bool, str | None, dict[str, str], str]

__all__ = ["ChannelOutcome", "run_channels", "local_row"]


@dataclass
class ChannelOutcome:
    """一轮通道并行调度的收口"""

    resolved: str | None = None
    errors: dict[str, str] = field(default_factory=dict)
    passed: bool = False  # 任一通道可走即真（含"通道通仅 token 错"）


def _never_stop() -> bool:
    """默认停止回调：永不中断"""
    return False


# ==================== 核心业务逻辑 ====================


async def _probe_safe(ch: Channel, probe: _Probe) -> _Verdict:
    """执行单通道探针：探针自身异常折为该通道 fail，取消原样上抛

    炸一行不掀桌：一只耗子的异常只判死它自己的通道。
    """
    try:
        resolved, errors, detail = await probe(ch)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        return False, None, {FieldKey.PROXY: CheckMessage.SELF_CRASH.format(err=e)}, ""
    ok = resolved is not None or bool(errors and FieldKey.PROXY not in errors)
    return ok, resolved, errors, detail


def _settle_frame(ch: Channel, verdict: _Verdict, via_label: _ViaLabel) -> dict:
    """组单行终态帧：展示句留空即按称谓统一拼装成败句"""
    ok, _, _, detail = verdict
    text = detail or CheckMessage.REACH.format(
        via=via_label(ch),
        state=CheckMessage.REACH_OK if ok else CheckMessage.REACH_FAIL,
    )
    return {"id": ch.kind, "status": RowStatus.OK if ok else RowStatus.FAIL, "detail": text}


async def run_channels(
    channels: Sequence[Channel],
    probe: _Probe,
    emit: _Emit,
    via_label: _ViaLabel,
    stop_check: _StopCheck | None = None,
) -> ChannelOutcome:
    """全通道并行发射，按阶梯顺序首成裁决，与两窗同款帧协议

    在场通道同时标 checking，行有结局即点亮；高优先未交代前，低优先先通不抢答。
    首个可走即定案，剩余在途取消并标跳过；stop_check 置真整体让路不发终态帧。
    """
    stop = stop_check or _never_stop
    outcome = ChannelOutcome()
    order = list(channels)
    if not order:
        return outcome
    for ch in order:
        emit({"id": ch.kind, "status": RowStatus.CHECKING, "detail": ""})

    tasks = {asyncio.ensure_future(_probe_safe(ch, probe)): ch for ch in order}
    pending = set(tasks)
    verdicts: dict[str, _Verdict] = {}
    winner: Channel | None = None
    while pending and winner is None:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        if stop():
            break
        for task in done:
            ch = tasks[task]
            verdict = task.result()
            # 定案后的迟到结局（陪跑抢先完成那一瞬）不再点亮，留给清场统一标跳过
            if winner is not None:
                continue
            verdicts[ch.kind] = verdict
            emit(_settle_frame(ch, verdict, via_label))
        # 按阶梯顺序走账：首个未交代处停下等它；已交代的位子里出现可走即定案
        for ch in order:
            verdict = verdicts.get(ch.kind)
            if verdict is None:
                break
            if verdict[0]:
                winner = ch
                break

    # 清场：在途陪跑取消并补标跳过，抢跑成功的改标跳过；败行保留真实✗不掩遮
    stragglers = {t for t in tasks if not t.done()}
    for task in stragglers:
        task.cancel()
    if winner is not None:
        for ch in order:
            if ch is winner:
                continue
            verdict = verdicts.get(ch.kind)
            if verdict is None or verdict[0]:
                emit(
                    {
                        "id": ch.kind,
                        "status": RowStatus.SKIP,
                        "detail": CheckMessage.SKIP,
                    }
                )
    if stragglers:
        await asyncio.wait(stragglers)

    if winner is not None:
        _, resolved, errors, _ = verdicts[winner.kind]
        outcome.passed = True
        outcome.resolved = resolved
        outcome.errors = errors
    else:
        # 全挂：取最高优先失败通道的字段错，最贴近用户自己填的配置
        for ch in order:
            verdict = verdicts.get(ch.kind)
            if verdict is not None and not verdict[0] and verdict[2]:
                outcome.errors = verdict[2]
                break
    return outcome


def local_row(schema: AppSchema, config: AppConfigData) -> tuple[dict, dict[str, str]]:
    """本地配置校验：返回（local 行终态帧，类型错误字典）

    纯函数零阻塞，结果并入开局整表先行落定，网络在跑时本地已亮。
    """
    errors = validate_types(schema, config)
    frame = {
        "id": RowId.LOCAL,
        "status": RowStatus.OK if not errors else RowStatus.FAIL,
        "detail": (
            CheckMessage.VERIFY_LOCAL_OK
            if not errors
            else CheckMessage.VERIFY_LOCAL_FAIL.format(n=len(errors))
        ),
    }
    return frame, errors
