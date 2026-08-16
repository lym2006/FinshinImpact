from pathlib import Path

from src.utils import CONFIG

rc = lambda role, content: {"role": role, "content": content}

BASE_DIR = Path(__file__).parent
RECORD_DIR = BASE_DIR / "record"
RECORD_DIR.mkdir(parents=True, exist_ok=True)
cupa = RECORD_DIR

ini = [rc("system", CONFIG["personality"]["default"])]
MODEL_NAME = CONFIG["api"]["model_name"]
API_KEY = CONFIG["api"]["api_key"]
TEMPERATURE = CONFIG["api"]["temperature"]
GROUP_TRIGGERS = CONFIG["triggers"]["group_keywords"]
CLEARUP_TIME = float(CONFIG["data"]["clearup"]) * 60 * 60
WAITING_TIME = float(CONFIG["data"]["waiting"]) * 60 * 60
