# src/profile_env.py
"""引导期基础设施

- 定义实例身份码的环境变量名与净化规则
- 定位项目根目录，作引导窗口与 utils 的路径单一来源
"""

import json
import os
import re
from pathlib import Path
from typing import Any

# 环境变量与净化规则
# 改名需同步 development.md 与选窗读写两侧
PROFILE_ENV = "FINSHINIMPACT_PROFILE"
_CODE_PATTERN = re.compile(
    r"[A-Za-z0-9-]+"
)  # 身份码拼进路径与锁名，不校验可穿越出数据目录
_ROOT_MARKERS = (".git", "pyproject.toml")  # 项目根特征文件，按优先级排序

# 实例与资源标识符，各方必须取同一个值
INSTANCE_PROFILE_NAME = "profile.json"  # 自描述文件，token 与备注名的唯一载体
INSTANCE_PERSONA_NAME = "persona.md"
ASSET_PERSONA_EXAMPLE_NAME = "persona.example.md"  # 引导期复制源与运行期回退源同名
ASSET_FONT_NAME = "font.ttf"  # GUI 令牌、帮助图、HTML 渲染三方共用
ASSET_EMOJI_FONT_NAME = "seguiemj.ttf"
TOKEN_KEY = "token"  # 自描述文件里的键名，改名即令全部既有实例失效
OWNER_PLACEHOLDER = "{OWNER_ID}"  # 人设正文的主人占位符，模板写侧与注入读侧必须同值


def _sanitize_profile(code: str) -> str:
    """净化身份码

    - 含非法字符或为空一律回落空串
    - 空串代表无身份实例，走根目录单套路径
    """
    code = code.strip()
    return code if _CODE_PATTERN.fullmatch(code) else ""


def get_profile() -> str:
    """读取当前实例身份码

    - 每次实时读环境变量，不缓存
    - 引导入口写完身份后 utils 才首次导入取值，缓存会锁死空身份
    """
    return _sanitize_profile(os.environ.get(PROFILE_ENV, ""))


def set_profile(code: str) -> str:
    """写入当前实例身份码

    - 环境变量作唯一载体，路径常量导入期即冻结只能靠它跨模块传递
    - 返回净化后的身份码，调用方据此建实例文件夹
    """
    clean = _sanitize_profile(code)
    os.environ[PROFILE_ENV] = clean
    return clean


def _find_root() -> Path:
    """逐级上溯特征文件定位项目根目录"""
    current = Path(__file__).resolve().parent

    for parent in (current, *current.parents):
        if any((parent / marker).exists() for marker in _ROOT_MARKERS):
            return parent

    # 找不到特征文件则退回 src 上一级
    return current.parent


# 路径单源，引导层与 utils 共用
ROOT_DIR = _find_root()
INSTANCES_DIR = ROOT_DIR / "instances"  # 整体不进版本库
ASSETS_DIR = ROOT_DIR / "assets"  # 随构建白名单进发布包，不随实例复制


def profile_dir(code: str) -> Path:
    """按身份码定位实例目录

    - 空身份码直接抛错，绝不回退父目录
    - pathlib 下 `INSTANCES_DIR / ""` 就是父目录本身，回退会让实例资产散落
    """
    clean = _sanitize_profile(code)
    if not clean:
        raise ValueError("身份码为空，无法定位实例目录")
    return INSTANCES_DIR / clean


def read_profile_data(code: str) -> dict[str, Any]:
    """读取实例自描述数据

    - 文件缺失或损坏一律返回空字典，由调用方决定容错方式
    """
    path = profile_dir(code) / INSTANCE_PROFILE_NAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_profile_data(code: str, payload: dict[str, Any]) -> None:
    """写入实例自描述数据

    - 整份覆盖，调用方负责合并既有字段
    """
    target = profile_dir(code)
    target.mkdir(parents=True, exist_ok=True)
    (target / INSTANCE_PROFILE_NAME).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def read_token(code: str) -> str:
    """读取实例的机器人凭证

    - 缺失返回空串，调用方据此判定实例不可用
    """
    data = read_profile_data(code)
    token = data.get(TOKEN_KEY, "")
    return str(token).strip() if isinstance(token, str) else ""
