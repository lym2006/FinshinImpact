"""扫描器自检的单元测试

- 十四个分节各备一份故意违规的样本，防判据空转与包路径搬家后静默失效
- 违规条目的分节名必须在 SECTIONS 内，防字面量改写错位
- 每个分节名在 coding-style 都有同名开头的小节标题，防文档改节名后命令行与豁免指空
- 回调形参四条判据各命中一次，业务协程与已合规写法不误报
- 日志消息串留占位往后传参判硬性，就地拼好与百分号当单位不误报
- CHANGELOG 载体三类判据各命中一次，合规样张零条目
- 文档写法两条判据各命中一次，代码区里的分号与链接字面不报
- 模块级别名按消费者定私有性，类型构造与被他模块取用的别名不判
- 豁免清单只罩待核，条目须可解析，本轮装载到的路径没命中才判失效转硬性
- devtools 树可直连私有模块：不报越界，其引用不把 src 公共名算成对外
- 扫描目标路径写错即报错退出
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_coding_style  # noqa: E402
import gates  # noqa: E402
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
from check_coding_style import _judged_dead, _run  # noqa: E402

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent


def _gate_targets() -> list[Path]:
    """按闸门那份目标算覆盖面，本体三棵树加盘上在场的子仓源码目录"""
    return [_ROOT / rel for rel in gates._source_targets(_ROOT)]


def _skeleton(rel: str) -> str:
    """按规范写好的文件头，样本只留本分节那一处违规"""
    return f'# {rel}\n"""定位\n\n- 说明\n"""\n\n'


_CLASS_DOC = '    """定位\n\n    - 说明\n    """\n\n'
_METHOD_DOC = '        """定位\n\n        - 说明\n        """\n'
_FUNC_DOC = '    """定位\n\n    - 说明\n    """\n'

# 样本里的模块级符号一律带 `_` 前缀，避开命名分节的连带条目
_USE = "_USE = None\n"

# 临时树按主仓形状带一份改名声明，样本里的点分模块名才与现码同形
_PYPROJECT_REL = "pyproject.toml"
_ROOT_DECLARATION = '[tool.setuptools]\npackage-dir = {"" = "src"}\n'


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
        (
            "src/ui/_probe_link.py",
            _skeleton("src/ui/_probe_link.py")
            + '_URL = "https://example.invalid/page"\n',
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
            "src/bundled/_probe_cb.py",
            _skeleton("src/bundled/_probe_cb.py")
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
    "文档写法": (
        ("docs/_probe_semi.md", "- 一句话说完；再来一句\n"),
        ("docs/_probe_fence.md", '```powershell\npy -3 -c "a=1; b=2"\n```\n'),
        (
            "docs/_probe_link.md",
            "[文字](_probe_link_target.md)\n`[文字](no_such_file.md)`\n",
        ),
        ("docs/_probe_link_target.md", "被活链指向的样张。\n"),
        ("docs/_probe_dead.md", "[文字](_no_such_target.md)\n"),
    ),
    "按钮样式": (
        (
            "src/skin/qss/_probe_btn.py",
            'QSS = """\nQPushButton#probe {\n    color: #FFFFFF;\n}\n"""\n',
        ),
    ),
}

# 样本共用的包门面，只为把点分模块名解析出来
_PKG_INITS: tuple[str, ...] = (
    "src/ui/__init__.py",
    "src/core/__init__.py",
    "src/bundled/__init__.py",
    "src/skin/__init__.py",
    "src/skin/messages/__init__.py",
)


