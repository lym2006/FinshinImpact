# 开发手册

面向贡献者与维护者。用户侧安装与更新见根目录 [`README.md`](../README.md)，发布操作细节见 [`packaging.md`](packaging.md)，代码风格见 [`coding-style.md`](coding-style.md)。

## 环境搭建

1. 安装 `Python 3.11+`（勾选 Add to PATH）。
2. 下载本仓库源码并解压，在项目根目录创建虚拟环境：`python -m venv .venv`。
3. 激活虚拟环境：`.venv\Scripts\activate`。
4. 安装依赖与开发工具：`pip install -e ".[dev]"`（可自行配置镜像源）。
5. 安装 Playwright 浏览器内核：`playwright install chromium`。
6. 启动：`python -m bot`，管理面板窗口即出现。
7. 首次运行自动生成 `config.toml` 并弹出配置向导，填入配置即完成初始化（无需手编文件）。

## 发布流程

1. `pyproject.toml` 递增版本号，`CHANGELOG` 定稿，打 `git tag vX.Y.Z` 并推送。
2. GitHub Release 上传发布物 `TelegramBot-vX.Y.Z.zip`（源码 + 启动器，不含 `.venv`）。
3. 手动把 `pyproject.toml` 覆盖到版本页仓库（`lym2006.github.io/TelegramBot`）并 `push`，其 Pages workflow 自动部署，在线版本号即生效。
4. 用户下次启动时，GUI 版本检查命中新版本，启动器自动完成升级。

## 更新方式

- **「检查更新」按钮**：两种版本行为一致，仅比对在线版本号并弹窗提示是否有新版，**不会** 替你更新。
- **开发版**：手动拉取新代码（`git pull` 或下载源码覆盖），若依赖有变动，重跑上文环境搭建的 `pip` 安装命令同步。
- **打包版**：启动器每次拉起主程序前自动比对版本，弹窗确认后完成下载升级，用户配置、数据与日志一律保留；启动器本体也随升级自动更换（v0.4.0 起，更换时自动重启一次）。
