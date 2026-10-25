# devtools/tests/test_style_checker_meta.py
"""扫描器自检的单元测试

- 十二个分节各备一份故意违规的样本，防判据空转与包路径搬家后静默失效
- 违规条目的分节名必须在 SECTIONS 内，防字面量改写错位
- 回调形参四条判据各命中一次，业务协程与已合规写法不误报
- 豁免清单只罩待核，条目须可解析且每条都在命中，失效即红
- devtools 树可直连私有模块：不报越界，其引用不把 src 公共名算成对外
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _style_checks import (  # noqa: E402
    SECTIONS,
    Finding,
    ImportGraph,
    Waiver,
    apply_waivers,
    load_files,
    load_waivers,
    run_checks,
)
from check_coding_style import _full_scan, _run  # noqa: E402

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent


def _skeleton(rel: str) -> str:
    """按规范写好的文件头，样本只留本分节那一处违规"""
    return f'# {rel}\n"""定位\n\n- 说明\n"""\n\n'


_CLASS_DOC = '    """定位\n\n    - 说明\n    """\n\n'
_METHOD_DOC = '        """定位\n\n        - 说明\n        """\n'
_FUNC_DOC = '    """定位\n\n    - 说明\n    """\n'

# 样本里的模块级符号一律带 `_` 前缀，避开命名分节的连带条目
_USE = "_USE = None\n"


def _message_enum(rel: str, cls: str, member: str, text: str) -> tuple[str, str]:
    """造一份文案域样本，成员与使用位注释齐全"""
    return (
        rel,
        _skeleton(rel)
        + "from enum import StrEnum\n\n\n"
        + f"class {cls}(StrEnum):\n{_CLASS_DOC}\n"
        + f'    # 使用位置\n    {member} = "{text}"\n',
    )


# 每个分节一组样本，键必须是 SECTIONS 里的分节名
_SAMPLES: dict[str, tuple[tuple[str, str], ...]] = {
    "文件骨架": (
        ("src/ui/_probe_skel.py", '# _other.py\n"""定位\n\n- 说明\n"""\n' + _USE),
    ),
    "拆分粒度": (
        (
            "src/ui/_probe_split.py",
            _skeleton("src/ui/_probe_split.py")
            + "class _Wide:\n"
            + _CLASS_DOC
            + "".join(
                f"    def m{i}(self) -> None:\n{_METHOD_DOC}\n        pass\n"
                for i in range(13)
            ),
        ),
    ),
    "Docstring": (
        (
            "src/ui/_probe_doc.py",
            _skeleton("src/ui/_probe_doc.py")
            + 'def _go() -> None:\n    """标题：解释\n    没有破折号起头\n    """\n',
        ),
    ),
    "注释": (
        (
            "src/ui/_probe_cmt.py",
            _skeleton("src/ui/_probe_cmt.py")
            + "_VALUE = 1\n\n# 一句话说完；再来一句\n_OTHER = 2\n",
        ),
    ),
    "命名与门面导出": (
        (
            "src/ui/_probe_a.py",
            _skeleton("src/ui/_probe_a.py") + "class _Hidden:\n" + _CLASS_DOC,
        ),
        (
            "src/ui/_probe_b.py",
            _skeleton("src/ui/_probe_b.py")
            + "from ._probe_a import _Hidden\n\n_USE = _Hidden\n",
        ),
    ),
    "魔法数字与字符串": (
        (
            "src/ui/_probe_magic.py",
            _skeleton("src/ui/_probe_magic.py")
            + f"def _go() -> int:\n{_FUNC_DOC}    return 42\n",
        ),
    ),
    "枚举": (
        (
            "src/core/_probe_enum.py",
            _skeleton("src/core/_probe_enum.py")
            + "from enum import IntEnum\n\n\nclass _Level(IntEnum):\n"
            + _CLASS_DOC
            + "    LOW = 10\n    HIGH = 10\n",
        ),
    ),
    "日志与文案": (
        (
            "src/ui/_probe_text.py",
            _skeleton("src/ui/_probe_text.py")
            + 'from utils import get_logger\n\n_logger = get_logger("Probe")\n\n\n'
            + f"def _go() -> None:\n{_FUNC_DOC}"
            + '    _logger.warning("注意一下")\n',
        ),
    ),
    "文案类": (
        ("src/skin/__init__.py", _skeleton("src/skin/__init__.py")),
        (
            "src/skin/messages/__init__.py",
            _skeleton("src/skin/messages/__init__.py")
            + "from ._extra import ExtraMessage\nfrom ._other import OtherMessage\n\n"
            + '__all__ = [\n    # 域类\n    "ExtraMessage",\n    "OtherMessage",\n]\n',
        ),
        _message_enum("src/skin/messages/_other.py", "OtherMessage", "START", "启动"),
        _message_enum("src/skin/messages/_extra.py", "ExtraMessage", "GO", "启动"),
    ),
    "回调形参": (
        (
            "src/plugins/_probe_cb.py",
            _skeleton("src/plugins/_probe_cb.py")
            + "from aiogram.types import Message\n\n\n"
            + f"async def _go(message: Message) -> None:\n{_FUNC_DOC}",
        ),
    ),
    "类型注解": (
        (
            "src/ui/_probe_type.py",
            _skeleton("src/ui/_probe_type.py")
            + "_VALUE = 1  # type: ignore\n\n\n"
            + f"def _go(x):\n{_FUNC_DOC}    return x\n",
        ),
    ),
    "导入": (
        (
            "src/ui/_probe_imp.py",
            _skeleton("src/ui/_probe_imp.py")
            + "from ui._probe_other import Thing\n\n_USE = Thing\n",
        ),
    ),
}

# 样本共用的包门面，只为把点分模块名解析出来
_PKG_INITS: tuple[str, ...] = (
    "src/ui/__init__.py",
    "src/core/__init__.py",
    "src/plugins/__init__.py",
    "src/skin/__init__.py",
    "src/skin/messages/__init__.py",
)


def _scan(
    samples: list[tuple[str, str]], targets: tuple[str, ...] = ("src",)
) -> dict[str, list[str]]:
    """在临时树里落样本并跑全量检查，按分节归名"""
    tree: dict[str, str] = {rel: _skeleton(rel) for rel in _PKG_INITS}
    tree.update(dict(samples))
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for rel, source in tree.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        files = load_files(root, [root / part for part in targets])
        findings = run_checks(files, ImportGraph(files))
    bucket: dict[str, list[str]] = {}
    for item in findings:
        bucket.setdefault(item.section, []).append(item.message)
    return bucket


class TestSectionLive(unittest.TestCase):
    """每个分节都真的能出条目"""

    def test_fixture_keys_match_sections(self) -> None:
        """样本表与分节名单双向对齐，改名即红"""
        self.assertEqual(set(_SAMPLES), set(SECTIONS))

    def test_every_section_fires(self) -> None:
        """逐分节断言样本命中，判据脱节即红"""
        for section in SECTIONS:
            with self.subTest(section=section):
                bucket = _scan(list(_SAMPLES[section]))
                self.assertTrue(
                    bucket.get(section),
                    f"分节「{section}」的样本没有命中，判据可能已脱节",
                )

    def test_section_names_are_known(self) -> None:
        """条目分节名必须在名单内，防字面量改写错位"""
        fired: set[str] = set()
        for samples in _SAMPLES.values():
            fired.update(_scan(list(samples)))
        for section in fired:
            with self.subTest(section=section):
                self.assertIn(section, SECTIONS)


class TestCallbackParams(unittest.TestCase):
    """回调形参四条判据的命中与对照"""

    def test_event_param_must_be_first_and_named_raw(self) -> None:
        """事件形参不在首位或改名都判硬性"""
        source = (
            _skeleton("src/plugins/_probe_cb.py")
            + "from aiogram.types import Message\n\n\n"
            + "async def _go(ctx: object, message: Message) -> None:\n"
            + '    """定位\n\n    - 说明\n    """\n'
        )
        hits = _scan([("src/plugins/_probe_cb.py", source)]).get("回调形参", [])
        self.assertEqual(len(hits), 2, hits)

    def test_middleware_signature(self) -> None:
        """中间件 __call__ 形参序列不对即判硬性"""
        source = (
            _skeleton("src/plugins/_probe_cb.py")
            + "from aiogram import BaseMiddleware\n\n\n"
            + "class _EchoMiddleware(BaseMiddleware):\n"
            + _CLASS_DOC
            + "    async def __call__(self, event: object, handler: object) -> None:\n"
            + '        """定位\n\n        - 说明\n        """\n'
        )
        hits = _scan([("src/plugins/_probe_cb.py", source)]).get("回调形参", [])
        self.assertTrue(any("handler, event, data" in text for text in hits), hits)

    def test_injected_context_rename(self) -> None:
        """回调里上下文形参改名即注入不到，判硬性"""
        source = (
            _skeleton("src/plugins/_probe_cb.py")
            + "from aiogram.types import Message\n"
            + "from services import HandlerContext\n\n\n"
            + "async def _go(raw: Message, host: HandlerContext) -> None:\n"
            + '    """定位\n\n    - 说明\n    """\n'
        )
        hits = _scan([("src/plugins/_probe_cb.py", source)]).get("回调形参", [])
        self.assertTrue(any("改名 `ctx`" in text for text in hits), hits)

    def test_swappable_optional_pair(self) -> None:
        """必填后紧跟同型可选参数提示加星号，属待核"""
        source = (
            _skeleton("src/ui/_probe_panel.py")
            + "class _Panel:\n"
            + _CLASS_DOC
            + "    def open(self, code: str, mode: str = '') -> None:\n"
            + '        """定位\n\n        - 说明\n        """\n'
        )
        hits = _scan([("src/ui/_probe_panel.py", source)]).get("回调形参", [])
        self.assertTrue(any("加 `*` 隔开" in text for text in hits), hits)

    def test_business_coroutine_not_flagged(self) -> None:
        """业务协程收上下文对象当数据不算注入位，不报"""
        source = (
            _skeleton("src/plugins/_probe_cb.py")
            + "from services import HandlerContext\n\n\n"
            + "async def _push(task: HandlerContext) -> None:\n"
            + '    """定位\n\n    - 说明\n    """\n'
        )
        self.assertEqual(
            _scan([("src/plugins/_probe_cb.py", source)]).get("回调形参", []), []
        )


class TestWaiverFile(unittest.TestCase):
    """豁免清单自身的完整性"""

    def test_hard_finding_not_waivable(self) -> None:
        """清单只罩待核，硬性违规一律照常报出"""
        waiver = Waiver(
            section="注释", path="src/ui/_probe.py", reason="探针", match="分号"
        )
        message = "注释含分号：`一句话说完；再来一句`"
        self.assertFalse(
            waiver.covers(Finding("注释", "src/ui/_probe.py", 9, message, True))
        )
        self.assertTrue(
            waiver.covers(Finding("注释", "src/ui/_probe.py", 9, message, False))
        )

    def test_waiver_needs_no_line_number(self) -> None:
        """行号漂移不影响罩住，清单不许靠行号续命"""
        waiver = Waiver(section="注释", path="src/ui/_probe.py", reason="探针")
        message = "注释含分号：`一句话说完；再来一句`"
        self.assertTrue(
            waiver.covers(Finding("注释", "src/ui/_probe.py", 9, message, False))
        )
        self.assertTrue(
            waiver.covers(Finding("注释", "src/ui/_probe.py", 480, message, False))
        )

    def test_entries_carry_reason(self) -> None:
        """每条豁免都要写理由，缺理由即读不出来"""
        waivers = load_waivers(_HERE.parent / "style_waivers.toml")
        self.assertTrue(waivers)
        for waiver in waivers:
            with self.subTest(path=waiver.path):
                self.assertTrue(waiver.reason.strip(), "豁免理由为空")

    def test_no_dead_waiver(self) -> None:
        """全仓扫描后清单里不许留失效条目"""
        files = load_files(_ROOT, [_ROOT / "src"])
        findings = run_checks(files, ImportGraph(files))
        _, dead = apply_waivers(
            findings, load_waivers(_HERE.parent / "style_waivers.toml")
        )
        self.assertEqual(
            [(w.section, w.path) for w in dead],
            [],
            "有豁免条目已不再命中，代码改完要删清单",
        )

    def test_hard_only_keeps_live_waivers(self) -> None:
        """只输出硬性时不许把在用的豁免判成失效"""
        ordered, _ = _run([_ROOT / "src"], list(SECTIONS), True)
        self.assertEqual(
            [f.message for f in ordered if "失效豁免" in f.message],
            [],
            "硬性过滤排在豁免匹配之前，清单条目会全被判死",
        )

    def test_full_scan_needs_root_coverage(self) -> None:
        """覆盖面判据，漏改会让失效检测静默停摆"""
        src, packaging, devtools, ui = (
            _ROOT / "src",
            _ROOT / "packaging",
            _ROOT / "devtools",
            _ROOT / "src" / "ui",
        )
        sections = list(SECTIONS)
        for targets, expected in (
            ([_ROOT], True),
            ([src], True),
            ([src, packaging, devtools], True),
            ([packaging, devtools], False),
            ([ui], False),
        ):
            with self.subTest(targets=[str(item.name) for item in targets]):
                self.assertEqual(_full_scan(sections, targets), expected)
        with self.subTest(msg="只扫单个分节不算扫全"):
            self.assertFalse(_full_scan([sections[0]], [_ROOT]))


class TestDevtoolsWhiteBox(unittest.TestCase):
    """devtools 树可直连私有模块，但引用不给公共名转正"""

    # 工具跨包取 src 的私有模块，模块内一个只被工具用的公共名
    _SAMPLE = [
        (
            "src/ui/_probe_white.py",
            _skeleton("src/ui/_probe_white.py") + "class Public:\n" + _CLASS_DOC,
        ),
        (
            "devtools/_probe_tool.py",
            _skeleton("devtools/_probe_tool.py")
            + "from ui._probe_white import Public\n\n_RUN = Public\n",
        ),
    ]
    _TARGETS = ("src", "devtools")

    def test_private_import_from_tool_passes(self) -> None:
        """工具直连私有模块不报跨包越界"""
        messages = _scan(self._SAMPLE, self._TARGETS).get("命名与门面导出", [])
        self.assertFalse([m for m in messages if "跨包访问私有模块" in m], messages)

    def test_tool_use_does_not_promote(self) -> None:
        """只被工具引用的公共名照样提示加下划线"""
        messages = _scan(self._SAMPLE, self._TARGETS).get("命名与门面导出", [])
        self.assertTrue([m for m in messages if "Public" in m], messages)


if __name__ == "__main__":
    unittest.main()
