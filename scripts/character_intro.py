"""
人物介绍卡片特效
基于教程《狂飙》人物介绍效果分析封装

制作手法：
- 纯色/渐变背景
- 人物照片+白色边框，依次入场（缩放+旋转+位移）
- 名字文字标签，带颜色区分
- 入场动画错开，形成节奏感

API限制：
- 3D倾斜用2D旋转+缩放模拟
- 边框用Pillow预生成带边框的图片
"""
import os
import sys
from typing import List, Dict, Optional, Tuple

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
# pyJianYingDraft已迁移到适配层
import os as _os, sys as _sys
_AVR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _AVR not in _sys.path: _sys.path.insert(0, _AVR)

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


# 预设配色方案
CARD_PRESETS = {
    "red_drama": {
        "bg_color": (120, 0, 0),
        "bg_gradient": (60, 0, 0),
        "border_color": (255, 255, 255),
        "border_width": 6,
        "name_colors": [(255, 60, 60), (255, 200, 60), (60, 255, 120)],
        "name_size": 14.0,
        "card_width": 0.5,
        "card_height": 0.35,
        "stagger": 0.4,
        "card_duration": 2.5,
    },
    "cyber_tech": {
        "bg_color": (10, 10, 30),
        "bg_gradient": (0, 0, 15),
        "border_color": (0, 200, 255),
        "border_width": 4,
        "name_colors": [(0, 200, 255), (255, 0, 200), (200, 255, 0)],
        "name_size": 12.0,
        "card_width": 0.45,
        "card_height": 0.3,
        "stagger": 0.35,
        "card_duration": 2.0,
    },
    "warm_friends": {
        "bg_color": (40, 20, 10),
        "bg_gradient": (20, 10, 5),
        "border_color": (255, 220, 180),
        "border_width": 5,
        "name_colors": [(255, 180, 100), (255, 220, 150), (200, 255, 200)],
        "name_size": 13.0,
        "card_width": 0.48,
        "card_height": 0.32,
        "stagger": 0.45,
        "card_duration": 2.8,
    },
    "minimal_white": {
        "bg_color": (240, 240, 240),
        "bg_gradient": (200, 200, 200),
        "border_color": (30, 30, 30),
        "border_width": 3,
        "name_colors": [(30, 30, 30), (80, 80, 80), (120, 120, 120)],
        "name_size": 11.0,
        "card_width": 0.42,
        "card_height": 0.28,
        "stagger": 0.3,
        "card_duration": 2.0,
    },
}


def create_framed_portrait(
    image_path: str,
    output_path: str,
    border_color: Tuple[int, int, int] = (255, 255, 255),
    border_width: int = 6,
    target_width: int = 600,
    target_height: int = 800,
) -> str:
    """给人物照片添加边框，生成带框肖像图

    Args:
        image_path: 原始人物照片路径
        output_path: 输出路径
        border_color: 边框颜色RGB
        border_width: 边框宽度像素
        target_width: 目标宽度
        target_height: 目标高度

    Returns:
        输出图片路径
    """
    try:
        from PIL import Image, ImageOps

        img = Image.open(image_path).convert("RGB")
        # 居中裁剪到目标比例
        img = ImageOps.fit(img, (target_width, target_height), Image.LANCZOS)

        # 添加边框
        framed = ImageOps.expand(img, border=border_width, fill=border_color)
        framed.save(output_path, quality=95)
        return output_path
    except Exception as e:
        print(f"  ⚠️ 边框生成失败，使用原图: {e}")
        return image_path


def create_gradient_background(
    color_top: Tuple[int, int, int],
    color_bottom: Tuple[int, int, int],
    width: int,
    height: int,
    output_path: str,
) -> str:
    """生成渐变背景图"""
    try:
        from PIL import Image

        img = Image.new("RGB", (width, height))
        pixels = img.load()
        for y in range(height):
            ratio = y / height
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
            for x in range(width):
                pixels[x, y] = (r, g, b)
        img.save(output_path, quality=90)
        return output_path
    except Exception as e:
        print(f"  ⚠️ 渐变背景生成失败: {e}")
        return None


