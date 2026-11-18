# 测试

用例在两处：本体在 `devtools/tests/`，各平台适配器随子仓带在 `finshin/adapter/<平台>/tests/`。一份文件对一个主题，命名 `test_<主题>.py`。
条文见 [coding-style.md](coding-style.md)，静态检查见 [style-checker.md](style-checker.md)，发布前的检查顺序见 [release-workflow.md](release-workflow.md)。

## 跑法

```powershell
# 全跑
python -m pytest

# 只跑一组，逐条列用例名
python -m pytest devtools/tests/test_grant_access.py -v
```

- 在项目根一条命令跑完两处。
- 收集范围写在 `pytest.ini` 的 `testpaths` 里。
  - `testpaths` 不展开通配，装载根那一棵只写根目录，pytest 自己走进去收各平台用例树。
  - 没挂载时那棵目录不在，收集范围少一条也不报错，只表现为用例数少一截。
- 本体用例直接 import `src` 下的真实模块，不需要装发布物。
- 用例侧共享件不带 `test_` 前缀，pytest 不收它们，只被用例 import。
- 子仓用例按各自包名引用，接口包与引擎库从环境取。

## 文件规矩

- 首行模块 docstring 用要点列出本文件证明的全部行为。
- 本体用例开头自行把 `src` 挂进 `sys.path`。
- 导入业务模块前先调 `set_profile` 落身份码。
- 真库用例每例自开临时库，收尾合并 WAL 再删目录，例与例不共享状态。
- 网络一律打桩，只验编排。

## 加用例的判据

- 改 `src` 行为就配一条回归，写得出一句「这条红了说明什么」才动手。
- 测私有函数可以，别为了好测把内部符号提升进门面。
- 同一分支的多种入参用 `subTest` 铺在一个用例里，别为每档复制一遍断言。
- `test_style_checker_meta.py` 查的是扫描器自己。
  - 每个分节各备一份必违规样本，判据脱节即红。
  - 样本只落临时目录，不留在 `src`。
  - 豁免清单留了不再命中的条目也红。

## 用例放宽的部分

风格上免这几处。

- 规范扫描器的目录豁免见 [style-checker.md](style-checker.md) 的「测试目录豁免」节。
- 内部实现的访问范围见 [coding-style.md](coding-style.md) 的「命名与门面导出」节。
- 类型检查（pyright）在 `pyrightconfig.json` 里管两层。
  - `exclude` 让闸门跳过本目录。
  - 编辑器单开一个用例文件时 `exclude` 拦不住分析，另按目录配一套环境：`extraPaths` 补 `src` 与 `devtools`。
  - 只关掉假件引起的两类报错（`reportArgumentType` 与 `reportAttributeAccessIssue`），其余照报。
- ruff 在 `ruff.toml` 里对本目录关掉 docstring 一组规则，测试函数名即文档。
