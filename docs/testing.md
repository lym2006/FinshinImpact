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

## 加用例的判据

- 改 `src` 行为就配一条回归，写得出一句「这条红了说明什么」才动手。
- 测私有函数可以，别为了好测把内部符号提升进门面。
- 同一分支的多种入参用 `subTest` 铺在一个用例里，别为每档复制一遍断言。
- `test_style_checker_meta.py` 查的是扫描器自己。
  - 十二个分节各备一份必违规样本，判据脱节即红。
  - 豁免清单留了不再命中的条目也红。

## 用例放宽的三处

风格上免三处，跑得过这条没免：ruff 其余规则照查，pytest 照跑，改名或漏文件照样红。

- 规范扫描器：`tests` 目录整体跳过，devtools 整树允许直连 src 的内部实现。机制与理由见 [style-checker.md](style-checker.md)。
- 类型检查（pyright）在 `pyproject.toml` 的 `[tool.pyright]` 里管两层。
  - `exclude` 让闸门跳过本目录。
  - 编辑器单开一个用例文件时 `exclude` 拦不住分析，所以另按目录配一套环境：`extraPaths` 补 `src` 与 `devtools`（用例运行时自己挂路径，静态层不补就整片报缺导入）。
  - 只关掉假件引起的两类报错（`reportArgumentType` 与 `reportAttributeAccessIssue`），其余照报。
- ruff 在 `ruff.toml` 里对本目录关掉 docstring 一组规则，测试函数名即文档。
