#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T3-2: 3D与空间视频集成层
封装 Blender 能力，提供 3D 特效预设和 API
"""
import os
import sys
import json
import time
import logging
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Blender skill 路径
BLENDER_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\blender-controls-skill\scripts"
if BLENDER_SKILL not in sys.path:
    sys.path.insert(0, BLENDER_SKILL)

# 输出目录
OUTPUT_DIR = r"C:\Users\Administrator\Videos\剪映导出\ai-video-editor\3d_effects"
os.makedirs(OUTPUT_DIR, exist_ok=True)


@dataclass
class EffectPreset:
    """3D特效预设"""
    preset_id: str
    name: str
    category: str  # intro/transition/effect/title
    description: str
    duration: float  # 秒
    complexity: str  # simple/medium/complex
    blender_script: str = ""  # Blender Python 脚本模板
    params: Dict[str, Any] = None


# 3D 特效预设库
EFFECT_PRESETS = {
    # ===== 片头特效 =====
    "logo_reveal": EffectPreset(
        preset_id="logo_reveal",
        name="3D Logo 揭示",
        category="intro",
        description="3D 立体 Logo 从黑暗中旋转揭示，带粒子效果",
        duration=3.0,
        complexity="medium",
        params={"logo_text": "LOGO", "color": "#4A90D9", "particles": 100},
    ),
    "cinematic_intro": EffectPreset(
        preset_id="cinematic_intro",
        name="电影感片头",
        category="intro",
        description="黑场渐入，3D 文字从远处推进，电影感画幅",
        duration=4.0,
        complexity="simple",
        params={"title": "标题", "subtitle": "副标题"},
    ),
    "particle_explosion": EffectPreset(
        preset_id="particle_explosion",
        name="粒子爆炸片头",
        category="intro",
        description="粒子从中心爆炸汇聚成文字",
        duration=3.5,
        complexity="complex",
        params={"text": "标题", "particle_count": 500},
    ),

    # ===== 转场特效 =====
    "cube_rotation": EffectPreset(
        preset_id="cube_rotation",
        name="3D 立方体旋转转场",
        category="transition",
        description="画面在 3D 立方体面上旋转切换",
        duration=1.5,
        complexity="medium",
        params={"direction": "left"},
    ),
    "page_flip_3d": EffectPreset(
        preset_id="page_flip_3d",
        name="3D 翻页转场",
        category="transition",
        description="画面像书页一样 3D 翻转",
        duration=1.2,
        complexity="medium",
        params={"direction": "right"},
    ),
    "door_open": EffectPreset(
        preset_id="door_open",
        name="3D 开门转场",
        category="transition",
        description="两扇 3D 门打开揭示新画面",
        duration=2.0,
        complexity="complex",
        params={},
    ),

    # ===== 特效 =====
    "floating_objects": EffectPreset(
        preset_id="floating_objects",
        name="漂浮物体特效",
        category="effect",
        description="3D 物体在空间中漂浮旋转",
        duration=5.0,
        complexity="medium",
        params={"object_type": "cube", "count": 10},
    ),
    "neon_grid": EffectPreset(
        preset_id="neon_grid",
        name="霓虹网格空间",
        category="effect",
        description="赛博朋克风格 3D 霓虹网格无限延伸",
        duration=6.0,
        complexity="complex",
        params={"color": "#00FFFF", "speed": 1.0},
    ),
    "depth_of_field": EffectPreset(
        preset_id="depth_of_field",
        name="景深空间效果",
        category="effect",
        description="3D 空间景深虚化，焦点切换",
        duration=4.0,
        complexity="medium",
        params={"focus_distance": 5.0},
    ),

    # ===== 文字特效 =====
    "3d_text_fly": EffectPreset(
        preset_id="3d_text_fly",
        name="3D 文字飞入",
        category="title",
        description="3D 立体文字从远处飞入画面",
        duration=2.5,
        complexity="simple",
        params={"text": "标题", "font_size": 2.0},
    ),
    "text_extrude": EffectPreset(
        preset_id="text_extrude",
        name="文字挤出动画",
        category="title",
        description="2D 文字逐渐挤出为 3D 立体",
        duration=3.0,
        complexity="medium",
        params={"text": "标题", "extrude_depth": 0.5},
    ),
}


class ThreeDEffectGenerator:
    """3D 特效生成器"""

    def __init__(self, blender_path: str = None, output_dir: str = None):
        self.blender_path = blender_path or self._find_blender()
        self.output_dir = output_dir or OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def _find_blender(self) -> str:
        """查找 Blender 可执行文件"""
        # 常见安装路径
        candidates = [
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
            r"D:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        # 尝试 PATH
        try:
            result = subprocess.run(["where", "blender"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split("\n")[0].strip()
        except Exception:
            pass
        return ""

    def is_available(self) -> bool:
        """检查 Blender 是否可用"""
        return bool(self.blender_path and os.path.exists(self.blender_path))

    def list_presets(self, category: str = None) -> List[Dict]:
        """列出可用特效预设"""
        result = []
        for preset in EFFECT_PRESETS.values():
            if category and preset.category != category:
                continue
            result.append(asdict(preset))
        return result

    def get_preset(self, preset_id: str) -> Optional[EffectPreset]:
        """获取指定预设"""
        return EFFECT_PRESETS.get(preset_id)

    def generate(self, preset_id: str, params: Dict = None,
                 output_path: str = None) -> Dict[str, Any]:
        """
        生成 3D 特效

        Args:
            preset_id: 预设ID
            params: 覆盖参数
            output_path: 输出路径

        Returns:
            生成结果
        """
        start_time = time.time()
        preset = self.get_preset(preset_id)
        if not preset:
            return {"success": False, "error": f"预设不存在: {preset_id}"}

        # 合并参数
        merged_params = {**preset.params, **(params or {})}

        if not output_path:
            output_path = os.path.join(
                self.output_dir, f"{preset_id}_{int(time.time())}.mp4"
            )

        logger.info(f"[3D特效] 生成: {preset.name} ({preset_id})")
        logger.info(f"  参数: {merged_params}")

        if not self.is_available():
            logger.warning("  Blender 未安装，返回预设配置（需手动渲染）")
            return {
                "success": False,
                "error": "Blender 未安装或未找到",
                "preset": asdict(preset),
                "params": merged_params,
                "output_path": output_path,
                "blender_path": self.blender_path,
            }

        # 生成 Blender 脚本
        script_path = self._generate_blender_script(preset, merged_params, output_path)

        # 执行 Blender
        try:
            cmd = [
                self.blender_path,
                "--background",
                "--python", script_path,
                "--render-anim",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if os.path.exists(output_path):
                duration = time.time() - start_time
                logger.info(f"  ✅ 生成成功: {os.path.basename(output_path)} ({duration:.1f}s)")
                return {
                    "success": True,
                    "preset": asdict(preset),
                    "params": merged_params,
                    "output_path": output_path,
                    "duration": round(duration, 1),
                }
            else:
                return {
                    "success": False,
                    "error": "渲染完成但输出文件不存在",
                    "stdout": result.stdout[-500:],
                    "stderr": result.stderr[-500:],
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "渲染超时（>600秒）"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_blender_script(self, preset: EffectPreset,
                                 params: Dict, output_path: str) -> str:
        """生成 Blender Python 脚本"""
        script = f"""
