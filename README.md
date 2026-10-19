# 🤖 Fool's Telegram Bot

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Aiogram Version](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Project Type](https://img.shields.io/badge/project-pyproject.toml-brightgreen.svg)](pyproject.toml)
[![Changelog](https://img.shields.io/badge/changelog-CHANGELOG.md-blue.svg)](CHANGELOG.md)

> 一个基于 `Python` 和 `aiogram 3.x` 构建的异步 Telegram 机器人，采用模块化插件设计。

## 📑 目录

- [✨ 功能特点](#-功能特点)
- [💬 关于 AI 对话](#-关于-ai-对话)
- [🛠️ 技术栈](#️-技术栈)
- [🚀 快速开始](#-快速开始)
  - [1. 克隆项目](#1-克隆项目)
  - [2. 创建虚拟环境并启动（推荐）](#2-创建虚拟环境并启动推荐)
  - [3. 安装依赖](#3-安装依赖)
  - [4. 配置项目](#4-配置项目)
  - [5. 准备 Chrome 环境](#5-准备-chrome-环境)
  - [6. 运行机器人](#6-运行机器人)
- [📂 项目结构](#-项目结构)
- [🚨 温馨提示](#-温馨提示)
- [📄 许可证 (`LICENSE`)](#-许可证-license)

---

## ✨ 功能特点

- 🚀 **异步架构**: 基于 `asyncio` 和 `aiogram`，提供高并发处理能力。
- 🔌 **插件化设计**: 功能模块位于 `src/plugins` 目录下，支持动态加载，易于扩展和维护。
- 📝 **完善日志**: 集成 `logging` 模块，支持控制台输出与文件   `Rotating` ，默认开启详细报错。
- ⚙️ **TOML 配置**: 使用 `config.toml` 进行集中式配置管理，类型安全且易读。
- 🌐 **浏览器自动化**: 使用 `Playwright` 实现异步处理。

[⤴️ 返回目录](#-目录)

---

## 💬 关于 AI 对话
目前仅支持 **私聊** 使用

- **独立会话**：不同用户 **或** 不同群组同用户
  > 群组中需触发关键词或 @机器人（**暂不可用**）
- **消息排队**：原子级别任务锁避免多任务并发出错
- **状态更新**：自动更新状态信息（排队中、思考中、思考完成内容），**计划** 加入取消排队按钮
- **自动引用**：状态信息引用原消息，回复内容引用思考过程
- **思考过程**：仅私聊输出，群组中请使用 `/history` 命令
- **取消会话**：若思考过程中用户删除原消息，停止处理该任务，消息不计入历史，**计划** 加入取消任务按钮
  > **注意：** 该功能经测试，目前只在 Nekogram 生效，原版 Telegram 不生效，其他版本未测试
- **删除判断**：若用户删除机器人发出的状态信息，机器人会在必要时重新发送
- **超时处理**：配置超时时间和判断间隔，自动清除用户记录
- **其他功能**：
  - `Markdown` 文件历史记录
  - `Markdown` 格式回复
  - 个性化定制人设（**暂不可用**）
  - 自主开关对话功能
  - 余额查询（**注意：** 查询数据与硅基流动网页端不一致属正常现象）
  - 更多参见 `/help` 命令

[⤴️ 返回目录](#-目录)

---

## 🛠️ 技术栈

| 组件 | 版本/描述 |
| :--- | :--- |
| **语言** | `Python 3.11+` |
| **核心框架** | [`aiogram 3.x`](https://docs.aiogram.dev/) |
| **依赖管理** | [`pyproject.toml`](pyproject.toml) |
| **浏览器驱动** | `Playwright` / `chromium`（根据步骤下载） |
| **日志系统** | `logging` |

[⤴️ 返回目录](#-目录)

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/lym2006/TelegramBot.git
cd TelegramBot
```

### 2. 创建虚拟环境并启动（推荐）
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

> **注意：** 如果使用虚拟环境，请确保后续步骤 **3**、**5** 都在虚拟环境启动状态下执行

### 3. 安装依赖

本项目使用 `pyproject.toml` 管理依赖，推荐使用以下命令安装：

```bash
pip install -e .
# 如果你在中国大陆，网络较慢，可以使用国内镜像源：
# pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 配置项目

编辑 `src/config.toml` 文件，填入你的配置：

```toml
# config.toml 示例配置
[network]
proxy="http://127.0.0.1:port" # 代理地址和端口

[api_keys]
telegram_token="123456:abcedfgh" # telegram bot token
```

编辑 `src/plugins/AI/config.toml` 文件，填入你的配置：

```toml
# config.toml 示例配置
[api]
model_name="Pro/deepseek-ai/DeepSeek-R1" # 模型名称
api_key="sk-xxxxxxxxxxxxxxx" # siliconflow的api
temperature=0.7 # 模型温度

[personality]
default="""
默认人设不建议修改
"""

[triggers]
group_keywords=["1","2"] # 群组中机器人触发词，建议改成机器人名称，可以直接@

[data] # 单位均为小时
clearup=6 # 超过时间未活跃清除记录
waiting=0.5 # 判断间隔时间
```

Token、机器人名称：在 [`BotFather`](https://t.me/BotFather) 对话获取、设置。

API、模型名称：在 [硅基流动模型广场](https://cloud.siliconflow.cn/me/models) 获取。

### 5. 准备 Chrome 环境

本项目使用 `Playwright` 实现浏览器自动化操作，可自动下载依赖文件。

```bash
# 1.如果在国内网络环境下，建议先配置镜像源
# Windows PowerShell:
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"

# Windows CMD:
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright

# Mac/Linux:
export PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"


# 2.安装 Chromium
playwright install chromium
```

### 6. 运行机器人

```bash
python -m src.bot
```

[⤴️ 返回目录](#-目录)

---

## 📂 项目结构

```text
TelegramBot/
├── 📄 README.md                           # 📘 项目说明文档
├── 📄 CHANGELOG.md                        # 📝 版本更新日志
├── 📄 .gitignore                          # 🙈 Git 忽略文件配置
├── 📄 .gitmessage                         # 📋 Git Commit 提交规范模板
├── 📄 LICENSE                             # ⚖️ 开源许可证 (MIT)
├── 📄 pyproject.toml                      # 🏗️ 项目构建配置
├── 📁 src/                                # 🐍 源代码目录
│   ├── 📄 bot.py                          # 🚀 机器人主程序
│   ├── 📄 config.toml                     # 🌍 全局配置文件
│   ├── 📁 utils/                          # 🛠️ 通用工具模块
│   │   ├── 📄 config_loader.py            # 📖 配置加载器
│   │   ├── 📄 logger_setup.py             # 📝 日志初始化
│   │   ├── 📄 middleware.py               # 🔄 中间件（场景日志）
│   │   └── 📄 plugins_register.py         # 🔌 插件自动注册
│   ├── 📁 plugins/                        # 🧩 功能插件
│   │   ├── 📁 help/                       # ❓ 帮助模块
│   │   │   ├── 📄 help.py                 # 💡 帮助指令实现
│   │   │   └── 📄 font.ttf                # 🔤 字体文件
│   │   └── 📁 AI/                         # 🤖 AI 核心功能
│   │       ├── 📄 config.toml             # ⚙️ AI 模块配置
│   │       ├── 📄 config.py               # 📥 AI 配置加载
│   │       ├── 📁 core/                   # 🧠 AI 核心逻辑
│   │       │   ├── 📄 session.py          # 👤 用户会话
│   │       │   ├── 📄 task.py             # 📦 任务队列
│   │       │   └── 📄 utils.py            # 🧰 其它工具
│   │       ├── 📁 handlers/               # 📩 消息处理器
│   │       │   ├── 📄 AIchat.py           # 💬 聊天逻辑
│   │       │   ├── 📄 auth.py             # 🔐 用户鉴权
│   │       │   ├── 📄 balance.py          # 💰 余额查询
│   │       │   ├── 📄 history.py          # 📜 历史记录
│   │       │   └── 📄 identity.py         # 🎭 人设更改
│   │       ├── 📁 services/               # ⚙️ 业务服务层
│   │       │   ├── 📄 blacklist.py        # 🚫 读写黑名单
│   │       │   ├── 📄 monitor.py          # 📡 监控排队
│   │       │   ├── 📄 worker.py           # ⚡ 执行操作
│   │       │   ├── 📄 client.py           # 🔗 API 客户端
│   │       │   └── 📁 render/             # 🎨 渲染服务
│   │       │       ├── 📄 css.py          # 🖌️ 样式处理
│   │       │       ├── 📄 renderer.py     # 🖥️ 内容渲染
│   │       │       └── 📄 screenshot.py   # 📸 截图工具
│   │       └── 📁 record/                 # 🗂️ 静态资源/数据记录
│   │           ├── 📄 black.txt           # 📝 黑名单
│   │           ├── 📄 personality.txt     # 🧠 人设提示词
│   │           └── 📄 *.ttf               # 🔣 字体文件
│   └── 📄 __init__.py                     # 📦 包初始化
└── 📁 assets/                             # 📂 外部静态资源
```

[⤴️ 返回目录](#-目录)

---

## 🚨 温馨提示

本项目目前仍处于 **测试阶段**，如遇报错或异常行为属正常现象，请勿惊慌 😊 

如需进行插件开发、查阅 API 或查看源码，请参考以下资源：
- 📖 **官方文档**：[`aiogram.dev`](https://docs.aiogram.dev/en/latest/)
- 💻 **GitHub 仓库**：[`aiogram`](https://github.com/aiogram/aiogram)

[⤴️ 返回目录](#-目录)

---

## 📄 许可证 (`LICENSE`)

本项目采用 MIT 许可证 - 查看 [`LICENSE`](LICENSE) 文件了解详情。

---
Made by **lym2006**