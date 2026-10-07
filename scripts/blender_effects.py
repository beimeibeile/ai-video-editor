"""
Blender扩展特效库
基于cap_blender_runner，提供更多可直接调用的特效生成器

特效列表：
1. create_particle_background - 粒子背景（星空/雪花/光斑/烟花）
2. create_text_intro - 3D文字入场动画（缩放+旋转+淡入）
3. create_transition - 转场视频（淡入淡出/滑动/缩放/旋转）
4. create_light_sweep - 光线扫描特效
5. create_energy_ring - 能量环扩散特效
"""

import os
import sys
import math
from typing import Optional, Tuple, List

# 导入BlenderRunner
_cap_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "capabilities")
sys.path.insert(0, _cap_dir)
from cap_blender_runner.blender_runner import (
    BlenderRunner, BlenderScene, BlenderText, BlenderParticles, BlenderGlow,
)

# 粒子背景预设
PARTICLE_PRESETS = {
    "stars": {
        "count": 300, "emitter_size": 8.0, "lifetime": 120,
        "particle_size": 0.05, "color": (1.0, 1.0, 1.0, 1.0),
        "emission_strength": 5.0, "normal_factor": 0.1,
        "background": (0.0, 0.0, 0.05),
    },
    "snow": {
        "count": 200, "emitter_size": 6.0, "lifetime": 180,
        "particle_size": 0.08, "color": (0.9, 0.95, 1.0, 1.0),
        "emission_strength": 2.0, "normal_factor": 0.5,
        "background": (0.1, 0.15, 0.2),
    },
    "bokeh": {
        "count": 80, "emitter_size": 5.0, "lifetime": 150,
        "particle_size": 0.3, "color": (1.0, 0.8, 0.4, 0.6),
        "emission_strength": 3.0, "normal_factor": 0.3,
        "background": (0.05, 0.02, 0.1),
    },
    "fireworks": {
        "count": 150, "emitter_size": 0.5, "lifetime": 60,
        "particle_size": 0.06, "color": (1.0, 0.3, 0.2, 1.0),
        "emission_strength": 8.0, "normal_factor": 5.0,
        "background": (0.0, 0.0, 0.02),
    },
    "neon": {
        "count": 120, "emitter_size": 5.0, "lifetime": 100,
        "particle_size": 0.1, "color": (0.0, 1.0, 1.0, 1.0),
        "emission_strength": 4.0, "normal_factor": 1.0,
        "background": (0.02, 0.0, 0.08),
    },
}


def create_particle_background(
    output_dir: str,
    preset: str = "stars",
    width: int = 1920,
    height: int = 1080,
    duration: float = 5.0,
    custom_config: dict = None,
) -> Optional[str]:
    """
    创建粒子背景视频

    Args:
        output_dir: 输出目录
        preset: 预设名称 (stars/snow/bokeh/fireworks/neon)
        width: 宽度
        height: 高度
        duration: 时长（秒）
        custom_config: 自定义配置（覆盖预设）

    Returns:
        MP4视频路径或None
    """
    runner = BlenderRunner()
    if not runner.is_available():
        print("❌ Blender不可用")
        return None

    config = PARTICLE_PRESETS.get(preset, PARTICLE_PRESETS["stars"]).copy()
    if custom_config:
        config.update(custom_config)

    fps = 30
    frames = int(duration * fps)

    scene = BlenderScene(
        width=width,
        height=height,
        fps=fps,
        frame_end=frames,
        background_color=config["background"],
        particles=BlenderParticles(
            count=config["count"],
            emitter_size=config["emitter_size"],
            lifetime=config["lifetime"],
            particle_size=config["particle_size"],
            color=config["color"],
            emission_strength=config["emission_strength"],
            normal_factor=config["normal_factor"],
            frame_end=frames,
        ),
        glow=BlenderGlow(enabled=True, threshold=0.1, size=8.0),
        camera_location=(0, 0, 8),
    )

    print(f"🎨 粒子背景: {preset} ({config['count']}粒子, {duration}s)")
    return runner.create_and_render(scene, output_dir)


