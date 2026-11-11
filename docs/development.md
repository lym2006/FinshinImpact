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
   - 发布包解压后手动单跑 `runtime\python.exe main.py` 也会先弹选择窗，无需自行设置该变量。
9. `config.toml` 住在实例目录里，根目录那一份不读取，手头的老配置要自己备份，再重填 API Key 与人设。

## 新增插件（清单驱动流程）

1. 建目录 `src/bundled/<Name>/`，`__init__.py` 里写一只 `BasePlugin` 子类，一只模块里只准有一只。
   - 取件优先从 `finshin_sdk` 顶层取，顶层没导出的那几样（谓词、随包档位表、分步保留串一类）再从 `finshin_sdk.domain` 取。
   - 两份交出来的是同一个对象，不必为「只用一个入口」去撤掉子包那份。
   - 四只方法都可以不写，不写即没有那一类能力，交出的清单按交出的顺序生效。
   - `message_routes` 交按顺序判定的路由清单，谓词只吃归一后的处理上下文，装配时由平台侧编成引擎对象。
   - `background_loops` 交常驻循环，元素为无参协程函数，随 Bot 服务起停：轮询开始即拉起，停服即取消。跑中途抛出即静默收摊，那行日志要等停服收拢时才落，循环本身不重跑。
   - `queued_actions` 交可排队的动作，动作名写成「插件名.动作」，前段不等于自己的插件名整只拒装。
   - `platform_moments` 交平台机会的订阅清单，元素写成 `MomentSubscription(时机, 协程)`，同一时机交多条即按交出的顺序跑。
   - 要交的那几样与处理上下文都取自接口包：`BasePlugin`、`MessageRoute`、`QueuedAction`、`MomentSubscription`、`HandlerContext`。
   - 要跨插件共用的守卫、谓词、话术放 `src/bundled/_shared/`，那里没有入口类故不会被当作插件加载。
2. 平台机会现有三条，加新时机在 `PlatformMoment` 加一名，不在入口基类上加方法：
   - `BEFORE_ENGINE_RUN` 排在轮询开跑前，跑在服务线程的事件循环上，重活自己交线程池。
   - `IDENTITY_CHANGED` 排在主人或生效正文变了、清历史那一刻。
   - `CONFIG_VERIFIED` 排在配置校验通过那一刻，此刻内存里已是刚验过的值，盘上可能还是旧值。
   - 三条轮到时协程都收同一份交代 `CapabilityCall`，要往外说话从它的 `say` 拿。
   - 订阅的协程抛出的异常由装载侧兜住，落一行带插件名与时机名的日志，平台接着跑。
3. 目录内放 `plugin.toml`（模板 `assets/plugin.example.toml`）：
   - 恒启用与加载档位由 `finshin_sdk.domain` 的随包表 `BUNDLED_PLUGIN_PRIORITY` 定，外部插件一律常规档。
   - 清单多写的键一律忽略，帮助段与命令条目里多写的键同样忽略，被忽略的键名记进调试日志。
   - `deps` 只写本插件独有的顶层库并 pin 版本，核心公共库走 `pyproject.toml`。
4. 注册序列与帮助图自动消费清单，随包表决定谁恒启用、谁排前面。`name` 必须与目录名一致，对不上时整份清单被拒收。
5. 命令可见性由清单 `[[help]]` 贡献决定，未写贡献的命令会被未知命令拦截误伤。
6. 命令的可选输入只在 `[[help.commands]]` 登记，help 侧取的就是这一份。
   - `flags` 每项写成 `["-i", "说明"]`，`-h` 全命令默认可用、不必登记。
   - 要带值的开关再补一段值名，写成 `["-t", "说明", "秒数"]`，一只开关最多带一个值。
   - 值就是紧跟在开关后面的那一段，后面紧跟别的开关即判缺值。
   - 值的类型解析器不管，命令拿到手自己判，判不过就回一句要什么。
   - `args` 写命令后面要带的内容，一句话说明，写了只收一个，没写一个都不收。
   - 带值开关后面又多一段数，算两个位置参数，一样判多余输入。
   - 分段与绑定归 `finshin_sdk.domain` 的 `bind_command`，平台层只交出原顺序的片段。
   - 多余输入的表现为：私聊与群里给这条命令的用法，群里引用发起人那条消息，频道静默。
   - 命令自己缺参时的补救流程归命令侧实现。
7. 命令权限档写清单 `role`，取 `owner` / `admin` / `member`，不写即 `member`。
   - 装配时与代码里 `require_role(CommandRole.X)` 的档位比对，对不上整份插件拒装。
   - 对话场景的门槛仍写进判定函数读 `role_of`，清单不认。
   - 帮助图的命令描述尾部按档位自动追加（仅主人）/（需授权），文案不要再手抄一份。
8. 段级 `note` 只写清单字段表达不了的规矩，比如私聊能不能用。
   - 权限与可选输入都有对应字段，抄进 `note` 就是第二份口径，改了代码不会自动跟着改。
9. 命令要分步等下一条输入时，中止用的保留串取 `finshin_sdk.domain` 的 `StepInput.STOP`，别在插件里另写一份。

装库链路：

- `plugin.toml` 的 `deps` 与 `assets` 由插件面板收集，选定实例后在启动前统一结算。
- 判定以启用插件的 pip 包实测优先，资源靠指纹兜底。
- 装完才放行启动，装失败的插件自动禁用并弹窗告知。
- 实例未保存过插件选择时仅随包插件运行。

装卸纪律：

- 禁用只改启用集，不删已装库。
- 删库只由依赖同步执行，入口是选窗「依赖管理」手动菜单。

