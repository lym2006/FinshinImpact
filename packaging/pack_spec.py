"""打包共享规格

- 产物身份名、发布地址与 Windows 协议值的常量表
- 版本页、发布说明与依赖清单的读取入口
"""

import hashlib
import json
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

import net_channel

# 仓库根与产物目录（_cache 存放重复构建可复用的原料）
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
APP_NAME = "FinshinImpact"  # 产物与启动器共用的应用名
EXE_NAME = f"{APP_NAME}.exe"
STAGE = DIST / APP_NAME  # 组装发布物的暂存目录
CACHE = DIST / "_cache"

_TIMEOUT_VERSION_PAGE = 10.0  # 版本页请求超时 10 秒
_TIMEOUT_RELEASE = 10.0  # release 正文请求超时 10 秒

HDR_CONTENT_LENGTH = "Content-Length"  # 探测与下载共用的响应头名

BYTES_PER_MB = 1024 * 1024  # 1 MB
HDR_USER_AGENT = "User-Agent"  # 请求头名，取件与目录生成两侧共用
HDR_AUTHORIZATION = "Authorization"  # 令牌请求头名

# 在线地址的家，启动器与构建脚本只在这一处写
_ACCOUNT = "lym2006"
_MAIN_REPO = "FinshinImpact"
_PAGES_HOST = f"https://{_ACCOUNT}.github.io"
API_HOST = "https://api.github.com"
DOWNLOAD_HOST = "https://github.com"
PROXY_SCHEME = "http://"  # 注册表只记地址与端口时补齐的协议头


class PackLayout:
    """包内布局名与工具名

    - 定义这份发布包里的目录名、脚本名、可执行名与临时件名
    - 成员只写语义本体，类名已表达域义
    """

    RUNTIME_DIR = "runtime"
    PAYLOAD_DIR = "payload"
    SDK_WHEEL_DIR = "_sdk"
    MAIN_SCRIPT = "main.py"
    LAUNCHER_SCRIPT = "launcher.py"
    PACK_SPEC_SCRIPT = "pack_spec.py"
    DECLARATION = "pyproject.toml"
    ICON = "app.ico"
    EMBED_ZIP = "python-embed.zip"
    UV_ZIP = "uv.zip"
    UV_EXE = "uv.exe"
    PYTHON_EXE = "python.exe"
    PYTHONW_EXE = "pythonw.exe"
    STAGE_ZIP = "package.zip"
    INSTALL_STAMP = ".installed"
    ICON_REFRESH_TOOL = "ie4uinit.exe"
    PYTHON_PTH_GLOB = "python*._pth"


# 版本信息网页
_PAGES_PYPROJECT_URL = f"{_PAGES_HOST}/{_MAIN_REPO}/{PackLayout.DECLARATION}"
_RELEASE_API_URL = API_HOST + f"/repos/{_ACCOUNT}/{_MAIN_REPO}/releases/tags/v{{ver}}"
_API_USER_AGENT = "Python-Script"  # GitHub API 认 UA，缺头即拒

# 发布包直链所在行的标记
_DOWNLOAD_MARK = "releases/download/"

# 发布包下载地址，build 自检与启动器升级共用
RELEASE_ZIP_URL = (
    DOWNLOAD_HOST
    + f"/{_ACCOUNT}/{_MAIN_REPO}/releases/download/v{{ver}}/{APP_NAME}-v{{ver}}.zip"
)


# 升级保留用户资产（_internal 只装二进制依赖，换壳无需动）
PRESERVE_NAMES = (
    "instances",
    PackLayout.RUNTIME_DIR,
    "_update",
    "_internal",
)

# 换壳：运行中的 exe 不许覆盖但可改名，新壳先暂存、择机换入重启
SHELL_EXE = EXE_NAME
SHELL_PENDING = "_shell_update"
SHELL_BAK_SUFFIX = ".old"

# 与本体身份件是同一份约定，两处改名必须同步：任务栏身份锚定到壳 exe 路径
AUMID_ANCHOR_VAR = "FINSHINIMPACT_EXE_PATH"

