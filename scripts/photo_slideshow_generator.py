# -*- coding: utf-8 -*-
"""
照片轮播短视频生成器 v1.0
Photo Slideshow Video Generator

从照片目录自动生成带配音/配乐/文字/转场/特效的剪映工程。

用法：
    from photo_slideshow_generator import PhotoSlideshowGenerator, StylePreset

    gen = PhotoSlideshowGenerator(
        photo_dir=r"C:/path/to/photos",
        style=StylePreset.FASHION_OOTD,
    )
    result = gen.generate("我的视频")
    logger.info(result["draft_path"])
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# 路径配置
RUNTIME_SCRIPTS = r"D:\DobaoWork_Project\Ai_Video_Editor\ai-video-editor-runtime\scripts"
SKILL_SCRIPTS = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\ai-video-editor\scripts"
JY_VENDOR = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor\scripts\vendor"

for p in [RUNTIME_SCRIPTS, SKILL_SCRIPTS, JY_VENDOR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pyJianYingDraft as draft
from pyJianYingDraft import Timerange, TrackType
from pyJianYingDraft import VideoSegment, VideoMaterial, AudioSegment, AudioMaterial
from pyJianYingDraft import TextSegment, TextStyle, TextBorder
from pyJianYingDraft.keyframe import KeyframeProperty as KP

try:
    from tts_executor import TTSExecutor
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    from jianying_effect_api import JianyingEffectAPI
    EFFECT_API_AVAILABLE = True
except ImportError:
    EFFECT_API_AVAILABLE = False


# ==================== 风格预设 ====================

@dataclass
class StylePreset:
    """视频风格预设"""
    name: str
    photo_count: int = 8
    photo_duration: float = 2.0          # 每张照片时长（秒）
    filter_name: str = ""                # 滤镜名称
    filter_intensity: float = 0.6        # 滤镜强度
    scene_effects: List[Dict] = field(default_factory=list)  # 场景特效
    transition_name: str = "叠化"        # 转场名称
    intro_animation: str = "渐显"        # 入场动画
    outro_animation: str = ""            # 出场动画
    ken_burns: bool = True               # Ken Burns缓慢推拉
    title_text: str = ""                 # 标题文字
    subtitle_texts: List[str] = field(default_factory=list)  # 字幕
    voice_text: str = ""                 # 配音文案
    voice_character: str = "Serena"      # 配音音色
    voice_emotion: str = "calm"          # 配音情绪
    bgm_path: str = ""                   # BGM路径
    bgm_volume: float = 0.25             # BGM音量
    title_font_size: float = 10.0        # 标题字号
    subtitle_font_size: float = 5.0      # 字幕字号

    # 预设常量
    FASHION_OOTD = None  # 下方定义
    VLOG_DAILY = None
    CINEMATIC = None
    TRAVEL = None
    FOOD = None


# 常用风格预设
StylePreset.FASHION_OOTD = StylePreset(
    name="时尚OOTD",
    photo_count=8, photo_duration=1.8,
    filter_name="质感电影", filter_intensity=0.65,
    scene_effects=[
        {"name": "故障", "start": 0.2, "duration": 0.3},
        {"name": "色差", "start": 3.6, "duration": 0.2},
        {"name": "闪白", "start": 7.2, "duration": 0.15},
        {"name": "光晕", "start": 9.0, "duration": 1.0},
        {"name": "震动", "start": 11.0, "duration": 0.3},
    ],
    transition_name="上下翻页",
    intro_animation="动感放大",
    title_text="时尚穿搭日记",
    subtitle_texts=["秋日穿搭", "街头风格", "自信出街"],
    voice_text="皮衣搭配豹纹围巾，秋日的街头，风把头发吹起，每一步都是自信的节奏。",
    voice_character="Vivian", voice_emotion="自信",
    bgm_volume=0.2,
)

StylePreset.VLOG_DAILY = StylePreset(
    name="治愈Vlog",
    photo_count=8, photo_duration=2.5,
    filter_name="清新", filter_intensity=0.5,
    scene_effects=[
        {"name": "光晕", "start": 0.5, "duration": 1.5},
        {"name": "闪白", "start": 10.0, "duration": 0.2},
    ],
    transition_name="叠化",
    intro_animation="渐显",
    title_text="和你一起看海",
    subtitle_texts=["治愈日常", "慢生活", "记录美好"],
    voice_text="有人说，看海的时候时间会变慢。和喜欢的人一起，连风都是温柔的。",
    voice_character="Serena", voice_emotion="温柔",
    bgm_volume=0.3,
)

StylePreset.CINEMATIC = StylePreset(
    name="电影感情绪",
    photo_count=8, photo_duration=2.8,
    filter_name="暗调电影", filter_intensity=0.7,
    scene_effects=[
        {"name": "光晕", "start": 0.5, "duration": 1.5},
        {"name": "闪白", "start": 8.0, "duration": 0.2},
        {"name": "色差", "start": 14.0, "duration": 0.3},
    ],
    transition_name="叠化",
    intro_animation="放大",
    title_text="海的尽头是你",
    subtitle_texts=["情绪短片", "电影感", "故事感"],
    voice_text="我们站在海的这一边，望向看不见的尽头。夕阳把海面染成金色，而你比夕阳更耀眼。",
    voice_character="Dylan", voice_emotion="凝重",
    bgm_volume=0.28,
)

StylePreset.TRAVEL = StylePreset(
    name="旅行记录",
    photo_count=10, photo_duration=2.2,
    filter_name="清新", filter_intensity=0.55,
    scene_effects=[
        {"name": "光晕", "start": 0.3, "duration": 1.0},
        {"name": "闪白", "start": 6.0, "duration": 0.15},
        {"name": "震动", "start": 12.0, "duration": 0.3},
    ],
    transition_name="叠化",
    intro_animation="向上滑动",
    title_text="旅行日记",
    subtitle_texts=["在路上", "风景", "回忆"],
    voice_text="每一次出发都是新的故事，每一张照片都是时光的标本。",
    voice_character="Ryan", voice_emotion="轻松",
    bgm_volume=0.25,
)


# ==================== 生成器主类 ====================

class PhotoSlideshowGenerator:
    """照片轮播短视频生成器"""

    def __init__(self, photo_dir: str, output_dir: str = None,
                 style: StylePreset = None, seed: int = 2026):
        """
        Args:
            photo_dir: 照片目录
            output_dir: 剪映草稿输出目录（默认自动检测）
            style: 风格预设
            seed: 随机种子（保证照片选择可复现）
        """
        self.photo_dir = photo_dir
        self.output_dir = output_dir or self._detect_drafts_dir()
        self.style = style or StylePreset.VLOG_DAILY
        self.seed = seed
        self.effect_api = JianyingEffectAPI() if EFFECT_API_AVAILABLE else None
        self.tts = TTSExecutor() if TTS_AVAILABLE else None

    def _detect_drafts_dir(self) -> str:
        """自动检测剪映草稿目录"""
        candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft"),
            r"D:\JianyingProDrafts\JianyingPro Drafts",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return candidates[0]

    def _scan_photos(self) -> List[str]:
        """扫描照片目录，返回照片路径列表"""
        exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        photos = []
        for f in os.listdir(self.photo_dir):
            ext = os.path.splitext(f)[1].lower()
            if ext in exts:
                photos.append(os.path.join(self.photo_dir, f))
        return sorted(photos)

    def _select_photos(self, photos: List[str]) -> List[str]:
        """选择照片（随机洗牌后取前N张）"""
        random.seed(self.seed)
        shuffled = photos.copy()
        random.shuffle(shuffled)
        return shuffled[:self.style.photo_count]

    def _find_enum(self, enum_cls, name: str):
        """按名称查找枚举值（支持AnimationMeta.title和普通.name）"""
        if not name:
            return None
        # 优先用from_name（如果有）
        if hasattr(enum_cls, "from_name"):
            try:
                return enum_cls.from_name(name)
            except Exception:
                pass
        # 回退：遍历查找
        for member in enum_cls:
            val = member.value
            member_name = getattr(val, "title", None) or getattr(val, "name", None) or str(val)
            if member_name == name:
                return member
        return None

    def _add_ken_burns(self, segment: VideoSegment, duration_us: int, zoom_in: bool = True):
        """添加Ken Burns缓慢推拉效果"""
        start_scale = 1.0
        end_scale = 1.12 if zoom_in else 0.92
        segment.add_keyframe(KP.uniform_scale, 0, start_scale)
        segment.add_keyframe(KP.uniform_scale, duration_us, end_scale,
                             curve_type="Bezier",
                             left_control=(0.42, 0.0),
                             right_control=(0.58, 1.0))

    def _generate_voice(self, text: str, character: str, emotion: str,
                        output_path: str) -> Optional[str]:
        """生成TTS配音"""
        if not self.tts or not text:
            return None
        try:
            result = self.tts.synthesize(text, character, emotion, output_path)
            return result
        except Exception as e:
            logger.error(f"  ⚠️ TTS生成失败: {e}")
            return None

    def _probe_audio_duration(self, path: str) -> int:
        """探测音频时长（微秒）"""
        try:
            import subprocess
            import json
            ffprobe = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"
            if not os.path.exists(ffprobe):
                ffprobe = "ffprobe"
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "json", path],
                capture_output=True, text=True, timeout=10
            )
            data = json.loads(result.stdout)
            return int(float(data["format"]["duration"]) * 1_000_000)
        except Exception:
            return 0

    def generate(self, draft_name: str, photos: List[str] = None) -> Dict:
        """
        生成剪映工程

        Args:
            draft_name: 工程名称
            photos: 自定义照片列表（为None时自动扫描选择）

        Returns:
            dict: {draft_path, photo_count, duration, voice_path, bgm_added}
        """
        style = self.style

        # 1. 选择照片
        if photos is None:
            all_photos = self._scan_photos()
            photos = self._select_photos(all_photos)
        if not photos:
            raise ValueError(f"未找到照片: {self.photo_dir}")

        # 2. 计算总时长
        total_us = int(len(photos) * style.photo_duration * 1_000_000)
        photo_dur_us = int(style.photo_duration * 1_000_000)

        # 3. 生成TTS配音
        voice_path = None
        voice_us = 0
        if style.voice_text and self.tts:
            voice_dir = os.path.join(os.path.dirname(self.photo_dir), "audio")
            os.makedirs(voice_dir, exist_ok=True)
            voice_path = os.path.join(voice_dir, f"vo_{draft_name}.mp3")
            voice_path = self._generate_voice(
                style.voice_text, style.voice_character,
                style.voice_emotion, voice_path
            )
            if voice_path:
                voice_us = self._probe_audio_duration(voice_path)
                logger.info(f"  ✅ 配音: {voice_us/1e6:.1f}秒")

        # 4. 创建工程
        df = draft.DraftFolder(self.output_dir)
        script = df.create_draft(draft_name, 1080, 1920, allow_replace=True)
        script.add_track(TrackType.video, "VideoTrack")
        script.add_track(TrackType.effect, "EffectTrack")
        script.add_track(TrackType.filter, "FilterTrack")
        script.add_track(TrackType.text, "TextTrack")
        script.add_track(TrackType.text, "TextTrack2")
        script.add_track(TrackType.audio, "VoiceTrack")
        script.add_track(TrackType.audio, "BgmTrack")

        # 5. 添加视频片段
        current_us = 0
        for i, photo_path in enumerate(photos):
            material = VideoMaterial(photo_path)
            seg = VideoSegment(material, Timerange(current_us, photo_dur_us))

            # Ken Burns
            if style.ken_burns:
                self._add_ken_burns(seg, photo_dur_us, zoom_in=(i % 2 == 0))

            # 入场动画
            if style.intro_animation and self.effect_api:
                self.effect_api.apply_animation(seg, "in", style.intro_animation)

            # 出场动画（末张）
            if style.outro_animation and self.effect_api and i == len(photos) - 1:
                self.effect_api.apply_animation(seg, "out", style.outro_animation)

            # 转场
            if style.transition_name and self.effect_api and i > 0:
                self.effect_api.apply_transition(seg, style.transition_name)

            script.add_segment(seg, "VideoTrack")
            current_us += photo_dur_us

        # 6. 添加滤镜
        if style.filter_name and self.effect_api:
            self.effect_api.apply_filter(
                script, style.filter_name, 0, total_us / 1e6,
                style.filter_intensity
            )
            logger.info(f"  ✅ 滤镜: {style.filter_name}")

        # 7. 添加场景特效
        if self.effect_api:
            for eff in style.scene_effects:
                if eff["start"] < total_us / 1e6:
                    self.effect_api.apply_scene_effect(
                        script, eff["name"], eff["start"],
                        eff.get("duration", 0.3)
                    )

        # 8. 添加标题文字
        if style.title_text:
            title_style = TextStyle(
                size=style.title_font_size,
                bold=True,
                color=(1.0, 1.0, 1.0),
                align=1,
                alpha=0.95,
            )
            title_border = TextBorder(color=(0.0, 0.0, 0.0), width=30.0, alpha=0.8)
            title_seg = TextSegment(
                style.title_text,
                Timerange(0, min(3_000_000, total_us)),
                style=title_style, border=title_border,
            )
            title_seg.clip_settings.transform_y = -0.65
            script.add_segment(title_seg, "TextTrack")

        # 9. 添加字幕
        if style.subtitle_texts:
            sub_dur = total_us // (len(style.subtitle_texts) + 1)
            for i, text in enumerate(style.subtitle_texts):
                sub_style = TextStyle(
                    size=style.subtitle_font_size,
                    bold=False,
                    color=(1.0, 1.0, 1.0),
                    align=1,
                    alpha=0.9,
                )
                sub_border = TextBorder(color=(0.0, 0.0, 0.0), width=20.0, alpha=0.7)
                start = sub_dur * (i + 1)
                sub_seg = TextSegment(
                    text,
                    Timerange(start, min(sub_dur, 2_500_000)),
                    style=sub_style, border=sub_border,
                )
                sub_seg.clip_settings.transform_y = 0.55
                script.add_segment(sub_seg, "TextTrack2")

        # 10. 添加配音
        if voice_path and voice_us > 0:
            vo_material = AudioMaterial(voice_path)
            vo_dur = min(voice_us, total_us - 500_000)
            vo_seg = AudioSegment(vo_material, Timerange(300_000, vo_dur))
            vo_seg.volume = 1.0
            script.add_segment(vo_seg, "VoiceTrack")

        # 11. 添加BGM
        bgm_added = False
        if style.bgm_path and os.path.exists(style.bgm_path):
            bgm_material = AudioMaterial(style.bgm_path)
            bgm_dur = min(total_us, bgm_material.duration)
            bgm_seg = AudioSegment(bgm_material, Timerange(0, bgm_dur))
            bgm_seg.volume = style.bgm_volume
            bgm_seg.add_keyframe(0, 0.0)
            bgm_seg.add_keyframe(500_000, style.bgm_volume)
            bgm_seg.add_keyframe(max(0, bgm_dur - 800_000), style.bgm_volume)
            bgm_seg.add_keyframe(bgm_dur, 0.0)
            script.add_segment(bgm_seg, "BgmTrack")
            bgm_added = True

        # 12. 保存
        script.save()
        draft_path = os.path.join(self.output_dir, draft_name)

        return {
            "draft_path": draft_path,
            "draft_name": draft_name,
            "photo_count": len(photos),
            "duration_sec": total_us / 1e6,
            "voice_path": voice_path,
            "voice_duration_sec": voice_us / 1e6,
            "bgm_added": bgm_added,
            "style": style.name,
        }


# ==================== 批量生成 ====================

def generate_multi_style(photo_dir: str, styles: List[Tuple[str, StylePreset]],
                         output_dir: str = None, seed: int = 2026) -> List[Dict]:
    """
    批量生成多种风格的视频

    Args:
        photo_dir: 照片目录
        styles: [(工程名, 风格预设), ...]
        output_dir: 输出目录
        seed: 随机种子

    Returns:
        生成结果列表
    """
    results = []
    for name, style in styles:
        logger.info(f"\n{'='*60}")
        logger.info(f"生成: {name} ({style.name})")
        logger.info(f"{'='*60}")
        gen = PhotoSlideshowGenerator(photo_dir, output_dir, style, seed)
        result = gen.generate(name)
        results.append(result)
        logger.info(f"  ✅ 完成: {result['draft_path']}")
    return results


# ==================== CLI ====================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="照片轮播短视频生成器")
    parser.add_argument("--photo_dir", required=True, help="照片目录")
    parser.add_argument("--name", default="照片视频", help="工程名称")
    parser.add_argument("--style", default="vlog",
                        choices=["fashion", "vlog", "cinematic", "travel"],
                        help="风格预设")
    parser.add_argument("--output", default=None, help="输出目录")
    parser.add_argument("--count", type=int, default=8, help="照片数量")
    args = parser.parse_args()

    style_map = {
        "fashion": StylePreset.FASHION_OOTD,
        "vlog": StylePreset.VLOG_DAILY,
        "cinematic": StylePreset.CINEMATIC,
        "travel": StylePreset.TRAVEL,
    }
    style = style_map[args.style]
    style.photo_count = args.count

    gen = PhotoSlideshowGenerator(args.photo_dir, args.output, style)
    result = gen.generate(args.name)
    logger.info(f"\n✅ 生成完成: {result['draft_path']}")
    logger.info(f"   照片: {result['photo_count']}张, 时长: {result['duration_sec']:.1f}秒")
