"""
背景图生成器 — 纯色/渐变/抽象背景
"""
from PIL import Image, ImageDraw, ImageFilter
import os, math, random

RATIOS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}


def generate_background(style="dark_gradient", ratio="16:9", output_path=None, **kwargs):
    """
    生成背景图
    
    Args:
        style: 样式 dark_gradient/light_gradient/solid/noise/radial_glow
        ratio: 比例
        output_path: 输出路径
    """
    size = RATIOS.get(ratio, (1920, 1080))
    w, h = size
    
    if style == "solid":
        color = kwargs.get("color", (20, 20, 30))
        img = Image.new('RGB', size, color)
    
    elif style == "dark_gradient":
        c1 = kwargs.get("color1", (10, 10, 30))
        c2 = kwargs.get("color2", (40, 10, 60))
        img = _linear_gradient(w, h, c1, c2, angle=135)
    
    elif style == "light_gradient":
        c1 = kwargs.get("color1", (240, 240, 250))
        c2 = kwargs.get("color2", (220, 230, 250))
        img = _linear_gradient(w, h, c1, c2, angle=135)
    
    elif style == "radial_glow":
        center = kwargs.get("color", (100, 50, 150))
        edge = kwargs.get("edge_color", (10, 10, 20))
        img = _radial_glow(w, h, center, edge)
    
    elif style == "noise":
        base = kwargs.get("color", (30, 30, 40))
        img = _noise_bg(w, h, base, kwargs.get("intensity", 20))
    
    else:
        img = Image.new('RGB', size, (20, 20, 30))
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)
        return output_path
    return img


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))


def _linear_gradient(w, h, c1, c2, angle=135):
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    rad = math.radians(angle)
    dx, dy = math.cos(rad), math.sin(rad)
    length = abs(dx)*w + abs(dy)*h
    for y in range(h):
        for x in range(w):
            t = max(0, min(1, (x*dx + y*dy)/length)) if length > 0 else 0
            pixels[x, y] = _lerp(c1, c2, t)
    return img


def _radial_glow(w, h, center, edge):
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    cx, cy = w//2, h//2
    max_r = math.sqrt(cx**2 + cy**2)
    for y in range(h):
        for x in range(w):
            r = math.sqrt((x-cx)**2 + (y-cy)**2) / max_r
            t = max(0, min(1, r))
            pixels[x, y] = _lerp(center, edge, t)
    return img


def _noise_bg(w, h, base, intensity=20):
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    random.seed(42)
    for y in range(h):
        for x in range(w):
            n = random.randint(-intensity, intensity)
            pixels[x, y] = tuple(max(0, min(255, base[i]+n)) for i in range(3))
    return img.filter(ImageFilter.GaussianBlur(1))
