# 规范扫描器

扫描器在 `devtools/check_coding_style.py`，按 [coding-style.md](coding-style.md) 的分节静态检查代码。
只报不改，输出供人工核实。

## 跑法

```powershell
# 默认扫 src，按分节输出违规清单
python devtools\check_coding_style.py

# 只扫指定目录或文件
python devtools\check_coding_style.py src\bot

# 只看规则明确可判的硬性违规
python devtools\check_coding_style.py --hard-only

# 只看某一节，可重复
python devtools\check_coding_style.py --section 注释
```

- 命令行给了路径就只扫那几个，没给即默认扫 `src`。
- 仓库根 `CHANGELOG.md` 恒随装载，不受命令行路径影响，非 py 文件只进 CHANGELOG 细则。
- 子仓的 py 文件按挂载现场点名进扫描，闸门那条命令自动带上，手动跑就把目录写上。
- 本机没挂上那只子仓就没得扫。
  - 包名按各仓项目声明里的 setuptools 改名表算，主仓不写第二份子仓名字。
  - 没有那份声明才退回按目录上溯算名。
- 每条违规带标记：
  - `[H]` 硬性，规则明确可判，须改。
  - `[?]` 待核，启发式提示，人工判断后再改。
- 待核条数与上一轮比对，只许减不许增。
  - 基线取登记完豁免清单后的读数。
  - 预留待接的项照样报，不算新增。
- 提交与发布的扫描范围、通过标准见 [release-workflow.md](release-workflow.md) 的「五项闸门（提交与发布前跑齐）」节。
- 子仓检查范围见 [release-workflow.md](release-workflow.md) 的「子仓供件」节。
- 测试目录的跳过机制见「测试目录豁免」节，其余用例放宽项见 [testing.md](testing.md)。
- 措辞类（背景解释、变更叙述、自评句）静态查不出，禁词清单与 grep 兜底见 [coding-style.md](coding-style.md)。

## 待核豁免清单

审过并决定不改的待核登记在 `devtools/style_waivers.toml`，随仓库走，扫到同一条即静音，末尾补一行「已豁免 N 条」。

一条由 `section`、`path`、`reason` 组成，可选 `match` 收口到消息里的关键字。
匹配只看分节、文件与消息子串，不写行号。

罩什么：

- 只罩待核。
- 单文件行数超限不罩，只拆分或改 `_s2_split.py` 的扫描阈值。

登记什么：

- 只登记裁定永久不改的。
- 预留待接的符号与还没拍板的项留在待核。
- 加条目前先问是哪个判据太宽，能收紧判据就别拿豁免兜底。

什么时候算失效：

- 条目不再命中即转一条硬性「失效豁免」报出。
- 本轮没装载的路径不作数，只扫本体时指向子仓的条目不算失效。
- 只扫单个分节也不作数，其余分节的条目本来就没进这一轮。
- `--hard-only` 只裁输出，豁免命中与失效一律按全量待核算。

## 分节与检查文件

一个分节一个主模块，摆在 `devtools/_style_checks/`。
细则太多就再拆委托模块（`_s5b`／`_s5c`／`_s6b`），由主模块调用，不单独登记。

- 文件骨架：`_s1_skeleton.py`
- 拆分粒度：`_s2_split.py`
- Docstring：`_s3_docstring.py`
- 注释：`_s4_comment.py`
- 命名与门面导出：`_s5_naming.py`、`_s5b_naming_style.py`、`_s5c_constants.py`、`_s5d_access.py`
- 魔法数字与字符串：`_s6_magic.py`、`_s6b_protocol_strings.py`、`_s6c_link_home.py`
- 枚举：`_s5e_enum.py`
- 日志与文案：`_s7_text.py`、`_s7b_changelog.py`（CHANGELOG 载体由登记表直连）
- 文案类：`_s8_messages.py`
- 回调形参：`_s8b_callback_param.py`
- 类型注解：`_s9_typing.py`
- 导入：`_s10_import_direction.py`

`_waivers.py` 不属于任何分节，只负责读清单与按清单静音。

「分层职责」不由本扫描器检查，判据见 [coding-style.md](coding-style.md) 的「分层职责」节，检查命令见 [release-workflow.md](release-workflow.md)。

## 工具树直连内部实现

允许范围见 [coding-style.md](coding-style.md) 的「命名与门面导出」节。

- 私有模块访问检查由 `_s5d_access` 执行。
- 消费者范围检查由 `_s5_naming` 执行。

## 符号私有性查哪些名字

「对外」判据见 [coding-style.md](coding-style.md) 的「命名与门面导出」节。

检查范围：

- 模块级的函数、类与别名赋值都进检查。
- 别名赋值按名字样式分档认领，全大写与小写蛇形两档归 `_s5c_constants`，大写开头的驼峰别名归 `_s5_naming`，一个名字只由一档判，不重复报。
- 右侧是 `TypeVar`／`NewType`／`ParamSpec`／`TypeAliasType` 调用的不判。
- 标识类型集中定义处按设计公开。
- 模块级小写蛇形赋值走 `_s5c_constants` 的另一条判据（加 `_` 前缀或收进命名空间类），不看消费者。

## 回调形参查什么

形参写法见 [coding-style.md](coding-style.md) 的「回调形参」节。

- 协程形参含 `Message` 注解或 `platform_raw` 时进入回调检查，否则跳过。
- 事件与上下文形参的命名、位置、注解违规报硬性。
- 类名以 `Middleware` 结尾时检查 `__call__`，形参与关键字隔断违规报硬性。
- 同步函数与协程都检查相邻必填、可选参数是否同型，命中时报待核。
- 同型比对前去掉类型文本中的空格与末尾 `|None`。

## 分节登记

新增步骤见 [development.md](development.md) 的「新增规范扫描分节」节。

- 分节名在各检查模块里写死字面量，不按 `SECTIONS` 的位置取。
- 模块写了 `SECTIONS` 里没有的名字，排序时当场报错。
- 检查模块未接入 `_registry.py` 时不会执行。

## 测试目录豁免

名为 `tests` 的目录整体跳过（`_common.py` 的 `_EXCLUDE_DIRS`），点名扫它也 0 条。
用例侧的其余口径见 [testing.md](testing.md)。
