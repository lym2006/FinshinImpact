"""在线目录生成器的单元测试

- 归属判定只看默认分支声明里的分发名，仓名不参与
- 最新一版的平台码、版本与直链取自该版声明与 release 附件自报的值
- 旧版本的版本号取 wheel 文件名，缺件的只丢那一版
- 陌生仓与没发版的仓跳过，发过版却缺件的当场报错
- 目录文本的段名与键位与本体读侧同值
"""

import base64
import os
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "packaging"))

import gen_catalog  # noqa: E402
import gen_release  # noqa: E402

_SDK_REPO = "FinshinLabs/FinshinSDK"
_TG_REPO = "FinshinLabs/FinshinAdapterTG"
_OTHER_REPO = "FinshinLabs/hello-world"
_XX_REPO = "FinshinLabs/FinshinAdapterXX"
_SHA = "1" * 64
_SDK_URL = f"https://example.invalid/{_SDK_REPO}/releases/download/v9.9.9/finshin_sdk-9.9.9-py3-none-any.whl"
_TG_URL = f"https://example.invalid/{_TG_REPO}/releases/download/v9.9.9/finshin_adapter_tg-9.9.9-py3-none-any.whl"


def _decl(distribution: str, platform: str = "") -> dict[str, Any]:
    """把一份声明编成 contents 接口回的结构"""
    lines = [
        "[project]",
        f'name = "{distribution}"',
        'version = "9.9.9"',
    ]
    if platform:
        lines += ["", "[tool.finshin-adapter]", f'platform = "{platform}"']
    blob = base64.b64encode("\n".join(lines).encode("utf-8")).decode("ascii")

    return {"content": blob}


def _asset(distribution: str, version: str, url: str, digest: str) -> dict[str, Any]:
    """拼一份 wheel 附件"""
    stem = distribution.replace("-", "_")

    return {
        "name": f"{stem}-{version}-py3-none-any.whl",
        "browser_download_url": url,
        "digest": digest,
    }


def _release(
    distribution: str, url: str, digest: str = f"sha256:{_SHA}"
) -> dict[str, Any]:
    """把一份最新 release 的附件表回结构"""
    return {
        "tag_name": "v9.9.9",
        "assets": [_asset(distribution, "9.9.9", url, digest)],
    }


def _older(
    distribution: str, version: str, digest: str = f"sha256:{_SHA}"
) -> dict[str, Any]:
    """一版旧 release，版本号只写在 wheel 文件名里"""
    stem = distribution.replace("-", "_")
    name = f"{stem}-{version}-py3-none-any.whl"

    return {
        "tag_name": f"v{version}",
        "assets": [
            _asset(
                distribution,
                version,
                f"https://example.invalid/releases/download/v{version}/{name}",
                digest,
            )
        ],
    }


def _repo(full_name: str) -> dict[str, Any]:
    """拼一行仓清单"""
    return {"full_name": full_name, "default_branch": "main", "archived": False}


class CatalogStub:
    """按 URL 分发假响应的取件替身"""

    def __init__(self, repos: list[dict[str, Any]], table: dict[str, Any]) -> None:
        """装入仓清单与按 URL 取用的假响应"""
        self.repos = repos
        self.table = table
        self.asked: list[str] = []

    def __call__(self, url: str) -> Any:
        self.asked.append(url)
        for needle, answer in self.table.items():
            if needle in url:
                return answer
        if "users/FinshinLabs/repos" in url:
            return self.repos
        return None


