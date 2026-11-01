# devtools/tests/test_connectivity_check.py
"""连接性检查重构的单元测试

- _map_construct_error 把构造期 ValueError 与 UnicodeError 映射为精确异常
- scheme 为空时不得丢失提示
- _check_config 聚合 proxy 与 token 双探测，两坏同时报
- token 纯格式校验，坏 token 不联网即标记
- verify_connectivity 覆盖三步通道解析与错误聚合
- 网络轮只在参数变化或上轮连通未通过时起，其余只跑本地
- 首轮全挂每种模式都预热后重检一轮，单路模式同样重检本路
"""

import asyncio
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from adapters.telegram import probe as probe_mod  # noqa: E402
from core.domain import FieldKey  # noqa: E402
from exceptions import ProxyAddressError, ProxySchemeError, TokenError  # noqa: E402

_check_config = probe_mod._check_config
_map_construct_error = probe_mod._map_construct_error


class TestRealProbeNoHang(unittest.TestCase):
    """回归点

    - 真实 _probe_proxy 遇非法端口必须映射为业务异常，不上抛不挂死
    """

    def test_bad_port_maps_not_escapes(self) -> None:
        """非法端口的真实探测返回 proxy 键错误而非穿透"""
        from adapters.telegram.probe import _check_config

        async def ok_get_me(token: str, proxy: str) -> None:
            return None

        errors = asyncio.run(
            _check_config("123:abc", "http://127.0.0.1:99999", get_me=ok_get_me)
        )
        self.assertIn("proxy", errors, "非法端口应产出 proxy 错误文案")


class TestMapConstructError(unittest.TestCase):
    """回归点

    - 异常消息携带有误（scheme 提取为空）
    """

    def test_empty_scheme_keeps_hint(self) -> None:
        """空 scheme 必须回退占位文案"""
        # proxy="aaa" 时 yarl 消息为 'Invalid scheme component: '（冒号后为空）
        e = ValueError("Invalid scheme component: ")
        mapped = _map_construct_error(e, "aaa")
        self.assertIsInstance(mapped, ProxySchemeError)
        self.assertTrue(
            mapped.scheme.strip(),
            "scheme 为空时必须回退为占位提示，不得输出空白（当前代码此处失败）",
        )

    def test_named_scheme_extracted(self) -> None:
        """具名非法协议被提取到异常属性"""
        e = ValueError("Invalid scheme component: ftp")
        mapped = _map_construct_error(e, "ftp://127.0.0.1:7890")
        self.assertIsInstance(mapped, ProxySchemeError)
        self.assertEqual(mapped.scheme, "ftp")

    def test_port_error_maps_to_address(self) -> None:
        """端口非法映射为地址错误"""
        mapped = _map_construct_error(
            ValueError("Invalid port component"), "http://127.0.0.1:99999"
        )
        self.assertIsInstance(mapped, ProxyAddressError)


