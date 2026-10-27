# devtools/tests/test_persona_sync.py
"""人设模板对账与正文重读的单元测试

- 副本缺失即从模板建好并落戳，不打扰
- 副本内容等于戳所记的模板才自动换新，行尾转换不算改动
- 从未改动判不出即弹一键覆盖窗，提示送达才记本版已提示
- 一键覆盖落当前模板指纹并重置进程内人设缓存
- 提示弹一键覆盖窗，自动换新只交回换新版标记
- 总控接线换成新版且清成功才弹告知窗，清不成不弹
- 对账排在配置进内存之后
- 打开入口用的副本补建只在缺失时动手
- 正文缓存按磁盘副本刷新，副本没变不报变化
- 磁盘正文按副本、内置模板、空正文三级取，取正文不装填缓存
- 副本与模板和戳都不同即判不出未改动，只提示不覆盖
"""

import asyncio
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from skin.messages import MiscMessage  # noqa: E402
from utils import init_files, persona  # noqa: E402

_V1 = "# 默认人设 v1\n"
_V2 = "# 默认人设 v2\n"
_V3 = "# 默认人设 v3\n"
_EDITED = "# 我自己改过的人设\n"


class _StageBase(unittest.TestCase):
    """把模板、实例副本与对账戳换成临时盘上的可控值"""

    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory(prefix="finshin-persona-")
        self.addCleanup(stage.cleanup)
        root = Path(stage.name)
        self.template = root / "persona.example.md"
        self.copy = root / "persona.md"
        self.stamp = root / ".persona.base"
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, path in (
            ("PERSONALITY_EXAMPLE", self.template),
            ("PERSONALITY_FILE", self.copy),
            ("PERSONALITY_STAMP", self.stamp),
        ):
            self.stack.enter_context(patch.object(init_files, name, path))
        for name, path in (
            ("PERSONALITY_EXAMPLE", self.template),
            ("PERSONALITY_FILE", self.copy),
        ):
            self.stack.enter_context(patch.object(persona, name, path))
        persona.reset_persona_cache()
        self.addCleanup(persona.reset_persona_cache)

    def write_template(self, text: str) -> None:
        """写内置默认模板"""
        self.template.write_text(text, encoding="utf-8")

    def write_copy(self, text: str) -> None:
        """写实例人设副本"""
        self.copy.write_text(text, encoding="utf-8")

    def sync(self) -> init_files.PersonaSync:
        """跑一次对账"""
        return init_files.sync_persona_template()


