# src/utils/root_dir.py
"""
项目根目录解析工具

提供：
- 通过特征文件向上遍历
- 项目根目录
"""

from pathlib import Path

# 定义项目根目录的特征文件（按优先级排序）
_ROOT_MARKERS = (".git", "pyproject.toml")


def _get_project_root() -> Path:
    """
    获取项目根目录

    从当前文件所在目录开始，逐级向上查找包含特征文件的目录
    """
    # 确保从源码目录开始，避免 __pycache__ 干扰
    current = Path(__file__).resolve().parent

    for parent in [current, *current.parents]:
        if any((parent / marker).exists() for marker in _ROOT_MARKERS):
            return parent

    # 兜底策略：如果找不到特征文件，默认返回当前文件向上三级 (utils -> src -> root)
    return current.parent.parent.parent


# 模块加载时立即解析并缓存根目录
ROOT_DIR = _get_project_root()
