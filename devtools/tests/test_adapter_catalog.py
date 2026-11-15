"""在线目录读取的单元测试

- 字段逐行验形态，坏行整条不进表并点名哪只发行件坏在哪一步
- 平台码只认目录里写的那一值，分发名与仓名都不参与判定
- 下载直链按独立整串收下，换 host 与换分发名互不影响
- 整份读不出与接口包段缺失各出一条说明，不牵动其余行
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from finshin_sdk.domain import Platform  # noqa: E402
from services import adapter_catalog as catalog_mod  # noqa: E402
from skin.messages import CatalogMessage  # noqa: E402

# 夹具一律合成值，线上发新版不许把用例改红
_SDK_URL = "https://example.invalid/FinshinSDK/finshin_sdk-9.9.9-py3-none-any.whl"
_TG_URL = (
    "https://example.invalid/FinshinAdapterTG/finshin_adapter_tg-9.9.9-py3-none-any.whl"
)
_SHA_SDK = "0" * 64
_SHA_TG = "1" * 64

_ORDER = ("platform", "distribution", "version", "url", "sha256")

_SDK_FIELDS = {
    "distribution": "finshin-sdk",
    "version": "9.9.9",
    "url": _SDK_URL,
    "sha256": _SHA_SDK,
}
_TG_FIELDS = {
    "platform": str(Platform.TELEGRAM),
    "distribution": "finshin-adapter-tg",
    "version": "9.9.9",
    "url": _TG_URL,
    "sha256": _SHA_TG,
}


def _section(name: str, **fields: str) -> str:
    """按固定键序拼一段目录文本"""
    header = f"[[{name}]]" if name == catalog_mod._SECTION_ADAPTER else f"[{name}]"
    rows = [f'{key} = "{fields[key]}"' for key in _ORDER if key in fields]

    return "\n".join([header] + rows)


def _sdk_text(**overrides: str) -> str:
    """只含接口包一段的目录文本"""
    return _section(catalog_mod._SECTION_SDK, **dict(_SDK_FIELDS, **overrides)) + "\n"


def _adapter_text(*rows: dict[str, str]) -> str:
    """只含适配器条目的目录文本"""
    return "".join(_section(catalog_mod._SECTION_ADAPTER, **row) + "\n" for row in rows)


def _full_text() -> str:
    """接口包与一只适配器都齐的目录文本"""
    return _sdk_text() + _adapter_text(_TG_FIELDS)


class TestCatalogParse(unittest.IsolatedAsyncioTestCase):
    """在线目录文本解析"""

    async def _read(
        self, text: str, proxy: str | None = None
    ) -> tuple[catalog_mod.Catalog, AsyncMock]:
        """喂文本走一遍读取，交出目录与取件替身"""
        fetch = AsyncMock(return_value=text)
        with patch.object(catalog_mod.GitClient, "get_pages", fetch):
            catalog = await catalog_mod.load_catalog(proxy)

        return catalog, fetch

    async def test_full_catalog(self) -> None:
        """字段齐的两段逐样收下且无拒收说明"""
        catalog, _ = await self._read(_full_text())
        if catalog.sdk is None or not catalog.adapters:
            self.fail(f"完整目录被拒收：{catalog.rejects}")

        self.assertEqual(catalog.rejects, ())
        self.assertEqual(catalog.sdk.distribution, "finshin-sdk")
        self.assertEqual(catalog.sdk.sha256, _SHA_SDK)
        self.assertEqual(catalog.adapters[Platform.TELEGRAM].url, _TG_URL)

    async def test_proxy_passed_to_fetch(self) -> None:
        """交出代理地址即原样递给取件那一步"""
        catalog, fetch = await self._read(_full_text(), "http://127.0.0.1:7897")
        self.assertEqual(fetch.call_args.args[2], "http://127.0.0.1:7897")
        if catalog.sdk is None:
            self.fail(f"带代理的目录没读出来：{catalog.rejects}")

    async def test_url_independent_of_distribution(self) -> None:
        """直链换 host 照收，不由分发名拼出"""
        swapped = "https://mirror.example.com/elsewhere/sdk-9.9.9-py3-none-any.whl"
        catalog, _ = await self._read(
            _sdk_text(url=swapped) + _adapter_text(_TG_FIELDS)
        )
        if catalog.sdk is None:
            self.fail(f"换过地址的行被拒收：{catalog.rejects}")

        self.assertEqual(catalog.sdk.url, swapped)
        self.assertEqual(catalog.sdk.distribution, "finshin-sdk")
        self.assertEqual(catalog.rejects, ())

    async def test_bad_sha_rejects_row(self) -> None:
        """指纹长度不对的行整条不进表并点名"""
        catalog, _ = await self._read(_sdk_text(sha256="abc123"))
        self.assertIsNone(catalog.sdk)
        self.assertEqual(len(catalog.rejects), 1)
        self.assertIn("finshin-sdk", catalog.rejects[0])
        self.assertIn("64", catalog.rejects[0])

    async def test_sha_uppercase_normalized(self) -> None:
        """大写指纹收下并归成小写"""
        catalog, _ = await self._read(_sdk_text(sha256=_SHA_SDK.upper()))
        if catalog.sdk is None:
            self.fail(f"大写指纹被拒收：{catalog.rejects}")

        self.assertEqual(catalog.sdk.sha256, _SHA_SDK)

    async def test_sha_not_hex_rejected(self) -> None:
        """非十六进制字符的指纹拒收"""
        catalog, _ = await self._read(_sdk_text(sha256="z" * 64))
        self.assertIsNone(catalog.sdk)
        self.assertEqual(len(catalog.rejects), 1)

    async def test_plain_http_url_rejected(self) -> None:
        """非 https 的直链拒收"""
        plain = _SDK_URL.replace("https://", "http://", 1)
        catalog, _ = await self._read(_sdk_text(url=plain))
        self.assertIsNone(catalog.sdk)
        self.assertIn("https", catalog.rejects[0])

    async def test_missing_field_rejected(self) -> None:
        """必填键空值的行拒收并点名缺哪一键"""
        catalog, _ = await self._read(_sdk_text(version=""))
        self.assertIsNone(catalog.sdk)
        self.assertIn("version", catalog.rejects[0])

    async def test_broken_text_rejects_all(self) -> None:
        """整份文本不是 TOML 时只出一条说明"""
        catalog, _ = await self._read("this is not a toml")
        self.assertIsNone(catalog.sdk)
        self.assertEqual(catalog.adapters, {})
        self.assertEqual(catalog.rejects, (CatalogMessage.BROKEN,))

    async def test_missing_sdk_section(self) -> None:
        """没有接口包那一段时报一句，适配器行照收"""
        catalog, _ = await self._read(_adapter_text(_TG_FIELDS))
        self.assertIsNone(catalog.sdk)
        self.assertEqual(len(catalog.adapters), 1)
        self.assertEqual(catalog.rejects, (CatalogMessage.SDK_MISSING,))


class TestPlatformJudge(unittest.IsolatedAsyncioTestCase):
    """平台码判定"""

    async def _read(self, *rows: dict[str, str]) -> catalog_mod.Catalog:
        """接口包段照旧在场，只覆写适配器条目"""
        text = _sdk_text() + _adapter_text(*rows)
        fetch = AsyncMock(return_value=text)
        with patch.object(catalog_mod.GitClient, "get_pages", fetch):
            return await catalog_mod.load_catalog()

    async def test_unknown_platform_rejected(self) -> None:
        """词表外的平台码整行不进表并报出那一值"""
        catalog = await self._read(dict(_TG_FIELDS, platform="wx"))
        self.assertEqual(catalog.adapters, {})
        self.assertEqual(len(catalog.rejects), 1)
        self.assertIn("wx", catalog.rejects[0])

    async def test_distribution_name_not_a_judge(self) -> None:
        """分发名换掉不影响平台码认下来的那只"""
        catalog = await self._read(
            dict(_TG_FIELDS, distribution="finshin-adapter-telegram")
        )
        self.assertEqual(list(catalog.adapters), [Platform.TELEGRAM])
        self.assertEqual(catalog.rejects, ())

    async def test_duplicated_platform_keeps_first(self) -> None:
        """同一平台码出现两行时只认先读到的那条"""
        later = dict(_TG_FIELDS, version="8.8.8", sha256=_SHA_SDK)
        catalog = await self._read(_TG_FIELDS, later)
        if catalog.adapters.get(Platform.TELEGRAM) is None:
            self.fail(f"先读到的那行没进表：{catalog.rejects}")

        self.assertEqual(catalog.adapters[Platform.TELEGRAM].version, "9.9.9")
        self.assertEqual(len(catalog.rejects), 1)
        self.assertIn(str(Platform.TELEGRAM), catalog.rejects[0])


if __name__ == "__main__":
    unittest.main()
