"""
模板风格复刻执行器（Template Style Replicator）

输入：教学视频路径
输出：风格复刻的剪映模板工程

流程：
1. 视频解析（ffprobe元数据 + ffmpeg关键帧提取）
2. 风格分析（识别模板类型、片段数、配色、转场、文字样式）
3. 素材生成（占位素材：纯色背景+数字标记+装饰文字）
4. 剪映工程构建（多片段+转场+遮罩+文字）
5. 输出草稿路径
"""

import os
import sys
import json
import subprocess
import uuid
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ============ 路径配置 ============
FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"

JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

# 智能转场选择器
from smart_transition_selector import SmartTransitionSelector, get_selector

# 工作目录
WORK_DIR = r"C:\Users\Administrator\AppData\Local\Temp\template_replicator"
os.makedirs(WORK_DIR, exist_ok=True)


# ============ 步骤1：视频解析 ============
def analyze_video(video_path: str) -> Dict[str, Any]:
    """解析视频基本信息"""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", video_path],
        capture_output=True, text=True, timeout=30
    )
    info = json.loads(result.stdout)

    video_stream = None
    audio_stream = None
    for s in info.get("streams", []):
        if s["codec_type"] == "video" and video_stream is None:
            video_stream = s
        if s["codec_type"] == "audio" and audio_stream is None:
            audio_stream = s

    duration = float(info.get("format", {}).get("duration", 0))

    return {
        "path": video_path,
        "width": video_stream.get("width", 1080) if video_stream else 1080,
        "height": video_stream.get("height", 1920) if video_stream else 1920,
        "fps": video_stream.get("r_frame_rate", "30/1") if video_stream else "30/1",
        "duration": duration,
        "has_audio": audio_stream is not None,
        "codec": video_stream.get("codec_name", "h264") if video_stream else "h264",
    }


def extract_keyframes(video_path: str, duration: float, count: int = 6) -> List[str]:
    """提取关键帧用于风格分析"""
    frame_dir = os.path.join(WORK_DIR, "frames_" + uuid.uuid4().hex[:8])
    os.makedirs(frame_dir, exist_ok=True)

    frames = []
    for i in range(count):
        t = (duration / count) * i + (duration / count / 2)
        output = os.path.join(frame_dir, f"frame_{i:02d}.png")
        subprocess.run(
            [FFMPEG, "-y", "-ss", str(t), "-i", video_path,
             "-vframes", "1", "-q:v", "2", output],
            capture_output=True, timeout=30
        )
        if os.path.exists(output):
            frames.append(output)

    return frames


