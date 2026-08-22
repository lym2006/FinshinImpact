# src/plugins/AI/core/config.py
"""
AI 核心配置

负责：
- 记录存放路径
- API 参数
- 运行状态。
"""

from src.utils import CONFIG, ROOT_DIR

from .utils import build_message

# ==================== 1. 路径配置 ====================
RECORD_DIR = ROOT_DIR / "data/ai_records"
BLACK_DIR = ROOT_DIR / "data/blacklists"

# ==================== 2. API 与模型配置 ====================
MODEL_NAME: str = CONFIG["api"]["model_name"]
API_KEY: str = CONFIG["api"]["api_key"]
TEMPERATURE: float = CONFIG["api"]["temperature"]

# ==================== 3. 运行参数配置 ====================
GROUP_TRIGGERS: list[str] = CONFIG["triggers"]["group_keywords"]
CLEARUP_TIME: float = CONFIG["data"]["clearup"] * 60 * 60
WAITING_TIME: float = CONFIG["data"]["waiting"] * 60 * 60

# ==================== 4. 初始化状态 ====================
INIT = [build_message("system", CONFIG["personality"]["default"])]
