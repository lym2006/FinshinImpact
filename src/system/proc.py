# src/system/proc.py
"""无窗口子进程执行

- popen_hidden 起隐藏控制台的子进程，输出走文本流
- run_hidden 跑完短命令并回取结果
"""

import subprocess

# GUI 进程派生 console 子进程会各开一个黑窗口，输出已管道捕获，窗口纯属多余
_CREATE_NO_WINDOW = 0x08000000  # 与 launcher 同值：CREATE_NO_WINDOW 标志


def popen_hidden(
    argv: list[str], env: dict[str, str] | None = None
) -> subprocess.Popen[str]:
    """起无窗口子进程

    - stdout 与 stderr 合流为 UTF-8 文本流，编码异常替换不中断
    """
    return subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        creationflags=_CREATE_NO_WINDOW,
    )


def run_hidden(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """跑完无窗口子进程并回取结果

    - stdout 与 stderr 分别捕获，退出码交调用方判定
    """
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_CREATE_NO_WINDOW,
    )
