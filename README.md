# Finshin Impact

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Aiogram Version](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Project Type](https://img.shields.io/badge/project-pyproject.toml-brightgreen.svg)](pyproject.toml)
[![Changelog](https://img.shields.io/badge/changelog-CHANGELOG.md-blue.svg)](CHANGELOG.md)

> 一个基于 `Python` 和 `aiogram 3.x` 构建的异步机器人，采用模块化插件设计。
>
> *鱼神，启动！*
>
**⚠️ 破坏性变更**
- 从 **v1.0.0-alpha.3.dev1** 以前的版本更新的用户需手动整包，因为路径变化较大，以防止旧数据污染。
- 具体请看 [**v1.0.0-alpha.3.dev1 专项**](#new)
> 
> **本项目仅限 `Windows` 用户使用。**

---

## 🚀 快速开始<a id="quickstart"></a>

无需 Python、无需 Git、无命令行，五步完成：

1. **代理**：大陆用户访问 `github` 和使用 **tg 端** 机器人需 **全程** 开启代理。
2. **下载**：下最新版的 `FinshinImpact-vX.Y.Z.zip`（认准此文件名；Releases 页标着 `Source code` 的压缩包不含启动器，不要下）。
   - 🚀 [国内镜像加速（推荐）](https://gh-proxy.com/#https://github.com/lym2006/FinshinImpact/releases)：打开最新条目在 `Assets` 里下载，无需代理；
   - 📦 [GitHub Releases](https://github.com/lym2006/FinshinImpact/releases)：官方直连，需代理时走这条。
3. **解压**：解压到任意 **可写目录**（如 `D:\FinshinImpact`）。
4. **首次启动**：双击 `FinshinImpact\FinshinImpact.exe`，确认后自动安装运行环境（嵌入式 Python、依赖、浏览器内核，默认走国内镜像加速），进度窗口实时显示安装步骤与下载速率，期间保持网络畅通。
5. **创建并运行实例**：运行后先弹出「选择机器人」窗口，点「新建」填入 Bot Token 即生成专属实例文件夹 `instances\<身份码>\`（同机可建多个、并存运行）；随后管理面板弹出配置向导，填入 API Key 与主人 ID 等即开始收发消息。

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

- **桌面管理面板**: 基于 `PySide6` 的 GUI 窗口，仪表盘实时日志按语义标记。
- **功能集成**:
  -  程序打包分发，下载解压双击即用，运行环境自动安装，无需预装 Python。
  -  内置版本检测更新、配置自动创建、类型范围自动校验逻辑。
- **异步架构**: 基于 `asyncio` 和 `aiogram`，提供高并发处理能力。
- **配置向导**: 窗口内可视化编辑 `config.toml`。
- **多实例隔离**: 每个机器人独占一个身份文件夹，配置、人设、数据、日志互不干扰；同 token 双开提示"已在运行"并退出，杜绝互踩长轮询，不同 token 可同机并存。
- **自定义应用图标**: 启动器文件、管理面板窗口与任务栏图标统一，旧版用户正常升级即自动生效。
- **优雅退出**: 关闭拦截 + 确认弹窗 + 资源清理钩子统一调度，致命错误弹窗提示后安全退出，避免闪退。
- **插件化设计**: 模块位于 `src/plugins` 目录，支持动态加载，易于扩展和维护。
- **完善日志系统**: 三级日志按内容语义自动标记，异常上下文自动归集，仪表盘与日志文件各取所需。
- **Markdown 渲染**: 对话内容可渲染，阅读体验提升。

[⤴️ 返回目录](#menu)

---

## 💬 关于 AI 对话<a id="ai_chat"></a>

目前仅支持 **私聊** 使用

- **独立会话**：不同用户 **或** 不同群组中的同一用户，会话相互隔离

  > **注意**：群组中需触发关键词 **或** @机器人 **（暂不可用）**

- **消息排队**：原子级别任务锁避免多任务并发出错
- **状态更新**：自动更新状态信息（排队中、思考中、思考完成内容），**计划** 加入取消排队按钮
- **自动引用**：状态信息引用原消息，回复内容引用思考过程
- **思考过程**：仅私聊输出，群组中请使用 `/history` 命令
- **取消会话**：若思考过程中用户删除原消息，停止处理该任务，消息不计入历史，**计划** 加入取消任务按钮

  > **注意**：该功能经测试，**目前** 只在 Nekogram 生效，原版 Telegram **不生效**，其他版本未测试

- **删除判断**：若用户删除机器人发出的状态信息，机器人会在必要时重新发送
- **超时处理**：配置超时时间和判断间隔，自动清除用户记录
- **其他功能**：
  - `Markdown` 文件历史记录
  - `Markdown` 格式回复
  - 个性化定制人设（**暂不可用**）
  - 自主开关对话功能
  - 更多参见 `/help` 命令

[⤴️ 返回目录](#menu)

---

## 🛠️ 技术栈<a id="techniques"></a>

| 组件 | 版本/描述 |
| :--- | :--- |
| **语言** | `Python 3.11+` |
| **核心框架** | [`aiogram 3.x`](https://docs.aiogram.dev/) |
| **桌面 GUI** | [`PySide6`](https://www.qt.io/qt-for-python)（管理面板与仪表盘日志） |
| **依赖管理** | [`pyproject.toml`](pyproject.toml) |
| **代码规范** | [`ruff.toml`](ruff.toml) 独立配置，统一代码风格、导入排序及格式化 |
| **浏览器驱动** | `Playwright` / `chromium`（根据步骤下载） |
| **HTML 清洗** | `bleach`（XSS 防御白名单清洗） |
| **日志系统** | `logging`，强制静默第三方库噪音，增强自定义 `Logger` |

[⤴️ 返回目录](#menu)

---

## 📖 开发与维护<a id="development"></a>

- 🧭 **开发手册**（环境搭建、发布流程、更新方式）：[`docs/development.md`](docs/development.md)
- 📐 **代码规范**（注释、docstring、命名约定）：[`docs/coding-style.md`](docs/coding-style.md)，模板 [`docs/example.py`](docs/example.py)
- 📦 **打包教程**（发布原理与操作）：[`docs/packaging.md`](docs/packaging.md)
- 📝 **提交规范**（commit 格式模板）：[`.gitmessage`](.gitmessage)
- 🚀 **发布工作流**（CHANGELOG、tag、release 四件套）：[`docs/release-workflow.md`](docs/release-workflow.md)
- ⚙️ **配置模板**（全部可改项与注释）：[`assets/config.telegram.example.toml`](assets/config.telegram.example.toml)

[⤴️ 返回目录](#menu)

---

## ⬆️ 旧版迁移<a id="previous"></a>

- 从 v0.3.x 及之前升级需手动整包。请删除旧目录，重新下载解压新包，想保留的 `config.toml`、`data\`、`logs\` 先备份再放回。
- 从 v0.4.0 起，启动器本体的修复跟着自动升级走，不再需要手动整包。
- 从 v0.4.3 起，启动器升级时会自动重启换壳，请耐心等待程序自动打开，多余的 `.old` 文件会在下一次启动时自动删除。
- **v1.0.0-alpha.2 专项**：
  - 从旧版本自动升级后若双击没反应，删除 `src\bot\_managers\_settings` 文件夹即可恢复
  - 从 alpha.2 起更新无此问题
- **v1.0.0-alpha.3.dev1 专项**：所有旧版本均需手动整包，不做自动迁移。<a id="new"></a>
  - 备份旧目录根部的 `config.toml`、`data\`、`logs\`，删除旧目录后解压新包
  - 新包首次启动会弹「选择机器人」窗口，点「新建」填 Bot Token，实例资产此后落在 `instances\<身份码>\` 下
  - Bot Token 不再写进配置文件，改存实例内 `profile.json`，管理面板不显示也不可改
  - 各项配置请自行从旧文件复制填写

[⤴️ 返回目录](#menu)

---

## ❗️ 温馨提示<a id="tips"></a>

本项目目前仍处于 **测试阶段**，如遇报错或异常行为属正常现象，请勿惊慌 😊 

- **代理语义**：填写地址优先使用，留空或试不通会自动尝试系统代理与直连，全不通时提示可用的本机端口。

如需进行插件开发、查阅 API 或查看源码，请参考以下资源：
- 📖 **官方文档**：[`aiogram.dev`](https://docs.aiogram.dev/en/latest/)
- 💻 **`GitHub` 仓库**：[`aiogram`](https://github.com/aiogram/aiogram)

[⤴️ 返回目录](#menu)

---

## 📄 许可证 (`LICENSE`)<a id="license"></a>

本项目采用 MIT 许可证 - 查看 [`LICENSE`](LICENSE) 文件了解详情。

[⤴️ 返回目录](#menu)

---

Made by **lym2006**