class TestGenCatalog(unittest.TestCase):
    """生成器聚合、版本清单与报错"""

    def setUp(self) -> None:
        """把账号名固定成测试用值"""
        self._owner = os.environ.get("GITHUB_REPOSITORY")
        os.environ["GITHUB_REPOSITORY"] = "FinshinLabs/FinshinImpact"
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        """还原账号环境变量"""
        if self._owner is None:
            os.environ.pop("GITHUB_REPOSITORY", None)
        else:
            os.environ["GITHUB_REPOSITORY"] = self._owner

    def _build(self, table: dict[str, Any], repos: list[dict[str, Any]]) -> str:
        """喂假响应生成一份目录文本"""
        with patch.object(gen_release, "_get", CatalogStub(repos, table)):
            return gen_catalog._build()

    def _both(self, tg_list: Any = None) -> dict[str, Any]:
        """接口包与 tg 各一份假响应表，tg 的 release 列表可另给"""
        tg_release = _release("finshin-adapter-tg", _TG_URL)

        return {
            f"{_SDK_REPO}/contents": _decl("finshin-sdk"),
            f"{_TG_REPO}/contents": _decl("finshin-adapter-tg", "tg"),
            f"{_SDK_REPO}/releases/latest": _release("finshin-sdk", _SDK_URL),
            f"{_SDK_REPO}/releases?": [_release("finshin-sdk", _SDK_URL)],
            f"{_TG_REPO}/releases/latest": tg_release,
            f"{_TG_REPO}/releases?": tg_list if tg_list is not None else [tg_release],
        }

    def _two(self) -> list[dict[str, Any]]:
        """生成目录用的两只仓"""
        return [_repo(_SDK_REPO), _repo(_TG_REPO)]

    def test_two_releases_agree_with_reader(self) -> None:
        """接口包与适配器各成一段，段名键位与本体读侧同值"""
        text = self._build(self._both(), self._two())

        self.assertIn("[sdk]", text)
        self.assertIn("[[adapter]]", text)
        self.assertIn(f'url = "{_TG_URL}"', text)
        self.assertIn(f'sha256 = "{_SHA}"', text)
        self.assertIn('platform = "tg"', text)
        self.assertIn('version = "9.9.9"', text)

    def test_version_list_keeps_latest_first(self) -> None:
        """一只发行件的行内带版本清单，最新那一版在最前"""
        listed = [
            _release("finshin-adapter-tg", _TG_URL),
            _older("finshin-adapter-tg", "8.8.8"),
        ]
        text = self._build(self._both(listed), self._two())

        self.assertEqual(text.count("[[adapter.versions]]"), 2)
        self.assertLess(text.index("9.9.9"), text.index("8.8.8"))

    def test_older_digest_absent_is_dropped(self) -> None:
        """旧版没报指纹即只丢那一版，最新那一版照进目录"""
        listed = [
            _release("finshin-adapter-tg", _TG_URL),
            _older("finshin-adapter-tg", "8.8.8", digest=""),
        ]
        text = self._build(self._both(listed), self._two())

        self.assertEqual(text.count("[[adapter.versions]]"), 1)
        self.assertNotIn("8.8.8", text)

    def test_latest_without_digest_raises(self) -> None:
        """最新那一版没报指纹即报错，不出半截目录"""
        table = self._both()
        table[f"{_TG_REPO}/releases/latest"] = _release(
            "finshin-adapter-tg", _TG_URL, digest=""
        )
        with self.assertRaises(RuntimeError):
            self._build(table, self._two())

    def test_version_list_is_capped(self) -> None:
        """一只发行件最多列十版，多发的不进取目录"""
        listed = [
            _release("finshin-adapter-tg", _TG_URL),
            *(_older("finshin-adapter-tg", f"0.{n}.0") for n in range(1, 15)),
        ]
        text = self._build(self._both(listed), self._two())

        self.assertEqual(text.count("[[adapter.versions]]"), 10)
        self.assertNotIn("0.14.0", text)

    def test_draft_and_prerelease_not_listed(self) -> None:
        """草稿与预发布的 release 不进版本清单"""
        listed = [
            _release("finshin-adapter-tg", _TG_URL),
            dict(_older("finshin-adapter-tg", "8.8.8"), draft=True),
            dict(_older("finshin-adapter-tg", "7.7.7"), prerelease=True),
        ]
        text = self._build(self._both(listed), self._two())

        self.assertEqual(text.count("[[adapter.versions]]"), 1)
        self.assertNotIn("8.8.8", text)
        self.assertNotIn("7.7.7", text)

    def test_repeated_version_listed_once(self) -> None:
        """两个 tag 撞出同一个版本号时清单只留一条"""
        listed = [
            _release("finshin-adapter-tg", _TG_URL),
            _older("finshin-adapter-tg", "9.9.9"),
        ]
        text = self._build(self._both(listed), self._two())

        self.assertEqual(text.count("[[adapter.versions]]"), 1)

    def test_stranger_repo_skipped(self) -> None:
        """分发名不属这一族的仓不进目录也不报错"""
        table = self._both()
        table[f"{_OTHER_REPO}/contents"] = None
        text = self._build(
            table, [_repo(_SDK_REPO), _repo(_TG_REPO), _repo(_OTHER_REPO)]
        )

        self.assertNotIn("hello-world", text)
        self.assertEqual(text.count("[[adapter]]"), 1)

    def test_family_without_release_skipped(self) -> None:
        """属这一族却还没发版的仓跳过，另一只照常进目录"""
        xx_url = "https://example.invalid/finshin_adapter_xx-9.9.9-py3-none-any.whl"
        xx = _release("finshin-adapter-xx", xx_url)
        table = self._both()
        table[f"{_XX_REPO}/contents"] = _decl("finshin-adapter-xx", "xx")
        table[f"{_TG_REPO}/releases/latest"] = None
        table[f"{_TG_REPO}/releases?"] = []
        table[f"{_XX_REPO}/releases/latest"] = xx
        table[f"{_XX_REPO}/releases?"] = [xx]
        text = self._build(table, [_repo(_SDK_REPO), _repo(_TG_REPO), _repo(_XX_REPO)])

        self.assertIn("[sdk]", text)
        self.assertEqual(text.count("[[adapter]]"), 1)
        self.assertIn('platform = "xx"', text)
        self.assertNotIn("tg", text)

    def test_no_adapter_at_all_raises(self) -> None:
        """一只适配器都没取到即报错，发布物没平台可用"""
        table = {
            f"{_SDK_REPO}/contents": _decl("finshin-sdk"),
            f"{_SDK_REPO}/releases/latest": _release("finshin-sdk", _SDK_URL),
            f"{_SDK_REPO}/releases?": [_release("finshin-sdk", _SDK_URL)],
        }
        with self.assertRaises(RuntimeError):
            self._build(table, [_repo(_SDK_REPO)])

    def test_missing_wheel_raises(self) -> None:
        """发过版却取不到 wheel 即报错，不出半截目录"""
        table = self._both()
        table[f"{_TG_REPO}/releases/latest"] = {"tag_name": "v9.9.9", "assets": []}
        with self.assertRaises(RuntimeError) as caught:
            self._build(table, self._two())

        self.assertIn(_TG_REPO, str(caught.exception))

    def test_no_sdk_raises(self) -> None:
        """取不到接口包即报错，缺它本体起不来"""
        table = {
            f"{_TG_REPO}/contents": _decl("finshin-adapter-tg", "tg"),
            f"{_TG_REPO}/releases/latest": _release("finshin-adapter-tg", _TG_URL),
            f"{_TG_REPO}/releases?": [_release("finshin-adapter-tg", _TG_URL)],
        }
        with self.assertRaises(RuntimeError):
            self._build(table, [_repo(_TG_REPO)])


if __name__ == "__main__":
    unittest.main()
