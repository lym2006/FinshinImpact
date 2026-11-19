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
2. **下载**：取最新的 `FinshinImpact-vX.Y.Z.zip`，别下 `Source code`（不含启动器）。[国内镜像](https://gh-proxy.com/#https://github.com/FinshinLabs/FinshinImpact/releases) ｜ [Releases](https://github.com/FinshinLabs/FinshinImpact/releases)。
3. **解压**：任意可写目录，如 `D:\FinshinImpact`。
4. **首启**：双击 `FinshinImpact\FinshinImpact.exe`，自动装好运行环境，期间保持联网。启用插件的依赖与浏览器内核在每次启动前的结算里一并装上。
5. **建实例**：「选择机器人」点「新建」。平台下拉只列本机装过的平台，没装过的先装再建。填 Bot Token，再经配置向导填 API Key 与主人 ID 即开始收发。同机可并存多个实例。

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
- **平台组件**：新建机器人那一步的平台下拉右侧有「管理平台组件」，逐只看本机版本与在线版本，给安装与卸载。展开「查看历史版本」挑一版旧版装上即回退，展开「本机安装包」看这台机器已下过哪几版件。在线装那只要走 GitHub，过程保持联网。
- **平台组件的卸载约束**：先删掉那个平台的实例才能卸适配器。
- **多实例隔离**：每个机器人独占一个实例目录，配置、人设、库、记录、日志互不干扰。同 token 双开提示"机器人已在运行"并退出。
- **权限三档**：主人、管理员、成员，对对话和命令全局生效。`/grant` 与 `/ungrant` 只有主人能使，授予跨群同一份。
- **插件化**：对话与帮助由 `src/bundled` 下的插件提供，面板勾选启用，未启用即不响应。

[⤴️ 返回目录](#menu)

---

## 💬 关于 AI 对话<a id="ai_chat"></a>

- **谁能聊**：私聊要主人或管理员，成员只收到一句门槛说明。群里要 @机器人、引用机器人发言，或命中配置的触发词。
- **按窗口隔离**：一个群共用一串上下文，一个私聊窗口另起一串，多人同发不互吞。每条正文带名字与 id。
- **长对话压摘要**：上文超过约 16384 token 时，最早的问答交给后台压成摘要，当轮照常回答。
- **记录与到期**：`Markdown` 记录一群一份、一私聊一份，用 `/history` 取文件。面板"记录保留（天）"到期后，记录与模型上下文同一串一起清。
- **人设**：取实例目录的 `persona/persona.md`，没改过的正文跟着内置模板升级。换正文或换主人会让所有人的历史与记录文件当场作废，要留存先自行备份。
- **人设什么时候生效**：面板里改人设都开两栏比对，选一份点确认即当场写回文件。在外面手改文件不会自动生效，启动时会弹同一个比对窗让你选。
- **只发一条答案**：回复引用原消息，不出"排队中""思考中"这类状态消息。按纯文本发送，模型的 `Markdown` 标记不渲染。
- **多图算一条**：同一人在同一会话连着发的图并成一条处理，一轮上传只回一次。原消息在开始处理前已被删除就不应答、不计入历史。

[⤴️ 返回目录](#menu)

---

## 🛠️ 技术栈<a id="techniques"></a>

| 组件 | 版本/描述 |
| :--- | :--- |
| **语言** | `Python 3.11+`，全链路 `asyncio` |
| **机器人连接** | `aiogram 3.x` 长轮询，由独立适配器仓提供 |
| **桌面面板** | [`PySide6`](https://www.qt.io/qt-for-python)（管理面板与仪表盘日志） |
| **存储** | `SQLite`（按实例分库，WAL 模式） |

[⤴️ 返回目录](#menu)

---

## 📖 开发与维护<a id="development"></a>

- 🤖 **先用规范喂工具**：动手写码或改文档前，把 [`docs/coding-style.md`](docs/coding-style.md)、[`docs/development.md`](docs/development.md) 交给 AI 编码工具（或写进项目规则文件），改完按 [`docs/style-checker.md`](docs/style-checker.md) 自查。
- 🧭 **开发手册**（环境搭建、新增插件、发布流程）：[`docs/development.md`](docs/development.md)，代码规范：[`docs/coding-style.md`](docs/coding-style.md)，检查工具与回归用例：[`docs/style-checker.md`](docs/style-checker.md)、[`docs/testing.md`](docs/testing.md)
- 🚀 **发布工作流与打包**：[`docs/release-workflow.md`](docs/release-workflow.md)、[`docs/packaging.md`](docs/packaging.md)，commit 模板 [`.gitmessage`](.gitmessage)
- 📚 **工程经验**（实测踩坑与验证方法）：[`docs/lessons/README.md`](docs/lessons/README.md)
- 🧩 **插件清单模板**：[`assets/plugin.example.toml`](assets/plugin.example.toml)，配置字段表单源在接口包的 `domain/config/`
- 🔌 **平台适配器**：每只平台一只独立仓，Telegram 的那只在 [`FinshinAdapterTG`](https://github.com/FinshinLabs/FinshinAdapterTG)，开发时 clone 进 `finshin/adapter/` 下的一个目录并同步环境即被认出来。新增平台照 [`docs/development.md`](docs/development.md) 的「新增平台适配器」一节做，本体代码不用改。
- 📦 **接口包**：本体与插件、适配器共用的形状在独立仓 [`FinshinSDK`](https://github.com/FinshinLabs/FinshinSDK)，开发时 clone 进 `finshin/sdk`，手顺见 [`docs/development.md`](docs/development.md) 的「挂载子仓」一节

[⤴️ 返回目录](#menu)

---

## ⬆️ 旧版迁移<a id="previous"></a>

- **v1.0.0-alpha.7.dev6**：
  - 仓库搬到组织 `FinshinLabs`，旧包里的版本页地址已取不到（实测旧 Pages 返回 404）：手动下新包覆盖解压即可，配置、记录、库与日志都在 `instances\`，不受影响。
- **v1.0.0-alpha.7.dev5**：
  - 只用发布包的：解压件不再自带平台适配器，首次建实例要先在平台下拉右侧「管理平台组件」里在线装一只，装的过程保持联网。已有实例的配置、记录与库都不动。
  - 自己写过插件的人才要动：`plugin.toml` 里 `deps` 那一行搬到同目录 `pyproject.toml` 的 `[project].dependencies`，缺这份文件那份插件整份不认。逐项改法见 `docs/development.md` 的「从 dev4 及更早的写法改过来」。
- **v1.0.0-alpha.7.dev4**：
  - 自己写过插件或适配器的人才要动：要改入口写法、取用来源和动作名。逐项改法见 `docs/development.md` 的「从 dev4 及更早的写法改过来」。
  - 只用发布包的：什么都不用改，`plugin.toml` 与库、记录结构都没动。
  - 启动失败现在当场弹一句人话（平台没装、要的接口版本比本机新、引导段炸掉），不再只留一张走表的启动卡。
- **v1.0.0-alpha.7.dev1 与 dev2**：
  - 启动时不再弹"同步重建环境"，多余包留在盘上，要清就去选窗「环境维护」手动同步。
  - 插件目录放进项目根的 `finshin/plugin\` 即被认出来，与内置重名的那份不放行。
  - 没改动过人设正文的实例自动跟新版模板，升级后第一条消息清空上下文与 `records\` 记录，要留存先自行备份。改过的不受影响。
  - 老库里的空列下次启动自动抹掉，抹之前整库备份到 `db\backups\`，不用动手。
  - 插件清单里的 `core` 与 `order` 两个键不再读取，清单文件不用改，照常起。
- **v1.0.0-alpha.5 与 alpha.6**：
  - 实例目录分隔符统一成点号，`instances\tg-<id>` 要改成 `instances\tg.<id>`，不改名列不出该实例。
  - 库进 `db\`、记录进 `records\`、帮助图进 `help\`，程序不动也不删旧 `data\`。要留记录就把 `data\ai_records\` 的 `.md` 挪进 `records\`，之后自行删掉 `data\`。
  - 记录改按窗口存，一群一份、一私聊一份。按人分的旧文件不再读写，要留自行合并。
  - 授权名单改按用户在本平台的 id 记，上一版存的名单不再命中，主人要重新 `/grant` 一遍。
  - 人设文件搬进 `persona\`，根目录旧的 `persona.md` 与 `.persona.base` 不再被读取。自定义正文要自己挪成 `persona\persona.md`。
  - 面板撤掉"超时（秒）"与"全局设置"整页，`config.toml` 里留下的 `[global]` 段不再被读取，下次保存配置即写掉。
- **v1.0.0-alpha.4 及更早**：自动升级过来首次启动会刷一段 `uv pip uninstall` 报错并弹「依赖安装失败」，属旧启动器拿着作废的清理清单空跑，再双击一次即正常。更早的旧装机连不上自动升级链，只能手动整包：先备份根目录 `config.toml` 与 `instances\`，删旧目录再解压新包，缺的配置按上面「建实例」重填一遍。

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
