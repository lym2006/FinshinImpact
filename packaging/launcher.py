# packaging/launcher.py
"""发布包启动器

- 首次启动自动安装嵌入式 Python 与核心依赖，使用随包 uv
- 启动时按包内清理清单卸载已删依赖的旧残留
- 启动前比对在线版本页，确认后整包升级并保留用户资产
- 升级后拉起新版启动器，新版取得引导锁后旧进程退出
- 弹窗、控制台、代理、运行环境、升级、换壳按域拆入 launch 子包
"""

import os
import subprocess
import sys
from pathlib import Path

from launch import console, dialogs, proxy, runtime, shell, update
from launch.instancelock import bootstrap_taken
from pack_spec import AUMID_ANCHOR_VAR, PROXY_ENV_VARS


def _already_running() -> bool:
    """选择窗占用提示

    - 引导锁已被占用则提示并退出，防重复弹选择窗
    - 同账号重复启动由主程序按身份码自行拦截，此处不管
    """
    # 只探测不持有，真正的持锁者是随后拉起的选择窗
    if bootstrap_taken():
        dialogs.info("已有一个选择窗口在打开，请在该窗口操作。")
        return True
    return False


def _root_dir() -> Path:
    """发布包根目录

    - 启动器 exe 位于包根
    """
    if not getattr(sys, "frozen", False):
        dialogs.fail_exit("本文件需经 build.py 编译成 exe 后使用")
    return Path(sys.executable).resolve().parent


def _launch(root: Path) -> None:
    """以无窗口解释器拉起主程序入口脚本

    - 注入源码路径后走引导层，先选实例再拉起主程序
    - 显式入口便于调试，可直接运行 main.py 复现问题
    """
    env = {k: v for k, v in os.environ.items() if k not in PROXY_ENV_VARS}
    env[AUMID_ANCHOR_VAR] = str(Path(sys.executable))  # 任务栏图标解析指向壳自身
    subprocess.Popen(
        [str(root / "runtime" / "pythonw.exe"), str(root / "main.py")],
        cwd=str(root),
        env=env,
    )


def main() -> None:
    """启动主流程

    - 依次：选择窗占用检查、换壳、装环境、检查升级、拉起主程序、回收进度窗口
    - 回收窗口后补删旧壳备份，旧壳退场即删，删不掉留到下次启动
    """
    if _already_running():
        sys.exit(0)
    root = _root_dir()
    shell.apply_shell_update(root)
    proxy.apply_system_proxy()
    runtime.ensure_runtime(root)
    update.check_update(root)
    _launch(root)
    console.close_console()
    shell.retire_old_shell(root)


if __name__ == "__main__":
    main()