# Windows 进程创建标志，协议值与系统语义一致
DETACHED_PROCESS = 0x00000008  # 新壳不继承旧进度窗口，换壳无闪窗
CREATE_NO_WINDOW = 0x08000000  # 后台命令不弹控制台窗口

# 安装期注入的代理环境变量名，拉起主程序前剔除
PROXY_ENV_VARS = ("HTTP_PROXY", "HTTPS_PROXY")


def _pyproject_data(root: Path) -> dict:
    """读取指定包根内 pyproject 的解析结果"""
    with open(root / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def local_version(root: Path) -> str:
    """指定包根内 pyproject 的版本号"""
    return str(_pyproject_data(root)["project"]["version"])


def remote_version(proxy_url: str | None = None) -> str | None:
    """读取版本页在线版本号，失败返回 None

    - 干净直连优先，给了代理地址再补试一轮
    """
    openers = [net_channel.clean_opener()]
    if proxy_url:
        openers.append(net_channel.proxied_opener(proxy_url))
    for opener in openers:
        try:
            with opener.open(
                _PAGES_PYPROJECT_URL, timeout=_TIMEOUT_VERSION_PAGE
            ) as resp:
                data = tomllib.loads(resp.read().decode("utf-8"))
            return str(data["project"]["version"])
        except Exception:
            continue
    return None


def _drop_download_lines(body: str) -> str:
    """release 正文剔掉发布包直链所在行"""
    return "\n".join(
        line for line in body.splitlines() if _DOWNLOAD_MARK not in line
    ).strip()


def remote_release_notes(version: str, *, proxy_url: str | None = None) -> str:
    """读取指定版本 release 正文，失败返回空串

    - 干净直连优先，给了代理地址再补试一轮
    """
    request = urllib.request.Request(
        _RELEASE_API_URL.format(ver=version), headers={HDR_USER_AGENT: _API_USER_AGENT}
    )
    openers = [net_channel.clean_opener()]
    if proxy_url:
        openers.append(net_channel.proxied_opener(proxy_url))
    for opener in openers:
        try:
            with opener.open(request, timeout=_TIMEOUT_RELEASE) as resp:
                body = json.loads(resp.read().decode("utf-8")).get("body")
        except Exception:
            continue
        return _drop_download_lines(str(body or ""))
    return ""


def dependencies(root: Path) -> list[str]:
    """获取运行依赖清单"""
    return list(_pyproject_data(root)["project"]["dependencies"])


def _tool_settings(root: Path) -> dict:
    """读取 [tool.finshin-impact] 表

    - 换源序列与缓存目录的读取处，引导期装库器读同一张表
    """
    data = _pyproject_data(root)
    return data.get("tool", {}).get(data["project"]["name"], {})


def require_setting(root: Path, key: str) -> Any:
    """取配置表键值，缺键即报错

    - 缺键即报错，代码不写第二份默认值
    """
    settings = _tool_settings(root)

    # 再写一份默认值就会与表里的值不一致
    if key not in settings:
        raise RuntimeError(f"pyproject 缺 [tool.finshin-impact].{key}")
    return settings[key]


_SETTING_MIRRORS = "github-mirrors"


def release_mirrors(root: Path = ROOT) -> tuple[str, ...]:
    """取 GitHub 加速镜像序列

    - 名单只在配置表里维护，代码不写第二份
    """
    return tuple(require_setting(root, _SETTING_MIRRORS))


# 本体侧那三件在 system/digest.py，打包边界两侧各留一份
_LINES_JOIN = "\n"


def file_digest(path: Path) -> str:
    """算文件字节指纹，读不出交出空串"""
    try:
        return bytes_digest(path.read_bytes())
    except OSError:
        return ""


def bytes_digest(payload: bytes) -> str:
    """算一段字节的指纹"""
    return hashlib.sha256(payload).hexdigest()


def lines_digest(items: list[str]) -> str:
    """算行清单的指纹，行序参与取值"""
    return bytes_digest(_LINES_JOIN.join(items).encode("utf-8"))
