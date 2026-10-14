# packaging/pack_spec.py
"""打包共享规格

- 产物身份名、发布地址与 Windows 协议值的标识符单源
- pyproject 版本与依赖清单的读取入口
"""

import tomllib
import urllib.request
from pathlib import Path
from typing import Any

# 仓库根与产物目录（_cache 存放重复构建可复用的原料）
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
APP_NAME = "FinshinImpact"  # 产物与启动器共用的应用名
EXE_NAME = f"{APP_NAME}.exe"
STAGE = DIST / APP_NAME  # 组装发布物的暂存目录
CACHE = DIST / "_cache"

_TIMEOUT_VERSION_PAGE = 10.0  # 版本页请求超时 10 秒

HDR_CONTENT_LENGTH = "Content-Length"  # 探测与下载共用的响应头名

# 版本信息网页
_PAGES_PYPROJECT_URL = "https://lym2006.github.io/FinshinImpact/pyproject.toml"

# 发布物下载地址，build 自检与启动器升级共用
RELEASE_ZIP_URL = "https://github.com/lym2006/FinshinImpact/releases/download/v{ver}/FinshinImpact-v{ver}.zip"

# 国内直连 GitHub 慢：公共加速镜像优先，官方源兜底
RELEASE_MIRRORS = ("https://gh-proxy.com/", "https://ghproxy.net/")

RUNTIME_DIR_NAME = "runtime"  # 包内运行目录名，安装解包与升级保留共用

# 升级保留用户资产（_internal 只装二进制依赖，换壳无需动）
PRESERVE_NAMES = (
    "instances",
    RUNTIME_DIR_NAME,
    "_update",
    "_internal",
)

# 换壳：运行中的 exe 不许覆盖但可改名，新壳先暂存、择机换入重启
SHELL_EXE = EXE_NAME
SHELL_PENDING = "_shell_update"
SHELL_BAK_SUFFIX = ".old"

# 与 app_icon.py 是同一份约定，两处改名必须同步：任务栏身份锚定到壳 exe 路径
AUMID_ANCHOR_VAR = "FINSHINIMPACT_EXE_PATH"

# Windows 进程创建标志，协议值与系统语义一致
DETACHED_PROCESS = 0x00000008  # 新壳不继承旧进度窗口，换壳无闪窗
CREATE_NO_WINDOW = 0x08000000  # 后台命令不弹控制台窗口

# 包内目录与原料文件名，build 落盘与启动器解包两侧必须同值
EMBED_ZIP_NAME = "python-embed.zip"
UV_PAYLOAD_DIR = "payload"
UV_ZIP_NAME = "uv.zip"
UV_EXE_NAME = "uv.exe"

# 安装期注入的代理环境变量名，拉起主程序前剔除
PROXY_ENV_VARS = ("HTTP_PROXY", "HTTPS_PROXY")


def _pyproject_data(root: Path) -> dict:
    """读取指定包根内 pyproject 的解析结果"""
    with open(root / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def local_version(root: Path) -> str:
    """指定包根内 pyproject 的版本号"""
    return str(_pyproject_data(root)["project"]["version"])


def remote_version() -> str | None:
    """读取版本页在线版本号，失败返回 None"""
    try:
        with urllib.request.urlopen(
            _PAGES_PYPROJECT_URL, timeout=_TIMEOUT_VERSION_PAGE
        ) as resp:
            data = tomllib.loads(resp.read().decode("utf-8"))
        return str(data["project"]["version"])
    except Exception:
        return None


def dependencies(root: Path) -> list[str]:
    """获取运行依赖清单"""
    return list(_pyproject_data(root)["project"]["dependencies"])


def removed_deps(root: Path) -> list[str]:
    """获取旧依赖清理清单"""
    data = _pyproject_data(root)
    tool = data.get("tool", {}).get(data["project"]["name"], {})
    return list(tool.get("removed-dependencies", []))


def _tool_settings(root: Path) -> dict:
    """读取 [tool.finshin-impact] 表

    - 换源序列与缓存目录的单源，bootstrap 装库器读同一张表
    """
    data = _pyproject_data(root)
    return data.get("tool", {}).get(data["project"]["name"], {})


def require_setting(root: Path, key: str) -> Any:
    """取配置表键值，缺键即报错

    - 代码不写默认值，避免出现第二份不一致的副本
    """
    settings = _tool_settings(root)
    if key not in settings:
        raise RuntimeError(f"pyproject 缺 [tool.finshin-impact].{key}")
    return settings[key]
