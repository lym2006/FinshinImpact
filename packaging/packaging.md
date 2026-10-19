# 打包教程

所有命令在项目根目录（含 `pyproject.toml`）的 PowerShell 中执行。

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

- 升级只换源码，`config.toml`、`data`、`logs`、`runtime` 与启动器本体保留（Windows 锁运行中的 exe，壳要升级就手动整包覆盖）。
- `runtime\python-embed.zip`、`get-pip.py` 是启动器按名字找的文件，**改名会坏**。
- `runtime\.installed` 记录依赖清单摘要，清单没变下次跳过安装。

## 第一步：装构建工具

```powershell
pip install -e ".[dev]"
python -m PyInstaller --version   # 应打印 6.22.3
```

## 第二步：本地构建

```powershell
python packaging\build.py
```

编译启动器 → 白名单组装（排除 egg-info 等开发残留）→ 下载嵌入式 Python（官方源坏了自动切 npmmirror，校验不过会中止）。成功标志：末行打印 `完成：dist\TelegramBot-vX.Y.Z.zip`。

参数：`--no-launcher` 复用已编译启动器只重打内容；`--check` 自检四行：本地版本号、远端 tag、本地 zip、在线版本页（tag 与版本页读远端，是发布真相；推 tag 前"tag 缺失"属正常）。

## 第三步：本地测试（必做）

1. 把 zip 复制到别处（如桌面）解压——在 dist 里测会污染构建目录；
2. 双击 `TelegramBot.exe`，进度窗口 [1/5]～[5/5]，pip 走清华源约几分钟，别关窗口；
3. 验证：向导填 token 能收发消息；再开一次应几秒直达、不再出现进度窗口；测试目录只多出 config.toml、data、logs、runtime；
4. 任一环节失败都不许发布。测完删掉测试目录。

## 第四步：正式发布（顺序不可乱）

```powershell
# 1. 定稿：改 pyproject 的 version；CHANGELOG 的 Unreleased 改为新版本号并补空 Unreleased
# 2. 提交推 tag
git add -A
git commit -m "build(release): vX.Y.Z 发布定稿"
git tag vX.Y.Z
git push origin main vX.Y.Z

# 3. 构建并上传：GitHub → Releases → 选 tag → 拖入 zip → Publish
python packaging\build.py
# 蓝奏云同步上传同名文件覆盖：https://wwbgy.lanzoub.com/b0pnwooed（密码 5rp0）
#   分享链接不变，README 备用下载入口即生效

# 4. 同步版本页：把本地 pyproject.toml 覆盖到 lym2006.github.io 仓库
python packaging\build.py --check   # 末行「在线版本页」显示新版本号即发布完成
```

版本页仓库自身的 Pages workflow 负责部署，push 即生效，无需其他操作。

## 报毒

已按防误报构建（onedir、无 UPX、不写注册表）。Defender 仍拦就"仍要运行"+ 微软页申诉；zip 可传 virustotal 看检出数，只应有启发式、不该有具体家族名。

## 排查

| 现象 | 处置 |
| :--- | :--- |
| 环境安装失败 | 看进度窗 pip 尾部输出，恢复网络重双击即可续装 |
| 内嵌运行环境包损坏 | zip 被截断，重下重传 |
| 双击无反应 | SmartScreen 拦截：右键属性解除锁定，或"更多信息 → 仍要运行" |
| 升级后版本没变 | 查 Release 资产是否传对 tag，再 `--check` 版本页读数 |
