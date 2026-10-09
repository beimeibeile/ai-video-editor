"""
结构化剧本内核 v1.0
借鉴 shuohao-skills 设计：节拍流 + 结构化台词 + 确定性质量门

核心原则：
- 剧本管戏，分镜管拍
- 台词必须是结构化数据（说话人+台词+语气），不能写成散文
- 节拍流：动作节拍与台词节拍交替
- 时长预算：台词按语速折算、动作按节拍估时
- 确定性质量门：不靠模型自觉，全部脚本检查

数据模型：
- BeatType: action/dialogue/hook/suspense/transition
- Beat: 单个节拍
- Scene: 场次
- StructuredScript: 结构化剧本
"""

import logging
logger = logging.getLogger(__name__)


import re
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class BeatType(Enum):
    """节拍类型"""
    ACTION = "action"        # 动作节拍
    DIALOGUE = "dialogue"    # 台词节拍
    HOOK = "hook"            # 钩子节拍（冷开场）
    SUSPENSE = "suspense"    # 悬念节拍（结尾留钩）
    TRANSITION = "transition"  # 转场节拍


@dataclass
class Beat:
    """单个节拍"""
    beat_type: BeatType
    content: str                    # 动作描述 或 台词文本
    speaker: Optional[str] = None   # 说话人（仅dialogue类型）
    tone: Optional[str] = None      # 语气（仅dialogue类型）
    duration_sec: float = 2.0       # 估时（秒）
    beat_index: int = 0             # 在场次中的序号
    is_hook_beat: bool = False      # 是否是钩子认领节拍
    is_payoff_beat: bool = False    # 是否是爽点兑现节拍

    def to_dict(self) -> Dict:
        return {
            "beat_type": self.beat_type.value,
            "content": self.content,
            "speaker": self.speaker,
            "tone": self.tone,
            "duration_sec": self.duration_sec,
            "beat_index": self.beat_index,
            "is_hook_beat": self.is_hook_beat,
            "is_payoff_beat": self.is_payoff_beat,
        }


@dataclass
class Scene:
    """场次"""
    scene_id: str
    location: str                   # 地点
    lighting: Optional[str] = None  # 光照状态
    props: List[str] = field(default_factory=list)  # 道具
    beats: List[Beat] = field(default_factory=list)
    scene_index: int = 0

    @property
    def duration_sec(self) -> float:
        return sum(b.duration_sec for b in self.beats)

    @property
    def has_action(self) -> bool:
        return any(b.beat_type == BeatType.ACTION for b in self.beats)

    @property
    def dialogue_count(self) -> int:
        return sum(1 for b in self.beats if b.beat_type == BeatType.DIALOGUE)

    def to_dict(self) -> Dict:
        return {
            "scene_id": self.scene_id,
            "location": self.location,
            "lighting": self.lighting,
            "props": self.props,
            "beats": [b.to_dict() for b in self.beats],
            "scene_index": self.scene_index,
            "duration_sec": self.duration_sec,
        }


@dataclass
class Character:
    """角色"""
    name: str
    role: str = "supporting"   # protagonist/major/supporting/functional
    voice_style: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class QualityGateResult:
    """质量门检查结果"""
    gate_id: str
    name: str
    passed: bool
    message: str
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StructuredScript:
    """结构化剧本"""
    title: str
    scenes: List[Scene] = field(default_factory=list)
    characters: List[Character] = field(default_factory=list)
    hook: Optional[str] = None           # 钩子描述
    suspense: Optional[str] = None       # 结尾悬念
    payoffs: List[str] = field(default_factory=list)  # 爽点列表
    target_duration_sec: float = 60.0    # 目标时长
    adaptation_level: str = "extract"    # faithful/extract/reuse（忠实/抽核/借壳）

    @property
    def total_duration_sec(self) -> float:
        return sum(s.duration_sec for s in self.scenes)

    @property
    def all_beats(self) -> List[Beat]:
        beats = []
        for s in self.scenes:
            beats.extend(s.beats)
        return beats

    @property
    def character_names(self) -> List[str]:
        return [c.name for c in self.characters]

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "scenes": [s.to_dict() for s in self.scenes],
            "characters": [c.to_dict() for c in self.characters],
            "hook": self.hook,
            "suspense": self.suspense,
            "payoffs": self.payoffs,
            "target_duration_sec": self.target_duration_sec,
            "adaptation_level": self.adaptation_level,
            "total_duration_sec": self.total_duration_sec,
        }

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