def _scan(
    samples: list[tuple[str, str]], targets: tuple[str, ...] = ("src",)
) -> dict[str, list[str]]:
    """在临时树里落样本并跑全量检查，按分节归名"""
    tree: dict[str, str] = {rel: _skeleton(rel) for rel in _PKG_INITS}
    tree[_PYPROJECT_REL] = _ROOT_DECLARATION
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

    def test_link_home_rule_fires(self) -> None:
        """链接归家细则单独也能出条目，判据脱节即红"""
        samples = [
            item for item in _SAMPLES["魔法数字与字符串"] if "_probe_link" in item[0]
        ]
        bucket = _scan(samples)
        messages = [msg for items in bucket.values() for msg in items]
        self.assertTrue(
            [msg for msg in messages if "在线地址裸写在家外" in msg],
            f"链接归家细则没命中：{messages}",
        )

    def test_section_names_have_doc_headings(self) -> None:
        """分节名与规范册小节标题对得上"""
        headings = [
            line.removeprefix("## ").strip()
            for line in (_ROOT / "docs/coding-style.md")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.startswith("## ")
        ]
        for section in SECTIONS:
            self.assertTrue(
                any(title.startswith(section) for title in headings),
                f"分节 {section} 在 coding-style 找不到同名小节标题",
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
            _skeleton("src/bundled/_probe_cb.py")
            + "from aiogram.types import Message\n\n\n"
            + "async def _go(ctx: object, message: Message) -> None:\n"
            + '    """定位\n\n    - 说明\n    """\n'
        )
        hits = _scan([("src/bundled/_probe_cb.py", source)]).get("回调形参", [])
        self.assertEqual(len(hits), 2, hits)

    def test_middleware_signature(self) -> None:
        """中间件 __call__ 形参序列不对即判硬性"""
        source = (
            _skeleton("src/bundled/_probe_cb.py")
            + "from aiogram import BaseMiddleware\n\n\n"
            + "class _EchoMiddleware(BaseMiddleware):\n"
            + _CLASS_DOC
            + "    async def __call__(self, event: object, handler: object) -> None:\n"
            + '        """定位\n\n        - 说明\n        """\n'
        )
        hits = _scan([("src/bundled/_probe_cb.py", source)]).get("回调形参", [])
        self.assertTrue(any("handler, event, data" in text for text in hits), hits)

    def test_injected_context_rename(self) -> None:
        """回调里上下文形参改名即注入不到，判硬性"""
        source = (
            _skeleton("src/bundled/_probe_cb.py")
            + "from aiogram.types import Message\n"
            + "from services import HandlerContext\n\n\n"
            + "async def _go(raw: Message, host: HandlerContext) -> None:\n"
            + '    """定位\n\n    - 说明\n    """\n'
        )
        hits = _scan([("src/bundled/_probe_cb.py", source)]).get("回调形参", [])
        self.assertTrue(any("改名 `ctx`" in text for text in hits), hits)

    def test_platform_raw_needs_object(self) -> None:
        """原始件口子按平台类型标注即锁死该平台，判硬性"""
        source = (
            _skeleton("src/bundled/_probe_cb.py")
            + "from aiogram.types import Message\n"
            + "from services import HandlerContext\n\n\n"
            + "async def _go(platform_raw: Message, ctx: HandlerContext) -> None:\n"
            + '    """定位\n\n    - 说明\n    """\n'
        )
        hits = _scan([("src/bundled/_probe_cb.py", source)]).get("回调形参", [])
        self.assertTrue(any("注解应写 `object`" in text for text in hits), hits)

    def test_platform_raw_ctx_rename(self) -> None:
        """首位收 object 也算回调，上下文改名照样查得到"""
        source = (
            _skeleton("src/bundled/_probe_cb.py")
            + "from services import HandlerContext\n\n\n"
            + "async def _go(platform_raw: object, host: HandlerContext) -> None:\n"
            + '    """定位\n\n    - 说明\n    """\n'
        )
        hits = _scan([("src/bundled/_probe_cb.py", source)]).get("回调形参", [])
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
            _skeleton("src/bundled/_probe_cb.py")
            + "from services import HandlerContext\n\n\n"
            + "async def _push(task: HandlerContext) -> None:\n"
            + '    """定位\n\n    - 说明\n    """\n'
        )
        self.assertEqual(
            _scan([("src/bundled/_probe_cb.py", source)]).get("回调形参", []), []
        )


class TestLazyLogArgs(unittest.TestCase):
    """日志消息串留占位往后传参判硬性，就地拼好的写法不误报"""

    def test_placeholder_with_args_flagged(self) -> None:
        """两种占位写法都命中"""
        head = (
            _skeleton("src/ui/_probe_lazy.py")
            + "from utils import get_logger\n\n_logger = get_logger('Probe')\n\n\n"
        )
        bucket = _scan(
            [
                (
                    "src/ui/_probe_lazy.py",
                    head
                    + f"def _a() -> None:\n{_FUNC_DOC}    _logger.info('按下 %s', n)\n",
                ),
                (
                    "src/ui/_probe_lazy2.py",
                    _skeleton("src/ui/_probe_lazy2.py")
                    + "from utils import get_logger\n\n_logger = get_logger('P')\n\n\n"
                    + f"def _b() -> None:\n{_FUNC_DOC}    _logger.debug('窗 %(t)s 空', t)\n",
                ),
            ]
        )
        self.assertEqual(len(bucket.get("日志与文案", [])), 2)

    def test_compliant_calls_pass(self) -> None:
        """f-string 现拼、百分号只当单位、非日志器调用都不报"""
        bucket = _scan(
            [
                (
                    "src/ui/_probe_ok.py",
                    _skeleton("src/ui/_probe_ok.py")
                    + "from utils import get_logger\n\n_logger = get_logger('Probe')\n\n\n"
                    + f"def _a(x: int) -> None:\n{_FUNC_DOC}"
                    + "    _logger.info(f'占用 {x}%')\n"
                    + "    _logger.debug('按下', x)\n"
                    + "    _logger.info('占用 80%')\n"
                    + "    box.warning(self, '标题 %s', x)\n",
                )
            ]
        )
        self.assertIsNone(bucket.get("日志与文案"))


