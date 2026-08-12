import tomllib
from pathlib import Path

rc=lambda role,content:{"role":role,"content":content}

BASE_DIR=Path(__file__).parent
CONFIG_PATH=BASE_DIR/"config.toml"
RECORD_DIR=BASE_DIR/'record'
RECORD_DIR.mkdir(parents=True,exist_ok=True)
cupa=RECORD_DIR

with open(CONFIG_PATH,"rb") as f:
    _config=tomllib.load(f)

ini=[rc("system",_config['personality']['default'])]
MODEL_NAME=_config['api']['model_name']
API_KEY=_config['api']['api_key']
TEMPERATURE=_config['api']['temperature']
GROUP_TRIGGERS=_config['triggers']['group_keywords']
CLEARUP_TIME=float(_config['data']['clearup'])*60*60
WAITING_TIME=float(_config['data']['waiting'])*60*60