class TestCheckConfig(unittest.IsolatedAsyncioTestCase):
    """回归点

    - 双探测聚合，token 与 proxy 问题同时上报
    """

    async def _ok_probe(self, proxy: str) -> None:
        return None

    async def _ok_get_me(self, token: str, proxy: str) -> None:
        return None

    async def test_all_good_returns_empty(self) -> None:
        """全通过返回空 dict"""
        errors = await _check_config(
            "123:abc",
            "http://127.0.0.1:7897",
            probe=self._ok_probe,
            get_me=self._ok_get_me,
        )
        self.assertEqual(errors, {})

    async def test_bad_token_marked(self) -> None:
        """远端拒绝时标记 token 字段"""

        async def bad_me(token: str, proxy: str) -> None:
            raise TokenError()

        errors = await _check_config(
            "123:abc",
            "http://127.0.0.1:7897",
            probe=self._ok_probe,
            get_me=bad_me,
        )
        self.assertIn(FieldKey.TOKEN, errors)

    async def test_bad_proxy_marks_both_with_skip_note(self) -> None:
        """代理坏时同时标记两字段且跳过 getMe"""

        async def dead_probe(proxy: str) -> None:
            raise ProxySchemeError(scheme="空", proxy=proxy)

        get_me_called = {"n": 0}

        async def counting_me(token: str, proxy: str) -> None:
            get_me_called["n"] += 1

        errors = await _check_config(
            "123:abc", "aaa", probe=dead_probe, get_me=counting_me
        )
        self.assertIn(FieldKey.PROXY, errors)
        self.assertIn(FieldKey.TOKEN, errors, "proxy 坏时 token 必须被标记为跳过")
        self.assertEqual(get_me_called["n"], 0, "proxy 已坏不得再浪费一次 getMe")

    async def test_format_invalid_token_no_network(self) -> None:
        """格式非法 token 本地判定不联网"""
        # token 格式非法（无冒号）：probe 正常也不得调用 get_me，直接本地标记
        get_me_called = {"n": 0}

        async def counting_me(token: str, proxy: str) -> None:
            get_me_called["n"] += 1

        errors = await _check_config(
            "aaa",
            "http://127.0.0.1:7897",
            probe=self._ok_probe,
            get_me=counting_me,
        )
        self.assertIn(FieldKey.TOKEN, errors)
        self.assertEqual(get_me_called["n"], 0, "格式非法的 token 应本地判定，不联网")


