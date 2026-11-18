# 开发手册

面向贡献者与维护者。其余文档各管一段：

- 用户侧安装与更新：根目录 [README.md](../README.md)
- 发布操作：[release-workflow.md](release-workflow.md)
- 构建与发布物：[packaging.md](packaging.md)
- 代码风格：[coding-style.md](coding-style.md)，静态检查：[style-checker.md](style-checker.md)，回归用例：[testing.md](testing.md)
- 实测出来的约束与踩坑：[lessons/](lessons/README.md)

## 环境搭建

1. 安装 `Python 3.11+`（勾选 Add to PATH）。
2. 克隆本仓库：`git clone <地址>`。装载根与接口包两棵都不在版本库里，要按「挂载子仓」那一节自己 clone 进去。
3. 在项目根目录创建虚拟环境：`python -m venv .venv`。
4. 激活虚拟环境：`.venv\Scripts\activate`。
5. 安装依赖与开发工具：`uv sync --all-packages`，镜像源可自行配置。
6. 启动：`python -m bootstrap`，先弹出"选择机器人"窗口，选定或新建实例后管理面板出现。
7. 首次运行在选择窗点"新建"，平台下拉只列本机装着适配器包的平台，装新的走下拉右侧"管理平台组件"。填 Bot Token 即生成实例文件夹 `instances/<身份码>/` 并弹出配置向导，填完即完成初始化，无需手编文件。
8. 实例文件夹：
   - 内含 `config.toml`、`plugins.toml`（插件启用集与目录指纹）、`persona/`（内有 `persona.md`、`template.sha256`、`applied.cache`）、`profile.json`、`records/`、`db/`（内有 `bot.db` 与 `backups/`）、`logs/`，整体不进版本库。
   - Bot Token 存 `profile.json`，不进 `config.toml`，面板不渲染也不可改。
9. 身份码：
   - 经环境变量 `FINSHINIMPACT_PROFILE` 传递，单源定义在 `src/system/profile_env.py` 的 `_PROFILE_ENV`，选窗写入、业务模块导入期读取。
   - 身份码必须在任何业务模块 import 前确定。
   - 发布包解压后手动单跑 `runtime\python.exe main.py` 也会先弹选择窗，无需自行设置该变量。
10. `config.toml` 住在实例目录里，根目录那一份不读取，手头的老配置要自己备份，再重填 API Key 与人设。

## 新增插件（清单驱动流程）

1. 建目录 `src/bundled/<Name>/`，`__init__.py` 里写一只 `BasePlugin` 子类，一只模块里只准有一只。
   - 取件优先从 `finshin_sdk` 顶层取，顶层没导出的那几样（谓词、随包档位表、分步保留串一类）再从 `finshin_sdk.domain` 取。
   - 这几只方法都可以不写，不写即没有那一类能力，交出的清单按交出的顺序生效。
   - `message_routes` 交按顺序判定的路由清单，谓词只吃归一后的处理上下文，装配时由平台侧编成引擎对象。
   - `background_loops` 交常驻循环，元素为无参协程函数，随 Bot 服务起停：轮询开始即拉起，停服即取消。跑中途抛出即静默收摊，那行日志要等停服收拢时才落，循环本身不重跑。
   - `queued_actions` 交可排队的动作，动作名写成「插件名.动作」，前段不等于自己的插件名整只拒装。
   - `platform_moments` 交平台机会的订阅清单，元素写成 `MomentSubscription(时机, 协程)`，同一时机交多条即按交出的顺序跑。
   - 要交的那几样与处理上下文都取自接口包：`BasePlugin`、`MessageRoute`、`QueuedAction`、`MomentSubscription`、`HandlerContext`。
   - 要跨插件共用的守卫、谓词、话术放 `src/bundled/_shared/`。
