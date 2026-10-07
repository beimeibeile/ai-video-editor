import sys
sys.path.insert(0, r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\ai-video-editor")
from adapters.jianying_adapter import (
    JianyingDraft, ScriptFile, DraftFolder, Track, TrackType,
    VideoSegment, AudioSegment, TextSegment, EffectSegment, FilterSegment,
    VideoMaterial, AudioMaterial, Timerange, tim,
    Keyframe, KeyframeProperty, KeyframeList,
    VideoAnimation, SegmentAnimations, ClipSettings, TextStyle,
    IntroType, OutroType, VideoSceneEffectType, FilterType,
)
print("所有核心类导入成功")
free_intros = [e for e in IntroType if not e.value.is_vip]
print(f"IntroType 免费入场动画: {len(free_intros)} 种")
methods = [m for m in dir(JianyingDraft) if not m.startswith("_")]
print(f"JianyingDraft 方法: {methods}")
