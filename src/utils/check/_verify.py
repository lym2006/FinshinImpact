# src/utils/check/_verify.py
"""连通校验公共核心

- 全部通道并发探测，按优先级顺序取首个成功的通道
- 首轮全挂则预热后重跑一轮再定性
- 校验窗与诊断窗共用本核心与同款进度帧
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from core.domain import ConfigKey, FieldKey
from skin.messages import CheckMessage

from ..config import AppConfigData, AppSchema, validate_types
from ..logger import get_logger
from ..network import Channel, RowId, RowStatus

_logger = get_logger("Check")

# 首轮全挂后的预热重检
_RETRY_WARMUP = 1.5  # 秒，等代理软件把 TUN 内核与监听拉起来再原样重跑

# 探针展示句留空时由核心按"称谓：可达/不可用"拼装，缺席句等特例显式覆盖
_ProbeCallback = Callable[[Channel], Awaitable[tuple[str | None, dict[str, str], str]]]
_EmitCallback = Callable[[dict], None]
_StopCheckCallback = Callable[[], bool]
_ViaLabel = Callable[[Channel], str]
_ReplayCallback = Callable[[], object]  # 重发整表清场的回调，返回值不吃

# 探针裁决：(通道可走, 生效地址, 字段错误, 表格展示句)
_Verdict = tuple[bool, str | None, dict[str, str], str]


@dataclass
class ChannelOutcome:
    """一轮通道并发探测的结果"""

    resolved: str | None = None
    errors: dict[str, str] = field(default_factory=dict)
    passed: bool = False  # 任一通道可走即真（含"通道通仅 token 错"）


def _never_stop() -> bool:
    """默认停止回调"""
    # 永不中断
    return False


async def _probe_safe(ch: Channel, probe: _ProbeCallback) -> _Verdict:
    """执行单通道探针

    - 探针异常记为该通道失败，不上抛
    """
    try:
        resolved, errors, detail = await probe(ch)
    except asyncio.CancelledError:
        raise
    except Exception:
        _logger.debug("连通探针异常")
        return (
            False,
            None,
            {FieldKey.PROXY: CheckMessage.SELF_CRASH},
            "",
        )
    ok = resolved is not None or bool(errors and FieldKey.PROXY not in errors)
    return ok, resolved, errors, detail


def _settle_frame(ch: Channel, verdict: _Verdict, via_label: _ViaLabel) -> dict:
    """组装单行终态帧

    - 展示句留空时按通道名统一生成成败文案
    """
    ok, _, _, detail = verdict
    text = detail or CheckMessage.REACH.format(
        via=via_label(ch),
        state=CheckMessage.REACH_OK if ok else CheckMessage.REACH_FAIL,
    )
    return {
        "id": ch.kind,
        "status": RowStatus.OK if ok else RowStatus.FAIL,
        "detail": text,
    }


async def _run_channels(
    channels: Sequence[Channel],
    probe: _ProbeCallback,
    emit: _EmitCallback,
    via_label: _ViaLabel,
    stop_check: _StopCheckCallback | None = None,
) -> ChannelOutcome:
    """并发探测全部通道

    - 所有通道先标 checking，按优先级取首个成功的通道
    - 高优先级未出结果时，低优先级成功不提前采用
    - 选定后取消其余探测，未采用的通道标跳过
    - stop_check 为真时中止整轮，不发终态帧
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
            verdicts[ch.kind] = verdict

            # 败行即时落红：✗ 是终局，不会被清场翻案
            if not verdict[0]:
                emit(_settle_frame(ch, verdict, via_label))

        # 按阶梯顺序走账：首个未交代处停下等它，已交代的位子里出现可走即定案
        for ch in order:
            verdict = verdicts.get(ch.kind)
            if verdict is None:
                break
            if verdict[0]:
                winner = ch

                # 定案的绿勾此刻才上屏：按住期间它从没亮过，不存在翻案
                emit(_settle_frame(ch, verdict, via_label))
                break

    # 清场：在途陪跑取消，按住未发的成功者与未完成者统一补绿色带过
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


async def run_probe_round(
    channels: Sequence[Channel],
    probe: _ProbeCallback,
    emit: _EmitCallback,
    via_label: _ViaLabel,
    replay: _ReplayCallback,
    stop_check: _StopCheckCallback | None = None,
) -> ChannelOutcome:
    """全挂则预热重跑的一轮通道探测

    - 校验轮与诊断轮同走本流程，两轮都全挂才定性
    - 重跑前调 replay 重发整表清场，已定案的红行不吃单行帧
    - 通道表为空或轮次被中止时不重跑
    """
    outcome = await _run_channels(channels, probe, emit, via_label, stop_check)
    stopped = stop_check is not None and stop_check()
    if outcome.passed or not channels or stopped:
        return outcome

    # 首轮全挂多为冷启动握手慢：歇一拍等内核拉起来，再趁热重检一轮定性
    await asyncio.sleep(_RETRY_WARMUP)
    replay()
    return await _run_channels(channels, probe, emit, via_label, stop_check)


def local_row(
    schema: AppSchema, config: AppConfigData
) -> tuple[dict, dict[ConfigKey, str]]:
    """本地配置校验

    - 返回 local 行终态帧与类型错误字典
    - 结果并入整表首帧先行显示，不等网络探测
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
