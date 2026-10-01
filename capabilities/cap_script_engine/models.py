"""
剧本引擎数据模型
Script → Scene → Shot 三层结构
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class VideoGenre(str, Enum):
    """视频类型"""
    EXPLORATION = "探店"          # 探店/美食
    TALKING = "口播"              # 口播/知识分享
    ECOMMERCE = "带货"            # 电商带货
    VLOG = "Vlog"                # 生活记录
    TUTORIAL = "教程"            # 教程/技能
    STORY = "剧情"               # 剧情/短剧
    PROMO = "宣传"               # 产品宣传
    CUSTOM = "自定义"


class Emotion(str, Enum):
    """情绪节奏"""
    HOOK = "钩子"        # 开头抓人
    TENSION = "紧张"     # 制造悬念
    RELIEF = "舒缓"      # 放松过渡
    CLIMAX = "高潮"      # 情绪顶点
    RESOLUTION = "收尾"  # 总结号召
    CALM = "平静"        # 平稳叙述


class ShotSize(str, Enum):
    """景别"""
    CLOSEUP = "特写"
    MEDIUM = "中景"
    WIDE = "全景"
    POV = "主观视角"
    AERIAL = "航拍"


@dataclass
class Shot:
    """单个镜头"""
    shot_id: str
    start_time: float          # 起始时间(秒)
    duration: float            # 时长(秒)
    shot_size: ShotSize = ShotSize.MEDIUM
    camera_move: str = "固定"  # 机位运动
    description: str = ""      # 画面描述
    subtitle: str = ""         # 字幕文案
    voiceover: str = ""        # 旁白
    effect_hint: str = ""      # 特效建议(供调度器)
    bgm_hint: str = ""         # 配乐建议
    emotion: Emotion = Emotion.CALM
    visual_ref: str = ""       # 画面参考/AI生成提示词


@dataclass
class Scene:
    """场景/幕"""
    scene_id: str
    title: str
    start_time: float
    duration: float
    emotion: Emotion = Emotion.CALM
    description: str = ""
    shots: List[Shot] = field(default_factory=list)
    transition_in: str = "硬切"   # 入场转场
    transition_out: str = "硬切"  # 出场转场

    @property
    def end_time(self) -> float:
        return self.start_time + self.duration


@dataclass
class Script:
    """完整剧本"""
    title: str
    genre: VideoGenre = VideoGenre.CUSTOM
    target_audience: str = ""
    total_duration: float = 60.0
    aspect_ratio: str = "9:16"    # 9:16竖屏 / 16:9横屏 / 1:1方形
    style: str = "快节奏"          # 整体风格
    hook: str = ""                # 钩子文案(前3秒)
    cta: str = ""                 # 号召行动(结尾)
    scenes: List[Scene] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    bgm_mood: str = ""            # 整体配乐情绪
    notes: str = ""               # 备注

    @property
    def total_shots(self) -> int:
        return sum(len(s.shots) for s in self.scenes)

    @property
    def actual_duration(self) -> float:
        return sum(s.duration for s in self.scenes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "genre": self.genre.value,
            "target_audience": self.target_audience,
            "total_duration": self.total_duration,
            "aspect_ratio": self.aspect_ratio,
            "style": self.style,
            "hook": self.hook,
            "cta": self.cta,
            "scenes": [
                {
                    "scene_id": s.scene_id,
                    "title": s.title,
                    "start_time": s.start_time,
                    "duration": s.duration,
                    "emotion": s.emotion.value,
                    "description": s.description,
                    "transition_in": s.transition_in,
                    "transition_out": s.transition_out,
                    "shots": [
                        {
                            "shot_id": sh.shot_id,
                            "start_time": sh.start_time,
                            "duration": sh.duration,
                            "shot_size": sh.shot_size.value,
                            "camera_move": sh.camera_move,
                            "description": sh.description,
                            "subtitle": sh.subtitle,
                            "voiceover": sh.voiceover,
                            "effect_hint": sh.effect_hint,
                            "emotion": sh.emotion.value,
                            "visual_ref": sh.visual_ref,
                        } for sh in s.shots
                    ]
                } for s in self.scenes
            ],
            "keywords": self.keywords,
            "bgm_mood": self.bgm_mood,
        }

    def to_markdown(self) -> str:
        """导出为Markdown可读格式"""
        lines = [
            f"# {self.title}",
            f"",
            f"- **类型**: {self.genre.value}",
            f"- **目标受众**: {self.target_audience}",
            f"- **时长**: {self.total_duration:.0f}秒",
            f"- **画幅**: {self.aspect_ratio}",
            f"- **风格**: {self.style}",
            f"- **关键词**: {', '.join(self.keywords)}",
            f"",
            f"## 钩子(前3秒)",
            f"> {self.hook}",
            f"",
        ]
        for scene in self.scenes:
            lines.append(f"## {scene.title} ({scene.start_time:.1f}s-{scene.end_time:.1f}s, {scene.duration:.1f}s)")
            lines.append(f"*情绪: {scene.emotion.value} | 转场: {scene.transition_in}→{scene.transition_out}*")
            lines.append(f"")
            lines.append(scene.description)
            lines.append(f"")
            for shot in scene.shots:
                lines.append(f"### {shot.shot_id} [{shot.shot_size.value}] {shot.start_time:.1f}s+{shot.duration:.1f}s")
                lines.append(f"- 画面: {shot.description}")
                if shot.subtitle:
                    lines.append(f"- 字幕: **{shot.subtitle}**")
                if shot.voiceover:
                    lines.append(f"- 旁白: {shot.voiceover}")
                if shot.effect_hint:
                    lines.append(f"- 特效: {shot.effect_hint}")
                lines.append(f"")
        lines.append(f"## 号召行动")
        lines.append(f"> {self.cta}")
        return "\n".join(lines)