class TestChangelogCarrier(unittest.TestCase):
    """CHANGELOG 载体三类判据的命中与对照"""

    _COMPLIANT = (
        "# Changelog\n"
        "\n"
        "本项目的所有重要更改都记录在此文件中。\n"
        "\n"
        "## [Unreleased]\n"
        "\n"
        "### ✨ Added\n"
        "\n"
        "- **跨平台**：QQ 平台实装。\n"
        "\n"
        "## [1.0.0-alpha.7.dev7] - 2026-11-17\n"
        "\n"
        "### 🔧 Changed\n"
        "\n"
        "- 一条改动，句末带句号。\n"
        "  - 缩进子项一行。\n"
    )

    def _hits(self, body: str) -> list[str]:
        """扫一份 CHANGELOG 样张，取日志与文案分节条目"""
        return _scan([("CHANGELOG.md", body)]).get("日志与文案", [])

    def test_compliant_body_passes(self) -> None:
        """合规样张零条目"""
        self.assertEqual(self._hits(self._COMPLIANT), [])

    def test_fullwidth_semicolon_flagged(self) -> None:
        """行含全角分号即报"""
        hits = self._hits("- 一句话说完；再来一句。\n")
        self.assertEqual(len([t for t in hits if "全角分号" in t]), 1, hits)

    def test_version_heading_shapes(self) -> None:
        """版本号坏形状、缺日期后缀与 Unreleased 多余内容三条都按形状不符报出"""
        hits = self._hits(
            "## [1.0] - 2026-11-18\n"
            "\n"
            "## [1.2.3] 2026-11-18\n"
            "\n"
            "## [Unreleased] - 2026-11-18\n"
        )
        self.assertEqual(len([t for t in hits if "版本段标题形状不符" in t]), 3, hits)

    def test_prerelease_heading_accepted(self) -> None:
        """alpha、beta 与 rc 各带 dev 实录后缀的段标题都放行"""
        hits = self._hits(
            "## [1.0.0-alpha.7.dev7] - 2026-11-17\n"
            "\n"
            "## [1.0.0-beta.2.dev3] - 2026-11-17\n"
            "\n"
            "## [1.0.0-rc.1] - 2026-11-17\n"
        )
        self.assertEqual(hits, [])

    def test_dev_suffix_needs_stage(self) -> None:
        """实录段只在预发布阶段之后放行，裸 dev 串报出"""
        hits = self._hits("## [1.0.1.dev0] - 2026-11-18\n")
        self.assertEqual(len([t for t in hits if "版本段标题形状不符" in t]), 1, hits)

    def test_bullet_period(self) -> None:
        """子项行末缺句号即报，止于冒号的纯主题行不误报"""
        hits = self._hits("- 缺句号的子项\n- **主题**：\n")
        self.assertEqual(len([t for t in hits if "子项行末缺句号" in t]), 1, hits)


class TestAliasPrivacy(unittest.TestCase):
    """模块级别名按消费者定私有性"""

    def _naming(self, samples: list[tuple[str, str]]) -> list[str]:
        """取命名分节的条目文本"""
        return _scan(samples).get("命名与门面导出", [])

    def test_unused_alias_flagged(self) -> None:
        """无人导入的别名提示加前缀"""
        rel = "src/ui/_probe_alias.py"
        found = self._naming([(rel, _skeleton(rel) + "HolderName = tuple[str, str]\n")])
        self.assertTrue(any("HolderName" in text for text in found), found)

    def test_imported_alias_passes(self) -> None:
        """被他模块导入的别名算对外，不报"""
        holder = "src/ui/_probe_holder.py"
        user = "src/ui/_probe_user.py"
        found = self._naming(
            [
                (holder, _skeleton(holder) + "WidgetSet = dict[str, str]\n"),
                (
                    user,
                    _skeleton(user)
                    + "from ._probe_holder import WidgetSet\n\n_USE = WidgetSet\n",
                ),
            ]
        )
        self.assertFalse(any("WidgetSet" in text for text in found), found)

    def test_type_constructor_exempt(self) -> None:
        """类型构造的别名不判，标识类型集中定义处按设计公开"""
        rel = "src/ui/_probe_newtype.py"
        source = (
            _skeleton(rel)
            + "from typing import NewType\n\nSlotId = NewType('SlotId', str)\n"
        )
        self.assertFalse(
            any("SlotId" in text for text in self._naming([(rel, source)]))
        )

    def test_styled_assignment_not_duplicated(self) -> None:
        """大写常量档归 _s5c_constants，别名档不重复报同一条"""
        rel = "src/ui/_probe_styled.py"
        found = self._naming([(rel, _skeleton(rel) + "WIDGET_SET = 1\n")])
        self.assertEqual(len([text for text in found if "WIDGET_SET" in text]), 1)


