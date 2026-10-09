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
    当前基于视频元数据和已知模板模式进行推断
    后续可接入视觉模型进行深度分析
    """
    width = video_info["width"]
    height = video_info["height"]
    duration = video_info["duration"]

    # 判断横竖屏
    orientation = "portrait" if height > width else "landscape"

    # 估算片段数（基于时长，每段3-4秒）
    segment_count = max(3, min(8, int(duration / 3.5)))

    # 默认风格配置（电影感画幅卡点模板）
    style = {
        "template_type": "cinematic_bar",  # 电影感画幅
        "orientation": orientation,
        "segment_count": segment_count,
        "segment_duration": 3.5,  # 秒
        "transition_duration": 0.5,  # 秒
        "has_letterbox": True,  # 上下黑边
        "letterbox_ratio": 0.13,  # 黑边占比
        "has_big_numbers": True,  # 大数字编号
        "has_decor_text": True,  # 装饰英文文字
        "has_title": True,  # 标题文字
        "title_text": "电影感画幅",
        "transitions": ["运镜转场", "幻灯", "翻页", "模糊", "淡化"],
        # 配色方案（6种主色）
        "palette": [
            "#FF6B35", "#00B4D8", "#B8E0D2",
            "#7B2D8E", "#FF8C42", "#2EC4B6",
            "#E63946", "#F4A261",
        ],
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
    }

    return style


# ============ 步骤3：素材生成 ============
def generate_placeholder_assets(style: Dict[str, Any], output_dir: str) -> List[str]:
    """生成占位素材（完整画布，上下内置黑边，中间彩色内容区+数字+装饰文字）"""
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

    letterbox_h = int(canvas_h * style["letterbox_ratio"])
    content_top = letterbox_h
    content_bottom = canvas_h - letterbox_h
    content_h = content_bottom - content_top

    assets = []
    palette = style["palette"]
    phrases = style["decor_phrases"]

    for i in range(style["segment_count"]):
        color = palette[i % len(palette)]
        num = str(i + 1)
        phrase = phrases[i % len(phrases)]

        # 完整画布：黑色背景 + 中间彩色内容区
        img = Image.new("RGB", (canvas_w, canvas_h), "black")
        draw = ImageDraw.Draw(img)

        # 画中间彩色内容区
        draw.rectangle([(0, content_top), (canvas_w, content_bottom)], fill=color)

        # 大号数字
        try:
            font_large = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", int(content_h * 0.28))
            font_small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", int(content_h * 0.028))
        except Exception:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # 数字居中（在内容区内）
        bbox = draw.textbbox((0, 0), num, font=font_large)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        num_y = content_top + (content_h - th) // 2 - int(content_h * 0.08)
        draw.text(((canvas_w - tw) // 2, num_y), num, fill="white", font=font_large)

        # 装饰文字（数字下方，留出间距）
        if style["has_decor_text"]:
            bbox2 = draw.textbbox((0, 0), phrase, font=font_small)
            tw2 = bbox2[2] - bbox2[0]
            decor_y = num_y + th + int(content_h * 0.06)
            draw.text(((canvas_w - tw2) // 2, decor_y), phrase, fill="white", font=font_small)

        path = os.path.join(output_dir, f"segment_{i + 1}.png")
        img.save(path)
        assets.append(path)
        logger.info(f"生成占位素材: {os.path.basename(path)}")

    return assets


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
        logger.info(f"  模板类型: {style['template_type']}, "
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
