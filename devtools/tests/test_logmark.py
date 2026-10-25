# devtools/tests/test_logmark.py
"""日志语义标记单元测试

- 级别仅 INFO/ERROR/DEBUG，标记由内容词表决定
- 结果标记优先：🚫 取消 / ⏸️ 中断 / ⚠️ 软警告 / ❌ 错误 / ✅ 成功 / 🛑 停止
- 领域图标按顺序命中，⚙️ 兜底
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from skin.messages import EngineMessage  # noqa: E402
from utils.logger._formatter import _resolve_mark  # noqa: E402

ALL_MARKS = {
    "✅",
    "❌",
    "⚠",
    "🚫",
    "⏸",
    "🛑",
    "📥",
    "💬",
    "🖼",
    "🌐",
    "🖥",
    "📂",
    "💡",
    "🔍",
    "🧹",
    "⏳",
    "⏱",
    "🤖",
    "🔌",
    "💾",
    "⚙",
    "📃",
    "ℹ",
}


class TestResolveMark(unittest.TestCase):
    """语义标记解析"""

    def _mark(self, level: int, msg: str) -> str:
        """取一行日志的标记字符

        - 去掉变体选择符
        """
        return _resolve_mark(level, msg).replace("\ufe0f", "")

    def test_exactly_one_mark(self) -> None:
        """任何输出都是单个标记"""
        for level, msg in [
            (20, "正在启动引擎..."),
            (40, "[Bot Token] Token 无效"),
            (20, "保存 1 项配置: proxy"),
            (20, "检测到配置有误，弹出配置向导..."),
        ]:
            mark = self._mark(level, msg)
            self.assertEqual(len(mark), 1, f"标记应单字符: {mark!r}")
            self.assertIn(mark, ALL_MARKS, f"非法标记: {mark!r}")

    def test_result_priority(self) -> None:
        """结果标记压过领域图标"""
        self.assertEqual(self._mark(20, "引擎启动成功"), "✅")
        self.assertEqual(self._mark(40, "配置验证失败"), "❌")
        self.assertEqual(self._mark(20, "正在执行全局清理..."), "🧹")

    def test_cancel_pause_stop(self) -> None:
        """取消/中断/停止各有其形"""
        self.assertEqual(self._mark(20, "用户取消关闭操作"), "🚫")
        self.assertEqual(self._mark(40, "思考中断"), "⏸")
        self.assertEqual(self._mark(20, "正在停止引擎..."), "🛑")

    def test_warn_words_beat_error_level(self) -> None:
        """软警告词优先于 error 默认红叉"""
        self.assertEqual(self._mark(40, "[Bot Token] 暂未检测：代理修复后复查"), "⚠")
        self.assertEqual(
            self._mark(20, EngineMessage.RETRYING.format(span="9 秒", n=3)), "⚠"
        )

    def test_link_lines_marks(self) -> None:
        """断连三行各有其形，恢复行不被重试词抢走"""
        self.assertEqual(self._mark(40, EngineMessage.DOWN), "❌")
        self.assertEqual(
            self._mark(20, EngineMessage.RECOVERED.format(span="3 分 09 秒", n=12)),
            "✅",
        )

    def test_error_level_default_cross(self) -> None:
        """错误级未命中词汇默认红叉"""
        self.assertEqual(self._mark(40, "协程执行失败: loop 未运行 [xx]"), "❌")
        self.assertEqual(self._mark(40, "协程执行失败: 超时 5s [xx]"), "❌")
        self.assertEqual(self._mark(40, "线程停止失败: xx"), "❌")

    def test_head_only_matching(self) -> None:
        """只看冒号前

        - 后文配置项名不误伤
        - "配置"域先于"保存"命中（校验词曾被 💾 抢走）
        """

        self.assertEqual(self._mark(20, "保存 2 项配置: 代理、超时（秒）"), "⚙")
        self.assertEqual(self._mark(20, "已写入磁盘: 超时（秒）"), "💾")

    def test_domain_icons(self) -> None:
        """过程行按领域分配图标"""
        cases = {
            "正在创建路径...": "📂",
            "正在检查版本...": "🔍",
            "用户 672 发起对话": "💬",
            "新任务入队，当前长度: 2": "📥",
            "正在启动引擎...": "🤖",
            "开始加载 3 个插件...": "🔌",
            "正在初始化全局 Playwright 浏览器...": "🌐",
        }
        for msg, expect in cases.items():
            self.assertEqual(self._mark(20, msg), expect, msg)

    def test_detect_light_bulb(self) -> None:
        """检测到归提示灯"""
        self.assertEqual(self._mark(20, "检测到配置有误，弹出配置向导..."), "💡")

    def test_cost_mark(self) -> None:
        """耗时行统一秒表符号，含配置词也不被抢"""
        self.assertEqual(self._mark(20, "主程序就绪耗时 5.6s"), "⏱")
        self.assertEqual(self._mark(20, "连通校验耗时 3.2s"), "⏱")
        self.assertEqual(self._mark(20, "通道 直连 探测耗时 0.9s"), "⏱")

    def test_default_gear(self) -> None:
        """都没命中齿轮兜底"""
        self.assertEqual(self._mark(20, "hello world"), "ℹ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
