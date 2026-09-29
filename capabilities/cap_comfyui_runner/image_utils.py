"""
基础图片处理工具集
调整大小、格式转换、拼接、裁剪、旋转、翻转、加水印等
基于Pillow实现，不依赖ComfyUI
"""
import os
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def resize_image(
    input_path: str,
    output_path: str = None,
    width: int = None,
    height: int = None,
    keep_ratio: bool = True,
    quality: int = 95,
) -> str:
    """
    调整图片大小

    Args:
        input_path: 输入图片路径
        output_path: 输出路径（None则自动命名）
        width: 目标宽度（None则按height等比）
        height: 目标高度（None则按width等比）
        keep_ratio: 是否保持宽高比
        quality: JPEG质量（1-100）

    Returns:
        输出图片路径
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"图片不存在: {input_path}")

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_resized{ext}"

    img = Image.open(input_path)
    orig_w, orig_h = img.size

    if width and height:
        if keep_ratio:
            # 按比例缩放，适应目标尺寸
            ratio = min(width / orig_w, height / orig_h)
            new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
        else:
            new_w, new_h = width, height
    elif width:
        ratio = width / orig_w
        new_w, new_h = width, int(orig_h * ratio)
    elif height:
        ratio = height / orig_h
        new_w, new_h = int(orig_w * ratio), height
    else:
        new_w, new_h = orig_w, orig_h

    img = img.resize((new_w, new_h), Image.LANCZOS)

    # 保存
    ext = os.path.splitext(output_path)[1].lower()
    if ext in ['.jpg', '.jpeg']:
        img = img.convert('RGB')
        img.save(output_path, quality=quality)
    else:
        img.save(output_path)

    return output_path


def convert_format(
    input_path: str,
    output_path: str = None,
    target_format: str = "PNG",
    quality: int = 95,
) -> str:
    """
    转换图片格式

    Args:
        input_path: 输入图片路径
        output_path: 输出路径（None则自动命名）
        target_format: 目标格式（PNG/JPEG/WEBP/BMP/GIF/TIFF）
        quality: JPEG/WEBP质量

    Returns:
        输出图片路径
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"图片不存在: {input_path}")

    fmt_map = {
        "PNG": ".png", "JPEG": ".jpg", "JPG": ".jpg",
        "WEBP": ".webp", "BMP": ".bmp", "GIF": ".gif", "TIFF": ".tiff"
    }
    ext = fmt_map.get(target_format.upper(), ".png")

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}{ext}"

    img = Image.open(input_path)
    if target_format.upper() in ["JPEG", "JPG", "WEBP"]:
        img = img.convert('RGB')

    save_kwargs = {}
    if target_format.upper() in ["JPEG", "JPG"]:
        save_kwargs["quality"] = quality
    elif target_format.upper() == "WEBP":
        save_kwargs["quality"] = quality

    img.save(output_path, format=target_format.upper(), **save_kwargs)
    return output_path


def concat_images(
    image_paths: List[str],
    output_path: str,
    direction: str = "horizontal",
    gap: int = 0,
    background: Tuple[int, int, int] = (0, 0, 0),
    align: str = "center",
) -> str:
    """
    拼接多张图片

    Args:
        image_paths: 输入图片路径列表
        output_path: 输出路径
        direction: 拼接方向（horizontal/vertical/grid）
        gap: 图片间距（像素）
        background: 背景颜色（RGB）
        align: 对齐方式（center/top/left/bottom/right）

    Returns:
        输出图片路径
    """
    if len(image_paths) < 2:
        raise ValueError("至少需要2张图片")

    images = []
    for p in image_paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"图片不存在: {p}")
        images.append(Image.open(p).convert('RGBA'))

    if direction == "horizontal":
        # 水平拼接
        max_h = max(img.height for img in images)
        total_w = sum(img.width for img in images) + gap * (len(images) - 1)
        canvas = Image.new('RGBA', (total_w, max_h), background + (255,))
        x = 0
        for img in images:
            if align == "center":
                y = (max_h - img.height) // 2
            elif align in ["top", "left"]:
                y = 0
            else:
                y = max_h - img.height
            canvas.paste(img, (x, y), img)
            x += img.width + gap

    elif direction == "vertical":
        # 垂直拼接
        max_w = max(img.width for img in images)
        total_h = sum(img.height for img in images) + gap * (len(images) - 1)
        canvas = Image.new('RGBA', (max_w, total_h), background + (255,))
        y = 0
        for img in images:
            if align == "center":
                x = (max_w - img.width) // 2
            elif align in ["top", "left"]:
                x = 0
            else:
                x = max_w - img.width
            canvas.paste(img, (x, y), img)
            y += img.height + gap

    elif direction == "grid":
        # 网格拼接（自动计算行列）
        import math
        n = len(images)
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        cell_w = max(img.width for img in images)
        cell_h = max(img.height for img in images)
        total_w = cols * cell_w + gap * (cols - 1)
        total_h = rows * cell_h + gap * (rows - 1)
        canvas = Image.new('RGBA', (total_w, total_h), background + (255,))
        for i, img in enumerate(images):
            row, col = divmod(i, cols)
            x = col * (cell_w + gap) + (cell_w - img.width) // 2
            y = row * (cell_h + gap) + (cell_h - img.height) // 2
            canvas.paste(img, (x, y), img)
    else:
        raise ValueError(f"不支持的拼接方向: {direction}")

    # 保存
    ext = os.path.splitext(output_path)[1].lower()
    if ext in ['.jpg', '.jpeg']:
        canvas = canvas.convert('RGB')
    canvas.save(output_path)
    return output_path


