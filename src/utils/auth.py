from pathlib import Path

file=Path("assets/blacklist.txt")

def get_list() -> list[str]:
    path=file
    if not path.exists():
        return [""]
    with open(path,'r',encoding='utf-8') as a:
        return [line.strip() for line in a if line.strip()]

def save_list(list:list):
    path=file
    with open(path,'w',encoding='utf-8') as a:
        a.write('\n'.join(list))

def is_blocked(user:int) -> bool:
    blacklist=get_list()
    return str(user) in blacklist