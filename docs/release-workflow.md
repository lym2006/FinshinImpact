# 发布工作流

覆盖一次版本从改码到上线的四件套：CHANGELOG → commit → tag → release。
本规范自 v1.0.0-alpha.1 起生效。

## 总流程（发布日按序执行）

```
功能提交若干（改动同步记 Unreleased）
  → 发布定稿提交（CHANGELOG 归段 + 版本号）
  → 构建 zip 并本地实测
  → 附注 tag 并推送
  → 发布 release
  → 版本页同步收尾
```

## CHANGELOG

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，条目一律 `- **加粗要点**：说明`。

- 分节固定，带 emoji：
  - `### 📝 Planned` / `### ✨ Added` / `### 🔧 Changed` / `### 🐛 Fixed` / `### 🗑️ Removed`
  - 破坏性变更额外加 `### ⚠️ Breaking Changes` 置顶该版本段。
- `## [Unreleased]` 恒在顶部，发布时把其中内容归入新段 `## [X.Y.Z] - YYYY-MM-DD`（日期为发布当天），Planned 段留在 Unreleased 里不过期。
- 只写关键条目，琐碎改动一笔带过或不写，加了又删的功能（净效果为零）不留任何痕迹。
- 条目正文禁用分号：首段 `- **加粗要点**：`，换行书写，每行一段，逐行 `-` 起头，注意缩进。
- 用户视角写行为，不写实现：说"坏配置不骗过验证"，不说"复验改走候选通道"。
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
- 一组提交为一个主题，不按文件凑数；同主题跨层（如消息+工具+bot）合为一组。
- 发布定稿单独一笔：`build(release): vX.Y.Z 发布定稿`，只含 CHANGELOG 归段与 pyproject 版本号。

## 构建 zip

定稿提交后本地构建，全程只构建这一次：

```powershell
python packaging\build.py
python packaging\build.py --check   # 自检：本地版本号、远端 tag、本地 zip、在线版本页
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

## 版本号（semver）

| 场景 | 升位 |
| :--- | :--- |
| 正式定版 | 1.0.0 |
| 定版前公开试用 | 预发布号 `X.Y.Z-alpha.N`（如 `1.0.0-alpha.1`），tag 与产物名全程带后缀 |
| 纯修复 | patch（1.0.0 → 1.0.1） |
| 有新功能 | minor（1.0.0 → 1.1.0） |
| 破坏性行为变更 | major（1.0.0 → 2.0.0） |

## Release

发布在 GitHub 网页端操作：进仓库 [Releases](https://github.com/lym2006/FinshinImpact/releases) → Draft a new release → 选推送上来的 tag `vX.Y.Z` → 上传 zip → 按下述格式填标题与正文 → Publish。

标题：`vX.Y.Z（重要变化，如需手动整包、引入全新操作，若无则不写）`。

正文模板：

```
📦 FinshinImpact-vX.Y.Z.zip
- 国内加速：https://gh-proxy.com/https://github.com/lym2006/FinshinImpact/releases/download/vX.Y.Z/FinshinImpact-vX.Y.Z.zip
- 官方直连：https://github.com/lym2006/FinshinImpact/releases/download/vX.Y.Z/FinshinImpact-vX.Y.Z.zip

本版变化
- 条目一（用户视角，2~5 条，从 CHANGELOG 该版本段提炼）
- 条目二

注意（仅升级路径或行为有特殊约束时写，无则整段省略）
- 只写事实与用户需要的动作，一句一条，禁口语、修辞、情绪化措辞
- 有破坏性变更时提示用户如何操作
```

## 版本页同步（发布最后一步）

Release 发布完成不等于升级链生效：在线版本页是启动器与 GUI 版本检查的唯一真相。

1. 把本地 `pyproject.toml` 覆盖到版本页仓库 `lym2006.github.io` 的 `FinshinImpact/` 目录并 push，Pages workflow 自动部署。
2. 跑 `python packaging\build.py --check`，末行「在线版本页」显示新版本号才算发布完成。

## 版本页同步

zip 上传完成不等于发布完成。在线版本页是启动器判断"有没有新版"的唯一真相，必须手动同步：

1. 把本项目 `pyproject.toml` 覆盖到版本页仓库 `lym2006.github.io` 的 `FinshinImpact/pyproject.toml`。
2. 在该仓库 `git commit` 并 `push`，其 Pages workflow 自动部署。
3. 回本项目跑 `python packaging\build.py --check`，末行「在线版本页」显示新版本号即发布闭环。

推 tag、传 zip、同步版本页三步齐了，老客户端才会在下次启动时收到升级提示。少同步版本页，用户看不到新版；zip 漏传，用户点了升级却下载失败。
