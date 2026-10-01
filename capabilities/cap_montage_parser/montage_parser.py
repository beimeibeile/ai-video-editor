"""
蒙太奇解析器 v1.0
识别剧本中的MONTAGE标记，自动拆分为快剪镜头序列

核心能力：
1. 识别MONTAGE标记（MONTAGE/蒙太奇/快速剪辑/时光流逝等）
2. 自动拆分为快剪镜头序列（每个1-3秒）
3. 蒙太奇节奏控制（加速/减速/变速）
4. 蒙太奇类型识别：成长蒙太奇/训练蒙太奇/时间流逝/对比蒙太奇
5. 与分镜引擎集成，输出标准镜头格式
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple


class MontageType(Enum):
    """蒙太奇类型"""
    GROWTH = "成长蒙太奇"      # 学习/成长/进步
    TRAINING = "训练蒙太奇"    # 训练/练习/努力
    TIME_PASSAGE = "时间流逝"   # 时光飞逝/季节变化
    CONTRAST = "对比蒙太奇"     # 前后对比/贫富对比
    PARALLEL = "平行蒙太奇"     # 多条线索并行
    EMOTION = "情绪蒙太奇"      # 情绪累积/爆发


# 蒙太奇标记关键词
MONTAGE_MARKERS = [
    r"MONTAGE", r"蒙太奇", r"快速剪辑", r"快剪",
    r"时光流逝", r"时间流逝", r"岁月如梭", r"日复一日",
    r"经过.*努力", r"经过.*训练", r"经过.*学习",
    r"几个月后", r"几周后", r"几天后",
    r"与此同时", r"另一边",
    r"成长", r"进步", r"蜕变",
]

# 蒙太奇类型关键词
MONTAGE_TYPE_KEYWORDS = {
    MontageType.GROWTH: ["学习", "成长", "进步", "掌握", "学会", "蜕变"],
    MontageType.TRAINING: ["训练", "练习", "努力", "奋斗", "拼搏", "反复"],
    MontageType.TIME_PASSAGE: ["时光", "时间", "岁月", "日复一日", "几个月", "几周", "几天"],
    MontageType.CONTRAST: ["对比", "以前", "现在", "曾经", "如今", "贫富"],
    MontageType.PARALLEL: ["与此同时", "另一边", "同时", "平行"],
    MontageType.EMOTION: ["情绪", "激动", "感慨", "百感交集"],
}


@dataclass
class MontageSegment:
    """蒙太奇中的单个快剪片段"""
    index: int
    description: str
    duration: float          # 秒（1-3秒）
    emotion: str = ""
    visual_hint: str = ""   # 画面提示


@dataclass
class MontagePlan:
    """蒙太奇方案"""
    montage_id: str
    montage_type: MontageType
    original_text: str
    total_duration: float    # 总时长
    segment_count: int
    segments: List[MontageSegment] = field(default_factory=list)
    pacing: str = "加速"     # 加速/减速/变速
    transition: str = "溶解"  # 蒙太奇内转场


class MontageParser:
    """蒙太奇解析器"""

    def __init__(self, default_segment_duration: float = 2.0,
                 min_segments: int = 3, max_segments: int = 12):
        self.default_segment_duration = default_segment_duration
        self.min_segments = min_segments
        self.max_segments = max_segments

    def detect_montage(self, text: str) -> Optional[Tuple[int, int, str]]:
        """
        检测文本中是否包含蒙太奇标记

        Args:
            text: 剧本文本

        Returns:
            (start_pos, end_pos, matched_marker) 或 None
        """
        for pattern in MONTAGE_MARKERS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return (match.start(), match.end(), match.group())
        return None

    def detect_montage_type(self, text: str) -> MontageType:
        """
        识别蒙太奇类型

        Args:
            text: 蒙太奇段落文本

        Returns:
            MontageType
        """
        scores = {}
        for mtype, keywords in MONTAGE_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            scores[mtype] = score

        best_type = max(scores, key=scores.get)
        if scores[best_type] > 0:
            return best_type
        return MontageType.GROWTH  # 默认成长蒙太奇

    def extract_montage_context(self, text: str, start: int, end: int,
                                 context_chars: int = 200) -> str:
        """
        提取蒙太奇标记周围的上下文

        Args:
            text: 完整文本
            start: 标记起始位置
            end: 标记结束位置
            context_chars: 上下文字符数

        Returns:
            蒙太奇上下文文本
        """
        ctx_start = max(0, start - context_chars)
        ctx_end = min(len(text), end + context_chars)
        return text[ctx_start:ctx_end]

    def generate_segments(self, montage_type: MontageType, context: str,
                           total_duration: float) -> List[MontageSegment]:
        """
        根据蒙太奇类型和上下文生成快剪片段

        Args:
            montage_type: 蒙太奇类型
            context: 上下文文本
            total_duration: 总时长

        Returns:
            MontageSegment列表
        """
        # 计算片段数量
        segment_count = max(
            self.min_segments,
            min(self.max_segments, int(total_duration / self.default_segment_duration))
        )

        # 根据类型生成片段描述
        segment_templates = self._get_segment_templates(montage_type, context)

        segments = []
        for i in range(segment_count):
            # 变速节奏：前慢后快
            if i < segment_count // 3:
                duration = min(3.0, self.default_segment_duration * 1.3)
            elif i > segment_count * 2 // 3:
                duration = max(1.0, self.default_segment_duration * 0.7)
            else:
                duration = self.default_segment_duration

            template = segment_templates[i % len(segment_templates)]
            progress = (i + 1) / segment_count

            description = template.format(
                index=i + 1,
                total=segment_count,
                progress=f"{int(progress * 100)}%",
            )

            segments.append(MontageSegment(
                index=i + 1,
                description=description,
                duration=round(duration, 1),
                emotion=self._get_segment_emotion(montage_type, progress),
                visual_hint=self._get_visual_hint(montage_type, progress),
            ))

        return segments

    def _get_segment_templates(self, montage_type: MontageType,
                                 context: str) -> List[str]:
        """获取蒙太奇片段模板"""
        templates_map = {
            MontageType.GROWTH: [
                "深夜伏案学习，屏幕光照在脸上",
                "反复练习操作，手指在键盘上飞舞",
                "查看教程笔记，眉头紧锁",
                "第一次尝试成功，露出微笑",
                "作品逐渐成型，画面越来越精致",
                "对比第一次和最新作品，进步明显",
                "自信地展示作品，眼神坚定",
            ],
            MontageType.TRAINING: [
                "清晨开始练习，阳光洒进房间",
                "反复打磨细节，汗水滴落",
                "失败后重新开始，不屈不挠",
                "技巧逐渐熟练，动作越来越流畅",
                "突破瓶颈，露出释然的笑容",
                "最终完成，疲惫但满足",
            ],
            MontageType.TIME_PASSAGE: [
                "窗外树叶从绿变黄",
                "日历一页页翻过",
                "咖啡杯从满到空，又重新倒满",
                "电脑屏幕上的日期不断变化",
                "季节交替，衣着从薄到厚",
                "时光飞逝，人物逐渐成长",
            ],
            MontageType.CONTRAST: [
                "过去：颓废地坐在电脑前",
                "现在：自信地展示作品",
                "过去：被人质疑嘲笑",
                "现在：令人刮目相看",
                "过去：迷茫无助",
                "现在：目标明确",
            ],
            MontageType.PARALLEL: [
                "主角在努力学习",
                "另一边，对手在放松娱乐",
                "主角在反复练习",
                "另一边，对手在虚度光阴",
                "主角的作品逐渐成型",
                "对比两人的状态，差距逐渐拉大",
            ],
            MontageType.EMOTION: [
                "回忆过去的挫折，眼眶湿润",
                "想到未来的希望，眼神发亮",
                "百感交集，嘴角微微上扬",
                "握紧拳头，下定决心",
                "深吸一口气，释然微笑",
            ],
        }
        return templates_map.get(montage_type, templates_map[MontageType.GROWTH])

    def _get_segment_emotion(self, montage_type: MontageType,
                               progress: float) -> str:
        """获取片段情绪（随进度变化）"""
        if progress < 0.3:
            return "紧张"
        elif progress < 0.6:
            return "坚定"
        elif progress < 0.9:
            return "期待"
        else:
            return "释然"

    def _get_visual_hint(self, montage_type: MontageType,
                           progress: float) -> str:
        """获取画面提示"""
        if progress < 0.3:
            return "暗色调，低角度"
        elif progress < 0.6:
            return "中性色调，平视"
        elif progress < 0.9:
            return "暖色调，略仰拍"
        else:
            return "明亮色调，全景"

    def parse_scene(self, scene_text: str, scene_id: str = "M01",
                     total_duration: float = 20.0) -> Optional[MontagePlan]:
        """
        解析单个场景中的蒙太奇

        Args:
            scene_text: 场景文本
            scene_id: 场景ID
            total_duration: 蒙太奇总时长

        Returns:
            MontagePlan 或 None（无蒙太奇）
        """
        detection = self.detect_montage(scene_text)
        if not detection:
            return None

        start, end, marker = detection
        context = self.extract_montage_context(scene_text, start, end)
        montage_type = self.detect_montage_type(context)
        segments = self.generate_segments(montage_type, context, total_duration)

        # 计算实际总时长
        actual_duration = sum(s.duration for s in segments)

        return MontagePlan(
            montage_id=scene_id,
            montage_type=montage_type,
            original_text=scene_text,
            total_duration=round(actual_duration, 1),
            segment_count=len(segments),
            segments=segments,
            pacing="变速",
            transition="溶解",
        )

    def parse_full_script(self, script_text: str) -> List[MontagePlan]:
        """
        解析完整剧本中的所有蒙太奇

        Args:
            script_text: 完整剧本文本

        Returns:
            MontagePlan列表
        """
        plans = []
        # 按场景分割
        scenes = re.split(r'(?:场景|Scene)\s*\d+', script_text)
        for i, scene_text in enumerate(scenes[1:], 1):  # 跳过第一个空段
            plan = self.parse_scene(scene_text, f"M{i:02d}")
            if plan:
                plans.append(plan)
        return plans

    def montage_to_shots(self, plan: MontagePlan,
                          scene_id: str = "") -> List[Dict[str, Any]]:
        """
        将蒙太奇方案转换为标准镜头格式

        Args:
            plan: 蒙太奇方案
            scene_id: 场景ID

        Returns:
            标准镜头字典列表
        """
        shots = []
        for seg in plan.segments:
            shot_id = f"{scene_id}M{seg.index:02d}" if scene_id else f"M{seg.index:02d}"
            shots.append({
                "shot_id": shot_id,
                "scene_id": scene_id or plan.montage_id,
                "description": seg.description,
                "dialogue": "",
                "shot_size": "特写" if seg.index % 3 != 0 else "中景",
                "camera_move": "快推" if seg.index % 2 == 0 else "固定",
                "camera_angle": "平视",
                "duration": seg.duration,
                "emotion": seg.emotion,
                "intent": "动作",
                "is_montage": True,
                "montage_type": plan.montage_type.value,
                "visual_hint": seg.visual_hint,
            })
        return shots


if __name__ == "__main__":
    print("=" * 60)
    print("蒙太奇解析器 v1.0")
    print("=" * 60)

    parser = MontageParser()

    # 测试：成长蒙太奇
    test_script = """
    场景3：陈默开始学习AI视频编辑器

    MONTAGE - 学习成长：
    陈默每天深夜伏案学习，反复练习操作，
    从最基础的指令开始，逐渐掌握高级技巧。
    经过几周的努力，他的作品越来越精致。

    场景4：...
    """

    print("\n检测蒙太奇标记:")
    detection = parser.detect_montage(test_script)
    if detection:
        print(f"  ✅ 检测到蒙太奇标记: '{detection[2]}' at pos {detection[0]}-{detection[1]}")
    else:
        print("  ❌ 未检测到")

    print("\n解析完整剧本:")
    plans = parser.parse_full_script(test_script)
    for plan in plans:
        print(f"\n  蒙太奇 {plan.montage_id}:")
        print(f"    类型: {plan.montage_type.value}")
        print(f"    总时长: {plan.total_duration}秒")
        print(f"    片段数: {plan.segment_count}")
        print(f"    节奏: {plan.pacing}, 转场: {plan.transition}")
        print(f"    片段列表:")
        for seg in plan.segments:
            print(f"      [{seg.index}] {seg.duration}s - {seg.description}")
            print(f"           情绪={seg.emotion}, 画面={seg.visual_hint}")

    print("\n转换为标准镜头格式:")
    if plans:
        shots = parser.montage_to_shots(plans[0], "S03")
        for shot in shots:
            print(f"  {shot['shot_id']}: {shot['duration']}s {shot['shot_size']}/{shot['camera_move']} - {shot['description'][:30]}...")
