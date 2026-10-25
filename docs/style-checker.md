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

- 每条违规带标记：`[H]` 硬性，规则明确可判，须改。`[?]` 待核，启发式提示，人工判断后再改。
- 待核条数与上一轮比对，只许减不许增。审过的写进豁免清单，见下节。
- 扫开发者内容跑 `python devtools\check_coding_style.py devtools`，应保持 0 硬性。
- 措辞类（背景解释、变更叙述、自评句）静态查不出，交付前对改动文件 grep 一遍禁词。

## 待核豁免清单

审过并决定不改的待核登记在 `devtools/style_waivers.toml`，随仓库走，扫到同一条即静音，末尾补一行「已豁免 N 条」。

一条三项：`section`、`path`、`reason`，可选 `match` 收口到消息里的关键字。
匹配只看分节、文件与消息子串，不写行号——行号随每次插删代码漂移，清单会变成新的待核。

- 只罩待核。硬性违规在 `Waiver.covers` 里直接判不罩，清单挡不住真违规。
- 只登记裁定永久不改的。将来一定会有消费方的预留符号、还没拍板的取舍一律留在待核池子，
  别提前签进清单——清单把一次未定刷成永久静音，待核每次都会重新摆到眼前，池子留活口正是它的用处。
- 条目不再命中即转成一条硬性「失效豁免」报出，闸门当场红，逼着代码改完回来删清单，防条目只增不减。
- 只有全分节扫 `src` 根才判失效，点名扫子目录时清单可能本来就不命中，不误报。
- 加条目前先问是哪个判据太宽，能收紧判据就别拿豁免兜底。

## 分节与检查文件

一个分节一个模块，摆在 `devtools/_style_checks/`，文件名前缀记的是并进规范的先后，与分节顺序无关。

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

## 回调形参查四样

- 带 `Message` 注解的协程形参须叫 `raw` 且排首位，两个都错就报两条 —— 硬性。
- 注解为 `HandlerContext` 的形参须叫 `ctx`，改了名框架按名取不到上下文 —— 硬性。
- 类名以 `Middleware` 结尾的 `__call__`，三形参按 `handler, event, data` 排且不许加 `*` —— 硬性。
- 必填参数后紧跟同型可选参数，提示加 `*` 隔开防实参错位 —— 待核，类型文本一致才算同型。

协程里一个带事件注解的形参都没有，就不查注入位。业务协程收上下文对象当数据传属正常写法，按注入位判会误报。

「分层职责」不在扫描器里，由 `.importlinter` 的契约管依赖方向，跑 `.venv\Scripts\lint-imports.exe`。
契约只判谁准 import 谁，某层内部写了什么业务规则它看不见，那部分仍靠人工评审。

## 加一节的做法

1. `coding-style.md` 先写条文，写明判据与后果。
2. `_style_checks/` 新建模块，导出 `check(files)`，只依赖 `_common`，
   违规条目里把分节名写成字面量。
3. `_common.py` 的 `SECTIONS` 加同名一项，`_registry.py` 的 `_FILE_CHECKS` 加一项。
4. `devtools/tests/test_style_checker_meta.py` 的 `_SAMPLES` 补一组必中样本，写进真违规那一处即可。
   - 样本只落临时目录，不许留在 `src`。
   - 不补这组，新分节空转没人看得见。
5. 跑 `python devtools\check_coding_style.py devtools` 自查，再跑一遍 `python -m pytest devtools/tests/test_style_checker_meta.py`。

分节清单只有 `SECTIONS` 一处，模块写错名字在排序时当场报错，不会静默漏检。
过去分节靠 `SECTIONS` 的下标取名字，插进「枚举」后下标整体错一位，
类型注解的违规被记到「文案类」名下，现统一改写字面量。

## 测试目录豁免

名为 `tests` 的目录整体跳过（`_common.py` 的 `_EXCLUDE_DIRS`），点名扫它也 0 条。
测试站在包外观察私有成员、桩函数不标类型都属正常写法，套生产口径只会产出假违规。
用例侧的其余口径见 [testing.md](testing.md)。
