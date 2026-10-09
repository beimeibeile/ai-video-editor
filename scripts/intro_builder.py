"""
片头生成器
组合特效库中的多个特效，生成可复用的短视频片头模板

模板类型：
- flash_title: 蒙版快闪+字幕条标题（适合卡点/炫酷风格）
- minimal_title: 简洁字幕条+淡入（适合治愈/文艺风格）
- cyber_intro: 赛博朋克风格快闪+霓虹字幕条

使用方式：
    from intro_builder import create_intro
    create_intro("flash_title", title="每日一练", subtitle="剪辑进阶")
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
from typing import Dict, List, Any

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

# 导入特效模块
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MODULE_DIR)
from mask_flash_transition import create_solid_color_image
try:
    from mask_flash_transition import add_expand_animation
except ImportError:
    add_expand_animation = None  # 旧版接口已移除，使用蒙版关键帧替代
from subtitle_bar import add_subtitle_bar, BAR_STYLES


# ──────────────────────────────────────────────
# 片头模板预设
# ──────────────────────────────────────────────

INTRO_TEMPLATES = {
    "flash_title": {
        "name": "快闪标题",
        "duration": 3.0,
        "description": "蒙版快闪转场+字幕条标题，适合卡点/炫酷风格",
        "flash_colors": [(0, 255, 255), (255, 0, 255), (255, 255, 0)],
        "flash_directions": ["left", "right", "center"],
        "flash_duration": 0.8,
        "bar_style": "pill_cyber",
        "bar_position_y": 0.0,
        "bar_anim_in": "弹入",
        "bg_color": (15, 15, 25),
    },
    "minimal_title": {
        "name": "极简标题",
        "duration": 2.5,
        "description": "简洁字幕条+淡入，适合治愈/文艺风格",
        "flash_colors": None,  # 无快闪
        "bar_style": "rect_minimal",
        "bar_position_y": 0.0,
        "bar_anim_in": "渐显",
        "bg_color": (245, 245, 245),
    },
    "warm_intro": {
        "name": "温暖开场",
        "duration": 3.0,
        "description": "暖色快闪+温暖字幕条，适合生活/情感风格",
        "flash_colors": [(255, 200, 100), (255, 150, 100), (255, 100, 150)],
        "flash_directions": ["top", "bottom", "center"],
        "flash_duration": 1.0,
        "bar_style": "pill_warm",
        "bar_position_y": 0.0,
        "bar_anim_in": "向上滑动",
        "bg_color": (30, 20, 15),
    },
    "cyber_intro": {
        "name": "赛博开场",
        "duration": 3.5,
        "description": "赛博朋克快闪+霓虹字幕条，适合科技/未来风格",
        "flash_colors": [(0, 255, 255), (255, 0, 255), (0, 255, 100), (255, 255, 0)],
        "flash_directions": ["left", "right", "top", "bottom"],
        "flash_duration": 0.6,
        "bar_style": "pill_cyber",
        "bar_position_y": 0.1,
        "bar_anim_in": "弹性伸缩",
        "bg_color": (10, 10, 20),
    },
    "tag_intro": {
        "name": "标签开场",
        "duration": 2.0,
        "description": "小标签快闪+标题，适合短视频钩子开场",
        "flash_colors": [(255, 80, 80)],
        "flash_directions": ["left"],
        "flash_duration": 0.5,
        "bar_style": "tag_small",
        "bar_position_y": 0.3,
        "bar_anim_in": "向左滑动",
        "bg_color": (20, 20, 20),
    },
}


# ──────────────────────────────────────────────
# 核心：创建片头
# ──────────────────────────────────────────────

def create_intro(
    template: str = "flash_title",
    title: str = "标题",
    subtitle: str = None,
    project_name: str = None,
    width: int = 1080,
    height: int = 1920,
    output_dir: str = None,
    custom_config: Dict = None,
) -> Dict[str, Any]:
    """创建片头工程

    Args:
        template: 模板名称（flash_title/minimal_title/warm_intro/cyber_intro/tag_intro）
        title: 主标题文字
        subtitle: 副标题文字（可选）
        project_name: 工程名（默认 Intro_{template}）
        width: 画布宽
        height: 画布高
        output_dir: 素材输出目录
        custom_config: 自定义配置覆盖

    Returns:
        工程信息字典
    """
    cfg = INTRO_TEMPLATES.get(template, INTRO_TEMPLATES["flash_title"]).copy()
    if custom_config:
        cfg.update(custom_config)

    if project_name is None:
        project_name = f"Intro_{template}"

    if output_dir is None:
        output_dir = os.path.join(MODULE_DIR, "intro_assets")
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"[片头生成器] 模板: {cfg['name']} ({template})")
    logger.info(f"  标题: {title}" + (f" / {subtitle}" if subtitle else ""))
    logger.info(f"  时长: {cfg['duration']}s")

    # 1. 创建工程
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 2. 添加背景
    bg_path = os.path.join(output_dir, f"bg_{template}.png")
    try:
        from PIL import Image
        bg = Image.new("RGB", (width, height), cfg["bg_color"])
        bg.save(bg_path)
        project.add_media_safe(bg_path, start_time="0s", duration=f"{cfg['duration']}s", track_name="BG")
    except Exception as e:
        logger.error(f"  ⚠️ 背景生成失败: {e}")

    # 3. 添加蒙版快闪（如果有）
    if cfg.get("flash_colors"):
        colors = cfg["flash_colors"]
        directions = cfg.get("flash_directions", ["center"] * len(colors))
        flash_dur = cfg.get("flash_duration", 0.8)
        stagger = flash_dur / len(colors) * 0.5

        for i, (color, direction) in enumerate(zip(colors, directions)):
            # 生成色块
            block_path = os.path.join(output_dir, f"flash_{template}_{i}.png")
            create_solid_color_image(color, width, height, block_path)

            # 添加到画中画轨道
            start = i * stagger
            seg = project.add_media_safe(
                block_path,
                start_time=f"{start:.2f}s",
                duration=f"{flash_dur:.2f}s",
                track_name=f"Flash_{i}",
            )

            if seg and add_expand_animation:
                # 添加展开动画
                add_expand_animation(
                    seg,
                    direction=direction,
                    duration_us=int(flash_dur * 1e6 * 0.8),
                    start_us=0,
                )
                # 淡出
                end_us = int(flash_dur * 1e6)
                fade_start = int(end_us * 0.7)
                seg.add_keyframe(draft.KeyframeProperty.alpha, fade_start, 1.0, **draft.Keyframe.EASE_OUT)
                seg.add_keyframe(draft.KeyframeProperty.alpha, end_us, 0.0, **draft.Keyframe.EASE_OUT)

        logger.info(f"  ✅ 快闪: {len(colors)}色块, {stagger:.2f}s错开")

    # 4. 添加字幕条标题
    bar_start = cfg["duration"] * 0.3  # 快闪后出现
    bar_duration = cfg["duration"] - bar_start
    add_subtitle_bar(
        project,
        text=title,
        start_time=f"{bar_start:.2f}s",
        duration=f"{bar_duration:.2f}s",
        style=cfg["bar_style"],
        position_y=cfg["bar_position_y"],
        anim_in=cfg["bar_anim_in"],
        output_dir=output_dir,
    )
    logger.info(f"  ✅ 标题: {title} ({cfg['bar_style']})")

    # 5. 添加副标题
    if subtitle:
        sub_start = bar_start + 0.3
        sub_duration = cfg["duration"] - sub_start
        project.add_text_simple(
            subtitle,
            start_time=f"{sub_start:.2f}s",
            duration=f"{sub_duration:.2f}s",
            font_size=6.0,
            color_rgb=(200, 200, 200),
            style=draft.TextStyle(size=6.0),
            clip_settings=draft.ClipSettings(transform_y=cfg["bar_position_y"] - 0.25),
            anim_in="渐显",
            track_name="Subtitle",
        )
        logger.info(f"  ✅ 副标题: {subtitle}")

    # 6. 保存
    project.save()
    logger.info(f"\n✅ 片头工程创建完成: {project_name}")
    logger.info(f"   草稿路径: {os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'JianyingPro', 'User Data', 'Projects', 'com.lveditor.draft', project_name)}")

    return {
        "project_name": project_name,
        "template": template,
        "title": title,
        "subtitle": subtitle,
        "duration": cfg["duration"],
    }


# ──────────────────────────────────────────────
# 批量创建多个片头
# ──────────────────────────────────────────────

def create_intro_batch(
    items: List[Dict[str, Any]],
    output_dir: str = None,
) -> List[Dict[str, Any]]:
    """批量创建片头

    Args:
        items: 片头配置列表，每个元素包含 template/title/subtitle/project_name
        output_dir: 素材输出目录

    Returns:
        结果列表
    """
    results = []
    for item in items:
        result = create_intro(
            template=item.get("template", "flash_title"),
            title=item.get("title", "标题"),
            subtitle=item.get("subtitle"),
            project_name=item.get("project_name"),
            output_dir=output_dir,
        )
        results.append(result)
    return results


def add_intro_to_project(
    project,
    template: str = "flash_title",
    title: str = "标题",
    subtitle: str = None,
    start_time: float = 0.0,
    width: int = 1080,
    height: int = 1920,
    output_dir: str = None,
    custom_config: Dict = None,
) -> float:
    """在已有剪映工程中添加片头（从指定时间开始）

    用于模式A/B流程集成，在正片之前插入片头。

    Args:
        project: JyProject实例（已创建的工程）
        template: 模板名称
        title: 主标题
        subtitle: 副标题（可选）
        start_time: 片头起始时间（秒），默认0
        width: 画布宽
        height: 画布高
        output_dir: 素材输出目录
        custom_config: 自定义配置覆盖

    Returns:
        片头时长（秒）
    """
    cfg = INTRO_TEMPLATES.get(template, INTRO_TEMPLATES["flash_title"]).copy()
    if custom_config:
        cfg.update(custom_config)

    duration = cfg["duration"]

    if output_dir is None:
        output_dir = os.path.join(MODULE_DIR, "intro_assets")
    os.makedirs(output_dir, exist_ok=True)

    # 1. 添加背景
    bg_path = os.path.join(output_dir, f"bg_{template}_{int(start_time*1000)}.png")
    try:
        from PIL import Image
        bg = Image.new("RGB", (width, height), cfg["bg_color"])
        bg.save(bg_path)
        project.add_media_safe(
            bg_path,
            start_time=f"{start_time:.2f}s",
            duration=f"{duration:.2f}s",
            track_name="IntroBG",
        )
    except Exception as e:
        logger.error(f"  ⚠️ 片头背景生成失败: {e}")

    # 2. 添加蒙版快闪
    if cfg.get("flash_colors"):
        colors = cfg["flash_colors"]
        directions = cfg.get("flash_directions", ["center"] * len(colors))
        flash_dur = cfg.get("flash_duration", 0.8)
        stagger = flash_dur / len(colors) * 0.5

        for i, (color, direction) in enumerate(zip(colors, directions)):
            block_path = os.path.join(output_dir, f"flash_{template}_{i}.png")
            create_solid_color_image(color, width, height, block_path)

            seg_start = start_time + i * stagger
            seg = project.add_media_safe(
                block_path,
                start_time=f"{seg_start:.2f}s",
                duration=f"{flash_dur:.2f}s",
                track_name=f"IntroFlash_{i}",
            )

            if seg and add_expand_animation:
                add_expand_animation(
                    seg,
                    direction=direction,
                    duration_us=int(flash_dur * 1e6 * 0.8),
                    start_us=0,
                )
                end_us = int(flash_dur * 1e6)
                fade_start = int(end_us * 0.7)
                seg.add_keyframe(draft.KeyframeProperty.alpha, fade_start, 1.0, **draft.Keyframe.EASE_OUT)
                seg.add_keyframe(draft.KeyframeProperty.alpha, end_us, 0.0, **draft.Keyframe.EASE_OUT)

    # 3. 添加字幕条标题
    bar_start = start_time + duration * 0.3
    bar_duration = duration - duration * 0.3
    add_subtitle_bar(
        project,
        text=title,
        start_time=f"{bar_start:.2f}s",
        duration=f"{bar_duration:.2f}s",
        style=cfg["bar_style"],
        position_y=cfg["bar_position_y"],
        anim_in=cfg["bar_anim_in"],
        output_dir=output_dir,
    )

    # 4. 添加副标题
    if subtitle:
        sub_start = bar_start + 0.3
        sub_duration = duration - (sub_start - start_time)
        project.add_text_simple(
            subtitle,
            start_time=f"{sub_start:.2f}s",
            duration=f"{sub_duration:.2f}s",
            font_size=6.0,
            color_rgb=(200, 200, 200),
            style=draft.TextStyle(size=6.0),
            clip_settings=draft.ClipSettings(transform_y=cfg["bar_position_y"] - 0.25),
            anim_in="渐显",
            track_name="IntroSub",
        )

    logger.info(f"  ✅ 片头已添加: {title} ({template}, {duration}s, 起始{start_time}s)")
    return duration


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("片头生成器 - 可用模板")
    logger.info("=" * 60)
    for tid, tcfg in INTRO_TEMPLATES.items():
        logger.info(f"\n  {tid}: {tcfg['name']}")
        logger.info(f"    {tcfg['description']}")
        logger.info(f"    时长: {tcfg['duration']}s, 字幕条: {tcfg['bar_style']}")

    logger.info("\n" + "=" * 60)
    logger.info("测试: 创建5种模板片头")
    logger.info("=" * 60)

    test_dir = r"D:\DobaoWork_Project\Ai_Video_Editor\debug\intro_test"
    os.makedirs(test_dir, exist_ok=True)

    tests = [
        {"template": "flash_title", "title": "每日一练", "subtitle": "剪辑进阶"},
        {"template": "minimal_title", "title": "治愈时光", "subtitle": "慢生活"},
        {"template": "warm_intro", "title": "温暖瞬间", "subtitle": "记录美好"},
        {"template": "cyber_intro", "title": "未来已来", "subtitle": "科技前沿"},
        {"template": "tag_intro", "title": "高能预警", "subtitle": None},
    ]

    for t in tests:
        try:
            create_intro(**t, output_dir=os.path.join(test_dir, "assets"))
        except Exception as e:
            logger.error(f"❌ {t['template']} 失败: {e}")
