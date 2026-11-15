"""压缩包取件

- 整包解压、单件取出与条目自检各一个出口
- 坏包原样上抛，怎么报由调用方判
"""

import zipfile
from pathlib import Path


def unpack_all(archive: Path, target: Path) -> None:
    """整包解压到指定目录"""
    with zipfile.ZipFile(archive) as package:
        package.extractall(target)


def unpack_entry(archive: Path, name: str, target: Path) -> None:
    """只取包里那一个条目"""
    with zipfile.ZipFile(archive) as package:
        package.extract(name, target)


def is_zip(archive: Path) -> bool:
    """判文件是不是 zip 载体"""
    return zipfile.is_zipfile(archive)


def zip_entries_ok(archive: Path) -> bool:
    """逐条目自检，坏包返回 False"""
    with zipfile.ZipFile(archive) as package:
        return package.testzip() is None
