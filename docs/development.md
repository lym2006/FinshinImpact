# 开发手册

面向贡献者与维护者。其余文档各管一段：

- 用户侧安装与更新：根目录 [`README.md`](../README.md)
- 发布操作：[`release-workflow.md`](release-workflow.md)
- 构建与发布物：[`packaging.md`](packaging.md)
- 代码风格：[`coding-style.md`](coding-style.md)，静态检查：[`style-checker.md`](style-checker.md)，回归用例：[`testing.md`](testing.md)
- 实测出来的约束与踩坑：[`lessons/`](lessons/README.md)

## 环境搭建

1. 安装 `Python 3.11+`（勾选 Add to PATH）。
2. 下载本仓库源码并解压，在项目根目录创建虚拟环境：`python -m venv .venv`。
3. 激活虚拟环境：`.venv\Scripts\activate`。
4. 安装依赖与开发工具：`pip install -e ".[dev]"`，镜像源可自行配置。
5. 启动：`python -m bootstrap`，先弹出「选择机器人」窗口，选定或新建实例后管理面板出现。
6. 首次运行在选择窗点「新建」，填 Bot Token 即生成实例文件夹 `instances/<身份码>/` 并弹出配置向导，填完即完成初始化，无需手编文件。
7. 实例文件夹：
   - 内含 `config.toml`、`persona.md`、`.persona.base`、`profile.json`、`records/`、`db/`（内有 `bot.db` 与 `backups/`）、`logs/`，整体不进版本库。
   - Bot Token 存 `profile.json`，不进 `config.toml`，面板不渲染也不可改。
8. 身份码：
   - 经环境变量 `FINSHINIMPACT_PROFILE` 传递，单源定义在 `src/system/profile_env.py` 的 `_PROFILE_ENV`，选窗写入、业务模块导入期读取。
   - `utils/paths` 的路径常量导入即冻结，故身份码必须在任何业务模块 import 前确定。
   - 手动单跑 `runtime\python.exe main.py` 也会先弹选择窗，无需自行设置该变量。
9. 旧版根目录 `config.toml` 不再被读取，老配置需手动备份，重填 API Key 与人设。

## 新增插件（清单驱动流程）

1. 建目录 `src/plugins/<Name>/`，`__init__.py` 导出 `spec` 或 `router`。
   - `spec` 交一份按顺序判定的路由清单，谓词只吃归一后的处理上下文，装配时由平台侧编成引擎对象。
   - `router` 直接交引擎原生路由，判定逻辑得写在过滤器里。
   - 要跨插件共用的守卫、过滤器、话术放 `src/plugins/_shared/`，那里没有清单故不会被当作插件加载。
2. 要常驻后台的，`spec` 里带 `backgrounds`，走 `router` 的再导出同名属性。
   - 元素为无参协程函数，随 Bot 服务起停：轮询开始即拉起，停服即取消。
   - 协程内抛出的异常只记日志。
3. 目录内放 `plugin.toml`（模板 `assets/plugin.example.toml`）：
   - `order` 取三档，0 最先（help 独占）、10 常规、50 最后（AI 独占）。
   - `deps` 只写本插件独有的顶层库并 pin 版本，核心公共库走 `pyproject.toml`。
4. 注册序列与帮助图自动消费清单，无白名单可改。`name` 必须与目录名一致，否则整份清单被拒收。
5. 命令可见性由清单 `[[help]]` 贡献决定，未写贡献的命令会被未知命令拦截误伤。
6. 要收位置参数的命令，还得在 `src/plugins/help/_commands.py` 的 `_ARGS_ALLOWED` 点名。
   - 没点名的命令，带的参数被当多余输入拦下，表现为群里静默、私聊报格式错误。
   - 命令自己缺参时的补救流程归命令侧实现。
7. 命令要分步等下一条输入时，中止用的保留串取 `core.domain` 的 `StepInput.STOP`，别在插件里另写一份。
8. 对话与命令的权限档一律标在插件代码里，不进 `plugin.toml`。
   - 命令挂 `require_role(CommandRole.X)`，场景门槛写进判定函数读 `role_of`。
   - 清单里只能存枚举串，读侧还要映射回档位，等于把一处判定拆成两处。

装库链路：

- `plugin.toml` 的 `deps` 与 `assets` 由插件面板收集，选定实例后在启动前统一结算。
- 判定以启用插件的 pip 包实测优先，资源靠指纹兜底。
- 装完才放行启动，装失败的插件自动禁用并弹窗告知。
- 实例未保存过插件选择时仅 core 插件运行。

装卸纪律：

- 禁用只改启用集，不删已装库。
- 删库只由依赖同步执行，入口是选窗「依赖管理」与启动引导期对账不符时的弹窗。

## 发布流程

版本号与 CHANGELOG 归段、tag、release、版本页收尾统一见 [release-workflow.md](release-workflow.md)，构建与本地实测见 [packaging.md](packaging.md)。

- 版本页仓库的 workflow 随发布自动同步 `pyproject.toml` 并部署 Pages，在线版本号随之生效，无需手动操作。
- 用户下次启动时 GUI 版本检查命中新版本，启动器自动完成升级。

## 更新方式

- **「版本检查」按钮**：两种版本行为一致，只比对在线版本号并弹窗提示有无新版，不当场替你更新。
  - 发现新版时提示重启本程序，启动器随即自动完成升级。
- **开发版**：手动拉取新代码（`git pull` 或下载源码覆盖），依赖有变动时重跑上文环境搭建的 `pip` 安装命令同步。
- **打包版**：启动器每次拉起主程序前自动比对版本，弹窗确认后完成下载升级，用户配置、数据与日志一律保留。
  - 启动器本体随升级当场更换，换壳机制见 [packaging.md](packaging.md)。
  - 各版本走自动升级还是手动整包，见根目录 [`README.md`](../README.md) 的旧版迁移。
