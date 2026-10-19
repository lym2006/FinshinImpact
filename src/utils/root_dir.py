from pathlib import Path


def get_project_root():
    current = Path(__file__).resolve().parent
    markers = [".git", "pyproject.toml", "setup.py", "requirements.txt"]
    for parent in [current] + list(current.parents):
        for marker in markers:
            if (parent / marker).exists():
                return parent
    return current


ROOT_DIR = get_project_root()