# ============================================================
# 时长预算
# ============================================================

# 中文短剧语速：约4字/秒（偏快），保守用3.5字/秒
CHINESE_SPEECH_RATE = 3.5  # 字/秒
DEFAULT_ACTION_DURATION = 2.0  # 秒
DEFAULT_TRANSITION_DURATION = 1.0  # 秒
MAX_DIALOGUE_CHARS = 35  # 单句台词最大字数


def estimate_dialogue_duration(text: str) -> float:
    """估算台词时长（按语速折算）"""
    # 去掉标点
    clean = re.sub(r"[，。！？、；：\"\"''（）\s]", '', text)
    char_count = len(clean)
    return max(1.0, round(char_count / CHINESE_SPEECH_RATE, 1))


# ============================================================
# 自然语言 → 节拍流 解析器
# ============================================================

# 台词模式：角色名：台词内容（支持有引号和无引号）
DIALOGUE_PATTERNS = [
    r'([\u4e00-\u9fa5A-Za-z]{1,4})[：:]["“]([^"”]+)["”]',
    r'([\u4e00-\u9fa5A-Za-z]{1,4})(说|道|喊|问|答|笑|哭|怒)[：:]["“]?([^"”，。！？]+)["”]?',
    # 无引号：角色名：台词（台词中不含场景标题关键词）
    r'^([\u4e00-\u9fa5A-Za-z]{1,4})[：:]([^\n，。！？]{2,40})$',
]

# 动作描述模式：以动词开头的句子
ACTION_KEYWORDS = [
    "突然", "这时", "然后", "接着", "最后", "终于", "于是",
    "走进", "走出", "拿起", "放下", "打开", "关闭", "转身",
    "跑", "走", "跳", "打", "踢", "推", "拉", "抱", "吻",
    "看", "盯", "望", "笑", "哭", "怒", "惊", "慌",
]

# 钩子关键词
HOOK_KEYWORDS = ["震惊", "意外", "没想到", "竟然", "居然", "突然", "卧槽", "什么"]
# 悬念关键词
SUSPENSE_KEYWORDS = ["未完", "待续", "下集", "预知", "究竟", "到底", "悬念"]


