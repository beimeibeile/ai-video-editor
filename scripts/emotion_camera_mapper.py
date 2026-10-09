"""
情绪-镜头映射引擎 v1.0
建立情绪→运镜→特效→字幕风格→BGM风格的完整映射表

覆盖34种常见情绪，每种情绪提供明确的镜头语言方案。
用于script_understanding_engine和instruction_translator的镜头决策。

使用方式：
    from emotion_camera_mapper import EmotionCameraMapper
    mapper = EmotionCameraMapper()
    plan = mapper.get_camera_plan("紧张", intensity=0.8)
    print(plan["camera_moves"])  # 运镜方案
    print(plan["effects"])       # 特效方案
    print(plan["subtitle_style"]) # 字幕风格
"""

import logging
logger = logging.getLogger(__name__)

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class EmotionCameraPlan:
    """情绪对应的镜头方案"""
    emotion: str
    intensity: float  # 0.0-1.0
    camera_moves: List[str] = field(default_factory=list)  # 运镜类型
    camera_intensity: str = "medium"  # low/medium/high
    effects: List[str] = field(default_factory=list)  # 特效类型
    transitions: List[str] = field(default_factory=list)  # 转场类型
    subtitle_style: str = "minimal"  # 字幕风格
    subtitle_animation: str = "渐显"  # 字幕动画
    bgm_mood: str = "neutral"  # BGM情绪
    color_grading: str = "natural"  # 调色风格
    shot_duration: str = "medium"  # 镜头时长 short/medium/long
    description: str = ""


