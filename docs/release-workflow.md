# 发布工作流

覆盖一次版本从改码到上线的四件套：CHANGELOG → commit → tag → release。

## 总流程（发布日按序执行）

```
功能提交若干（改动同步记 Unreleased）
  → 发布定稿提交（CHANGELOG 归段 + 版本号）
  → 构建 zip 并本地实测
  → 附注 tag 并推送
  → 发布 release
  → 版本页校验收尾
```

## 五项闸门（提交与发布前跑齐）

```powershell
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\ruff.exe check .
$env:ELECTRON_RUN_AS_NODE = 1
node .venv\Lib\site-packages\pyright\dist\index.js --pythonpath .venv\Scripts\python.exe --project pyproject.toml src packaging devtools
$env:PYTHONUTF8 = 1; $env:PYTHONPATH = "src"
.venv\Scripts\lint-imports.exe
.venv\Scripts\python.exe devtools\check_coding_style.py
.venv\Scripts\pytest.exe devtools\tests -q
```

- 绿的标准：ruff 两项通过，pyright 0 errors，契约 0 broken，扫描器 0 硬性，pytest 全过。
- `.venv\Scripts\pyright.exe` 会联网拉 nodeenv 失败，必须用外部 node 跑随包 dist，`node` 可换成任意 node 等价可执行文件。
- 扫描器的待核条数与上一轮比对，只许减不许增。分节与豁免见 [style-checker.md](style-checker.md)。

## 开发分支攒改动

- 一轮改动四件套全绿即分组 commit，本地攒着不 push，半成品不入库。
- 攒够一批、发布前统一理历史：`rebase -i` squash 并主题、reword 修措辞，只在未 push 的本地提交上做。
- 理完必验 `git diff 理前位置 HEAD` 为空，内容零变化才并回 main，并回用 merge 保追溯。
- push、tag 只在发布日动。

## CHANGELOG

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，条目一律 `- **加粗要点**：说明`。

- 分节固定，带 emoji，一个版本段内按此序排列，缺项不占位：
  - `### ⚠️ Breaking Changes` → `### ✨ Added` → `### 🔧 Changed` → `### 🐛 Fixed` → `### 🗑️ Removed`
  - `### 📝 Planned` 只出现在 `## [Unreleased]` 里，恒排最前。
  - 移除能力、入口或渠道的条目归 Removed，不留在 Changed。
- `## [Unreleased]` 恒在顶部，发布时把其中内容归入新段 `## [X.Y.Z] - YYYY-MM-DD`（日期为发布当天），Planned 段留在 Unreleased 里不过期。
- 预发布线：`devN` 段随每次预发布实录，发正式号（如 `1.0.0-alpha.3`）时新增版本段，按用户可感知的功能域写本版变化，不复述 dev 明细。
- 正式号归段后删除该条线上所有 `devN` 段，CHANGELOG 只留正式号。⚠️归段前 dev 段是那次预发布的唯一记录，不得提前删。
- 末个 dev 段之后未单独发号的收敛改动直接写入正式段，按实录颗粒度写足，不倒造无产物的 dev 段。
- 只写关键条目，琐碎改动一笔带过或不写，加了又删的功能（净效果为零）不留任何痕迹。
- 条目正文禁用分号：首段 `- **加粗要点**：`，换行书写，每行一段，逐行 `-` 起头，注意缩进。
- 句号与引号：条目是完整句，行尾带句号。纯主题行 `- **主题**：` 止于冒号不带句号。引用界面词一律半角双引号，不用弯引号。
- 中英文混排按 pangu spacing：中文与英文单词、数字之间补半角空格，如 `PySide6 面板`、`20 秒`、`3 处`。全角标点紧贴中文不加空格，反引号内的代码原样保留、不拆空格。
- 代码标识一律用反引号括起，且落在正文而非加粗主题行内。专有名词与单位（GitHub、PySide6、KB/s）不算代码标识，裸写。
- 已发布的版本段日常不回改，Unreleased 内条目随新规整理。历史整备期按现行规范全量重写属例外。
- 用户视角写行为，不写实现细节：说"坏配置不骗过验证"，不说"复验改走候选通道"。
- 内部重构属实现方式变化，最终行为不变也要记一条 Changed，写"做了什么、对维护意味着什么"（如"界面控件收敛到公共件，改样式一处生效"），不铺实现黑话。
- 纯注释与措辞整改不算实现方式变化，不记。
- 简洁优先：一句一个事实，删除修饰、比喻与连接性废话，不堆书面腔也不刻意口语，能砍的字一律砍。
- 分区：同域改动攒够多条即收进一个加粗主题，主题行只写 `- **主题**：`，明细换行缩进两格逐条 `-` 起头。
  - 主题按用户可感知的功能域命名（如「多实例身份隔离」「选窗平台」「配置向导人设预览」），不按文件、不按实现。
  - 单条能说完的改动不硬凑主题，保持一行 `- **要点**：说明`。
  - 子项一行一个事实，主题行不重复子项内容。

## Commit

Conventional Commits + 中文标题，多要点用 `-` 分行，详见 [`.gitmessage`](../.gitmessage)。

```
type(scope): 主题

- 要点一
- 要点二
```

| type | 用途 |
| :--- | :--- |
| feat | 新增用户可感知的行为 |
| fix | 纠正错误行为 |
| refactor | 内部重整，行为不变 |
| perf | 性能/体验优化 |
| docs / style | 文档 / 格式（可省 scope） |
| build | 版本与打包定稿 |
| revert | 回退，标题注明回退什么、恢复什么语义 |

