"""启动期插件规则

- 定本实例应结算哪几只插件，把装失败的插件移出启用集
"""

from finshin_sdk.domain import ManifestKey, StateKey, is_enabled
from system.plugin_state import load_instance_enabled

from .deps_manifest import (
    catalog_digest,
    load_manifests,
    plugins_roots,
    save_state,
    state_path_of,
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
    enabled = load_instance_enabled(state_path_of(code), StateKey.ENABLED)
    return [
        manifest
        for manifest in load_manifests(roots)
        if is_enabled(manifest[ManifestKey.NAME], enabled)
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
    enabled = load_instance_enabled(state_path_of(code), StateKey.ENABLED)
    if not enabled:
        return []

    manifests = load_manifests(roots)
    tops = {top_package_name(item) for item in failed}
    ordered: list[str] = []
    dropped: list[str] = []
    for manifest in manifests:
        name = manifest[ManifestKey.NAME]
        if name not in enabled:
            continue
        ordered.append(name)
        deps = {top_package_name(pin) for pin in manifest[ManifestKey.DEPS]}
        assets = set(manifest[ManifestKey.ASSETS])
        if deps & tops or assets & set(failed):
            dropped.append(name)
    if not dropped:
        dropped = ordered

    keep = [name for name in ordered if name not in dropped]
    save_state(code, keep, catalog_digest(manifests))
    return dropped