def add_card_entrance_animation(
    segment,
    duration_us: int,
    direction: str = "up",
    rotation: float = 0.0,
):
    """给卡片添加入场动画（缩放+位移+旋转）

    Args:
        segment: 视频片段
        duration_us: 片段时长微秒
        direction: 入场方向 up/down/left/right/zoom
        rotation: 初始旋转角度
    """
    anim_dur = int(duration_us * 0.4)  # 前40%做入场动画

    # 缩放：0→1
    segment.add_keyframe(KeyframeProperty.uniform_scale, 0, 0.3, **Keyframe.EASE_OUT)
    segment.add_keyframe(KeyframeProperty.uniform_scale, anim_dur, 1.0, **Keyframe.EASE_OUT)

    # 位移
    if direction == "up":
        segment.add_keyframe(KeyframeProperty.position_y, 0, -0.5, **Keyframe.EASE_OUT)
        segment.add_keyframe(KeyframeProperty.position_y, anim_dur, 0.0, **Keyframe.EASE_OUT)
    elif direction == "down":
        segment.add_keyframe(KeyframeProperty.position_y, 0, 0.5, **Keyframe.EASE_OUT)
        segment.add_keyframe(KeyframeProperty.position_y, anim_dur, 0.0, **Keyframe.EASE_OUT)
    elif direction == "left":
        segment.add_keyframe(KeyframeProperty.position_x, 0, -0.5, **Keyframe.EASE_OUT)
        segment.add_keyframe(KeyframeProperty.position_x, anim_dur, 0.0, **Keyframe.EASE_OUT)
    elif direction == "right":
        segment.add_keyframe(KeyframeProperty.position_x, 0, 0.5, **Keyframe.EASE_OUT)
        segment.add_keyframe(KeyframeProperty.position_x, anim_dur, 0.0, **Keyframe.EASE_OUT)

    # 旋转（如果有）
    if rotation != 0:
        segment.add_keyframe(KeyframeProperty.rotation, 0, rotation, **Keyframe.EASE_OUT)
        segment.add_keyframe(KeyframeProperty.rotation, anim_dur, 0.0, **Keyframe.EASE_OUT)

    # 透明度
    segment.add_keyframe(KeyframeProperty.alpha, 0, 0.0, **Keyframe.EASE_OUT)
    segment.add_keyframe(KeyframeProperty.alpha, int(anim_dur * 0.5), 1.0, **Keyframe.EASE_OUT)


