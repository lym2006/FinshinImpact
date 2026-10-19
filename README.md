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
> ❗️ **v0.3.0 升级须知（破坏性变更）**：
> - **GUI 桌面化**：程序入口从纯控制台变为 `PySide6` 桌面窗口，日志、配置修改、关闭确认全部在窗口内完成。
> - **停止方式变更**：关闭窗口并在弹窗确认即可安全退出，不再使用 `Ctrl + C`。
> - **配置可视化**：无需手动编辑 `config.toml`，窗口内「修改配置」即可，类型与连通性当场校验。

---

## 📑 目录

- [✨ 功能特点](#-功能特点)
- [💬 关于 AI 对话](#-关于-ai-对话)
- [🛠️ 技术栈](#️-技术栈)
- [🚀 快速开始](#-快速开始)
- [🔄 更新版本](#-更新版本)
- [❗️ 温馨提示](#️-温馨提示)
- [📄 许可证 (`LICENSE`)](#-许可证-license)

---

## ✨ 功能特点

- **一键安装运行**: 打包版双击即用，启动器自动安装运行环境与浏览器内核、启动时自动更新；开发版见[快速开始](#-快速开始)。
- **异步架构**: 基于 `asyncio` 和 `aiogram`，提供高并发处理能力。
- **桌面管理面板**: 基于 `PySide6` 的 GUI 窗口，仪表盘实时日志按语义标记，一目了然。
- **配置向导**: 窗口内可视化编辑 `config.toml`，保存前校验并二次确认；配置出错时强制向导标红出错项，改对即自动重启服务。校验含类型与数值区间（温度、超时等越界当场拦截），加载校验期间编辑入口自动锁止，杜绝误写模板值覆盖配置。连通性按 `配置代理 → 系统代理 → 直连` 三级解析，先通者生效并在日志标注生效通道与耗时；代理留空即自动模式。三级全不通时额外探测本机常用代理端口，实测可通的仅**提示**你确认后填入，程序不会自动采用。
- **优雅退出**: 关闭拦截 + 确认弹窗 + 资源清理钩子统一调度，致命错误弹窗提示后安全退出，避免闪退。
- **插件化设计**: 功能模块位于 `src/plugins` 目录下，支持动态加载，易于扩展和维护。
- **完善日志**: 集成 `logging` 模块，支持控制台输出与文件 `Rotating` ，文件默认开启详细报错。
- **浏览器自动化**: 使用 `Playwright` 实现异步处理。
- **启动自动检测**: 启动机器人自动检测是否更新了新配置项并提醒用户在 `config.toml` 中填写，自动检测是否有新版本。
- **Markdown 安全渲染**: 对话内容渲染，进行白名单清洗，防止恶意脚本注入。
- **动态尺寸计算**: 图片尺寸计算基于字体本身的数据，而非硬编码，提升渲染适配性。
- **全局缓存**: 内存缓存配置、黑名单，大幅减少高频磁盘 `I/O` 开销。

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

## 🚀 快速开始

### 开发版（当前）

1. 安装 `Python 3.11+`（勾选 Add to PATH）
2. 下载本仓库源码并解压，在项目根目录创建虚拟环境：`python -m venv .venv`
3. 激活虚拟环境：`.venv\Scripts\activate`
4. 安装依赖与开发工具：`pip install -e ".[dev]"`
5. 安装 Playwright 浏览器内核：`playwright install chromium`
6. 复制 `config.example.toml` 为 `config.toml` 并填写 `telegram_token`（其余配置可在 GUI 内改）
7. 启动：`python -m bot`，管理面板窗口即出现

### 打包版（规划中，方案已定）

下载 Release 压缩包解压，双击 `TelegramBot.exe`：首次运行自动安装嵌入式 Python 环境、依赖与浏览器内核，之后启动时自动检查并应用更新。无需 Python、无需 Git、无命令行。

**发布流程（维护者）**：
1. `pyproject.toml` 递增版本号，CHANGELOG 定稿，打 `git tag vX.Y.Z` 并推送；
2. GitHub Release 上传发布物 `TelegramBot-vX.Y.Z.zip`（源码 + 启动器，不含 `.venv`）；
3. 同步 `pyproject.toml` 到版本页仓库（`lym2006.github.io/TelegramBot`），在线版本号即生效；
4. 用户下次启动时，GUI 版本检查命中新版本，启动器自动完成升级。

[⤴️ 返回目录](#-目录)

---

## 🔄 更新版本

- **开发版**：GUI 工具栏「检查更新」提示新版本；拉取新代码后，若依赖有变动，重跑快速开始的 pip 安装命令同步。
- **打包版（规划中）**：启动器在拉起主程序前自动完成版本比对与更新，GUI 内「检查更新」按钮可随时手动触发。

[⤴️ 返回目录](#-目录)

---

## ❗️ 温馨提示

本项目目前仍处于 **测试阶段**，如遇报错或异常行为属正常现象，请勿惊慌 😊 

- **代理语义**：`proxy` 填写地址为手动模式，留空为自动模式（系统代理 → 直连；全不通时提示可填的本机端口）。代理软件只关系统代理开关、进程仍在监听时，程序仍可直连其本地端口收发消息，属正常现象而非缓存故障。

如需进行插件开发、查阅 API 或查看源码，请参考以下资源：
- 📖 **官方文档**：[`aiogram.dev`](https://docs.aiogram.dev/en/latest/)
- 💻 **`GitHub` 仓库**：[`aiogram`](https://github.com/aiogram/aiogram)

[⤴️ 返回目录](#-目录)

---

## 📄 许可证 (`LICENSE`)

本项目采用 MIT 许可证 - 查看 [`LICENSE`](LICENSE) 文件了解详情。

---
Made by **lym2006**
