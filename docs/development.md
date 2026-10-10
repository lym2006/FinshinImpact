# 开发手册

面向贡献者与维护者。用户侧安装与更新见根目录 [`README.md`](../README.md)，发布操作细节见 [`packaging.md`](packaging.md)，代码风格见 [`coding-style.md`](coding-style.md)。

## 环境搭建

1. 安装 `Python 3.11+`（勾选 Add to PATH）。
2. 下载本仓库源码并解压，在项目根目录创建虚拟环境：`python -m venv .venv`。
3. 激活虚拟环境：`.venv\Scripts\activate`。
4. 安装依赖与开发工具：`pip install -e ".[dev]"`（可自行配置镜像源）。
5. 安装 Playwright 浏览器内核：`playwright install chromium`。
6. 启动：`python -m bootstrap`，先弹出「选择机器人」窗口，选定或新建实例后管理面板出现。
7. 首次运行需在选择窗点「新建」，填 Bot Token 即生成实例文件夹 `instances/<身份码>/` 并弹出配置向导，填入配置即完成初始化（无需手编文件）。
8. 实例文件夹内含 `config.toml`、`persona.md`、`profile.json`、`data/`、`logs/`，整体不进版本库。Bot Token 存 `profile.json`，不进 `config.toml`，面板不渲染也不可改。
9. 身份码经环境变量 `FINSHINIMPACT_PROFILE` 传递（单源定义在 `src/profile_env.py` 的 `PROFILE_ENV`），选窗写入、业务模块导入期读取。`init_files` 的路径常量导入即冻结，故身份码必须在任何业务模块 import 前确定。手动单跑 `runtime\python.exe main.py` 也会先弹选择窗，无需自行设置该变量。
10. 已有旧版根目录 `config.toml` 的老配置需手动备份重填 API Key、人设等项，旧位置不再被读取。

## 代码规范检查

改码前后跑一次规范扫描器，对照 `docs/coding-style.md` 九个分节自查。扫描器只报不改，输出供人工核实。

```powershell
python devtools\check_coding_style.py            # 默认扫 src，按分节输出违规清单
python devtools\check_coding_style.py src\bot    # 只扫指定目录或文件
python devtools\check_coding_style.py --hard-only  # 只看规则明确可判的硬性违规
python devtools\check_coding_style.py --section 注释  # 只看某一节，可重复
```

- 每条违规带标记：`[H]` 硬性，规则明确可判，须改；`[?]` 待核，启发式提示，人工判断后再改。
- 扫描器本体在 `devtools/`，与 `src`、`packaging` 同级，属开发者内容，不进发布包（打包走白名单，见 [packaging.md](packaging.md)）。
- 扫描器自身也须合规，改完检查逻辑后跑 `python devtools\check_coding_style.py devtools` 自查，应保持 0 违规。

## 发布流程

1. `pyproject.toml` 递增版本号，`CHANGELOG` 定稿，打 `git tag vX.Y.Z` 并推送。
2. GitHub Release 上传发布物 `FinshinImpact-vX.Y.Z.zip`（源码 + 启动器，不含 `.venv`）。
3. 版本页仓库 workflow 随发布自动同步 `pyproject.toml` 并部署 Pages，在线版本号随之生效，无需手动操作。
4. 用户下次启动时，GUI 版本检查命中新版本，启动器自动完成升级。

## 更新方式

- **「检查更新」按钮**：两种版本行为一致，只比对在线版本号并弹窗提示有无新版，不当场替你更新。
  - 发现新版时提示重启本程序，启动器随即自动完成升级
- **开发版**：手动拉取新代码（`git pull` 或下载源码覆盖），依赖有变动时重跑上文环境搭建的 `pip` 安装命令同步。
- **打包版**：启动器每次拉起主程序前自动比对版本，弹窗确认后完成下载升级，用户配置、数据与日志一律保留。
  - 启动器本体随升级当场更换，旧壳拉起新壳并确认接管后退场
  - 慢启动弹限时提示，极端情况旧壳直接启动兜底
  - v0.4.3 起随升级分发，此前版本为下次启动时更换