## 外部插件

1. 建目录 `plugins_installed/<Name>/`（项目根下），清单与字段同上，`name` 与目录名一致。
   - 只引 `finshin_sdk` 交来的那几样，别伸手本体各层——随包插件跟本体同一个版本，外部插件伸进本体就是改一次本体可能装不上。装载前先扫一遍源码，引了本体的整只拒装，面板那行写明引了谁与落在哪个文件名第几行，一份多处只报第一处。
   - 两根目录一起扫，先读随包再读外部。外部目录按文件路径挂成独立顶层包，插件目录内部的相对引用走得通。
2. 与随包插件同名的那份不放行，改 `name` 或写进启用集都不认。
   - 面板给被顶掉的那一份单开一行，排在整张清单末尾，勾选位是「重名」按钮，点开写明插件名被谁占用。
3. 清单声明的命令名已被拿走的整只不装载，面板把勾选位换成「冲突」按钮，点开逐条写明哪条命令被哪只插件占用。
   - 随包插件优先拿走命令名，同一命令名被两只外部插件一起勾上时整组不装载，状态文件怎么写都不算数。
   - 一只插件交出的是整套路由，摘不掉单独一条命令，所以一被抢走即整只不装载。
4. 勾选与取消当场重算，撞车的另一只立刻换成按钮，不用重启也不用再保存。

## 从 dev3 及更早的写法改过来

1. 入口写法：模块属性 `spec` 那套不再读取，改在 `__init__.py` 里写一只 `BasePlugin` 子类，一只模块只准有一只。`plugin.toml` 不用改。
2. 导入行：领域词表、归一数据快照与处理上下文从 `core` 整只搬进 `finshin_sdk`。原来写 `from core.domain import ...`、`from core.dto import ...` 的行改从 `finshin_sdk` 取，`CapabilityCall` 同住接口包。
3. 交出的东西改名：`PluginRoute` → `MessageRoute`、`PluginPredicate` → `RouteMatcher`、`PluginBackground` → `BackgroundLoop`、`TaskHandler` → `QueuedAction`、`timings` → `platform_moments`。
   - 时机三样一并归到 moment 词根：`PlatformTiming` → `PlatformMoment`、`PluginTiming` → `MomentSubscription`、`PluginTimingRun` → `MomentRun`。
   - `PluginSpec` 那只袋子删了。
4. 动作名带归属：`queued_actions` 交的动作名写成「插件名.动作」，前段不等于自己的插件名整只拒装。内置对话的动作名由 `chat` 改成 `AI.chat`。
5. 接口包撤掉四处没人用的形状：`ContentDTO` 的 `file_token` 与 `origin_ref`、`AdapterFieldSpec.default`、`BoundCommand.value_of`、`PrincipalRepository.find_by_key`。用到哪一处改哪一处，没用到不必动。
6. 清单可声明接口版本：`adapter.toml` 新增 `requires_sdk` 一行，没写即不设限。要的比本机新会拒在装载之前，弹窗与日志各落一句。

## 新增平台适配器

1. 建目录 `src/adapters/<平台>/`，目录内交一份 `adapter.toml`，写平台标识，用到第三方库再写 `deps`。
   - 入口模块名由本体规定（`entry`），清单缺件或字段非法的适配器整份不进表。
   - `deps` 里 pin 的库由启动器随首装与升级补装一起装上，依赖同步删库时被保留。
   - 平台自带库的版本号以 `deps` 这一行为准，开发环境用的 `pyproject.toml` dev 段照抄同一串。
   - `requires_sdk` 写要接口包几版以上，不写即不设限。要得比本机新就拒在装载入口之前，弹窗与日志各落一句写明要哪版与本机哪版。装卸入口归面板平台那一页。
2. 要实现的两份抽象接口在 `finshin_sdk`，那一只包不含任何第三方库。
   - 本体不直接引适配器，适配器经这一包取要实现的两份接口，除适配层外全仓不许 import aiogram。
   - 这一包能单独装：打包配置在 `src/finshin_sdk/pyproject.toml`，构建 wheel 跑 `uv build src/finshin_sdk --wheel`，版本号的单源是它 `__init__.py` 里的 `SDK_VERSION`。
   - 只写插件或适配器的人要的那几样都在这只包里，它零第三方依赖、能单独打 wheel。包目前仍随主仓构建，独立发布渠道等适配器拆仓之后再补。
3. 入口模块交出运行时装配、探测、引擎预热与诊断四件，运行时实例交出交互端口、插件路由挂载口与路由清单编译器。
   - 挂日志中间件与按启用序列注册插件由装载侧完成，适配器不参与那两步。

## 发布流程

版本号与 CHANGELOG 归段、tag、release、版本页收尾统一见 [release-workflow.md](release-workflow.md)，构建与本地实测见 [packaging.md](packaging.md)。

## 更新方式

- **「版本检查」按钮**：两种版本行为一致，只比对在线版本号并弹窗提示有无新版，不当场更新，发现新版时提示重启本程序、由启动器自动完成升级。顺带拉一次发布说明清单，把弹窗焦点定到那一支版本。
- **开发版**：手动拉取新代码（`git pull` 或下载源码覆盖），依赖有变动时重跑上文环境搭建的 `pip` 安装命令同步。
- **打包版**：启动器每次拉起主程序前自动比对版本，弹窗确认后完成下载升级，用户配置、数据与日志一律保留。
  - 启动器本体随升级当场更换，换壳机制见 [packaging.md](packaging.md)。
  - 各版本走自动升级还是手动整包，见根目录 [`README.md`](../README.md) 的旧版迁移。