class TestSyncPersonaTemplate(_StageBase):
    """副本、模板与戳三方比对"""

    def test_missing_copy_created_from_template(self) -> None:
        """副本缺失即从模板建好并落戳"""
        self.write_template(_V1)

        self.assertIs(self.sync(), init_files.PersonaSync.UNCHANGED)
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V1)
        self.assertEqual(
            self.stamp.read_text(encoding="utf-8"), init_files._digest(self.template)
        )

    def test_copy_matching_template_writes_stamp_only(self) -> None:
        """副本已是当前模板即只补落戳，缺戳也不惊动用户"""
        self.write_template(_V1)
        self.write_copy(_V1)

        self.assertIs(self.sync(), init_files.PersonaSync.UNCHANGED)
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V1)
        self.assertEqual(
            self.stamp.read_text(encoding="utf-8"), init_files._digest(self.template)
        )

    def test_untouched_copy_auto_updated(self) -> None:
        """副本仍是戳所记的旧模板原样即自动换新"""
        self.write_template(_V1)
        self.sync()
        self.write_template(_V2)

        self.assertIs(self.sync(), init_files.PersonaSync.UPDATED)
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V2)
        self.assertEqual(
            self.stamp.read_text(encoding="utf-8"), init_files._digest(self.template)
        )

    def test_edited_copy_notifies_until_prompted(self) -> None:
        """提示未送达即不落戳，落戳后同一版模板不再提示"""
        self.write_template(_V1)
        self.sync()
        self.write_copy(_EDITED)
        self.write_template(_V2)

        self.assertIs(self.sync(), init_files.PersonaSync.NOTIFY)
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _EDITED)
        self.assertNotEqual(
            self.stamp.read_text(encoding="utf-8"), init_files._digest(self.template)
        )

        self.assertIs(self.sync(), init_files.PersonaSync.NOTIFY)

        init_files.mark_persona_prompted()
        self.assertIs(self.sync(), init_files.PersonaSync.UNCHANGED)
        self.assertEqual(
            self.stamp.read_text(encoding="utf-8"), init_files._digest(self.template)
        )

    def test_apply_template_after_prompt_clears_cache(self) -> None:
        """提示过再点覆盖，正文按模板重读"""
        self.write_template(_V1)
        self.sync()
        self.write_copy(_EDITED)
        init_files.mark_persona_prompted()

        self.assertEqual(persona.build_persona(""), _EDITED)

        self.assertTrue(init_files.apply_persona_template())

        self.assertEqual(persona.build_persona(""), _V1)

    def test_edited_copy_notifies_again_on_next_template(self) -> None:
        """提示送达后模板再更新即重新提示一轮"""
        self.write_template(_V1)
        self.sync()
        self.write_copy(_EDITED)
        self.write_template(_V2)
        self.sync()
        init_files.mark_persona_prompted()
        self.write_template(_V3)

        self.assertIs(self.sync(), init_files.PersonaSync.NOTIFY)
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _EDITED)

    def test_legacy_copy_without_stamp_only_notifies(self) -> None:
        """无戳的旧副本无从证明未改动，绝不覆盖只提示"""
        self.write_template(_V2)
        self.write_copy(_V1)

        self.assertIs(self.sync(), init_files.PersonaSync.NOTIFY)
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V1)
        self.assertFalse(self.stamp.exists())

    def test_crlf_copy_counts_as_untouched(self) -> None:
        """副本只被编辑器换成 CRLF 行尾即仍判未改动"""
        self.write_template(_V1)
        self.sync()
        self.copy.write_bytes(_V2.encode("utf-8").replace(b"\n", b"\r\n"))
        self.write_template(_V2)

        self.assertIs(self.sync(), init_files.PersonaSync.UNCHANGED)

    def test_absent_template_skips(self) -> None:
        """模板缺失即不判定，副本原样保留"""
        self.write_copy(_EDITED)

        self.assertIs(self.sync(), init_files.PersonaSync.UNCHANGED)
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _EDITED)
        self.assertFalse(self.stamp.exists())


class TestApplyPersonaTemplate(_StageBase):
    """用户当场授权的一键覆盖"""

    def test_copy_replaced_and_stamp_written(self) -> None:
        """覆盖即换新并落当前模板指纹"""
        self.write_template(_V2)
        self.write_copy(_EDITED)

        self.assertTrue(init_files.apply_persona_template())
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V2)
        self.assertEqual(
            self.stamp.read_text(encoding="utf-8"), init_files._digest(self.template)
        )

    def test_cache_reset_after_apply(self) -> None:
        """覆盖后进程内缓存失效，下一轮组装取到新正文"""
        self.write_template(_V2)
        self.write_copy(_EDITED)
        self.assertEqual(persona.build_persona(""), _EDITED)

        init_files.apply_persona_template()

        self.assertEqual(persona.build_persona(""), _V2)

    def test_unreadable_template_returns_false(self) -> None:
        """模板读不出即判失败，副本原样保留"""
        self.write_copy(_EDITED)

        self.assertFalse(init_files.apply_persona_template())
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _EDITED)
        self.assertFalse(self.stamp.exists())

    def test_mark_skipped_without_template(self) -> None:
        """模板缺失即不落已提示戳"""
        init_files.mark_persona_prompted()

        self.assertFalse(self.stamp.exists())


class TestEnsurePersonaCopy(_StageBase):
    """打开入口依赖的副本补建"""

    def test_missing_copy_created_with_stamp(self) -> None:
        """副本缺失即从模板建好并落当前模板戳"""
        self.write_template(_V1)

        self.assertTrue(init_files.ensure_persona_copy())
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V1)
        self.assertEqual(
            self.stamp.read_text(encoding="utf-8"), init_files._digest(self.template)
        )

    def test_existing_copy_kept(self) -> None:
        """副本已在即原样保留，内容不动也不刷戳"""
        self.write_template(_V2)
        self.write_copy(_EDITED)
        self.stamp.write_text("旧戳", encoding="utf-8")

        self.assertTrue(init_files.ensure_persona_copy())
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _EDITED)
        self.assertEqual(self.stamp.read_text(encoding="utf-8"), "旧戳")

    def test_absent_template_returns_false(self) -> None:
        """模板读不出即判失败，不留半个副本"""
        self.assertFalse(init_files.ensure_persona_copy())

        self.assertFalse(self.copy.exists())


