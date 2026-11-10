# src/services/env_setup/deps_startup.py
"""启动期插件规则

- 定本实例应结算哪几只插件，把装失败的插件移出启用集
"""

from finshin_sdk.domain import BUNDLED_PLUGIN_PRIORITY, ManifestKey, StateKey

from .deps_manifest import (
    catalog_digest,
    load_manifests,
    load_state,
    plugins_roots,
    save_state,
    top_package_name,
)


def target_manifests(code: str) -> list[dict]:
    """取本实例应结算的插件清单

    - 范围是随包插件与本实例启用集
    - 随包插件不看勾选，读取侧恒并入
    """
    roots = plugins_roots()
    if not roots:
        return []
    enabled = set(load_state(code).get(StateKey.ENABLED, []))
    return [
        manifest
        for manifest in load_manifests(roots)
        if manifest[ManifestKey.NAME] in BUNDLED_PLUGIN_PRIORITY
        or manifest[ManifestKey.NAME] in enabled
    ]


def disable_failed(code: str, failed: list[str]) -> list[str]:
    """把安装失败的启用插件移出启用集并落盘

    - 失败项按顶层包名或资源声明命中哪个插件就禁哪个
    - 命中不了具体插件（整轮异常）时启用集全禁
    - 只改启用集，不动已装库
    """
    roots = plugins_roots()
    if not roots:
        return []
    enabled = [
        name
        for name in load_state(code).get(StateKey.ENABLED, [])
        if isinstance(name, str)
    ]
    if not enabled:
        return []

    tops = {top_package_name(item) for item in failed}
    dropped: list[str] = []
    for manifest in load_manifests(roots):
        name = manifest[ManifestKey.NAME]
        if name not in enabled:
            continue
        deps = {top_package_name(pin) for pin in manifest[ManifestKey.DEPS]}
        assets = set(manifest[ManifestKey.ASSETS])
        if deps & tops or assets & set(failed):
            dropped.append(name)
    if not dropped:
        dropped = list(enabled)

    keep = [name for name in enabled if name not in dropped]
    save_state(code, keep, catalog_digest(load_manifests(roots)))
    return dropped