class TestPackageDeclaration(unittest.TestCase):
    """点分模块名按各仓自己的改名声明算"""

    def _naming(self, declared: bool) -> list[str]:
        """造一只子仓与一个按声明名取用它的消费者，回命名分节的相关条目"""
        provider = "mini/src/_log.py"
        user = "src/core/_use_log.py"
        samples: list[tuple[str, str]] = [
            (
                provider,
                _skeleton(provider) + f"def bind_logger() -> None:\n{_FUNC_DOC}",
            ),
            (
                user,
                _skeleton(user)
                + "from mini_pkg._log import bind_logger\n\n_USE = bind_logger\n",
            ),
        ]
        if declared:
            samples.insert(
                0,
                (
                    "mini/pyproject.toml",
                    '[tool.setuptools]\npackage-dir = {"mini_pkg" = "src"}\n',
                ),
            )
        found = _scan(samples, ("src", "mini")).get("命名与门面导出", [])
        return [text for text in found if "bind_logger" in text]

    def test_declared_package_name(self) -> None:
        """子仓声明了改名就按声明算名，取用它的符号不判无消费者"""
        self.assertEqual(self._naming(True), [])

    def test_missing_declaration_falls_back(self) -> None:
        """没有声明才退回按目录上溯，此时声明名那条对不上、照常报出"""
        self.assertTrue(self._naming(False))


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

    def test_file_size_not_waivable(self) -> None:
        """单文件行数超限只认拆或抬常量，清单罩不住"""
        rel = "src/ui/_probe_size.py"
        source = _skeleton(rel) + "_USE = None\n" * 300
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / rel
            target.parent.mkdir(parents=True)
            target.write_text(source, encoding="utf-8")
            files = load_files(root, [root / "src"])
            sized = [
                item
                for item in run_checks(files, ImportGraph(files))
                if item.section == "拆分粒度" and item.rel == rel
            ]
        self.assertTrue(sized, "样本没造出单文件行数超限")
        waiver = Waiver(section="拆分粒度", path=rel, reason="探针")
        self.assertEqual(
            [item.message for item in sized if waiver.covers(item)],
            [],
            "行数阈值被清单罩住了",
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
        """按闸门那份目标扫到后，清单里不许留失效条目"""
        files = load_files(_ROOT, _gate_targets())
        findings = run_checks(files, ImportGraph(files))
        waivers = load_waivers(_HERE.parent / "style_waivers.toml")
        _, dead = apply_waivers(findings, waivers)
        judged = _judged_dead(dead, list(SECTIONS), {f.rel for f in files})
        self.assertEqual(
            [(w.section, w.path) for w in judged],
            [],
            "有豁免条目已不再命中，代码改完要删清单",
        )

    def test_hard_only_keeps_live_waivers(self) -> None:
        """只输出硬性时不许把在用的豁免判成失效"""
        ordered, _ = _run(_gate_targets(), list(SECTIONS), True)
        self.assertEqual(
            [f.message for f in ordered if "失效豁免" in f.message],
            [],
            "硬性过滤排在豁免匹配之前，清单条目会全被判死",
        )

    def test_dead_waiver_needs_path_loaded(self) -> None:
        """失效判据按本轮装载的路径与分节覆盖面算，漏改会让失效检测静默停摆"""
        src_waiver = Waiver("命名与门面导出", "src/ui/_probe.py", "理由")
        sub_waiver = Waiver("命名与门面导出", "finshin/sdk/src/x.py", "理由")
        dead = (src_waiver, sub_waiver)
        loaded = {"src/ui/_probe.py", "CHANGELOG.md"}
        sections = list(SECTIONS)
        cases = (
            (dead, sections, loaded, (src_waiver,)),
            (dead, sections[:2], loaded, ()),
            (dead, sections, set(), ()),
            ((), sections, loaded, ()),
        )
        for want_dead, want_sections, want_loaded, expected in cases:
            with self.subTest(sections=len(want_sections), loaded=sorted(want_loaded)):
                self.assertEqual(
                    _judged_dead(want_dead, want_sections, want_loaded), expected
                )


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


class TestMissingTarget(unittest.TestCase):
    """扫描目标不在场时的取径"""

    def _run_main(self, target: Path) -> tuple[int, str]:
        sink = io.StringIO()
        with redirect_stderr(sink):
            code = check_coding_style.main([str(target)])
        return code, sink.getvalue()

    def test_wrong_path_still_errors(self) -> None:
        """路径写错即报错退出"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        absent = Path(holder.name) / "typo_dir"
        code, text = self._run_main(absent)
        self.assertEqual(code, 2, text)


if __name__ == "__main__":
    unittest.main()