def crop_image(
    input_path: str,
    output_path: str = None,
    box: Tuple[int, int, int, int] = None,
    ratio: str = None,
) -> str:
    """
    裁剪图片

    Args:
        input_path: 输入图片路径
        output_path: 输出路径（None则自动命名）
        box: 裁剪区域（left, upper, right, lower）
        ratio: 裁剪比例（如"1:1", "16:9", "9:16", "4:3", "3:4"），居中裁剪

    Returns:
        输出图片路径
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"图片不存在: {input_path}")

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_cropped{ext}"

    img = Image.open(input_path)
    w, h = img.size

    if box:
        img = img.crop(box)
    elif ratio:
        # 按比例居中裁剪
        rw, rh = map(int, ratio.split(":"))
        target_ratio = rw / rh
        current_ratio = w / h
        if current_ratio > target_ratio:
            # 太宽，裁剪左右
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            # 太高，裁剪上下
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

    img.save(output_path)
    return output_path


def rotate_image(
    input_path: str,
    output_path: str = None,
    angle: float = 90,
    expand: bool = True,
    fillcolor: Tuple[int, int, int] = (0, 0, 0),
) -> str:
    """
    旋转图片

    Args:
        input_path: 输入图片路径
        output_path: 输出路径（None则自动命名）
        angle: 旋转角度（逆时针为正）
        expand: 是否扩展画布以适应旋转后的图片
        fillcolor: 填充颜色

    Returns:
        输出图片路径
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"图片不存在: {input_path}")

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_rotated{ext}"

    img = Image.open(input_path)
    img = img.rotate(angle, expand=expand, fillcolor=fillcolor)
    img.save(output_path)
    return output_path


def flip_image(
    input_path: str,
    output_path: str = None,
    direction: str = "horizontal",
) -> str:
    """
    翻转图片

    Args:
        input_path: 输入图片路径
        output_path: 输出路径（None则自动命名）
        direction: 翻转方向（horizontal/vertical/both）

    Returns:
        输出图片路径
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"图片不存在: {input_path}")

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_flipped{ext}"

    img = Image.open(input_path)
    if direction == "horizontal":
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif direction == "vertical":
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    elif direction == "both":
        img = img.transpose(Image.ROTATE_180)
    else:
        raise ValueError(f"不支持的翻转方向: {direction}")

    img.save(output_path)
    return output_path


def add_watermark(
    input_path: str,
    output_path: str = None,
    text: str = "Watermark",
    position: str = "bottom-right",
    opacity: float = 0.5,
    font_size: int = 36,
    color: Tuple[int, int, int] = (255, 255, 255),
) -> str:
    """
    添加文字水印

    Args:
        input_path: 输入图片路径
        output_path: 输出路径（None则自动命名）
        text: 水印文字
        position: 位置（top-left/top-right/bottom-left/bottom-right/center）
        opacity: 不透明度（0-1）
        font_size: 字体大小
        color: 文字颜色

    Returns:
        输出图片路径
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"图片不存在: {input_path}")

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_watermarked{ext}"

    img = Image.open(input_path).convert('RGBA')
    w, h = img.size

    # 创建水印层
    watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)

    # 尝试加载字体
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    # 计算文字大小
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # 计算位置
    margin = 20
    positions = {
        "top-left": (margin, margin),
        "top-right": (w - text_w - margin, margin),
        "bottom-left": (margin, h - text_h - margin),
        "bottom-right": (w - text_w - margin, h - text_h - margin),
        "center": ((w - text_w) // 2, (h - text_h) // 2),
    }
    x, y = positions.get(position, positions["bottom-right"])

    # 绘制水印
    draw.text((x, y), text, font=font, fill=color + (int(opacity * 255),))

    # 合并
    result = Image.alpha_composite(img, watermark)
    ext = os.path.splitext(output_path)[1].lower()
    if ext in ['.jpg', '.jpeg']:
        result = result.convert('RGB')
    result.save(output_path)
    return output_path


def get_image_info(image_path: str) -> dict:
    """
    获取图片信息

    Returns:
        {width, height, mode, format, size_bytes, aspect_ratio}
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片不存在: {image_path}")

    img = Image.open(image_path)
    w, h = img.size
    return {
        "width": w,
        "height": h,
        "mode": img.mode,
        "format": img.format,
        "size_bytes": os.path.getsize(image_path),
        "aspect_ratio": round(w / h, 3) if h > 0 else 0,
    }


def batch_resize(
    image_paths: List[str],
    output_dir: str,
    width: int = None,
    height: int = None,
    keep_ratio: bool = True,
) -> List[str]:
    """批量调整图片大小"""
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for p in image_paths:
        fname = os.path.basename(p)
        out = os.path.join(output_dir, fname)
        results.append(resize_image(p, out, width, height, keep_ratio))
    return results


# 导出所有函数
__all__ = [
    "resize_image", "convert_format", "concat_images", "crop_image",
    "rotate_image", "flip_image", "add_watermark", "get_image_info",
    "batch_resize",
]


if __name__ == "__main__":
    print("基础图片处理工具集已加载")
    print("可用函数:")
    for fn in __all__:
        print(f"  - {fn}")
