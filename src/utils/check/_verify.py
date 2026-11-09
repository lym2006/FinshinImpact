# src/utils/check/_verify.py
"""连通校验公共核心

- 全部通道并发探测，按优先级顺序取首个成功的通道
- 首轮全挂则预热后重跑一轮再定性
- 每轮逐档记耗时、上限与跳过，只落调试日志
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from finshin_sdk.domain import ConfigKey, FieldKey
from skin.messages import CheckMessage

from ..config import AppConfigData, AppSchema, validate_types
from ..logger import get_logger
from ..network import NETWORK_ROWS, Channel, RowId, RowStatus, probe_budget

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


def _probe_tag(round_no: int, ch: Channel, started: float, budget: float) -> str:
    """通道耗时行"""
    cost = asyncio.get_running_loop().time() - started
    return f"探测第{round_no}轮 {ch.kind} 跑了 {cost:.1f}s 上限 {budget:.1f}s"


def _log_skipped_rows(round_no: int, channels: Sequence[Channel]) -> None:
    """未起表的档位逐行标跳过"""
    kinds = {ch.kind for ch in channels}
    for rid in NETWORK_ROWS:
        if rid not in kinds:
            _logger.debug(f"探测第{round_no}轮 {rid} 未起表 跳过")


async def _probe_safe(
    ch: Channel, probe: _ProbeCallback, round_no: int, budget: float
) -> _Verdict:
    """执行单通道探针

    - 探针异常记为该通道失败，不上抛
    - 耗时与终局逐行落调试日志
    """
    started = asyncio.get_running_loop().time()
    try:
        resolved, errors, detail = await probe(ch)
    except asyncio.CancelledError:
        _logger.debug(f"{_probe_tag(round_no, ch, started, budget)} 未采用 跳过")
        raise
    except Exception:
        _logger.debug(
            f"{_probe_tag(round_no, ch, started, budget)} 探针异常", exc_info=True
        )
        return (
            False,
            None,
            {FieldKey.PROXY: CheckMessage.SELF_CRASH},
            "",
        )
    ok = resolved is not None or bool(errors and FieldKey.PROXY not in errors)
    state = "过" if ok else f"不通 {detail or errors.get(FieldKey.PROXY, '')}"
    _logger.debug(f"{_probe_tag(round_no, ch, started, budget)} {state}")
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
    round_no: int,
    probe: _ProbeCallback,
    emit: _EmitCallback,
    via_label: _ViaLabel,
    stop_check: _StopCheckCallback | None = None,
) -> ChannelOutcome:
    """并发探测全部通道

    - 全部通道先标为检测中
    - 高优先级未出结果时，低优先级的成功不提前采用
    - 选定后取消其余探测，未采用的标为跳过
    - 收到中止请求时整轮停下，不发终态帧
    """
    stop = stop_check or _never_stop
    outcome = ChannelOutcome()
    order = list(channels)
    _log_skipped_rows(round_no, order)
    if not order:
        return outcome
    for ch in order:
        emit({"id": ch.kind, "status": RowStatus.CHECKING, "detail": ""})

    tasks = {
        asyncio.ensure_future(
            _probe_safe(ch, probe, round_no, probe_budget(ch.url))
        ): ch
        for ch in order
    }
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

    - 重跑前重发整表清场，已定案的失败行不吃单行帧
    - 通道表为空或轮次被中止时不重跑
    """
    outcome = await _run_channels(channels, 1, probe, emit, via_label, stop_check)
    stopped = stop_check is not None and stop_check()
    if outcome.passed or not channels or stopped:
        return outcome

    # 首轮全挂多为冷启动握手慢：歇一拍等内核拉起来，再趁热重检一轮定性
    _logger.debug(f"探测首轮全不通 预热 {_RETRY_WARMUP}s 后重跑第二轮")
    await asyncio.sleep(_RETRY_WARMUP)
    replay()
    return await _run_channels(channels, 2, probe, emit, via_label, stop_check)


def local_row(
    schema: AppSchema, config: AppConfigData
) -> tuple[dict, dict[ConfigKey, str]]:
    """本地配置校验

    - 交回本地行的终态帧与类型错误字典
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
