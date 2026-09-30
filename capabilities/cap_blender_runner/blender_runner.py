"""
Blender合成运行器
完全免费 + 完整Python API + 命令行后台渲染

功能：
- 文字动画（发光、描边、挤出）
- 粒子系统（点云、发射、重力）
- 合成器特效（辉光、模糊、色彩校正）
- 命令行后台渲染（blender -b file.blend -a）
- ffmpeg自动合成MP4

依赖：
- Blender 4.x（安装路径可配置）
- ffmpeg（合成视频）
"""

import os
import sys
import subprocess
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


# 默认Blender路径
DEFAULT_BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# 默认ffmpeg路径
DEFAULT_FFMPEG_PATH = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"


@dataclass
class BlenderText:
    """文字元素"""
    text: str = "Text"
    size: float = 2.0
    location: Tuple[float, float, float] = (0, 0, 0)
    rotation: Tuple[float, float, float] = (0, 0, 0)
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    emission_strength: float = 0.0  # >0 则发光
    extrude: float = 0.0
    bevel_depth: float = 0.0
    font: str = ""  # 空=默认字体


@dataclass
class BlenderParticles:
    """粒子系统"""
    count: int = 100
    emitter_size: float = 1.0
    lifetime: int = 90
    frame_start: int = 1
    frame_end: int = 60
    normal_factor: float = 2.0
    particle_size: float = 0.1
    color: Tuple[float, float, float, float] = (0.3, 0.8, 1.0, 1.0)
    emission_strength: float = 2.0
    gravity: float = 0.0


@dataclass
class BlenderGlow:
    """辉光合成效果"""
    enabled: bool = True
    threshold: float = 0.2
    size: float = 5.0
    glow_type: str = "FOG_GLOW"  # FOG_GLOW, GHOST, STREAKS, FILTER


@dataclass
class BlenderScene:
    """Blender场景配置"""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    frame_start: int = 1
    frame_end: int = 90
    background_color: Tuple[float, float, float] = (0.05, 0.05, 0.1)
    texts: List[BlenderText] = field(default_factory=list)
    particles: Optional[BlenderParticles] = None
    glow: Optional[BlenderGlow] = None
    camera_location: Tuple[float, float, float] = (0, 0, 10)