class TestVerifyConnectivityAggregation(unittest.IsolatedAsyncioTestCase):
    """回归点

    - 三步通道解析（配置→系统→直连）与错误聚合
    """

    @contextmanager
    def _patches(self, mod, fake_check, types=None):
        """统一打桩

        - 探针、本地校验、系统代理缺席、重检预热归零
        - fake_check 返回错误 dict，适配成 attempt_channel 的 (生效址, 错误) 元组
        """

        local = ({"id": "local", "status": "ok", "detail": ""}, types or {})

        async def fake_probe(
            token: str, proxy: str
        ) -> tuple[str | None, dict[str, str]]:
            errors = await fake_check(token, proxy)
            return (proxy, {}) if not errors else (None, errors)

        with (
            patch.object(mod, "attempt_channel", fake_probe),
            patch.object(mod, "local_row", return_value=local),
            patch.object(mod, "detect_system_proxy", return_value=None),
            patch.object(mod, "_RETRY_WARMUP", 0.0),
        ):
            yield

    async def test_all_channels_fail_aggregates(self) -> None:
        """三步全不通

        - 聚合为一句跨路汇总，token 占位被取代
        - 尾句指向代理软件自查
        """

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))

        async def dead(token: str, proxy: str) -> dict:
            return {
                "proxy": "无法连接到代理服务器",
                "telegram_token": "暂未检测：代理修复后复查",
            }

        mod = sys.modules["bot._managers._settings"]
        with self._patches(mod, dead):
            ok = await mgr.verify_connectivity()

        self.assertFalse(ok)
        self.assertIsNone(mgr.resolved_proxy)
        self.assertEqual(list(mgr.last_errors), ["proxy"])
        self.assertIn("均无法连通", mgr.last_errors["proxy"])
        self.assertIn("代理软件", mgr.last_errors["proxy"])

    async def test_fallback_direct_when_config_dead(self) -> None:
        """配置代理死、直连通

        - 生效通道=直连，net 残留清零
        """

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))

        async def only_direct(token: str, proxy: str) -> dict:
            return {} if not proxy else {"proxy": "无法连接到代理服务器"}

        mod = sys.modules["bot._managers._settings"]
        with self._patches(mod, only_direct):
            ok = await mgr.verify_connectivity()

        self.assertTrue(ok)
        self.assertEqual(mgr.resolved_proxy, "")
        self.assertEqual(mgr.last_errors, {})

    async def test_token_error_stops_channel_switch(self) -> None:
        """通道已通仅 token 无效

        - 不换道不聚合，原样上报
        """

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "prox"))

        async def token_bad(token: str, proxy: str) -> dict:
            return {"telegram_token": "Token 无效"}

        mod = sys.modules["bot._managers._settings"]
        with self._patches(mod, token_bad):
            ok = await mgr.verify_connectivity()

        self.assertFalse(ok)
        self.assertIsNone(mgr.resolved_proxy)
        self.assertEqual(mgr.last_errors, {"telegram_token": "Token 无效"})

    async def test_single_candidate_keeps_original_error(self) -> None:
        """仅直连单候选不通

        - 代理留空且无系统代理
        - 保留原始网络错误文案，不跨路聚合
        """

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", ""))

        async def dead_direct(token: str, proxy: str) -> dict:
            return {"proxy": "直连超时，请开启系统代理或在代理项填写地址"}

        mod = sys.modules["bot._managers._settings"]
        with self._patches(mod, dead_direct):
            ok = await mgr.verify_connectivity()

        self.assertFalse(ok)
        self.assertIsNone(mgr.resolved_proxy)
        self.assertIn("直连超时", mgr.last_errors["proxy"])
        self.assertNotIn("均无法连通", mgr.last_errors["proxy"])
        self.assertIn("代理软件", mgr.last_errors["proxy"])

    async def test_network_and_type_errors_merged(self) -> None:
        """连通性与类型错误合并上报

        - 网络项在前、类型项在后
        """
        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "prox"))

        async def net_fail(token: str, proxy: str) -> dict:
            return {"proxy": "代理协议不支持: https"}

        mod = sys.modules["bot._managers._settings"]
        with self._patches(
            mod,
            net_fail,
            types={"temperature": "类型应为 float"},
        ):
            ok = await mgr.verify_connectivity()

        self.assertFalse(ok)
        self.assertEqual(
            list(mgr.last_errors),
            ["proxy", "temperature"],
            "错误顺序应为网络在前、类型在后",
        )

    async def test_unchanged_params_run_local_only(self) -> None:
        """网络参数未变的二次校验只跑本地

        - 免测轮不联网，也不发整表帧
        """
        from unittest.mock import MagicMock

        from bot._managers._settings import SettingsManager
        from utils.network import FrameKey

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:7890"))
        probes: list[str] = []

        async def alive(token: str, proxy: str) -> dict:
            probes.append(proxy)
            return {}

        frames: list[dict] = []
        bridge = MagicMock()
        bridge.verify_progress.emit.side_effect = frames.append

        mod = sys.modules["bot._managers._settings"]
        with self._patches(mod, alive), patch.object(mod, "gui_bridge", bridge):
            self.assertTrue(await mgr.verify_connectivity())
            self.assertTrue(probes, "首轮应联网探测")
            probes.clear()
            frames.clear()
            self.assertTrue(await mgr.verify_connectivity())

        self.assertEqual(probes, [], "网络参数没变不该再联网")
        self.assertEqual(
            [f for f in frames if FrameKey.ROWS in f],
            [],
            "免测轮不发整表帧",
        )
        self.assertEqual(len(frames), 1, "免测轮只发结论帧")

    async def test_token_change_not_a_network_round(self) -> None:
        """只换 token 不再单点复查通道

        - token 不进变化判定，网络参数未变即免测
        """
        from bot._managers._settings import SettingsManager

        getter = {"token": "tok1"}
        mgr = SettingsManager(lambda: (getter["token"], "http://127.0.0.1:7890"))
        probes: list[str] = []

        async def alive(token: str, proxy: str) -> dict:
            probes.append(token)
            return {}

        mod = sys.modules["bot._managers._settings"]
        with self._patches(mod, alive):
            self.assertTrue(await mgr.verify_connectivity())
            getter["token"] = "tok2"
            probes.clear()
            self.assertTrue(await mgr.verify_connectivity())

        self.assertEqual(probes, [], "token 变动不该起联网轮")

    async def test_type_error_alone_keeps_local_only(self) -> None:
        """上轮只报本地类型错时保持免测

        - 网络参数没变且连通已过，类型错走免测轮复查
        """
        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", ""))
        probes: list[str] = []

        async def alive(token: str, proxy: str) -> dict:
            probes.append(proxy)
            return {}

        mod = sys.modules["bot._managers._settings"]
        with self._patches(mod, alive, types={"temperature": "类型应为 float"}):
            self.assertFalse(await mgr.verify_connectivity())
            self.assertTrue(probes, "首轮应联网探测")
            self.assertIsNotNone(mgr.resolved_proxy, "直连通了应记下生效通道")
            probes.clear()
            self.assertFalse(await mgr.verify_connectivity())

        self.assertEqual(probes, [], "只有类型错时不该重联网")

    async def test_proxy_error_forces_network_retest(self) -> None:
        """上轮代理不通作废免测

        - 生效通道没记下，网络参数没变也要重探
        """
        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))
        probes: list[str] = []
        reach = {"ok": False}

        async def dead_then_alive(token: str, proxy: str) -> dict:
            probes.append(proxy)
            return {} if reach["ok"] else {"proxy": "无法连接到代理服务器"}

        mod = sys.modules["bot._managers._settings"]
        with self._patches(mod, dead_then_alive):
            self.assertFalse(await mgr.verify_connectivity())
            self.assertIsNone(mgr.resolved_proxy, "全挂时不该记下生效通道")
            probes.clear()
            reach["ok"] = True
            self.assertTrue(await mgr.verify_connectivity())

        self.assertTrue(probes, "上轮不通不该免测")


