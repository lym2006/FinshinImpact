"""适配器在线目录生成

- 聚合账号下属于本体这一族的发行件，接口包一段，适配器按平台码升序逐段
- 一只发行件一段，段内先写最新一版，再逐版写版本清单
- 已发版却取不到声明、wheel 或指纹的仓当场报错，不出半截目录
"""

import json
import sys
from typing import Any

from gen_release import (
    KEY_DISTRIBUTION,
    KEY_PLATFORM,
    KEY_SHA256,
    KEY_URL,
    KEY_VERSION,
    KEY_VERSIONS,
    SDK_DISTRIBUTION,
    VERSION_KEYS,
    owner,
    release_row,
    repos,
)

# 目录里的段名，与本体读目录那侧同值，两处改名必须同步
_SECTION_SDK = "sdk"
_SECTION_ADAPTER = "adapter"

_SDK_ORDER = (KEY_DISTRIBUTION, KEY_VERSION, KEY_URL, KEY_SHA256)
_ADAPTER_ORDER = (KEY_PLATFORM, *_SDK_ORDER)


def _lines(row: dict[str, Any], order: tuple[str, ...]) -> list[str]:
    """按固定键序把一行写成键值串"""
    return [f"{key} = {json.dumps(row[key])}" for key in order if key in row]


def _version_lines(section: str, row: dict[str, Any]) -> list[str]:
    """把版本清单写成父段下的缩进子段"""
    lines: list[str] = []
    for item in row[KEY_VERSIONS]:
        body = [f"  {line}" for line in _lines(item, VERSION_KEYS)]
        lines.extend(["", f"  [[{section}.{KEY_VERSIONS}]]", *body])

    return lines


def _dump(sdk: dict[str, Any], adapters: list[dict[str, Any]]) -> str:
    """把目录写成 TOML 文本"""
    blocks = [
        f"[{_SECTION_SDK}]",
        *_lines(sdk, _SDK_ORDER),
        *_version_lines(_SECTION_SDK, sdk),
    ]
    for row in adapters:
        blocks.append("")
        blocks.append(f"[[{_SECTION_ADAPTER}]]")
        blocks.extend(_lines(row, _ADAPTER_ORDER))
        blocks.extend(_version_lines(_SECTION_ADAPTER, row))

    return "\n".join(blocks) + "\n"


def _build() -> str:
    """聚合账号下所有属于本体这一族的发行件

    - 接口包一段，适配器按平台码升序逐段
    """
    account = owner()
    sdk: dict[str, Any] | None = None
    adapters: list[dict[str, Any]] = []
    for repo in repos(account):
        name = str(repo.get("full_name") or "")
        ref = str(repo.get("default_branch") or "")
        row, reason = release_row(name, ref)
        if row is None:
            print(f"跳过 {reason}", file=sys.stderr)
            continue
        if KEY_PLATFORM in row:
            adapters.append(row)
        elif sdk is None:
            sdk = row

    if sdk is None:
        raise RuntimeError(f"账号 {account} 下取不到 {SDK_DISTRIBUTION} 的发行件")
    if not adapters:
        raise RuntimeError(f"账号 {account} 下一只适配器都没取到")

    adapters.sort(key=lambda item: str(item[KEY_PLATFORM]))

    return _dump(sdk, adapters)


def main() -> None:
    """生成目录并写到指定文件"""
    if len(sys.argv) < 2:
        raise RuntimeError("用法：gen_catalog.py <输出路径>")

    with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as handle:
        handle.write(_build())
    print(f"目录写出：接口包见 {_SECTION_SDK} 段，适配器见 {_SECTION_ADAPTER} 段")


if __name__ == "__main__":
    main()
