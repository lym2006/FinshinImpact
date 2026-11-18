# 发布工作流

本文规定改动提交与发布步骤。
中文措辞、条目与排版见 [coding-style.md](coding-style.md) 的「文档写法」节。

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
.venv\Scripts\python.exe devtools\gates.py
```

- 一条命令跑齐五步，每步一行读数，任一步红即整体退一。
- 红的那步下面带最多 30 行原始输出。
- 只重跑点名的步：`--only` 接步名，可多次，候选 `ruff`／`pyright`／`imports`／`style`／`pytest`。
- 目标不写死：类型检查与用例两步按挂载现场算，含本体三棵树与各挂载子仓声明的源码与用例目录。
- 绿的标准：
  - ruff format 与 check 都通过。
  - pyright 0 errors。
  - 契约 0 broken。
  - 扫描器 0 硬性。
  - pytest 全过。
- pyright 跑的是开发依赖带的 node：`devtools/pyproject.toml` 声明 `pyright[nodejs]`，`uv sync --all-packages` 之后即齐，不需要另外装 Node.js。
- 各步判据不在这里重复：扫描器的分节、待核基线与豁免见 [style-checker.md](style-checker.md)，用例口径见 [testing.md](testing.md)，构建与发布物见 [packaging.md](packaging.md)。

## 日常与定稿

- 一轮改动五项闸门全绿即分组 commit。
- 本地攒着不 push，半成品不入库。
- 未 push 期间随便整历史，已 push 的笔日常不改写：
  - 改动按行折回它原来那笔。
  - 同主题并笔、reword 修措辞，不留「先写后改」的碎笔，CHANGELOG 条目跟着它那条行为改动的笔一起交。
  - 整完必验 `git diff 整备前位置 HEAD` 为空，内容零变化才算整对。
- 历史整备期允许一次全量重写，条件四条：release 附件与 zip 不动、全部 tag 删旧重打并钉 tagger 日期、镜像仓重灌、`git diff 重写前位置 HEAD` 为空。
- push、tag 只在发布日动。

## 子仓供件

- 子仓的挂载、日常改动、更新与摘掉见 [development.md](development.md) 的「挂载子仓」节。
- 子仓跑格式、类型、规范、用例四项检查，目标由闸门那条命令按挂载现场算。
- 分层契约与发布物打包归本体。
- 子仓版本号以 `pyproject.toml` 的 `[project].version` 为单源，tag、wheel 文件名与本体读到的版本都从它取。
- wheel 构建见 [packaging.md](packaging.md) 的「子仓构建」节。
- 适配器发版只在子仓，本体的发布链不含适配器版本：
  - tag 打在子仓那一笔上，名字就是版本号（`v0.1.0`）。
  - release 附件只放 wheel，不放源码快照，不在用户机器上构建。
  - 下载直链与指纹取 GitHub 记在 wheel 附件上的值。
  - 正文标题行写 `🐳 仓名-v版本号`。
  - 正文不写下载直链，wheel 只以附件在场。
  - release 建完即定稿，旧版附件不撤。
  - 在线目录由本体的 Pages 工作流按账号下各仓的声明聚合，与版本页同一份产物一起部署。
  - 子仓单独发版后，目录最长等到本体一次 push 或每日定时重建才反映那一版。
- 「工作区干净」这条判据算本体与每只子仓，只看本体那棵不算数。

## CHANGELOG

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，条目一律 `- **加粗要点**：说明`。

### 版本段

- 分节固定，带 emoji，一个版本段内按此序排列，缺项不占位：
  - `### ⚠️ Breaking Changes` → `### ✨ Added` → `### 🔧 Changed` → `### 🐛 Fixed` → `### 🗑️ Removed`
  - `### 📝 Planned` 只出现在 `## [Unreleased]` 里，恒排最前。
- `## [Unreleased]` 恒在顶部。
  - 标题行只写 `## [Unreleased]`，不带日期，也不带别的字。
  - 发布时把其中内容归入新段 `## [X.Y.Z] - YYYY-MM-DD`，日期为发布当天。
  - Planned 段留在 Unreleased 里不过期。
- 预发布线：`devN` 段随每次预发布实录。
  - 发正式号（如 `1.0.0-alpha.3`）时新增版本段。
  - 正式段按用户可感知的功能域写本版变化，不复述 dev 明细。
