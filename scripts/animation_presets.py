# -*- coding: utf-8 -*-
"""
动画预设库 v1.0
统一管理各类动画预设，包括：
- 角色动画（豆包被打、表情切换等）
- UI动画（按钮点击、页面切换等）
- 文字动画（淡入、滑入、弹入、打字机、渐变）
- 转场特效（淡入淡出、滑动、缩放、擦除）
- 冲击特效（拳击、爆炸、震动）

使用方式：
    from animation_presets import AnimationPresetLibrary
    lib = AnimationPresetLibrary()
    presets = lib.list_presets(category="text")
    preset = lib.get_preset("text_fade")
    config = lib.get_config("text_fade", text="你好", duration=3.0)
"""

import logging
logger = logging.getLogger(__name__)

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class AnimationPreset:
    """动画预设"""
    id: str                          # 预设ID
    name: str                        # 预设名称
    category: str                    # 分类：character/ui/text/transition/impact
    description: str                 # 描述
    duration: float = 3.0            # 默认时长（秒）
    params: Dict = field(default_factory=dict)  # 默认参数
    required_params: List[str] = field(default_factory=list)  # 必填参数
    engine: str = "jianying"         # 执行引擎：jianying/remotion/comfyui
    version: str = "1.0"             # 版本


class AnimationPresetLibrary:
    """动画预设库"""

    def __init__(self):
        self.presets: Dict[str, AnimationPreset] = {}
        self._init_builtin_presets()

    def _init_builtin_presets(self):
        """初始化内置预设"""

        # ===== 文字动画 =====
        self._add(AnimationPreset(
            id="text_fade",
            name="淡入淡出",
            category="text",
            description="文字淡入显示，停留后淡出",
            duration=3.0,
            params={"fade_in": 0.5, "fade_out": 0.5, "font_size": 60, "color": "#FFFFFF"},
            required_params=["text"],
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="text_slide",
            name="滑入滑出",
            category="text",
            description="文字从指定方向滑入，反向滑出",
            duration=3.0,
            params={"direction": "left", "distance": 0.3, "font_size": 60, "color": "#FFFFFF"},
            required_params=["text"],
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="text_bounce",
            name="弹性弹入",
            category="text",
            description="文字弹性缩放弹入",
            duration=2.0,
            params={"bounce_scale": 1.3, "font_size": 60, "color": "#FFFFFF"},
            required_params=["text"],
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="text_typewriter",
            name="打字机效果",
            category="text",
            description="逐字显现打字机效果，带光标闪烁",
            duration=4.0,
            params={"chars_per_second": 8, "cursor_blink": True, "font_size": 60, "color": "#FFFFFF"},
            required_params=["text"],
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="text_gradient",
            name="渐变流光",
            category="text",
            description="颜色流动渐变效果",
            duration=3.0,
            params={"colors": ["#FF6B6B", "#4ECDC4", "#45B7D1"], "font_size": 60},
            required_params=["text"],
            engine="jianying",
        ))

        # ===== 转场特效 =====
        self._add(AnimationPreset(
            id="transition_fade",
            name="淡入淡出转场",
            category="transition",
            description="两段素材之间淡入淡出过渡",
            duration=1.0,
            params={"direction": "inOut"},
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="transition_slide",
            name="滑动转场",
            category="transition",
            description="新画面从指定方向滑入覆盖旧画面",
            duration=1.0,
            params={"direction": "left"},
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="transition_zoom",
            name="缩放转场",
            category="transition",
            description="推近或拉远的缩放过渡",
            duration=1.0,
            params={"direction": "in", "scale": 1.2},
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="transition_wipe",
            name="擦除转场",
            category="transition",
            description="新画面从边缘擦除展开",
            duration=1.0,
            params={"direction": "left", "feather": 0.05},
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="transition_glitch",
            name="故障风转场",
            category="transition",
            description="RGB分离+扫描线故障效果",
            duration=0.5,
            params={"intensity": 0.5, "scanlines": True},
            engine="remotion",
        ))

        # ===== 冲击特效 =====
        self._add(AnimationPreset(
            id="impact_punch",
            name="拳击冲击",
            category="impact",
            description="冲击波+星星+白闪的拳击效果",
            duration=0.5,
            params={"scale": 1.2, "stars": 8, "flash": True},
            engine="remotion",
        ))
        self._add(AnimationPreset(
            id="impact_flash",
            name="冲击闪光",
            category="impact",
            description="快速白闪效果",
            duration=0.3,
            params={"intensity": 1.0, "fade_out": 0.2},
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="impact_shake",
            name="画面震动",
            category="impact",
            description="振幅衰减的随机震动",
            duration=0.5,
            params={"amplitude": 0.05, "decay": 0.9, "frequency": 20},
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="impact_particles",
            name="粒子爆发",
            category="impact",
            description="星星/火花/碎片粒子爆发",
            duration=1.0,
            params={"count": 16, "particle_type": "star", "spread": 0.5},
            engine="remotion",
        ))
        self._add(AnimationPreset(
            id="impact_shockwave",
            name="冲击波扩散",
            category="impact",
            description="多环冲击波向外扩散",
            duration=1.0,
            params={"rings": 3, "max_scale": 2.0, "color": "#FFFFFF"},
            engine="remotion",
        ))

        # ===== UI动画 =====
        self._add(AnimationPreset(
            id="ui_button_click",
            name="按钮点击",
            category="ui",
            description="按钮按下缩放反馈",
            duration=0.3,
            params={"press_scale": 0.95, "release_scale": 1.05},
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="ui_page_switch",
            name="页面切换",
            category="ui",
            description="页面滑动切换效果",
            duration=0.5,
            params={"direction": "left", "ease": "ease_in_out"},
            engine="jianying",
        ))
        self._add(AnimationPreset(
            id="ui_loading",
            name="加载动画",
            category="ui",
            description="旋转加载指示器",
            duration=2.0,
            params={"speed": 1.0, "color": "#00CED1"},
            engine="remotion",
        ))

        # ===== 角色动画 =====
        self._add(AnimationPreset(
            id="char_idle",
            name="角色待机",
            category="character",
            description="角色轻微呼吸浮动",
            duration=3.0,
            params={"breath_scale": 1.02, "float_amplitude": 0.01},
            engine="remotion",
        ))
        self._add(AnimationPreset(
            id="char_fall",
            name="角色掉落",
            category="character",
            description="角色从上方掉落并弹跳",
            duration=1.5,
            params={"fall_distance": 0.8, "bounce": True, "bounce_count": 2},
            engine="remotion",
        ))
        self._add(AnimationPreset(
            id="char_hit",
            name="角色被打",
            category="character",
            description="角色受击后退+震动+闪白",
            duration=0.8,
            params={"knockback": 0.2, "shake": True, "flash": True},
            engine="remotion",
        ))
        self._add(AnimationPreset(
            id="char_crawl_back",
            name="角色爬回",
            category="character",
            description="角色从画面底部爬回原位",
            duration=2.0,
            params={"crawl_speed": 0.5, "struggle": True},
            engine="remotion",
        ))

    def _add(self, preset: AnimationPreset):
        """添加预设"""
        self.presets[preset.id] = preset

    def list_presets(self, category: Optional[str] = None,
                     engine: Optional[str] = None) -> List[Dict]:
        """列出预设

        Args:
            category: 按分类筛选
            engine: 按引擎筛选

        Returns:
            预设列表
        """
        result = []
        for p in self.presets.values():
            if category and p.category != category:
                continue
            if engine and p.engine != engine:
                continue
            result.append({
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "description": p.description,
                "duration": p.duration,
                "engine": p.engine,
                "version": p.version,
            })
        return result

    def get_preset(self, preset_id: str) -> Optional[AnimationPreset]:
        """获取预设"""
        return self.presets.get(preset_id)

    def get_config(self, preset_id: str, **kwargs) -> Optional[Dict]:
        """获取预设配置（合并用户参数）

        Args:
            preset_id: 预设ID
            **kwargs: 用户参数覆盖

        Returns:
            完整配置字典
        """
        preset = self.presets.get(preset_id)
        if not preset:
            return None

        # 检查必填参数
        for req in preset.required_params:
            if req not in kwargs:
                logger.info(f"⚠️ 预设 {preset_id} 缺少必填参数: {req}")

        config = {
            "id": preset.id,
            "name": preset.name,
            "category": preset.category,
            "engine": preset.engine,
            "duration": kwargs.get("duration", preset.duration),
            "params": {**preset.params, **{k: v for k, v in kwargs.items()
                                            if k not in ["duration"]}},
        }
        return config

    def list_categories(self) -> Dict[str, int]:
        """列出分类及预设数量"""
        categories = {}
        for p in self.presets.values():
            categories[p.category] = categories.get(p.category, 0) + 1
        return categories

    def export_to_json(self, output_path: str) -> str:
        """导出预设库为JSON"""
        data = {
            "version": "1.0",
            "total": len(self.presets),
            "categories": self.list_categories(),
            "presets": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "description": p.description,
                    "duration": p.duration,
                    "params": p.params,
                    "required_params": p.required_params,
                    "engine": p.engine,
                    "version": p.version,
                }
                for p in self.presets.values()
            ],
        }
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path


def main():
    """命令行测试"""
    logger.info("=" * 60)
    logger.info("动画预设库 v1.0")
    logger.info("=" * 60)

    lib = AnimationPresetLibrary()

    logger.info(f"\n预设总数: {len(lib.presets)}")
    logger.info(f"\n分类统计:")
    for cat, count in lib.list_categories().items():
        logger.info(f"  {cat}: {count}个")

    logger.info(f"\n文字动画预设:")
    for p in lib.list_presets(category="text"):
        logger.info(f"  - {p['id']}: {p['name']} ({p['duration']}s)")

    logger.info(f"\n转场预设:")
    for p in lib.list_presets(category="transition"):
        logger.info(f"  - {p['id']}: {p['name']} ({p['duration']}s)")

    logger.info(f"\n冲击特效预设:")
    for p in lib.list_presets(category="impact"):
        logger.info(f"  - {p['id']}: {p['name']} ({p['duration']}s)")

    logger.info(f"\n测试配置生成:")
    config = lib.get_config("text_fade", text="你好世界", duration=5.0)
    logger.info(f"  {json.dumps(config, ensure_ascii=False, indent=2)[:200]}...")

    logger.info("\n✅ 动画预设库验证通过")


if __name__ == "__main__":
    main()
