# devtools/probe_stream_usage.py
"""流式用量探针

- 同一端点连发两条流式请求，分别看不声明与声明用量的末帧形态
- 交出本地字符估与端点回读的 prompt_tokens 供对照
- 密钥只报长度，不打印内容
- 实例走 FINSHINIMPACT_PROFILE 环境变量点名
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from plugins.AI.config import ai_config  # noqa: E402
from plugins.AI.core import AIClient  # noqa: E402
from plugins.AI.utils import estimate_tokens  # noqa: E402
from system.profile_env import get_profile  # noqa: E402
from utils import config_manager  # noqa: E402
from utils.config import load_config  # noqa: E402
from utils.network import BaseClient  # noqa: E402

# 探针话术与帧解析参数
_PROBE_TEXT = "只回一个字：好"
_TAIL_FRAMES = 3  # 打印末尾几帧原文
_DATA_MARK = "data: "  # SSE 帧前缀
_DONE_MARK = "[DONE]"


async def _probe(label: str, stream_options: dict[str, Any] | None) -> None:
    """发一条流式请求并按帧收集

    - 用量声明为空即复刻现网 payload 形态
    """
    payload: dict[str, Any] = {
        "model": ai_config.model_name,
        "messages": [{"role": "user", "content": _PROBE_TEXT}],
        "stream": True,
        "temperature": ai_config.temperature,
        **dict(ai_config.think_mode),
    }
    if stream_options is not None:
        payload["stream_options"] = stream_options

    frames: list[dict[str, Any]] = []
    async for line in BaseClient.stream_post(
        base_url=ai_config.base_url,
        request_path=ai_config.request_path,
        headers=AIClient._headers(),
        payload=payload,
        timeout=ai_config.timeout,
    ):
        if not line.startswith(_DATA_MARK):
            continue
        body = line[len(_DATA_MARK) :].strip()
        if body == _DONE_MARK:
            continue
        try:
            frames.append(json.loads(body))
        except json.JSONDecodeError:
            print(f"  非 JSON 帧: {body[:120]}")

    print(f"── {label}：共 {len(frames)} 帧")
    for frame in frames[-_TAIL_FRAMES:]:
        print(f"  {json.dumps(frame, ensure_ascii=False)}")
    usage = next((f.get("usage") for f in reversed(frames) if f.get("usage")), None)
    print(f"  用量读数: {usage if usage else '无'}")


async def _main() -> None:
    """两条请求都要，只看不声明的那条能否白拿到用量"""
    config_manager.load(load_config())
    print(f"实例 {get_profile()}｜模型 {ai_config.model_name}")
    print(f"密钥长度 {len(ai_config.api_key)}")
    print(f"字符估约 {estimate_tokens(_PROBE_TEXT)} token")

    await _probe("不声明用量（现网形态）", None)
    await _probe("声明 include_usage", {"include_usage": True})


if __name__ == "__main__":
    asyncio.run(_main())