- 正式号归段后删除该条线上所有 `devN` 段，CHANGELOG 只留正式号。
- `devN` 段在归段前是那次预发布的唯一记录，不得提前删。
- 末个 dev 段之后未单独发号的收敛改动直接写入正式段，按实录颗粒度写足，不倒造无产物的 dev 段。

### 写什么

- 只写关键条目，琐碎改动一笔带过或不写，加了又删的功能不留任何痕迹，增与删的条目一起清。
- 用户视角写行为，不写实现细节。
- 内部重构写对维护的影响，如「界面控件收敛到公共件，改样式一处生效」。
- 改动类型与 CHANGELOG 归段见「Commit」节。

### 条目与措辞

- 主题名按功能域起。
- 主题行不重复子项内容。
- 单条能说完的改动不硬凑主题，保持一行 `- **要点**：说明`。

### 排版

- 条目是完整句，行尾带句号。
- 纯主题行 `- **主题**：` 止于冒号，不带句号。
- 反引号不落进加粗主题行。

### 回改

- 已发布的版本段日常不回改，Unreleased 内的条目随新规整理，历史整备期按现行规范全量重写属例外。

## Commit

- 标题采用 Conventional Commits 与中文标题的 `type(scope): 主题`，50 字符内，首字母小写，模板见 [.gitmessage](../.gitmessage)。
- 标题与正文之间空一行。
- 正文逐行以 `- ` 起头，每行 72 字符内。
- 页脚用于关联 Issue，破坏性变更写在正文，不写页脚标记。

| type | 用途 | CHANGELOG 归段 |
| :--- | :--- | :--- |
| feat | 纯新增用户可感知的行为 | Added |
| change | 改掉既有的用户可感知行为 | Changed |
| fix | 纠正与既定期望相违的行为 | Fixed |
| remove | 删掉用户可感知的行为或产物 | Removed |
| breaking | 主体就是让用户动手 | Breaking Changes |
| refactor | 内部重整，用户可感知行为不变 | Changed |
| perf | 只改耗时与资源占用，功能与观感不变 | Changed |
| docs / style / test | 只改文档 / 格式 / 用例 | 不记 |
| build | 版本与打包定稿 | 不记 |
| revert | 回退已推送的改动 | 跟着被回退的那两条一起清 |
| chore | 已停用 | 历史重整时按内容归进 refactor、docs 或 build |

- 第一刀按用户能不能感知分：能感知用前五类，不能感知用后六类。
- 一笔只写一个 type，取主题主导那一面。
- 其余面只进 CHANGELOG 对应段，不在标题里堆两类。
- fix 与 change 的分界：有没有一条已写下的期望被违反，违反了是 fix，没违反只是改主意是 change。
- remove 与 change 的分界：做完用户少一样能用的东西或少一个产物是 remove。
- perf 与 change 的分界：观感与功能的变化都归 change，perf 只指耗时、内存与体积。
- breaking 只在主体是「用户必须动手」时才用，既新增又要动手的笔按新增定 type。
- 版本号档不由 type 决定，见「版本号（semver）」节。
- 版本段写法见「CHANGELOG」节。
- 标题与正文要点行尾不带句号。
- scope 用模块域小写，取它改的那一块的名字。
- `docs`、`style`、`test`、`build` 可省 scope，其余必带。
- 一组提交为一个主题，不按文件凑数，同主题跨层（如消息+工具+bot）合为一组。
- 发布定稿单独一笔 `build(release): vX.Y.Z 发布定稿`，只含 CHANGELOG 归段与 pyproject 版本号。

## 构建 zip

- 定稿提交后本地构建，全程只构建这一次。
- 构建命令、自检与用户路径实测见 [packaging.md](packaging.md)。
- 测试、上传使用同一次构建的 zip，任一实测环节失败都不许发布。

## Tag

附注 tag，注解格式固定：

```powershell
git tag -a vX.Y.Z -m "Release vX.Y.Z: 关键词一，关键词二，关键词三"
git push origin main vX.Y.Z
```

- 摘要用逗号分隔的功能关键词，3 个上下，无句号，打在发布定稿提交上，不追打历史提交。
- 重写历史后按定稿笔标题重打全部 tag，属修正落点，不算追打历史。

## 版本号（semver）

