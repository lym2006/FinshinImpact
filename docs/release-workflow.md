# 发布工作流

覆盖一次版本从改码到上线的四件套：CHANGELOG → commit → tag → release。
0.3.0 以前的历史不追溯，本规范自 v0.5.1 起生效。

## 总流程（发布日按序执行）

```
功能提交若干（改动同步记 Unreleased）
  → 发布定稿提交（CHANGELOG 归段 + 版本号）
  → 附注 tag
  → 构建 zip
  → 发布 release
```

## CHANGELOG

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，条目一律 `- **加粗要点**：说明`。

- 分节固定四个，带 emoji：`### ✨ Added` / `### 🔧 Changed` / `### 🐛 Fixed` / `### 📝 Planned`；破坏性变更加 `### ⚠️ Breaking Changes` 置顶该版本段。
- `## [Unreleased]` 恒在顶部；发布时把其中内容归入新段 `## [X.Y.Z] - YYYY-MM-DD`（日期为发布当天），Planned 段留在 Unreleased 里不过期。
- 只写关键条目，琐碎改动一笔带过或不写；加了又删的功能（净效果为零）不留任何痕迹。
- 用户视角写行为，不写实现：说"坏配置不再能骗过验证"，不说"复验改走候选通道"。
- 简洁优先：一句一个事实，删除修饰、比喻与连接性废话；不堆书面腔也不刻意口语，能砍的字一律砍。

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
- 一组提交为一个主题，不按文件凑数；同主题跨层（如消息+工具+bot）合为一组。
- 发布定稿单独一笔：`build(release): vX.Y.Z 发布定稿`，只含 CHANGELOG 归段与 pyproject 版本号。

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
| 纯修复 | patch（0.5.0 → 0.5.1） |
| 有新功能 | minor（0.5.1 → 0.6.0） |
| 破坏性行为变更 | 0.x 内仍走 minor，但 CHANGELOG 记 Breaking、release 正文加"注意"段 |
| 正式定版 | 1.0.0 |

## Release

发布在 GitHub 网页端操作：进仓库 [Releases](https://github.com/lym2006/TelegramBot/releases) → Draft a new release → 选推送上来的 tag `vX.Y.Z` → 上传 zip → 按下述格式填标题与正文 → Publish。

标题：`vX.Y.Z（重要变化，如第一个 xxx 版本，需手动操作，若无则不写）`。

正文模板：

```
📦 TelegramBot-vX.Y.Z.zip
- 国内加速：https://gh-proxy.com/https://github.com/lym2006/TelegramBot/releases/download/vX.Y.Z/TelegramBot-vX.Y.Z.zip
- 官方直连：https://github.com/lym2006/TelegramBot/releases/download/vX.Y.Z/TelegramBot-vX.Y.Z.zip

本版变化
- 条目一（用户视角，2~5 条，从 CHANGELOG 该版本段提炼）
- 条目二

注意（仅升级路径或行为有特殊约束时写，无则整段省略）
- 只写事实与用户需要的动作，一句一条，禁口语、修辞、情绪化措辞
- 有破坏性变更时提示用户如何操作
```