def create_character_intro(
    project_name: str,
    characters: List[Dict],
    preset: str = "red_drama",
    width: int = 1080,
    height: int = 1920,
    output_dir: str = None,
    custom_config: Dict = None,
) -> Dict:
    """创建人物介绍卡片视频工程

    Args:
        project_name: 工程名
        characters: 人物列表，每个元素包含 {"image": 路径, "name": 名字, "subtitle": 副标题(可选)}
        preset: 预设名称 red_drama/cyber_tech/warm_friends/minimal_white
        width: 画布宽
        height: 画布高
        output_dir: 素材输出目录
        custom_config: 自定义配置覆盖

    Returns:
        工程信息字典
    """
    cfg = CARD_PRESETS.get(preset, CARD_PRESETS["red_drama"]).copy()
    if custom_config:
        cfg.update(custom_config)

    if output_dir is None:
        output_dir = os.path.join(MODULE_DIR, "character_intro_assets")
    os.makedirs(output_dir, exist_ok=True)

    # 1. 生成背景
    print(f"[1/4] 生成渐变背景...")
    bg_path = os.path.join(output_dir, f"bg_{preset}.png")
    create_gradient_background(cfg["bg_color"], cfg["bg_gradient"], width, height, bg_path)

    # 2. 生成带框人物照
    print(f"[2/4] 生成 {len(characters)} 张带框人物照...")
    framed_images = []
    for i, char in enumerate(characters):
        if not os.path.exists(char.get("image", "")):
            print(f"  ⚠️ 人物{i}图片不存在，跳过")
            continue
        framed_path = os.path.join(output_dir, f"framed_{i}.png")
        create_framed_portrait(
            char["image"], framed_path,
            border_color=cfg["border_color"],
            border_width=cfg["border_width"],
        )
        framed_images.append((framed_path, char))
        print(f"  ✅ {char.get('name', f'人物{i}')}")

    # 3. 创建工程
    print(f"[3/4] 创建工程: {project_name}")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 添加背景
    total_duration = len(framed_images) * cfg["stagger"] + cfg["card_duration"]
    project.add_media_safe(bg_path, start_time="0s", duration=f"{total_duration}s", track_name="BG")

    # 4. 添加人物卡片+名字
    print(f"[4/4] 添加人物卡片和名字...")
    directions = ["up", "down", "left", "right", "up", "down"]
    rotations = [-5, 5, -3, 3, -8, 8]

    for i, (img_path, char) in enumerate(framed_images):
        start_time = i * cfg["stagger"]
        card_dur = cfg["card_duration"]

        # 人物卡片（画中画轨道）
        seg = project.add_media_safe(
            img_path,
            start_time=f"{start_time:.2f}s",
            duration=f"{card_dur}s",
            track_name=f"Card_{i}",
        )

        if seg:
            # 设置卡片位置（垂直排列，错开）
            y_offset = (i - len(framed_images) / 2 + 0.5) * 0.35
            seg.clip_settings = ClipSettings(
                transform_x=0.0,
                transform_y=y_offset,
            )
            # 入场动画
            add_card_entrance_animation(
                seg,
                duration_us=int(card_dur * 1e6),
                direction=directions[i % len(directions)],
                rotation=rotations[i % len(rotations)],
            )

            # 名字文字
            name_color = cfg["name_colors"][i % len(cfg["name_colors"])]
            name_y = y_offset - 0.22
            project.add_text_simple(
                char.get("name", f"人物{i}"),
                start_time=f"{start_time + 0.2:.2f}s",
                duration=f"{card_dur - 0.2}s",
                font_size=cfg["name_size"],
                color_rgb=tuple(c / 255 for c in name_color),
                style=TextStyle(size=cfg["name_size"], bold=True),
                border=TextBorder(color=(0, 0, 0), width=40),
                clip_settings=ClipSettings(transform_y=name_y),
                anim_in="弹入",
                track_name=f"Name_{i}",
            )

            # 副标题
            if char.get("subtitle"):
                project.add_text_simple(
                    char["subtitle"],
                    start_time=f"{start_time + 0.4:.2f}s",
                    duration=f"{card_dur - 0.4}s",
                    font_size=6.0,
                    color_rgb=(200, 200, 200),
                    style=TextStyle(size=6.0),
                    clip_settings=ClipSettings(transform_y=name_y - 0.12),
                    anim_in="渐显",
                    track_name=f"Sub_{i}",
                )

            print(f"  ✅ {char.get('name', f'人物{i}')} ({start_time:.1f}s)")

    project.save()
    print(f"\n✅ 人物介绍卡片工程创建完成: {project_name}")
    print(f"   人物数: {len(framed_images)}, 总时长: {total_duration:.1f}s")

    return {
        "project_name": project_name,
        "character_count": len(framed_images),
        "total_duration": total_duration,
        "preset": preset,
    }


