"""
轮廓图生成器 — 黑底白边描边图
用于正片叠底混合模式：黑色背景透出下层彩色，白色轮廓显示下层颜色
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

def generate_outline(shape="circle", size=(1920, 1080), line_width=8,
                     output_path=None, add_decorations=True):
    """
    生成黑底白边轮廓图
    
    Args:
        shape: 形状类型 circle/rect/star/heart/custom
        size: 画布尺寸 (width, height)
        line_width: 描边宽度
        output_path: 输出路径，None则返回Image对象
        add_decorations: 是否添加装饰刻度线
    
    Returns:
        output_path 或 Image对象
    """
    img = Image.new('RGB', size, (0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = size
    cx, cy = w // 2, h // 2
    
    if shape == "circle":
        r = min(w, h) // 3
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(255,255,255), width=line_width)
        # 内圈
        r2 = int(r * 0.82)
        draw.ellipse([cx-r2, cy-r2, cx+r2, cy+r2], outline=(255,255,255), width=max(2, line_width//3))
        if add_decorations:
            # 刻度线
            for i in range(12):
                angle = i * 30 * math.pi / 180
                x1 = cx + int((r + 15) * math.cos(angle))
                y1 = cy + int((r + 15) * math.sin(angle))
                x2 = cx + int((r + 35) * math.cos(angle))
                y2 = cy + int((r + 35) * math.sin(angle))
                draw.line([x1, y1, x2, y2], fill=(255,255,255), width=max(2, line_width//3))
    
    elif shape == "rect":
        rw, rh = w // 3, h // 3
        draw.rectangle([cx-rw, cy-rh, cx+rw, cy+rh], outline=(255,255,255), width=line_width)
    
    elif shape == "star":
        r_outer = min(w, h) // 3
        r_inner = r_outer // 2
        points = []
        for i in range(10):
            angle = -math.pi/2 + i * math.pi / 5
            r = r_outer if i % 2 == 0 else r_inner
            points.append((cx + int(r*math.cos(angle)), cy + int(r*math.sin(angle))))
        draw.polygon(points, outline=(255,255,255), width=line_width)
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)
        return output_path
    return img


def generate_outline_from_text(text, size=(1920, 1080), font_size=200,
                               output_path=None, stroke_width=6):
    """
    生成黑底白边文字轮廓图（仅描边，不填充）
    
    Args:
        text: 文字内容
        size: 画布尺寸
        font_size: 字体大小
        output_path: 输出路径
        stroke_width: 描边宽度
    """
    img = Image.new('RGB', size, (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体
    font = None
    for font_path in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/msyhbd.ttc",
    ]:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
            break
    if font is None:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size[0] - tw) // 2 - bbox[0]
    y = (size[1] - th) // 2 - bbox[1]
    
    # 只描边不填充（fill=黑色=背景色，stroke=白色）
    draw.text((x, y), text, font=font, fill=(0,0,0),
              stroke_width=stroke_width, stroke_fill=(255,255,255))
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)
        return output_path
    return img
