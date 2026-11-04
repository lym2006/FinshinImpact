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
   - 内含 `config.toml`、`persona/`（内有 `persona.md`、`template.sha256`、`applied.cache`）、`profile.json`、`records/`、`db/`（内有 `bot.db` 与 `backups/`）、`logs/`，整体不进版本库。
   - Bot Token 存 `profile.json`，不进 `config.toml`，面板不渲染也不可改。
8. 身份码：
   - 经环境变量 `FINSHINIMPACT_PROFILE` 传递，单源定义在 `src/system/profile_env.py` 的 `_PROFILE_ENV`，选窗写入、业务模块导入期读取。
   - `utils/paths` 的路径常量导入即冻结，故身份码必须在任何业务模块 import 前确定。
   - 手动单跑 `runtime\python.exe main.py` 也会先弹选择窗，无需自行设置该变量。
9. 旧版根目录 `config.toml` 不再被读取，老配置需手动备份，重填 API Key 与人设。

## 新增插件（清单驱动流程）

1. 建目录 `src/plugins/<Name>/`，`__init__.py` 导出 `spec`。
   - `spec` 交一份按顺序判定的路由清单，谓词只吃归一后的处理上下文，装配时由平台侧编成引擎对象。
   - 要跨插件共用的守卫、谓词、话术放 `src/plugins/_shared/`，那里没有清单故不会被当作插件加载。
2. 要常驻后台的，`spec` 里带 `backgrounds`。
   - 元素为无参协程函数，随 Bot 服务起停：轮询开始即拉起，停服即取消。
   - 协程内抛出的异常只记日志。
3. 目录内放 `plugin.toml`（模板 `assets/plugin.example.toml`）：
   - `order` 取三档，0 最先（help 独占）、10 常规、50 最后（AI 独占）。
   - `deps` 只写本插件独有的顶层库并 pin 版本，核心公共库走 `pyproject.toml`。
4. 注册序列与帮助图自动消费清单，无白名单可改。`name` 必须与目录名一致，对不上时整份清单被拒收。
5. 命令可见性由清单 `[[help]]` 贡献决定，未写贡献的命令会被未知命令拦截误伤。
6. 命令的可选输入全写在 `[[help.commands]]` 里，help 侧不再维护任何命令名单。
   - `flags` 每项写成 `["-i", "说明"]`，`-h` 全命令默认可用、不必登记。
   - 要带值的开关再补一段值名，写成 `["-t", "说明", "秒数"]`，一只开关最多带一个值。
   - 值就是紧跟在开关后面的那一段，后面紧跟别的开关即判缺值。
   - 值的类型解析器不管，命令拿到手自己判，判不过就回一句要什么。
   - `args` 写命令后面要带的内容，一句话说明，写了只收一个，没写一个都不收。
   - 带值开关后面又多一段数，算两个位置参数，一样判多余输入。
   - 分段与绑定归 `core.domain` 的 `bind_command`，平台层只交出原顺序的片段。
   - 多余输入的表现为：私聊与群里给这条命令的用法，群里 @ 发起人，频道静默。
   - 命令自己缺参时的补救流程归命令侧实现。
7. 命令权限档写清单 `role`，取 `owner` / `admin` / `member`，不写即 `member`。
   - 装配时与代码里 `require_role(CommandRole.X)` 的档位比对，对不上整份插件拒装。
   - 对话场景的门槛仍写进判定函数读 `role_of`，清单不认。
   - 帮助图的命令描述尾部按档位自动追加（仅主人）/（需授权），文案不要再手抄一份。
8. 段级 `note` 只写清单字段表达不了的规矩，比如私聊能不能用。
   - 权限与可选输入都有对应字段，抄进 `note` 就是第二份口径，改了代码不会自动跟着改。
9. 命令要分步等下一条输入时，中止用的保留串取 `core.domain` 的 `StepInput.STOP`，别在插件里另写一份。

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

## 更新方式

- **「版本检查」按钮**：两种版本行为一致，只比对在线版本号并弹窗提示有无新版，不当场更新，发现新版时提示重启本程序、由启动器自动完成升级。
- **开发版**：手动拉取新代码（`git pull` 或下载源码覆盖），依赖有变动时重跑上文环境搭建的 `pip` 安装命令同步。
- **打包版**：启动器每次拉起主程序前自动比对版本，弹窗确认后完成下载升级，用户配置、数据与日志一律保留。
  - 启动器本体随升级当场更换，换壳机制见 [packaging.md](packaging.md)。
  - 各版本走自动升级还是手动整包，见根目录 [`README.md`](../README.md) 的旧版迁移。
