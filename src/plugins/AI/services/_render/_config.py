# src/plugins/AI/services/_render/_config.py
"""渲染配置（内部实现）

- 定义浏览器运行与自动化参数
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class RenderConfig:
    """渲染配置"""

    max_concurrent_screenshots: int = 3  # 最多允许同时执行的截图任务数

    # Playwright 超时与等待时间（单位：毫秒）
    page_load_timeout: int = 30000  # 界面加载超时
    wait_after_load: int = 2000  # 界面加载后等待
    wait_after_resize: int = 1000  # 图片裁剪后等待

    # 视口尺寸配置
    viewport_safe_margin: int = 100  # 视口安全边距，防止内容贴边被裁切
    min_viewport_width: int = 800  # 最小视口宽度
    render_cavas_height: int = 10000  # 渲染画布高度（撑大视口，确保完整渲染，后续裁剪）

    # 智能裁剪颜色：检测 HTML 中定义的橙色背景边框 (#FFA500)
    orange_target: np.ndarray = field(default_factory=lambda: np.array([255, 165, 0]))


# 实例化为全局单例
render_config = RenderConfig()