class EmotionCameraMapper:
    """情绪-镜头映射引擎"""

    def __init__(self):
        self.emotion_map = self._build_emotion_map()

    def _build_emotion_map(self) -> Dict[str, Dict]:
        """构建34种情绪的完整映射表"""
        return {
            # ===== 积极情绪 =====
            "开心": {
                "camera_moves": ["推近", "轻微晃动", "环绕"],
                "camera_intensity": "medium",
                "effects": ["闪白", "柔光"],
                "transitions": ["闪白", "淡入淡出"],
                "subtitle_style": "fun",
                "subtitle_animation": "弹入",
                "bgm_mood": "欢快",
                "color_grading": "明亮暖调",
                "shot_duration": "short",
                "description": "轻松愉快，节奏明快",
            },
            "兴奋": {
                "camera_moves": ["快速推近", "剧烈晃动", "快速变焦"],
                "camera_intensity": "high",
                "effects": ["闪白", "震动", "光效"],
                "transitions": ["闪白", "快速切换"],
                "subtitle_style": "fun",
                "subtitle_animation": "弹性伸缩",
                "bgm_mood": "激昂",
                "color_grading": "高饱和暖调",
                "shot_duration": "short",
                "description": "高度兴奋，节奏极快",
            },
            "惊喜": {
                "camera_moves": ["快速推近", "轻微震动", "定格"],
                "camera_intensity": "high",
                "effects": ["闪白", "放大", "光效"],
                "transitions": ["闪白", "突然切入"],
                "subtitle_style": "fun",
                "subtitle_animation": "弹出",
                "bgm_mood": "惊喜",
                "color_grading": "明亮",
                "shot_duration": "short",
                "description": "意外惊喜，瞬间爆发",
            },
            "得意": {
                "camera_moves": ["缓慢推近", "环绕", "仰拍"],
                "camera_intensity": "medium",
                "effects": ["柔光", "光晕"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "epic",
                "subtitle_animation": "放大",
                "bgm_mood": "自信",
                "color_grading": "暖调",
                "shot_duration": "medium",
                "description": "自信得意，略带炫耀",
            },
            "满足": {
                "camera_moves": ["缓慢拉远", "缓慢平移", "固定"],
                "camera_intensity": "low",
                "effects": ["柔光", "暖光"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "warm",
                "subtitle_animation": "渐显",
                "bgm_mood": "温馨",
                "color_grading": "暖调",
                "shot_duration": "long",
                "description": "心满意足，平静温暖",
            },
            "感动": {
                "camera_moves": ["缓慢推近", "轻微晃动", "固定"],
                "camera_intensity": "low",
                "effects": ["柔光", "光晕", "暖光"],
                "transitions": ["淡入淡出", "叠化"],
                "subtitle_style": "warm",
                "subtitle_animation": "逐字显影",
                "bgm_mood": "感人",
                "color_grading": "暖调柔光",
                "shot_duration": "long",
                "description": "深情感动，节奏舒缓",
            },
            "期待": {
                "camera_moves": ["缓慢推近", "轻微晃动", "聚焦"],
                "camera_intensity": "medium",
                "effects": ["柔光", "聚焦"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "minimal",
                "subtitle_animation": "打字机",
                "bgm_mood": "期待",
                "color_grading": "自然",
                "shot_duration": "medium",
                "description": "充满期待，略带紧张",
            },
            "轻松": {
                "camera_moves": ["缓慢平移", "轻微晃动", "固定"],
                "camera_intensity": "low",
                "effects": ["柔光"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "轻松",
                "color_grading": "明亮自然",
                "shot_duration": "medium",
                "description": "轻松自在，节奏平稳",
            },
            "治愈": {
                "camera_moves": ["缓慢拉远", "缓慢平移", "环绕"],
                "camera_intensity": "low",
                "effects": ["柔光", "暖光", "光晕"],
                "transitions": ["淡入淡出", "叠化"],
                "subtitle_style": "warm",
                "subtitle_animation": "渐显",
                "bgm_mood": "治愈",
                "color_grading": "暖调柔光",
                "shot_duration": "long",
                "description": "温暖治愈，节奏舒缓",
            },

            # ===== 消极情绪 =====
            "悲伤": {
                "camera_moves": ["缓慢拉远", "缓慢下移", "固定"],
                "camera_intensity": "low",
                "effects": ["暗角", "冷调", "模糊"],
                "transitions": ["淡入淡出", "叠化"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "悲伤",
                "color_grading": "冷调低饱和",
                "shot_duration": "long",
                "description": "悲伤难过，节奏缓慢",
            },
            "难过": {
                "camera_moves": ["缓慢拉远", "轻微晃动", "固定"],
                "camera_intensity": "low",
                "effects": ["暗角", "冷调"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "难过",
                "color_grading": "冷调",
                "shot_duration": "long",
                "description": "难过失落，节奏偏慢",
            },
            "委屈": {
                "camera_moves": ["缓慢推近", "轻微晃动", "仰拍"],
                "camera_intensity": "low",
                "effects": ["柔光", "暗角"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "warm",
                "subtitle_animation": "渐显",
                "bgm_mood": "委屈",
                "color_grading": "偏冷",
                "shot_duration": "medium",
                "description": "委屈可怜，令人同情",
            },
            "愤怒": {
                "camera_moves": ["快速推近", "剧烈晃动", "快速变焦"],
                "camera_intensity": "high",
                "effects": ["震动", "闪白", "高对比"],
                "transitions": ["闪白", "快速切换", "硬切"],
                "subtitle_style": "epic",
                "subtitle_animation": "弹出",
                "bgm_mood": "愤怒",
                "color_grading": "高对比暖红",
                "shot_duration": "short",
                "description": "愤怒爆发，节奏极快",
            },
            "紧张": {
                "camera_moves": ["快速推近", "剧烈晃动", "手持感"],
                "camera_intensity": "high",
                "effects": ["震动", "闪白", "模糊"],
                "transitions": ["快速切换", "硬切"],
                "subtitle_style": "minimal",
                "subtitle_animation": "打字机",
                "bgm_mood": "紧张",
                "color_grading": "高对比冷调",
                "shot_duration": "short",
                "description": "紧张刺激，节奏快速",
            },
            "恐惧": {
                "camera_moves": ["缓慢推近", "剧烈晃动", "手持感"],
                "camera_intensity": "high",
                "effects": ["震动", "暗角", "模糊", "冷调"],
                "transitions": ["快速切换", "突然切入"],
                "subtitle_style": "minimal",
                "subtitle_animation": "打字机",
                "bgm_mood": "恐怖",
                "color_grading": "冷调低饱和",
                "shot_duration": "short",
                "description": "恐惧不安，节奏急促",
            },
            "焦虑": {
                "camera_moves": ["快速平移", "剧烈晃动", "手持感"],
                "camera_intensity": "high",
                "effects": ["震动", "模糊"],
                "transitions": ["快速切换"],
                "subtitle_style": "minimal",
                "subtitle_animation": "打字机",
                "bgm_mood": "焦虑",
                "color_grading": "高对比",
                "shot_duration": "short",
                "description": "焦虑不安，节奏紊乱",
            },
            "尴尬": {
                "camera_moves": ["轻微晃动", "缓慢拉远", "固定"],
                "camera_intensity": "medium",
                "effects": ["轻微震动"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "fun",
                "subtitle_animation": "渐显",
                "bgm_mood": "尴尬",
                "color_grading": "自然",
                "shot_duration": "medium",
                "description": "尴尬无语，略带幽默",
            },
            "失望": {
                "camera_moves": ["缓慢拉远", "缓慢下移", "固定"],
                "camera_intensity": "low",
                "effects": ["暗角", "冷调"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "失望",
                "color_grading": "冷调低饱和",
                "shot_duration": "long",
                "description": "失望失落，节奏缓慢",
            },
            "痛苦": {
                "camera_moves": ["剧烈晃动", "快速推近", "手持感"],
                "camera_intensity": "high",
                "effects": ["震动", "模糊", "高对比"],
                "transitions": ["快速切换", "硬切"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "痛苦",
                "color_grading": "高对比冷调",
                "shot_duration": "short",
                "description": "痛苦挣扎，节奏急促",
            },
            "孤独": {
                "camera_moves": ["缓慢拉远", "固定", "缓慢平移"],
                "camera_intensity": "low",
                "effects": ["暗角", "冷调", "空镜"],
                "transitions": ["淡入淡出", "叠化"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "孤独",
                "color_grading": "冷调低饱和",
                "shot_duration": "long",
                "description": "孤独寂寞，节奏极慢",
            },

            # ===== 中性/复杂情绪 =====
            "平静": {
                "camera_moves": ["固定", "缓慢平移", "缓慢推近"],
                "camera_intensity": "low",
                "effects": ["柔光"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "平静",
                "color_grading": "自然",
                "shot_duration": "long",
                "description": "平静自然，节奏平稳",
            },
            "思考": {
                "camera_moves": ["缓慢推近", "固定", "聚焦"],
                "camera_intensity": "low",
                "effects": ["聚焦", "柔光"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "minimal",
                "subtitle_animation": "打字机",
                "bgm_mood": "思考",
                "color_grading": "自然偏冷",
                "shot_duration": "medium",
                "description": "沉思冥想，节奏偏慢",
            },
            "疑惑": {
                "camera_moves": ["缓慢推近", "轻微晃动", "聚焦"],
                "camera_intensity": "medium",
                "effects": ["聚焦", "轻微模糊"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "minimal",
                "subtitle_animation": "打字机",
                "bgm_mood": "疑惑",
                "color_grading": "自然",
                "shot_duration": "medium",
                "description": "疑惑不解，略带悬念",
            },
            "震惊": {
                "camera_moves": ["快速推近", "剧烈晃动", "定格"],
                "camera_intensity": "high",
                "effects": ["闪白", "震动", "放大"],
                "transitions": ["闪白", "突然切入", "硬切"],
                "subtitle_style": "epic",
                "subtitle_animation": "弹出",
                "bgm_mood": "震惊",
                "color_grading": "高对比",
                "shot_duration": "short",
                "description": "极度震惊，瞬间凝固",
            },
            "无奈": {
                "camera_moves": ["缓慢拉远", "轻微晃动", "固定"],
                "camera_intensity": "low",
                "effects": ["暗角"],
                "transitions": ["淡入淡出"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "无奈",
                "color_grading": "偏冷",
                "shot_duration": "medium",
                "description": "无奈接受，节奏偏慢",
            },
            "严肃": {
                "camera_moves": ["固定", "缓慢推近", "对称构图"],
                "camera_intensity": "medium",
                "effects": ["高对比"],
                "transitions": ["硬切", "淡入淡出"],
                "subtitle_style": "epic",
                "subtitle_animation": "渐显",
                "bgm_mood": "严肃",
                "color_grading": "高对比冷调",
                "shot_duration": "medium",
                "description": "严肃正式，节奏沉稳",
            },
            "神秘": {
                "camera_moves": ["缓慢推近", "缓慢平移", "阴影"],
                "camera_intensity": "medium",
                "effects": ["暗角", "模糊", "冷调"],
                "transitions": ["淡入淡出", "叠化"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "神秘",
                "color_grading": "冷调低饱和",
                "shot_duration": "medium",
                "description": "神秘莫测，略带悬念",
            },
            "悬疑": {
                "camera_moves": ["缓慢推近", "轻微晃动", "手持感"],
                "camera_intensity": "medium",
                "effects": ["暗角", "模糊", "冷调"],
                "transitions": ["淡入淡出", "突然切入"],
                "subtitle_style": "minimal",
                "subtitle_animation": "打字机",
                "bgm_mood": "悬疑",
                "color_grading": "冷调低饱和",
                "shot_duration": "medium",
                "description": "悬疑紧张，节奏渐快",
            },
            "幽默": {
                "camera_moves": ["轻微晃动", "快速推近", "定格"],
                "camera_intensity": "medium",
                "effects": ["闪白", "轻微震动"],
                "transitions": ["闪白", "快速切换"],
                "subtitle_style": "fun",
                "subtitle_animation": "弹性伸缩",
                "bgm_mood": "幽默",
                "color_grading": "明亮",
                "shot_duration": "short",
                "description": "幽默搞笑，节奏轻快",
            },
            "讽刺": {
                "camera_moves": ["缓慢推近", "固定", "对称构图"],
                "camera_intensity": "medium",
                "effects": ["高对比", "冷调"],
                "transitions": ["硬切", "淡入淡出"],
                "subtitle_style": "minimal",
                "subtitle_animation": "渐显",
                "bgm_mood": "讽刺",
                "color_grading": "高对比冷调",
                "shot_duration": "medium",
                "description": "讽刺挖苦，节奏沉稳",
            },
            "热血": {
                "camera_moves": ["快速推近", "剧烈晃动", "快速变焦"],
                "camera_intensity": "high",
                "effects": ["闪白", "震动", "光效", "高对比"],
                "transitions": ["闪白", "快速切换", "硬切"],
                "subtitle_style": "epic",
                "subtitle_animation": "放大",
                "bgm_mood": "热血",
                "color_grading": "高饱和暖调",
                "shot_duration": "short",
                "description": "热血沸腾，节奏极快",
            },
            "燃": {
                "camera_moves": ["快速推近", "剧烈晃动", "环绕"],
                "camera_intensity": "high",
                "effects": ["闪白", "震动", "光效"],
                "transitions": ["闪白", "快速切换"],
                "subtitle_style": "epic",
                "subtitle_animation": "弹性伸缩",
                "bgm_mood": "激昂",
                "color_grading": "高饱和暖调",
                "shot_duration": "short",
                "description": "燃爆全场，节奏极快",
            },
            "治愈": {
                "camera_moves": ["缓慢拉远", "缓慢平移", "环绕"],
                "camera_intensity": "low",
                "effects": ["柔光", "暖光", "光晕"],
                "transitions": ["淡入淡出", "叠化"],
                "subtitle_style": "warm",
                "subtitle_animation": "渐显",
                "bgm_mood": "治愈",
                "color_grading": "暖调柔光",
                "shot_duration": "long",
                "description": "温暖治愈，节奏舒缓",
            },
        }

    def get_camera_plan(self, emotion: str, intensity: float = 0.5) -> EmotionCameraPlan:
        """
        获取情绪对应的镜头方案

        Args:
            emotion: 情绪名称（如"开心"、"紧张"）
            intensity: 情绪强度 0.0-1.0

        Returns:
            EmotionCameraPlan 镜头方案
        """
        # 精确匹配
        if emotion in self.emotion_map:
            base = self.emotion_map[emotion]
        else:
            # 模糊匹配（包含关系）
            matched = None
            for key in self.emotion_map:
                if emotion in key or key in emotion:
                    matched = self.emotion_map[key]
                    break
            if matched:
                base = matched
            else:
                # 默认用"平静"
                base = self.emotion_map.get("平静", {})

        # 根据强度调整
        intensity = max(0.0, min(1.0, intensity))
        camera_intensity = base.get("camera_intensity", "medium")
        if intensity > 0.7 and camera_intensity == "low":
            camera_intensity = "medium"
        elif intensity < 0.3 and camera_intensity == "high":
            camera_intensity = "medium"

        return EmotionCameraPlan(
            emotion=emotion,
            intensity=intensity,
            camera_moves=base.get("camera_moves", ["固定"]),
            camera_intensity=camera_intensity,
            effects=base.get("effects", []),
            transitions=base.get("transitions", ["淡入淡出"]),
            subtitle_style=base.get("subtitle_style", "minimal"),
            subtitle_animation=base.get("subtitle_animation", "渐显"),
            bgm_mood=base.get("bgm_mood", "neutral"),
            color_grading=base.get("color_grading", "natural"),
            shot_duration=base.get("shot_duration", "medium"),
            description=base.get("description", ""),
        )

    def list_emotions(self) -> List[str]:
        """列出所有支持的情绪"""
        return list(self.emotion_map.keys())

    def get_emotion_summary(self) -> Dict:
        """获取情绪映射摘要"""
        categories = {
            "积极情绪": ["开心", "兴奋", "惊喜", "得意", "满足", "感动", "期待", "轻松", "治愈"],
            "消极情绪": ["悲伤", "难过", "委屈", "愤怒", "紧张", "恐惧", "焦虑", "尴尬", "失望", "痛苦", "孤独"],
            "中性/复杂": ["平静", "思考", "疑惑", "震惊", "无奈", "严肃", "神秘", "悬疑", "幽默", "讽刺", "热血", "燃"],
        }
        return {
            "total_emotions": len(self.emotion_map),
            "categories": categories,
            "camera_intensity_levels": ["low", "medium", "high"],
            "subtitle_styles": ["epic", "warm", "fun", "minimal"],
        }

    def generate_shot_plan(
        self,
        emotion_segments: List[Dict],
        total_duration: float,
        num_shots: int = 16,
    ) -> List[Dict]:
        """
        根据情绪段落生成镜头计划

        Args:
            emotion_segments: 情绪段落列表 [{"start_time": 0, "duration": 5, "emotion": "开心", "intensity": 0.8}]
            total_duration: 总时长（秒）
            num_shots: 镜头数量

        Returns:
            镜头计划列表
        """
        if not emotion_segments:
            return []

        shot_plan = []
        shots_per_segment = max(1, num_shots // len(emotion_segments))

        for seg in emotion_segments:
            plan = self.get_camera_plan(seg.get("emotion", "平静"), seg.get("intensity", 0.5))
            seg_shots = min(shots_per_segment, num_shots - len(shot_plan))
            if seg_shots <= 0:
                break

            seg_duration = seg.get("duration", 5)
            shot_duration = seg_duration / seg_shots

            for i in range(seg_shots):
                shot_start = seg.get("start_time", 0) + i * shot_duration
                camera_move = plan.camera_moves[i % len(plan.camera_moves)]
                transition = plan.transitions[i % len(plan.transitions)]

                shot_plan.append({
                    "index": len(shot_plan),
                    "start_time": round(shot_start, 2),
                    "duration": round(shot_duration, 2),
                    "emotion": seg.get("emotion", "平静"),
                    "emotion_intensity": seg.get("intensity", 0.5),
                    "camera_move": camera_move,
                    "camera_intensity": plan.camera_intensity,
                    "transition_in": transition if i > 0 else "无",
                    "effects": plan.effects,
                    "subtitle_style": plan.subtitle_style,
                    "subtitle_animation": plan.subtitle_animation,
                    "bgm_mood": plan.bgm_mood,
                    "color_grading": plan.color_grading,
                })

        return shot_plan


def main():
    """命令行测试"""
    mapper = EmotionCameraMapper()

    logger.info("=" * 60)
    logger.info("情绪-镜头映射引擎 v1.0")
    logger.info("=" * 60)

    summary = mapper.get_emotion_summary()
    logger.info(f"\n支持情绪数: {summary['total_emotions']}")
    logger.info(f"情绪分类:")
    for cat, emotions in summary["categories"].items():
        logger.info(f"  {cat}: {len(emotions)}种")

    logger.info("\n=== 测试：紧张情绪（强度0.8）===")
    plan = mapper.get_camera_plan("紧张", 0.8)
    logger.info(f"  运镜: {plan.camera_moves}")
    logger.info(f"  运镜强度: {plan.camera_intensity}")
    logger.info(f"  特效: {plan.effects}")
    logger.info(f"  字幕风格: {plan.subtitle_style}")
    logger.info(f"  字幕动画: {plan.subtitle_animation}")
    logger.info(f"  BGM情绪: {plan.bgm_mood}")
    logger.info(f"  调色: {plan.color_grading}")

    logger.info("\n=== 测试：生成镜头计划 ===")
    segments = [
        {"start_time": 0, "duration": 5, "emotion": "平静", "intensity": 0.3},
        {"start_time": 5, "duration": 5, "emotion": "紧张", "intensity": 0.8},
        {"start_time": 10, "duration": 5, "emotion": "开心", "intensity": 0.9},
    ]
    shots = mapper.generate_shot_plan(segments, total_duration=15, num_shots=9)
    logger.info(f"  生成镜头数: {len(shots)}")
    for s in shots[:3]:
        logger.info(f"  [{s['index']}] {s['start_time']}s {s['emotion']} - {s['camera_move']} ({s['camera_intensity']})")


if __name__ == "__main__":
    main()