class TestProxyModeFlow(unittest.IsolatedAsyncioTestCase):
    """回归点

    - 单路模式只探选定通道，失败不跨路聚合
    - 每种模式首轮全挂都等待预热后重检一轮
    - 重检轮开场重发整表，待测行刷回检测中并带头部重测提示
    - 代理行被隐藏的模式，网络错标在看得见的代理模式行上
    """

    @contextmanager
    def _mode_patches(self, mod, fake_check, mode, sys_proxy=None):
        """按模式打桩

        - 内存配置注入 proxy_mode，系统代理可控，重检预热归零
        """
        local_frame = {"id": "local", "status": "ok", "detail": ""}

        async def fake_probe(
            token: str, proxy: str
        ) -> tuple[str | None, dict[str, str]]:
            errors = await fake_check(token, proxy)
            return (proxy, {}) if not errors else (None, errors)

        with (
            patch.object(mod, "attempt_channel", fake_probe),
            patch.object(mod, "local_row", return_value=(local_frame, {})),
            patch.object(mod, "detect_system_proxy", return_value=sys_proxy),
            patch.object(mod, "_RETRY_WARMUP", 0.0),
            patch.object(
                mod.config_manager,
                "get_all",
                return_value={"proxy": {"proxy": "", "proxy_mode": mode}},
            ),
        ):
            yield

    async def test_single_cfg_probes_only_config(self) -> None:
        """仅配置代理模式不探直连"""

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))
        seen: list[str] = []

        async def probe(token: str, proxy: str) -> dict:
            seen.append(proxy)
            return {}

        mod = sys.modules["bot._managers._settings"]
        with self._mode_patches(mod, probe, "cfg"):
            ok = await mgr.verify_connectivity()

        self.assertTrue(ok)
        self.assertEqual(seen, ["http://127.0.0.1:9999"], "单路配置模式不得探测直连")
        self.assertEqual(mgr.resolved_proxy, "http://127.0.0.1:9999")

    async def test_single_cfg_fail_reports_own_error(self) -> None:
        """单路失败只回本路错，不跨路聚合"""

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))
        calls = {"n": 0}

        async def dead(token: str, proxy: str) -> dict:
            calls["n"] += 1
            return {"proxy": "无法连接到代理服务器"}

        mod = sys.modules["bot._managers._settings"]
        with self._mode_patches(mod, dead, "cfg"):
            ok = await mgr.verify_connectivity()

        self.assertFalse(ok)
        self.assertEqual(calls["n"], 2, "单路配置模式也重检一轮")
        self.assertIn("无法连接到代理服务器", mgr.last_errors["proxy"])
        self.assertNotIn("均无法连通", mgr.last_errors["proxy"])

    async def test_hidden_proxy_mode_takes_the_mark(self) -> None:
        """代理行隐藏的模式，网络错的标红落在代理模式行

        - 仅系统代理与仅直连两档用不到代理项，面板把那一行整行藏掉
        """

        from bot._managers._settings import SettingsManager

        for mode, sys_proxy in (("direct", None), ("sys", "http://127.0.0.1:7890")):
            with self.subTest(mode=mode):
                mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))

                async def dead(token: str, proxy: str) -> dict:
                    return {"proxy": "连不上"}

                mod = sys.modules["bot._managers._settings"]
                with self._mode_patches(mod, dead, mode, sys_proxy):
                    ok = await mgr.verify_connectivity()

                self.assertFalse(ok)
                self.assertEqual(
                    list(mgr.last_errors), ["proxy_mode"], "红点要落在看得见的行上"
                )
                self.assertIn("连不上", mgr.last_errors["proxy_mode"])

    async def test_single_direct_fail_retries(self) -> None:
        """仅直连模式首轮失败同样重检

        - TUN 内核冷启动可能只卡住首探
        """

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))
        calls = {"n": 0}

        async def cold_start(token: str, proxy: str) -> dict:
            calls["n"] += 1
            if calls["n"] == 1:
                return {"proxy": "直连超时，请开启系统代理或在代理项填写地址"}
            return {}

        mod = sys.modules["bot._managers._settings"]
        with self._mode_patches(mod, cold_start, "direct"):
            ok = await mgr.verify_connectivity()

        self.assertTrue(ok, "重检轮通过即算数")
        self.assertEqual(calls["n"], 2, "直连模式应重检一轮")
        self.assertEqual(mgr.resolved_proxy, "")

    async def test_direct_mode_probes_empty_proxy(self) -> None:
        """仅直连模式以空 proxy 探测且不误报降级"""

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))
        seen: list[str] = []

        async def probe(token: str, proxy: str) -> dict:
            seen.append(proxy)
            return {}

        mod = sys.modules["bot._managers._settings"]
        with self._mode_patches(mod, probe, "direct"):
            ok = await mgr.verify_connectivity()

        self.assertTrue(ok)
        self.assertEqual(seen, [""], "直连模式应只探空 proxy 一路")
        self.assertEqual(mgr.resolved_proxy, "")

    async def test_sys_mode_absent_no_probe(self) -> None:
        """选系统代理但注册表无地址，缺席不发探测"""

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", ""))
        calls = {"n": 0}

        async def probe(token: str, proxy: str) -> dict:
            calls["n"] += 1
            return {}

        mod = sys.modules["bot._managers._settings"]
        with self._mode_patches(mod, probe, "sys", sys_proxy=None):
            ok = await mgr.verify_connectivity()

        self.assertFalse(ok)
        self.assertEqual(calls["n"], 0, "缺席单路不应发探测")
        self.assertIn("系统代理未开启", mgr.last_errors["proxy_mode"])

    async def test_auto_fail_then_retry_passes(self) -> None:
        """自动模式首轮全挂，重检轮通过即算数"""

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))
        cfg_calls = {"n": 0}

        async def flaky(token: str, proxy: str) -> dict:
            if not proxy:
                return {"proxy": "直连超时"}
            cfg_calls["n"] += 1
            return {"proxy": "验证超时"} if cfg_calls["n"] <= 1 else {}

        mod = sys.modules["bot._managers._settings"]
        with self._mode_patches(mod, flaky, "auto"):
            ok = await mgr.verify_connectivity()

        self.assertTrue(ok, "重检轮应通过")
        self.assertEqual(cfg_calls["n"], 2, "配置通道恰在两轮的第二次通过")

    async def test_auto_retry_both_fail(self) -> None:
        """自动模式两轮皆败才定性失败"""

        from bot._managers._settings import SettingsManager

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))
        calls = {"n": 0}

        async def dead(token: str, proxy: str) -> dict:
            calls["n"] += 1
            return {"proxy": "无法连接到代理服务器"}

        mod = sys.modules["bot._managers._settings"]
        with self._mode_patches(mod, dead, "auto"):
            ok = await mgr.verify_connectivity()

        self.assertFalse(ok)
        self.assertEqual(calls["n"], 4, "两轮各两通道")
        self.assertIn("均无法连通", mgr.last_errors["proxy"])

    async def test_auto_retry_reopens_table_with_hint(self) -> None:
        """重检轮重发整表刷掉首轮红行，头部带重测提示"""
        from unittest.mock import MagicMock

        from bot._managers._settings import SettingsManager
        from skin.messages import CheckMessage
        from utils.network import FrameKey, RowStatus

        mgr = SettingsManager(lambda: ("tok", "http://127.0.0.1:9999"))
        cfg_calls = {"n": 0}

        async def flaky(token: str, proxy: str) -> dict:
            if not proxy:
                return {"proxy": "直连超时"}
            cfg_calls["n"] += 1
            return {"proxy": "验证超时"} if cfg_calls["n"] <= 1 else {}

        frames: list[dict] = []
        bridge = MagicMock()
        bridge.verify_progress.emit.side_effect = frames.append

        mod = sys.modules["bot._managers._settings"]
        with (
            self._mode_patches(mod, flaky, "auto"),
            patch.object(mod, "gui_bridge", bridge),
        ):
            ok = await mgr.verify_connectivity()

        self.assertTrue(ok, "重检轮应通过")
        resets = [f for f in frames if FrameKey.ROWS in f]
        self.assertEqual(len(resets), 2, "重检轮应重发一次整表")
        retry = resets[1]
        self.assertEqual(retry.get(FrameKey.HEAD), CheckMessage.RETRY_HEAD)
        probed = [r for r in retry[FrameKey.ROWS] if r["id"] in ("cfg", "direct")]
        self.assertEqual(
            [r["status"] for r in probed],
            [RowStatus.CHECKING, RowStatus.CHECKING],
            "重检整表的待测通道行应全部刷回检测中",
        )
        self.assertTrue(all("budget" in r for r in probed), "重检行应重新装上计时预算")