| 场景 | 升位 |
| :--- | :--- |
| 正式定版 | 1.0.0 |
| 定版前公开试用 | 预发布号 `X.Y.Z-<阶段>.N`（如 `1.0.0-alpha.1`），tag 与产物名全程带后缀 |
| 纯修复 | patch（1.0.0 → 1.0.1） |
| 有新功能 | minor（1.0.0 → 1.1.0） |
| 破坏性行为变更 | major（1.0.0 → 2.0.0） |

- 预发布阶段取 `alpha`、`beta`、`rc` 三档之一，写作 `X.Y.Z-<阶段>.N`。
  - 每次预发布的实录段在其后再缀 `.devM`，写作 `X.Y.Z-<阶段>.N.devM`。
  - 三种串在 CHANGELOG 版本段、tag、产物名与 pyproject 版本号全程同形，只差 tag 与产物名前那个 `v`。

## Release

发布在 GitHub 网页端操作，按序：

- 进仓库 [Releases](https://github.com/FinshinLabs/FinshinImpact/releases)。
- Draft a new release。
- 选推送上来的 tag `vX.Y.Z`。
- 填正文，正文形状见下面两小节。
- 选上一版 tag 并点 **Generate release notes**。
- Publish。

- 比较链接由 Generate release notes 生成，形状 `**Full Changelog**: https://github.com/FinshinLabs/FinshinImpact/compare/v<上一版>...v<X.Y.Z>`。
- 正式号那条取上一个**正式号**，覆盖整条预发布线。
- dev 那条取紧邻的上一个号，只覆盖这一次预发布的增量。
- 首版没有上一版 tag，比较链接那行写本版 tag 的提交链接。

### 首发正文（发布日，带 zip）

```
🐳 FinshinImpact-vX.Y.Z

- 国内加速：https://gh-proxy.com/https://github.com/FinshinLabs/FinshinImpact/releases/download/vX.Y.Z/FinshinImpact-vX.Y.Z.zip
- 官方直连：https://github.com/FinshinLabs/FinshinImpact/releases/download/vX.Y.Z/FinshinImpact-vX.Y.Z.zip

变化
- 条目一（用户视角，2~5 条，从 CHANGELOG 该版本段提炼）
- 条目二

注意（仅升级路径或行为有特殊约束时写，无则整段省略）
- 只写事实与用户需要的动作，一句一条，禁口语、修辞、情绪化措辞
- 有破坏性变更时提示用户如何操作
```

### 保留序列

更新方式见 [development.md](development.md) 的「更新方式」节。

保留规则：

- 正式号（不带 `.devM` 的那两种串，形状见「版本号（semver）」节）各留一条 release，长期保留。
- dev 段的 release 只在预发布期挂着供当时下载。
- 正式号发出时把该正式号下各 dev 的变化汇总进正式号那一条，再删掉 dev 的 release 条目。
- 汇总按用户可感知的功能域写，不复述 dev 明细。
- 纯内部重构、用户无感知的 dev 段不写入汇总。
- ⚠️ 删的是 release 条目，tag 一律保留。
- 正式号之间按「旧版收敛」一节撤发布包、留条目，正文只去掉两条下载直链，其余行照留。

### 旧版收敛（不带 zip）

被取代的旧版只删发布包、留条目，正文不写任何下载行。GitHub 每条 release 页自动挂 `Source code (zip)` 与 `Source code (tar.gz)`，源码在那里拿，正文不重复挂链接：

```
🐳 FinshinImpact-vX.Y.Z

变化
- 条目一
- 条目二

注意
- 条目一

**Full Changelog**: https://github.com/FinshinLabs/FinshinImpact/compare/v<上一版>...vX.Y.Z
```

⚠️**删发布包不可逆**。

### prerelease 与 latest

- 预发布号一律勾 `Pre-release`。
- 正式版新发布默认勾选 `Latest`。

## 版本页同步（发布最后一步）

Release 发布完成不等于升级链生效：在线版本页是启动器与 GUI 版本检查的唯一真相。

- 主仓 workflow 随 push `main` 部署版本页与在线目录，无需手动覆盖推送。
- 闭环判据：跑 `python packaging\build.py --check`，「在线版本页」那一行显示新版本号。
- Pages 部署有延迟，读数未变稍后重跑。
