# 规范扫描器

本体在 `devtools/check_coding_style.py`，按 [`coding-style.md`](coding-style.md) 的分节静态检查代码。
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

- 目标就是命令行给的那几个路径，不给默认 `src` 一个。末行「扫描 N 个目标」报的是路径条数，跟违规多少无关。
- 每条违规带标记：
  - `[H]` 硬性，规则明确可判，须改。
  - `[?]` 待核，启发式提示，人工判断后再改。
- 待核条数与上一轮比对，只许减不许增。基线取登记完豁免清单后的读数，预留待接的项照样报，不算新增。
- 闸门固定扫三棵树 `src packaging devtools`，都要 0 硬性，漏一棵就有照不到的地方。命令见 [release-workflow.md](release-workflow.md)。
- 措辞类（背景解释、变更叙述、自评句）静态查不出，禁词清单与 grep 兜底见 [coding-style.md](coding-style.md)。

## 待核豁免清单

审过并决定不改的待核登记在 `devtools/style_waivers.toml`，随仓库走，扫到同一条即静音，末尾补一行「已豁免 N 条」。

一条三项：`section`、`path`、`reason`，可选 `match` 收口到消息里的关键字。
匹配只看分节、文件与消息子串，不写行号（随插删代码漂移）。

罩什么：

- 只罩待核，硬性违规一律不罩。
- 单文件行数超限不罩，只拆分或改 `_s2_split.py` 的扫描阈值（罩住等于给那个文件永久关掉阈值）。

登记什么：

- 只登记裁定永久不改的。预留待接的符号、还没拍板留在待核。
- 加条目前先问是哪个判据太宽，能收紧判据就别拿豁免兜底。

什么时候算失效：

- 条目不再命中即转一条硬性「失效豁免」报出。
- 覆盖面扫到才判失效。目标含 `src` 根或仓库根算扫全。
- `--hard-only` 只裁输出。豁免命中与失效一律按全量待核算。

## 分节与检查文件

一个分节一个主模块，摆在 `devtools/_style_checks/`，文件名前缀记的是并进规范的先后，与分节顺序无关。
细则太多就再拆委托模块（`_s5b`／`_s5c`／`_s6b`），由主模块调用，不单独登记。

- 文件骨架：`_s1_skeleton.py`
- 拆分粒度：`_s2_split.py`
- Docstring：`_s3_docstring.py`
- 注释：`_s4_comment.py`
- 命名与门面导出：`_s5_naming.py`、`_s5b_naming_style.py`、`_s5c_constants.py`、`_s5d_access.py`
- 魔法数字与字符串：`_s6_magic.py`、`_s6b_protocol_strings.py`
- 枚举：`_s5e_enum.py`
- 日志与文案：`_s7_text.py`
- 文案类：`_s8_messages.py`
- 回调形参：`_s8b_callback_param.py`
- 类型注解：`_s9_typing.py`
- 导入：`_s10_import_direction.py`

`_waivers.py` 不属于任何分节，只负责读清单与按清单静音。

「分层职责」不在扫描器里，由 `.importlinter` 的契约管依赖方向，跑 `.venv\Scripts\lint-imports.exe`。
契约只判谁准 import 谁，层内业务规则仍靠人工评审。

## 工具树直连内部实现

devtools 整棵树允许直连 src 的内部实现，这条减免只管 devtools 往 src 伸手那一头：

- `_s5d_access`：`devtools/` 里的文件导入 src 的私有模块，不报越界。
- `_s5_naming`：src 里某个名字算不算「对外」，只看 src 自己有没有人用它。devtools 用它不算，所以只被工具用到的 src 符号照样报「没消费者，建议加 `_`」。
- 反过来，devtools 自己文件之间的调用（如 `_registry` 调各检查模块）算真实使用，工具树内部的命名照常判。

## 符号私有性查哪些名字

「对外」判据只在 [`coding-style.md`](coding-style.md)「命名与门面导出」写一处，本节只说扫描器捞哪些名字：
  - 模块级的函数、类与别名赋值三类名字都进检查。
  - 别名赋值按名字样式分档认领，全大写与小写蛇形两档归 `_s5c_constants`，大写开头的驼峰别名归 `_s5_naming`，一个名字只由一档判，不重复报。
  - 右侧是 `TypeVar`／`NewType`／`ParamSpec`／`TypeAliasType` 调用的不判。标识类型集中定义处按设计公开，逐个查消费者只会产出要豁免的噪音。
  - 模块级小写蛇形赋值走另一条判据（加 `_` 前缀或收进命名空间类），不看消费者，也在 `_s5c_constants`。

## 回调形参查四样

硬性：

- 带 `Message` 注解的协程形参须叫 `raw` 且排首位。
- 注解为 `HandlerContext` 的形参须叫 `ctx`，改了名框架取不到上下文。
- 类名以 `Middleware` 结尾的 `__call__`，三形参按 `handler, event, data` 排且不许加 `*`。

待核：

- 必填参数后紧跟同型可选参数，提示加 `*` 隔开防实参错位，类型文本一致才算同型。

本节只查框架回调。判据是协程的形参里有没有带事件类型注解（`Message` 这类）：一个都没有就当它是普通业务协程，整段跳过。
业务协程把上下文对象当普通数据传进来属正常写法，不跳就会假报。

## 加一节的做法

1. `coding-style.md` 先写条文，写明判据与后果。
2. `_style_checks/` 新建模块，只依赖 `_common`，违规条目里把分节名写成字面量。
   - 只看单个文件的导出 `check(files)`。
   - 要跨模块查消费者的导出 `check(files, graph)`。
3. `_common.py` 的 `SECTIONS` 加同名一项。
   - 单文件那类（`check(files)`）进 `_registry.py` 的 `_FILE_CHECKS`。
   - 要导入图那类（`check(files, graph)`）不进那张表，得在 `run_checks` 里单独调用并把导入图传进去。
   - 漏了不报错，只是这一节静默不查。
4. `devtools/tests/test_style_checker_meta.py` 的 `_SAMPLES` 补一组必中样本，写进真违规那一处即可。
   - 样本只落临时目录，不许留在 `src`。
   - 不补这组，新分节空转没人看得见。
5. 跑 `python devtools\check_coding_style.py devtools` 自查，再跑一遍 `python -m pytest devtools/tests/test_style_checker_meta.py`。

分节名在各检查模块里写死字面量，不按 `SECTIONS` 的位置取。新分节插进中间会让后面每一项的位置挪一位，位置取来的名字就对不上，违规记到隔壁分节名下。
模块写了 `SECTIONS` 里没有的名字，排序时当场报错。

## 测试目录豁免

名为 `tests` 的目录整体跳过（`_common.py` 的 `_EXCLUDE_DIRS`），点名扫它也 0 条。
测试站在包外观察私有成员，桩函数不写类型注解属正常写法，套生产口径只会产出假违规。
用例侧的其余口径见 [testing.md](testing.md)。
