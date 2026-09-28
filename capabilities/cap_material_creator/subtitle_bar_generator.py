"""
半透明字幕条生成器 — 静态PNG + 动态MP4
替代剪映"贴纸图形库+复合片段"方案（jianying-editor不支持复合片段）

两种模式：
- burn_text=True: 文字烧录到PNG（静态成品，排版精确）
- burn_text=False: 只生成背景条（文字在剪映中添加，可保存为文字预设复用）

动态模式：生成可循环MP4（黑色背景，剪映中用"滤色"混合去黑），支持微变光/律动/流光/呼吸
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os, math, subprocess, tempfile, shutil


def _find_font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\Deng.ttf",
    ]
    for f in candidates:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _make_gradient(width, height, colors, angle=0, brightness=1.0):
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    rad = math.radians(angle)
    dx, dy = math.cos(rad), math.sin(rad)
    length = abs(dx) * width + abs(dy) * height
    c1, c2 = colors[0], colors[-1]
    for y in range(height):
        for x in range(width):
            t = max(0, min(1, (x * dx + y * dy) / length)) if length > 0 else 0
            if len(colors) > 2:
                seg = t * (len(colors) - 1)
                idx = min(int(seg), len(colors) - 2)
                lt = seg - idx
                r = int(colors[idx][0] + (colors[idx+1][0] - colors[idx][0]) * lt)
                g = int(colors[idx][1] + (colors[idx+1][1] - colors[idx][1]) * lt)
                b = int(colors[idx][2] + (colors[idx+1][2] - colors[idx][2]) * lt)
            else:
                r = int(c1[0] + (c2[0] - c1[0]) * t)
                g = int(c1[1] + (c2[1] - c1[1]) * t)
                b = int(c1[2] + (c2[2] - c1[2]) * t)
            pixels[x, y] = (int(r*brightness), int(g*brightness), int(b*brightness))
    return img


def _render_bar_frame(width, height, gradient_colors, gradient_angle, opacity,
                      corner_radius, border_color, border_width, highlight,
                      avatar_size, avatar_offset, brightness=1.0,
                      highlight_offset=(0, 0), scale=1.0, title_text=None,
                      subtitle_text=None, title_color=(255,255,255),
                      subtitle_color=(220,220,220), title_size=None,
                      subtitle_size=None, text_offset_x=20, burn_text=True):
    if corner_radius is None:
        corner_radius = height // 2
    if title_size is None:
        title_size = int(height * 0.42)
    if subtitle_size is None:
        subtitle_size = int(height * 0.22)

    pad = 40
    canvas_w = int((width + pad * 2) * scale)
    canvas_h = int((height + pad * 2) * scale)
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    ox, oy = pad, pad

    gradient = _make_gradient(width, height, gradient_colors, gradient_angle, brightness)
    mask = Image.new('L', (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, width-1, height-1], radius=corner_radius, fill=255)
    alpha = mask.point(lambda p: int(p * opacity)) if opacity < 1.0 else mask
    gradient.putalpha(alpha)
    img.paste(gradient, (ox, oy), gradient)

    if highlight:
        hl_size = int(height * 1.2)
        hl = Image.new('RGBA', (hl_size, hl_size), (0, 0, 0, 0))
        ImageDraw.Draw(hl).ellipse([0, 0, hl_size-1, hl_size-1], fill=(255, 255, 255, 200))
        hl = hl.filter(ImageFilter.GaussianBlur(radius=8))
        hl_mask = Image.new('L', (hl_size, hl_size), 0)
        ImageDraw.Draw(hl_mask).ellipse([0, 0, hl_size-1, hl_size-1], fill=180)
        hl.putalpha(hl_mask)
        hl_x = ox + width - hl_size // 2 - 10 + highlight_offset[0]
        hl_y = oy - hl_size // 4 + highlight_offset[1]
        img.paste(hl, (hl_x, hl_y), hl)

    if border_width > 0:
        border = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(border).rounded_rectangle(
            [0, 0, width-1, height-1], radius=corner_radius,
            outline=border_color + (255,), width=border_width
        )
        img.paste(border, (ox, oy), border)

    avatar_right = ox + avatar_offset
    if avatar_size > 0:
        av = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
        av_grad = _make_gradient(avatar_size, avatar_size, gradient_colors, 90, brightness)
        av_mask = Image.new('L', (avatar_size, avatar_size), 0)
        ImageDraw.Draw(av_mask).ellipse([0, 0, avatar_size-1, avatar_size-1], fill=255)
        av_grad.putalpha(av_mask)
        av.paste(av_grad, (0, 0), av_grad)
        ImageDraw.Draw(av).ellipse(
            [0, 0, avatar_size-1, avatar_size-1],
            outline=(255, 255, 255, 255), width=border_width
        )
        av_x = ox + avatar_offset
        av_y = oy + (height - avatar_size) // 2
        img.paste(av, (av_x, av_y), av)
        avatar_right = av_x + avatar_size

    if burn_text and (title_text or subtitle_text):
        draw = ImageDraw.Draw(img)
        text_x = avatar_right + text_offset_x
        if title_text and subtitle_text:
            title_font = _find_font(title_size, bold=True)
            sub_font = _find_font(subtitle_size)
            tb = draw.textbbox((0, 0), title_text, font=title_font)
            sb = draw.textbbox((0, 0), subtitle_text, font=sub_font)
            th = tb[3] - tb[1]
            sh = sb[3] - sb[1]
            gap = 4
            total_h = th + gap + sh
            start_y = oy + (height - total_h) // 2
            draw.text((text_x, start_y), title_text, fill=title_color + (255,), font=title_font)
            draw.text((text_x, start_y + th + gap), subtitle_text, fill=subtitle_color + (255,), font=sub_font)
        elif title_text:
            title_font = _find_font(title_size, bold=True)
            tb = draw.textbbox((0, 0), title_text, font=title_font)
            th = tb[3] - tb[1]
            y = oy + (height - th) // 2 - tb[1]
            draw.text((text_x, y), title_text, fill=title_color + (255,), font=title_font)

    if scale != 1.0:
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    return img


def generate_subtitle_bar(
    width=950, height=150,
    gradient_colors=((255, 200, 0), (255, 50, 0)),
    gradient_angle=0, opacity=0.8, corner_radius=None,
    border_color=(255, 255, 255), border_width=2,
    highlight=True, avatar_size=120, avatar_offset=15,
    title_text=None, subtitle_text=None,
    title_color=(255, 255, 255), subtitle_color=(220, 220, 220),
    title_size=None, subtitle_size=None, text_offset_x=20,
    burn_text=True, output_path=None,
):
    """生成静态字幕条PNG。burn_text=False只输出背景条（文字在剪映中添加，可保存为预设）"""
    img = _render_bar_frame(
        width, height, gradient_colors, gradient_angle, opacity,
        corner_radius, border_color, border_width, highlight,
        avatar_size, avatar_offset, burn_text=burn_text,
        title_text=title_text, subtitle_text=subtitle_text,
        title_color=title_color, subtitle_color=subtitle_color,
        title_size=title_size, subtitle_size=subtitle_size,
        text_offset_x=text_offset_x
    )
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)
        return output_path
    return img


ANIMATION_PRESETS = {
    "glow_pulse": {"name": "微变背景光", "desc": "渐变亮度呼吸+高光缓慢漂移"},
    "subtle_bounce": {"name": "轻微律动", "desc": "整体轻微缩放呼吸1.0→1.02→1.0"},
    "light_sweep": {"name": "流光扫过", "desc": "高光从左到右缓慢扫过"},
    "breath": {"name": "呼吸透明度", "desc": "不透明度轻微呼吸变化"},
}


def generate_subtitle_bar_animated(
    output_path, duration=3.0, fps=30,
    animation="glow_pulse",
    width=950, height=150,
    gradient_colors=((255, 200, 0), (255, 50, 0)),
    gradient_angle=0, opacity=0.8, corner_radius=None,
    border_color=(255, 255, 255), border_width=2,
    highlight=True, avatar_size=120, avatar_offset=15,
    title_text=None, subtitle_text=None, burn_text=False,
    **kwargs
):
    """
    生成动态字幕条MP4（黑色背景，剪映中用"滤色"混合去黑）
    animation: glow_pulse/subtle_bounce/light_sweep/breath
    burn_text: 动态模式建议False，文字在剪映添加
    """
    total_frames = int(duration * fps)
    tmpdir = tempfile.mkdtemp(prefix="bar_anim_")

    try:
        for i in range(total_frames):
            t = i / total_frames
            phase = 2 * math.pi * t

            brightness = 1.0
            hl_offset = (0, 0)
            scale = 1.0
            cur_opacity = opacity

            if animation == "glow_pulse":
                brightness = 0.85 + 0.15 * (0.5 + 0.5 * math.sin(phase))
                hl_offset = (int(15 * math.sin(phase)), int(8 * math.cos(phase)))
            elif animation == "subtle_bounce":
                scale = 1.0 + 0.02 * (0.5 + 0.5 * math.sin(phase))
            elif animation == "light_sweep":
                sweep_x = int((t - 0.5) * width * 1.5)
                hl_offset = (sweep_x - width // 2, 0)
                brightness = 0.9 + 0.1 * (0.5 + 0.5 * math.sin(phase))
            elif animation == "breath":
                cur_opacity = opacity * (0.9 + 0.1 * (0.5 + 0.5 * math.sin(phase)))

            frame = _render_bar_frame(
                width, height, gradient_colors, gradient_angle, cur_opacity,
                corner_radius, border_color, border_width, highlight,
                avatar_size, avatar_offset, brightness=brightness,
                highlight_offset=hl_offset, scale=scale,
                title_text=title_text, subtitle_text=subtitle_text,
                burn_text=burn_text
            )
            bg = Image.new('RGB', (frame.width, frame.height), (0, 0, 0))
            bg.paste(frame, (0, 0), frame)
            bg.save(os.path.join(tmpdir, f"frame_{i:04d}.png"))

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(tmpdir, "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


SUBTITLE_BAR_PRESETS = {
    "sunset": {"gradient_colors": ((255, 200, 0), (255, 50, 0)), "name": "日落橙红"},
    "ocean": {"gradient_colors": ((0, 200, 255), (0, 50, 150)), "name": "海洋蓝"},
    "purple": {"gradient_colors": ((180, 100, 255), (80, 0, 150)), "name": "梦幻紫"},
    "neon": {"gradient_colors": ((0, 255, 200), (255, 0, 200)), "name": "霓虹青粉"},
    "gold": {"gradient_colors": ((255, 220, 100), (200, 150, 0)), "name": "金色"},
    "minimal": {"gradient_colors": ((60, 60, 70), (30, 30, 40)), "name": "极简深灰"},
}


def generate_subtitle_bar_preset(preset="sunset", **kwargs):
    config = SUBTITLE_BAR_PRESETS.get(preset, SUBTITLE_BAR_PRESETS["sunset"]).copy()
    config.pop("name", None)
    config.update(kwargs)
    return generate_subtitle_bar(**config)