# ============ 步骤2：风格分析 ============
def analyze_style(video_info: Dict[str, Any], keyframes: List[str]) -> Dict[str, Any]:
    """
    分析视频风格特征
    基于视频元数据 + 关键帧颜色统计进行风格分类
    支持5种模板风格：cinematic_bar / music_player / book_flip / photo_album / vlog
    """
    width = video_info["width"]
    height = video_info["height"]
    duration = video_info["duration"]

    # 判断横竖屏
    orientation = "portrait" if height > width else "landscape"

    # 估算片段数（基于时长，每段3-4秒）
    segment_count = max(3, min(8, int(duration / 3.5)))

    # 关键帧颜色分析（用于风格分类）
    style_type = _classify_style_by_keyframes(keyframes, orientation, duration)

    # 根据风格类型返回配置
    style_configs = {
        "cinematic_bar": {
            "type": "cinematic_bar",
            "orientation": orientation,
            "segment_count": segment_count,
            "segment_duration": 3.5,
            "transition_duration": 0.5,
            "has_letterbox": True,
            "letterbox_ratio": 0.13,
            "has_big_numbers": True,
            "has_decor_text": True,
            "has_title": True,
            "title_text": "电影感画幅",
            "palette": ["#FF6B35", "#00B4D8", "#B8E0D2", "#7B2D8E", "#FF8C42", "#2EC4B6", "#E63946", "#F4A261"],
            "decor_phrases": [
                "colors and promises how to be brave",
                "heart beats fast",
                "colors and promises how to be brave",
                "the success turns on our effort",
                "how can I love",
                "high definition audio",
                "moments last forever",
                "chase your dreams",
            ],
        },
        "music_player": {
            "type": "music_player",
            "orientation": "portrait",
            "segment_count": segment_count,
            "segment_duration": 3.0,
            "transition_duration": 0.4,
            "has_letterbox": False,
            "letterbox_ratio": 0.0,
            "has_big_numbers": True,
            "has_decor_text": True,
            "has_title": True,
            "title_text": "音乐播放器",
            "palette": ["#1DB954", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#FF8C42"],
            "decor_phrases": [
                "now playing",
                "high definition audio",
                "heart beats fast",
                "feel the rhythm",
                "music is life",
                "turn it up",
                "sound on",
                "bass boosted",
            ],
        },
        "book_flip": {
            "type": "book_flip",
            "orientation": "landscape",
            "segment_count": segment_count,
            "segment_duration": 4.0,
            "transition_duration": 0.8,
            "has_letterbox": False,
            "letterbox_ratio": 0.0,
            "has_big_numbers": True,
            "has_decor_text": True,
            "has_title": True,
            "title_text": "翻书相册",
            "palette": ["#F5E6D3", "#E8D5B7", "#D4C4A8", "#C9B896", "#B8A888", "#A89878", "#E0D0B8", "#F0E0C8"],
            "decor_phrases": [
                "life diary",
                "live simply love deeply",
                "embrace every moment",
                "memories forever",
                "our story",
                "precious times",
                "sweet days",
                "treasure today",
            ],
        },
        "photo_album": {
            "type": "photo_album",
            "orientation": orientation,
            "segment_count": segment_count,
            "segment_duration": 3.5,
            "transition_duration": 0.6,
            "has_letterbox": False,
            "letterbox_ratio": 0.0,
            "has_big_numbers": False,
            "has_decor_text": True,
            "has_title": True,
            "title_text": "照片相册",
            "palette": ["#FFB6C1", "#87CEEB", "#98FB98", "#FFDAB9", "#DDA0DD", "#F0E68C", "#E6E6FA", "#FFA07A"],
            "decor_phrases": [
                "memories",
                "best moments",
                "our journey",
                "forever young",
                "good times",
                "happy days",
                "together",
                "smile",
            ],
        },
        "vlog": {
            "type": "vlog",
            "orientation": "portrait",
            "segment_count": segment_count,
            "segment_duration": 2.5,
            "transition_duration": 0.3,
            "has_letterbox": False,
            "letterbox_ratio": 0.0,
            "has_big_numbers": False,
            "has_decor_text": True,
            "has_title": True,
            "title_text": "日常Vlog",
            "palette": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"],
            "decor_phrases": [
                "day in my life",
                "vlog",
                "daily routine",
                "good vibes",
                "stay positive",
                "new day",
                "let's go",
                "enjoy",
            ],
        },
    }

    style = style_configs.get(style_type, style_configs["cinematic_bar"])
    logger.info(f"风格分类结果: {style_type} (orientation={orientation}, duration={duration:.1f}s)")
    return style


def _classify_style_by_keyframes(keyframes: List[str], orientation: str, duration: float) -> str:
    """
    基于关键帧颜色统计进行简单风格分类
    后续可接入视觉模型进行深度分析
    """
    if not keyframes:
        return "cinematic_bar"

    try:
        from PIL import Image
        import numpy as np

        # 分析前3帧的颜色特征
        color_stats = []
        for kf in keyframes[:3]:
            if not os.path.exists(kf):
                continue
            img = Image.open(kf).convert("RGB")
            img_small = img.resize((50, 50))
            arr = np.array(img_small)

            # 计算黑色像素占比（判断是否有黑边/电影感画幅）
            black_pixels = np.sum(np.all(arr < 30, axis=2))
            black_ratio = black_pixels / (50 * 50)

            # 计算颜色丰富度（标准差）
            color_std = np.mean(np.std(arr, axis=(0, 1)))

            # 计算主色调
            mean_color = np.mean(arr, axis=(0, 1))

            color_stats.append({
                "black_ratio": black_ratio,
                "color_std": color_std,
                "mean_brightness": np.mean(mean_color),
            })

        if not color_stats:
            return "cinematic_bar"

        avg_black = np.mean([s["black_ratio"] for s in color_stats])
        avg_std = np.mean([s["color_std"] for s in color_stats])
        avg_brightness = np.mean([s["mean_brightness"] for s in color_stats])

        # 风格分类规则
        # 1. 黑色像素占比高 → 电影感画幅（上下黑边）
        if avg_black > 0.15:
            return "cinematic_bar"

        # 2. 竖屏 + 颜色饱和度高 + 时长较短 → 音乐播放器
        if orientation == "portrait" and avg_std > 50 and duration < 20:
            return "music_player"

        # 3. 横屏 + 亮度较高 + 时长较长 → 翻书相册
        if orientation == "landscape" and avg_brightness > 150 and duration > 15:
            return "book_flip"

        # 4. 颜色柔和 + 中等亮度 → 照片相册
        if avg_std < 45 and avg_brightness > 120:
            return "photo_album"

        # 5. 默认 → Vlog风格
        return "vlog"

    except Exception as e:
        logger.warning(f"关键帧风格分类失败，使用默认: {e}")
        return "cinematic_bar"


# ============ 步骤3：素材生成 ============
def generate_placeholder_assets(style: Dict[str, Any], output_dir: str) -> List[str]:
    """
    生成占位素材（根据模板风格生成不同视觉效果）
    支持5种风格：cinematic_bar / music_player / book_flip / photo_album / vlog
    所有素材中的彩色区域代表"用户可替换素材位"
    """
    os.makedirs(output_dir, exist_ok=True)

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise RuntimeError("Pillow未安装，无法生成素材")

    # 完整画布尺寸
    if style["orientation"] == "portrait":
        canvas_w, canvas_h = 1080, 1920
    else:
        canvas_w, canvas_h = 1920, 1080

    style_type = style.get("type", "cinematic_bar")
    palette = style["palette"]
    phrases = style["decor_phrases"]

    # 风格生成器映射
    generators = {
        "cinematic_bar": _gen_cinematic_bar,
        "music_player": _gen_music_player,
        "book_flip": _gen_book_flip,
        "photo_album": _gen_photo_album,
        "vlog": _gen_vlog,
    }
    gen_func = generators.get(style_type, _gen_cinematic_bar)

    assets = []
    for i in range(style["segment_count"]):
        color = palette[i % len(palette)]
        num = str(i + 1)
        phrase = phrases[i % len(phrases)]

        img = gen_func(canvas_w, canvas_h, color, num, phrase, style)
        path = os.path.join(output_dir, f"segment_{i + 1}.png")
        img.save(path)
        assets.append(path)
        logger.info(f"生成占位素材[{style_type}]: {os.path.basename(path)}")

    return assets


def _get_fonts(content_h: int):
    """获取字体（大号+小号）"""
    from PIL import ImageFont
    try:
        font_large = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", int(content_h * 0.28))
        font_small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", int(content_h * 0.028))
        font_medium = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", int(content_h * 0.06))
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_medium = ImageFont.load_default()
    return font_large, font_medium, font_small


def _gen_cinematic_bar(canvas_w, canvas_h, color, num, phrase, style):
    """电影感画幅：上下黑边 + 中间彩色内容区 + 大数字 + 装饰文字"""
    from PIL import Image, ImageDraw
    letterbox_h = int(canvas_h * style.get("letterbox_ratio", 0.13))
    content_top = letterbox_h
    content_bottom = canvas_h - letterbox_h
    content_h = content_bottom - content_top

    img = Image.new("RGB", (canvas_w, canvas_h), "black")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, content_top), (canvas_w, content_bottom)], fill=color)

    font_large, _, font_small = _get_fonts(content_h)

    bbox = draw.textbbox((0, 0), num, font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    num_y = content_top + (content_h - th) // 2 - int(content_h * 0.08)
    draw.text(((canvas_w - tw) // 2, num_y), num, fill="white", font=font_large)

    if style.get("has_decor_text"):
        bbox2 = draw.textbbox((0, 0), phrase, font=font_small)
        tw2 = bbox2[2] - bbox2[0]
        decor_y = num_y + th + int(content_h * 0.06)
        draw.text(((canvas_w - tw2) // 2, decor_y), phrase, fill="white", font=font_small)

    return img


def _gen_music_player(canvas_w, canvas_h, color, num, phrase, style):
    """音乐播放器：中心圆角卡片 + 播放按钮 + 进度条 + 歌曲信息"""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (canvas_w, canvas_h), color)
    draw = ImageDraw.Draw(img)

    # 中心圆角卡片（用户可替换封面图区域）
    card_size = int(canvas_w * 0.6)
    card_x = (canvas_w - card_size) // 2
    card_y = int(canvas_h * 0.18)
    radius = int(card_size * 0.08)
    draw.rounded_rectangle(
        [(card_x, card_y), (card_x + card_size, card_y + card_size)],
        radius=radius, fill="white", outline="#333333", width=3
    )

    # 卡片内大数字（代表封面）
    font_large, font_medium, font_small = _get_fonts(card_size)
    bbox = draw.textbbox((0, 0), num, font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((card_x + (card_size - tw) // 2, card_y + (card_size - th) // 2),
              num, fill=color, font=font_large)

    # 歌曲标题（装饰文字）
    title_y = card_y + card_size + int(canvas_h * 0.04)
    bbox2 = draw.textbbox((0, 0), phrase, font=font_medium)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((canvas_w - tw2) // 2, title_y), phrase, fill="white", font=font_medium)

    # 播放按钮（三角形）
    btn_size = int(canvas_w * 0.08)
    btn_cx = canvas_w // 2
    btn_cy = title_y + int(canvas_h * 0.08)
    draw.polygon([
        (btn_cx - btn_size // 2, btn_cy - btn_size // 2),
        (btn_cx - btn_size // 2, btn_cy + btn_size // 2),
        (btn_cx + btn_size // 2, btn_cy),
    ], fill="white")

    # 进度条
    bar_y = btn_cy + int(canvas_h * 0.06)
    bar_w = int(canvas_w * 0.6)
    bar_x = (canvas_w - bar_w) // 2
    bar_h = int(canvas_h * 0.006)
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)],
                           radius=bar_h // 2, fill="white")
    # 进度点
    progress_x = bar_x + int(bar_w * 0.35)
    draw.ellipse([(progress_x - 8, bar_y - 6), (progress_x + 8, bar_y + bar_h + 6)],
                 fill="white")

    return img


def _gen_book_flip(canvas_w, canvas_h, color, num, phrase, style):
    """翻书相册：书页效果 + 页码 + 装饰边框"""
    from PIL import Image, ImageDraw
    # 米色背景（书页）
    bg_color = "#F5E6D3"
    img = Image.new("RGB", (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(img)

    # 左右书页分割线
    mid_x = canvas_w // 2
    draw.line([(mid_x, 0), (mid_x, canvas_h)], fill="#D4C4A8", width=3)

    # 内容区域（用户可替换照片区域）
    margin = int(canvas_w * 0.08)
    content_w = (canvas_w - margin * 3) // 2
    content_h = int(canvas_h * 0.65)
    content_y = int(canvas_h * 0.15)

    # 左页照片区
    left_x = margin
    draw.rounded_rectangle(
        [(left_x, content_y), (left_x + content_w, content_y + content_h)],
        radius=10, fill=color, outline="#C9B896", width=2
    )

    # 右页照片区（交替显示）
    right_x = mid_x + margin // 2
    if int(num) % 2 == 0:
        draw.rounded_rectangle(
            [(right_x, content_y), (right_x + content_w, content_y + content_h)],
            radius=10, fill=color, outline="#C9B896", width=2
        )

    # 页码
    font_large, font_medium, font_small = _get_fonts(content_h)
    page_num = f"Page {num}"
    bbox = draw.textbbox((0, 0), page_num, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text((mid_x - tw // 2, canvas_h - int(canvas_h * 0.06)),
              page_num, fill="#8B7355", font=font_small)

    # 装饰文字（左页底部）
    if style.get("has_decor_text"):
        bbox2 = draw.textbbox((0, 0), phrase, font=font_small)
        tw2 = bbox2[2] - bbox2[0]
        draw.text((left_x + (content_w - tw2) // 2, content_y + content_h + int(canvas_h * 0.03)),
                  phrase, fill="#8B7355", font=font_small)

    return img


def _gen_photo_album(canvas_w, canvas_h, color, num, phrase, style):
    """照片相册：照片框 + 阴影 + 标签"""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (canvas_w, canvas_h), "#F0F0F0")
    draw = ImageDraw.Draw(img)

    # 照片框（用户可替换照片区域）
    margin = int(canvas_w * 0.1)
    photo_w = canvas_w - margin * 2
    photo_h = int(canvas_h * 0.6)
    photo_x = margin
    photo_y = int(canvas_h * 0.12)

    # 阴影
    shadow_offset = 8
    draw.rounded_rectangle(
        [(photo_x + shadow_offset, photo_y + shadow_offset),
         (photo_x + photo_w + shadow_offset, photo_y + photo_h + shadow_offset)],
        radius=8, fill="#CCCCCC"
    )
    # 照片框
    draw.rounded_rectangle(
        [(photo_x, photo_y), (photo_x + photo_w, photo_y + photo_h)],
        radius=8, fill=color, outline="white", width=6
    )

    # 大数字（代表照片内容）
    font_large, font_medium, font_small = _get_fonts(photo_h)
    bbox = draw.textbbox((0, 0), num, font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((photo_x + (photo_w - tw) // 2, photo_y + (photo_h - th) // 2),
              num, fill="white", font=font_large)

    # 标签条
    label_y = photo_y + photo_h + int(canvas_h * 0.04)
    label_h = int(canvas_h * 0.06)
    draw.rounded_rectangle(
        [(photo_x, label_y), (photo_x + photo_w, label_y + label_h)],
        radius=label_h // 2, fill="white", outline="#DDDDDD", width=2
    )

    # 装饰文字
    if style.get("has_decor_text"):
        bbox2 = draw.textbbox((0, 0), phrase, font=font_small)
        tw2 = bbox2[2] - bbox2[0]
        draw.text((photo_x + (photo_w - tw2) // 2, label_y + (label_h - (bbox2[3]-bbox2[1])) // 2),
                  phrase, fill="#666666", font=font_small)

    return img


def _gen_vlog(canvas_w, canvas_h, color, num, phrase, style):
    """日常Vlog：简洁背景 + 顶部标题条 + 底部日期标签"""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (canvas_w, canvas_h), color)
    draw = ImageDraw.Draw(img)

    # 顶部半透明标题条
    bar_h = int(canvas_h * 0.1)
    draw.rectangle([(0, 0), (canvas_w, bar_h)], fill=(0, 0, 0, 128))

    # 标题文字
    font_large, font_medium, font_small = _get_fonts(canvas_h)
    title = f"VLOG #{num}"
    bbox = draw.textbbox((0, 0), title, font=font_medium)
    tw = bbox[2] - bbox[0]
    draw.text((int(canvas_w * 0.05), (bar_h - (bbox[3]-bbox[1])) // 2),
              title, fill="white", font=font_medium)

    # 中心大数字（代表视频内容）
    center_y = int(canvas_h * 0.4)
    bbox2 = draw.textbbox((0, 0), num, font=font_large)
    tw2, th2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
    draw.text(((canvas_w - tw2) // 2, center_y), num, fill="white", font=font_large)

    # 装饰文字
    if style.get("has_decor_text"):
        bbox3 = draw.textbbox((0, 0), phrase, font=font_small)
        tw3 = bbox3[2] - bbox3[0]
        draw.text(((canvas_w - tw3) // 2, center_y + th2 + int(canvas_h * 0.03)),
                  phrase, fill="white", font=font_small)

    # 底部日期标签
    date_y = canvas_h - int(canvas_h * 0.08)
    date_text = "DAY " + num.zfill(2)
    bbox4 = draw.textbbox((0, 0), date_text, font=font_small)
    tw4 = bbox4[2] - bbox4[0]
    # 标签背景
    tag_pad = 16
    draw.rounded_rectangle(
        [((canvas_w - tw4) // 2 - tag_pad, date_y - tag_pad // 2),
         ((canvas_w + tw4) // 2 + tag_pad, date_y + (bbox4[3]-bbox4[1]) + tag_pad // 2)],
        radius=12, fill=(255, 255, 255, 200)
    )
    draw.text(((canvas_w - tw4) // 2, date_y), date_text, fill=color, font=font_small)

    return img


# ============ 步骤4：剪映工程构建 ============
def build_jianying_project(style: Dict[str, Any], assets: List[str],
                           project_name: str, drafts_root: str = None) -> Dict[str, Any]:
    """构建剪映模板工程"""
    from jy_wrapper import JyProject
    import pyJianYingDraft as draft

    if style["orientation"] == "portrait":
        width, height = 1080, 1920
    else:
        width, height = 1920, 1080

    project = JyProject(project_name, width=width, height=height, overwrite=True)
    logger.info(f"创建工程: {project_name} ({width}x{height})")

    seg_duration = int(style["segment_duration"] * 1000000)  # 微秒
    trans_duration = int(style["transition_duration"] * 1000000)

    # 添加素材片段
    segments = []
    for i, asset_path in enumerate(assets):
        start = i * seg_duration
        seg = project.add_media_safe(asset_path, start, seg_duration, "VideoTrack")
        segments.append(seg)

    # 添加智能转场（根据风格类型匹配情绪/节奏/场景）
    style_type = style.get("type", "general")
    # 根据模板类型推断情绪和节奏
    emotion_map = {
        "cinematic_bar": ("震撼", "normal", "cinematic"),
        "music_player": ("炫酷", "normal", "creative"),
        "book_flip": ("回忆", "slow", "general"),
        "photo_album": ("温馨", "normal", "general"),
        "vlog": ("轻快", "fast", "vlog"),
        "travel": ("旅行", "normal", "travel"),
        "general": ("平静", "normal", "general"),
    }
    emotion, pace, scene = emotion_map.get(style_type, ("平静", "normal", "general"))

    selector = get_selector()
    selector.reset()
    emotions = [emotion] * len(segments)
    smart_transitions = selector.select_sequence(emotions, pace=pace, scene_type=scene)

    for i, trans in enumerate(smart_transitions):
        if i >= len(segments) - 1:
            break
        try:
            project.add_transition_simple(
                trans["name"],
                video_segment=segments[i],  # 转场必须加在前一个片段上
                duration=trans["duration"],
            )
            logger.info(f"  智能转场 [{i+1}] {trans['name']} ({trans['duration']}s) [{trans['category']}]")
        except Exception as e:
            logger.warning(f"  智能转场 [{i+1}] {trans['name']} 失败: {e}，回退叠化")
            try:
                project.add_transition_simple("叠化", video_segment=segments[i], duration=0.5)
            except Exception:
                pass

    # 注：电影感黑边已内置在占位素材图片中，无需独立遮罩轨道

    # 添加标题文字
    if style.get("has_title") and style.get("title_text"):
        project.add_text_simple(
            style["title_text"], 0, 2000000, "Titles",
            style=draft.TextStyle(size=8.0),
            border=draft.TextBorder(color=(0, 0, 0), alpha=1.0, width=60.0)
        )

    # 保存
    result = project.save()
    return result


# ============ 主入口 ============
def create_template_from_video(video_path: str,
                               project_name: str = None,
                               output_dir: str = None) -> Dict[str, Any]:
    """
    从教学视频创建风格复刻剪映模板

    Args:
        video_path: 教学视频路径
        project_name: 工程名称（默认自动生成）
        output_dir: 素材输出目录

    Returns:
        {
            "status": "success"/"failed",
            "draft_path": 剪映草稿路径,
            "project_name": 工程名,
            "style": 风格分析结果,
            "segment_count": 片段数,
            "assets": 生成的素材路径列表,
        }
    """
    task_id = uuid.uuid4().hex[:8]

    try:
        # 1. 视频解析
        logger.info(f"[1/4] 解析视频: {os.path.basename(video_path)}")
        video_info = analyze_video(video_path)
        logger.info(f"  分辨率: {video_info['width']}x{video_info['height']}, "
                    f"时长: {video_info['duration']:.1f}s")

        # 2. 提取关键帧 + 风格分析
        logger.info("[2/4] 提取关键帧并分析风格")
        keyframes = extract_keyframes(video_path, video_info["duration"])
        style = analyze_style(video_info, keyframes)
        logger.info(f"  模板类型: {style['type']}, "
                    f"片段数: {style['segment_count']}")

        # 3. 生成占位素材
        logger.info("[3/4] 生成占位素材")
        asset_dir = output_dir or os.path.join(WORK_DIR, f"assets_{task_id}")
        assets = generate_placeholder_assets(style, asset_dir)

        # 4. 构建剪映工程
        logger.info("[4/4] 构建剪映工程")
        pname = project_name or f"风格复刻_{os.path.splitext(os.path.basename(video_path))[0]}"
        result = build_jianying_project(style, assets, pname)

        return {
            "status": "success",
            "task_id": task_id,
            "draft_path": result.get("draft_path", ""),
            "project_name": pname,
            "style": style,
            "segment_count": len(assets),
            "assets": assets,
            "video_info": video_info,
        }

    except Exception as e:
        logger.error(f"模板创建失败: {e}", exc_info=True)
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    import argparse
    parser = argparse.ArgumentParser(description="从教学视频创建风格复刻剪映模板")
    parser.add_argument("video", help="教学视频路径")
    parser.add_argument("--name", help="工程名称", default=None)
    args = parser.parse_args()

    result = create_template_from_video(args.video, args.name)
    print(json.dumps(result, indent=2, ensure_ascii=False))
