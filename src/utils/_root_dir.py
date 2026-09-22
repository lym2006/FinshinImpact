# src/utils/_root_dir.py
"""根目录定位（内部实现）

- 定义特征文件上溯与缓存机制
"""

from pathlib import Path

# 定义项目根目录的特征文件（按优先级排序）
_ROOT_MARKERS = (".git", "pyproject.toml")


def _get_project_root() -> Path:
    """逐级上溯特征文件定位项目根目录"""
    # 确保从源码目录开始，避免 __pycache__ 干扰
    current = Path(__file__).resolve().parent

    for parent in [current, *current.parents]:
        if any((parent / marker).exists() for marker in _ROOT_MARKERS):
            return parent

    # 如果找不到特征文件，默认返回当前文件向上三级 (utils -> src -> root)
    fallback = current.parent.parent.parent
    return fallback


# 模块加载时立即解析并缓存根目录
ROOT_DIR = _get_project_root()
