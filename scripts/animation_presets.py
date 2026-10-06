"""
动画预设库 v1.0
建立常用动画预设，可复用于Remotion和剪映关键帧

包含：下落/弹起/震动/闪烁/委屈表情/旋转/缩放/滑动等常用动画

使用方式：
    from animation_presets import AnimationPresetLibrary
    lib = AnimationPresetLibrary()
    preset = lib.get_preset("fall")
    print(preset["keyframes"])  # 关键帧列表
    print(preset["duration"])   # 持续时长
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Keyframe:
    """关键帧"""
    frame: int  # 帧号
    property: str  # 属性名 position/scale/rotation/opacity
    value: float  # 属性值
    curve: str = "ease_out"  # 缓动曲线


@dataclass
class AnimationPreset:
    """动画预设"""
    name: str
    display_name: str
    category: str  # motion/emotion/effect
    description: str
    duration_frames: int  # 持续帧数
    keyframes: List[Keyframe] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)  # 可调参数


class AnimationPresetLibrary:
    """动画预设库"""

    def __init__(self):
        self.presets = self._build_presets()

    def _build_presets(self) -> Dict[str, AnimationPreset]:
        """构建所有动画预设"""
        presets = {}

        # ===== 运动类动画 =====
        presets["fall"] = AnimationPreset(
            name="fall",
            display_name="下落",
            category="motion",
            description="从上方下落到目标位置，带重力加速效果",
            duration_frames=30,
            parameters={"start_y": -500, "end_y": 0, "bounce": True},
            keyframes=[
                Keyframe(0, "position_y", -500, "ease_in"),
                Keyframe(20, "position_y", 50, "ease_out"),
                Keyframe(25, "position_y", -20, "ease_out"),
                Keyframe(30, "position_y", 0, "ease_out"),
            ],
        )

        presets["bounce_up"] = AnimationPreset(
            name="bounce_up",
            display_name="弹起",
            category="motion",
            description="从下方弹起，带弹性效果",
            duration_frames=25,
            parameters={"start_y": 500, "end_y": 0, "bounce_height": 100},
            keyframes=[
                Keyframe(0, "position_y", 500, "ease_out"),
                Keyframe(15, "position_y", -80, "ease_in"),
                Keyframe(20, "position_y", 30, "ease_out"),
                Keyframe(25, "position_y", 0, "ease_out"),
            ],
        )

        presets["shake"] = AnimationPreset(
            name="shake",
            display_name="震动",
            category="motion",
            description="左右/上下快速震动，振幅逐渐衰减",
            duration_frames=20,
            parameters={"amplitude": 20, "frequency": 4, "decay": 0.8},
            keyframes=[
                Keyframe(0, "position_x", 0, "linear"),
                Keyframe(2, "position_x", -20, "linear"),
                Keyframe(4, "position_x", 18, "linear"),
                Keyframe(6, "position_x", -15, "linear"),
                Keyframe(8, "position_x", 12, "linear"),
                Keyframe(10, "position_x", -10, "linear"),
                Keyframe(12, "position_x", 8, "linear"),
                Keyframe(14, "position_x", -5, "linear"),
                Keyframe(16, "position_x", 3, "linear"),
                Keyframe(20, "position_x", 0, "linear"),
            ],
        )

        presets["slide_in_left"] = AnimationPreset(
            name="slide_in_left",
            display_name="左滑入",
            category="motion",
            description="从左侧滑入画面",
            duration_frames=20,
            parameters={"distance": 500},
            keyframes=[
                Keyframe(0, "position_x", -500, "ease_out"),
                Keyframe(20, "position_x", 0, "ease_out"),
            ],
        )

        presets["slide_in_right"] = AnimationPreset(
            name="slide_in_right",
            display_name="右滑入",
            category="motion",
            description="从右侧滑入画面",
            duration_frames=20,
            parameters={"distance": 500},
            keyframes=[
                Keyframe(0, "position_x", 500, "ease_out"),
                Keyframe(20, "position_x", 0, "ease_out"),
            ],
        )

        presets["slide_in_top"] = AnimationPreset(
            name="slide_in_top",
            display_name="上滑入",
            category="motion",
            description="从上方滑入画面",
            duration_frames=20,
            parameters={"distance": 500},
            keyframes=[
                Keyframe(0, "position_y", -500, "ease_out"),
                Keyframe(20, "position_y", 0, "ease_out"),
            ],
        )

        presets["slide_in_bottom"] = AnimationPreset(
            name="slide_in_bottom",
            display_name="下滑入",
            category="motion",
            description="从下方滑入画面",
            duration_frames=20,
            parameters={"distance": 500},
            keyframes=[
                Keyframe(0, "position_y", 500, "ease_out"),
                Keyframe(20, "position_y", 0, "ease_out"),
            ],
        )

        presets["zoom_in"] = AnimationPreset(
            name="zoom_in",
            display_name="放大进入",
            category="motion",
            description="从小到大放大进入",
            duration_frames=20,
            parameters={"start_scale": 0, "end_scale": 1},
            keyframes=[
                Keyframe(0, "scale", 0, "ease_out"),
                Keyframe(15, "scale", 1.1, "ease_out"),
                Keyframe(20, "scale", 1, "ease_out"),
            ],
        )

        presets["zoom_out"] = AnimationPreset(
            name="zoom_out",
            display_name="缩小退出",
            category="motion",
            description="从大到小缩小退出",
            duration_frames=15,
            parameters={"start_scale": 1, "end_scale": 0},
            keyframes=[
                Keyframe(0, "scale", 1, "ease_in"),
                Keyframe(15, "scale", 0, "ease_in"),
            ],
        )

        presets["rotate_in"] = AnimationPreset(
            name="rotate_in",
            display_name="旋转进入",
            category="motion",
            description="旋转着进入画面",
            duration_frames=25,
            parameters={"start_rotation": -180, "end_rotation": 0},
            keyframes=[
                Keyframe(0, "rotation", -180, "ease_out"),
                Keyframe(0, "scale", 0, "ease_out"),
                Keyframe(25, "rotation", 0, "ease_out"),
                Keyframe(25, "scale", 1, "ease_out"),
            ],
        )

        # ===== 情绪类动画 =====
        presets["grievance"] = AnimationPreset(
            name="grievance",
            display_name="委屈",
            category="emotion",
            description="委屈表情：轻微颤抖+低头+缓慢缩放",
            duration_frames=60,
            parameters={"tremble_amount": 3, "head_tilt": -5},
            keyframes=[
                Keyframe(0, "position_y", 0, "linear"),
                Keyframe(10, "position_y", 5, "linear"),
                Keyframe(20, "position_y", 3, "linear"),
                Keyframe(30, "position_y", 8, "linear"),
                Keyframe(40, "position_y", 5, "linear"),
                Keyframe(50, "position_y", 10, "linear"),
                Keyframe(60, "position_y", 8, "linear"),
                Keyframe(0, "rotation", 0, "linear"),
                Keyframe(60, "rotation", -3, "linear"),
                Keyframe(0, "scale", 1, "linear"),
                Keyframe(60, "scale", 0.95, "ease_out"),
            ],
        )

        presets["angry"] = AnimationPreset(
            name="angry",
            display_name="愤怒",
            category="emotion",
            description="愤怒表情：剧烈震动+放大+红色闪烁",
            duration_frames=30,
            parameters={"shake_amount": 15, "scale_peak": 1.2},
            keyframes=[
                Keyframe(0, "position_x", 0, "linear"),
                Keyframe(3, "position_x", -15, "linear"),
                Keyframe(6, "position_x", 12, "linear"),
                Keyframe(9, "position_x", -10, "linear"),
                Keyframe(12, "position_x", 8, "linear"),
                Keyframe(15, "position_x", -5, "linear"),
                Keyframe(20, "position_x", 0, "linear"),
                Keyframe(0, "scale", 1, "ease_out"),
                Keyframe(10, "scale", 1.2, "ease_out"),
                Keyframe(30, "scale", 1.1, "ease_out"),
            ],
        )

        presets["happy"] = AnimationPreset(
            name="happy",
            display_name="开心",
            category="emotion",
            description="开心表情：弹跳+轻微旋转+缩放",
            duration_frames=40,
            parameters={"bounce_height": 30, "rotation_range": 5},
            keyframes=[
                Keyframe(0, "position_y", 0, "ease_out"),
                Keyframe(10, "position_y", -30, "ease_in"),
                Keyframe(20, "position_y", 0, "ease_out"),
                Keyframe(30, "position_y", -15, "ease_in"),
                Keyframe(40, "position_y", 0, "ease_out"),
                Keyframe(0, "scale", 1, "linear"),
                Keyframe(10, "scale", 1.1, "linear"),
                Keyframe(20, "scale", 1, "linear"),
                Keyframe(30, "scale", 1.05, "linear"),
                Keyframe(40, "scale", 1, "linear"),
            ],
        )

        presets["surprised"] = AnimationPreset(
            name="surprised",
            display_name="惊喜",
            category="emotion",
            description="惊喜表情：快速放大+定格+轻微震动",
            duration_frames=25,
            parameters={"scale_peak": 1.3, "freeze_frames": 5},
            keyframes=[
                Keyframe(0, "scale", 1, "ease_out"),
                Keyframe(5, "scale", 1.3, "ease_out"),
                Keyframe(10, "scale", 1.25, "linear"),
                Keyframe(15, "scale", 1.2, "linear"),
                Keyframe(25, "scale", 1.15, "ease_out"),
                Keyframe(0, "position_x", 0, "linear"),
                Keyframe(5, "position_x", -5, "linear"),
                Keyframe(8, "position_x", 5, "linear"),
                Keyframe(11, "position_x", -3, "linear"),
                Keyframe(15, "position_x", 0, "linear"),
            ],
        )

        presets["sad"] = AnimationPreset(
            name="sad",
            display_name="难过",
            category="emotion",
            description="难过表情：缓慢下沉+缩小+透明度降低",
            duration_frames=50,
            parameters={"sink_amount": 30, "opacity_end": 0.7},
            keyframes=[
                Keyframe(0, "position_y", 0, "ease_in"),
                Keyframe(50, "position_y", 30, "ease_in"),
                Keyframe(0, "scale", 1, "ease_in"),
                Keyframe(50, "scale", 0.9, "ease_in"),
                Keyframe(0, "opacity", 1, "linear"),
                Keyframe(50, "opacity", 0.7, "linear"),
            ],
        )

        # ===== 特效类动画 =====
        presets["flash"] = AnimationPreset(
            name="flash",
            display_name="闪烁",
            category="effect",
            description="快速闪烁：透明度快速变化",
            duration_frames=10,
            parameters={"flash_count": 3},
            keyframes=[
                Keyframe(0, "opacity", 1, "linear"),
                Keyframe(2, "opacity", 0, "linear"),
                Keyframe(4, "opacity", 1, "linear"),
                Keyframe(6, "opacity", 0, "linear"),
                Keyframe(8, "opacity", 1, "linear"),
                Keyframe(10, "opacity", 1, "linear"),
            ],
        )

        presets["pulse"] = AnimationPreset(
            name="pulse",
            display_name="脉冲",
            category="effect",
            description="脉冲效果：缩放周期性变化",
            duration_frames=30,
            parameters={"pulse_scale": 1.1, "frequency": 2},
            keyframes=[
                Keyframe(0, "scale", 1, "ease_in_out"),
                Keyframe(7, "scale", 1.1, "ease_in_out"),
                Keyframe(15, "scale", 1, "ease_in_out"),
                Keyframe(22, "scale", 1.1, "ease_in_out"),
                Keyframe(30, "scale", 1, "ease_in_out"),
            ],
        )

        presets["fade_in"] = AnimationPreset(
            name="fade_in",
            display_name="淡入",
            category="effect",
            description="淡入效果：透明度从0到1",
            duration_frames=15,
            parameters={},
            keyframes=[
                Keyframe(0, "opacity", 0, "ease_out"),
                Keyframe(15, "opacity", 1, "ease_out"),
            ],
        )

        presets["fade_out"] = AnimationPreset(
            name="fade_out",
            display_name="淡出",
            category="effect",
            description="淡出效果：透明度从1到0",
            duration_frames=15,
            parameters={},
            keyframes=[
                Keyframe(0, "opacity", 1, "ease_in"),
                Keyframe(15, "opacity", 0, "ease_in"),
            ],
        )

        presets["glitch"] = AnimationPreset(
            name="glitch",
            display_name="故障风",
            category="effect",
            description="故障效果：位置偏移+颜色分离",
            duration_frames=20,
            parameters={"offset_amount": 10},
            keyframes=[
                Keyframe(0, "position_x", 0, "linear"),
                Keyframe(3, "position_x", -10, "linear"),
                Keyframe(5, "position_x", 8, "linear"),
                Keyframe(7, "position_x", -5, "linear"),
                Keyframe(10, "position_x", 10, "linear"),
                Keyframe(12, "position_x", -8, "linear"),
                Keyframe(15, "position_x", 5, "linear"),
                Keyframe(20, "position_x", 0, "linear"),
            ],
        )

        return presets

    def get_preset(self, name: str) -> Optional[AnimationPreset]:
        """获取动画预设"""
        return self.presets.get(name)

    def list_presets(self, category: str = None) -> List[Dict]:
        """列出所有预设"""
        result = []
        for name, preset in self.presets.items():
            if category and preset.category != category:
                continue
            result.append({
                "name": name,
                "display_name": preset.display_name,
                "category": preset.category,
                "description": preset.description,
                "duration_frames": preset.duration_frames,
                "keyframe_count": len(preset.keyframes),
            })
        return result

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return list(set(p.category for p in self.presets.values()))

    def generate_remotion_config(self, name: str, fps: int = 30) -> Optional[Dict]:
        """生成Remotion配置格式"""
        preset = self.get_preset(name)
        if not preset:
            return None

        # 按属性分组关键帧
        properties = {}
        for kf in preset.keyframes:
            if kf.property not in properties:
                properties[kf.property] = []
            properties[kf.property].append({
                "frame": kf.frame,
                "value": kf.value,
                "curve": kf.curve,
            })

        return {
            "name": preset.name,
            "display_name": preset.display_name,
            "duration_in_frames": preset.duration_frames,
            "duration_in_seconds": round(preset.duration_frames / fps, 2),
            "properties": properties,
            "parameters": preset.parameters,
        }

    def generate_jianying_keyframes(
        self,
        name: str,
        start_time_us: int = 0,
        fps: int = 30,
    ) -> Optional[List[Dict]]:
        """生成剪映关键帧格式"""
        preset = self.get_preset(name)
        if not preset:
            return None

        keyframes = []
        frame_duration_us = int(1_000_000 / fps)

        # 按属性分组
        prop_groups = {}
        for kf in preset.keyframes:
            if kf.property not in prop_groups:
                prop_groups[kf.property] = []
            prop_groups[kf.property].append(kf)

        # 剪映属性映射
        property_map = {
            "position_x": "transform_x",
            "position_y": "transform_y",
            "scale": "uniform_scale",
            "rotation": "rotation",
            "opacity": "opacity",
        }

        for prop, kfs in prop_groups.items():
            jianying_prop = property_map.get(prop, prop)
            for kf in kfs:
                time_offset = start_time_us + kf.frame * frame_duration_us
                keyframes.append({
                    "property": jianying_prop,
                    "time_offset": time_offset,
                    "value": kf.value,
                    "curve": kf.curve,
                })

        return keyframes

    def search_presets(self, keyword: str) -> List[Dict]:
        """搜索预设"""
        keyword = keyword.lower()
        results = []
        for preset_info in self.list_presets():
            if (keyword in preset_info["name"].lower() or
                keyword in preset_info["display_name"].lower() or
                keyword in preset_info["description"].lower()):
                results.append(preset_info)
        return results


def main():
    """命令行测试"""
    lib = AnimationPresetLibrary()

    print("=" * 60)
    print("动画预设库 v1.0")
    print("=" * 60)

    print(f"\n预设总数: {len(lib.presets)}")
    print(f"分类: {lib.get_categories()}")

    print("\n=== 运动类动画 ===")
    for p in lib.list_presets("motion"):
        print(f"  {p['name']:20s} {p['display_name']:8s} {p['duration_frames']}帧 {p['keyframe_count']}关键帧")

    print("\n=== 情绪类动画 ===")
    for p in lib.list_presets("emotion"):
        print(f"  {p['name']:20s} {p['display_name']:8s} {p['duration_frames']}帧 {p['keyframe_count']}关键帧")

    print("\n=== 特效类动画 ===")
    for p in lib.list_presets("effect"):
        print(f"  {p['name']:20s} {p['display_name']:8s} {p['duration_frames']}帧 {p['keyframe_count']}关键帧")

    print("\n=== 测试：生成Remotion配置（下落动画）===")
    config = lib.generate_remotion_config("fall")
    if config:
        print(f"  名称: {config['display_name']}")
        print(f"  时长: {config['duration_in_seconds']}秒")
        print(f"  属性: {list(config['properties'].keys())}")

    print("\n=== 测试：生成剪映关键帧（震动动画）===")
    keyframes = lib.generate_jianying_keyframes("shake", start_time_us=1_000_000)
    if keyframes:
        print(f"  关键帧数: {len(keyframes)}")
        print(f"  前3个: {keyframes[:3]}")

    print("\n=== 测试：搜索'弹' ===")
    results = lib.search_presets("弹")
    for r in results:
        print(f"  {r['name']}: {r['description']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