2. 平台机会列在下面，加新时机在 `PlatformMoment` 加一名，不在入口基类上加方法：
   - `BEFORE_ENGINE_RUN` 排在轮询开跑前，跑在服务线程的事件循环上，重活自己交线程池。
   - `IDENTITY_CHANGED` 排在主人或生效正文变了、清历史那一刻。
   - `CONFIG_VERIFIED` 排在配置校验通过那一刻，此刻内存里已是刚验过的值，盘上可能还是旧值。
   - 轮到时协程都收同一份交代 `CapabilityCall`，要往外说话从它的 `say` 拿。
   - 订阅的协程抛出的异常由装载侧兜住，落一行带插件名与时机名的日志，平台接着跑。
3. 目录内放 `plugin.toml`（模板 `assets/plugin.example.toml`）：
   - 恒启用与加载档位由 `finshin_sdk.domain` 的随包表 `BUNDLED_PLUGIN_PRIORITY` 定，外部插件一律常规档。
   - 清单多写的键一律忽略，帮助段与命令条目里多写的键同样忽略，被忽略的键名记进调试日志。
   - 本插件独有的顶层库写在同目录 `pyproject.toml` 的 `[project].dependencies` 里并 pin 版本，清单里不再写 `deps`。
   - 外部插件的清单与依赖声明缺任一整份不认。随包插件的库照旧在项目根的 `pyproject.toml` 里，目录内只放清单。
4. 注册序列与帮助图自动消费清单，随包表决定谁恒启用、谁排前面。`name` 必须与目录名一致，对不上时整份清单被拒收。
5. 命令可见性由清单 `[[help]]` 贡献决定，未写贡献的命令按未知命令拦截。
6. 命令的可选输入只在 `[[help.commands]]` 登记，help 侧取的就是这一份。
   - `flags` 每项写成 `["-i", "说明"]`，这是不收值的纯开关。`-h` 全命令默认可用、不必登记。
   - 要带值的开关补第三段默认值，写成 `["-t", "说明", 0.0]`，命令没写这只开关即落默认值。
   - 默认值只认整数、小数、文本三种，写成真假值、空文本或数组当场报错，报的是类型本名，不在解析里静默吞。
   - 默认值的类型即这只开关的取值类型：整数档拒收小数写法，小数档把 `5` 这类写法转成 `5.0`，文本档原样交出。
   - 收不进该档的写法判多余输入。范围仍由命令自己判，判不过回一句要什么。
   - 开关数量不设上限，值就是紧跟在开关后面的那一段，后面紧跟别的开关即判缺值。
   - 位置参数只认第一只开关之前的片段，开关之后出现裸段一律判多余输入。
   - `args` 写命令后面要带的内容，一句话说明，写了即收开关之前的全部片段，没写一段都不收。
   - 分段与绑定归 `finshin_sdk.domain` 的 `bind_command`，平台层只交出原顺序的片段。
   - 多余输入的表现为：私聊与群里给这条命令的用法，群里引用发起人那条消息，频道静默。
   - 命令自己缺参时的补救流程归命令侧实现。
7. 命令权限档写清单 `role`，取 `owner` / `admin` / `member`，不写即 `member`。
   - 装配时与代码里 `require_role(CommandRole.X)` 的档位比对，对不上整份插件拒装。
   - 对话场景的门槛仍写进判定函数读 `role_of`，清单不认。
   - 帮助图的命令描述尾部按档位自动追加（仅主人）/（需授权），文案不要再手抄一份。
8. 段级 `note` 只写清单字段表达不了的规矩，比如私聊能不能用。
9. 命令要分步等下一条输入时，中止用的保留串取 `finshin_sdk.domain` 的 `StepInput.STOP`，别在插件里另写一份。

装库链路：

- 插件的库按自家 `pyproject.toml` 的 `[project].dependencies` 收集，`plugin.toml` 的 `assets` 照旧，两者由插件面板汇总，选定实例后在启动前统一结算。
- 判定以启用插件的 pip 包实测优先，资源靠指纹兜底。
- 装 wheel 时逐只点名重装，装完再按本机读到的版本复核一次。
- 装完才放行启动，装失败的插件自动禁用并弹窗告知。
- 实例未保存过插件选择时仅随包插件运行。

装卸纪律：

- 禁用只改启用集，不删已装库。
- 删库只由依赖同步执行，入口是选窗"环境维护"手动菜单。

