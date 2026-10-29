# devtools/tests/test_persona_sync.py
"""人设模板对账与生效正文的单元测试

- 副本缺失即从模板建好并落戳，不打扰
- 副本内容等于戳所记的模板才自动换新，行尾转换不算改动
- 从未改动判不出即弹一键覆盖窗，提示送达才记本版已提示
- 一键覆盖落当前模板指纹，换副本、刷存档与重装正文同批
- 提示弹一键覆盖窗，自动换新只交回换新版标记
- 总控接线换成新版且清成功才弹告知窗，清不成不弹
- 拍板排在对账前面，起服务不等拍板
- 打开入口用的副本补建只在缺失时动手
- 生效正文按存档装填，存档缺失按副本补落一次
- 运行期只读生效正文，外部改过的副本要拍板才生效
- 外部改动靠文件与存档比对检出，一致或读不出都不打扰
- 磁盘正文按副本、内置模板、空正文三级取，取正文不装填正文
- 副本与模板和戳都不同即判不出未改动，只提示不覆盖
- 写入副本只动副本，存档与对账戳留给落盘与对账
- 模板原文供覆盖确认窗比对，读不出给空串
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

from skin.messages import DialogMessage, MiscMessage  # noqa: E402
from utils import init_files, persona  # noqa: E402

_V1 = "# 默认人设 v1\n"
_V2 = "# 默认人设 v2\n"
_V3 = "# 默认人设 v3\n"
_EDITED = "# 我自己改过的人设\n"


class _StageBase(unittest.TestCase):
    """把模板、副本、对账戳与存档换成可控值

    - 四个文件路径各指临时盘
    - 生效正文槽在每条用例开头清空
    """

    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory(prefix="finshin-persona-")
        self.addCleanup(stage.cleanup)
        root = Path(stage.name)
        self.template = root / "persona.example.md"
        self.copy = root / "persona" / "persona.md"
        self.stamp = root / "persona" / "template.sha256"
        self.applied = root / "persona" / "applied.cache"
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, path in (
            ("PERSONA_TEMPLATE", self.template),
            ("PERSONA_FILE", self.copy),
            ("PERSONA_STAMP", self.stamp),
        ):
            self.stack.enter_context(patch.object(init_files, name, path))
        for name, path in (
            ("PERSONA_TEMPLATE", self.template),
            ("PERSONA_FILE", self.copy),
            ("PERSONA_APPLIED", self.applied),
        ):
            self.stack.enter_context(patch.object(persona, name, path))
        self.stack.enter_context(patch.object(persona, "_persona_text", ""))

    def write_template(self, text: str) -> None:
        """写内置默认模板"""
        self.template.write_text(text, encoding="utf-8")

    def write_copy(self, text: str) -> None:
        """写实例人设副本"""
        self.copy.parent.mkdir(parents=True, exist_ok=True)
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
        """副本仍是戳所记的旧模板原样即自动换新并顺手刷存档"""
        self.write_template(_V1)
        self.sync()
        self.write_template(_V2)

        self.assertIs(self.sync(), init_files.PersonaSync.UPDATED)
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V2)
        self.assertEqual(self.applied.read_text(encoding="utf-8"), _V2)
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

    def test_apply_template_after_prompt_reloads_cache(self) -> None:
        """提示过再点覆盖，正文按新副本重装"""
        self.write_template(_V1)
        self.sync()
        self.write_copy(_EDITED)
        init_files.mark_persona_prompted()
        persona.load_persona_cache()

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
        """覆盖即换新副本、刷存档并落当前模板指纹"""
        self.write_template(_V2)
        self.write_copy(_EDITED)

        self.assertTrue(init_files.apply_persona_template())
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V2)
        self.assertEqual(self.applied.read_text(encoding="utf-8"), _V2)
        self.assertEqual(
            self.stamp.read_text(encoding="utf-8"), init_files._digest(self.template)
        )

    def test_cache_reloaded_after_apply(self) -> None:
        """覆盖后进程内正文换成新副本，组装取到新正文"""
        self.write_template(_V2)
        self.write_copy(_EDITED)
        persona.load_persona_cache()
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

        self.assertTrue(init_files._ensure_persona_copy())
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V1)
        self.assertEqual(
            self.stamp.read_text(encoding="utf-8"), init_files._digest(self.template)
        )

    def test_existing_copy_kept(self) -> None:
        """副本已在即原样保留，内容不动也不刷戳"""
        self.write_template(_V2)
        self.write_copy(_EDITED)
        self.stamp.write_text("旧戳", encoding="utf-8")

        self.assertTrue(init_files._ensure_persona_copy())
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _EDITED)
        self.assertEqual(self.stamp.read_text(encoding="utf-8"), "旧戳")

    def test_absent_template_returns_false(self) -> None:
        """模板读不出即判失败，不留半个副本"""
        self.assertFalse(init_files._ensure_persona_copy())

        self.assertFalse(self.copy.exists())


class TestSavePersonaText(_StageBase):
    """落盘第一步只写副本"""

    def test_copy_replaced_only(self) -> None:
        """写入即换副本，生效正文与存档都不动"""
        self.write_copy(_V1)
        persona.load_persona_cache()

        self.assertTrue(init_files.save_persona_text(_V2))
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _V2)
        self.assertEqual(self.applied.read_text(encoding="utf-8"), _V1)
        self.assertEqual(persona.build_persona(""), _V1)

    def test_stamp_left_untouched(self) -> None:
        """写过的副本不刷戳，对账按用户改动版处理"""
        self.write_template(_V1)
        self.sync()
        stamp = self.stamp.read_text(encoding="utf-8")

        self.assertTrue(init_files.save_persona_text(_EDITED))

        self.assertEqual(self.stamp.read_text(encoding="utf-8"), stamp)

    def test_missing_copy_created_first(self) -> None:
        """副本缺失即先建好再写入正文"""
        self.write_template(_V1)

        self.assertTrue(init_files.save_persona_text(_EDITED))
        self.assertEqual(self.copy.read_text(encoding="utf-8"), _EDITED)

    def test_absent_template_returns_false(self) -> None:
        """模板读不出又没副本即判失败"""
        self.assertFalse(init_files.save_persona_text(_EDITED))
        self.assertFalse(self.copy.exists())


class TestReadTemplateText(_StageBase):
    """覆盖确认窗要的模板原文"""

    def test_template_read_as_is(self) -> None:
        """正文按原文读出，不做注入也不加工"""
        self.write_template(_V1)
        self.assertEqual(persona.read_template_text(), _V1)

    def test_absent_template_returns_empty(self) -> None:
        """模板读不出给空串，由调用方判停"""
        self.assertEqual(persona.read_template_text(), "")


class TestExternalDetection(_StageBase):
    """启动比对文件与存档，不一致才开拍板窗"""

    def setUp(self) -> None:
        super().setUp()
        from bot._managers import _initialization

        self.manager = _initialization.InitializationManager()
        self.resolve = self.stack.enter_context(
            patch.object(_initialization.gui_bridge, "request_persona_resolve")
        )

    def test_edited_copy_opens_resolve(self) -> None:
        """文件与存档不一致即发拍板信号，带两栏栏名"""
        self.write_copy(_V1)
        persona.load_persona_cache()
        self.write_copy(_EDITED)

        self.manager.detect_external_persona()

        self.resolve.emit.assert_called_once_with(
            _V1,
            _EDITED,
            DialogMessage.SETUP_PERSONA_LABEL_SAVED,
            DialogMessage.SETUP_PERSONA_LABEL_FILE,
        )

    def test_cache_keeps_applied_after_edit(self) -> None:
        """外部改动不自动顶替生效正文"""
        self.write_copy(_V1)
        persona.load_persona_cache()
        self.write_copy(_EDITED)

        self.assertEqual(persona.build_persona(""), _V1)

    def test_same_text_stays_silent(self) -> None:
        """两处一致不打扰"""
        self.write_copy(_V1)
        persona.load_persona_cache()

        self.manager.detect_external_persona()

        self.resolve.emit.assert_not_called()

    def test_missing_file_stays_silent(self) -> None:
        """文件读不出不打扰，装填那处已报过"""
        self.write_copy(_V1)
        persona.load_persona_cache()
        self.copy.unlink()

        self.manager.detect_external_persona()

        self.resolve.emit.assert_not_called()


class TestInitFiles(_StageBase):
    """建路径那一步把正文装好

    - 目录创建挂空，只验装填时机
    """

    def test_cache_loaded_before_config_apply(self) -> None:
        """配置应用之前正文已按磁盘装填，身份基准不落空"""
        from bot._managers import _initialization

        self.stack.enter_context(patch.object(_initialization, "init_project_files"))
        self.write_copy(_V1)

        _initialization.InitializationManager()._init_files()

        self.assertEqual(persona.applied_persona_text(), _V1)
        self.assertEqual(self.applied.read_text(encoding="utf-8"), _V1)


class TestStartupWiring(unittest.TestCase):
    """启动接线按对账结果分派弹窗

    - 正文装填在本组挂空，只留弹窗分派一条线
    """

    def setUp(self) -> None:
        from bot._managers import _initialization

        self.initialization = _initialization
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.load = self.stack.enter_context(
            patch.object(_initialization, "load_persona_cache")
        )
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
        self.load.assert_called_once_with()
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
            execute=_noop,
            detect_external_persona=lambda: None,
            sync_persona=lambda: swapped,
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
    """拍板排在对账前面，起服务不等拍板"""

    def test_resolve_runs_before_sync(self) -> None:
        """start 先应用配置，再比对文件，最后对人设模板"""
        from bot._managers import BotManager

        order: list[str] = []

        async def execute() -> None:
            order.append("init")

        async def apply_config() -> None:
            order.append("apply")

        def detect() -> None:
            order.append("detect")

        manager = BotManager.__new__(BotManager)
        manager._initializer = SimpleNamespace(
            execute=execute,
            detect_external_persona=detect,
            sync_persona=lambda: order.append("persona"),
        )
        manager._applier = SimpleNamespace(apply_config=apply_config)

        asyncio.run(manager.start())

        self.assertEqual(order, ["init", "apply", "detect", "persona"])


class TestLoadPersonaCache(_StageBase):
    """生效正文按存档装填，存档缺失才按副本补落"""

    def test_load_fills_from_applied(self) -> None:
        """存档在场即以存档为准，副本内容不参与"""
        self.write_copy(_V2)
        self.applied.write_text(_V1, encoding="utf-8")

        persona.load_persona_cache()

        self.assertEqual(persona.applied_persona_text(), _V1)

    def test_missing_applied_seeds_from_copy(self) -> None:
        """存档缺失即按副本装填并补落一次"""
        self.write_copy(_V1)

        persona.load_persona_cache()

        self.assertEqual(persona.applied_persona_text(), _V1)
        self.assertEqual(self.applied.read_text(encoding="utf-8"), _V1)

    def test_missing_copy_falls_back_to_template(self) -> None:
        """副本读不出即按内置模板装填，不落存档"""
        self.write_template(_V2)

        persona.load_persona_cache()

        self.assertEqual(persona.applied_persona_text(), _V2)
        self.assertFalse(self.applied.exists())

    def test_external_edit_stays_out_of_cache(self) -> None:
        """装填之后外部改副本不碰生效正文"""
        self.write_copy(_V1)
        persona.load_persona_cache()

        self.write_copy(_V2)
        persona.load_persona_cache()

        self.assertEqual(persona.applied_persona_text(), _V1)
        self.assertEqual(persona.build_persona(""), _V1)


class TestSaveAppliedPersona(_StageBase):
    """上次生效存档的写入"""

    def test_stored_as_raw_text(self) -> None:
        """主人占位符保持字面，换主人不被判成正文变了"""
        self.assertTrue(persona.save_applied_persona("主人是 {OWNER_ID}\n"))

        self.assertEqual(
            self.applied.read_text(encoding="utf-8"), "主人是 {OWNER_ID}\n"
        )

    def test_unwritable_returns_false(self) -> None:
        """写不进返回 False，调用方据此不换正文"""
        self.applied.parent.mkdir(parents=True, exist_ok=True)
        self.applied.mkdir()

        self.assertFalse(persona.save_applied_persona(_V1))


class TestReadPersonaText(_StageBase):
    """磁盘正文按副本、内置模板、空正文三级取"""

    def test_copy_preferred(self) -> None:
        """副本可读即以副本为准"""
        self.write_template(_V2)
        self.write_copy(_V1)

        self.assertEqual(
            persona._read_persona_text(), (_V1, persona._PersonaSource.FILE)
        )

    def test_template_used_without_copy(self) -> None:
        """副本读不出即退内置模板"""
        self.write_template(_V2)

        self.assertEqual(
            persona._read_persona_text(), (_V2, persona._PersonaSource.TEMPLATE)
        )

    def test_empty_without_copy_and_template(self) -> None:
        """模板也读不出即空正文"""
        self.assertEqual(
            persona._read_persona_text(), ("", persona._PersonaSource.EMPTY)
        )

    def test_owner_injected_into_body(self) -> None:
        """组装把主人 id 填进占位符"""
        self.write_copy("主人 id 是 {OWNER_ID}\n")
        persona.load_persona_cache()

        self.assertEqual(persona.build_persona("456"), "主人 id 是 456\n")

    def test_read_keeps_cache_untouched(self) -> None:
        """取正文不装填正文，预览读盘不改运行中的正文"""
        self.write_template(_V2)
        self.write_copy(_V1)
        persona.load_persona_cache()

        self.write_copy(_EDITED)
        persona._read_persona_text()

        self.assertEqual(persona.build_persona(""), _V1)
        self.assertEqual(persona.applied_persona_text(), _V1)


if __name__ == "__main__":
    unittest.main()
