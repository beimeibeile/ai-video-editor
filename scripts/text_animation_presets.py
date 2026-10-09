"""
文字字幕动画预设库 v1.0
封装5种常用字幕动画预设，支持直接生成剪映工程。

预设列表：
1. fade      — 淡入淡出（alpha关键帧）
2. slide     — 滑入（position关键帧，支持上下左右）
3. bounce    — 弹入（scale关键帧，弹性曲线）
4. typewriter— 打字机（PIL预渲染逐字显现）
5. gradient  — 渐变流光（PIL预渲染颜色流动）

使用方法：
    from text_animation_presets import TextAnimationPresets
    presets = TextAnimationPresets()
    presets.create("fade", "你好世界", project_name="test_fade", duration=3.0)
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import math
import uuid
from typing import Dict, Any, Optional, Tuple, List

# 剪映skill路径
SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

from jy_wrapper import JyProject
import pyJianYingDraft as draft
from pyJianYingDraft.keyframe import KeyframeProperty as KP
from pyJianYingDraft.track import TrackType

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False

# 输出目录
DEFAULT_OUTPUT = r"D:\DobaoWork_Project\Ai_Video_Editor\text_animation_output"


class TextAnimationPresets:
    """文字字幕动画预设库"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or DEFAULT_OUTPUT
        os.makedirs(self.output_dir, exist_ok=True)

    # ═══════════════════════════════════════════════════════════
    # 统一入口
    # ═══════════════════════════════════════════════════════════

    def create(
        self,
        preset: str,
        text: str,
        project_name: str = None,
        duration: float = 3.0,
        width: int = 1080,
        height: int = 1920,
        font_size: float = 12.0,
        color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        position: Tuple[float, float] = (0.0, -0.5),
        **kwargs,
    ) -> Dict[str, Any]:
        """
        创建文字动画工程

        Args:
            preset: 预设名 (fade/slide/bounce/typewriter/gradient)
            text: 文字内容
            project_name: 工程名（None则自动生成）
            duration: 时长（秒）
            width/height: 画布尺寸
            font_size: 字体大小
            color: 文字颜色 (R,G,B) 0-1
            position: 位置 (x,y) 相对画布中心
            **kwargs: 预设特定参数

        Returns:
            工程信息字典
        """
        if project_name is None:
            project_name = f"text_anim_{preset}_{uuid.uuid4().hex[:6]}"

        logger.info(f"\n{'='*60}")
        logger.info(f"文字动画预设: {preset}")
        logger.info(f"文字: {text}")
        logger.info(f"时长: {duration}s, 尺寸: {width}x{height}")
        logger.info(f"{'='*60}")

        handlers = {
            "fade": self._fade,
            "slide": self._slide,
            "bounce": self._bounce,
            "typewriter": self._typewriter,
            "gradient": self._gradient,
        }

        handler = handlers.get(preset)
        if not handler:
            return {"status": "failed", "reason": f"未知预设: {preset}, 可用: {list(handlers.keys())}"}

        try:
            result = handler(
                text=text, project_name=project_name, duration=duration,
                width=width, height=height, font_size=font_size,
                color=color, position=position, **kwargs
            )
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "failed", "reason": str(e)}

    # ═══════════════════════════════════════════════════════════
    # 预设1: 淡入淡出
    # ═══════════════════════════════════════════════════════════

    def _fade(self, text, project_name, duration, width, height,
              font_size, color, position, fade_in=0.3, fade_out=0.3, **kwargs):
        """淡入淡出：alpha从0→1→0"""
        project = JyProject(project_name, width=width, height=height, overwrite=True)
        project.script.add_track(TrackType.text, "TextTrack")

        style = draft.TextStyle(size=font_size, color=color)
        seg = draft.TextSegment(
            text, draft.Timerange(0, int(duration * 1e6)),
            style=style
        )
        # 位置
        seg.clip_settings.transform_x = position[0]
        seg.clip_settings.transform_y = position[1]

        # 淡入
        seg.add_keyframe(KP.alpha, 0, 0.0)
        seg.add_keyframe(KP.alpha, int(fade_in * 1e6), 1.0)
        # 淡出
        seg.add_keyframe(KP.alpha, int((duration - fade_out) * 1e6), 1.0)
        seg.add_keyframe(KP.alpha, int(duration * 1e6), 0.0)

        project.script.add_segment(seg, "TextTrack")
        project.save()

        logger.info(f"  ✅ 淡入淡出工程已创建: {project_name}")
        return {"status": "success", "project": project_name, "preset": "fade"}

    # ═══════════════════════════════════════════════════════════
    # 预设2: 滑入
    # ═══════════════════════════════════════════════════════════

    def _slide(self, text, project_name, duration, width, height,
               font_size, color, position, direction="left", slide_in=0.3,
               slide_out=0.3, distance=1.5, **kwargs):
        """
        滑入：从指定方向滑入，停留后滑出

        Args:
            direction: left/right/up/down
            distance: 滑动距离（相对画布半宽/半高）
        """
        project = JyProject(project_name, width=width, height=height, overwrite=True)
        project.script.add_track(TrackType.text, "TextTrack")

        style = draft.TextStyle(size=font_size, color=color)
        seg = draft.TextSegment(
            text, draft.Timerange(0, int(duration * 1e6)),
            style=style
        )

        # 方向偏移
        offsets = {
            "left": (-distance, 0), "right": (distance, 0),
            "up": (0, -distance), "down": (0, distance),
        }
        dx, dy = offsets.get(direction, (-distance, 0))
        cx, cy = position

        # 起始位置（偏移）
        seg.clip_settings.transform_x = cx + dx
        seg.clip_settings.transform_y = cy + dy

        # 滑入
        seg.add_keyframe(KP.position_x, 0, cx + dx)
        seg.add_keyframe(KP.position_y, 0, cy + dy)
        seg.add_keyframe(KP.position_x, int(slide_in * 1e6), cx)
        seg.add_keyframe(KP.position_y, int(slide_in * 1e6), cy)

        # 滑出
        seg.add_keyframe(KP.position_x, int((duration - slide_out) * 1e6), cx)
        seg.add_keyframe(KP.position_y, int((duration - slide_out) * 1e6), cy)
        seg.add_keyframe(KP.position_x, int(duration * 1e6), cx - dx)
        seg.add_keyframe(KP.position_y, int(duration * 1e6), cy - dy)

        # 同步淡入淡出
        seg.add_keyframe(KP.alpha, 0, 0.0)
        seg.add_keyframe(KP.alpha, int(slide_in * 1e6), 1.0)
        seg.add_keyframe(KP.alpha, int((duration - slide_out) * 1e6), 1.0)
        seg.add_keyframe(KP.alpha, int(duration * 1e6), 0.0)

        project.script.add_segment(seg, "TextTrack")
        project.save()

        logger.info(f"  ✅ 滑入工程已创建: {project_name} (方向={direction})")
        return {"status": "success", "project": project_name, "preset": "slide", "direction": direction}

    # ═══════════════════════════════════════════════════════════
    # 预设3: 弹入
    # ═══════════════════════════════════════════════════════════

    def _bounce(self, text, project_name, duration, width, height,
                font_size, color, position, bounce_in=0.5, bounce_out=0.3,
                scale_start=0.3, scale_peak=1.2, **kwargs):
        """
        弹入：缩放弹性动画（小→大→正常）

        Args:
            scale_start: 起始缩放比例
            scale_peak: 峰值缩放比例（超过1.0产生回弹感）
        """
        project = JyProject(project_name, width=width, height=height, overwrite=True)
        project.script.add_track(TrackType.text, "TextTrack")

        style = draft.TextStyle(size=font_size, color=color)
        seg = draft.TextSegment(
            text, draft.Timerange(0, int(duration * 1e6)),
            style=style
        )
        seg.clip_settings.transform_x = position[0]
        seg.clip_settings.transform_y = position[1]

        # 弹性曲线控制点
        ease_out = {"curve_type": "Bezier", "left_control": (0.0, 0.0), "right_control": (0.58, 1.0)}

        # 弹入：0→scale_start→scale_peak→1.0
        t0 = 0
        t1 = int(bounce_in * 0.4 * 1e6)  # 到峰值
        t2 = int(bounce_in * 0.7 * 1e6)  # 回弹
        t3 = int(bounce_in * 1e6)        # 稳定

        seg.add_keyframe(KP.uniform_scale, t0, scale_start, **ease_out)
        seg.add_keyframe(KP.uniform_scale, t1, scale_peak)
        seg.add_keyframe(KP.uniform_scale, t2, 0.95)
        seg.add_keyframe(KP.uniform_scale, t3, 1.0)

        # 淡入
        seg.add_keyframe(KP.alpha, 0, 0.0)
        seg.add_keyframe(KP.alpha, int(bounce_in * 0.3 * 1e6), 1.0)

        # 弹出
        seg.add_keyframe(KP.uniform_scale, int((duration - bounce_out) * 1e6), 1.0)
        seg.add_keyframe(KP.uniform_scale, int(duration * 1e6), 0.5)
        seg.add_keyframe(KP.alpha, int((duration - bounce_out) * 1e6), 1.0)
        seg.add_keyframe(KP.alpha, int(duration * 1e6), 0.0)

        project.script.add_segment(seg, "TextTrack")
        project.save()

        logger.info(f"  ✅ 弹入工程已创建: {project_name}")
        return {"status": "success", "project": project_name, "preset": "bounce"}

    # ═══════════════════════════════════════════════════════════
    # 预设4: 打字机（PIL预渲染）
    # ═══════════════════════════════════════════════════════════

    def _typewriter(self, text, project_name, duration, width, height,
                    font_size, color, position, chars_per_second=8,
                    cursor=True, **kwargs):
        """
        打字机：逐字显现+光标闪烁（PIL预渲染帧序列→视频）

        Args:
            chars_per_second: 每秒显示字数
            cursor: 是否显示光标
        """
        if not PIL_OK:
            return {"status": "failed", "reason": "Pillow不可用，打字机效果需要PIL"}

        # 生成帧序列
        frames_dir = os.path.join(self.output_dir, f"{project_name}_frames")
        os.makedirs(frames_dir, exist_ok=True)

        fps = 30
        total_frames = int(duration * fps)
        char_duration = 1.0 / chars_per_second
        frames_per_char = int(char_duration * fps)

        # 字体
        font_path = self._find_font()
        font_size_px = int(font_size * width / 20)  # 转换为像素
        try:
            font = ImageFont.truetype(font_path, font_size_px) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        color_rgb = (int(color[0]*255), int(color[1]*255), int(color[2]*255))

        logger.info(f"  生成打字机帧序列: {total_frames}帧, {chars_per_second}字/秒")

        for frame_idx in range(total_frames):
            t = frame_idx / fps
            chars_to_show = min(len(text), int(t * chars_per_second))
            display_text = text[:chars_to_show]

            # 光标
            if cursor and frame_idx % fps < fps // 2:
                display_text += "|"

            # 渲染帧
            img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 居中绘制
            bbox = draw.textbbox((0, 0), display_text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            x = (width - tw) // 2 + int(position[0] * width / 2)
            y = (height - th) // 2 + int(position[1] * height / 2)

            draw.text((x, y), display_text, fill=color_rgb + (255,), font=font)

            frame_path = os.path.join(frames_dir, f"frame_{frame_idx:04d}.png")
            img.save(frame_path)

        # 合成视频
        video_path = os.path.join(self.output_dir, f"{project_name}.mp4")
        self._frames_to_video(frames_dir, video_path, fps)

        # 创建剪映工程
        project = JyProject(project_name, width=width, height=height, overwrite=True)
        project.add_media_safe(video_path, 0, int(duration * 1e6), "VideoTrack")
        project.save()

        logger.info(f"  ✅ 打字机工程已创建: {project_name} ({total_frames}帧)")
        return {"status": "success", "project": project_name, "preset": "typewriter",
                "video": video_path, "frames": frames_dir}

    # ═══════════════════════════════════════════════════════════
    # 预设5: 渐变流光（PIL预渲染）
    # ═══════════════════════════════════════════════════════════

    def _gradient(self, text, project_name, duration, width, height,
                  font_size, color, position, gradient_colors=None,
                  speed=1.0, **kwargs):
        """
        渐变流光：文字颜色流动渐变（PIL预渲染帧序列→视频）

        Args:
            gradient_colors: 渐变颜色列表 [(R,G,B), ...]，默认金白渐变
            speed: 流动速度
        """
        if not PIL_OK:
            return {"status": "failed", "reason": "Pillow不可用，渐变效果需要PIL"}

        if gradient_colors is None:
            gradient_colors = [
                (255, 215, 0),   # 金色
                (255, 255, 255), # 白色
                (255, 100, 100), # 粉红
                (255, 255, 255), # 白色
            ]

        frames_dir = os.path.join(self.output_dir, f"{project_name}_frames")
        os.makedirs(frames_dir, exist_ok=True)

        fps = 30
        total_frames = int(duration * fps)

        font_path = self._find_font()
        font_size_px = int(font_size * width / 20)
        try:
            font = ImageFont.truetype(font_path, font_size_px) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        logger.info(f"  生成渐变流光帧序列: {total_frames}帧")

        for frame_idx in range(total_frames):
            t = frame_idx / fps * speed

            # 计算当前渐变偏移
            offset = (t * 0.5) % 1.0

            # 创建文字mask
            mask_img = Image.new("L", (width, height), 0)
            mask_draw = ImageDraw.Draw(mask_img)
            bbox = mask_draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = (width - tw) // 2 + int(position[0] * width / 2)
            ty = (height - th) // 2 + int(position[1] * height / 2)
            mask_draw.text((tx, ty), text, fill=255, font=font)

            # 创建渐变背景
            gradient = Image.new("RGB", (width, height), (0, 0, 0))
            grad_draw = ImageDraw.Draw(gradient)

            # 水平渐变流动
            for x in range(width):
                # 计算该位置的颜色
                pos = (x / width + offset) % 1.0
                color_idx = pos * (len(gradient_colors) - 1)
                idx = int(color_idx)
                frac = color_idx - idx
                idx = min(idx, len(gradient_colors) - 2)

                c1 = gradient_colors[idx]
                c2 = gradient_colors[idx + 1]
                r = int(c1[0] + (c2[0] - c1[0]) * frac)
                g = int(c1[1] + (c2[1] - c1[1]) * frac)
                b = int(c1[2] + (c2[2] - c1[2]) * frac)
                grad_draw.line([(x, 0), (x, height)], fill=(r, g, b))

            # 应用mask
            result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            result.paste(gradient, (0, 0), mask_img)

            frame_path = os.path.join(frames_dir, f"frame_{frame_idx:04d}.png")
            result.save(frame_path)

        # 合成视频
        video_path = os.path.join(self.output_dir, f"{project_name}.mp4")
        self._frames_to_video(frames_dir, video_path, fps)

        # 创建剪映工程
        project = JyProject(project_name, width=width, height=height, overwrite=True)
        project.add_media_safe(video_path, 0, int(duration * 1e6), "VideoTrack")
        project.save()

        logger.info(f"  ✅ 渐变流光工程已创建: {project_name} ({total_frames}帧)")
        return {"status": "success", "project": project_name, "preset": "gradient",
                "video": video_path, "frames": frames_dir}

    # ═══════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════

    def _find_font(self) -> Optional[str]:
        """查找可用中文字体"""
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
            r"C:\Windows\Fonts\msyhbd.ttc",    # 微软雅黑粗体
            r"C:\Windows\Fonts\simhei.ttf",    # 黑体
            r"C:\Windows\Fonts\simsun.ttc",    # 宋体
            r"C:\Windows\Fonts\simkai.ttf",    # 楷体
        ]
        for f in candidates:
            if os.path.exists(f):
                return f
        return None

    def _frames_to_video(self, frames_dir: str, output_path: str, fps: int = 30):
        """帧序列合成视频"""
        import subprocess
        ffmpeg = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
        if not os.path.exists(ffmpeg):
            ffmpeg = "ffmpeg"

        input_pattern = os.path.join(frames_dir, "frame_%04d.png")
        cmd = [
            ffmpeg, "-y",
            "-framerate", str(fps),
            "-i", input_pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            output_path
        ]
        subprocess.run(cmd, capture_output=True)
        return output_path if os.path.exists(output_path) else None

    def list_presets(self) -> List[Dict]:
        """列出所有可用预设"""
        return [
            {"name": "fade", "desc": "淡入淡出", "params": ["fade_in", "fade_out"]},
            {"name": "slide", "desc": "滑入滑出", "params": ["direction", "slide_in", "slide_out", "distance"]},
            {"name": "bounce", "desc": "弹性弹入", "params": ["bounce_in", "bounce_out", "scale_start", "scale_peak"]},
            {"name": "typewriter", "desc": "打字机效果", "params": ["chars_per_second", "cursor"]},
            {"name": "gradient", "desc": "渐变流光", "params": ["gradient_colors", "speed"]},
        ]


# ═══════════════════════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("文字字幕动画预设库 v1.0")
    logger.info("=" * 60)

    presets = TextAnimationPresets()

    logger.info(f"\n可用预设 ({len(presets.list_presets())}种):")
    for p in presets.list_presets():
        logger.info(f"  {p['name']:12s} — {p['desc']}")

    logger.info(f"\nPillow: {'✅' if PIL_OK else '❌'}")

    logger.info(f"\n使用示例:")
    logger.info(f"  presets = TextAnimationPresets()")
    logger.info(f"  presets.create('fade', '你好世界', duration=3.0)")
    logger.info(f"  presets.create('slide', '滑入文字', direction='left', duration=3.0)")
    logger.info(f"  presets.create('bounce', '弹入文字', duration=3.0)")
    logger.info(f"  presets.create('typewriter', '打字机效果', chars_per_second=8, duration=4.0)")
    logger.info(f"  presets.create('gradient', '渐变流光', duration=3.0)")