- scope 用模块域小写：`gui` `bot` `launcher` `messages` `utils` `packaging` `instance` `release`。
- 正文要点禁用分号：一段一要点，逐行 `-` 起头。
- 标题与正文要点行尾均不带句号（标签式列举，与 docstring 详情行同口径）。
- 一组提交为一个主题，不按文件凑数。同主题跨层（如消息+工具+bot）合为一组。
- 发布定稿单独一笔：`build(release): vX.Y.Z 发布定稿`，只含 CHANGELOG 归段与 pyproject 版本号。

## 构建 zip

定稿提交后本地构建，全程只构建这一次：

```powershell
python packaging\build.py
python packaging\build.py --check   # 自检：本地版本号、远端 tag、本地 zip、在线版本页、发布物官方直连、发布物 gh-proxy
```

成功标志：末行打印 `完成：dist\FinshinImpact-vX.Y.Z.zip`。发布前必须拿这个 zip 走一遍用户路径实测（解压、双击、装环境、收发），细节见 [packaging.md](packaging.md)。

## Tag

附注 tag，注解格式固定：

```powershell
git tag -a vX.Y.Z -m "Release vX.Y.Z: 关键词一，关键词二，关键词三"
git push origin main vX.Y.Z
```

- 摘要用逗号分隔的功能关键词，3 个上下，无句号。
- 打在发布定稿提交上，不追打历史提交。
- 重写历史后按定稿笔标题重打全部 tag，这属于修正落点，不算追打历史提交。

## 版本号（semver）

| 场景 | 升位 |
| :--- | :--- |
| 正式定版 | 1.0.0 |
| 定版前公开试用 | 预发布号 `X.Y.Z-alpha.N`（如 `1.0.0-alpha.1`），tag 与产物名全程带后缀 |
| 纯修复 | patch（1.0.0 → 1.0.1） |
| 有新功能 | minor（1.0.0 → 1.1.0） |
| 破坏性行为变更 | major（1.0.0 → 2.0.0） |

## Release

发布在 GitHub 网页端操作：进仓库 [Releases](https://github.com/lym2006/FinshinImpact/releases) → Draft a new release → 选推送上来的 tag `vX.Y.Z` → 填正文 → 选上一版 tag 并点 **Generate release notes** → Publish。

Generate release notes 生成正文末尾比较链接：

```
**Full Changelog**: https://github.com/lym2006/FinshinImpact/compare/v<上一版>...v<X.Y.Z>
```

> 正式号那条取上一个**正式号**，覆盖整条预发布线。
> dev 那条取紧邻的上一个号，只覆盖这一次预发布的增量。

### 首发正文（发布日，带 zip）

```
🐳 FinshinImpact-vX.Y.Z

- 国内加速：https://gh-proxy.com/https://github.com/lym2006/FinshinImpact/releases/download/vX.Y.Z/FinshinImpact-vX.Y.Z.zip
- 官方直连：https://github.com/lym2006/FinshinImpact/releases/download/vX.Y.Z/FinshinImpact-vX.Y.Z.zip

变化
- 条目一（用户视角，2~5 条，从 CHANGELOG 该版本段提炼）
- 条目二

注意（仅升级路径或行为有特殊约束时写，无则整段省略）
- 只写事实与用户需要的动作，一句一条，禁口语、修辞、情绪化措辞
- 有破坏性变更时提示用户如何操作
```

标题行与列表之间必须空一行。CommonMark 下紧贴标题行的 `-` 会被当作该段落的续行，列表不成立，两条直链会挤成一行显示。

### 保留序列

Release 不承担升级链（升级走版本页与 PEP440 比对），只承担新用户首次下载与老用户回看某版变化。所以 release 只跟正式号，不跟预发布号：

- 正式号（`X.Y.Z`、`X.Y.Z-alpha.N`）各留一条 release，长期保留。
- dev 段的 release 只在预发布期挂着供当时下载。正式号发出时把该正式号下各 dev 的变化汇总进正式号那一条，再删掉 dev 的 release 条目。
- 汇总按用户可感知的功能域写，不复述 dev 明细。纯内部重构、用户无感知的 dev 段不写入 release。
- ⚠️**删的是 release 条目，tag 一律保留**——dev 的 tag 是那一次定稿笔的锚点，删了就 checkout 不回那次预发布。
- 正式号之间按下一节撤发布包、留条目，正文只去掉两条下载直链，🐳 标题行与变化、注意两节照留。

### 旧版收敛（不带 zip）

被取代的旧版只删发布包、留条目，正文不写任何下载行。GitHub 每条 release 页自动挂 `Source code (zip)` 与 `Source code (tar.gz)`，要源码的人在那里拿，正文重复挂链接是冗余：

```
🐳 FinshinImpact-vX.Y.Z

变化
- 条目一
- 条目二

注意
- 条目一

**Full Changelog**: https://github.com/lym2006/FinshinImpact/compare/v<上一版>...vX.Y.Z
```

⚠️**删发布包不可逆**：zip 随 release 删掉后只能重新构建，而重建产物与当时发出去的不是同一份。

### prerelease 与 latest

预发布号一律勾 `Pre-release`，正式版新发布默认勾选 `Latest`。

## 版本页同步（发布最后一步）

Release 发布完成不等于升级链生效：在线版本页是启动器与 GUI 版本检查的唯一真相。

版本页仓库的 workflow 随发布自动同步 `pyproject.toml` 并部署 Pages，**无需手动覆盖推送**。跑 `python packaging\build.py --check`，末行「在线版本页」显示新版本号即发布闭环（Pages 部署有延迟，读数未变稍后重跑）。

推 tag、传 zip 两步齐了，老客户端才会在下次启动时收到升级提示。zip 漏传，用户点了升级却下载失败。