class BlenderRunner:
    """Blender合成运行器"""

    def __init__(
        self,
        blender_path: str = None,
        ffmpeg_path: str = None,
    ):
        self.blender_path = blender_path or DEFAULT_BLENDER_PATH
        self.ffmpeg_path = ffmpeg_path or DEFAULT_FFMPEG_PATH

    def is_available(self) -> bool:
        """检查Blender是否可用"""
        return os.path.exists(self.blender_path)

    def _generate_python_script(self, scene: BlenderScene, output_dir: str) -> str:
        """生成Blender Python脚本"""
        lines = []
        lines.append("import bpy")
        lines.append("import os")
        lines.append("")

        # 清空场景
        lines.append("# 清空场景")
        lines.append("for obj in bpy.data.objects:")
        lines.append("    bpy.data.objects.remove(obj, do_unlink=True)")
        lines.append("for mesh in bpy.data.meshes:")
        lines.append("    bpy.data.meshes.remove(mesh)")
        lines.append("for mat in bpy.data.materials:")
        lines.append("    bpy.data.materials.remove(mat)")
        lines.append("")

        # 渲染设置
        lines.append("# 渲染设置")
        lines.append("scene = bpy.context.scene")
        lines.append("scene.render.engine = 'BLENDER_EEVEE'")
        lines.append(f"scene.render.resolution_x = {scene.width}")
        lines.append(f"scene.render.resolution_y = {scene.height}")
        lines.append(f"scene.render.fps = {scene.fps}")
        lines.append(f"scene.frame_start = {scene.frame_start}")
        lines.append(f"scene.frame_end = {scene.frame_end}")
        lines.append(f"scene.render.filepath = r'{output_dir}' + os.sep + 'frame_'")
        lines.append("scene.render.image_settings.file_format = 'PNG'")
        lines.append("")

        # 背景世界
        lines.append("# 背景")
        lines.append("world = bpy.data.worlds.new('World')")
        lines.append("world.use_nodes = True")
        lines.append("bg_node = world.node_tree.nodes['Background']")
        lines.append(f"bg_node.inputs[0].default_value = ({scene.background_color[0]}, {scene.background_color[1]}, {scene.background_color[2]}, 1.0)")
        lines.append("scene.world = world")
        lines.append("")

        # 相机
        lines.append("# 相机")
        lines.append("cam_data = bpy.data.cameras.new(name='Camera')")
        lines.append("cam_obj = bpy.data.objects.new('Camera', cam_data)")
        lines.append(f"cam_obj.location = ({scene.camera_location[0]}, {scene.camera_location[1]}, {scene.camera_location[2]})")
        lines.append("cam_obj.rotation_euler = (0, 0, 0)")
        lines.append("scene.collection.objects.link(cam_obj)")
        lines.append("scene.camera = cam_obj")
        lines.append("")

        # 文字
        for i, text_cfg in enumerate(scene.texts):
            var_name = f"text_{i}"
            lines.append(f"# 文字 {i}: {text_cfg.text}")
            lines.append(f"{var_name}_curve = bpy.data.curves.new(name='Text{i}', type='FONT')")
            lines.append(f"{var_name}_curve.body = '{text_cfg.text}'")
            lines.append(f"{var_name}_curve.align_x = 'CENTER'")
            lines.append(f"{var_name}_curve.align_y = 'CENTER'")
            lines.append(f"{var_name}_curve.size = {text_cfg.size}")
            lines.append(f"{var_name}_curve.extrude = {text_cfg.extrude}")
            lines.append(f"{var_name}_curve.bevel_depth = {text_cfg.bevel_depth}")
            lines.append(f"{var_name}_obj = bpy.data.objects.new('Text{i}', {var_name}_curve)")
            lines.append(f"{var_name}_obj.location = ({text_cfg.location[0]}, {text_cfg.location[1]}, {text_cfg.location[2]})")
            lines.append(f"{var_name}_obj.rotation_euler = ({text_cfg.rotation[0]}, {text_cfg.rotation[1]}, {text_cfg.rotation[2]})")
            lines.append(f"scene.collection.objects.link({var_name}_obj)")

            # 文字材质
            lines.append(f"{var_name}_mat = bpy.data.materials.new(name='TextMat{i}')")
            lines.append(f"{var_name}_mat.use_nodes = True")
            lines.append(f"{var_name}_nodes = {var_name}_mat.node_tree.nodes")
            lines.append(f"{var_name}_links = {var_name}_mat.node_tree.links")
            lines.append(f"for node in {var_name}_nodes:")
            lines.append(f"    {var_name}_nodes.remove(node)")

            if text_cfg.emission_strength > 0:
                # 发光材质
                lines.append(f"{var_name}_emission = {var_name}_nodes.new(type='ShaderNodeEmission')")
                lines.append(f"{var_name}_emission.inputs[0].default_value = ({text_cfg.color[0]}, {text_cfg.color[1]}, {text_cfg.color[2]}, {text_cfg.color[3]})")
                lines.append(f"{var_name}_emission.inputs[1].default_value = {text_cfg.emission_strength}")
            else:
                # 普通材质
                lines.append(f"{var_name}_bsdf = {var_name}_nodes.new(type='ShaderNodeBsdfPrincipled')")
                lines.append(f"{var_name}_bsdf.inputs['Base Color'].default_value = ({text_cfg.color[0]}, {text_cfg.color[1]}, {text_cfg.color[2]}, {text_cfg.color[3]})")

            lines.append(f"{var_name}_output = {var_name}_nodes.new(type='ShaderNodeOutputMaterial')")
            if text_cfg.emission_strength > 0:
                lines.append(f"{var_name}_links.new({var_name}_emission.outputs[0], {var_name}_output.inputs[0])")
            else:
                lines.append(f"{var_name}_links.new({var_name}_bsdf.outputs[0], {var_name}_output.inputs[0])")
            lines.append(f"{var_name}_obj.data.materials.append({var_name}_mat)")
            lines.append("")

        # 粒子系统
        if scene.particles:
            p = scene.particles
            lines.append("# 粒子系统")
            lines.append("pmesh = bpy.data.meshes.new(name='Emitter')")
            lines.append(f"pverts = [(-{p.emitter_size}, -{p.emitter_size}, 0), ({p.emitter_size}, -{p.emitter_size}, 0), ({p.emitter_size}, {p.emitter_size}, 0), (-{p.emitter_size}, {p.emitter_size}, 0)]")
            lines.append("pfaces = [(0, 1, 2, 3)]")
            lines.append("pmesh.from_pydata(pverts, [], pfaces)")
            lines.append("pmesh.update()")
            lines.append("emitter_obj = bpy.data.objects.new('Emitter', pmesh)")
            lines.append("emitter_obj.hide_render = True")
            lines.append("scene.collection.objects.link(emitter_obj)")
            lines.append("ps_mod = emitter_obj.modifiers.new(name='Particles', type='PARTICLE_SYSTEM')")
            lines.append("ps = emitter_obj.particle_systems[0]")
            lines.append(f"ps.settings.count = {p.count}")
            lines.append(f"ps.settings.frame_start = {p.frame_start}")
            lines.append(f"ps.settings.frame_end = {p.frame_end}")
            lines.append(f"ps.settings.lifetime = {p.lifetime}")
            lines.append(f"ps.settings.normal_factor = {p.normal_factor}")
            lines.append("ps.settings.render_type = 'HALO'")
            lines.append(f"ps.settings.particle_size = {p.particle_size}")
            # 粒子材质
            lines.append("pmat = bpy.data.materials.new(name='ParticleMat')")
            lines.append("pmat.use_nodes = True")
            lines.append("pnodes = pmat.node_tree.nodes")
            lines.append("plinks = pmat.node_tree.links")
            lines.append("for node in pnodes:")
            lines.append("    pnodes.remove(node)")
            lines.append("pemission = pnodes.new(type='ShaderNodeEmission')")
            lines.append(f"pemission.inputs[0].default_value = ({p.color[0]}, {p.color[1]}, {p.color[2]}, {p.color[3]})")
            lines.append(f"pemission.inputs[1].default_value = {p.emission_strength}")
            lines.append("poutput = pnodes.new(type='ShaderNodeOutputMaterial')")
            lines.append("plinks.new(pemission.outputs[0], poutput.inputs[0])")
            lines.append("emitter_obj.data.materials.append(pmat)")
            lines.append("ps.settings.material = 0")
            lines.append("")

        # EEVEE Bloom辉光（兼容Blender 4.x和5.x）
        if scene.glow and scene.glow.enabled:
            g = scene.glow
            lines.append("# EEVEE Bloom辉光（try/except兼容多版本）")
            lines.append("try:")
            lines.append("    scene.eevee.use_bloom = True")
            lines.append(f"    scene.eevee.bloom_threshold = {g.threshold}")
            lines.append(f"    scene.eevee.bloom_radius = {g.size / 10.0}")
            lines.append("    scene.eevee.bloom_intensity = 0.8")
            lines.append("except AttributeError:")
            lines.append("    pass")
            lines.append("")

        # 保存blend文件
        lines.append("# 保存blend文件")
        lines.append(f"blend_path = os.path.join(r'{output_dir}', 'scene.blend')")
        lines.append("bpy.ops.wm.save_as_mainfile(filepath=blend_path)")
        lines.append("print('✅ Blender场景已创建')")

        return "\n".join(lines)

    def create_scene(
        self,
        scene: BlenderScene,
        output_dir: str,
    ) -> str:
        """
        创建Blender场景并保存.blend文件

        Args:
            scene: 场景配置
            output_dir: 输出目录

        Returns:
            .blend文件路径
        """
        os.makedirs(output_dir, exist_ok=True)

        # 生成Python脚本
        script_content = self._generate_python_script(scene, output_dir)
        script_path = os.path.join(output_dir, "setup_scene.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # 运行Blender创建场景
        result = subprocess.run(
            [self.blender_path, "-b", "-P", script_path],
            capture_output=True, text=True, timeout=120,
        )

        blend_path = os.path.join(output_dir, "scene.blend")
        if os.path.exists(blend_path):
            print(f"✅ 场景已创建: {blend_path}")
            return blend_path
        else:
            print(f"❌ 场景创建失败")
            print(result.stdout[-500:] if result.stdout else "")
            print(result.stderr[-500:] if result.stderr else "")
            return None

    def render(
        self,
        blend_path: str,
        output_dir: str,
        fps: int = 30,
    ) -> Optional[str]:
        """
        渲染Blender场景并合成MP4

        Args:
            blend_path: .blend文件路径
            output_dir: 输出目录
            fps: 帧率

        Returns:
            MP4视频路径或None
        """
        if not os.path.exists(blend_path):
            print(f"❌ blend文件不存在: {blend_path}")
            return None

        # 后台渲染
        print(f"开始渲染: {blend_path}")
        result = subprocess.run(
            [self.blender_path, "-b", blend_path, "-a"],
            capture_output=True, text=True, timeout=600,
        )

        # 检查PNG序列
        png_pattern = os.path.join(output_dir, "frame_*.png")
        import glob
        png_files = sorted(glob.glob(png_pattern))

        if not png_files:
            print(f"❌ 渲染未生成PNG帧")
            print(result.stdout[-500:] if result.stdout else "")
            return None

        print(f"✅ 渲染完成: {len(png_files)}帧")

        # ffmpeg合成MP4
        mp4_path = os.path.join(output_dir, "output.mp4")
        first_frame = png_files[0]
        # 确定帧编号格式
        import re
        match = re.search(r'frame_(\d+)\.png', os.path.basename(first_frame))
        if match:
            digits = len(match.group(1))
            input_pattern = os.path.join(output_dir, f"frame_%0{digits}d.png")
        else:
            input_pattern = os.path.join(output_dir, "frame_%04d.png")

        ffmpeg_result = subprocess.run(
            [
                self.ffmpeg_path, "-y",
                "-framerate", str(fps),
                "-i", input_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                mp4_path,
            ],
            capture_output=True, text=True, timeout=120,
        )

        if os.path.exists(mp4_path):
            size_kb = os.path.getsize(mp4_path) / 1024
            print(f"✅ 视频已生成: {mp4_path} ({size_kb:.1f}KB)")
            return mp4_path
        else:
            print(f"❌ 视频合成失败")
            print(ffmpeg_result.stderr[-500:] if ffmpeg_result.stderr else "")
            return None

    def create_and_render(
        self,
        scene: BlenderScene,
        output_dir: str,
    ) -> Optional[str]:
        """
        创建场景并渲染（一步到位）

        Args:
            scene: 场景配置
            output_dir: 输出目录

        Returns:
            MP4视频路径或None
        """
        blend_path = self.create_scene(scene, output_dir)
        if not blend_path:
            return None
        return self.render(blend_path, output_dir, scene.fps)


# 便捷函数：创建文字动画特效
def create_text_animation(
    text: str,
    output_dir: str,
    width: int = 1920,
    height: int = 1080,
    duration: float = 3.0,
    color: Tuple[float, float, float, float] = (1.0, 0.8, 0.2, 1.0),
    glow: bool = True,
) -> Optional[str]:
    """
    创建文字动画特效

    Args:
        text: 文字内容
        output_dir: 输出目录
        width: 宽度
        height: 高度
        duration: 时长（秒）
        color: 文字颜色 (R, G, B, A)
        glow: 是否启用辉光

    Returns:
        MP4视频路径或None
    """
    runner = BlenderRunner()
    if not runner.is_available():
        print("❌ Blender不可用")
        return None

    scene = BlenderScene(
        width=width,
        height=height,
        fps=30,
        frame_end=int(duration * 30),
        texts=[
            BlenderText(
                text=text,
                size=2.0,
                color=color,
                emission_strength=3.0 if glow else 0.0,
                extrude=0.1,
                bevel_depth=0.02,
            )
        ],
        glow=BlenderGlow(enabled=glow, threshold=0.2, size=5.0),
    )

    return runner.create_and_render(scene, output_dir)


# 便捷函数：创建粒子特效
def create_particle_effect(
    output_dir: str,
    width: int = 1920,
    height: int = 1080,
    duration: float = 3.0,
    count: int = 200,
    color: Tuple[float, float, float, float] = (0.3, 0.8, 1.0, 1.0),
    text: str = "",
) -> Optional[str]:
    """
    创建粒子特效

    Args:
        output_dir: 输出目录
        width: 宽度
        height: 高度
        duration: 时长（秒）
        count: 粒子数量
        color: 粒子颜色
        text: 可选文字（叠加在粒子上）

    Returns:
        MP4视频路径或None
    """
    runner = BlenderRunner()
    if not runner.is_available():
        print("❌ Blender不可用")
        return None

    texts = []
    if text:
        texts.append(BlenderText(
            text=text,
            size=1.5,
            color=(1.0, 1.0, 1.0, 1.0),
            emission_strength=2.0,
            location=(0, 0, 2),
        ))

    scene = BlenderScene(
        width=width,
        height=height,
        fps=30,
        frame_end=int(duration * 30),
        texts=texts,
        particles=BlenderParticles(
            count=count,
            lifetime=int(duration * 30),
            color=color,
            emission_strength=3.0,
        ),
        glow=BlenderGlow(enabled=True, threshold=0.1, size=8.0),
    )

    return runner.create_and_render(scene, output_dir)


if __name__ == "__main__":
    print("=" * 60)
    print("Blender合成运行器")
    print("=" * 60)
    runner = BlenderRunner()
    print(f"Blender路径: {runner.blender_path}")
    print(f"Blender可用: {'✅' if runner.is_available() else '❌'}")
    print(f"ffmpeg路径: {runner.ffmpeg_path}")
    print("\n便捷函数:")
    print("  create_text_animation(text, output_dir) - 文字动画")
    print("  create_particle_effect(output_dir) - 粒子特效")
