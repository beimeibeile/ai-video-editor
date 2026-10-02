"""
短视频标签引擎 v1.0
标签驱动的特效匹配系统：输入主题/风格/节奏标签 → 自动匹配特效组合和参数

标签体系：
- 风格标签(style): 赛博朋克/故障风/复古/水墨/极简/科技感/日系/港风/暗黑/明亮/vlog
- 节奏标签(rhythm): 快切/卡点/慢节奏/变速/鼓点/舒缓
- 转场标签(transition): 闪白/划像/缩放/旋转/故障/模糊/黑场/百叶窗
- 文字标签(text): 大字报/打字机/弹幕/花字/描边/渐变/字幕条
- 特效标签(effect): 发光/粒子/光效/抖动/缩放冲击/分屏/拍立得
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional, Tuple

# 标签→特效映射表
TAG_EFFECT_MAP = {
    # === 风格标签 ===
    "赛博朋克": {
        "effects": ["glow_outline", "blender_particles"],
        "params": {"glow_color": (0, 255, 200), "particle": "neon", "text_color": (0, 255, 200)},
        "bgm_mood": "cyberpunk",
    },
    "故障风": {
        "effects": ["mask_flash_transition"],
        "params": {"flash_colors": "neon", "direction": "horizontal", "intensity": "high"},
        "bgm_mood": "glitch",
    },
    "复古": {
        "effects": ["blender_particles"],
        "params": {"particle": "bokeh", "warm_tone": True},
        "bgm_mood": "retro",
    },
    "水墨": {
        "effects": ["mask_flash_transition"],
        "params": {"flash_colors": "mono", "direction": "center"},
        "bgm_mood": "ink",
    },
    "极简": {
        "effects": ["text_bg_slide"],
        "params": {"bg_color": (255, 255, 255), "text_color": (0, 0, 0), "minimal": True},
        "bgm_mood": "minimal",
    },
    "科技感": {
        "effects": ["stack_intro", "blender_light_sweep"],
        "params": {"stack_colors": "tech", "light_sweep": True},
        "bgm_mood": "tech",
    },
    "暗黑": {
        "effects": ["glow_outline", "character_card"],
        "params": {"bg_dark": True, "glow_intensity": "high", "card_style": "kuangbiao"},
        "bgm_mood": "dark",
    },
    "明亮": {
        "effects": ["subtitle_bar", "text_layout"],
        "params": {"bright": True, "warm_tone": True},
        "bgm_mood": "bright",
    },
    "vlog": {
        "effects": ["subtitle_bar", "date_badge", "polaroid_wall"],
        "params": {"subtitle_style": "pill_warm", "date_badge": True, "photo_wall": True},
        "bgm_mood": "vlog",
    },

    # === 节奏标签 ===
    "快切": {
        "cut_interval": 0.8,
        "transition": "闪白",
        "camera_move": "快推",
    },
    "卡点": {
        "cut_interval": "beat",
        "transition": "缩放",
        "beat_sync": True,
    },
    "慢节奏": {
        "cut_interval": 3.0,
        "transition": "模糊",
        "camera_move": "缓推",
    },
    "变速": {
        "speed_ramp": True,
        "transition": "缩放",
    },
    "鼓点": {
        "cut_interval": "beat",
        "transition": "闪白",
        "beat_sync": True,
        "impact_effect": "缩放冲击",
    },
    "舒缓": {
        "cut_interval": 4.0,
        "transition": "黑场",
        "camera_move": "缓拉",
    },

    # === 转场标签 ===
    "闪白": {"effect": "mask_flash_transition", "params": {"type": "flash_white", "duration": 0.15}},
    "划像": {"effect": "mask_flash_transition", "params": {"type": "wipe", "direction": "left"}},
    "缩放": {"effect": "camera_moves", "params": {"type": "zoom_in", "intensity": 0.3}},
    "旋转": {"effect": "camera_moves", "params": {"type": "rotate_cw", "intensity": 0.2}},
    "故障": {"effect": "mask_flash_transition", "params": {"type": "glitch", "duration": 0.2}},
    "模糊": {"effect": "camera_moves", "params": {"type": "fade_out", "duration": 0.3}},
    "黑场": {"effect": "camera_moves", "params": {"type": "fade_out", "duration": 0.5}},
    "百叶窗": {"effect": "blinds_transition", "params": {"direction": "horizontal"}},

    # === 文字标签 ===
    "大字报": {"effect": "text_layout", "params": {"style": "horizontal_title", "size": 18.0}},
    "打字机": {"effect": "text_ops", "params": {"anim_in": "打字机_I", "size": 12.0}},
    "弹幕": {"effect": "text_layout", "params": {"style": "left_align_stack", "multi_track": True}},
    "花字": {"effect": "artistic_subtitle", "params": {"gradient": True, "outline": True}},
    "描边": {"effect": "artistic_subtitle", "params": {"outline": True, "shadow": True}},
    "渐变": {"effect": "artistic_subtitle", "params": {"gradient": True}},
    "字幕条": {"effect": "subtitle_bar", "params": {"style": "pill"}},

    # === 特效标签 ===
    "发光": {"effect": "glow_outline", "params": {"intensity": "medium"}},
    "粒子": {"effect": "blender_particles", "params": {"preset": "stars"}},
    "光效": {"effect": "blender_light_sweep", "params": {}},
    "抖动": {"effect": "camera_moves", "params": {"type": "handheld", "intensity": 0.15}},
    "缩放冲击": {"effect": "camera_moves", "params": {"type": "zoom_in", "intensity": 0.4}},
    "分屏": {"effect": "pip_layouts", "params": {"layout": "left_right"}},
    "拍立得": {"effect": "polaroid_wall", "params": {}},
}

# 标签同义词映射（口语→标准标签）
TAG_SYNONYMS = {
    "赛博": "赛博朋克", "cyberpunk": "赛博朋克", "霓虹": "赛博朋克",
    "故障": "故障风", "glitch": "故障风", "花屏": "故障风",
    "复古风": "复古", "怀旧": "复古", "retro": "复古",
    "中国风": "水墨", "国风": "水墨",
    "简约": "极简", "干净": "极简", "minimal": "极简",
    "科技": "科技感", "未来感": "科技感", "tech": "科技感",
    "黑暗": "暗黑", "暗调": "暗黑", "dark": "暗黑",
    "清新": "明亮", "亮调": "明亮", "bright": "明亮",
    "日常": "vlog", "生活": "vlog",
    "快剪": "快切", "快速": "快切",
    "踩点": "卡点", "beat": "卡点",
    "慢": "慢节奏", "缓慢": "慢节奏",
    "节奏": "鼓点", "重拍": "鼓点",
    "舒服": "舒缓", "治愈": "舒缓",
    "大标题": "大字报", "标题": "大字报",
    "逐字": "打字机", "typewriter": "打字机",
    "滚动字幕": "弹幕",
    "艺术字": "花字",
    "边框字": "描边",
    "渐变色": "渐变",
    "字幕背景": "字幕条", "底条": "字幕条",
    "光晕": "发光", "辉光": "发光",
    "星空": "粒子", "雪花": "粒子",
    "扫光": "光效",
    "震屏": "抖动", "晃动": "抖动",
    "冲击": "缩放冲击", "放大冲击": "缩放冲击",
    "左右分屏": "分屏", "画中画": "分屏",
    "照片墙": "拍立得", "相册": "拍立得",
}


class TagEngine:
    """短视频标签引擎"""

    def __init__(self):
        self.tag_map = TAG_EFFECT_MAP
        self.synonyms = TAG_SYNONYMS

    def normalize_tags(self, raw_tags: List[str]) -> List[str]:
        """将口语标签转为标准标签"""
        normalized = []
        for tag in raw_tags:
            tag_lower = tag.strip().lower()
            # 直接匹配
            if tag in self.tag_map:
                normalized.append(tag)
            # 同义词匹配
            elif tag_lower in self.synonyms:
                normalized.append(self.synonyms[tag_lower])
            # 包含匹配
            else:
                for syn, std in self.synonyms.items():
                    if syn in tag_lower or tag_lower in syn:
                        normalized.append(std)
                        break
        # 去重保序
        seen = set()
        result = []
        for t in normalized:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result

    def match_effects(self, tags: List[str]) -> Dict[str, Any]:
        """
        根据标签匹配特效组合

        Returns:
            {
                "style": 风格标签,
                "rhythm": 节奏配置,
                "transition": 转场配置,
                "text": 文字配置,
                "effects": [特效列表],
                "bgm_mood": BGM情绪,
                "params": 合并参数,
            }
        """
        normalized = self.normalize_tags(tags)
        result = {
            "input_tags": tags,
            "normalized_tags": normalized,
            "style": None,
            "rhythm": {"cut_interval": 2.0, "transition": "闪白"},
            "transition": None,
            "text": None,
            "effects": [],
            "bgm_mood": "default",
            "params": {},
        }

        style_tags = ["赛博朋克", "故障风", "复古", "水墨", "极简", "科技感", "暗黑", "明亮", "vlog"]
        rhythm_tags = ["快切", "卡点", "慢节奏", "变速", "鼓点", "舒缓"]
        transition_tags = ["闪白", "划像", "缩放", "旋转", "故障", "模糊", "黑场", "百叶窗"]
        text_tags = ["大字报", "打字机", "弹幕", "花字", "描边", "渐变", "字幕条"]
        effect_tags = ["发光", "粒子", "光效", "抖动", "缩放冲击", "分屏", "拍立得"]

        for tag in normalized:
            cfg = self.tag_map.get(tag, {})
            if tag in style_tags:
                result["style"] = tag
                result["effects"].extend(cfg.get("effects", []))
                result["params"].update(cfg.get("params", {}))
                if "bgm_mood" in cfg:
                    result["bgm_mood"] = cfg["bgm_mood"]
            elif tag in rhythm_tags:
                result["rhythm"].update(cfg)
            elif tag in transition_tags:
                result["transition"] = cfg
            elif tag in text_tags:
                result["text"] = cfg
            elif tag in effect_tags:
                result["effects"].append(cfg.get("effect", tag))
                result["params"].update(cfg.get("params", {}))

        # 默认节奏
        if not result["transition"] and result["rhythm"].get("transition"):
            t_name = result["rhythm"]["transition"]
            result["transition"] = self.tag_map.get(t_name, {"effect": "mask_flash_transition"})

        # 去重特效
        result["effects"] = list(dict.fromkeys(result["effects"]))

        return result

    def generate_preset(self, tags: List[str], duration: float = 15.0) -> Dict[str, Any]:
        """
        生成完整的短视频预设配置

        Args:
            tags: 标签列表
            duration: 视频时长（秒）

        Returns:
            完整预设，可直接用于pipeline
        """
        matched = self.match_effects(tags)
        cut_interval = matched["rhythm"].get("cut_interval", 2.0)

        if cut_interval == "beat":
            num_cuts = int(duration / 0.5)  # 卡点模式假设0.5秒一拍
        else:
            num_cuts = max(1, int(duration / cut_interval))

        preset = {
            "tags": matched["normalized_tags"],
            "style": matched["style"],
            "duration": duration,
            "num_cuts": num_cuts,
            "cut_interval": cut_interval if cut_interval != "beat" else 0.5,
            "beat_sync": matched["rhythm"].get("beat_sync", False),
            "speed_ramp": matched["rhythm"].get("speed_ramp", False),
            "transition": matched["transition"],
            "text_style": matched["text"],
            "effects": matched["effects"],
            "bgm_mood": matched["bgm_mood"],
            "params": matched["params"],
            "camera_move": matched["rhythm"].get("camera_move", "缓推"),
        }
        return preset

    def list_all_tags(self) -> Dict[str, List[str]]:
        """列出所有可用标签"""
        return {
            "风格": ["赛博朋克", "故障风", "复古", "水墨", "极简", "科技感", "暗黑", "明亮", "vlog"],
            "节奏": ["快切", "卡点", "慢节奏", "变速", "鼓点", "舒缓"],
            "转场": ["闪白", "划像", "缩放", "旋转", "故障", "模糊", "黑场", "百叶窗"],
            "文字": ["大字报", "打字机", "弹幕", "花字", "描边", "渐变", "字幕条"],
            "特效": ["发光", "粒子", "光效", "抖动", "缩放冲击", "分屏", "拍立得"],
        }


if __name__ == "__main__":
    engine = TagEngine()

    print("=" * 60)
    print("短视频标签引擎 v1.0")
    print("=" * 60)

    # 测试1：赛博朋克+卡点
    print("\n[测试1] 标签: ['赛博朋克', '卡点', '发光', '大字报']")
    preset = engine.generate_preset(["赛博朋克", "卡点", "发光", "大字报"], 15)
    print(json.dumps(preset, ensure_ascii=False, indent=2))

    # 测试2：vlog+舒缓
    print("\n[测试2] 标签: ['vlog', '舒缓', '字幕条', '拍立得']")
    preset = engine.generate_preset(["vlog", "舒缓", "字幕条", "拍立得"], 30)
    print(json.dumps(preset, ensure_ascii=False, indent=2))

    # 测试3：口语标签
    print("\n[测试3] 口语标签: ['赛博', '踩点', '光晕', '大标题']")
    normalized = engine.normalize_tags(["赛博", "踩点", "光晕", "大标题"])
    print(f"标准化: {normalized}")

    # 列出所有标签
    print("\n[所有标签]")
    for category, tags in engine.list_all_tags().items():
        print(f"  {category}: {', '.join(tags)}")