def parse_to_structured_script(
    text: str,
    title: str = "未命名",
    target_duration_sec: float = 60.0,
    known_characters: List[str] = None,
) -> StructuredScript:
    """
    将自然语言剧本解析为结构化剧本（节拍流）

    Args:
        text: 自然语言剧本文本
        title: 标题
        target_duration_sec: 目标时长
        known_characters: 已知角色名列表

    Returns:
        StructuredScript
    """
    script = StructuredScript(
        title=title,
        target_duration_sec=target_duration_sec,
    )

    if known_characters:
        for name in known_characters:
            script.characters.append(Character(name=name))

    # 按行处理
    lines = text.split('\n')
    scenes = []
    current_scene_lines = []
    current_location = None

    scene_header_pattern = re.compile(
        r'^(?:场景\s*\d*|第[一二三四五六七八九十\d]+[场集])\s*[：:]?\s*(.*)$'
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测场景标题
        m = scene_header_pattern.match(line)
        if m:
            # 保存上一个场景
            if current_scene_lines:
                scenes.append((current_location, current_scene_lines))
            # 新场景
            location = m.group(1).strip() if m.group(1) else f"场景{len(scenes)+1}"
            current_location = location if location else f"场景{len(scenes)+1}"
            current_scene_lines = []
        else:
            current_scene_lines.append(line)

    # 保存最后一个场景
    if current_scene_lines:
        scenes.append((current_location or "场景1", current_scene_lines))

    if not scenes:
        # 没有场景分割，整体作为一个场景
        scenes = [("场景1", [l.strip() for l in text.split('\n') if l.strip()])]

    for idx, (location, scene_lines) in enumerate(scenes):
        scene = Scene(
            scene_id=f"S{idx+1:02d}",
            location=location,
            scene_index=idx,
        )

        beat_idx = 0

        for line in scene_lines:
            # 尝试匹配台词（行级匹配，更准确）
            dialogue_match = None
            for pattern in DIALOGUE_PATTERNS:
                m = re.search(pattern, line)
                if m:
                    # 排除场景标题误匹配
                    if not re.match(r'^(?:场景|第[一二三四五六七八九十\d]+[场集])', line):
                        dialogue_match = m
                        break

            if dialogue_match:
                speaker = dialogue_match.group(1)
                # group(2)可能是台词或语气词
                content = dialogue_match.group(2) if dialogue_match.lastindex >= 2 else line
                # 如果group(2)是语气词（说/道/喊等），则台词在group(3)
                if content in ("说", "道", "喊", "问", "答", "笑", "哭", "怒"):
                    content = dialogue_match.group(3) if dialogue_match.lastindex >= 3 else line

                # 注册角色
                if speaker not in script.character_names:
                    script.characters.append(Character(name=speaker))

                # 检测语气
                tone = "平静"
                if any(k in line for k in ["愤怒", "怒", "吼"]):
                    tone = "愤怒"
                elif any(k in line for k in ["开心", "笑", "高兴"]):
                    tone = "开心"
                elif any(k in line for k in ["委屈", "哭", "难过"]):
                    tone = "委屈"
                elif any(k in line for k in ["惊讶", "惊", "卧槽", "什么"]):
                    tone = "惊讶"
                elif any(k in line for k in ["紧张", "慌", "怕"]):
                    tone = "紧张"

                beat = Beat(
                    beat_type=BeatType.DIALOGUE,
                    content=content,
                    speaker=speaker,
                    tone=tone,
                    duration_sec=estimate_dialogue_duration(content),
                    beat_index=beat_idx,
                )
                beat_idx += 1
                scene.beats.append(beat)

                # 钩子检测
                if any(k in content for k in HOOK_KEYWORDS) and beat_idx <= 3:
                    beat.is_hook_beat = True
                    if not script.hook:
                        script.hook = content[:30]
            else:
                # 动作节拍（可能包含多个句子，按句号分割）
                sub_sentences = re.split(r'[。！？]', line)
                for sub in sub_sentences:
                    sub = sub.strip()
                    if not sub:
                        continue

                    # 子句级别也尝试匹配台词
                    sub_dialogue = None
                    for pattern in DIALOGUE_PATTERNS:
                        m = re.search(pattern, sub)
                        if m:
                            sub_dialogue = m
                            break

                    if sub_dialogue:
                        speaker = sub_dialogue.group(1)
                        content = sub_dialogue.group(2) if sub_dialogue.lastindex >= 2 else sub
                        if content in ("说", "道", "喊", "问", "答", "笑", "哭", "怒"):
                            content = sub_dialogue.group(3) if sub_dialogue.lastindex >= 3 else sub

                        if speaker not in script.character_names:
                            script.characters.append(Character(name=speaker))

                        tone = "惊讶" if any(k in content for k in HOOK_KEYWORDS) else "平静"

                        beat = Beat(
                            beat_type=BeatType.DIALOGUE,
                            content=content,
                            speaker=speaker,
                            tone=tone,
                            duration_sec=estimate_dialogue_duration(content),
                            beat_index=beat_idx,
                        )
                        if any(k in content for k in HOOK_KEYWORDS) and beat_idx <= 3:
                            beat.is_hook_beat = True
                            if not script.hook:
                                script.hook = content[:30]
                    else:
                        beat_type = BeatType.ACTION
                        if any(k in sub for k in SUSPENSE_KEYWORDS):
                            beat_type = BeatType.SUSPENSE
                            if not script.suspense:
                                script.suspense = sub[:30]

                        beat = Beat(
                            beat_type=beat_type,
                            content=sub,
                            duration_sec=DEFAULT_ACTION_DURATION,
                            beat_index=beat_idx,
                        )

                    beat_idx += 1
                    scene.beats.append(beat)

        script.scenes.append(scene)

    return script


# ============================================================
# 确定性质量门（10道）
# ============================================================

def run_quality_gates(script: StructuredScript) -> List[QualityGateResult]:
    """
    运行10道确定性质量门检查

    Returns:
        质量门结果列表
    """
    results = []

    # Q01: 时长预算 ±15%
    total = script.total_duration_sec
    target = script.target_duration_sec
    deviation = abs(total - target) / target if target > 0 else 0
    q01_passed = deviation <= 0.15
    results.append(QualityGateResult(
        gate_id="Q01",
        name="时长预算",
        passed=q01_passed,
        message=f"实际{total:.1f}s / 目标{target:.1f}s，偏差{deviation*100:.1f}%",
        details=[f"允许±15%，实际{'通过' if q01_passed else '超差'}"],
    ))

    # Q02: 单句台词 ≤35字
    long_lines = []
    for beat in script.all_beats:
        if beat.beat_type == BeatType.DIALOGUE:
            clean = re.sub(r"[，。！？、；：\"\"''（）\s]", '', beat.content)
            if len(clean) > MAX_DIALOGUE_CHARS:
                long_lines.append(f"{beat.speaker}: {beat.content[:20]}...({len(clean)}字)")
    results.append(QualityGateResult(
        gate_id="Q02",
        name="单句台词字数",
        passed=len(long_lines) == 0,
        message=f"超长台词{len(long_lines)}句（上限{MAX_DIALOGUE_CHARS}字）",
        details=long_lines[:5],
    ))

    # Q03: 说话人合法（在角色表中）
    unknown_speakers = []
    for beat in script.all_beats:
        if beat.beat_type == BeatType.DIALOGUE and beat.speaker:
            if beat.speaker not in script.character_names:
                unknown_speakers.append(beat.speaker)
    results.append(QualityGateResult(
        gate_id="Q03",
        name="说话人合法性",
        passed=len(unknown_speakers) == 0,
        message=f"未注册说话人{len(set(unknown_speakers))}个",
        details=list(set(unknown_speakers)),
    ))

    # Q04: 钩子悬念落纸
    has_hook = script.hook is not None and len(script.hook) > 0
    has_suspense = script.suspense is not None and len(script.suspense) > 0
    results.append(QualityGateResult(
        gate_id="Q04",
        name="钩子悬念落纸",
        passed=has_hook and has_suspense,
        message=f"钩子={'有' if has_hook else '无'}，悬念={'有' if has_suspense else '无'}",
        details=[f"钩子: {script.hook}" if has_hook else "缺少钩子",
                 f"悬念: {script.suspense}" if has_suspense else "缺少悬念"],
    ))

    # Q05: 钩子前3拍内兑现
    hook_in_first_3 = False
    for beat in script.all_beats[:3]:
        if beat.is_hook_beat or (beat.beat_type == BeatType.DIALOGUE and any(k in beat.content for k in HOOK_KEYWORDS)):
            hook_in_first_3 = True
            break
    results.append(QualityGateResult(
        gate_id="Q05",
        name="钩子前3拍兑现",
        passed=hook_in_first_3,
        message="钩子在前3拍内兑现" if hook_in_first_3 else "钩子未在前3拍内兑现（冷开场要求）",
    ))

    # Q06: 每场至少一个动作节拍
    no_action_scenes = []
    for scene in script.scenes:
        if not scene.has_action:
            no_action_scenes.append(f"{scene.scene_id}({scene.location})")
    results.append(QualityGateResult(
        gate_id="Q06",
        name="每场至少一个动作节拍",
        passed=len(no_action_scenes) == 0,
        message=f"纯对白场次{len(no_action_scenes)}个（广播剧病）",
        details=no_action_scenes,
    ))

    # Q07: 爽点认领（如果有爽点列表，必须有兑现节拍）
    unclaimed_payoffs = []
    if script.payoffs:
        for payoff in script.payoffs:
            claimed = any(
                b.is_payoff_beat or (payoff[:5] in b.content if len(payoff) >= 5 else False)
                for b in script.all_beats
            )
            if not claimed:
                unclaimed_payoffs.append(payoff)
    results.append(QualityGateResult(
        gate_id="Q07",
        name="爽点认领",
        passed=len(unclaimed_payoffs) == 0,
        message=f"未认领爽点{len(unclaimed_payoffs)}个" if script.payoffs else "无爽点列表（跳过）",
        details=unclaimed_payoffs,
    ))

    # Q08: 节拍流连续性（不连续3拍以上纯对白）
    dialogue_runs = []
    current_run = 0
    for beat in script.all_beats:
        if beat.beat_type == BeatType.DIALOGUE:
            current_run += 1
            if current_run >= 3:
                dialogue_runs.append(f"连续{current_run}拍对白")
        else:
            current_run = 0
    results.append(QualityGateResult(
        gate_id="Q08",
        name="节拍流连续性",
        passed=len(dialogue_runs) == 0,
        message=f"连续对白≥3拍的段落{len(dialogue_runs)}处（动作⇄台词应交替）",
        details=dialogue_runs[:3],
    ))

    # Q09: 台词装得下（台词秒数≤场次秒数的合理比例）
    overflow_dialogues = []
    for scene in script.scenes:
        dialogue_time = sum(b.duration_sec for b in scene.beats if b.beat_type == BeatType.DIALOGUE)
        scene_time = scene.duration_sec
        if scene_time > 0 and dialogue_time / scene_time > 0.9 and scene.dialogue_count > 2:
            overflow_dialogues.append(f"{scene.scene_id}: 对白占比{dialogue_time/scene_time*100:.0f}%")
    results.append(QualityGateResult(
        gate_id="Q09",
        name="台词装得下",
        passed=len(overflow_dialogues) == 0,
        message=f"对白占比过高场次{len(overflow_dialogues)}个（>90%）",
        details=overflow_dialogues,
    ))

    # Q10: 角色分档上限（主角≤5，重要配角≤10）
    char_count = len(script.characters)
    results.append(QualityGateResult(
        gate_id="Q10",
        name="角色数量控制",
        passed=char_count <= 15,
        message=f"角色总数{char_count}个（建议≤15，主角≤5）",
        details=[f"角色: {', '.join(script.character_names[:10])}"],
    ))

    return results


def print_quality_report(results: List[QualityGateResult]):
    """打印质量门报告"""
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    logger.info(f"\n{'='*60}")
    logger.info(f"质量门报告: {passed}/{total} 通过")
    logger.info(f"{'='*60}")

    for r in results:
        status = "✅" if r.passed else "❌"
        logger.info(f"  {status} {r.gate_id} {r.name}: {r.message}")
        if not r.passed and r.details:
            for d in r.details[:3]:
                logger.info(f"      → {d}")

    logger.info(f"{'='*60}\n")
    return passed == total


# ============================================================
# 结构化剧本 → P24翻译器标准格式
# ============================================================

def to_standard_format(script: StructuredScript) -> Dict:
    """
    将结构化剧本转换为P24指令翻译器可接受的标准分镜格式

    输出格式与script_parser.parse()一致：
    {
        "title": ...,
        "characters": [...],
        "scenes": [
            {
                "scene_id": ...,
                "location": ...,
                "shots": [
                    {
                        "shot_id": ...,
                        "description": ...,
                        "character": ...,
                        "action": ...,
                        "dialogue": ...,
                        "tone": ...,
                        "duration": ...,
                        "camera_move": ...,
                    }
                ]
            }
        ]
    }
    """
    result = {
        "title": script.title,
        "characters": [c.to_dict() for c in script.characters],
        "scenes": [],
        "hook": script.hook,
        "suspense": script.suspense,
        "structured": True,  # 标记为结构化剧本
    }

    for scene in script.scenes:
        scene_data = {
            "scene_id": scene.scene_id,
            "location": scene.location,
            "lighting": scene.lighting,
            "props": scene.props,
            "shots": [],
        }

        shot_idx = 0
        for beat in scene.beats:
            shot = {
                "shot_id": f"{scene.scene_id}_shot{shot_idx+1:02d}",
                "description": beat.content,
                "duration": beat.duration_sec,
                "beat_type": beat.beat_type.value,
            }

            if beat.beat_type == BeatType.DIALOGUE:
                shot["character"] = beat.speaker
                shot["dialogue"] = beat.content
                shot["tone"] = beat.tone
                shot["action"] = "说话"
            else:
                shot["action"] = beat.content
                shot["dialogue"] = None

            if beat.is_hook_beat:
                shot["is_hook"] = True
            if beat.is_payoff_beat:
                shot["is_payoff"] = True

            scene_data["shots"].append(shot)
            shot_idx += 1

        result["scenes"].append(scene_data)

    return result


# ============================================================
# 体检模式：只跑质量门给诊断
# ============================================================

def health_check(text: str, title: str = "体检", target_duration: float = 60.0) -> Dict:
    """
    体检模式：解析文本并跑质量门，只给诊断不修改

    Args:
        text: 剧本文本
        title: 标题
        target_duration: 目标时长

    Returns:
        体检报告
    """
    script = parse_to_structured_script(text, title=title, target_duration_sec=target_duration)
    gates = run_quality_gates(script)

    return {
        "title": title,
        "script_summary": {
            "scenes": len(script.scenes),
            "beats": len(script.all_beats),
            "characters": len(script.characters),
            "estimated_duration": script.total_duration_sec,
            "target_duration": target_duration,
        },
        "quality_gates": [g.to_dict() for g in gates],
        "passed": sum(1 for g in gates if g.passed),
        "total": len(gates),
        "structured_script": script.to_dict(),
    }


if __name__ == "__main__":
    # 测试
    test_script = """
    场景1：办公室，深夜。
    小张坐在电脑前，屏幕上代码飞速滚动。
    小张：这bug怎么改不完啊...
    突然，屏幕上的光标自己动了起来，开始自动写代码。
    小张：卧槽？！
    场景2：小张后退一步，盯着屏幕。
    代码越写越快，最后弹出一行字：谢谢你的键盘，我自己来。
    小张：...那我下班了？
    """

    logger.info("="*60)
    logger.info("结构化剧本内核测试")
    logger.info("="*60)

    # 解析
    script = parse_to_structured_script(
        test_script,
        title="代码觉醒",
        target_duration_sec=20.0,
    )

    logger.info(f"\n解析结果:")
    logger.info(f"  场次: {len(script.scenes)}")
    logger.info(f"  节拍: {len(script.all_beats)}")
    logger.info(f"  角色: {script.character_names}")
    logger.info(f"  估算时长: {script.total_duration_sec:.1f}s")
    logger.info(f"  钩子: {script.hook}")
    logger.info(f"  悬念: {script.suspense}")

    for scene in script.scenes:
        logger.info(f"\n  {scene.scene_id} ({scene.location}, {scene.duration_sec:.1f}s):")
        for beat in scene.beats:
            type_label = "💬" if beat.beat_type == BeatType.DIALOGUE else "🎬"
            speaker = f" [{beat.speaker}/{beat.tone}]" if beat.speaker else ""
            logger.info(f"    {type_label} #{beat.beat_index} ({beat.duration_sec:.1f}s){speaker}: {beat.content[:30]}")

    # 质量门
    gates = run_quality_gates(script)
    print_quality_report(gates)

    # 标准格式
    standard = to_standard_format(script)
    logger.info(f"标准格式转换: {len(standard['scenes'])}场景, {sum(len(s['shots']) for s in standard['scenes'])}镜头")

    # 体检模式
    logger.info("\n体检模式测试:")
    report = health_check(test_script, title="代码觉醒体检", target_duration=20.0)
    logger.info(f"  通过: {report['passed']}/{report['total']}")
