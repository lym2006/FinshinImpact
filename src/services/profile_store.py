# src/services/profile_store.py
"""实例仓储

- 扫描身份文件夹枚举已有实例
- 从 token 推导身份码并落盘新实例
"""

import json
import re
import shutil
import time
from pathlib import Path

from core.domain import Platform, make_profile_code, platform_of_profile
from system.atomic_write import write_bytes_atomic
from system.profile_env import (
    ASSET_PERSONA_EXAMPLE_NAME,
    ASSETS_DIR,
    INSTANCE_PERSONA_DIR_NAME,
    INSTANCE_PERSONA_NAME,
    INSTANCE_PROFILE_NAME,
    INSTANCES_DIR,
    TOKEN_KEY,
    profile_dir,
    read_profile_data,
    write_profile_data,
)

# Telegram token 结构 bot_id:secret，bot_id 即机器人数字 ID，重生成 token 不变
_TG_TOKEN_PATTERN = re.compile(r"(\d+):[A-Za-z0-9_-]+")

# 引导期身份码未定，路径常量所在的通用包一导入即按空身份码冻结，故模板路径就地拼
_PERSONA_TEMPLATE = ASSETS_DIR / ASSET_PERSONA_EXAMPLE_NAME

# 实例判定只认自描述文件，引导期必写，新建实例此刻还没有 config.toml
_INSTANCE_MARK = INSTANCE_PROFILE_NAME

# 备注名在自描述文件里的键名，token 键名由 profile_env 单源提供
_REMARK_KEY = "remark"

# 最近使用时间（创建或启动）在自描述文件里的键名，选窗列表按它降序置顶
_LAST_USED_KEY = "last_used"


def code_for_token(platform: Platform, token: str) -> str:
    """按平台从凭证推导身份码

    - Telegram 取 bot_id，结构非法返回空串
    - QQ 端身份码待适配器落地，见 multi-instance-profile.md §八
    """
    match platform:
        case Platform.TELEGRAM:
            return _code_for_telegram(token)
        case Platform.QQ:
            raise NotImplementedError("QQ 端身份码待适配器落地")
        case _:
            raise ValueError(f"未知平台 {platform!r}")


def _code_for_telegram(token: str) -> str:
    """Telegram 身份码推导

    - 重新生成 token 后 bot_id 不变，实例资产仍可定位
    """
    match = _TG_TOKEN_PATTERN.fullmatch(token.strip())
    return make_profile_code(Platform.TELEGRAM, match.group(1)) if match else ""


def list_profiles() -> list[tuple[str, str]]:
    """枚举已有实例

    - 扫 instances 下一级身份文件夹，返回 (身份码, 备注名) 列表
    - 目录不存在时返回空列表
    - 身份码解析不出平台的目录跳过，旧格式改名即回来
    - 按最近使用时间降序，时间缺失或相同时按身份码降序
    """
    profiles: list[tuple[float, str, str]] = []

    if not INSTANCES_DIR.is_dir():
        return []

    for path in sorted(INSTANCES_DIR.iterdir()):
        if not path.is_dir() or not (path / _INSTANCE_MARK).is_file():
            continue
        if platform_of_profile(path.name) is None:
            continue
        data = read_profile_data(path.name)
        last_used = data.get(_LAST_USED_KEY)
        stamp = float(last_used) if isinstance(last_used, (int, float)) else 0.0
        profiles.append((stamp, path.name, _read_remark(path)))

    profiles.sort(key=lambda item: (item[0], item[1]))
    profiles.reverse()
    return [(code, remark) for _, code, remark in profiles]


def touch_profile(code: str) -> None:
    """记录实例最近使用时间

    - 选窗确认启动时调用，下次打开选窗该实例置顶
    - 整份读改写，文件损坏或写不进一律静默放弃，不阻断启动
    """
    data = read_profile_data(code)
    if not data:
        return
    data[_LAST_USED_KEY] = time.time()
    try:
        write_profile_data(code, data)
    except OSError:
        return


def remark_of(code: str) -> str:
    """取实例备注名，缺失返回空串"""
    return str(read_profile_data(code).get(_REMARK_KEY, ""))


def create_profile(code: str, token: str, remark: str) -> None:
    """新建实例文件夹

    - 只建目录、人设与自描述文件，config.toml 由首次启动的向导生成
    - token 与备注名写进自描述文件
    - 创建即计入最近使用，新实例在选窗置顶
    """
    target = profile_dir(code)
    target.mkdir(parents=True, exist_ok=True)

    if _PERSONA_TEMPLATE.exists():
        persona = target / INSTANCE_PERSONA_DIR_NAME / INSTANCE_PERSONA_NAME
        persona.parent.mkdir(parents=True, exist_ok=True)
        write_bytes_atomic(persona, _PERSONA_TEMPLATE.read_bytes())

    write_profile_data(
        code,
        {
            TOKEN_KEY: token.strip(),
            _REMARK_KEY: remark.strip(),
            _LAST_USED_KEY: time.time(),
        },
    )


def update_profile(code: str, token: str, remark: str) -> None:
    """就地改写已有实例

    - 只覆盖自描述文件的 token 与备注名，目录与配置原样保留
    - 身份码须与既有目录一致，换机器人属新建而非编辑
    - 合并改写，保留 last_used 等既有字段
    """
    data = read_profile_data(code)
    data[TOKEN_KEY] = token.strip()
    data[_REMARK_KEY] = remark.strip()
    write_profile_data(code, data)


def delete_profile(code: str) -> bool:
    """删除实例文件夹

    - 配置、人设与数据整目录一并删除
    - 返回是否确已删除，占用导致失败时如实报告
    """
    target = profile_dir(code)
    if not target.is_dir():
        return False

    # 被占用文件会让部分删除失败，删后复查目录才算数
    shutil.rmtree(target, ignore_errors=True)
    return not target.is_dir()


def _read_remark(target: Path) -> str:
    """读取实例备注名

    - 按传入目录直接读取，不重走身份码净化
    - 文件缺失或损坏一律当空备注，不阻断选择窗
    """
    try:
        data = json.loads((target / INSTANCE_PROFILE_NAME).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    return str(data.get(_REMARK_KEY, "")) if isinstance(data, dict) else ""
