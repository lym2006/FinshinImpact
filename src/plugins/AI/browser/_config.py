# src/plugins/AI/browser/_config.py
"""浏览器启动配置（内部实现）

- 定义 Playwright 启动参数
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BrowserConfig:
    """浏览器配置"""

    # PlayWright 浏览器参数
    args: tuple[str, ...] = field(
        default_factory=lambda: (
            "--disable-gpu",  # 禁用GPU硬件加速，无头服务器无显卡驱动，防黑屏崩溃
            "--no-sandbox",  # 关闭沙箱隔离，Linux/Docker环境下Chrome默认权限不足无法启动沙箱
            "--force-device-scale-factor=2",  # 200% 像素密度，保证截图清晰
            "--high-dpi-support=2",  # 配合上面的高 DPI 支持
            "--disable-font-antialiasing",  # 关闭字体抗锯齿，减少边框颜色渲染偏差
            "--disable-partial-raster",  # 禁用部分光栅化，减少渲染管线干预
            "--ignore-certificate-errors",  # 忽略SSL证书错误，file:///协议加载本地资源用
            "--allow-insecure-localhost",  # 允许localhost访问不安全内容
            "--disable-dev-shm-usage",  # 服务器/Docker 环境防崩溃
        )
    )


# 实例化为全局单例
browser_config = BrowserConfig()