## 外部插件

1. 建目录 `finshin/plugin/<Name>/`，清单与字段同上，`name` 与目录名一致，代码放 `src` 那一层。
   - 导入范围见 [coding-style.md](coding-style.md) 的「分层职责」节。
   - 装载前扫描源码，引了本体的整只拒装，面板写明引用位置，一份多处只报第一处。
   - 两根目录一起扫，先读随包再读外部。外部插件的导入名是 `plugin.<Name>`，代码所在那一层按名字接到它，插件内部的相对引用走得通。
2. 与随包插件同名的那份不放行，改 `name` 或写进启用集都不认。
3. 被顶掉的那一份在面板单开一行，排在整张清单末尾，勾选位是"重名"按钮，点开写明插件名被谁占用。
4. 清单声明的命令名已被拿走的整只不装载，面板把勾选位换成"冲突"按钮，点开逐条写明哪条命令被哪只插件占用。
   - 随包插件优先拿走命令名，同一命令名被两只外部插件一起勾上时整组不装载，状态文件怎么写都不算数。
   - 一只插件交出的是整套路由，摘不掉单独一条命令，命令名被抢走即整只不装载。
5. 勾选与取消当场重算，撞车的另一只立刻换成按钮，不用重启也不用再保存。

## 从 dev4 及更早的写法改过来

1. 入口写法：模块属性 `spec` 那套不再读取，改在 `__init__.py` 里写一只 `BasePlugin` 子类，一只模块只准有一只。`plugin.toml` 不用改。
2. 导入行：领域词表、归一数据快照与处理上下文从 `core` 整只搬进 `finshin_sdk`。原来写 `from core.domain import ...`、`from core.dto import ...` 的行改从 `finshin_sdk` 取，`CapabilityCall` 同住接口包。
3. 交出的东西改名：`PluginRoute` → `MessageRoute`、`PluginPredicate` → `RouteMatcher`、`PluginBackground` → `BackgroundLoop`、`TaskHandler` → `QueuedAction`、`timings` → `platform_moments`。
   - 时机那几样一并归到 moment 词根：`PlatformTiming` → `PlatformMoment`、`PluginTiming` → `MomentSubscription`、`PluginTimingRun` → `MomentRun`。
   - `PluginSpec` 那只袋子删了。
4. 动作名带归属：`queued_actions` 交的动作名写成「插件名.动作」，前段不等于自己的插件名整只拒装。内置对话的动作名由 `chat` 改成 `AI.chat`。
5. 接口包撤掉没人用的形状：`ContentDTO` 的 `file_token` 与 `origin_ref`、`AdapterFieldSpec.default`、`BoundCommand.value_of`、`PrincipalRepository.find_by_key`。用到哪一处改哪一处，没用到不必动。
6. 把适配器声明从 `adapter.toml` 搬进 `pyproject.toml`，字段写法见「新增平台适配器」节。
7. 插件独有的库从 `plugin.toml` 的 `deps` 搬到同目录 `pyproject.toml` 的 `[project].dependencies`，清单里再写 `deps` 属未知键、一律忽略。随包插件的库走项目根的 `pyproject.toml`。

## 新增平台适配器

1. 命名与发现按一套词表走，加平台不改本体代码：
   - 本体代码里平台码只有一处来源：`Platform` 枚举里的 `tg`、`qq`。
   - 装载根下的目录名用平台码，`finshin/adapter/<平台码>/`，与声明里的 `platform` 同值。
   - 分发名 `finshin-adapter-tg`，可导入的包名是同一串把连字符换成下划线，两处都由子仓根的 `pyproject.toml` 派生。
   - 仓名以 `Finshin` 起头接词根，适配器族是 `FinshinAdapter` 加平台码大写。
   - 声明里的平台标识、入口点段的键、枚举里的平台码必须同值，装载侧读到不一致就整份不进表。
   - 本体只问那张表：装载、依赖保留与引擎预热都从 `load_adapter_manifests()` 取，不认路径也不写死平台名。
   - 发出去的平台靠一份远端目录在场：每行交平台码、分发名、版本、下载直链与指纹五样，直链是独立整串。
   - 行内那一版是最新版，行里另嵌一段版本清单：每条交版本、下载直链与指纹三样，最新一版排在最前。
   - 清单只收正式 release，最多十版。
   - 旧版的版本号取 wheel 文件名，没报指纹的旧版不进清单。
   - 目录缺版本清单那段时按只有一版处理，老目录不必重发。
   - 在线目录的发布与刷新见 [release-workflow.md](release-workflow.md) 的「子仓供件」节。
   - 判定只看声明里写明的值与字段形态，仓名与附件名都不参与。
