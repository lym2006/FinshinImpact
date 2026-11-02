# src/utils/network/_link.py
"""链路状态上报

- 维护断连周期计时与重试计数
- 快照供界面轮询读取
"""

import time
from dataclasses import dataclass

from skin.messages import EngineMessage

from ..logger import get_logger

# 断连判定与上报节流
_DOWN_THRESHOLD = 2  # 连续失败次数，达到才翻断连，滤掉单条请求抖动
_FAIL_LOG_EVERY = 3  # 次，重连进度补报间隔
_RETRY_OFFSET = 1  # 首次失败属正常请求本身，面板的重连计数从其后起算

# 时长换算档位
_SECONDS_PER_MINUTE = 60  # 秒，一分钟
_SECONDS_PER_HOUR = 3600  # 秒，一小时

_logger = get_logger("Net")


def _timer_of(seconds: int) -> str:
    """时长转计时串

    - 不足一小时只报分秒，满一小时补时位
    """
    hours, rest = divmod(seconds, _SECONDS_PER_HOUR)
    minutes, secs = divmod(rest, _SECONDS_PER_MINUTE)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _span_of(seconds: int) -> str:
    """时长转面板短串

    - 满一小时报时分，其余报分秒
    """
    hours, rest = divmod(seconds, _SECONDS_PER_HOUR)
    minutes, secs = divmod(rest, _SECONDS_PER_MINUTE)
    if hours:
        return f"{hours} 时 {minutes:02d} 分"
    if minutes:
        return f"{minutes} 分 {secs:02d} 秒"
    return f"{seconds} 秒"


@dataclass(frozen=True)
class LinkStatus:
    """链路快照"""

    down: bool  # 是否处于断连周期
    elapsed: int  # 本次断连已持续秒数
    retries: int  # 本次断连累计的重连尝试次数

    @property
    def timer_text(self) -> str:
        """弹窗计时串"""
        return _timer_of(self.elapsed)

    @property
    def span_text(self) -> str:
        """面板时长短串"""
        return _span_of(self.elapsed)


class _LinkReport:
    """断连周期状态机"""

    def __init__(self) -> None:
        self._fails = 0
        self._since = 0.0

    def failed(self, api: str, error: BaseException) -> None:
        """记录一次网络层失败"""
        self._fails += 1
        _logger.debug(f"链路失败：{api} {type(error).__name__}: {error}")
        if self._fails == _DOWN_THRESHOLD:
            self._since = time.monotonic()
            _logger.error(EngineMessage.DOWN)
        elif self._fails > _DOWN_THRESHOLD and self._fails % _FAIL_LOG_EVERY == 0:
            _logger.debug(
                EngineMessage.RETRYING.format(span=self._span(), n=self._retries())
            )

    def recovered(self) -> None:
        """记录一次成功，收尾断连周期"""
        if self._fails >= _DOWN_THRESHOLD:
            _logger.info(
                EngineMessage.RECOVERED.format(span=self._span(), n=self._retries())
            )
        self._fails = 0

    def reset(self) -> None:
        """作废进行中的断连周期"""
        self._fails = 0

    def snapshot(self) -> LinkStatus:
        """当前断连周期快照"""
        # 未起表或周期已作废时归零，免得界面读到陈旧起始点
        if self._fails < _DOWN_THRESHOLD:
            return LinkStatus(down=False, elapsed=0, retries=0)
        return LinkStatus(
            down=True,
            elapsed=int(time.monotonic() - self._since),
            retries=self._retries(),
        )

    def _retries(self) -> int:
        """面板口径的重连尝试次数"""
        return self._fails - _RETRY_OFFSET

    def _span(self) -> str:
        """本次断连时长面板短串"""
        return _span_of(int(time.monotonic() - self._since))


link_report = _LinkReport()  # 链路上报的进程级实例
