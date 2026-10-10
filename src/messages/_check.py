# src/messages/_check.py
"""检查进度窗文案"""


class CheckMessage:
    """检查进度窗文案

    - 行骨架、通道称谓、轮次差异句、探测错误与面板日志五段话术的聚合入口
    - 校验轮与诊断轮共窗共词，轮专属句按 VERIFY_ / ADVICE_ 前缀分组
    """

    # 用：utils/net_probe.py 与 utils/diagnose.py 两轮的表行名（界面与生成器共用）
    ROW_CFG = "配置代理通道"
    ROW_SYS = "系统代理通道"
    ROW_DIRECT = "直连通道"
    ROW_PORT = "本地监听端口"
    ROW_LOCAL = "本地配置"
    ROW_ADVICE = "检查结论"

    # 用：两轮表格与日志的统一称谓，代理类一律带地址
    VIA_DIRECT = "直连"
    VIA_CFG = "配置代理 {proxy}"
    VIA_SYSTEM = "系统代理 {proxy}"

    # 用：未被单独探测的通道行绿色带过（前级已通/定案陪跑）
    SKIP = "跳过（前级已连通）"

    # 用：通道行成败句模板与两态
    REACH = "{via}：{state}"
    REACH_OK = "可达"
    REACH_FAIL = "不可用"

    # 用：结论行成功句——两轮同款
    ADVICE_OK = "已找到可用通道"

    # 用：gui/dialogs/_check.py 验证回调原地转绿的短句
    VERIFIED_OK = "配置验证通过"

    # 用：检查自身异常兜底句
    SELF_CRASH = "检查异常: {err}"

    # 用：gui/dialogs/_table.py 进行中行独立计时后缀（已测秒/预算秒）
    COUNTDOWN = "检测中 {n}/{budget}s"

    # 用：配置代理行——代理项留空
    CFG_EMPTY = "未配置（可填 http://127.0.0.1:端口）"

    # 用：系统代理行——不可用收口句（未开启或地址解析不出）
    SYS_UNAVAILABLE = "无可用系统代理（未开启或地址不可解析）"

    # 用：端口行——探活符号与默认组标注
    DIAG_PORT_ALIVE = "✓"
    DIAG_PORT_DEAD = "✗"
    DIAG_PORT_FALLBACK = "（默认组，未在配置/系统代理中发现端口）"

    # 用：仅靠端口扫描发现可用通道
    DIAG_ADVICE_ALT = "当前配置不通：把 {url} 填入代理配置项即可"

    # 用：全链不通
    DIAG_ADVICE_NONE = "未找到可用通道：启动代理软件后重试，或开启 TUN"

    # 用：端口行——复测实测可通的收口句
    VERIFY_PORT_HIT = "复测通过：{url}"

    # 用：端口行——本机未探到任何存活监听
    VERIFY_PORT_EMPTY = "未发现存活端口"

    # 用：端口行——存活候选全部实测不可用
    VERIFY_PORT_NONE = "存活端口均无法出网"

    # 用：通道行——仅换 token 复查时复用上轮结论
    VERIFY_REUSE = "复用已验证通道"

    # 用：本地配置行——类型校验全过
    VERIFY_LOCAL_OK = "全部通过"

    # 用：本地配置行——存在本地校验失败项，明细靠字段标红承载
    VERIFY_LOCAL_FAIL = "{n} 项未通过，详见标红字段"

    # 用：结论行失败汇总——表格走 HTML 渲染，多行明细会被吞，只留一句计数
    VERIFY_ADVICE_FAIL = "{n} 项配置异常"

    # 用：三通道全挂的聚合句
    ALL_FAIL = "配置代理 / 系统代理 / 直连均无法连通"

    # 用：全挂时引导自查的短尾句
    DIAGNOSE = "请点「网络诊断」自查"

    # 用：端口扫描发现可用地址的提示尾句
    PORT_HOVER = "检测到可用端口 {url}，请确认后填入"

    # 用：代理协议头为空时的占位描述
    SCHEME_EMPTY = "（空，缺少 :// 协议头）"

    # 用：配置值坏但被后续通道救活的提醒句
    STALE = "配置代理 {raw!r} 不可用，本次改用{via}，请自行修正"

    # 用：Token 结构本地校验失败句
    TOKEN_BAD_FORMAT = "Token 格式错误（应为 数字:密钥）"

    # 用：代理不通时 Token 的待复查标注
    TOKEN_PENDING = "{mark}：代理修复后复查"

    # 用：bot/_managers token 探测失败的致命弹窗，确认后退出重开选窗编辑
    TOKEN_FATAL = (
        "Token 无效，无法启动\n请退出后重新打开程序\n在选择窗编辑该实例更换 Token"
    )

    # 用：单通道探测超时的错误句（用户面不带秒数，秒数只进 debug 日志）
    TIMEOUT = "验证超时，请稍后重试"

    # 用：校验发起（reason 为 启动/保存/复验）
    VERIFY_START = "正在校验连通性（{reason}）"

    # 用：VERIFY_START 的三个触发原因
    REASON_STARTUP = "启动"
    REASON_SAVE = "保存"
    REASON_RECHECK = "复验"

    # 用：单通道耗时（debug 级，面板不展示）
    COST = "通道 {via} 探测耗时 {cost:.1f}s"

    # 用：校验通过的日志句
    PASS = "连通校验通过：生效通道 {via}"

    # 用：字段级失败的日志句
    FAIL = "连通校验失败：{fields}"

    # 用：校验通过后的真正落盘（文案避"配置"与结果词，归 💾）
    WRITTEN = "新值已写入磁盘"

    # 用：配置与诊断入口未就绪时的门控提示
    NOT_READY = "配置尚未就绪，稍后再试"

    # 用：面板单行日志：启动校验未出结论时点诊断的拦截
    STARTUP_BUSY = "启动校验进行中，网络诊断稍后再试"

    # 用：面板单行日志：他轮在途时开新轮的拦截（唯一窗互斥守卫）
    BUSY = "已有检查正在进行，请稍候再试"

    # 用：面板单行日志：保存流点"取消"，候选作废未落盘
    VERIFY_ABORTED = "已取消本次校验，候选配置未落盘"

    # 用：复验流点"取消"，无候选，仅中止后台轮
    VERIFY_STOPPED = "已取消本次校验"
