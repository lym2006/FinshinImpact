# src/utils/init_files.py
"""
项目文件初始化工具

提供：
- 项目必要文件检查与初始化
- 临时目录清理
"""

import logging
import shutil

from .root_dir import ROOT_DIR

logger = logging.getLogger("Bot.Init")


# ==================== 1. 文件创建 ====================
def ensure_file_exists(target_path: str, template_path: str | None = None) -> None:
    """确保文件存在，若不存在则从模板创建或创建空文件"""
    target = ROOT_DIR / target_path
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if template_path and (ROOT_DIR / template_path).exists():
        target.write_bytes((ROOT_DIR / template_path).read_bytes())
        logger.info(f"已从模板创建: {target}")
    else:
        target.touch()
        logger.info(f"已创建空文件: {target}")


# ==================== 2. 目录创建 ====================
def _ensure_dir_exists(dir_path: str) -> None:
    """确保目录存在，不存在则创建"""
    target = ROOT_DIR / dir_path
    target.mkdir(parents=True, exist_ok=True)


# ==================== 3. 项目文件初始化 ====================
def init_project_files() -> None:
    """检查并初始化项目运行所需的必要文件"""
    # 1. 清理临时目录
    temp_dir = "data/ai_records/temp"
    logger.info("正在删除残留临时文件...")
    shutil.rmtree(temp_dir, ignore_errors=True)

    logger.info("开始检查项目必要文件...")

    # 2. 初始化必要目录
    _ensure_dir_exists(temp_dir)
    _ensure_dir_exists("data/docs")
    _ensure_dir_exists("data/ai_records/staged")

    # 3. 初始化必要文件
    ensure_file_exists("data/blacklists/blacklist.txt")

    logger.info("文件检查与初始化完成。")
