# src/utils/config/_io.py
"""配置读写（内部实现）

- 实现 TOML 加载与全量保存
"""

import shutil
from pathlib import Path

import tomlkit

from exceptions import ConfigInputError, ConfigMissingError, ConfigOutputError

from .models import AppConfigData


class ConfigIO:
    """配置文件读写器"""

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path

    # ==================== 读取 ====================

    def load(self) -> AppConfigData:
        """读取配置数据"""
        if not self._config_path.exists():
            raise ConfigMissingError() from None

        try:
            raw_text = self._config_path.read_text(encoding="utf-8")
            return tomlkit.parse(raw_text)
        except Exception as e:
            raise ConfigInputError() from e

    # ==================== 写入 ====================

    def save(self, config_data: AppConfigData) -> None:
        """全量保存配置"""
        try:
            # 写入前自动备份旧文件
            if self._config_path.exists():
                backup_path = self._config_path.with_suffix(".toml.bak")
                shutil.copy2(self._config_path, backup_path)

            doc = tomlkit.document()
            for section, values in config_data.items():
                table = tomlkit.table()
                for key, value in values.items():
                    table[key] = value
                doc.add(section, table)

            self._config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
        except Exception as e:
            raise ConfigOutputError() from e