class TestResyncOnSave(_StageBase):
    """重跑对账即按磁盘当前内容重读正文"""

    def setUp(self) -> None:
        super().setUp()
        from bot._managers import _initialization

        self.stack.enter_context(
            patch.object(_initialization.gui_bridge, "request_persona_update")
        )
        self.manager = _initialization.InitializationManager()

    def _body(self) -> str:
        """取当前组装出的正文"""
        return persona.build_persona("")

    def test_copy_edit_reads_in_after_resync(self) -> None:
        """重跑一次即按磁盘当前内容重新组装，且不动副本"""
        self.write_template(_V1)
        self.manager.sync_persona()
        self.assertEqual(self._body(), _V1)

        self.write_copy(_EDITED)

        self.assertEqual(self._body(), _V1)

        self.manager.sync_persona()

        self.assertEqual(self._body(), _EDITED)
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _EDITED)


class TestStartupWiring(unittest.TestCase):
    """启动接线按对账结果分派弹窗"""

    def setUp(self) -> None:
        from bot._managers import _initialization

        self.initialization = _initialization
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.result = self.stack.enter_context(
            patch.object(
                _initialization,
                "sync_persona_template",
                return_value=init_files.PersonaSync.NOTIFY,
            )
        )
        self.popup = self.stack.enter_context(
            patch.object(_initialization.gui_bridge, "request_persona_update")
        )
        self.notice = self.stack.enter_context(
            patch.object(_initialization.gui_bridge, "request_notice")
        )
        self.manager = _initialization.InitializationManager()

    def test_notify_emits_persona_popup(self) -> None:
        """判为需用户定夺才弹一键覆盖窗"""
        self.assertFalse(self.manager.sync_persona())

        self.result.assert_called_once_with()
        self.popup.emit.assert_called_once()
        self.notice.emit.assert_not_called()

    def test_updated_returns_swap_flag_without_popup(self) -> None:
        """自动换新只交回换新版标记，告知窗归总控接线"""
        self.result.return_value = init_files.PersonaSync.UPDATED

        self.assertTrue(self.manager.sync_persona())

        self.popup.emit.assert_not_called()
        self.notice.emit.assert_not_called()


class TestStartupNotice(unittest.TestCase):
    """总控按清理结果决定要不要弹告知窗"""

    def _wire(self, swapped: bool, cleared: bool):
        """拼出只关心人设与清理的总控，交出清理调用记录"""
        from bot._managers import BotManager, _manager

        calls: list[int] = []

        async def _noop() -> None:
            return None

        async def _reset() -> bool:
            calls.append(1)
            return cleared

        manager = BotManager.__new__(BotManager)
        manager._initializer = SimpleNamespace(
            execute=_noop, sync_persona=lambda: swapped
        )
        manager._applier = SimpleNamespace(apply_config=_noop, reset_identity=_reset)
        notice = self.enterContext(patch.object(_manager.gui_bridge, "request_notice"))
        return manager, calls, notice

    def test_swapped_and_cleared_opens_notice(self) -> None:
        """换成新版且清成功才弹告知"""
        manager, calls, notice = self._wire(swapped=True, cleared=True)

        asyncio.run(manager.start())

        self.assertEqual(calls, [1])
        notice.emit.assert_called_once_with(MiscMessage.PERSONA_AUTO_APPLIED, False)

    def test_unswapped_stays_silent(self) -> None:
        """没换新版就不清也不弹"""
        manager, calls, notice = self._wire(swapped=False, cleared=True)

        asyncio.run(manager.start())

        self.assertEqual(calls, [])
        notice.emit.assert_not_called()

    def test_clear_failure_stays_silent(self) -> None:
        """清理没办成就不弹，免得报假清空"""
        manager, calls, notice = self._wire(swapped=True, cleared=False)

        asyncio.run(manager.start())

        self.assertEqual(calls, [1])
        notice.emit.assert_not_called()


