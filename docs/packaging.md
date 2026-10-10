# 打包教程

所有命令在项目根目录（含 `pyproject.toml`）的 `PowerShell` 中执行。首次使用需先创建并激活虚拟环境（提示符出现 `(.venv)`），未装过依赖时先跑第一步。

## 原理

发布物是绿色便携目录：

```
FinshinImpact\
├── FinshinImpact.exe   启动器（用户双击这个）
├── _internal\        启动器运行库
├── main.py           程序入口，走引导层（调试可单跑：runtime\python.exe main.py，会先弹选择窗）
├── runtime\          嵌入式 Python 原料，首启自装于此
├── src\              代码文件
```

启动器首启：解压嵌入式 Python → 放开 site-packages → 落位随包 uv → 清理旧依赖 → 装依赖 → 拉无头浏览器内核（chromium-headless-shell，截图渲染唯一用到的内核）→ 拉起主程序。此后每次启动比对在线版本页，弹窗确认后整包升级。

- 升级换源码与启动器：
  - 新壳有变化时暂存 `_shell_update\`，当场换入并由旧壳拉起新壳，确认新程序抢到引导锁（弹选择窗即持有）后旧壳退场
  - 新壳启动慢会弹限时提示，始终等不到接管则旧壳直接启动兜底
  - 换壳失败则下次启动兜底换入
  - 用户资产与运行环境一律保留
- `runtime\python-embed.zip` 是启动器按名字找的文件，**改名会坏**；`payload\uv.zip` 供首启解出 uv.exe，取用后 payload 自动删除。
- `runtime\.installed` 记录依赖清单摘要，清单没变下次跳过安装；`runtime\.cleaned` 记录清理清单指纹，清单变更即补做一次旧依赖清理。
- 旧依赖清理清单登记在 `pyproject.toml` 的 `[tool.finshin-impact] removed-dependencies`，与依赖同处一文件；删库时把名字加进去，重新加回某库时删对应行。
- 装包缓存放 `runtime\uv-cache`（不写用户目录的 uv 默认缓存），全链成功后删除；安装中途失败则保留，续装直接命中免重下。

## 第一步：装构建工具

```powershell
pip install -e ".[dev]"
python -m PyInstaller --version   # 应打印 6.22.3
```

## 第二步：定稿并构建

版本号在构建前定稿，zip 名取自 `pyproject.toml`，全程只构建这一次：

1. `pyproject.toml` 的 `version` 改为发布号；`CHANGELOG.md` 的 `[Unreleased]` 改为新版本号并补空 `[Unreleased]`，如有 `Planned` 则原样保留在新 `[Unreleased]`；
2. 构建：

```powershell
python packaging\build.py
```

编译启动器 → 白名单组装（排除 `*.egg-info` 等开发残留）→ 下载嵌入式 `Python` 与 `uv`（镜像优先、官方兜底，zip 逐条目校验并比对官方 sha256，不过会中止）。成功标志：末行打印 `完成：dist\FinshinImpact-vX.Y.Z.zip`——第三步测试与第四步上传用的都是这个包，不要再重跑构建。

参数：`--no-launcher` 跳过编译环节；`--check` 自检六行：本地版本号、远端 tag、本地 zip（大小+sha256 前缀）、在线版本页、发布物官方直连、发布物 gh-proxy（后两行 HEAD 探测远端资产，大小与本地包一致才算上传闭环；推 tag 前"tag 缺失"、发布前"不可达"属正常）。

## 构建缓存

两类重复开销已自动免除，正常构建无需额外操作：

- **启动器指纹复用**：编译前比对 `launcher.py` 源码与 `assets\app.ico` 图标的合并哈希，未变则打印"启动器源码与图标未变，复用已编译启动器"并跳过 PyInstaller——启动器 exe 哈希不随无关构建漂移，用户端不会触发无谓换壳；改过 launcher 或换过图标后首次构建才会重新编译。
- **原料缓存**：嵌入式 Python 与 `uv` 首次下载后存入 `dist\_cache`，二次构建直接命中免下载。清缓存就删 `dist\_cache`；升级 `_EMBED_VERSION` 或 `_UV_VERSION` 后缓存名带新版本号，自动失效重下，无需手动处理。

## 第三步：本地测试（必做）

拿第二步产出的 zip 走一遍用户路径：

1. 把 zip 复制到别处（如桌面）解压——在 `dist\` 里测会污染构建目录。
2. 双击 `FinshinImpact.exe`，进度窗口 `[1/5]`～`[5/5]`，uv 按腾讯→阿里→清华→官方四源回退，约一两分钟，别关窗口。
3. 验证：向导填 token 能收发消息；再开一次应几秒直达、不再出现进度窗口；测试目录只多出 `instances\` 与 `runtime\`；`payload\` 首启取完 uv 即删，不应残留。实例文件夹内应含 `config.toml`、`persona.md`、`profile.json`、`data\`、`logs\`。
4. 任一环节失败都不许发布。测完删掉测试目录。

## 第四步：正式发布

详见 [release-workflow](release-workflow.md) 要求。


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
