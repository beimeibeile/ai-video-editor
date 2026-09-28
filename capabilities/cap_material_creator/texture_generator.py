"""
纹理图生成器 — 彩色渐变/流体/火焰/赛博朋克等纹理
用于正片叠底混合模式的下层彩色素材
"""
from PIL import Image, ImageDraw, ImageFilter
import os, math, random

# 预设纹理配置
TEXTURE_PRESETS = {
    "rainbow": {
        "name": "彩虹流体",
        "colors": [(255,0,0), (255,127,0), (255,255,0), (0,255,0), (0,0,255), (75,0,130), (148,0,211)],
        "mode": "linear_gradient",
        "angle": 45,
    },
    "fire": {
        "name": "火焰",
        "colors": [(255,255,0), (255,100,0), (255,0,0), (100,0,0)],
        "mode": "radial_gradient",
        "blur": 8,
    },
    "cyber": {
        "name": "赛博朋克",
        "colors": [(0,255,255), (255,0,255), (0,0,255), (128,0,255)],
        "mode": "diagonal_gradient",
        "glow": True,
    },
    "sunset": {
        "name": "日落",
        "colors": [(255,94,98), (255,153,102), (255,206,102), (170,102,204)],
        "mode": "linear_gradient",
        "angle": 180,
    },
    "ocean": {
        "name": "海洋",
        "colors": [(0,50,150), (0,150,200), (0,200,200), (100,255,200)],
        "mode": "linear_gradient",
        "angle": 90,
    },
    "neon": {
        "name": "霓虹",
        "colors": [(255,0,128), (0,255,128), (128,0,255), (255,255,0)],
        "mode": "radial_gradient",
        "blur": 4,
    },
}


def generate_texture(preset="rainbow", size=(1920, 1080), output_path=None,
                     colors=None, mode=None, angle=0, blur=0):
    """
    生成彩色纹理图
    
    Args:
        preset: 预设名称（rainbow/fire/cyber/sunset/ocean/neon）
        size: 画布尺寸
        output_path: 输出路径
        colors: 自定义颜色列表（覆盖预设）
        mode: 渐变模式 linear_gradient/radial_gradient/diagonal_gradient
        angle: 线性渐变角度（度）
        blur: 模糊半径
    """
    config = TEXTURE_PRESETS.get(preset, TEXTURE_PRESETS["rainbow"]).copy()
    if colors: config["colors"] = colors
    if mode: config["mode"] = mode
    if angle: config["angle"] = angle
    if blur: config["blur"] = blur
    
    colors = config["colors"]
    mode = config.get("mode", "linear_gradient")
    w, h = size
    
    if mode == "linear_gradient":
        img = _linear_gradient(w, h, colors, config.get("angle", 0))
    elif mode == "radial_gradient":
        img = _radial_gradient(w, h, colors)
    elif mode == "diagonal_gradient":
        img = _diagonal_gradient(w, h, colors)
    else:
        img = _linear_gradient(w, h, colors, 0)
    
    if config.get("blur", 0) > 0:
        img = img.filter(ImageFilter.GaussianBlur(config["blur"]))
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)
        return output_path
    return img


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _linear_gradient(w, h, colors, angle=0):
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    rad = math.radians(angle)
    dx, dy = math.cos(rad), math.sin(rad)
    length = abs(dx) * w + abs(dy) * h
    
    for y in range(h):
        for x in range(w):
            t = (x * dx + y * dy) / length if length > 0 else 0
            t = max(0, min(1, t))
            # 多色渐变
            seg = t * (len(colors) - 1)
            idx = min(int(seg), len(colors) - 2)
            local_t = seg - idx
            pixels[x, y] = _lerp_color(colors[idx], colors[idx+1], local_t)
    return img


def _radial_gradient(w, h, colors):
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    cx, cy = w // 2, h // 2
    max_r = math.sqrt(cx**2 + cy**2)
    
    for y in range(h):
        for x in range(w):
            r = math.sqrt((x-cx)**2 + (y-cy)**2) / max_r
            r = max(0, min(1, r))
            seg = r * (len(colors) - 1)
            idx = min(int(seg), len(colors) - 2)
            local_t = seg - idx
            pixels[x, y] = _lerp_color(colors[idx], colors[idx+1], local_t)
    return img


def _diagonal_gradient(w, h, colors):
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            t = (x / w + y / h) / 2
            seg = t * (len(colors) - 1)
            idx = min(int(seg), len(colors) - 2)
            local_t = seg - idx
            pixels[x, y] = _lerp_color(colors[idx], colors[idx+1], local_t)
    return img
