"""
文字排版预设特效
基于抖音教程《文字排版常用技巧》分析封装

制作手法：
- 多轨道文字叠加，竖排/横排/错落排列
- 颜色区分主副文字
- 位置错开形成层次感
- 入场动画错开，形成节奏感

API支持：
- 剪映原生文字轨道，多轨道叠加
- 支持入场动画
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
from typing import List, Dict

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


# 排版预设
LAYOUT_PRESETS = {
    "vertical_stagger": {
        "name": "竖排错落",
        "description": "三列竖排文字，主标题黄色高亮，副文白色，位置错落",
        "columns": 3,
        "direction": "vertical",
        "colors": [(1.0, 0.85, 0.3), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)],
        "sizes": [12.0, 9.0, 10.0],
        "x_offsets": [0.25, 0.0, -0.25],
        "y_offsets": [0.0, 0.1, -0.1],
        "stagger": 0.3,
        "anim_in": ["弹入", "渐显", "渐显"],
    },
    "horizontal_title": {
        "name": "横排标题",
        "description": "主标题大字+副标题小字，横排居中",
        "columns": 2,
        "direction": "horizontal",
        "colors": [(1.0, 1.0, 1.0), (0.8, 0.8, 0.8)],
        "sizes": [14.0, 7.0],
        "x_offsets": [0.0, 0.0],
        "y_offsets": [0.15, -0.15],
        "stagger": 0.2,
        "anim_in": ["放大", "渐显"],
    },
    "diagonal_cascade": {
        "name": "斜向层叠",
        "description": "文字沿对角线层叠排列，颜色渐变",
        "columns": 3,
        "direction": "diagonal",
        "colors": [(1.0, 0.4, 0.4), (1.0, 0.7, 0.3), (1.0, 0.9, 0.5)],
        "sizes": [11.0, 10.0, 9.0],
        "x_offsets": [-0.3, 0.0, 0.3],
        "y_offsets": [0.2, 0.0, -0.2],
        "stagger": 0.25,
        "anim_in": ["弹入", "弹入", "弹入"],
    },
    "left_align_stack": {
        "name": "左对齐堆叠",
        "description": "文字左对齐堆叠，序号标签+主标题+描述",
        "columns": 3,
        "direction": "horizontal",
        "colors": [(0.3, 0.8, 1.0), (1.0, 1.0, 1.0), (0.7, 0.7, 0.7)],
        "sizes": [8.0, 12.0, 6.0],
        "x_offsets": [-0.4, -0.4, -0.4],
        "y_offsets": [0.25, 0.05, -0.15],
        "stagger": 0.2,
        "anim_in": ["打字机_I", "弹入", "渐显"],
    },
    "center_focus": {
        "name": "居中聚焦",
        "description": "主标题居中放大，两侧装饰文字",
        "columns": 3,
        "direction": "horizontal",
        "colors": [(0.6, 0.6, 0.6), (1.0, 0.85, 0.3), (0.6, 0.6, 0.6)],
        "sizes": [7.0, 16.0, 7.0],
        "x_offsets": [-0.45, 0.0, 0.45],
        "y_offsets": [0.0, 0.0, 0.0],
        "stagger": 0.15,
        "anim_in": ["渐显", "放大", "渐显"],
    },
}


def add_text_layout(
    project,
    texts: List[str],
    layout: str = "vertical_stagger",
    start_time: float = 0.0,
    duration: float = 3.0,
    custom_config: Dict = None,
) -> Dict:
    """在已有剪映工程中添加文字排版效果

    Args:
        project: JyProject 实例
        texts: 文字列表，每个元素对应一列/一行
        layout: 预设名称 vertical_stagger/horizontal_title/diagonal_cascade/left_align_stack/center_focus
        start_time: 起始时间（秒）
        duration: 持续时长（秒）
        custom_config: 自定义配置覆盖

    Returns:
        结果字典
    """
    cfg = LAYOUT_PRESETS.get(layout, LAYOUT_PRESETS["vertical_stagger"]).copy()
    if custom_config:
        cfg.update(custom_config)

    n = min(len(texts), cfg["columns"])
    added = []

    for i in range(n):
        text = texts[i]
        col_start = start_time + i * cfg["stagger"]
        col_duration = duration - i * cfg["stagger"] * 0.5

        color = cfg["colors"][i % len(cfg["colors"])]
        size = cfg["sizes"][i % len(cfg["sizes"])]
        x_off = cfg["x_offsets"][i % len(cfg["x_offsets"])]
        y_off = cfg["y_offsets"][i % len(cfg["y_offsets"])]
        anim = cfg["anim_in"][i % len(cfg["anim_in"])]

        # 竖排文字需要逐字换行
        display_text = text
        if cfg["direction"] == "vertical":
            display_text = "\n".join(list(text))

        seg = project.add_text_simple(
            display_text,
            start_time=f"{col_start:.2f}s",
            duration=f"{col_duration:.2f}s",
            font_size=size,
            color_rgb=color,
            style=draft.TextStyle(size=size, bold=True),
            border=draft.TextBorder(color=(0, 0, 0), width=30),
            clip_settings=draft.ClipSettings(
                transform_x=x_off,
                transform_y=y_off,
            ),
            anim_in=anim,
            track_name=f"TextLayout_{i}",
        )
        if seg:
            added.append({"text": text, "start": col_start, "duration": col_duration})

    return {
        "status": "success",
        "layout": layout,
        "text_count": len(added),
        "duration": duration,
        "start_time": start_time,
        "added": added,
    }


def create_text_layout_demo(
    project_name: str = "TextLayout_Demo",
    width: int = 1080,
    height: int = 1920,
) -> Dict:
    """创建文字排版演示工程（所有预设各展示一段）

    Args:
        project_name: 工程名
        width: 画布宽
        height: 画布高

    Returns:
        工程信息字典
    """
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 黑色背景
    bg_path = os.path.join(MODULE_DIR, "text_layout_assets", "black_bg.png")
    os.makedirs(os.path.dirname(bg_path), exist_ok=True)
    from PIL import Image
    Image.new("RGB", (width, height), (20, 20, 20)).save(bg_path)

    demo_texts = {
        "vertical_stagger": ["是什么让", "食无肉病无药的", "绝境"],
        "horizontal_title": ["一眼万年", "—— 文字排版艺术"],
        "diagonal_cascade": ["过去", "现在", "未来"],
        "left_align_stack": ["01", "文字排版", "常用技巧与实战"],
        "center_focus": ["光影", "文字之美", "叙事"],
    }

    current_time = 0.0
    results = []

    for layout_name, texts in demo_texts.items():
        seg_duration = 3.5
        result = add_text_layout(
            project, texts,
            layout=layout_name,
            start_time=current_time,
            duration=seg_duration,
        )
        results.append(result)
        current_time += seg_duration + 0.5

    # 添加背景（覆盖全程）
    project.add_media_safe(
        bg_path,
        start_time="0s",
        duration=f"{current_time}s",
        track_name="BG",
    )

    project.save()
    logger.info(f"✅ 文字排版演示工程创建完成: {project_name}")
    logger.info(f"   预设数: {len(results)}, 总时长: {current_time:.1f}s")

    return {
        "project_name": project_name,
        "layouts": list(demo_texts.keys()),
        "total_duration": current_time,
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("文字排版预设特效")
    logger.info("=" * 60)
    logger.info("可用预设:")
    for name, cfg in LAYOUT_PRESETS.items():
        logger.info(f"  - {name}: {cfg['name']} - {cfg['description']}")
    logger.info("\n用法:")
    logger.info("  add_text_layout(project, ['文字1', '文字2'], layout='vertical_stagger')")
    logger.info("  create_text_layout_demo()")
