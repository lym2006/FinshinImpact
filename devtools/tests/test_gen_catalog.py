"""在线目录生成器的单元测试

- 归属判定只看默认分支声明里的分发名，仓名不参与
- 平台码、版本与直链取自该版声明与 release 附件自报的值
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

_SDK_REPO = "lym2006/FinshinSDK"
_TG_REPO = "lym2006/FinshinAdapterTG"
_OTHER_REPO = "lym2006/hello-world"
_XX_REPO = "lym2006/FinshinAdapterXX"
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


def _release(
    distribution: str, url: str, digest: str = f"sha256:{_SHA}"
) -> dict[str, Any]:
    """把一份 release 附件表回的结构"""
    stem = distribution.replace("-", "_")

    return {
        "tag_name": "v9.9.9",
        "assets": [
            {
                "name": f"{stem}-9.9.9-py3-none-any.whl",
                "browser_download_url": url,
                "digest": digest,
            }
        ],
    }


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
        if "users/lym2006/repos" in url:
            return self.repos
        return None


def _repo(full_name: str) -> dict[str, Any]:
    """拼一行仓清单"""
    return {"full_name": full_name, "default_branch": "main", "archived": False}


class TestGenCatalog(unittest.TestCase):
    """生成器聚合与报错"""

    def setUp(self) -> None:
        """把账号名固定成测试用值"""
        self._owner = os.environ.get("GITHUB_REPOSITORY")
        os.environ["GITHUB_REPOSITORY"] = "lym2006/FinshinImpact"
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        """还原账号环境变量"""
        if self._owner is None:
            os.environ.pop("GITHUB_REPOSITORY", None)
        else:
            os.environ["GITHUB_REPOSITORY"] = self._owner

    def _build(self, table: dict[str, Any], repos: list[dict[str, Any]]) -> str:
        """喂假响应生成一份目录文本"""
        with patch.object(gen_catalog, "_get", CatalogStub(repos, table)):
            return gen_catalog._build()

    def test_two_releases_agree_with_reader(self) -> None:
        """接口包与适配器各成一段，段名键位与本体读侧同值"""
        table = {
            f"{_SDK_REPO}/contents": _decl("finshin-sdk"),
            f"{_TG_REPO}/contents": _decl("finshin-adapter-tg", "tg"),
            f"{_SDK_REPO}/releases": _release("finshin-sdk", _SDK_URL),
            f"{_TG_REPO}/releases": _release("finshin-adapter-tg", _TG_URL),
        }
        text = self._build(table, [_repo(_SDK_REPO), _repo(_TG_REPO)])

        self.assertIn("[sdk]", text)
        self.assertIn("[[adapter]]", text)
        self.assertIn(f'url = "{_TG_URL}"', text)
        self.assertIn(f'sha256 = "{_SHA}"', text)
        self.assertIn('platform = "tg"', text)
        self.assertIn('version = "9.9.9"', text)

    def test_stranger_repo_skipped(self) -> None:
        """分发名不属这一族的仓不进目录也不报错"""
        table = {
            f"{_SDK_REPO}/contents": _decl("finshin-sdk"),
            f"{_TG_REPO}/contents": _decl("finshin-adapter-tg", "tg"),
            f"{_OTHER_REPO}/contents": None,
            f"{_SDK_REPO}/releases": _release("finshin-sdk", _SDK_URL),
            f"{_TG_REPO}/releases": _release("finshin-adapter-tg", _TG_URL),
        }
        text = self._build(
            table, [_repo(_SDK_REPO), _repo(_TG_REPO), _repo(_OTHER_REPO)]
        )

        self.assertNotIn("hello-world", text)
        self.assertEqual(text.count("[[adapter]]"), 1)

    def test_family_without_release_skipped(self) -> None:
        """属这一族却还没发版的仓跳过，另一只照常进目录"""
        xx_url = "https://example.invalid/finshin_adapter_xx-9.9.9-py3-none-any.whl"
        table = {
            f"{_SDK_REPO}/contents": _decl("finshin-sdk"),
            f"{_TG_REPO}/contents": _decl("finshin-adapter-tg", "tg"),
            f"{_XX_REPO}/contents": _decl("finshin-adapter-xx", "xx"),
            f"{_SDK_REPO}/releases": _release("finshin-sdk", _SDK_URL),
            f"{_TG_REPO}/releases": None,
            f"{_XX_REPO}/releases": _release("finshin-adapter-xx", xx_url),
        }
        text = self._build(table, [_repo(_SDK_REPO), _repo(_TG_REPO), _repo(_XX_REPO)])

        self.assertIn("[sdk]", text)
        self.assertEqual(text.count("[[adapter]]"), 1)
        self.assertIn('platform = "xx"', text)
        self.assertNotIn("tg", text)

    def test_no_adapter_at_all_raises(self) -> None:
        """一只适配器都没取到即报错，发布物没平台可用"""
        table = {
            f"{_SDK_REPO}/contents": _decl("finshin-sdk"),
            f"{_SDK_REPO}/releases": _release("finshin-sdk", _SDK_URL),
        }
        with self.assertRaises(RuntimeError):
            self._build(table, [_repo(_SDK_REPO)])

    def test_missing_wheel_raises(self) -> None:
        """发过版却取不到 wheel 即报错，不出半截目录"""
        table = {
            f"{_SDK_REPO}/contents": _decl("finshin-sdk"),
            f"{_TG_REPO}/contents": _decl("finshin-adapter-tg", "tg"),
            f"{_SDK_REPO}/releases": _release("finshin-sdk", _SDK_URL),
            f"{_TG_REPO}/releases": {"tag_name": "v9.9.9", "assets": []},
        }
        with self.assertRaises(RuntimeError) as caught:
            self._build(table, [_repo(_SDK_REPO), _repo(_TG_REPO)])

        self.assertIn(_TG_REPO, str(caught.exception))

    def test_foreign_digest_raises(self) -> None:
        """附件指纹不是 sha256 即报错"""
        table = {
            f"{_SDK_REPO}/contents": _decl("finshin-sdk"),
            f"{_TG_REPO}/contents": _decl("finshin-adapter-tg", "tg"),
            f"{_SDK_REPO}/releases": _release("finshin-sdk", _SDK_URL),
            f"{_TG_REPO}/releases": _release(
                "finshin-adapter-tg", _TG_URL, digest=f"md5:{_SHA}"
            ),
        }
        with self.assertRaises(RuntimeError):
            self._build(table, [_repo(_SDK_REPO), _repo(_TG_REPO)])

    def test_no_sdk_raises(self) -> None:
        """取不到接口包即报错，缺它本体起不来"""
        table = {
            f"{_TG_REPO}/contents": _decl("finshin-adapter-tg", "tg"),
            f"{_TG_REPO}/releases": _release("finshin-adapter-tg", _TG_URL),
        }
        with self.assertRaises(RuntimeError):
            self._build(table, [_repo(_TG_REPO)])


if __name__ == "__main__":
    unittest.main()
