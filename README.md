# 🐳 Finshin Impact

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Aiogram Version](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Changelog](https://img.shields.io/badge/changelog-CHANGELOG.md-blue.svg)](CHANGELOG.md)

> 基于 `Python` 与 `aiogram 3.x` 的异步 Telegram 机器人，功能由插件提供，带 `PySide6` 桌面管理面板。
>
> *鱼神，启动！*
>
> **仅限 `Windows` 用户使用。**

升级前先看 [旧版迁移](#previous)，破坏性变更和要手动处理的文件都在那一节。

---

## 🚀 快速开始<a id="quickstart"></a>

1. **代理**：下载走国内镜像可免代理，运行期连 `Telegram` 和检查更新需开代理。
2. **下载**：取最新的 `FinshinImpact-vX.Y.Z.zip`，别下 `Source code`（不含启动器）。[国内镜像](https://gh-proxy.com/#https://github.com/lym2006/FinshinImpact/releases) ｜ [Releases](https://github.com/lym2006/FinshinImpact/releases)。
3. **解压**：任意可写目录，如 `D:\FinshinImpact`。
4. **首启**：双击 `FinshinImpact\FinshinImpact.exe`，自动装好运行环境，期间保持联网。插件依赖与浏览器内核在启用该插件时按需安装。
5. **建实例**：「选择机器人」点「新建」填 Bot Token，再经配置向导填 API Key 与主人 ID 即开始收发。同机可并存多个实例。

**注意**：升级会整树替换 `src\` 与 `assets\`，自定义文件别放这两处。

---

## 📑 目录<a id="menu"></a>

- [🚀 快速开始](#quickstart)
- [✨ 功能特点](#feature)
- [💬 关于 AI 对话](#ai_chat)
- [🛠️ 技术栈](#techniques)
- [📖 开发与维护](#development)
- [⬆️ 旧版迁移](#previous)
- [❗️ 温馨提示](#tips)
- [📄 许可证](#license)

---

## ✨ 功能特点<a id="feature"></a>

- **免安装分发**：解压双击即用，运行环境与依赖自动装好，内置版本检测更新与配置校验。
- **桌面管理面板**：日志按内容语义标记、异常自动归集，配置、代理模式、插件启用与网络诊断都在窗口里改。
- **多实例隔离**：每个机器人独占一个实例目录，配置、人设、库、记录、日志互不干扰。同 token 双开提示"机器人已在运行"并退出。
- **权限三档**：主人、管理员、成员，对对话和命令全局生效。`/grant` 与 `/ungrant` 只有主人能使，授予跨群同一份。
- **插件化**：对话与帮助由 `src/plugins` 下的插件提供，面板勾选启用，未启用即不响应。
- **对话记忆**：上下文按窗口存进 `SQLite`，长对话自动压成摘要，到期记录与模型记忆一起清。

[⤴️ 返回目录](#menu)

---

## 💬 关于 AI 对话<a id="ai_chat"></a>

- **谁能聊**：私聊要主人或管理员，成员只收到一句门槛说明。群里要 @机器人、引用机器人发言，或命中配置的触发词。
- **按窗口隔离**：一个群共用一串上下文，一个私聊窗口另起一串，多人同发不互吞。每条正文带名字与 id。
- **长对话压摘要**：上文超过约 16384 token 时，最早的问答交给后台压成摘要，当轮照常回答。
- **记录与到期**：`Markdown` 记录一群一份、一私聊一份，用 `/history` 取文件。面板"记录保留（天）"到期后，记录与模型上下文同一串一起清。
- **人设**：取实例目录的 `persona/persona.md`，没改过的正文跟着随包模板升级。换正文或换主人会让所有人的历史与记录文件当场作废，要留存先自行备份。
- **人设什么时候生效**：面板里的"编辑人设""从文件重新加载""用模板覆盖"都开两栏比对，选一份点确认即当场写回文件并换正文。在外面手改文件不会自动生效，启动时会弹同一个比对窗让你选。
- **授权能分步**：`/grant` 不带 id 时先问"要授权谁"，单发一条 id 即完成，发 `-1` 取消，只认发起命令的那个人。
- **连发多图算一条**：同一人在同一会话连着发的图并成一条处理，一轮上传只回一次，不再逐张应答。
- **只发一条答案**：回复引用原消息，不出"排队中""思考中"这类状态消息。按纯文本发送，模型的 `Markdown` 标记不渲染。
- **删原消息即跳过**：开始处理前先探一次，原消息已删除就不应答、不计入历史。

[⤴️ 返回目录](#menu)

---

## 🛠️ 技术栈<a id="techniques"></a>

| 组件 | 版本/描述 |
| :--- | :--- |
| **语言** | `Python 3.11+`，`asyncio` + `aiogram 3.x` 长轮询 |
| **桌面 GUI** | [`PySide6`](https://www.qt.io/qt-for-python)（管理面板与仪表盘日志） |
| **存储** | `SQLite`（`aiosqlite`，按实例分库，WAL 模式） |
| **依赖与规范** | [`pyproject.toml`](pyproject.toml)、[`ruff.toml`](ruff.toml) |

[⤴️ 返回目录](#menu)

---

## 📖 开发与维护<a id="development"></a>

- 🤖 **先用规范喂工具**：动手写码或改文档前，把 [`docs/coding-style.md`](docs/coding-style.md)、[`docs/development.md`](docs/development.md) 交给 AI 编码工具（或写进项目规则文件），改完按 [`docs/style-checker.md`](docs/style-checker.md) 自查。
- 🧭 **开发手册**（环境搭建、新增插件、发布流程）：[`docs/development.md`](docs/development.md)，代码规范：[`docs/coding-style.md`](docs/coding-style.md)，检查工具与回归用例：[`docs/style-checker.md`](docs/style-checker.md)、[`docs/testing.md`](docs/testing.md)
- 🚀 **发布工作流与打包**：[`docs/release-workflow.md`](docs/release-workflow.md)、[`docs/packaging.md`](docs/packaging.md)，commit 模板 [`.gitmessage`](.gitmessage)
- 📚 **工程经验**（实测踩坑与验证方法）：[`docs/lessons/README.md`](docs/lessons/README.md)
- 🧩 **插件清单模板**：[`assets/plugin.example.toml`](assets/plugin.example.toml)，配置字段表单源在 [`src/core/domain/config/`](src/core/domain/config/)

[⤴️ 返回目录](#menu)

---

## ⬆️ 旧版迁移<a id="previous"></a>

- **v1.0.0-alpha.5**：从 alpha.4 升上来要动手四处，换人设模板还会清历史。
  - 实例目录改名：分隔符统一为点号，`instances\tg-7558512722` 改成 `instances\tg.7558512722`，不改名列不出该实例。
  - 旧 `data\` 目录：库进 `db\`、记录进 `records\`、帮助图进 `help\`，程序不动也不删旧目录。要留记录就把 `data\ai_records\` 的 `.md` 挪进 `records\`，文件名不用改，之后自行删掉 `data\`。
  - 旧对话记录：记录改按窗口存，一群一份 `records\tg.g100123.md`，一私聊一份。按人分的旧文件不再读写，要留自行合并，不要的手动删。
  - 面板保留期：项名换成"记录保留（天）"，默认 30 天，升级后重看一眼填的值。
  - 历史作废：没改动过 `persona.md` 的实例，内置模板换版后下一条消息清空记录与上下文，改过的不受影响。
- **v1.0.0-alpha.4 及之前**：自动升级过来首次启动会刷一段 `uv pip uninstall` 报错并弹「依赖安装失败」，属旧启动器拿着作废的清理清单空跑，再双击一次即正常。
- **更早的旧装机**：连不上自动升级链，只能手动整包。先备份根目录 `config.toml` 与 `instances\`，删旧目录再解压新包，缺的配置按上面「建实例」重填一遍。

[⤴️ 返回目录](#menu)

---

## ❗️ 温馨提示<a id="tips"></a>

仍在测试阶段，遇到报错请连同 `instances\<身份码>\logs\` 一起反馈。

- **代理**：默认自动模式，填了地址优先用它，不通会自动尝试系统代理与直连。面板「代理模式」可强制仅配置代理 / 仅系统代理 / 仅直连，全不通时报错里给出可用的本机端口。
- 📖 **`aiogram` 文档**：[`aiogram.dev`](https://docs.aiogram.dev/en/latest/)

[⤴️ 返回目录](#menu)

---

## 📄 许可证<a id="license"></a>

MIT，详见 [`LICENSE`](LICENSE)。

---

Made by **lym2006**
