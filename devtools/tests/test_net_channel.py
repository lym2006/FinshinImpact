"""启动器与构建侧取数通道的单元测试

- 通道清单只有干净直连那一条
- 每条通道按同一节奏发到上限为止，换通道即换一次机会
- 取 JSON、取字节、探长度坏光交出空值，落盘下载坏光交出原因
- 落盘件写坏不留 .part
"""

import sys
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "packaging"))

import net_channel  # noqa: E402

_TIMEOUT = 1.0


class _FakeResponse:
    """假通道回的一条响应，正文与响应头都按用例给定的值报

    - 正文只给一次，第二次读交出空串，流式写盘靠这一条收尾
    """

    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self._body = body
        self.headers = headers

    def read(self, _size: int = -1) -> bytes:
        found, self._body = self._body, b""

        return found

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _FakeOpener:
    """按脚本一次发一条的假通道，记下发过几次

    - 脚本项是异常即模拟那一发坏了
    - 脚本项是整数即模拟状态码不合
    """

    def __init__(self, script: list[Any]) -> None:
        self.script = script
        self.sends = 0

    def open(self, _request: Any, timeout: float) -> _FakeResponse:
        found = self.script[min(self.sends, len(self.script) - 1)]
        self.sends += 1
        if isinstance(found, BaseException):
            raise found
        if isinstance(found, int):
            raise urllib.error.HTTPError("https://x", found, "nope", None, None)

        return _FakeResponse(found[0], found[1])


def _json_body() -> tuple[bytes, dict[str, str]]:
    """一份 JSON 正文的响应内容"""
    return (b'{"body": "first line"}', {})


def _ok(body: bytes = b"hi") -> tuple[bytes, dict[str, str]]:
    """一份正常正文的响应内容"""
    return (body, {})


class TestOpeners(unittest.TestCase):
    """通道清单的条数"""

    def test_only_clean_direct_channel(self) -> None:
        """通道清单只排干净直连那一条"""
        self.assertEqual(len(net_channel.openers()), 1)


class TestRetries(unittest.TestCase):
    """重发节奏与换通道"""

    def setUp(self) -> None:
        self.no_wait = patch.object(net_channel, "_RETRY_DELAY", 0.0)
        self.no_wait.start()
        self.addCleanup(self.no_wait.stop)

    def test_bad_channel_is_emptied_before_next(self) -> None:
        """一条通道发到次数上限才换下一条"""
        broken: list[Any] = [ValueError("坏")] * net_channel._MAX_ATTEMPTS
        first = _FakeOpener(broken)
        second = _FakeOpener([_json_body()])

        found = net_channel.fetch_json("https://x", [first, second], {}, _TIMEOUT)

        self.assertEqual(found, {"body": "first line"})
        self.assertEqual(first.sends, net_channel._MAX_ATTEMPTS)
        self.assertEqual(second.sends, 1)

    def test_all_channels_used_up_yields_none(self) -> None:
        """通道与次数全用完即交出空值，不抛异常"""
        broken: list[Any] = [OSError("断")] * net_channel._MAX_ATTEMPTS
        first = _FakeOpener(broken)
        second = _FakeOpener(broken)

        self.assertIsNone(
            net_channel.fetch_bytes("https://x", [first, second], {}, _TIMEOUT)
        )
        self.assertEqual(second.sends, net_channel._MAX_ATTEMPTS)

    def test_status_code_counts_as_failure(self) -> None:
        """状态码不合即这一发没成，换下一发"""
        opener = _FakeOpener([404, _ok(b"second")])

        self.assertEqual(
            net_channel.fetch_bytes("https://x", [opener], {}, _TIMEOUT), b"second"
        )

    def test_empty_body_counts_as_failure(self) -> None:
        """空正文即这一发没成"""
        opener = _FakeOpener([_ok(b""), _ok(b"body")])

        self.assertEqual(
            net_channel.fetch_bytes("https://x", [opener], {}, _TIMEOUT), b"body"
        )


class TestProbeSize(unittest.TestCase):
    """HEAD 探长度交出的两样"""

    def test_size_found_has_no_note(self) -> None:
        """探到长度即说明交出空串"""
        opener = _FakeOpener([(_ok(), {"Content-Length": "2048"})])

        self.assertEqual(
            net_channel.probe_size("https://x", [opener], "Content-Length", _TIMEOUT),
            (2048, ""),
        )

    def test_failure_names_the_error(self) -> None:
        """没探到即点名末次失败的类型"""
        opener = _FakeOpener([OSError("连不上")] * net_channel._MAX_ATTEMPTS)

        size, note = net_channel.probe_size(
            "https://x", [opener], "Content-Length", _TIMEOUT
        )

        self.assertEqual((size, note), (0, "OSError: 连不上"))

    def test_missing_header_reads_as_zero(self) -> None:
        """响应头没给长度即读成零，不算失败"""
        opener = _FakeOpener([(_ok(), {})])

        self.assertEqual(
            net_channel.probe_size("https://x", [opener], "Content-Length", _TIMEOUT),
            (0, ""),
        )


class TestDownloadTo(unittest.TestCase):
    """落盘下载"""

    def setUp(self) -> None:
        self.no_wait = patch.object(net_channel, "_RETRY_DELAY", 0.0)
        self.no_wait.start()
        self.addCleanup(self.no_wait.stop)
        self.holder = TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.target = Path(self.holder.name) / "pkg.zip"

    def test_written_file_has_no_part_left(self) -> None:
        """取到即只留正式名，半截件不剩"""
        opener = _FakeOpener([_ok(b"payload")])

        net_channel.download_to("https://x", [opener], self.target, _TIMEOUT)

        self.assertEqual(self.target.read_bytes(), b"payload")
        self.assertEqual(list(self.target.parent.glob("*.part")), [])

    def test_all_channels_used_up_raises_with_reason(self) -> None:
        """全用完仍坏即带原因上抛，正式名不落"""
        broken: list[Any] = [OSError("断了")] * net_channel._MAX_ATTEMPTS
        opener = _FakeOpener(broken)

        with self.assertRaises(RuntimeError) as ctx:
            net_channel.download_to("https://x", [opener], self.target, _TIMEOUT)
        self.assertIn("OSError: 断了", str(ctx.exception))
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