2. 每只平台适配器一只独立仓，clone 进装载根 `finshin/adapter/` 下的一个目录里，主仓不记这笔登记。
   - 声明文件是仓根的 `pyproject.toml`，代码在 `src` 那一层，由 `package-dir` 映射成包，包名由 `[project].name` 定。
   - 装载侧按声明里的模块名取件，代码从环境里那只包来，取不到就走拒载那句交代。
   - 包目录改名必须同步改声明里 `[project.entry-points]` 那条值，两处同名才算一只包。
   - 适配器可从面板联网安装，源码开发见「挂载子仓」节。
   - 同名同职责的模块平铺在包里，平台独有的机制放包里的 `features/`。
   - 开发说明见那只适配器仓自己的 README。
   - 入口由 `[project.entry-points."finshin.adapters"]` 那一段交出：键写平台标识，值写「入口模块:parts」，冒号后那个名字由本体规定。声明缺件、字段非法或入口点不点名本平台的适配器整份不进表。
   - `[project].dependencies` 里 pin 的引擎库随那只 wheel 装进环境时一起带上，依赖同步删库时被保留。
   - 该不该装只看在线版本比本机版本新不新，相等与更旧都不动。
   - 逐行还能从版本清单里挑一版装，挑更旧那版即回退，走的还是同一条 `--find-links` 装法。
   - 核过指纹的件把指纹记进同目录一份 `downloaded.json`，目录取不到时本机记过的那几份仍算可装。
   - 盘上那份件既不在目录里、本机也没记过指纹时没有权威值可核，那一版不给装。
   - 来源那一行分四档：源码仓挂着（装进环境与没装进环境各一档）、只有环境里那只包、本机没有。
   - 卸载那颗只在本机没有源码仓挂着时出，源码仓挂着即不给卸。
   - 来路那一行点名该装的那一版从哪儿取：本机已下载的件、在线目录、源码仓三档。
   - 版本串读不懂按不动处理。
   - 一条 uv 命令带全部 wheel 与 `--find-links`，接口包与适配器互相喂依赖。
   - 装不进运行环境的按发行件逐只点名，不只报一句失败。
   - 卸一只适配器只动那只包与只有它声明过的库，这一平台还有实例即先拦下来要人删实例。
   - 已装的接口包进保留清单，卸掉最后一只适配器再点同步也不会被删。
   - 平台自带库的版本号以 `[project].dependencies` 这一行为准，本体的 `pyproject.toml` 不重复钉这些包。
   - `[tool.finshin-adapter]` 写平台标识 `platform`。
   - 接口包版本要求写在 `[project].dependencies` 里的 `finshin-sdk` 那一条，形如 `>=0.1.0,<0.2.0`，上下限都算数，没写即不设限。
   - 本机接口包不在要求的区间内即拒在装载入口之前，弹窗与日志各落一句写明要求与本机版本。
   - 子仓版本号与 release 附件见 [release-workflow.md](release-workflow.md) 的「子仓供件」节。
   - 装载侧认两路读声明：`finshin/adapter/` 里那份，与装进环境的适配器包各自的元数据。同一平台两路都在时认目录里那一份。
   - 适配器声明里的 `[tool.finshin-adapter].platform` 是平台码的对外出处，目录生成侧只读它。
   - 单独生成在线目录见 [packaging.md](packaging.md) 的「在线目录」节。
