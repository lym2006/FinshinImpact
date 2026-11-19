# 工程经验

这里沉淀实现过程中实测出来的经验：某条约束的真实成因、某个结论是怎么验出来的、哪条路踩过并为什么走不通。

代码见 [coding-style.md](../coding-style.md)，中文写法见 [writing-style.md](../writing-style.md)，发布流程见 [release-workflow.md](../release-workflow.md)，环境搭建见 [development.md](../development.md)。

## 怎么找

按使用场景查：

- 要搬文件、改符号名、改库结构、做兼容迁移 → [migration-and-renaming.md](migration-and-renaming.md)
- 要给一段代码或一个符号挑归宿、改依赖方向 → [layering.md](layering.md)
- 碰启动链路、引导期窗体、实例锁 → [bootstrap-and-startup.md](bootstrap-and-startup.md)
- 碰界面、样式表、控件尺寸，或要证明观感没变 → [gui-and-styles.md](gui-and-styles.md)
- 碰 asyncio、事件循环、Qt 跨线程、重连与轮询 → [concurrency.md](concurrency.md)
- 碰配置结构、实例数据、落盘与备份 → [config-and-data.md](config-and-data.md)
- 碰装依赖、子进程、打包产物与发布 → [deps-and-release.md](deps-and-release.md)
- 碰大模型调用、token 预算、人设与权限话术 → [model-and-persona.md](model-and-persona.md)
- 碰图片、GIF、渲染降级与输出格式 → [rendering-and-output.md](rendering-and-output.md)
- 闸门、lint、pyright、扫描器报绿但你怀疑 → [tooling-false-green.md](tooling-false-green.md)
- 想提一个以前讨论过的方案，先查有没有被否 → [rejected.md](rejected.md)

## 收录规矩

- 只收换个项目还用得上的抽象教训，实例写成类别说法。
- 安全相关的只写判据，不写攻防原文、模型输出原句与本项目泄露史。
- 文件路径与符号的写法见 [指针写法](../writing-style.md#指针写法)。
- 第三方 API 的键名、命令行与工具名照写。
- 新经验并进已有主题，找不到归属才另开一份。
- 每节开头交代适用场景，再写成因与做法。
- 数字写明实测条件，不写成普适常数。
- 文末记录核实日期。

收录规矩核实日期：2026-11-17。
