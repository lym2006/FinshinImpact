# src/utils/network/_link.py
"""链路状态上报

- 维护断连周期计时与重试计数
- 提供快照供界面轮询读取
"""

import time
from dataclasses import dataclass

from messages import EngineMessage

from ..logger import get_logger

# 断连上报节流
_FAIL_LOG_EVERY = 3  # 次，重连进度补报间隔

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

    - 冒号后只留尾段，分秒两档够用，满一小时改报时
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
    elapsed: int  # 本轮已断秒数
    retries: int  # 本轮累计失败次数

    @property
    def timer_text(self) -> str:
        """弹窗计时串"""
        return _timer_of(self.elapsed)

    @property
    def span_text(self) -> str:
        """面板时长短串"""
        return _span_of(self.elapsed)


class _LinkReport:
    """断连周期状态机

    - 断连首行、重连进度与恢复收尾各一句，链路正常时零输出
    """

    def __init__(self) -> None:
        self._fails = 0
        self._since = 0.0

    def failed(self, api: str, error: BaseException) -> None:
        """记录一次网络层失败"""
        if self._fails == 0:
            self._since = time.monotonic()
            _logger.error(EngineMessage.DOWN)
        self._fails += 1
        _logger.debug(f"链路失败：{api} {type(error).__name__}: {error}")
        if self._fails % _FAIL_LOG_EVERY == 0:
            _logger.debug(
                EngineMessage.RETRYING.format(span=self._span(), n=self._fails)
            )

    def recovered(self) -> None:
        """记录一次成功，收尾断连周期"""
        if self._fails:
            _logger.info(
                EngineMessage.RECOVERED.format(span=self._span(), n=self._fails)
            )
        self._fails = 0

    def reset(self) -> None:
        """作废进行中的断连周期"""
        self._fails = 0

    def snapshot(self) -> LinkStatus:
        """当前断连周期快照

        - 链路正常或周期已作废时归零，避免读到陈旧起始点
        """
        if self._fails == 0:
            return LinkStatus(down=False, elapsed=0, retries=0)
        return LinkStatus(
            down=True,
            elapsed=int(time.monotonic() - self._since),
            retries=self._fails,
        )

    def _span(self) -> str:
        """本轮已断时长面板短串"""
        return _span_of(int(time.monotonic() - self._since))


link_report = _LinkReport()  # 全局链路上报单例