3. 分层与导入方向见 [coding-style.md](coding-style.md) 的「分层职责」节。
   - 接口包安装见「环境搭建」节，源码挂载见「挂载子仓」节。
   - wheel 构建与随包安装见 [packaging.md](packaging.md) 的「子仓构建」节。
4. 入口模块交出运行时装配、频道探测与引擎预热，运行时实例交出交互端口、插件路由挂载口与路由清单编译器。
5. 日志中间件实例由装载侧交来，挂上更新链那一步由各平台自己认，按启用序列注册插件全归装载侧。

## 挂载子仓

开发只在克隆出来的仓库里做。发布物是给用户用的绿色目录，里面没有工具配置、没有用例树、也没有 `.git`，拿它当开发环境只会发现形状缺一片。

- 挂载点有两处：平台适配器是 `finshin/adapter/<平台码>`，接口包是 `finshin/sdk`。
- 适配器那棵留下空壳目录时，装载侧读不到声明会跳过。
- 接口包那棵缺位时，本体 import 失败。

| 仓名 | 分发名 | 导入名 | 挂载点 |
| :--- | :--- | :--- | :--- |
| `FinshinSDK` | `finshin-sdk` | `finshin_sdk` | `finshin/sdk` |
| `FinshinAdapterTG` | `finshin-adapter-tg` | `finshin_adapter_tg` | `finshin/adapter/tg` |

1. 挂载：`git clone <子仓地址> <挂载点>`。
2. 日常改动：在挂载点目录里改、提交，推送跑 `git -C <挂载点> push origin main`，只推子仓自己那一笔，主仓这边没有要提的东西。
3. 改完生效：跑 `.venv\Scripts\uv.exe sync --all-packages --reinstall-package <分发名>`，普通 sync 不重装子仓那棵。
4. 面板与运行时读的都是环境里那只包：不重跑这一步，屏上的版本号和行为都还是旧源码的。
5. 更新：`git -C <挂载点> pull`。主仓 pull 不带动子仓，两边各拉各的。
6. 摘掉：连目录一并删掉 `<挂载点>`。
7. 主仓不记子仓停在哪个提交号。要把两边版本对上，看各自声明里的版本号。

## 新增规范扫描分节

1. 先在 [coding-style.md](coding-style.md) 写条文，写明判据与后果。
2. 在 `devtools/_style_checks/` 新建模块，只依赖 `_common`。
   - 单文件检查导出 `check(files)`。
   - 跨模块消费者检查导出 `check(files, graph)`。
3. 在 `_common.py` 的 `SECTIONS` 加同名一项，分节名写法见 [style-checker.md](style-checker.md) 的「分节登记」节。
   - 单文件检查进 `_registry.py` 的 `_FILE_CHECKS`。
   - 导入图检查在 `run_checks` 里单独调用并传入导入图。
4. 在 `devtools/tests/test_style_checker_meta.py` 的 `_SAMPLES` 补样本，要求见 [testing.md](testing.md) 的「加用例的判据」节。
5. 跑 `python devtools\check_coding_style.py devtools` 自查。
6. 跑 `python -m pytest devtools/tests/test_style_checker_meta.py`。

## 发布流程

版本号与 CHANGELOG 归段、tag、release、版本页收尾统一见 [release-workflow.md](release-workflow.md)，构建与本地实测见 [packaging.md](packaging.md)。

## 更新方式

- **"版本检查"按钮**：开发版与打包版都只比对在线版本号并弹窗提示有无新版，不当场更新，发现新版时提示重启本程序、由启动器自动完成升级。顺带拉一次发布说明清单，把弹窗焦点定到那一支版本。
- **开发版**：手动拉取新代码（`git pull` 或下载源码覆盖），依赖有变动时重跑上文环境搭建的 `uv sync --all-packages`。
- **打包版**：启动器每次拉起主程序前自动比对版本，弹窗确认后完成下载升级，用户配置、数据与日志一律保留。
  - 启动器本体随升级当场更换，换壳机制见 [packaging.md](packaging.md)。
  - 各版本走自动升级还是手动整包，见根目录 [README.md](../README.md) 的旧版迁移。
