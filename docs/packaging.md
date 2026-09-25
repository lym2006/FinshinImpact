# 打包教程

所有命令在项目根目录（含 `pyproject.toml`）的 `PowerShell` 中执行。首次使用需先创建并激活虚拟环境（提示符出现 `(.venv)`），未装过依赖时先跑第一步。

## 原理

发布物是绿色便携目录：

```
TelegramBot\
├── TelegramBot.exe   启动器（用户双击这个）
├── _internal\        启动器运行库
├── main.py           主程序入口（调试可单跑：runtime\python.exe main.py）
├── runtime\          嵌入式 Python 原料，首启自装于此
├── src\  pyproject.toml 等
```

启动器首启：解压嵌入式 Python → 放开 site-packages → 装 pip → 装依赖 → 拉浏览器内核 → 拉起主程序。此后每次启动比对在线版本页，弹窗确认后整包升级。

- 升级换源码与启动器：新壳有变化时暂存 `_shell_update\`，下次启动自动换入并重启一次；用户资产与运行环境保留。
- `runtime\python-embed.zip`、`get-pip.py` 是启动器按名字找的文件，**改名会坏**。
- `runtime\.installed` 记录依赖清单摘要，清单没变下次跳过安装。

## 第一步：装构建工具

```powershell
pip install -e ".[dev]"
python -m PyInstaller --version   # 应打印 6.22.3
```

## 第二步：定稿并构建

版本号在构建前定稿，zip 名取自 `pyproject.toml`，全程只构建这一次：

1. `pyproject.toml` 的 `version` 改为发布号；`CHANGELOG.md` 的 `[Unreleased]` 改为新版本号并补空 `[Unreleased]`；
2. 构建：

```powershell
python packaging\build.py
```

编译启动器 → 白名单组装（排除 `*.egg-info` 等开发残留）→ 下载嵌入式 `Python` 与 `get-pip.py`（国内镜像优先、官方兜底，zip 逐条目校验、脚本验头，不过会中止）。成功标志：末行打印 `完成：dist\TelegramBot-vX.Y.Z.zip`——第三步测试与第四步上传用的都是这个包，不要再重跑构建。

参数：`--no-launcher` 跳过编译环节；`--check` 自检四行：本地版本号、远端 tag、本地 zip、在线版本页（tag 与版本页读远端，是发布真相；推 tag 前"tag 缺失"属正常）。

## 构建缓存

两类重复开销已自动免除，正常构建无需额外操作：

- **启动器指纹复用**：编译前比对 `launcher.py` 源码哈希，未变则打印"复用已编译启动器"并跳过 PyInstaller——启动器 exe 哈希不随无关构建漂移，用户端不会触发无谓换壳；改过 launcher 后首次构建才会重新编译。
- **原料缓存**：嵌入式 Python 与 `get-pip.py` 首次下载后存入 `dist\_cache`，二次构建直接命中免下载。清缓存就删 `dist\_cache`；升级 `_EMBED_VERSION` 后文件名带新版本号，自动失效重下，无需手动处理。

## 第三步：本地测试（必做）

拿第二步产出的 zip 走一遍用户路径：

1. 把 zip 复制到别处（如桌面）解压——在 `dist\` 里测会污染构建目录。
2. 双击 `TelegramBot.exe`，进度窗口 `[1/5]`～`[5/5]`，pip 按清华→阿里→腾讯→官方四源回退，约几分钟，别关窗口。
3. 验证：向导填 token 能收发消息；再开一次应几秒直达、不再出现进度窗口；测试目录只多出 `config.toml`、`data\`、`logs\`、`runtime\`。
4. 任一环节失败都不许发布。测完删掉测试目录。

## 第四步：正式发布（顺序不可乱）

```powershell
# 1. 提交推 tag
git add -A
git commit -m "build(release): vX.Y.Z 发布定稿"
git tag vX.Y.Z
git push origin main vX.Y.Z

# 2. 上传：GitHub → Releases → 选 tag → 拖入第二步的 zip → Publish
#    正文下载行给双链（镜像优先）：
#    https://gh-proxy.com/https://github.com/lym2006/TelegramBot/releases/download/vX.Y.Z/TelegramBot-vX.Y.Z.zip

# 3. 同步版本页：把本地 pyproject.toml 覆盖到 lym2006.github.io 仓库
python packaging\build.py --check   # 自检 tag 已推、zip 已生成；末行「在线版本页」显示新版本号即发布完成
```

## 报毒

已按防误报构建（`--onedir`、无 UPX、不写注册表）。Defender 仍拦就"仍要运行"+ 微软页申诉；zip 可传 virustotal 看检出数，只应有启发式、不该有具体家族名。

## 排查

| 现象 | 处置 |
| :--- | :--- |
| 进度窗红色报错 | 无需处理，程序自动换源/回退重试，有"已自动换源"即正常 |
| 环境安装失败 | 四源全部失败才会弹；看进度窗尾部输出，恢复网络重双击即可续装 |
| 升级失败 | 进度窗打印失败原因并按当前版本启动；镜像与官方全部失败才会触发，稍后重试即可 |
| 内嵌运行环境包损坏 | zip 被截断，重下重传 |
| 双击无反应 | SmartScreen 拦截：右键属性解除锁定，或"更多信息 → 仍要运行" |
| 升级后版本没变 | 查 Release 资产是否传对 tag，再 `--check` 版本页读数 |
