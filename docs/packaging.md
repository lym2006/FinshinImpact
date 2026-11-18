# 打包教程

所有命令在项目根目录的 PowerShell 中执行。
环境搭建见 [development.md](development.md) 的「环境搭建」节，发布顺序见 [release-workflow.md](release-workflow.md)。

## 原理

发布物指构建出来的绿色便携目录。
发布包指分发它的那只 zip 文件。

发布物形状：

```
FinshinImpact\
├── FinshinImpact.exe   启动器（用户双击这个）
├── _internal\          启动器运行库
├── main.py             程序入口，走引导层
├── runtime\            嵌入式 Python 原料，首启自装于此
├── src\                代码文件
```

启动器首启：解压嵌入式 Python → 放开 site-packages → 落位随包 uv → 装依赖 → 拉起主程序。

- 插件依赖与浏览器内核由引导层在启动前按需安装，不在首装链路。
- 更新入口与触发方式见 [development.md](development.md) 的「更新方式」节。

升级换源码与启动器：

- 新壳有变化时暂存 `_shell_update\`，当场换入，由旧壳拉起新壳。
- 新程序抢到引导锁后旧壳退场。
- 新壳启动慢会弹限时提示，等不到接管则旧壳直接启动兜底。
- 换壳失败留到下次启动换入。
- 换壳遗留的 `.old` 备份在启动收尾限时删除，删不掉留到下次。
- 运行环境保留在原目录。

按名字找的文件：

- `runtime\python-embed.zip` **改名会坏**。
- `payload\uv.zip` 供首启解出 `uv.exe`，取用后 payload 自动删除。

依赖清单：

- 要装的库出自 `pyproject.toml` 的核心依赖。
- `runtime\.installed` 记依赖清单摘要，清单没变下次跳过安装。
- 构建只在临时副本里跑，或在仓内跑完即清 `build\`、`*.egg-info`、`dist\`。
- 启动器装依赖只追加，删库入口见 [development.md](development.md) 的「新增插件（清单驱动流程）」节。

下载缓存：

- 放 `runtime\uv-cache`，启动器装完不删，供随后的依赖同步复用。
- 手动清理走选窗"环境维护"里的"清理下载缓存"。

## 构建

版本定稿与构建次数见 [release-workflow.md](release-workflow.md) 的「构建 zip」节。
zip 名取自 `pyproject.toml`。

检查构建工具：

```powershell
python -m PyInstaller --version
```

构建命令：

```powershell
python packaging\build.py
```

构建做这几步：

- 编译启动器。
- 白名单组装，排除 `*.egg-info` 等开发残留。
- 包内 `pyproject.toml` 与仓里那份一字一样。
- 下载嵌入式 `Python` 与 `uv`，镜像优先、官方兜底，zip 逐条目校验，`uv` 另比对官方 sha256，不过会中止。
- GitHub 加速镜像名单只在项目声明的 `github-mirrors` 键里维护。
- 用随包嵌入式解释器预编暂存区 `src` 与 `main.py` 的字节码，取认内容不认时间的 checked-hash 模式，用户解压即热，首启不必现场编译。

成功标志：末行打印 `完成：dist\FinshinImpact-vX.Y.Z.zip`。

参数：

- `--no-launcher`：跳过编译环节。
- `--check`：逐行打印本地版本号、远端 tag、本地 zip（大小与 sha256 前缀）、在线版本页、发布包官方直连、发布包 gh-proxy 与 ghproxy.net 的镜像。
  - 探测远端资产的那几行，大小与本地包一致才算上传闭环。
  - 推 tag 前报"tag 缺失"、发布前报"不可达"属正常。

## 子仓构建

- 子仓挂载见 [development.md](development.md) 的「挂载子仓」节。
- 子仓版本号与附件要求见 [release-workflow.md](release-workflow.md) 的「子仓供件」节。

```powershell
# 平台适配器
uv build finshin/adapter/<平台码> --wheel

# 接口包
uv build finshin/sdk --wheel
```

- 适配器产物名形如 `finshin_adapter_tg-0.1.0-py3-none-any.whl`。
- 主仓构建现打接口包 wheel，放入发布目录 `_sdk`。
- 首启由启动器把需安装的接口包与核心依赖一条命令装进环境。
- 安装成功后删除 `_sdk`，失败则保留供下次续装。
- 升级整目录替换，接口包 wheel 随新发布物带入。

## 在线目录

```powershell
python packaging/gen_catalog.py <输出路径>
```

- 账号取自 `GITHUB_REPOSITORY`。
- 发布与刷新时机见 [release-workflow.md](release-workflow.md) 的「子仓供件」节。

## 构建缓存

重复开销已自动免除，正常构建无需额外操作：

- **启动器指纹复用**：编译前比对 `launcher.py` 源码与 `assets\app.ico` 的合并哈希，未变即跳过 PyInstaller 复用旧包，改过两者才重编。
- **原料缓存**：嵌入式 Python 与 `uv` 首次下载后存入 `dist\_cache`，二次构建直接命中，清缓存就删该目录。
- **版本失效**：缓存名带版本号，升级 `_EMBED_VERSION` 或 `_UV_VERSION` 后自动失效重下。

## 本地测试

拿构建出的 zip 走一遍用户路径：

1. 把 zip 复制到别处解压，不在 `dist\` 里测试。
2. 双击 `FinshinImpact.exe`，等待环境安装完成。
3. 验证首装：
   - 按 [development.md](development.md) 的「环境搭建」节创建实例，完成向导后验证收发消息。
   - 再开一次，确认依赖未变时跳过安装。
   - 确认 `payload\` 的清理结果，见「按名字找的文件」节。
4. 升级路径按 [README.md](../README.md) 的「旧版迁移」节验证。
5. 测完删掉测试目录。

正式发布见 [release-workflow.md](release-workflow.md)。

## 报毒

已按防误报构建：`--onedir`、无 UPX、不写注册表。

- zip 可传 virustotal 看检出数，只应有启发式、不该有具体家族名。

## 排查

| 现象 | 处置 |
| :--- | :--- |
| 进度窗红色报错 | 无需处理，程序自动换源/回退重试，有"已自动换源"即正常 |
| 环境安装失败 | 四源全部失败才会弹。看进度窗尾部输出，恢复网络重双击即可续装 |
| 升级失败 | 进度窗打印失败原因并按当前版本启动。镜像与官方全部失败才会触发，稍后重试即可 |
| 内嵌运行环境包损坏 | zip 被截断，重下重传 |
| 双击无反应 | SmartScreen 拦截：右键属性解除锁定，或"更多信息 → 仍要运行" |
| 升级后版本没变 | 查 Release 资产是否传对 tag，再 `--check` 版本页读数 |