class TestSingleRowPlan(unittest.TestCase):
    """回归点

    - 单路模式校验表裁剪为本路、本地与结论三行
    """

    def test_cfg_single_rows(self) -> None:
        """单路配置表只剩三行"""
        from utils.network import plan_channels, verify_plan
        from utils.network.probe import single_row_of

        channels = plan_channels("http://127.0.0.1:9999", None, mode="cfg")
        rows = verify_plan(channels, single=single_row_of("cfg"))
        self.assertEqual([r["id"] for r in rows], ["cfg", "local", "advice"])

    def test_auto_single_none(self) -> None:
        """自动模式不裁行"""
        from utils.network.probe import single_row_of

        self.assertIsNone(single_row_of("auto"))


class TestEnumFieldValidation(unittest.TestCase):
    """回归点

    - 枚举字段非法值检出，合法值放行
    """

    def test_bad_mode_flagged(self) -> None:
        """模式值不在选项表即报错"""
        from dataclasses import replace

        from core.domain import Platform
        from utils.config._schema import build_schema
        from utils.config._validator import validate_types

        proxy_tab = build_schema(Platform.TELEGRAM)[0]
        mode_field = next(f for f in proxy_tab.fields if f.key == "proxy_mode")
        schema = [replace(proxy_tab, fields=[mode_field])]
        self.assertIn(
            "proxy_mode", validate_types(schema, {"proxy": {"proxy_mode": "tun"}})
        )
        self.assertEqual(validate_types(schema, {"proxy": {"proxy_mode": "sys"}}), {})


