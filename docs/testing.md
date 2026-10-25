# 测试

用例全在 `devtools/tests/`，一份文件对一个主题，命名 `test_<主题>.py`。
条文见 [`coding-style.md`](coding-style.md)，静态检查见 [`style-checker.md`](style-checker.md)，
发布前的检查顺序见 [`release-workflow.md`](release-workflow.md)。

## 跑法

```powershell
# 全跑
python -m pytest

# 只跑一组，逐条列用例名
python -m pytest devtools/tests/test_grant_access.py -v
```

- 在项目根跑，`pytest` 自己找到 `devtools/tests`，无需配 `testpaths`。
- 用例直接 import `src` 下的真实模块，跑测试不需要装发布物，也不需要网络。

## 文件规矩

- 首行注释写文件自身路径，改名或搬动要连着改。
- 第二行模块 docstring 用要点列全本文件证明的行为，一条一个事实。
- 开头自行把 `src` 挂进 `sys.path`，全仓无 `conftest.py`，也不依赖已安装的包。
- 导入业务模块前先调 `set_profile` 落身份码，路径常量在导入期冻结，晚一步就取错实例目录。
- 真库用例每例自开临时库，收尾合并 WAL 再删目录，例与例不共享状态。
- 网络一律打桩，只验编排，不发真请求。

## 不套生产口径

三处豁免各有落点，免的都是风格，不免「跑得过」：

- 规范扫描器把名为 `tests` 的目录列进跳过名单（`devtools/_style_checks/_common.py`），
  跨包取私有函数、桩函数缺类型注解都不算违规。
- 类型检查在 `pyproject.toml` 的 `[tool.pyright]` 里分两层：`exclude` 让闸门跳过本目录；
  编辑器打开单个用例时 `exclude` 拦不住分析，另配一套按目录的环境——`extraPaths` 补 `src` 与
  `devtools`（用例运行期自己挂路径，静态层不补就整片报缺导入），只关掉假件那两类
  `reportArgumentType` 与 `reportAttributeAccessIssue`，其余照报。
- ruff 在 `ruff.toml` 里对本目录关掉 docstring 一组规则，测试函数名即文档。

ruff 的其余规则照查，pytest 照跑，改名或漏文件都过不了闸门。

## 加用例的判据

- 改 `src` 行为就配一条回归，写得出一句「这条红了说明什么」才动手。
- 测私有函数可以，别为了好测把内部符号提升进门面。
- 同一分支的多种入参用 `subTest` 铺在一个用例里，别为每档复制一遍断言。
- `test_style_checker_meta.py` 查的是扫描器自己。
  - 十二个分节各备一份必违规样本，判据脱节即红。
  - 豁免清单留了不再命中的条目也红。给扫描器加分节要连着补样本。
