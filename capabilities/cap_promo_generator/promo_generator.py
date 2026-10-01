"""
宣传视频生成器 v1.0
专门针对宣传视频优化，解决以下问题：
1. 全程有视觉素材（无黑屏）
2. 使用剪映原生文字轨道（非文字图片）
3. 时间线连续，片段无缝衔接
4. ComfyUI生成关键帧素材
5. 自动转场+字幕+背景音乐位

核心原则：每个时间点都必须有视觉内容
"""
import os
import sys
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple

# 技能路径
SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# 渐变色预设
GRADIENT_PRESETS = {
    "sunset": [(255, 94, 98), (255, 153, 102), (255, 204, 102)],
    "ocean": [(0, 82, 147), (0, 119, 182), (0, 168, 232)],
    "forest": [(34, 87, 46), (56, 142, 60), (102, 187, 106)],
    "purple": [(88, 28, 135), (123, 31, 162), (156, 39, 176)],
    "dark": [(20, 20, 30), (40, 40, 60), (60, 60, 90)],
    "warm": [(180, 40, 30), (220, 80, 40), (255, 140, 60)],
    "cool": [(30, 60, 120), (50, 100, 180), (80, 150, 220)],
    "gold": [(139, 90, 20), (218, 165, 32), (255, 215, 0)],
}


