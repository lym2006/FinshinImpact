# 规范扫描器

本体在 `devtools/check_coding_style.py`，按 [`coding-style.md`](coding-style.md) 的分节静态检查代码。
只报不改，输出供人工核实。

## 跑法

```powershell
python devtools\check_coding_style.py                # 默认扫 src，按分节输出违规清单
python devtools\check_coding_style.py src\bot        # 只扫指定目录或文件
python devtools\check_coding_style.py --hard-only    # 只看规则明确可判的硬性违规
python devtools\check_coding_style.py --section 注释  # 只看某一节，可重复
```

- 每条违规带标记：`[H]` 硬性，规则明确可判，须改。`[?]` 待核，启发式提示，人工判断后再改。
- 待核条数与上一轮比对，只许减不许增。
- 扫开发者内容跑 `python devtools\check_coding_style.py devtools`，应保持 0 硬性。
- 措辞类（背景解释、变更叙述、自评句）静态查不出，交付前对改动文件 grep 一遍禁词。

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

「分层职责」不在扫描器里，由 `.importlinter` 的契约把关，跑 `.venv\Scripts\lint-imports.exe`。

## 加一节的做法

1. `coding-style.md` 先写条文，写明判据与后果。
2. `_style_checks/` 新建模块，导出 `check(files)`，只依赖 `_common`，
   违规条目里把分节名写成字面量。
3. `_common.py` 的 `SECTIONS` 加同名一项，`_registry.py` 的 `_FILE_CHECKS` 加一项。
4. 造一个必中的探针文件实跑一遍，验完即删，探针不许留在 `src`。
5. 跑 `python devtools\check_coding_style.py devtools` 自查。

分节清单只有 `SECTIONS` 一处，模块写错名字在排序时当场报错，不会静默漏检。
过去分节靠 `SECTIONS` 的下标取名字，插进「枚举」后下标整体错一位，
类型注解的违规被记到「文案类」名下，现统一改写字面量。

## 测试目录豁免

名为 `tests` 的目录整体跳过（`_common.py` 的 `_EXCLUDE_DIRS`），点名扫它也 0 条。
测试站在包外观察私有成员、桩函数不标类型都属正常写法，套生产口径只会产出假违规。
用例侧的其余口径见 [testing.md](testing.md)。
