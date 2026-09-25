# src/utils/_proxy_check.py
"""网络连通诊断（内部实现）

- 提供等待态骨架供界面先行渲染
- 生成器逐项上报结果驱动平滑刷新
"""

import socket
import sys
import urllib.error
import urllib.request

from ._system_proxy import detect_system_proxy

_PROBE_URL = "https://api.telegram.org/bot0:probe/getMe"
_PROBE_TIMEOUT = 6

# 仅当配置项与系统注册表都拿不到端口时，才回退扫描这组常见默认值
_FALLBACK_PORTS = (7890, 7897, 7898)
_PENDING = "pending"
_CHECKING = "checking"
_OK = "ok"
_FAIL = "fail"

# 固定骨架：id 与标题（界面与检测器共用，顺序即展示顺序）
_ROWS = (
    ("sysproxy", "系统代理开关"),
    ("detect", "程序代理识别"),
    ("ports", "本地代理端口"),
    ("current", "当前生效通道"),
    ("channel", "其他可通通道"),
    ("advice", "诊断结论"),
)


def diagnose_plan() -> list[dict]:
    """生成全等待态骨架，界面打开即可渲染"""
    return [
        {"id": rid, "title": title, "status": _PENDING, "detail": ""}
        for rid, title in _ROWS
    ]


def _registry_proxy() -> dict:
    """读注册表系统代理开关与地址，失败按未开启处理"""
    info = {"enable": None, "server": ""}
    if sys.platform != "win32":
        return info
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            for field, name in (("enable", "ProxyEnable"), ("server", "ProxyServer")):
                try:
                    info[field] = winreg.QueryValueEx(key, name)[0]
                except OSError:
                    pass
    except OSError:
        pass
    return info


def _extract_port(address: str) -> int | None:
    """从裸地址或分号串里提取端口，取第一个合法值"""
    for token in str(address).replace("=", ";").split(";"):
        item = token.strip().rsplit(":", 1)[-1].split("/")[0]
        if item.isdigit():
            return int(item)
    return None


def _probe_port(port: int) -> bool:
    """TCP 能否连上本地端口"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except OSError:
        return False


def _reach(proxy: str | None) -> bool:
    """实测 Telegram 可达

    收到任意 HTTP 状态码即证明网络层已打通
    """
    handlers = []
    if proxy:
        handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})]
    opener = urllib.request.build_opener(*handlers)
    try:
        opener.open(_PROBE_URL, timeout=_PROBE_TIMEOUT)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def iter_diagnose(configured_proxy: str = ""):
    """逐项产出 {id, status, detail}

    每行先 checking 再结果，结论只对当前生效通道负责。
    """
    reg = _registry_proxy()
    detected = detect_system_proxy()
    cfg = configured_proxy.strip()
    passed: list[str] = []

    # 系统代理开关
    yield {"id": "sysproxy", "status": _CHECKING, "detail": ""}
    yield {
        "id": "sysproxy",
        "status": _OK if reg["enable"] else _FAIL,
        "detail": (
            f"已开启（{reg['server']}）"
            if reg["enable"]
            else "未开启（TUN 接管或直连时可不管）"
        ),
    }

    # 程序代理识别
    yield {"id": "detect", "status": _CHECKING, "detail": ""}
    yield {
        "id": "detect",
        "status": _OK if detected else _FAIL,
        "detail": (
            f"配置留空将自动使用 {detected}" if detected else "未识别到，留空即直连"
        ),
    }

    # 本地代理端口
    yield {"id": "ports", "status": _CHECKING, "detail": ""}

    # 端口只探"有出处"的：配置项、系统注册表；两者都拿不到才回退默认组
    sources = dict.fromkeys(
        p for p in (_extract_port(cfg), _extract_port(str(reg["server"]))) if p
    )
    fallback = not sources
    ports = list(sources) if sources else list(_FALLBACK_PORTS)
    alive: list[int] = []
    marks: list[str] = []
    for port in ports:
        up = _probe_port(port)
        if up:
            alive.append(port)
        marks.append(f"{port} {'✓' if up else '✗'}")
    prefix = "默认组 " if fallback else ""
    suffix = "（未在配置/系统代理中发现端口，仅试默认值）" if fallback else ""
    yield {
        "id": "ports",
        "status": _OK if alive else _FAIL,
        "detail": prefix + "  ".join(marks) + suffix,
    }

    # 生效通道判定与 SettingsManager 的三级解析保持一致，两处改动须同步
    effective = cfg or detected
    via = (
        f"配置代理 {effective}"
        if cfg
        else f"系统代理 {effective}"
        if effective
        else "直连（代理留空且系统代理未开）"
    )

    # 当前生效通道
    yield {"id": "current", "status": _CHECKING, "detail": ""}
    current_ok = _reach(effective or None)
    yield {
        "id": "current",
        "status": _OK if current_ok else _FAIL,
        "detail": f"{via}：{'可达' if current_ok else '不可达'}",
    }

    # 其他可通通道
    yield {"id": "channel", "status": _CHECKING, "detail": ""}
    if current_ok:
        yield {"id": "channel", "status": _OK, "detail": "当前通道已通，无需再试其他"}
    else:
        candidates: list[str] = []
        if detected and detected != effective:
            candidates.append(detected)
        candidates += [
            f"http://127.0.0.1:{p}"
            for p in alive
            if f"http://127.0.0.1:{p}" != effective
        ]
        passed = [url for url in list(dict.fromkeys(candidates))[:3] if _reach(url)]
        yield {
            "id": "channel",
            "status": _OK if passed else _FAIL,
            "detail": "可改用：" + "、".join(passed) if passed else "没有其他可通通道",
        }

    # 诊断结论
    yield {"id": "advice", "status": _CHECKING, "detail": ""}
    if current_ok:
        advice = "当前配置可达 Telegram，无需修改"
    elif passed:
        advice = f"当前配置不通：把 {passed[0]} 填入代理配置项即可"
    else:
        advice = "当前配置不通且无备选：启动代理软件后重试，或开启 TUN"
    yield {
        "id": "advice",
        "status": _OK if current_ok else _FAIL,
        "detail": advice,
        "broken": not current_ok,
    }