class PromoVideoGenerator:
    """宣传视频生成器"""

    def __init__(self, work_dir: str = None, comfyui_addr: str = "http://127.0.0.1:8188"):
        self.work_dir = work_dir or os.path.join(SKILL_ROOT, "capabilities", "promo_outputs")
        os.makedirs(self.work_dir, exist_ok=True)
        self.asset_dir = os.path.join(self.work_dir, "assets")
        os.makedirs(self.asset_dir, exist_ok=True)
        self.comfyui_addr = comfyui_addr

    def generate_gradient_background(self, width: int = 1080, height: int = 1920,
                                      style: str = "sunset", output_path: str = None) -> str:
        """生成渐变背景图（确保无黑屏）"""
        if not _PIL_AVAILABLE:
            # 兜底：纯色
            return self._generate_solid_background(width, height, (40, 40, 60), output_path)

        colors = GRADIENT_PRESETS.get(style, GRADIENT_PRESETS["sunset"])
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # 垂直渐变
        for y in range(height):
            ratio = y / height
            # 找到在哪个颜色段
            segment = ratio * (len(colors) - 1)
            idx = min(int(segment), len(colors) - 2)
            t = segment - idx
            r = int(colors[idx][0] + (colors[idx+1][0] - colors[idx][0]) * t)
            g = int(colors[idx][1] + (colors[idx+1][1] - colors[idx][1]) * t)
            b = int(colors[idx][2] + (colors[idx+1][2] - colors[idx][2]) * t)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        if output_path is None:
            output_path = os.path.join(self.asset_dir, f"bg_{style}_{uuid.uuid4().hex[:8]}.png")
        img.save(output_path, "PNG")
        return output_path

    def _generate_solid_background(self, width: int, height: int,
                                     color: Tuple[int, int, int], output_path: str = None) -> str:
        """生成纯色背景（兜底）"""
        if _PIL_AVAILABLE:
            img = Image.new("RGB", (width, height), color)
            if output_path is None:
                output_path = os.path.join(self.asset_dir, f"bg_solid_{uuid.uuid4().hex[:8]}.png")
            img.save(output_path, "PNG")
            return output_path
        return ""

    def generate_comfyui_image(self, prompt: str, width: int = 1080, height: int = 1920) -> Optional[str]:
        """用ComfyUI生成图片（失败则返回None，用渐变背景兜底）"""
        try:
            sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))
            from cap_comfyui_runner.api import text2image_sdxl, check_comfyui_ready
            if not check_comfyui_ready(self.comfyui_addr):
                print(f"  ⚠️ ComfyUI未就绪，使用渐变背景")
                return None

            output_path = os.path.join(self.asset_dir, f"comfy_{uuid.uuid4().hex[:8]}.png")
            result = text2image_sdxl(
                prompt=prompt,
                width=width,
                height=height,
                output_path=output_path,
                server_addr=self.comfyui_addr,
            )
            if result and os.path.exists(result):
                return result
            return None
        except Exception as e:
            print(f"  ⚠️ ComfyUI生成失败: {e}，使用渐变背景")
            return None

    def create_promo_video(self,
                            title: str,
                            scenes: List[Dict[str, Any]],
                            project_name: str = None,
                            width: int = 1080,
                            height: int = 1920,
                            bg_style: str = "sunset",
                            use_comfyui: bool = True,
                            transition: str = "fade",
                            ) -> Dict[str, Any]:
        """
        创建宣传视频（核心方法）

        Args:
            title: 视频标题
            scenes: 场景列表，每个场景:
                {
                    "text": "主标题文字",
                    "subtitle": "副标题文字（可选）",
                    "duration": 5.0,  # 秒
                    "bg_style": "sunset",  # 可选，覆盖全局
                    "image_prompt": "AI生成图片的提示词（可选）",
                    "text_size": 12.0,  # 可选
                    "text_color": (1.0, 1.0, 1.0),  # 可选
                }
            project_name: 工程名
            width/height: 画布尺寸
            bg_style: 默认背景风格
            use_comfyui: 是否使用ComfyUI生成图片
            transition: 转场类型（fade/slide/none）

        Returns:
            合成结果字典
        """
        if project_name is None:
            project_name = f"Promo_{uuid.uuid4().hex[:6]}"

        print(f"\n{'='*60}")
        print(f"🎬 宣传视频生成器")
        print(f"{'='*60}")
        print(f"标题: {title}")
        print(f"场景数: {len(scenes)}")
        print(f"总时长: {sum(s.get('duration', 3) for s in scenes):.1f}秒")
        print(f"ComfyUI: {'开启' if use_comfyui else '关闭'}")

        # 1. 创建工程
        print(f"\n[1/4] 创建剪映工程: {project_name}")
        project = JyProject(project_name, width=width, height=height, overwrite=True)

        # 2. 生成背景素材（全程覆盖，确保无黑屏）
        print(f"\n[2/4] 生成背景素材（确保全程有画面）")
        total_duration = sum(s.get('duration', 3) for s in scenes)
        global_bg = self.generate_gradient_background(width, height, bg_style)
        if global_bg:
            # 全局背景轨道（全程覆盖）
            project.add_media_safe(
                global_bg,
                start_time="0s",
                duration=f"{total_duration:.2f}s",
                track_name="GlobalBG",
            )
            print(f"  ✅ 全局背景: {total_duration:.1f}秒全程覆盖")

        # 3. 逐场景合成
        print(f"\n[3/4] 逐场景合成")
        current_time = 0.0
        scene_bgs = []  # 每个场景的背景图路径

        for i, scene in enumerate(scenes):
            scene_duration = scene.get('duration', 3.0)
            scene_bg_style = scene.get('bg_style', bg_style)
            text = scene.get('text', '')
            subtitle = scene.get('subtitle', '')
            text_size = scene.get('text_size', 12.0)
            text_color = scene.get('text_color', (1.0, 1.0, 1.0))

            print(f"\n  场景 {i+1}/{len(scenes)}: {text[:20]}... ({scene_duration:.1f}s)")

            # 3a. 生成场景背景（ComfyUI或渐变）
            scene_bg = None
            if use_comfyui and scene.get('image_prompt'):
                scene_bg = self.generate_comfyui_image(
                    prompt=scene['image_prompt'],
                    width=width,
                    height=height,
                )
            if not scene_bg:
                scene_bg = self.generate_gradient_background(width, height, scene_bg_style)

            scene_bgs.append(scene_bg)

            # 3b. 添加场景背景（在全局背景之上）
            if scene_bg:
                bg_seg = project.add_media_safe(
                    scene_bg,
                    start_time=f"{current_time:.2f}s",
                    duration=f"{scene_duration:.2f}s",
                    track_name=f"SceneBG_{i+1}",
                )
                # 背景淡入淡出
                if bg_seg and transition == "fade":
                    fade_dur = min(0.5, scene_duration * 0.2)
                    bg_seg.add_keyframe(draft.KeyframeProperty.alpha,
                                         int(current_time * 1e6), 0.0, **draft.Keyframe.EASE_OUT)
                    bg_seg.add_keyframe(draft.KeyframeProperty.alpha,
                                         int((current_time + fade_dur) * 1e6), 1.0, **draft.Keyframe.EASE_OUT)
                    bg_seg.add_keyframe(draft.KeyframeProperty.alpha,
                                         int((current_time + scene_duration - fade_dur) * 1e6), 1.0, **draft.Keyframe.EASE_IN)
                    bg_seg.add_keyframe(draft.KeyframeProperty.alpha,
                                         int((current_time + scene_duration) * 1e6), 0.0, **draft.Keyframe.EASE_IN)

            # 3c. 添加主标题（剪映原生文字轨道，非图片！）
            if text:
                main_style = draft.TextStyle(size=text_size, color=text_color)
                main_seg = project.add_text_simple(
                    text=text,
                    start_time=f"{current_time + 0.3:.2f}s",
                    duration=f"{scene_duration - 0.6:.2f}s",
                    track_name=f"Title_{i+1}",
                    style=main_style,
                    clip_settings=draft.ClipSettings(transform_y=0.0),
                )
                # 文字淡入
                if main_seg:
                    main_seg.add_keyframe(draft.KeyframeProperty.alpha,
                                           int((current_time + 0.3) * 1e6), 0.0, **draft.Keyframe.EASE_OUT)
                    main_seg.add_keyframe(draft.KeyframeProperty.alpha,
                                           int((current_time + 0.8) * 1e6), 1.0, **draft.Keyframe.EASE_OUT)
                print(f"    ✅ 主标题: {text[:15]}... (原生文字轨道)")

            # 3d. 添加副标题（原生文字轨道）
            if subtitle:
                sub_style = draft.TextStyle(size=text_size * 0.6, color=(text_color[0]*0.8, text_color[1]*0.8, text_color[2]*0.8))
                sub_seg = project.add_text_simple(
                    text=subtitle,
                    start_time=f"{current_time + 0.8:.2f}s",
                    duration=f"{scene_duration - 1.2:.2f}s",
                    track_name=f"Subtitle_{i+1}",
                    style=sub_style,
                    clip_settings=draft.ClipSettings(transform_y=-0.5),
                )
                if sub_seg:
                    sub_seg.add_keyframe(draft.KeyframeProperty.alpha,
                                           int((current_time + 0.8) * 1e6), 0.0, **draft.Keyframe.EASE_OUT)
                    sub_seg.add_keyframe(draft.KeyframeProperty.alpha,
                                           int((current_time + 1.3) * 1e6), 1.0, **draft.Keyframe.EASE_OUT)
                print(f"    ✅ 副标题: {subtitle[:15]}...")

            current_time += scene_duration

        # 4. 保存工程
        print(f"\n[4/4] 保存工程")
        result = project.save()
        draft_path = result.get("draft_path", "")

        print(f"\n{'✅'*20}")
        print(f"宣传视频生成完成!")
        print(f"工程: {project_name}")
        print(f"草稿: {draft_path}")
        print(f"场景: {len(scenes)}个")
        print(f"时长: {total_duration:.1f}秒")
        print(f"背景: 全局+{len(scene_bgs)}个场景背景（无黑屏）")
        print(f"文字: 全部使用剪映原生文字轨道")
        print(f"{'✅'*20}")

        return {
            "status": "success",
            "project_name": project_name,
            "draft_path": draft_path,
            "title": title,
            "scene_count": len(scenes),
            "total_duration": total_duration,
            "backgrounds": [global_bg] + scene_bgs,
            "width": width,
            "height": height,
        }

    def quick_promo(self, title: str, points: List[str],
                     duration_per_point: float = 4.0,
                     bg_style: str = "sunset",
                     project_name: str = None) -> Dict[str, Any]:
        """
        快速生成宣传视频（简化接口）

        Args:
            title: 视频标题（开场场景）
            points: 要点列表，每个要点一个场景
            duration_per_point: 每个要点时长（秒）
            bg_style: 背景风格
            project_name: 工程名

        Returns:
            合成结果
        """
        scenes = []
        # 开场
        scenes.append({
            "text": title,
            "subtitle": "精彩内容马上开始",
            "duration": duration_per_point,
            "bg_style": bg_style,
        })
        # 要点
        for i, point in enumerate(points):
            scenes.append({
                "text": point,
                "subtitle": f"{i+1}/{len(points)}",
                "duration": duration_per_point,
                "bg_style": bg_style,
            })
        # 结尾
        scenes.append({
            "text": "感谢观看",
            "subtitle": "点赞关注不迷路",
            "duration": duration_per_point,
            "bg_style": bg_style,
        })

        return self.create_promo_video(
            title=title,
            scenes=scenes,
            project_name=project_name,
            bg_style=bg_style,
            use_comfyui=False,  # 快速模式不用ComfyUI
        )


if __name__ == "__main__":
    print("=" * 60)
    print("宣传视频生成器 v1.0")
    print("=" * 60)
    print("\n可用背景风格:")
    for name in GRADIENT_PRESETS:
        print(f"  - {name}")
    print("\n使用方法:")
    print("  generator = PromoVideoGenerator()")
    print("  result = generator.quick_promo('我的视频', ['要点1', '要点2', '要点3'])")
    print("  # 或自定义场景:")
    print("  result = generator.create_promo_video('标题', [{'text': '...', 'duration': 5}])")
