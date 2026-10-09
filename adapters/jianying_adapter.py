"""
jianying_adapter.py - 剪映工程适配层 v1.0
封装 pyJianYingDraft 所有常用类和方法，ai-video-editor 应通过此层访问剪映能力，
不得直接 import pyJianYingDraft。

设计原则：
1. 所有 pyJianYingDraft 类在此 re-export，保持API兼容
2. 提供 JianyingDraft 高层封装类，简化常用操作
3. 统一处理路径、编码、异常
4. 未来切换剪映版本或替代方案时只需修改此层
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

# ── pyJianYingDraft 路径注入 ──────────────────────────────────
_JIANYING_SKILL = Path(r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor")
_VENDOR = str(_JIANYING_SKILL / "scripts" / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

# ── 核心类 re-export ──────────────────────────────────────────
from pyJianYingDraft.script_file import ScriptFile  # noqa: E402
from pyJianYingDraft.draft_folder import DraftFolder  # noqa: E402
from pyJianYingDraft.track import Track, TrackType  # noqa: E402
from pyJianYingDraft.video_segment import VideoSegment, Transition  # noqa: E402
from pyJianYingDraft.audio_segment import AudioSegment  # noqa: E402
from pyJianYingDraft.text_segment import TextSegment, TextStyle, TextBorder, TextShadow  # noqa: E402
from pyJianYingDraft.effect_segment import EffectSegment, FilterSegment  # noqa: E402
from pyJianYingDraft.local_materials import VideoMaterial, AudioMaterial  # noqa: E402
from pyJianYingDraft.time_util import Timerange, tim  # noqa: E402
from pyJianYingDraft.keyframe import Keyframe, KeyframeProperty, KeyframeList  # noqa: E402
from pyJianYingDraft.animation import (  # noqa: E402
    VideoAnimation, Text_animation, SegmentAnimations,
)
from pyJianYingDraft.segment import ClipSettings, MediaSegment, BaseSegment  # noqa: E402

# ── 元数据枚举 re-export ──────────────────────────────────────
from pyJianYingDraft.metadata import (  # noqa: E402
    IntroType, OutroType, GroupAnimationType,
    TextIntro, TextOutro, TextLoopAnim,
    VideoSceneEffectType, VideoCharacterEffectType, FilterType,
    AudioSceneEffectType, ToneEffectType, SpeechToSongType,
    AnimationMeta, EffectMeta, EffectParamInstance,
    FontType, MaskType, MaskMeta, TransitionType,
)
from pyJianYingDraft.metadata.effect_meta import EffectEnum  # noqa: E402

# ── 默认草稿目录 ──────────────────────────────────────────────
DEFAULT_DRAFTS_ROOT = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "JianyingPro", "User Data", "Projects", "com.lveditor.draft",
)


class JianyingDraft:
    """
    剪映草稿高层封装 - 简化常用操作

    用法:
        draft = JianyingDraft("我的视频", width=1080, height=1920)
        draft.add_video("clip.mp4", start=0, duration=5)
        draft.add_text("Hello", start=0, duration=3, y=-0.5)
        draft.save()
    """

    def __init__(self, name: str, width: int = 1080, height: int = 1920,
                 fps: int = 30, drafts_root: str = None):
        self.name = name
        self.width = width
        self.height = height
        self.fps = fps
        self.drafts_root = drafts_root or DEFAULT_DRAFTS_ROOT
        self.draft_path = os.path.join(self.drafts_root, name)

        # 创建草稿目录和ScriptFile
        os.makedirs(self.draft_path, exist_ok=True)
        self.script = ScriptFile(name, width, height, fps)
        self._tracks: Dict[str, Track] = {}
        self._next_track_index = 0

    def _get_or_create_track(self, track_type: TrackType) -> Track:
        """获取或创建指定类型的轨道"""
        key = track_type.name
        if key not in self._tracks:
            self.script.add_track(track_type, key)
            self._tracks[key] = self.script.tracks[key]
        return self._tracks[key]

    def add_video(self, file_path: str, start: float = 0, duration: float = None,
                  *, track_index: int = 0, scale: float = 1.0,
                  x: float = 0, y: float = 0, rotation: float = 0,
                  alpha: float = 1.0) -> VideoSegment:
        """
        添加视频/图片片段

        Args:
            file_path: 媒体文件路径
            start: 起始时间（秒）
            duration: 持续时间（秒，None=全长）
            track_index: 视频轨道索引（0=主轨，>0=画中画轨）
            scale/x/y/rotation/alpha: 变换参数
        """
        material = VideoMaterial(file_path)
        self.script.add_material(material)

        dur = duration or material.duration
        target_tr = Timerange(tim(start), tim(dur))
        source_tr = Timerange(0, tim(dur))
        seg = VideoSegment(material, target_tr, source_timerange=source_tr,
                           clip_settings=ClipSettings(
                               scale_x=scale, scale_y=scale,
                               transform_x=x, transform_y=y,
                               rotation=rotation, alpha=alpha,
                           ))

        if track_index == 0:
            track = self._get_or_create_track(TrackType.video)
        else:
            # 画中画轨道（video类型，不同名称）
            key = f"pip_{track_index}"
            if key not in self._tracks:
                self.script.add_track(TrackType.video, key, relative_index=track_index)
                self._tracks[key] = self.script.tracks[key]
            track = self._tracks[key]
        track.add_segment(seg)
        return seg

    def add_audio(self, file_path: str, start: float = 0, duration: float = None,
                  *, volume: float = 1.0, track_index: int = 0) -> AudioSegment:
        """添加音频片段"""
        material = AudioMaterial(file_path)
        self.script.add_material(material)

        dur = duration or material.duration
        target_tr = Timerange(tim(start), tim(dur))
        seg = AudioSegment(material, target_tr, volume=volume)

        key = f"audio_{track_index}"
        if key not in self._tracks:
            self.script.add_track(TrackType.audio, key)
            self._tracks[key] = self.script.tracks[key]
        track = self._tracks[key]
        track.add_segment(seg)
        return seg

    def add_text(self, text: str, start: float = 0, duration: float = 3,
                 *, x: float = 0, y: float = 0,
                 font_size: int = 48, color: Tuple[int, int, int] = (255, 255, 255),
                 align: int = 1,
                 track_index: int = 0) -> TextSegment:
        """添加文字片段"""
        style = TextStyle(
            size=font_size,
            color=color,
            align=align,
        )
        target_tr = Timerange(tim(start), tim(duration))
        seg = TextSegment(text, target_tr, style=style)
        seg.clip_settings = ClipSettings(transform_x=x, transform_y=y)

        track = self._get_or_create_track(TrackType.text)
        track.add_segment(seg)
        return seg

    def add_effect(self, effect_type: Union[VideoSceneEffectType, str],
                   start: float = 0, duration: float = 1,
                   *, params: List[Optional[float]] = None) -> EffectSegment:
        """添加全局特效"""
        if isinstance(effect_type, str):
            effect_type = getattr(VideoSceneEffectType, effect_type)
        target_tr = Timerange(tim(start), tim(duration))
        seg = EffectSegment(effect_type, target_tr, params)
        track = self._get_or_create_track(TrackType.effect)
        track.add_segment(seg)
        return seg

    def add_filter(self, filter_type: Union[FilterType, str],
                   start: float = 0, duration: float = 1,
                   *, intensity: float = 1.0) -> FilterSegment:
        """添加全局滤镜"""
        if isinstance(filter_type, str):
            filter_type = getattr(FilterType, filter_type)
        target_tr = Timerange(tim(start), tim(duration))
        seg = FilterSegment(filter_type, target_tr, intensity)
        track = self._get_or_create_track(TrackType.filter)
        track.add_segment(seg)
        return seg

    def add_animation(self, segment: MediaSegment,
                      anim_type: str = "in", anim_name: str = "渐显",
                      *, start_offset: float = 0, duration: float = 0.5):
        """
        给片段添加动画（入场/出场）

        Args:
            segment: 目标片段
            anim_type: "in" / "out"
            anim_name: 动画名称（对应IntroType/OutroType枚举）
            start_offset: 动画相对片段起始的偏移（秒）
            duration: 动画持续时间（秒）
        """
        if anim_type == "in":
            enum_cls = IntroType
        else:
            enum_cls = OutroType
        anim_enum = getattr(enum_cls, anim_name)
        anim = VideoAnimation(anim_enum, tim(start_offset), tim(duration))
        if segment.animations is None:
            segment.animations = SegmentAnimations()
        segment.animations.add_animation(anim)

    def add_keyframe(self, segment: VideoSegment,
                     property: KeyframeProperty,
                     time_offset: float, value: float,
                     *, curve_type: str = "Line",
                     left_control: Tuple[float, float] = (0, 0),
                     right_control: Tuple[float, float] = (0, 0)):
        """给视频片段添加关键帧"""
        if segment.keyframes is None:
            segment.keyframes = []
        # 查找或创建KeyframeList
        kf_list = None
        for kfl in segment.keyframes:
            if kfl.keyframe_property == property:
                kf_list = kfl
                break
        if kf_list is None:
            kf_list = KeyframeList(property)
            segment.keyframes.append(kf_list)
        kf_list.add_keyframe(tim(time_offset), value,
                             curve_type=curve_type,
                             left_control=left_control,
                             right_control=right_control)

    def save(self) -> Dict[str, Any]:
        """保存草稿到磁盘，返回状态字典"""
        draft_content_path = os.path.join(self.draft_path, "draft_content.json")
        draft_info_path = os.path.join(self.draft_path, "draft_info.json")

        try:
            with open(draft_content_path, "w", encoding="utf-8") as f:
                f.write(self.script.dumps())

            # draft_info.json
            info = {
                "draft_name": self.name,
                "draft_id": os.path.basename(self.draft_path),
                "width": self.width,
                "height": self.height,
                "fps": self.fps,
                "create_time": int(__import__("time").time() * 1000),
            }
            with open(draft_info_path, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)

            return {"status": "SUCCESS", "path": self.draft_path}
        except Exception as e:
            return {"status": "FAILED", "error": str(e), "path": self.draft_path}


# 延迟import json（避免循环）
import json  # noqa: E402


__all__ = [
    # 核心类
    "JianyingDraft", "ScriptFile", "DraftFolder",
    "Track", "TrackType",
    "VideoSegment", "AudioSegment", "TextSegment",
    "EffectSegment", "FilterSegment", "Transition",
    "VideoMaterial", "AudioMaterial",
    "Timerange", "tim",
    "Keyframe", "KeyframeProperty", "KeyframeList",
    "VideoAnimation", "Text_animation", "SegmentAnimations",
    "ClipSettings", "MediaSegment", "BaseSegment",
    "TextStyle", "TextBorder",
    # 枚举
    "IntroType", "OutroType", "TextIntro", "TextOutro", "TextLoopAnim",
    "VideoSceneEffectType", "VideoCharacterEffectType", "FilterType",
    "EffectEnum", "AnimationMeta",
    "AudioSceneEffectType", "ToneEffectType", "SpeechToSongType",
    # 常量
    "DEFAULT_DRAFTS_ROOT",
]
