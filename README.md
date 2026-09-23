# Fool's Telegram Bot

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Aiogram Version](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Project Type](https://img.shields.io/badge/project-pyproject.toml-brightgreen.svg)](pyproject.toml)
[![Changelog](https://img.shields.io/badge/changelog-CHANGELOG.md-blue.svg)](CHANGELOG.md)

> 一个基于 `Python` 和 `aiogram 3.x` 构建的异步 Telegram 机器人，采用模块化插件设计。
>
> **本项目仅限 `Windows` 用户使用。**
>
> ❗️ **v0.3.1 升级须知（破坏性变更）**：
> - **GUI 桌面化**：程序入口从纯控制台变为 `PySide6` 桌面窗口，日志、配置修改、关闭确认全部在窗口内完成。
> - **停止方式变更**：关闭窗口并在弹窗确认即可安全退出，不再使用 `Ctrl + C`。
> - **配置可视化**：无需手动编辑 `config.toml`，窗口内「修改配置」即可，类型与连通性当场校验。
> - **启动方式变更**：程序打包，功能集成。

---

## 🚀 快速开始

无需 Python、无需 Git、无命令行，五步完成：

1. **代理**：大陆用户访问 `github` 和使用机器人需 **全程** 开启代理。
2. **下载**：二选一，下最新版的 `TelegramBot-vX.Y.Z.zip`（认准此文件名；Releases 页标着 `Source code` 的压缩包不含启动器，不要下）。
   - 🚀 [蓝奏云备用（国内推荐）](https://wwbgy.lanzoub.com/b0pnwooed)，页面顶部输入访问密码 `5rp0` 后点击下载；
   - 📦 [GitHub Releases](https://github.com/lym2006/TelegramBot/releases)，打开最新条目在 `Assets` 里下载。
3. **解压**：解压到任意 **可写目录**（如 `D:\TelegramBot`）。
4. **首次启动**：双击 `TelegramBot\TelegramBot.exe`，确认后自动安装运行环境（嵌入式 Python、依赖、浏览器内核，默认走国内镜像加速），进度窗口实时显示安装步骤与下载速率，期间保持网络畅通。中途出现红色报错无需处理——镜像源失效时程序会自动换源重试，窗口会打印 `换源重试` 进度提示。
5. **配置**：完成后管理面板弹出配置向导，填入 `telegram_token` 保存即开始收发消息（`config.toml` 自动生成，无需手编）。

---

## 📑 目录

- [🚀 快速开始](#-快速开始)
- [✨ 功能特点](#-功能特点)
- [💬 关于 AI 对话](#-关于-ai-对话)
- [🛠️ 技术栈](#️-技术栈)
- [📦 开发版](#-开发版)
- [🔄 更新版本](#-更新版本)
- [❗️ 温馨提示](#️-温馨提示)
- [📄 许可证 (`LICENSE`)](#-许可证-license)

---

## ✨ 功能特点

- **桌面管理面板**: 基于 `PySide6` 的 GUI 窗口，仪表盘实时日志按语义标记。
- **功能集成**:
  -  程序打包分发，下载解压双击即用，运行环境自动安装，无需预装 Python。
  -  内置版本检测更新、配置自动创建、类型范围自动校验逻辑。
- **异步架构**: 基于 `asyncio` 和 `aiogram`，提供高并发处理能力。
- **配置向导**: 窗口内可视化编辑 `config.toml`。
- **优雅退出**: 关闭拦截 + 确认弹窗 + 资源清理钩子统一调度，致命错误弹窗提示后安全退出，避免闪退。
- **插件化设计**: 模块位于 `src/plugins` 目录，支持动态加载，易于扩展和维护。
- **完善日志系统**: 三级日志按内容语义自动标记，异常上下文自动归集，仪表盘与日志文件各取所需。
- **Markdown 渲染**: 对话内容可渲染，阅读体验提升。

---

## 💬 关于 AI 对话

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

[⤴️ 返回目录](#-目录)

---

## 🛠️ 技术栈

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

[⤴️ 返回目录](#-目录)

---

## 📦 开发版

1. 安装 `Python 3.11+`（勾选 Add to PATH）
2. 下载本仓库源码并解压，在项目根目录创建虚拟环境：`python -m venv .venv`
3. 激活虚拟环境：`.venv\Scripts\activate`
4. 安装依赖与开发工具：`pip install -e ".[dev]"`（可自行配置镜像源）
5. 安装 Playwright 浏览器内核：`playwright install chromium`
6. 启动：`python -m bot`，管理面板窗口即出现
7. 首次运行自动生成 `config.toml` 并弹出配置向导，填入配置即完成初始化（无需手编文件）

<details>
<summary><b>发布流程（维护者）</b></summary>

1. `pyproject.toml` 递增版本号，`CHANGELOG` 定稿，打 `git tag vX.Y.Z` 并推送；
2. GitHub Release 上传发布物 `TelegramBot-vX.Y.Z.zip`（源码 + 启动器，不含 `.venv`）；
3. 手动把 `pyproject.toml` 覆盖到版本页仓库（`lym2006.github.io/TelegramBot`）并 `push`，其 Pages workflow 自动部署，在线版本号即生效；
4. 用户下次启动时，GUI 版本检查命中新版本，启动器自动完成升级。

</details>

[⤴️ 返回目录](#-目录)

---

## 🔄 更新版本

- **「检查更新」按钮**：两种版本行为一致，仅比对在线版本号并弹窗提示是否有新版，**不会** 替你更新。
- **开发版更新方式**：手动拉取新代码（`git pull` 或下载源码覆盖），若依赖有变动，重跑[📦 开发版](#-开发版)的 `pip` 安装命令同步。
- **打包版更新方式**：启动器每次拉起主程序前自动比对版本，弹窗确认后完成下载升级，用户配置、数据与日志一律保留。

[⤴️ 返回目录](#-目录)

---

## ❗️ 温馨提示

本项目目前仍处于 **测试阶段**，如遇报错或异常行为属正常现象，请勿惊慌 😊 

- **代理语义**：填写地址优先使用；留空或试不通会自动尝试系统代理与直连，全不通时提示可用的本机端口，经你确认才采用，程序绝不擅自使用。

如需进行插件开发、查阅 API 或查看源码，请参考以下资源：
- 📖 **官方文档**：[`aiogram.dev`](https://docs.aiogram.dev/en/latest/)
- 💻 **`GitHub` 仓库**：[`aiogram`](https://github.com/aiogram/aiogram)

维护者资源：
- 📦 **打包教程**（发布原理与操作）：[`packaging/packaging.md`](packaging/packaging.md)
- 📝 **提交规范**（commit 格式模板）：[`.gitmessage`](.gitmessage)
- ⚙️ **配置模板**（全部可改项与注释）：[`config.example.toml`](config.example.toml)

[⤴️ 返回目录](#-目录)

---

## 📄 许可证 (`LICENSE`)

本项目采用 MIT 许可证 - 查看 [`LICENSE`](LICENSE) 文件了解详情。

---
Made by **lym2006**
