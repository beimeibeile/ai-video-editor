"""
占位图生成器 — 纯色/数字/简单图形占位图
用于模式B仿制模板的可替换素材标记
"""
from PIL import Image, ImageDraw, ImageFont
import os

# 常用比例
RATIOS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:3": (1440, 1080),
    "3:4": (1080, 1440),
}

# 背景色预设
BG_COLORS = [
    (255, 87, 87),    # 红
    (255, 159, 67),   # 橙
    (255, 212, 59),   # 黄
    (46, 213, 115),   # 绿
    (30, 144, 255),   # 蓝
    (165, 94, 234),   # 紫
    (255, 121, 198),  # 粉
    (0, 206, 209),    # 青
    (255, 165, 0),    # 金
    (128, 128, 128),  # 灰
    (255, 255, 255),  # 白
    (30, 30, 30),     # 深灰
]


def generate_placeholder(number=1, ratio="9:16", bg_color=None, output_path=None):
    """
    生成单张数字占位图
    
    Args:
        number: 显示的数字
        ratio: 比例 9:16/16:9/1:1/4:3/3:4
        bg_color: 背景色RGB tuple，None则按数字自动分配
        output_path: 输出路径
    """
    size = RATIOS.get(ratio, (1080, 1920))
    if bg_color is None:
        bg_color = BG_COLORS[number % len(BG_COLORS)]
    
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)
    w, h = size
    
    # 文字颜色：深色背景用白字，浅色背景用黑字
    luminance = bg_color[0]*0.299 + bg_color[1]*0.587 + bg_color[2]*0.114
    text_color = (255, 255, 255) if luminance < 128 else (0, 0, 0)
    
    # 加载字体
    font_size = min(w, h) // 3
    font = None
    for fp in ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/Arial.ttf"]:
        if os.path.exists(fp):
            font = ImageFont.truetype(fp, font_size)
            break
    if font is None:
        font = ImageFont.load_default()
    
    text = str(number)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (w - tw) // 2 - bbox[0]
    y = (h - th) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=text_color)
    
    # 比例标签（小字）
    label_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", min(w, h)//20) if os.path.exists("C:/Windows/Fonts/arial.ttf") else font
    label = ratio
    lb = draw.textbbox((0, 0), label, font=label_font)
    lw = lb[2] - lb[0]
    draw.text(((w-lw)//2, h - min(w,h)//10), label, font=label_font,
              fill=tuple(max(0,c-60) for c in text_color))
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)
        return output_path
    return img


def generate_placeholder_batch(start=0, end=30, ratio="9:16", output_dir=None):
    """
    批量生成数字占位图
    
    Args:
        start: 起始数字
        end: 结束数字（含）
        ratio: 比例
        output_dir: 输出目录
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "reusable", "placeholders")
    os.makedirs(output_dir, exist_ok=True)
    
    ratio_safe = ratio.replace(":", "x")
    paths = []
    for n in range(start, end + 1):
        path = os.path.join(output_dir, f"placeholder_{n:02d}_{ratio_safe}.png")
        generate_placeholder(n, ratio, output_path=path)
        paths.append(path)
    
    print(f"✅ 生成 {len(paths)} 张占位图 ({ratio}) -> {output_dir}")
    return paths