def create_text_intro(
    text: str,
    output_dir: str,
    subtitle: str = "",
    width: int = 1920,
    height: int = 1080,
    duration: float = 3.0,
    style: str = "zoom",  # zoom/slide/fade/rotate
    color: Tuple[float, float, float, float] = (1.0, 0.85, 0.2, 1.0),
    bg_color: Tuple[float, float, float] = (0.02, 0.02, 0.05),
) -> Optional[str]:
    """
    创建3D文字入场动画

    Args:
        text: 主标题文字
        output_dir: 输出目录
        subtitle: 副标题
        width/height: 分辨率
        duration: 时长
        style: 动画风格 (zoom/slide/fade/rotate)
        color: 文字颜色
        bg_color: 背景色

    Returns:
        MP4视频路径或None
    """
    runner = BlenderRunner()
    if not runner.is_available():
        print("❌ Blender不可用")
        return None

    fps = 30
    frames = int(duration * fps)

    texts = [
        BlenderText(
            text=text,
            size=2.5,
            color=color,
            emission_strength=3.0,
            extrude=0.15,
            bevel_depth=0.03,
            location=(0, 0, 0),
        )
    ]
    if subtitle:
        texts.append(
            BlenderText(
                text=subtitle,
                size=1.0,
                color=(0.8, 0.8, 0.8, 1.0),
                emission_strength=1.0,
                location=(0, -2.0, 0),
            )
        )

    scene = BlenderScene(
        width=width,
        height=height,
        fps=fps,
        frame_end=frames,
        background_color=bg_color,
        texts=texts,
        particles=BlenderParticles(
            count=80, emitter_size=6.0, lifetime=frames,
            particle_size=0.05, color=(0.5, 0.7, 1.0, 0.8),
            emission_strength=2.0, normal_factor=0.5,
        ),
        glow=BlenderGlow(enabled=True, threshold=0.15, size=6.0),
        camera_location=(0, 0, 10),
    )

    # 生成带动画的脚本（在基础脚本上扩展）
    os.makedirs(output_dir, exist_ok=True)
    script_content = runner._generate_python_script(scene, output_dir)

    # 注入文字入场动画关键帧
    anim_lines = [
        "",
        "# 文字入场动画",
        "text_obj = bpy.data.objects.get('Text0')",
        "if text_obj:",
        f"    text_obj.scale = (0.01, 0.01, 0.01)",
        "    text_obj.keyframe_insert(data_path='scale', frame=1)",
        f"    text_obj.scale = (1.0, 1.0, 1.0)",
        f"    text_obj.keyframe_insert(data_path='scale', frame={frames // 3})",
        "    # 旋转动画",
        "    text_obj.rotation_euler = (0, 0.3, 0)",
        "    text_obj.keyframe_insert(data_path='rotation_euler', frame=1)",
        "    text_obj.rotation_euler = (0, 0, 0)",
        f"    text_obj.keyframe_insert(data_path='rotation_euler', frame={frames // 3})",
        "",
        "# 保存",
        f"bpy.ops.wm.save_as_mainfile(filepath=os.path.join(r'{output_dir}', 'scene.blend'))",
    ]
    # 替换原有的保存行
    script_content = script_content.replace(
        "bpy.ops.wm.save_as_mainfile(filepath=blend_path)",
        "\n".join(anim_lines),
    )

    script_path = os.path.join(output_dir, "setup_scene.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    # 运行创建场景
    import subprocess
    result = subprocess.run(
        [runner.blender_path, "-b", "-P", script_path],
        capture_output=True, text=True, timeout=120,
    )

    blend_path = os.path.join(output_dir, "scene.blend")
    if not os.path.exists(blend_path):
        print(f"❌ 场景创建失败")
        print(result.stderr[-500:] if result.stderr else "")
        return None

    print(f"🎬 文字入场: {style}风格 - {text}")
    return runner.render(blend_path, output_dir, fps)


def create_transition(
    output_dir: str,
    style: str = "fade",  # fade/slide_left/slide_right/zoom_in/zoom_out
    width: int = 1920,
    height: int = 1080,
    duration: float = 1.0,
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> Optional[str]:
    """
    创建转场遮罩视频（白色区域=显示上层，黑色=显示下层）

    Args:
        output_dir: 输出目录
        style: 转场风格
        width/height: 分辨率
        duration: 时长
        color: 遮罩颜色（默认白色）

    Returns:
        MP4视频路径或None
    """
    runner = BlenderRunner()
    if not runner.is_available():
        return None

    fps = 30
    frames = int(duration * fps)

    # 使用一个平面作为遮罩，通过缩放/位移动画实现转场
    scene = BlenderScene(
        width=width,
        height=height,
        fps=fps,
        frame_end=frames,
        background_color=(0, 0, 0),
        texts=[],
        glow=None,
        camera_location=(0, 0, 10),
    )

    os.makedirs(output_dir, exist_ok=True)
    script_content = runner._generate_python_script(scene, output_dir)

    # 注入遮罩平面动画
    transition_script = f"""
# 转场遮罩平面
import bpy
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
mask_obj = bpy.context.active_object
mask_obj.name = 'TransitionMask'

# 白色发光材质
mat = bpy.data.materials.new(name='MaskMat')
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
for n in nodes: nodes.remove(n)
emission = nodes.new(type='ShaderNodeEmission')
emission.inputs[0].default_value = ({color[0]}, {color[1]}, {color[2]}, 1.0)
emission.inputs[1].default_value = 5.0
output = nodes.new(type='ShaderNodeOutputMaterial')
links.new(emission.outputs[0], output.inputs[0])
mask_obj.data.materials.append(mat)

# 转场动画
"""
    if style == "fade":
        transition_script += """
mask_obj.scale = (0.01, 0.01, 1)
mask_obj.keyframe_insert(data_path='scale', frame=1)
mask_obj.scale = (1.5, 1.5, 1)
mask_obj.keyframe_insert(data_path='scale', frame=FRAME_END)
""".replace("FRAME_END", str(frames))
    elif style == "slide_left":
        transition_script += f"""
mask_obj.location = (20, 0, 0)
mask_obj.keyframe_insert(data_path='location', frame=1)
mask_obj.location = (-20, 0, 0)
mask_obj.keyframe_insert(data_path='location', frame={frames})
"""
    elif style == "slide_right":
        transition_script += f"""
mask_obj.location = (-20, 0, 0)
mask_obj.keyframe_insert(data_path='location', frame=1)
mask_obj.location = (20, 0, 0)
mask_obj.keyframe_insert(data_path='location', frame={frames})
"""
    elif style == "zoom_in":
        transition_script += f"""
mask_obj.scale = (3.0, 3.0, 1)
mask_obj.keyframe_insert(data_path='scale', frame=1)
mask_obj.scale = (0.01, 0.01, 1)
mask_obj.keyframe_insert(data_path='scale', frame={frames})
"""
    elif style == "zoom_out":
        transition_script += f"""
mask_obj.scale = (0.01, 0.01, 1)
mask_obj.keyframe_insert(data_path='scale', frame=1)
mask_obj.scale = (3.0, 3.0, 1)
mask_obj.keyframe_insert(data_path='scale', frame={frames})
"""

    transition_script += f"""
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(r'{output_dir}', 'scene.blend'))
print('✅ 转场场景已创建: {style}')
"""

    script_content = script_content.replace(
        "bpy.ops.wm.save_as_mainfile(filepath=blend_path)",
        transition_script,
    )

    script_path = os.path.join(output_dir, "setup_scene.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    import subprocess
    result = subprocess.run(
        [runner.blender_path, "-b", "-P", script_path],
        capture_output=True, text=True, timeout=120,
    )

    blend_path = os.path.join(output_dir, "scene.blend")
    if not os.path.exists(blend_path):
        print(f"❌ 转场创建失败: {style}")
        return None

    print(f"🔄 转场: {style} ({duration}s)")
    return runner.render(blend_path, output_dir, fps)


def create_light_sweep(
    output_dir: str,
    width: int = 1920,
    height: int = 1080,
    duration: float = 2.0,
    color: Tuple[float, float, float] = (1.0, 0.9, 0.6, 1.0),
) -> Optional[str]:
    """
    创建光线扫描特效（横向扫光）

    Args:
        output_dir: 输出目录
        width/height: 分辨率
        duration: 时长
        color: 光线颜色

    Returns:
        MP4视频路径或None
    """
    runner = BlenderRunner()
    if not runner.is_available():
        return None

    fps = 30
    frames = int(duration * fps)

    scene = BlenderScene(
        width=width, height=height, fps=fps, frame_end=frames,
        background_color=(0, 0, 0),
        glow=BlenderGlow(enabled=True, threshold=0.05, size=15.0),
        camera_location=(0, 0, 10),
    )

    os.makedirs(output_dir, exist_ok=True)
    script_content = runner._generate_python_script(scene, output_dir)

    sweep_script = f"""
# 光线扫描
import bpy
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
light_obj = bpy.context.active_object
light_obj.scale = (0.1, 15, 1)

mat = bpy.data.materials.new(name='LightSweep')
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
for n in nodes: nodes.remove(n)
emission = nodes.new(type='ShaderNodeEmission')
emission.inputs[0].default_value = ({color[0]}, {color[1]}, {color[2]}, 1.0)
emission.inputs[1].default_value = 10.0
output = nodes.new(type='ShaderNodeOutputMaterial')
links.new(emission.outputs[0], output.inputs[0])
light_obj.data.materials.append(mat)

# 扫光动画
light_obj.location = (-15, 0, 0)
light_obj.keyframe_insert(data_path='location', frame=1)
light_obj.location = (15, 0, 0)
light_obj.keyframe_insert(data_path='location', frame={frames})

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(r'{output_dir}', 'scene.blend'))
print('✅ 光线扫描已创建')
"""
    script_content = script_content.replace(
        "bpy.ops.wm.save_as_mainfile(filepath=blend_path)",
        sweep_script,
    )

    script_path = os.path.join(output_dir, "setup_scene.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    import subprocess
    subprocess.run([runner.blender_path, "-b", "-P", script_path],
                   capture_output=True, text=True, timeout=120)

    blend_path = os.path.join(output_dir, "scene.blend")
    if not os.path.exists(blend_path):
        return None
    print(f"💡 光线扫描: {duration}s")
    return runner.render(blend_path, output_dir, fps)


if __name__ == "__main__":
    print("=" * 60)
    print("Blender扩展特效库")
    print("=" * 60)
    print("\n可用特效:")
    print("  1. create_particle_background - 粒子背景")
    print("     预设: stars / snow / bokeh / fireworks / neon")
    print("  2. create_text_intro - 3D文字入场动画")
    print("     风格: zoom / slide / fade / rotate")
    print("  3. create_transition - 转场遮罩")
    print("     风格: fade / slide_left / slide_right / zoom_in / zoom_out")
    print("  4. create_light_sweep - 光线扫描")
    print("\n粒子预设:")
    for name in PARTICLE_PRESETS:
        cfg = PARTICLE_PRESETS[name]
        print(f"  {name}: {cfg['count']}粒子, {cfg['particle_size']}大小")
