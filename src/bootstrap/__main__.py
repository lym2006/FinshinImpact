# src/bootstrap/__main__.py
"""引导入口脚本

- 支撑 python -m bootstrap 直接运行
"""

import sys

from . import main

if __name__ == "__main__":
    sys.exit(main())