class TestStartupOrder(unittest.TestCase):
    """对账排在配置进内存之后"""

    def test_sync_runs_after_config_apply(self) -> None:
        """start 先应用配置再对人设"""
        from bot._managers import BotManager

        order: list[str] = []

        async def execute() -> None:
            order.append("init")

        async def apply_config() -> None:
            order.append("apply")

        manager = BotManager.__new__(BotManager)
        manager._initializer = SimpleNamespace(
            execute=execute, sync_persona=lambda: order.append("persona")
        )
        manager._applier = SimpleNamespace(apply_config=apply_config)

        asyncio.run(manager.start())

        self.assertEqual(order, ["init", "apply", "persona"])


class TestReloadPersonaCache(_StageBase):
    """正文缓存按磁盘副本刷新"""

    def test_empty_cache_skips_compare(self) -> None:
        """缓存未装填不作判定，组装按磁盘内容填"""
        self.write_copy(_V1)
        self.assertFalse(persona.reload_persona_cache())
        self.assertEqual(persona.build_persona(""), _V1)

    def test_same_copy_reports_no_change(self) -> None:
        """副本与缓存逐字相同即无变化"""
        self.write_copy(_V1)
        persona.build_persona("")
        self.assertFalse(persona.reload_persona_cache())
        self.assertEqual(persona.build_persona(""), _V1)

    def test_edited_copy_refreshes_cache(self) -> None:
        """副本被改过即把缓存换成磁盘正文"""
        self.write_copy(_V1)
        persona.build_persona("")
        self.write_copy(_V2)
        self.assertTrue(persona.reload_persona_cache())
        self.assertEqual(persona.build_persona(""), _V2)

    def test_missing_copy_falls_back_to_template(self) -> None:
        """副本读不出即弃缓存，组装退回内置模板正文"""
        self.write_template(_V2)
        self.write_copy(_V1)
        persona.build_persona("")
        self.copy.unlink()

        self.assertTrue(persona.reload_persona_cache())
        self.assertEqual(persona.build_persona(""), _V2)


class TestReadPersonaText(_StageBase):
    """磁盘正文按副本、内置模板、空正文三级取"""

    def test_copy_preferred(self) -> None:
        """副本可读即以副本为准"""
        self.write_template(_V2)
        self.write_copy(_V1)

        self.assertEqual(persona.read_persona_text(), (_V1, persona.PersonaSource.FILE))

    def test_template_used_without_copy(self) -> None:
        """副本读不出即退内置模板"""
        self.write_template(_V2)

        self.assertEqual(
            persona.read_persona_text(), (_V2, persona.PersonaSource.TEMPLATE)
        )

    def test_empty_without_copy_and_template(self) -> None:
        """模板也读不出即空正文"""
        self.assertEqual(persona.read_persona_text(), ("", persona.PersonaSource.EMPTY))

    def test_owner_injected_into_body(self) -> None:
        """组装把主人 id 填进占位符"""
        self.write_copy("主人 id 是 {OWNER_ID}\n")

        self.assertEqual(persona.build_persona("456"), "主人 id 是 456\n")

    def test_read_keeps_cache_untouched(self) -> None:
        """取正文不装填缓存，预览读盘不改运行中的正文"""
        self.write_template(_V2)
        self.write_copy(_V1)
        persona.build_persona("")

        self.write_copy(_EDITED)
        persona.read_persona_text()

        self.assertEqual(persona.build_persona(""), _V1)
        self.assertEqual(persona.applied_persona_text(), _V1)


class TestCheckPersonaState(_StageBase):
    """副本、模板与对账戳的关系判定"""

    def test_same_when_copy_matches_template(self) -> None:
        """副本即当前模板"""
        self.write_template(_V1)
        self.write_copy(_V1)

        self.assertIs(init_files.check_persona_state(), init_files.PersonaState.SAME)

    def test_outdated_when_copy_matches_stamp(self) -> None:
        """副本还是戳所记的旧模板即有版可换"""
        self.write_template(_V1)
        self.sync()
        self.write_template(_V2)

        self.assertIs(
            init_files.check_persona_state(), init_files.PersonaState.OUTDATED
        )

    def test_edited_when_copy_matches_neither(self) -> None:
        """副本与模板和戳都不同即判不出未改动"""
        self.write_template(_V2)
        self.write_copy(_EDITED)

        self.assertIs(init_files.check_persona_state(), init_files.PersonaState.EDITED)

    def test_unreadable_without_copy(self) -> None:
        """副本读不出即无从比对"""
        self.write_template(_V1)

        self.assertIs(
            init_files.check_persona_state(), init_files.PersonaState.UNREADABLE
        )


if __name__ == "__main__":
    unittest.main()