def add_character_intro_to_project(
    project,
    characters: List[Dict],
    preset: str = "red_drama",
    start_time: float = 0.0,
    width: int = 1080,
    height: int = 1920,
    output_dir: str = None,
) -> Dict:
    """在已有剪映工程中添加人物介绍卡片

    Args:
        project: JyProject 实例（已有工程）
        characters: 人物列表 [{"image": 路径, "name": 名字, "subtitle": 副标题(可选)}]
        preset: 预设名称 red_drama/cyber_tech/warm_friends/minimal_white
        start_time: 起始时间（秒）
        width: 画布宽
        height: 画布高
        output_dir: 素材输出目录

    Returns:
        结果字典
    """
    cfg = CARD_PRESETS.get(preset, CARD_PRESETS["red_drama"]).copy()

    if output_dir is None:
        output_dir = os.path.join(MODULE_DIR, "character_intro_assets")
    os.makedirs(output_dir, exist_ok=True)

    # 1. 生成背景
    bg_path = os.path.join(output_dir, f"bg_{preset}.png")
    if not os.path.exists(bg_path):
        create_gradient_background(cfg["bg_color"], cfg["bg_gradient"], width, height, bg_path)

    # 2. 生成带框人物照
    framed_images = []
    for i, char in enumerate(characters):
        if not os.path.exists(char.get("image", "")):
            print(f"  ⚠️ 人物{i}图片不存在，跳过")
            continue
        framed_path = os.path.join(output_dir, f"framed_{i}.png")
        create_framed_portrait(
            char["image"], framed_path,
            border_color=cfg["border_color"],
            border_width=cfg["border_width"],
        )
        framed_images.append((framed_path, char))

    if not framed_images:
        return {"status": "failed", "reason": "无有效人物图片"}

    # 3. 添加背景
    total_duration = len(framed_images) * cfg["stagger"] + cfg["card_duration"]
    project.add_media_safe(
        bg_path,
        start_time=f"{start_time:.2f}s",
        duration=f"{total_duration:.2f}s",
        track_name="CharBG",
    )

    # 4. 添加人物卡片+名字
    directions = ["up", "down", "left", "right", "up", "down"]
    rotations = [-5, 5, -3, 3, -8, 8]

    for i, (img_path, char) in enumerate(framed_images):
        card_start = start_time + i * cfg["stagger"]
        card_dur = cfg["card_duration"]

        # 人物卡片（画中画轨道）
        seg = project.add_media_safe(
            img_path,
            start_time=f"{card_start:.2f}s",
            duration=f"{card_dur:.2f}s",
            track_name=f"CharCard_{i}",
        )

        if seg:
            y_offset = (i - len(framed_images) / 2 + 0.5) * 0.35
            seg.clip_settings = ClipSettings(
                transform_x=0.0,
                transform_y=y_offset,
            )
            add_card_entrance_animation(
                seg,
                duration_us=int(card_dur * 1e6),
                direction=directions[i % len(directions)],
                rotation=rotations[i % len(rotations)],
            )

            # 名字文字
            name_color = cfg["name_colors"][i % len(cfg["name_colors"])]
            name_y = y_offset - 0.22
            project.add_text_simple(
                char.get("name", f"人物{i}"),
                start_time=f"{card_start + 0.2:.2f}s",
                duration=f"{card_dur - 0.2:.2f}s",
                font_size=cfg["name_size"],
                color_rgb=tuple(c / 255 for c in name_color),
                style=TextStyle(size=cfg["name_size"], bold=True),
                border=TextBorder(color=(0, 0, 0), width=40),
                clip_settings=ClipSettings(transform_y=name_y),
                anim_in="弹入",
                track_name=f"CharName_{i}",
            )

            # 副标题
            if char.get("subtitle"):
                project.add_text_simple(
                    char["subtitle"],
                    start_time=f"{card_start + 0.4:.2f}s",
                    duration=f"{card_dur - 0.4:.2f}s",
                    font_size=6.0,
                    color_rgb=(200, 200, 200),
                    style=TextStyle(size=6.0),
                    clip_settings=ClipSettings(transform_y=name_y - 0.12),
                    anim_in="渐显",
                    track_name=f"CharSub_{i}",
                )

    return {
        "status": "success",
        "character_count": len(framed_images),
        "duration": total_duration,
        "preset": preset,
        "start_time": start_time,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("人物介绍卡片特效")
    print("=" * 60)
    print("可用预设:")
    for name in CARD_PRESETS:
        print(f"  - {name}")
    print("\n用法:")
    print("  create_character_intro(")
    print("    project_name='测试',")
    print("    characters=[")
    print("      {'image': 'person1.jpg', 'name': '张三', 'subtitle': '主角'},")
    print("      {'image': 'person2.jpg', 'name': '李四', 'subtitle': '反派'},")
    print("    ],")
    print("    preset='red_drama'")
    print("  )")
