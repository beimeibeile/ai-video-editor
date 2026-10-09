"""
半透明字幕条特效模块
基于抖音教程"剪辑进阶，剪映制作半透明字幕条-文本框效果"封装

核心原理：
1. 用Pillow预生成半透明渐变圆角矩形PNG（药丸形状背景）
2. 用Pillow生成高光圆形PNG
3. 剪映中画中画轨道叠加背景条+高光+文字
4. 支持入场动画（滑入/淡入/弹出）

相比剪映原生贴纸方案：
- 不依赖剪映云端贴纸库，完全本地生成
- 颜色/渐变/圆角/不透明度完全可控
- 可批量生成，适合模板创作者
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import math
from typing import Tuple, List, Dict, Any

# 探测 jianying-editor skill 路径
SKILL_ROOT = next((p for p in [
    os.getenv("JY_SKILL_ROOT", "").strip(),
    r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor",
] if p and os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py"))), None)

if SKILL_ROOT:
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    from jy_wrapper import JyProject
    import pyJianYingDraft as draft
else:
    raise ImportError("Could not find jianying-editor skill root.")

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    Image = None


# ──────────────────────────────────────────────
# 素材生成：半透明渐变圆角矩形
# ──────────────────────────────────────────────

def create_gradient_bar(
    width: int = 950,
    height: int = 150,
    color_start: Tuple[int, int, int] = (255, 200, 50),
    color_end: Tuple[int, int, int] = (255, 50, 50),
    alpha: int = 204,  # 80%不透明 = 204/255
    radius: int = None,  # None则自动为高度的一半（药丸形）
    gradient_angle: float = 0,  # 渐变角度，0=水平，90=垂直
    highlight: bool = False,  # 是否在内部左侧绘制高光
    output_path: str = None,
) -> str:
    """生成半透明渐变圆角矩形PNG

    Args:
        width: 宽度
        height: 高度
        color_start: 渐变起始色RGB
        color_end: 渐变结束色RGB
        alpha: 不透明度 0-255
        radius: 圆角半径，None则为height/2（药丸形）
        gradient_angle: 渐变角度（度）
        output_path: 输出路径

    Returns:
        生成的图片路径
    """
    if Image is None:
        raise ImportError("Pillow not installed. Run: pip install Pillow")

    if radius is None:
        radius = height // 2

    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"bar_{color_start[0]}_{color_start[1]}_{color_start[2]}_{alpha}.png"
        )

    # 创建带透明通道的画布
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 绘制渐变
    # 创建渐变贴图
    grad = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(grad)

    # 计算渐变方向
    angle_rad = math.radians(gradient_angle)
    dx = math.cos(angle_rad)
    dy = math.sin(angle_rad)

    for x in range(width):
        for y in range(height):
            # 计算该点在渐变方向上的投影比例
            t = (x * dx + y * dy) / (width * abs(dx) + height * abs(dy) + 0.001)
            t = max(0, min(1, t))
            r = int(color_start[0] + (color_end[0] - color_start[0]) * t)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * t)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * t)
            grad_draw.point((x, y), fill=(r, g, b, alpha))

    # 创建圆角蒙版
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (width - 1, height - 1)], radius=radius, fill=255)

    # 应用蒙版
    img.paste(grad, (0, 0), mask)

    # 绘制立体球高光（内部左侧，径向渐变+左上高光点）
    if highlight:
        hl_radius = int(height * 0.50)
        hl_cx = int(height * 0.50)
        hl_cy = height // 2
        hl_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        hl_draw = ImageDraw.Draw(hl_layer)
        # 球体基底：径向渐变（中心亮，边缘暗）
        for r in range(hl_radius, 0, -1):
            t = r / hl_radius
            br = int(color_start[0] * (1 - t * 0.4) + 30 * (1 - t))
            bg = int(color_start[1] * (1 - t * 0.4) + 30 * (1 - t))
            bb = int(color_start[2] * (1 - t * 0.4) + 30 * (1 - t))
            a = int(alpha * (1 - t * t * 0.7))
            hl_draw.ellipse(
                [(hl_cx - r, hl_cy - r), (hl_cx + r, hl_cy + r)],
                fill=(min(255, br), min(255, bg), min(255, bb), a)
            )
        # 左上高光点（小亮点）
        spot_r = int(hl_radius * 0.25)
        spot_x = hl_cx - int(hl_radius * 0.3)
        spot_y = hl_cy - int(hl_radius * 0.3)
        for r in range(spot_r, 0, -1):
            t = r / spot_r
            a = int(180 * (1 - t * t))
            hl_draw.ellipse(
                [(spot_x - r, spot_y - r), (spot_x + r, spot_y + r)],
                fill=(255, 255, 255, a)
            )
        img = Image.alpha_composite(img, hl_layer)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def create_highlight_circle(
    size: int = 150,
    color: Tuple[int, int, int] = (255, 255, 255),
    alpha: int = 180,
    output_path: str = None,
) -> str:
    """生成高光圆形PNG

    Args:
        size: 直径
        color: 颜色RGB
        alpha: 不透明度
        output_path: 输出路径
    """
    if Image is None:
        raise ImportError("Pillow not installed.")

    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"highlight_{size}.png"
        )

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 绘制圆形渐变（中心亮边缘暗）
    for r in range(size // 2, 0, -1):
        t = r / (size // 2)
        a = int(alpha * t * t)
        draw.ellipse(
            [(size // 2 - r, size // 2 - r), (size // 2 + r, size // 2 + r)],
            fill=(color[0], color[1], color[2], a)
        )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


# ──────────────────────────────────────────────
# 字幕条样式预设
# ──────────────────────────────────────────────

BAR_STYLES = {
    "pill_warm": {
        "width": 950, "height": 150,
        "color_start": (255, 200, 50), "color_end": (255, 80, 50),
        "alpha": 204, "radius": None, "gradient_angle": 0,
        "text_color": (255, 255, 255), "text_size": 10.0,
        "highlight": True,
    },
    "pill_cool": {
        "width": 950, "height": 150,
        "color_start": (50, 150, 255), "color_end": (150, 50, 255),
        "alpha": 204, "radius": None, "gradient_angle": 0,
        "text_color": (255, 255, 255), "text_size": 10.0,
        "highlight": True,
    },
    "pill_cyber": {
        "width": 950, "height": 150,
        "color_start": (0, 255, 255), "color_end": (255, 0, 255),
        "alpha": 180, "radius": None, "gradient_angle": 45,
        "text_color": (255, 255, 255), "text_size": 10.0,
        "highlight": True,
    },
    "rect_dark": {
        "width": 900, "height": 120,
        "color_start": (30, 30, 30), "color_end": (60, 60, 60),
        "alpha": 200, "radius": 20, "gradient_angle": 0,
        "text_color": (255, 255, 255), "text_size": 9.0,
        "highlight": False,
    },
    "rect_minimal": {
        "width": 800, "height": 100,
        "color_start": (255, 255, 255), "color_end": (240, 240, 240),
        "alpha": 220, "radius": 10, "gradient_angle": 0,
        "text_color": (30, 30, 30), "text_size": 8.0,
        "highlight": False,
    },
    "tag_small": {
        "width": 400, "height": 80,
        "color_start": (255, 100, 100), "color_end": (255, 50, 50),
        "alpha": 230, "radius": 40, "gradient_angle": 90,
        "text_color": (255, 255, 255), "text_size": 7.0,
        "highlight": True,
    },
}


# ──────────────────────────────────────────────
# 核心：给工程添加半透明字幕条
# ──────────────────────────────────────────────

def add_subtitle_bar(
    project,
    text: str,
    start_time: str = "0s",
    duration: str = "3s",
    style: str = "pill_warm",
    position_y: float = -0.6,  # -1到1，0为中心，负值偏下
    anim_in: str = "向左滑动",  # 入场动画
    custom_style: Dict = None,
    output_dir: str = None,
) -> Dict[str, Any]:
    """给剪映工程添加半透明字幕条

    Args:
        project: JyProject实例
        text: 字幕文字
        start_time: 起始时间
        duration: 持续时长
        style: 样式预设名
        position_y: 垂直位置（-1到1）
        anim_in: 入场动画名称
        custom_style: 自定义样式覆盖
        output_dir: 素材输出目录

    Returns:
        包含片段信息的字典
    """
    # 获取样式配置
    cfg = BAR_STYLES.get(style, BAR_STYLES["pill_warm"]).copy()
    if custom_style:
        cfg.update(custom_style)

    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "subtitle_bar_assets"
        )
    os.makedirs(output_dir, exist_ok=True)

    # 1. 生成背景条
    bar_path = os.path.join(output_dir, f"bar_{style}.png")
    create_gradient_bar(
        width=cfg["width"], height=cfg["height"],
        color_start=cfg["color_start"], color_end=cfg["color_end"],
        alpha=cfg["alpha"], radius=cfg["radius"],
        gradient_angle=cfg["gradient_angle"],
        highlight=cfg.get("highlight", False),
        output_path=bar_path,
    )

    # 2. 生成高光
    # 3. 添加背景条到画中画轨道
    bar_seg = project.add_media_safe(
        bar_path,
        start_time=start_time,
        duration=duration,
        track_name="SubtitleBar_BG",
    )

    if bar_seg:
        # 设置位置
        bar_seg.clip_settings = draft.ClipSettings(
            transform_x=0.0,
            transform_y=position_y,
        )
        # 入场动画
        if anim_in:
            try:
                bar_seg.add_animation(draft.IntroType[anim_in] if hasattr(draft.IntroType, anim_in) else None, 0, 500000)
            except Exception:
                pass

    # 4. 高光已内置在背景条PNG中

    # 5. 添加文字
    text_seg = project.add_text_simple(
        text,
        start_time=start_time,
        duration=duration,
        font_size=cfg["text_size"],
        color_rgb=cfg["text_color"],
        style=draft.TextStyle(size=cfg["text_size"], bold=True),
        border=draft.TextBorder(color=(0, 0, 0), width=30),
        clip_settings=draft.ClipSettings(transform_x=0.0, transform_y=position_y),
        anim_in="向左滑动",
        track_name="SubtitleBar_Text",
    )

    return {
        "text": text,
        "style": style,
        "bar_segment": bar_seg,
        "text_segment": text_seg,
        "bar_path": bar_path,
    }


# ──────────────────────────────────────────────
# 批量添加字幕条
# ──────────────────────────────────────────────

def add_subtitle_bars(
    project,
    items: List[Dict[str, Any]],
    default_style: str = "pill_warm",
    output_dir: str = None,
) -> List[Dict[str, Any]]:
    """批量添加字幕条

    Args:
        project: JyProject实例
        items: 字幕条列表，每个元素包含 text/start_time/duration/style/position_y
        default_style: 默认样式
        output_dir: 素材输出目录

    Returns:
        结果列表
    """
    results = []
    for item in items:
        result = add_subtitle_bar(
            project,
            text=item["text"],
            start_time=item.get("start_time", "0s"),
            duration=item.get("duration", "3s"),
            style=item.get("style", default_style),
            position_y=item.get("position_y", -0.6),
            anim_in=item.get("anim_in", "向左滑动"),
            output_dir=output_dir,
        )
        results.append(result)
    return results


# ──────────────────────────────────────────────
# 创建独立的字幕条测试工程
# ──────────────────────────────────────────────

def create_subtitle_bar_demo(
    project_name: str = "SubtitleBar_Demo",
    width: int = 1080,
    height: int = 1920,
    output_dir: str = None,
) -> Dict[str, Any]:
    """创建字幕条效果演示工程

    展示6种不同样式的字幕条依次出现。
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "subtitle_bar_assets"
        )
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"[1/2] 创建工程: {project_name}")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 添加黑色背景
    bg_path = os.path.join(output_dir, "bg_black.png")
    if Image:
        bg = Image.new("RGB", (width, height), (20, 20, 20))
        bg.save(bg_path)
        project.add_media_safe(bg_path, start_time="0s", duration="12s", track_name="BG")

    logger.info(f"[2/2] 添加6种样式字幕条")
    styles = list(BAR_STYLES.keys())
    texts = ["每日一练", "精彩瞬间", "重点来了", "温馨提示", "高能预警", "下期预告"]
    positions = [-0.7, -0.4, -0.1, 0.2, 0.5, 0.8]

    for i, (style, text, pos) in enumerate(zip(styles, texts, positions)):
        start = f"{i * 2}s"
        add_subtitle_bar(
            project, text,
            start_time=start, duration="2s",
            style=style, position_y=pos,
            anim_in="向左滑动",
            output_dir=output_dir,
        )
        logger.info(f"  ✅ [{i+1}] {style}: {text}")

    project.save()
    return {"project_name": project_name, "styles_count": len(styles)}


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("半透明字幕条特效模块")
    logger.info("=" * 60)
    logger.info("\n核心函数:")
    logger.info("  create_gradient_bar(...) - 生成半透明渐变圆角矩形")
    logger.info("  create_highlight_circle(...) - 生成高光圆形")
    logger.info("  add_subtitle_bar(project, text, ...) - 给工程加字幕条")
    logger.info("  add_subtitle_bars(project, items) - 批量加字幕条")
    logger.info("  create_subtitle_bar_demo() - 创建演示工程")
    logger.info("\n预设样式:")
    for name in BAR_STYLES:
        s = BAR_STYLES[name]
        logger.info(f"  {name}: {s['color_start']}→{s['color_end']}, {s['width']}x{s['height']}")
