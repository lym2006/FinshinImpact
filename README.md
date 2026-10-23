# 🐳 Finshin Impact

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Aiogram Version](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Changelog](https://img.shields.io/badge/changelog-CHANGELOG.md-blue.svg)](CHANGELOG.md)

> 一个基于 `Python` 和 `aiogram 3.x` 构建的异步机器人，采用模块化插件设计。
>
> *鱼神，启动！*
>
> **本项目仅限 `Windows` 用户使用。**

**⚠️ 破坏性变更**

- 从 **v1.0.0-alpha.5.dev4** 起，对话记录改按群与私聊窗口各存一份，`records\` 下按人分开的旧文件不再读写，需用户自行处理，见 [**dev4 专项**](#a5dev4)。
- 从 **v1.0.0-alpha.5.dev3** 起，实例目录按用途分档，旧 `data\` 不再读写也不由程序删除，见 [**dev3 专项**](#a5dev3)。

---

## 🚀 快速开始<a id="quickstart"></a>

无需 Python、无需 Git、无命令行，五步完成：

1. **代理**：下载本包的 `zip` 可走国内镜像免代理。运行期连 `Telegram` 与检查更新（访问 `GitHub` API）需开代理，大陆用户建议全程开启。
2. **下载**：取最新的 `FinshinImpact-vX.Y.Z.zip`，认准这个文件名。Releases 页标着 `Source code` 的压缩包不含启动器，不要下那个。
   - 🚀 [国内镜像加速（推荐）](https://gh-proxy.com/#https://github.com/lym2006/FinshinImpact/releases)：打开最新条目在 `Assets` 里下载。
   - ⬇️ [GitHub Releases](https://github.com/lym2006/FinshinImpact/releases)：官方直连。
3. **解压**：解压到任意 **可写目录**（如 `D:\FinshinImpact`）。
4. **首次启动**：双击 `FinshinImpact\FinshinImpact.exe`，确认后自动安装运行环境（嵌入式 Python 与核心依赖，默认走国内镜像加速），进度窗口实时显示安装步骤与下载速率，期间保持网络畅通。插件依赖与浏览器内核在启用对应插件时按需安装。
5. **创建并运行实例**：运行后先弹出「选择机器人」窗口，点「新建」填入 Bot Token 即生成专属实例文件夹 `instances\<身份码>\`，同机可建多个并存运行。随后管理面板弹出配置向导，填入 API Key 与主人 ID 等即开始收发消息。

**注意**：升级会整树替换 `src\` 与 `assets\`，自定义文件 **一定不要** 放这两个目录。

---

## 📑 目录<a id="menu"></a>

- [🚀 快速开始](#quickstart)
- [✨ 功能特点](#feature)
- [💬 关于 AI 对话](#ai_chat)
- [🛠️ 技术栈](#techniques)
- [📖 开发与维护](#development)
- [⬆️ 旧版迁移](#previous)
- [❗️ 温馨提示](#tips)
- [📄 许可证 (`LICENSE`)](#license)

---

## ✨ 功能特点<a id="feature"></a>

- **桌面管理面板**: 基于 `PySide6` 的 GUI 窗口，仪表盘实时日志按内容语义标记，异常上下文自动归集。
- **免安装分发**: 下载解压双击即用，运行环境自动装好，无需预装 Python。内置版本检测更新、配置自动创建与类型范围校验。
- **异步架构**: 基于 `asyncio` 和 `aiogram`，长轮询收消息，应答走事件循环。
- **配置向导**: 窗口内可视化编辑 `config.toml`，字段带类型与范围校验。
- **多实例隔离**: 每个机器人独占一个身份文件夹，配置、人设、库、记录、日志互不干扰。同 token 双开提示"已在运行"并退出，杜绝互踩长轮询，不同 token 可同机并存。
- **优雅退出**: 关闭拦截加确认弹窗，资源清理钩子统一调度，致命错误弹窗提示后安全退出，不闪退。
- **插件化**: 对话与帮助功能由 `src/plugins` 下的插件提供，支持动态加载。「插件设置」面板勾选启用，未启用即命令消失。
- **对话记忆**: 上下文按窗口存放，长对话自动压成摘要，到期记录与模型记忆一起清。

[⤴️ 返回目录](#menu)

---

## 💬 关于 AI 对话<a id="ai_chat"></a>

- **私聊与群聊**：私聊要主人或管理员才应答，成员在私聊只收到一句门槛说明。群里要 @机器人、引用机器人的发言，或命中配置的触发词。
- **按窗口隔离会话**：一个群共用一串上下文，一个私聊窗口另起一串，同群多人同时发不互吞上文。
- **群里分清发言人**：每条正文带名字与 id 的标注，模型知道这句话是谁说的。
- **消息排队**：同一个窗口的消息排成一串依次应答，任务锁按窗口加，不并发写同一串上下文。
- **长对话自动压摘要**：上文超过约 16384 token 时，把最早的问答交给后台压成一段摘要，当轮照常回答，用户不等。
- **落盘记录**：`Markdown` 文件一群一份、一私聊一份，用 `/history` 取文件。压摘要只动模型的上文，不动记录文件。
- **到期一起清**：面板"记录保留（天）"（默认 30 天）到期后，落盘记录与模型上下文同一串一起清，不留"你看不到但机器人还记得"的历史。
- **人设**：取实例目录的 `persona.md`，没改过的副本跟着随包模板升级。换过正文会让所有人的历史一起作废。
- **权限三档**：主人、管理员、成员，对话与命令都按档放行。`/grant <用户 id>` 与 `/ungrant <用户 id>` 只有主人能使，授予跨群同一份。`/history` 与 `/clear` 要管理员以上，其他人只收到无权限提示。
- **授权能分步走**：不带 id 时先问"要授权谁"，把 id 单独发一条即完成，发 `-1` 取消。待输入只认发起命令的那个人，别人在同群发言不受干扰。这一轮没办成不终止，提示问题接着等，直到发对或发 `-1`。
- **一条答案消息**：回复引用你发的那条原消息，全程只发最终答案，不出"排队中""思考中"这类状态消息。
- **删原消息即中断**：思考期间用户删掉原消息，本轮任务停止处理，该条消息不计入历史。

  > **注意**：该功能经测试只在 Nekogram 生效，原版 Telegram 不生效，其他客户端未测。

- **保留期可调**：保留天数在面板配，扫描间隔在 `config.toml` 的 `[data] waiting`（单位小时，默认 0.5）。
- **其他**：回复按纯文本发送，模型给的 `Markdown` 标记不渲染。命令清单与用法见 `/help`。

[⤴️ 返回目录](#menu)

---

## 🛠️ 技术栈<a id="techniques"></a>

| 组件 | 版本/描述 |
| :--- | :--- |
| **语言** | `Python 3.11+` |
| **核心框架** | [`aiogram 3.x`](https://docs.aiogram.dev/) |
| **桌面 GUI** | [`PySide6`](https://www.qt.io/qt-for-python)（管理面板与仪表盘日志） |
| **存储** | `SQLite`（`aiosqlite`，按实例分库，WAL 模式） |
| **依赖管理** | [`pyproject.toml`](pyproject.toml) |
| **代码规范** | [`ruff.toml`](ruff.toml) 独立配置，统一代码风格、导入排序及格式化 |
| **日志系统** | `logging`，强制静默第三方库噪音，增强自定义 `Logger` |

[⤴️ 返回目录](#menu)

---

## 📖 开发与维护<a id="development"></a>

- 🧭 **开发手册**（环境搭建、新增插件流程、发布流程）：[`docs/development.md`](docs/development.md)
- 📐 **代码规范**（注释、docstring、命名约定）：[`docs/coding-style.md`](docs/coding-style.md)，模板 [`docs/example.py`](docs/example.py)
- 🔧 **打包教程**（发布原理与操作）：[`docs/packaging.md`](docs/packaging.md)
- 📝 **提交规范**（commit 格式模板）：[`.gitmessage`](.gitmessage)
- 🚀 **发布工作流**（CHANGELOG、commit、tag、release 四件套）：[`docs/release-workflow.md`](docs/release-workflow.md)
- 📚 **工程经验**（实测踩坑与验证方法，按使用场景分册）：[`docs/lessons/README.md`](docs/lessons/README.md)
- 🧩 **插件清单模板**（`plugin.toml` 字段与示例）：[`assets/plugin.example.toml`](assets/plugin.example.toml)
- ⚙️ **配置字段表**（全部可改项、默认值与平台归属）：单源在 [`src/core/domain/config/`](src/core/domain/config/)

[⤴️ 返回目录](#menu)

---

## ⬆️ 旧版迁移<a id="previous"></a>

- 从 **v1.0.0-alpha.5.dev4** 起，对话记录改按群与私聊窗口各存一份。<a id="a5dev4"></a>
  - 一名群一份叫 `instances\<身份码>\records\tg.g100123.md`，一个私聊窗口一份叫 `tg.u456.md`，同群成员的问答写进同一个文件。
  - `records\` 下按人分开的旧文件（如 `tg.g100123.456.md`）不再读写，程序不会自动合并也不会改名，确认不要了就手动删。
  - 库里同窗口的上下文照常接着用，旧文件的去留不影响正在聊的会话。
- 从 **v1.0.0-alpha.5.dev3** 起，实例目录按用途分档，旧 `data\` 不再读写，程序也不替用户删。<a id="a5dev3"></a>
  - 库文件与迁移备份放 `db\`，对话记录放 `records\`，帮助图与它的指纹放 `help\`。
  - 想留下旧对话记录，把 `data\ai_records\` 下的 `.md` 整批挪进 `records\`，文件名不用改。
  - 挪完或不想留之后，`data\` 整目录由用户自行删除，留着不影响新版本运行。
  - 帮助图会在新位置重新生成，旧 `data\help.png` 不必搬。
- 从 **v1.0.0-alpha.5.dev1** 起，标识分隔符统一为点号，不做自动迁移。<a id="a5dev1"></a>
  - 实例文件夹名改用点号分段，旧目录如 `instances\tg-7558512722` 需手工改名为 `instances\tg.7558512722`，不改名则「选择机器人」窗口列不出这个实例。
  - 记录文件名的口径此后又被 dev4 改为按窗口存，dev1 那套主体键改名指引不再适用，旧文件一律按 dev4 段处理。
  - 旧记录不改名也能正常收发消息，只是旧内容读不到，新会话另起文件续写。
- 从 **v1.0.0-alpha.4** 及更早版本走自动升级上来的，首次启动会刷一段 `uv pip uninstall` 用法报错并弹「依赖安装失败」。那是旧启动器拿着已作废的清理清单空跑，再双击一次即换入新启动器正常启动。
- 从 **v1.0.0-alpha.3.dev1** 之前的版本升级一律手动整包，不做自动迁移。
  - 先备份旧目录根部的 `config.toml`、`data\`、`logs\`，删除旧目录后解压新包。这里的 `data\` 指旧版本根目录那个，与实例内的 `db\`、`records\` 无关。
  - 新包首次启动弹「选择机器人」窗口，点「新建」填 Bot Token，实例资产此后落在 `instances\<身份码>\` 下。
  - Bot Token 不再写进配置文件，改存实例内 `profile.json`，管理面板不显示也不可改。
  - 各项配置请自行从旧文件复制填写。
- **v1.0.0-alpha.2** 及更早、**v0.3.x** 及更早的旧版本一律手动整包：删旧目录、重新下载解压，想留的 `config.toml`、`data\`、`logs\` 先备份再放回。
- 从 **v0.4.3** 起，启动器升级时会自动重启换壳，等它自己打开即可。启动器本体的修复从 **v0.4.0** 起跟着自动升级走，不再需要手动整包。

[⤴️ 返回目录](#menu)

---

## ❗️ 温馨提示<a id="tips"></a>

本项目仍在测试阶段。遇到报错请连同 `instances\<身份码>\logs\` 里的日志一起反馈。

- **代理语义**：默认自动模式，填了地址优先用它，不通会自动尝试系统代理与直连。代理软件开 TUN 时直连那一路也会被吸进同一进程。
- **强制模式**：面板「代理模式」可切为仅配置代理 / 仅系统代理 / 仅直连，只校验选定那一路。
- **全不通时**：报错里给出可用的本机端口。

插件开发与源码查阅入口：

- 📖 **`aiogram` 官方文档**：[`aiogram.dev`](https://docs.aiogram.dev/en/latest/)
- 💻 **`aiogram` 仓库**：[`github.com/aiogram/aiogram`](https://github.com/aiogram/aiogram)

[⤴️ 返回目录](#menu)

---

## 📄 许可证 (`LICENSE`)<a id="license"></a>

本项目采用 MIT 许可证，查看 [`LICENSE`](LICENSE) 文件了解详情。

[⤴️ 返回目录](#menu)

---

Made by **lym2006**