import bpy
import os

# 清除默认场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# 输出设置
bpy.context.scene.render.filepath = r"{output_path}"
bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
bpy.context.scene.render.ffmpeg.format = 'MPEG4'
bpy.context.scene.render.ffmpeg.codec = 'H264'
bpy.context.scene.frame_end = int({preset.duration} * 24)
bpy.context.scene.render.fps = 24

# 预设: {preset.name}
# 类别: {preset.category}
{self._get_preset_script(preset.preset_id, params)}

logger.info("渲染完成")
"""
        script_path = os.path.join(self.output_dir, f"{preset.preset_id}_script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        return script_path

    def _get_preset_script(self, preset_id: str, params: Dict) -> str:
        """获取预设的 Blender 脚本片段"""
        scripts = {
            "3d_text_fly": f"""
# 3D 文字飞入
text = "{params.get('text', '标题')}"
bpy.ops.object.text_add(location=(0, 0, 0))
text_obj = bpy.context.active_object
text_obj.data.body = text
text_obj.data.extrude = 0.1
text_obj.data.size = {params.get('font_size', 2.0)}

# 动画：从远处飞入
text_obj.location = (0, -10, 0)
text_obj.keyframe_insert(data_path="location", frame=1)
text_obj.location = (0, 0, 0)
text_obj.keyframe_insert(data_path="location", frame=48)

# 相机
bpy.ops.object.camera_add(location=(0, -5, 2))
bpy.context.scene.camera = bpy.context.active_object
""",
            "cinematic_intro": f"""
# 电影感片头
bpy.ops.object.text_add(location=(0, 0, 0))
text_obj = bpy.context.active_object
text_obj.data.body = "{params.get('title', '标题')}"
text_obj.data.size = 2.0

# 相机推进
bpy.ops.object.camera_add(location=(0, -15, 3))
camera = bpy.context.active_object
camera.location = (0, -15, 3)
camera.keyframe_insert(data_path="location", frame=1)
camera.location = (0, -5, 2)
camera.keyframe_insert(data_path="location", frame=72)
bpy.context.scene.camera = camera
""",
        }
        return scripts.get(preset_id, "# 预设脚本待实现\npass")


# 便捷函数
def list_3d_presets(category: str = None) -> List[Dict]:
    """列出 3D 特效预设"""
    return ThreeDEffectGenerator().list_presets(category)


def generate_3d_effect(preset_id: str, params: Dict = None) -> Dict:
    """生成 3D 特效"""
    return ThreeDEffectGenerator().generate(preset_id, params)


def check_blender_available() -> bool:
    """检查 Blender 是否可用"""
    return ThreeDEffectGenerator().is_available()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    logger.info("=== 3D特效预设库 ===")
    logger.info(f"Blender 可用: {check_blender_available()}")
    logger.info()

    categories = ["intro", "transition", "effect", "title"]
    for cat in categories:
        presets = list_3d_presets(cat)
        logger.info(f"【{cat.upper()}】({len(presets)}个)")
        for p in presets:
            logger.info(f"  - {p['name']} ({p['preset_id']}): {p['description']} [{p['duration']}s]")
        logger.info()
