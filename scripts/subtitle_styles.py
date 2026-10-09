#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
艺术字幕风格库
定义多种字幕风格，包括背景条颜色、发光颜色、字体大小、动画等
"""

from typing import Dict, Tuple, Any


# 字幕风格定义
# 每种风格包含：bar_color（背景条颜色）、glow_color（发光颜色RGB）、
# font_size（默认字号）、anim_in（入场动画）、anim_out（出场动画）、
# border_width（描边宽度）、description（风格描述）
SUBTITLE_STYLES: Dict[str, Dict[str, Any]] = {
    # ============ 原有风格 ============
    "epic": {
        "bar_color": "0x000000",
        "glow_color": (1.0, 0.85, 0.3),  # 金色
        "font_size": 8.0,
        "anim_in": "渐显",
        "anim_out": "渐隐",
        "border_width": 40,
        "description": "史诗感：黑色背景条+金色发光，适合大气开场",
    },
    "warm": {
        "bar_color": "0x2a1810",
        "glow_color": (1.0, 0.6, 0.2),  # 橙色
        "font_size": 8.0,
        "anim_in": "渐显",
        "anim_out": "渐隐",
        "border_width": 40,
        "description": "温暖感：深棕背景条+橙色发光，适合情感类",
    },
    "fun": {
        "bar_color": "0x1a1a2e",
        "glow_color": (0.3, 0.8, 1.0),  # 青色
        "font_size": 8.0,
        "anim_in": "放大",
        "anim_out": "缩小",
        "border_width": 40,
        "description": "活泼感：深蓝背景条+青色发光，适合趣味类",
    },
    "minimal": {
        "bar_color": "0x000000",
        "glow_color": (1.0, 1.0, 1.0),  # 白色
        "font_size": 7.0,
        "anim_in": "渐显",
        "anim_out": "渐隐",
        "border_width": 30,
        "description": "极简风：黑色背景条+白色发光，干净简洁",
    },

    # ============ 新增风格 ============
    "cinematic": {
        "bar_color": "0x0a0a0a",
        "glow_color": (1.0, 0.84, 0.0),  # 电影金
        "font_size": 9.0,
        "anim_in": "渐显",
        "anim_out": "渐隐",
        "border_width": 50,
        "description": "电影感：深黑背景条+电影金发光，适合影视解说",
    },
    "tech": {
        "bar_color": "0x0a1628",
        "glow_color": (0.0, 1.0, 0.9),  # 科技青
        "font_size": 8.0,
        "anim_in": "向右滑动",
        "anim_out": "向左滑动",
        "border_width": 40,
        "description": "科技感：深蓝背景条+科技青发光，适合科技产品",
    },
    "elegant": {
        "bar_color": "0x1a0a1a",
        "glow_color": (1.0, 0.4, 0.7),  # 优雅粉
        "font_size": 8.5,
        "anim_in": "渐显",
        "anim_out": "渐隐",
        "border_width": 35,
        "description": "优雅感：深紫背景条+粉色发光，适合美妆/时尚",
    },
    "bold": {
        "bar_color": "0x2a0a0a",
        "glow_color": (1.0, 1.0, 1.0),  # 白色
        "font_size": 10.0,
        "anim_in": "动感放大",
        "anim_out": "缩小",
        "border_width": 60,
        "description": "醒目感：深红背景条+白色粗体，适合强调/标题",
    },
    "retro": {
        "bar_color": "0x2a1a0a",
        "glow_color": (1.0, 0.55, 0.0),  # 复古橙
        "font_size": 8.0,
        "anim_in": "打字机",
        "anim_out": "渐隐",
        "border_width": 40,
        "description": "复古感：深棕背景条+复古橙发光，适合怀旧类",
    },
    "neon": {
        "bar_color": "0x000000",
        "glow_color": (0.0, 1.0, 0.5),  # 霓虹绿
        "font_size": 9.0,
        "anim_in": "闪烁",
        "anim_out": "渐隐",
        "border_width": 45,
        "description": "霓虹感：黑色背景条+霓虹绿发光，适合赛博朋克",
    },
    "vlog": {
        "bar_color": "0xffffff",
        "glow_color": (0.0, 0.0, 0.0),  # 黑色
        "font_size": 7.5,
        "anim_in": "向上滑动",
        "anim_out": "向下滑动",
        "border_width": 0,
        "description": "Vlog风：白色背景条+黑色文字，适合日常vlog",
    },
    "news": {
        "bar_color": "0x0a1a3a",
        "glow_color": (1.0, 1.0, 1.0),  # 白色
        "font_size": 8.0,
        "anim_in": "向左滑动",
        "anim_out": "向右滑动",
        "border_width": 40,
        "description": "新闻感：深蓝背景条+白色文字，适合资讯/新闻",
    },
}


def get_style(style_name: str) -> Dict[str, Any]:
    """
    获取字幕风格配置

    Args:
        style_name: 风格名称

    Returns:
        风格配置字典，不存在时返回epic风格
    """
    return SUBTITLE_STYLES.get(style_name, SUBTITLE_STYLES["epic"])


def list_styles() -> list:
    """列出所有可用风格"""
    return [
        {"name": name, "description": style["description"]}
        for name, style in SUBTITLE_STYLES.items()
    ]


def get_style_names() -> list:
    """获取所有风格名称列表"""
    return list(SUBTITLE_STYLES.keys())


if __name__ == "__main__":
    print("=== 艺术字幕风格库 ===")
    print(f"共 {len(SUBTITLE_STYLES)} 种风格\n")
    for name, style in SUBTITLE_STYLES.items():
        print(f"  [{name}]")
        print(f"    描述: {style['description']}")
        print(f"    背景条: {style['bar_color']}")
        print(f"    发光色: {style['glow_color']}")
        print(f"    字号: {style['font_size']}")
        print(f"    动画: {style['anim_in']} → {style['anim_out']}")
        print()