class TestStaleFrameDrain(unittest.TestCase):
    """回归点

    - 无窗轮次缓存的行帧在结论帧到达时作废
    - 过期行帧不得补播进下一轮窗口刷出假红
    """

    def test_drain_on_conclusion(self) -> None:
        """结论帧清缓存"""
        from unittest.mock import MagicMock

        from ui._windows._controllers._verify import VerifyCoordinator
        from utils.network import RowId, RowStatus

        mod = sys.modules["ui._windows._controllers._verify"]
        coord = VerifyCoordinator(MagicMock())
        with patch.object(mod, "current_check_window", return_value=None):
            coord.on_frame({"id": RowId.CFG, "status": RowStatus.CHECKING})
            self.assertEqual(len(coord.pre_frames), 1, "无窗轮次应先缓存行帧")
            coord.on_frame({"id": RowId.ADVICE, "status": RowStatus.FAIL})
            self.assertEqual(coord.pre_frames, [], "结论帧应作废旧行帧")


class TestRoundWindowOpens(unittest.TestCase):
    """回归点

    - 起轮只挂中断标记，首个进度帧才开等待窗
    - 免测轮不发进度帧，窗口一次不开
    - 上轮收尾留下的常驻死窗不吃帧，新一轮照旧开窗补播
    """

    def _parts(self, stale: object = None) -> tuple[object, object, dict]:
        """造协调器与假窗

        - stale 非空即模拟上轮收尾后常驻的死窗
        """
        from unittest.mock import MagicMock

        from ui._windows._controllers._verify import VerifyCoordinator

        win = MagicMock()
        mod = sys.modules["ui._windows._controllers._verify"]
        opener = {"n": 0}

        def fake_open(_parent: object) -> MagicMock:
            opener["n"] += 1
            return win

        patch.object(mod, "current_check_window", return_value=stale).start()
        patch.object(mod, "open_check_window", fake_open).start()
        self.addCleanup(patch.stopall)
        return VerifyCoordinator(MagicMock()), win, opener

    def test_first_frame_opens_window(self) -> None:
        """整表帧到达才开窗"""
        from utils.network import FrameKey, RowId

        coord, win, opener = self._parts()

        self.assertTrue(coord.start_round(aborts=True))
        self.assertEqual(opener["n"], 0, "起轮不该立刻开窗")

        coord.on_frame({FrameKey.ROWS: [{"id": RowId.CFG}]})
        self.assertEqual(opener["n"], 1, "首个进度帧应拉起等待窗")
        win.begin_round.assert_called_once()

    def test_local_round_never_opens(self) -> None:
        """免测轮只有结论帧，不开窗"""
        from utils.network import RowId, RowStatus

        coord, _, opener = self._parts()

        self.assertTrue(coord.start_round(aborts=True))
        coord.on_frame({"id": RowId.ADVICE, "status": RowStatus.OK})

        self.assertEqual(opener["n"], 0, "免测轮不该开等待窗")
        self.assertEqual(coord.pre_frames, [], "结论帧应清空中转缓存")

    def test_stale_window_reopens(self) -> None:
        """上轮收尾的死窗改走重开，进度帧不落空"""
        from unittest.mock import MagicMock

        from ui._dialogs import Round
        from utils.network import FrameKey, RowId

        stale = MagicMock()
        stale.round = Round.VERIFY
        stale.is_running = False
        coord, win, opener = self._parts(stale=stale)

        self.assertTrue(coord.start_round(aborts=True))
        coord.on_frame({FrameKey.ROWS: [{"id": RowId.CFG}]})

        self.assertEqual(opener["n"], 1, "死窗不该顶掉新一轮的等待窗")
        win.begin_round.assert_called_once()
        stale.apply.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
