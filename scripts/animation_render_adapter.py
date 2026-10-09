#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一动画渲染适配器 (Animation Render Adapter)
根据动画类型自动选择HyperFrames或Remotion后端

分工:
- HyperFrames: 文字/字幕/标题卡/动态排版（主力）
- Remotion: 透明背景角色动画（备选，需Alpha通道）

用法:
    from animation_render_adapter import AnimationRenderAdapter
    adapter = AnimationRenderAdapter()
    result = adapter.render_text_animation("标题", style="epic", duration=5)
    result = adapter.render_character_animation("doubao_fall", transparent=True)
"""

import os
import sys
from typing import Dict, Any, List
from dataclasses import dataclass

PROJECT_ROOT = r"D:\DobaoWork_Project\Ai_Video_Editor"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from hyperframes_executor import HyperFramesExecutor
from hyperframes_text_animator import HyperFramesTextAnimator, TextAnimationConfig
import logging
logger = logging.getLogger(__name__)


@dataclass
class RenderResult:
    """渲染结果"""
    success: bool
    output_path: str = ""
    backend: str = ""  # hyperframes / remotion
    render_time: float = 0
    error: str = ""
    width: int = 0
    height: int = 0


class AnimationRenderAdapter:
    """统一动画渲染适配器

    自动根据动画类型选择后端:
    - 文字类 → HyperFrames（高效、内置AI、GPU加速）
    - 透明角色类 → Remotion（Alpha通道）
    """

    def __init__(self, work_dir: str = None):
        self.work_dir = work_dir or os.path.join(PROJECT_ROOT, "animation_output")
        os.makedirs(self.work_dir, exist_ok=True)
        self.hf_executor = HyperFramesExecutor()
        self.hf_animator = HyperFramesTextAnimator()
        self._remotion_available = self._check_remotion()

    def _check_remotion(self) -> bool:
        """检查Remotion是否可用"""
        remotion_project = os.path.join(PROJECT_ROOT, "remotion-project")
        return os.path.isdir(remotion_project)

    def render_text_animation(
        self,
        text: str,
        style: str = "default",
        intro: str = "fade_in",
        outro: str = "fade_out",
        loop: str = None,
        duration: float = 5.0,
        subtitle: str = None,
        bg_color: str = "#0a0a0a",
        position: str = "center",
        width: int = 1920,
        height: int = 1080,
        output_name: str = None,
    ) -> RenderResult:
        """渲染文字动画（使用HyperFrames）

        Args:
            text: 文字内容
            style: 样式 (default/epic/warm/fun/minimal/cinematic/neon/gradient)
            intro: 入场动画 (fade_in/slide_up/zoom_in/blur_in/typewriter等)
            outro: 出场动画
            loop: 循环动画 (pulse/shake/float/wiggle/glow/color_shift)
            duration: 时长（秒）
            subtitle: 副标题
            bg_color: 背景色
            position: 位置 (center/top/bottom)
            width/height: 分辨率
            output_name: 输出文件名

        Returns:
            RenderResult
        """
        import time
        start = time.time()

        try:
            config = TextAnimationConfig(
                text=text, duration=duration, style=style,
                intro=intro, outro=outro, loop=loop,
                subtitle=subtitle, bg_color=bg_color,
                width=width, height=height, position=position,
            )
            html = self.hf_animator.generate_html(config)

            safe_name = output_name or "".join(c if c.isalnum() else "_" for c in text[:15])
            output_path = os.path.join(self.work_dir, f"{safe_name}.mp4")

            result = self.hf_executor.render(html, output_path=output_path, duration=duration)

            if result["success"]:
                return RenderResult(
                    success=True,
                    output_path=result["output_path"],
                    backend="hyperframes",
                    render_time=time.time() - start,
                    width=result.get("width", width),
                    height=result.get("height", height),
                )
            else:
                return RenderResult(success=False, backend="hyperframes",
                                    error=result.get("error", "未知错误"))

        except Exception as e:
            return RenderResult(success=False, backend="hyperframes", error=str(e))

    def render_kinetic_typography(
        self,
        lines: List[Dict[str, Any]],
        duration: float = 8.0,
        bg_color: str = "#0a0a0a",
        output_name: str = "kinetic_typography",
    ) -> RenderResult:
        """渲染动态排版（多行文字依次出现，使用HyperFrames）

        Args:
            lines: 每行配置 [{text, style, intro, delay, duration}]
            duration: 总时长
            bg_color: 背景色
            output_name: 输出文件名
        """
        import time
        start = time.time()

        try:
            from hyperframes_text_animator import generate_kinetic_typography
            html = generate_kinetic_typography(lines, duration, bg_color)
            output_path = os.path.join(self.work_dir, f"{output_name}.mp4")
            result = self.hf_executor.render(html, output_path=output_path, duration=duration)

            if result["success"]:
                return RenderResult(
                    success=True, output_path=result["output_path"],
                    backend="hyperframes", render_time=time.time() - start,
                )
            return RenderResult(success=False, backend="hyperframes",
                                error=result.get("error", ""))
        except Exception as e:
            return RenderResult(success=False, backend="hyperframes", error=str(e))

    def render_character_animation(
        self,
        animation_id: str,
        transparent: bool = True,
        duration: float = 3.0,
        output_name: str = None,
        character_image: str = None,
        motion_type: str = "fall_hit",
        width: int = 720,
        height: int = 1280,
        fps: int = 30,
    ) -> RenderResult:
        """渲染角色动画（PNG序列+ffmpeg ProRes 4444，支持透明背景）

        Args:
            animation_id: 动画ID（用于输出命名）
            transparent: 是否需要透明背景（默认True，输出ProRes 4444）
            duration: 时长（秒）
            output_name: 输出文件名（不含扩展名）
            character_image: 角色头像路径（RGBA透明背景PNG），为None时用内置简化角色
            motion_type: 运动类型
                - "fall_hit": 掉落→被打→晕眩（3阶段，默认）
                - "bounce": 弹跳
                - "shake": 震动
                - "float": 漂浮
                - "idle": 静止呼吸
            width/height: 分辨率
            fps: 帧率

        Returns:
            RenderResult（output_path为.mov透明背景或.mp4不透明）
        """
        import time
        import math
        import subprocess
        from PIL import Image, ImageDraw, ImageFilter
        import numpy as np

        start = time.time()
        total_frames = int(duration * fps)
        safe_name = output_name or animation_id
        frames_dir = os.path.join(self.work_dir, f"{safe_name}_frames")
        os.makedirs(frames_dir, exist_ok=True)

        # 加载角色图片
        avatar = None
        if character_image and os.path.exists(character_image):
            avatar = Image.open(character_image).convert("RGBA")
            avatar.thumbnail((300, 300), Image.LANCZOS)

        base_x, base_y = width // 2, height // 3
        avatar_size = 300 if avatar else 200

        def get_position(frame_idx):
            """根据运动类型计算位置/旋转/缩放"""
            t = frame_idx / total_frames
            x, y, rot, scale = base_x, base_y, 0, 1.0

            if motion_type == "fall_hit":
                # 3阶段: 掉落(0-33%) → 被打(33-66%) → 晕眩(66-100%)
                if t < 0.33:
                    p = t / 0.33
                    y = -avatar_size + (base_y + avatar_size) * (p ** 2)
                elif t < 0.66:
                    p = (t - 0.33) / 0.33
                    x = base_x + math.sin(p * 30) * 15 * (1 - p)
                    y = base_y + math.cos(p * 25) * 10 * (1 - p)
                    rot = math.sin(p * 20) * 10 * (1 - p)
                    scale = 1.0 + 0.2 * math.sin(p * 15) * (1 - p)
                else:
                    p = (t - 0.66) / 0.34
                    x = base_x + math.sin(p * 4) * 10
                    y = base_y + math.sin(p * 3) * 5
                    rot = math.sin(p * 6) * 15
                    scale = 0.95 + 0.05 * math.sin(p * 5)
            elif motion_type == "bounce":
                y = base_y - abs(math.sin(t * math.pi * 4)) * 100
                scale = 1.0 - 0.1 * abs(math.sin(t * math.pi * 4))
            elif motion_type == "shake":
                x = base_x + math.sin(t * 40) * 20 * (1 - t * 0.5)
                y = base_y + math.cos(t * 35) * 15 * (1 - t * 0.5)
                rot = math.sin(t * 30) * 8
            elif motion_type == "float":
                y = base_y + math.sin(t * math.pi * 2) * 30
                rot = math.sin(t * math.pi * 2) * 5
            elif motion_type == "idle":
                scale = 1.0 + 0.03 * math.sin(t * math.pi * 2)
                y = base_y + math.sin(t * math.pi * 2) * 5

            return x, y, rot, scale

        # 生成帧
        for i in range(total_frames):
            img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            x, y, rot, scale = get_position(i)

            if avatar:
                w, h = avatar.size
                new_w, new_h = int(w * scale), int(h * scale)
                char_img = avatar.resize((new_w, new_h), Image.LANCZOS)
                if rot != 0:
                    char_img = char_img.rotate(rot, resample=Image.BICUBIC, expand=True)
                aw, ah = char_img.size
                img.paste(char_img, (int(x - aw / 2), int(y - ah / 2)), char_img)
            else:
                # 内置简化角色（圆形+表情）
                draw = ImageDraw.Draw(img)
                r = int(avatar_size / 2 * scale)
                draw.ellipse([x - r, y - r, x + r, y + r], fill=(100, 150, 255, 255))
                # 眼睛
                eye_r = r // 5
                draw.ellipse([x - r // 2 - eye_r, y - r // 4 - eye_r, x - r // 2 + eye_r, y - r // 4 + eye_r], fill=(255, 255, 255, 255))
                draw.ellipse([x + r // 2 - eye_r, y - r // 4 - eye_r, x + r // 2 + eye_r, y - r // 4 + eye_r], fill=(255, 255, 255, 255))

            img.save(os.path.join(frames_dir, f"frame_{i:04d}.png"))

        # 合成视频
        FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

        if transparent:
            output_path = os.path.join(self.work_dir, f"{safe_name}.mov")
            cmd = [FFMPEG, "-y", "-framerate", str(fps),
                   "-i", os.path.join(frames_dir, "frame_%04d.png"),
                   "-c:v", "prores_ks", "-profile:v", "4",
                   "-pix_fmt", "yuva444p12le", "-vendor", "apl0",
                   output_path]
        else:
            output_path = os.path.join(self.work_dir, f"{safe_name}.mp4")
            cmd = [FFMPEG, "-y", "-framerate", str(fps),
                   "-i", os.path.join(frames_dir, "frame_%04d.png"),
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
                   output_path]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return RenderResult(success=False, backend="png_sequence",
                                error=f"ffmpeg失败: {result.stderr[-300:]}")

        return RenderResult(
            success=True, output_path=output_path,
            backend="png_sequence", render_time=time.time() - start,
            width=width, height=height,
        )

    def auto_render(
        self,
        animation_type: str,
        **kwargs,
    ) -> RenderResult:
        """自动选择后端渲染

        Args:
            animation_type: 动画类型
                - "title_card" / "subtitle" / "text" / "kinetic" → HyperFrames
                - "character" / "sprite" / "transparent_element" → Remotion
        """
        if animation_type in ("title_card", "subtitle", "text", "kinetic", "chapter_title"):
            if animation_type == "kinetic":
                return self.render_kinetic_typography(**kwargs)
            return self.render_text_animation(**kwargs)
        elif animation_type in ("character", "sprite", "transparent_element"):
            return self.render_character_animation(**kwargs)
        else:
            return RenderResult(success=False, error=f"未知动画类型: {animation_type}")

    def list_capabilities(self) -> Dict[str, Any]:
        """列出适配器能力"""
        return {
            "hyperframes": {
                "available": True,
                "styles": self.hf_animator.list_styles(),
                "animations": self.hf_animator.list_animations(),
                "supports_transparent": False,
                "best_for": ["文字动画", "字幕", "标题卡", "动态排版"],
            },
            "remotion": {
                "available": self._remotion_available,
                "supports_transparent": True,
                "best_for": ["透明背景角色动画", "Alpha通道元素"],
            },
        }


# ============ 快捷函数 ============

def render_title(text: str, subtitle: str = None, style: str = "epic",
                 duration: float = 5.0) -> RenderResult:
    """快捷渲染标题卡"""
    adapter = AnimationRenderAdapter()
    return adapter.render_text_animation(
        text=text, subtitle=subtitle, style=style,
        intro="blur_in", outro="fade_out", loop="pulse",
        duration=duration,
    )


def render_subtitle(text: str, speaker: str = None, emotion: str = "calm",
                    duration: float = 3.0) -> RenderResult:
    """快捷渲染对话字幕"""
    style_map = {"angry": "neon", "happy": "fun", "sad": "minimal",
                 "calm": "default", "excited": "epic", "surprise": "fun"}
    adapter = AnimationRenderAdapter()
    return adapter.render_text_animation(
        text=text, subtitle=f"—— {speaker}" if speaker else None,
        style=style_map.get(emotion, "default"),
        intro="slide_up", outro="fade_out",
        duration=duration, position="bottom",
        bg_color="rgba(0,0,0,0.7)",
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("=== 动画渲染适配器测试 ===")
    adapter = AnimationRenderAdapter()

    logger.info("\n能力列表:")
    caps = adapter.list_capabilities()
    for backend, info in caps.items():
        logger.info(f"  {backend}: 可用={info['available']}, 透明={info['supports_transparent']}")
        logger.info(f"    适用: {', '.join(info['best_for'])}")

    logger.info("\n快捷渲染标题卡...")
    result = render_title("测试标题", "副标题", style="neon", duration=3.0)
    logger.info(f"  结果: {result.success}, 后端={result.backend}, 耗时={result.render_time:.1f}s")
    if result.success:
        logger.info(f"  输出: {result.output_path}")
