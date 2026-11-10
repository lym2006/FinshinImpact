# src/bundled/help/_render.py
"""帮助图绘制

- 只负责画图与落盘，菜单数据与缓存判定留在服务层
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class HelpRenderConfig:
    """帮助菜单图片渲染配置"""

    font_size: int = 30
    line_spacing: int = 18
    padding: int = 15
    column_gap: int = 60  # 左列与说明列的像素间距
    flag_indent: int = 4  # 开关行缩进字符数
    color_mode: str = "RGB"
    palette_colors: int = 64  # 落盘转索引色后的调色板色数
    bg_color: str = "#FFFFFF"
    text_color: str = "#000000"


def draw_menu(
    cells: list[tuple[str, str | None]],
    config: HelpRenderConfig,
    font_path: Path,
    save_path: Path,
) -> None:
    """按左右两列画出菜单图并落盘

    - 左列取最宽一条定列宽，说明列按像素对齐
    - 段名与空行不分列，空行绘成整行留白
    """
    font = ImageFont.truetype(str(font_path), config.font_size)
    padding = config.padding
    left_width = max(
        (font.getlength(left) for left, note in cells if note is not None), default=0.0
    )
    desc_x = padding + left_width + config.column_gap
    max_width = max(
        (
            desc_x + font.getlength(note) if note is not None else font.getlength(left)
            for left, note in cells
        ),
        default=0.0,
    )

    line_height = config.line_spacing + config.font_size
    img = Image.new(
        config.color_mode,
        (int(max_width) + padding * 2, len(cells) * line_height + padding * 2),
        config.bg_color,
    )
    dr = ImageDraw.Draw(img)

    for index, (left, note) in enumerate(cells):
        y = padding + index * line_height
        dr.text((padding, y), left, font=font, fill=config.text_color)
        if note is not None:
            dr.text((desc_x, y), note, font=font, fill=config.text_color)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    palette = img.convert(
        "P", palette=Image.Palette.ADAPTIVE, colors=config.palette_colors
    )
    palette.save(save_path)
