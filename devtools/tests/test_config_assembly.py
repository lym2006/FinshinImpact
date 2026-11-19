"""配置装配与点分段名的回归用例

- ConfigIO：点分三层段名读写，notes 子表读盘丢弃
- _ConfigManager：按来源身份与段名拼出的段名取到值
- ensure_config：缺文件时逐来源复制默认值，已有文件不读不写
- assemble：同一身份码被两份认领时拒后交的那份并点名，同一来源段内重键只留先出现的
  那一项，跨来源同名段各留各的
- config_sources：各来源自己交标题与段，装载不成的插件那一只不进配置
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from config_plan import fake_adapter_parts  # noqa: E402

from bot._managers._config_sources import config_sources  # noqa: E402
from bundled.AI.config import CONFIG_SOURCE  # noqa: E402
from finshin_sdk.domain import (  # noqa: E402
    SECTIONS_BY_PLATFORM,
    ConfigKey,
    ConfigSection,
    FieldSpec,
    Platform,
    SectionSpec,
)
from utils._config_manager import _ConfigManager  # noqa: E402
from utils.config import ensure_config  # noqa: E402
from utils.config._io import ConfigIO  # noqa: E402
from utils.config._schema import build_schema  # noqa: E402
from utils.config.models import FieldSchema, TabSchema  # noqa: E402
from utils.config.sources import ConfigSource, SourceKind, assemble  # noqa: E402

_PROXY_VALUE = "http://127.0.0.1:7890"

_TG = SECTIONS_BY_PLATFORM[Platform.TELEGRAM]  # 接口包交出的段，按平台顺序
_AI = CONFIG_SOURCE.sections  # 插件自己交出的段


def _temp_file() -> Path:
    """临时目录里开一份配置文件路径"""
    return Path(tempfile.mkdtemp()) / "config.toml"


class TestDottedSectionRoundtrip(unittest.TestCase):
    """回归点

    - 段名写成三层点分串，盘上是嵌套表，读回内存与单层段名同值
    """

    def test_three_level_writes_nested_table(self) -> None:
        """三层段名落盘写的是 [adapter.tg.proxy] 而不是带引号的键"""
        path = _temp_file()
        data = {"adapter.tg.proxy": {"proxy": _PROXY_VALUE, "proxy_mode": "auto"}}

        ConfigIO(path).save(data, notes={})

        text = path.read_text(encoding="utf-8")
        self.assertIn('id = "adapter.tg"', text)
        self.assertIn("[source.proxy]", text)
        self.assertNotIn('["proxy"]', text)

    def test_three_level_roundtrip(self) -> None:
        """三层段名存读一轮后值不变"""
        path = _temp_file()
        data = {"adapter.tg.proxy": {"proxy": _PROXY_VALUE, "proxy_mode": "auto"}}

        ConfigIO(path).save(data, notes={})

        self.assertEqual(ConfigIO(path).load(), data)

    def test_manager_reads_assembled_section(self) -> None:
        """取值入口按来源身份与段名拼出的段名读值"""
        mgr = _ConfigManager()
        mgr._schema = [
            TabSchema(
                title="连接",
                section="adapter.tg.proxy",
                group="adapter.tg",
                group_title="Telegram",
                section_id=ConfigSection.PROXY,
                fields=[FieldSchema(ConfigKey.PROXY, "代理", "", "", str)],
            )
        ]
        mgr.load({"adapter.tg.proxy": {"proxy": _PROXY_VALUE}})

        item = ConfigKey.PROXY.path("adapter.tg", ConfigSection.PROXY)
        self.assertEqual(mgr.get(item, str), _PROXY_VALUE)

    def test_notes_subtable_stays_out_of_memory(self) -> None:
        """notes 子表属文件说明，读盘不并进配置"""
        path = _temp_file()
        path.write_text(
            "[[source]]\n"
            'id = "adapter.tg"\n'
            "[source.proxy]\n"
            'proxy = "http://127.0.0.1:7890"\n'
            "[source.proxy.notes]\n"
            'proxy = "自动与仅配置代理两档使用该项"\n'
            "[[source]]\n"
            'id = "core"\n'
            "[source.data]\n"
            "record_keep = 30.0\n"
            "[source.data.notes]\n"
            'record_keep = "闲置超过这个天数的对话记录一并删除"\n',
            encoding="utf-8",
        )

        data = ConfigIO(path).load()

        self.assertEqual(
            data,
            {
                "adapter.tg.proxy": {"proxy": _PROXY_VALUE},
                "core.data": {"record_keep": 30.0},
            },
        )

    def test_notes_written_as_subtable_of_own_section(self) -> None:
        """notes 写在所属段之下，键名与值键同名"""
        path = _temp_file()
        data = {"adapter.tg.proxy": {"proxy": _PROXY_VALUE}}
        notes = {"adapter.tg.proxy": {"proxy": "说明文案"}}

        ConfigIO(path).save(data, notes=notes)

        text = path.read_text(encoding="utf-8")
        self.assertIn("[source.proxy.notes]", text)
        self.assertIn('proxy = "说明文案"', text)


class TestSourceBlockShape(unittest.TestCase):
    """回归点

    - 来源块里除 id 还有别的直接键即拒那一块并点名，那几个键另立一段保留
    - 同一身份码写两块时只认前一块，后一块拒收并点名块序
    """

    def test_block_with_extra_keys_is_refused_and_named(self) -> None:
        """写歪一块不进气，值不丢"""
        path = _temp_file()
        path.write_text(
            "[[source]]\n"
            'id = "core"\n'
            'data = "本该写成 [source.data]"\n'
            "[[source]]\n"
            'id = "plugin.AI"\n'
            "[source.model]\n"
            'api_key = "sk-真"\n',
            encoding="utf-8",
        )

        with self.assertLogs("Bot.Config", level="ERROR") as logs:
            data = ConfigIO(path).load()

        self.assertEqual(set(data), {"core", "plugin.AI.model"})
        self.assertEqual(data["core"]["data"], "本该写成 [source.data]")
        self.assertTrue(any("整块不进配置" in line for line in logs.output))

    def test_duplicate_identity_block_refused_and_named(self) -> None:
        """同一身份码写两块只认前一块，后一块整块不进并点名块序"""
        path = _temp_file()
        path.write_text(
            "[[source]]\n"
            'id = "core"\n'
            "[source.data]\n"
            "record_keep = 12.0\n"
            "[[source]]\n"
            'id = "core"\n'
            "[source.data]\n"
            "record_keep = 99.0\n",
            encoding="utf-8",
        )

        with self.assertLogs("Bot.Config", level="ERROR") as logs:
            data = ConfigIO(path).load()

        self.assertEqual(data["core.data"]["record_keep"], 12.0)
        named = [line for line in logs.output if "重复" in line]
        self.assertEqual(len(named), 1, logs.output)
        self.assertIn("第 2 块", named[0])
        self.assertIn("第 1 块", named[0])


class TestSourceAssembly(unittest.TestCase):
    """回归点

    - 缺配置文件时逐来源交出各自默认值，段顺序即来源顺序
    - 面板左列按来源出行，大类标题取交出者给的那一份
    - 同一来源段内重键只留先出现的一项，跨来源同名段各留各的
    """

    def test_missing_file_gets_defaults_per_source(self) -> None:
        """缺文件时装配写出的段与说明都来自交出模板"""
        path = _temp_file()
        with patch("utils.config.CONFIG_FILE", path), fake_adapter_parts():
            ensure_config(config_sources())

        data = ConfigIO(path).load()
        self.assertEqual(
            list(data),
            ["adapter.tg.proxy", "plugin.AI.model", "plugin.AI.chore", "core.data"],
        )
        self.assertEqual(data["core.data"]["record_keep"], 30.0)
        self.assertEqual(data["adapter.tg.proxy"]["proxy_mode"], "auto")
        text = path.read_text(encoding="utf-8")
        self.assertIn("[source.chore.notes]", text)

    def test_left_column_takes_source_identity_and_title(self) -> None:
        """面板左列按来源出行，标题取交出者给的那一份"""
        with fake_adapter_parts("Telegram"):
            schema = build_schema(assemble(config_sources()).sections)

        self.assertEqual(
            [(tab.group, tab.group_title) for tab in schema],
            [
                ("adapter.tg", "Telegram"),
                ("plugin.AI", "AI 设置"),
                ("plugin.AI", "AI 设置"),
                ("core", "Bot 设置"),
            ],
        )

    def test_same_identity_rejects_the_later_source(self) -> None:
        """同一身份码被两份认领时后交的那份整份不进，并点名一句"""
        first = ConfigSource(SourceKind.PLUGIN, "AI", "先交的来源", _AI)
        later = ConfigSource(SourceKind.PLUGIN, "AI", "后交的来源", _TG)
        path = _temp_file()
        with (
            patch("utils.config.CONFIG_FILE", path),
            self.assertLogs("Bot.Config", level="INFO") as logs,
        ):
            ensure_config((first, later))

        self.assertEqual(
            list(ConfigIO(path).load()), ["plugin.AI.model", "plugin.AI.chore"]
        )
        named = [line for line in logs.output if "被两份认领" in line]
        self.assertEqual(len(named), 1, logs.output)
        self.assertIn("proxy", named[0])

    def test_duplicate_key_in_one_section_is_refused_and_named(self) -> None:
        """同一来源同一段里键重复时只留先出现的一项，日志点名来源、段与键"""
        section = SectionSpec(
            section=ConfigSection.AI,
            title="模型",
            fields=(
                FieldSpec(
                    section=ConfigSection.AI,
                    key=ConfigKey.API_KEY,
                    value_type=str,
                    default="sk-先",
                    label="API Key",
                    desc="",
                ),
                FieldSpec(
                    section=ConfigSection.AI,
                    key=ConfigKey.API_KEY,
                    value_type=str,
                    default="sk-后",
                    label="API Key",
                    desc="",
                ),
            ),
        )
        source = ConfigSource(SourceKind.PLUGIN, "AI", "AI 设置", (section,))

        with self.assertLogs("Bot.Config", level="ERROR") as logs:
            plan = assemble((source,))

        self.assertEqual(len(plan.sections[0].spec.fields), 1)
        self.assertEqual(plan.defaults()["plugin.AI.model"], {"api_key": "sk-先"})
        named = [line for line in logs.output if "重复" in line]
        self.assertEqual(len(named), 1, logs.output)
        for part in ("plugin.AI", "model", "api_key"):
            self.assertIn(part, named[0])

    def test_same_section_name_from_two_sources_both_kept(self) -> None:
        """两家来源各带同名段时两段都在、互不覆盖"""
        plugin_proxy = SectionSpec(
            section=ConfigSection.PROXY,
            title="代理",
            fields=(
                FieldSpec(
                    section=ConfigSection.PROXY,
                    key=ConfigKey.PROXY,
                    value_type=str,
                    default="http://2.2.2.2:1080",
                    label="代理",
                    desc="",
                ),
            ),
        )
        telegram = ConfigSource(SourceKind.ADAPTER, "tg", "Telegram", _TG)
        plugin = ConfigSource(SourceKind.PLUGIN, "AI", "AI 设置", (plugin_proxy,))
        path = _temp_file()
        with patch("utils.config.CONFIG_FILE", path):
            ensure_config((telegram, plugin))

        data = ConfigIO(path).load()
        self.assertEqual(set(data), {"adapter.tg.proxy", "plugin.AI.proxy"})
        self.assertEqual(data["adapter.tg.proxy"]["proxy_mode"], "auto")
        self.assertEqual(data["adapter.tg.proxy"]["proxy"], "")
        self.assertEqual(data["plugin.AI.proxy"], {"proxy": "http://2.2.2.2:1080"})

    def test_plugin_that_fails_to_load_is_skipped(self) -> None:
        """装载不成的插件那一只不进配置，日志点名它"""
        path = _temp_file()
        with (
            patch("utils.config.CONFIG_FILE", path),
            fake_adapter_parts(),
            patch(
                "bot._managers._config_sources.load_plugin", side_effect=RuntimeError
            ),
            self.assertLogs("Bot.Config", level="ERROR") as logs,
        ):
            ensure_config(config_sources())

        self.assertEqual(list(ConfigIO(path).load()), ["adapter.tg.proxy", "core.data"])
        self.assertTrue(any("AI" in line for line in logs.output))


class TestExistingFileUntouched(unittest.TestCase):
    """回归点

    - 配置文件已存在时启动不动盘，模板多出来的键不补进文件
    """

    def test_existing_file_is_not_rewritten(self) -> None:
        """已填过的值照留，模板里的其它键不进文件"""
        path = _temp_file()
        ConfigIO(path).save({"plugin.AI.model": {"api_key": "sk-已填"}}, notes={})
        before = path.read_bytes()

        with patch("utils.config.CONFIG_FILE", path), fake_adapter_parts():
            ensure_config(config_sources())

        self.assertEqual(path.read_bytes(), before)
        data = ConfigIO(path).load()
        self.assertEqual(data, {"plugin.AI.model": {"api_key": "sk-已填"}})


if __name__ == "__main__":
    unittest.main(verbosity=2)
