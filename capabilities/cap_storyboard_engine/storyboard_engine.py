"""
分镜叙事引擎 (Storyboard Engine)
软实力核心：把创意想法转化为可执行的分镜脚本

核心能力：
- 叙事结构：钩子→展开→高潮→收束
- 景别递进：特写→近景→中景→全景→远景（或反向）
- 运镜连贯：推→推→移→拉（避免方向断裂）
- 转场匹配：快切/叠化/闪白根据情绪选择
- 节奏设计：快慢对比，平均时长变化
- 颜色衔接：相邻镜头色调过渡
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json
import hashlib


# ==================== 数据结构 ====================

@dataclass
class Shot:
    """单个镜头"""
    index: int                    # 镜头序号
    duration: float               # 时长（秒）
    shot_size: str                # 景别：特写/近景/中景/全景/远景
    camera_move: str              # 运镜：推/拉/摇/移/跟/固定
    move_intensity: float         # 运镜强度 0.05-0.2
    transition_in: str            # 入场转场：无/叠化/快切/闪白/黑场
    transition_duration: float    # 转场时长（秒）
    emotion: str                  # 情绪：钩子/展开/高潮/收束/平静/紧张/欢快
    subtitle: str                 # 字幕文案
    subtitle_style: str           # 字幕风格：epic/warm/fun/minimal
    color_tone: str               # 色调：冷/暖/中性/高对比/低饱和
    narration: str = ""           # 旁白（可选）
    sfx_hint: str = ""            # 音效提示（可选）
    notes: str = ""               # 备注

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "duration": round(self.duration, 2),
            "shot_size": self.shot_size,
            "camera_move": self.camera_move,
            "move_intensity": round(self.move_intensity, 3),
            "transition_in": self.transition_in,
            "transition_duration": round(self.transition_duration, 2),
            "emotion": self.emotion,
            "subtitle": self.subtitle,
            "subtitle_style": self.subtitle_style,
            "color_tone": self.color_tone,
            "narration": self.narration,
            "sfx_hint": self.sfx_hint,
            "notes": self.notes,
        }


@dataclass
class Storyboard:
    """完整分镜脚本"""
    theme: str                    # 主题
    style: str                    # 整体风格
    total_duration: float         # 总时长
    shots: List[Shot] = field(default_factory=list)
    hook_text: str = ""           # 钩子文案
    ending_text: str = ""         # 结尾文案
    bgm_mood: str = ""            # BGM情绪
    intro_style: str = ""         # 片头风格
    outro_style: str = ""         # 片尾风格

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme": self.theme,
            "style": self.style,
            "total_duration": round(self.total_duration, 2),
            "hook_text": self.hook_text,
            "ending_text": self.ending_text,
            "bgm_mood": self.bgm_mood,
            "intro_style": self.intro_style,
            "outro_style": self.outro_style,
            "shot_count": len(self.shots),
            "shots": [s.to_dict() for s in self.shots],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def get_shot(self, index: int) -> Optional[Shot]:
        if 0 <= index < len(self.shots):
            return self.shots[index]
        return None

    def summary(self) -> str:
        """分镜摘要"""
        lines = [
            f"主题: {self.theme}",
            f"风格: {self.style}",
            f"时长: {self.total_duration:.1f}s / {len(self.shots)}镜头",
            f"钩子: {self.hook_text}",
            f"结尾: {self.ending_text}",
            "",
            "镜头序列:",
        ]
        for s in self.shots:
            lines.append(
                f"  [{s.index}] {s.duration:.1f}s | {s.shot_size} | {s.camera_move} | "
                f"{s.transition_in}({s.transition_duration}s) | {s.emotion} | {s.subtitle}"
            )
        return "\n".join(lines)


# ==================== 叙事模板 ====================

# 景别递进序列（从近到远，适合"揭示"型叙事）
SHOT_SIZE_PROGRESSION = ["特写", "近景", "中景", "全景", "远景"]
# 景别递进序列（从远到近，适合"聚焦"型叙事）
SHOT_SIZE_REGRESSION = ["远景", "全景", "中景", "近景", "特写"]

# 运镜连贯序列（推→推→移→拉，避免方向断裂）
CAMERA_MOVE_FLOW = {
    "reveal": ["推", "推", "移右", "拉"],        # 揭示型：先聚焦再拉开
    "focus": ["拉", "移左", "推", "推"],          # 聚焦型：先拉开再推进
    "journey": ["移右", "推", "移左", "拉"],      # 旅程型：左右移动+推拉
    "calm": ["固定", "缓推", "固定", "缓拉"],      # 平静型：缓慢变化
    "intense": ["快推", "快切", "快推", "拉"],     # 紧张型：快速推进
}

# 转场匹配（根据情绪选择）
TRANSITION_BY_EMOTION = {
    "钩子": {"type": "闪白", "duration": 0.2},
    "展开": {"type": "叠化", "duration": 0.4},
    "高潮": {"type": "快切", "duration": 0.15},
    "收束": {"type": "叠化", "duration": 0.6},
    "平静": {"type": "叠化", "duration": 0.5},
    "紧张": {"type": "快切", "duration": 0.2},
    "欢快": {"type": "快切", "duration": 0.25},
    "神秘": {"type": "黑场", "duration": 0.4},
}

# 节奏模板（各镜头时长占比）
RHYTHM_TEMPLATES = {
    "standard": [0.15, 0.20, 0.25, 0.20, 0.20],      # 标准：慢-中-快-中-慢
    "fast_paced": [0.10, 0.15, 0.20, 0.25, 0.30],    # 快节奏：越来越快
    "slow_build": [0.30, 0.25, 0.20, 0.15, 0.10],    # 慢起：越来越慢（收束感）
    "hook_heavy": [0.25, 0.15, 0.20, 0.20, 0.20],    # 钩子重：开头长
}

# 色调衔接（相邻镜头色调过渡）
COLOR_TONE_FLOW = {
    "cool_to_warm": ["冷", "冷", "中性", "暖", "暖"],
    "warm_to_cool": ["暖", "暖", "中性", "冷", "冷"],
    "monochrome": ["中性", "中性", "中性", "中性", "中性"],
    "high_contrast": ["高对比", "高对比", "中性", "低饱和", "低饱和"],
}

# 风格预设
STYLE_PRESETS = {
    "cinematic": {
        "shot_size": SHOT_SIZE_PROGRESSION,
        "camera_move": CAMERA_MOVE_FLOW["reveal"],
        "rhythm": RHYTHM_TEMPLATES["standard"],
        "color": COLOR_TONE_FLOW["cool_to_warm"],
        "subtitle_style": "epic",
        "intro_style": "impact",
        "bgm_mood": "史诗",
    },
    "vlog": {
        "shot_size": ["中景", "近景", "特写", "中景", "全景"],
        "camera_move": CAMERA_MOVE_FLOW["journey"],
        "rhythm": RHYTHM_TEMPLATES["fast_paced"],
        "color": COLOR_TONE_FLOW["warm_to_cool"],
        "subtitle_style": "warm",
        "intro_style": "cute",
        "bgm_mood": "欢快",
    },
    "tutorial": {
        "shot_size": ["近景", "特写", "中景", "近景", "中景"],
        "camera_move": CAMERA_MOVE_FLOW["calm"],
        "rhythm": RHYTHM_TEMPLATES["slow_build"],
        "color": COLOR_TONE_FLOW["monochrome"],
        "subtitle_style": "minimal",
        "intro_style": "minimal",
        "bgm_mood": "平静",
    },
    "thriller": {
        "shot_size": SHOT_SIZE_REGRESSION,
        "camera_move": CAMERA_MOVE_FLOW["intense"],
        "rhythm": RHYTHM_TEMPLATES["hook_heavy"],
        "color": COLOR_TONE_FLOW["high_contrast"],
        "subtitle_style": "minimal",
        "intro_style": "suspense",
        "bgm_mood": "紧张",
    },
    "emotional": {
        "shot_size": ["特写", "近景", "中景", "近景", "特写"],
        "camera_move": CAMERA_MOVE_FLOW["calm"],
        "rhythm": RHYTHM_TEMPLATES["standard"],
        "color": COLOR_TONE_FLOW["warm_to_cool"],
        "subtitle_style": "warm",
        "intro_style": "minimal",
        "bgm_mood": "温馨",
    },
}


# ==================== 分镜生成器 ====================

class StoryboardGenerator:
    """分镜生成器"""

    def __init__(self):
        self.presets = STYLE_PRESETS

    def generate(self,
                 theme: str,
                 style: str = "cinematic",
                 total_duration: float = 15.0,
                 shot_count: int = 5,
                 hook_text: str = "",
                 ending_text: str = "",
                 custom_subtitles: List[str] = None,
                 rhythm: str = None) -> Storyboard:
        """
        生成分镜脚本

        Args:
            theme: 视频主题
            style: 风格 - cinematic/vlog/tutorial/thriller/emotional
            total_duration: 总时长（秒）
            shot_count: 镜头数量
            hook_text: 钩子文案（第一个镜头的字幕）
            ending_text: 结尾文案（最后一个镜头的字幕）
            custom_subtitles: 自定义字幕列表（覆盖自动生成）
            rhythm: 节奏模板覆盖 - standard/fast_paced/slow_build/hook_heavy

        Returns:
            Storyboard 分镜脚本
        """
        preset = self.presets.get(style, self.presets["cinematic"])
        rhythm_pattern = RHYTHM_TEMPLATES.get(rhythm, preset["rhythm"]) if rhythm else preset["rhythm"]

        # 情绪序列：钩子→展开→高潮→收束
        emotion_sequence = self._build_emotion_sequence(shot_count)

        # 生成镜头
        shots = []
        for i in range(shot_count):
            # 景别（循环使用预设序列）
            shot_size = preset["shot_size"][i % len(preset["shot_size"])]

            # 运镜
            camera_move = preset["camera_move"][i % len(preset["camera_move"])]
            move_intensity = self._calc_move_intensity(camera_move, emotion_sequence[i])

            # 时长（根据节奏模板分配）
            duration = total_duration * rhythm_pattern[i % len(rhythm_pattern)]

            # 转场（第一个镜头无入场转场）
            if i == 0:
                transition_in = "无"
                transition_duration = 0.0
            else:
                trans = TRANSITION_BY_EMOTION.get(emotion_sequence[i], TRANSITION_BY_EMOTION["展开"])
                transition_in = trans["type"]
                transition_duration = trans["duration"]

            # 色调
            color_tone = preset["color"][i % len(preset["color"])]

            # 字幕
            if custom_subtitles and i < len(custom_subtitles):
                subtitle = custom_subtitles[i]
            elif i == 0 and hook_text:
                subtitle = hook_text
            elif i == shot_count - 1 and ending_text:
                subtitle = ending_text
            else:
                subtitle = self._auto_subtitle(theme, i, shot_count, emotion_sequence[i])

            # 音效提示
            sfx_hint = self._sfx_hint(emotion_sequence[i], i)

            shot = Shot(
                index=i,
                duration=round(duration, 2),
                shot_size=shot_size,
                camera_move=camera_move,
                move_intensity=move_intensity,
                transition_in=transition_in,
                transition_duration=transition_duration,
                emotion=emotion_sequence[i],
                subtitle=subtitle,
                subtitle_style=preset["subtitle_style"],
                color_tone=color_tone,
                sfx_hint=sfx_hint,
            )
            shots.append(shot)

        return Storyboard(
            theme=theme,
            style=style,
            total_duration=total_duration,
            shots=shots,
            hook_text=hook_text or shots[0].subtitle,
            ending_text=ending_text or shots[-1].subtitle,
            bgm_mood=preset["bgm_mood"],
            intro_style=preset["intro_style"],
            outro_style=preset["intro_style"],
        )

    def _build_emotion_sequence(self, count: int) -> List[str]:
        """构建情绪序列：钩子→展开→高潮→收束"""
        if count <= 2:
            return ["钩子", "收束"]
        if count == 3:
            return ["钩子", "高潮", "收束"]
        if count == 4:
            return ["钩子", "展开", "高潮", "收束"]
        # 5+镜头：钩子→展开→展开→高潮→收束
        seq = ["钩子"]
        middle = count - 2
        for i in range(middle):
            if i < middle // 2:
                seq.append("展开")
            elif i == middle // 2 and middle % 2 == 1:
                seq.append("高潮")
            else:
                seq.append("高潮" if i == middle - 1 else "展开")
        seq.append("收束")
        return seq[:count]

    def _calc_move_intensity(self, camera_move: str, emotion: str) -> float:
        """根据运镜类型和情绪计算强度"""
        base = {"推": 0.10, "拉": 0.10, "移右": 0.08, "移左": 0.08,
                "固定": 0.0, "缓推": 0.05, "缓拉": 0.05, "快推": 0.15, "快切": 0.12}
        intensity = base.get(camera_move, 0.08)
        # 情绪调节
        if emotion in ["高潮", "紧张", "钩子"]:
            intensity *= 1.3
        elif emotion in ["收束", "平静"]:
            intensity *= 0.7
        return round(min(intensity, 0.2), 3)

    def _auto_subtitle(self, theme: str, index: int, total: int, emotion: str) -> str:
        """自动生成字幕文案（简单模板，实际应结合创意引擎）"""
        templates = {
            "钩子": [f"{theme}，你敢信？", f"这就是{theme}", f"关于{theme}的秘密"],
            "展开": [f"原来如此", f"继续看", f"细节在这里"],
            "高潮": [f"太震撼了", f"绝了", f"这就是{theme}的魅力"],
            "收束": [f"这就是{theme}", f"你学会了吗", f"关注我，了解更多"],
            "平静": [f"{theme}日常", f"记录一下", f"美好瞬间"],
            "紧张": [f"屏住呼吸", f"接下来...", f"注意看"],
            "欢快": [f"开心", f"太棒了", f"耶！"],
            "神秘": [f"你发现了吗", f"仔细看", f"隐藏的细节"],
        }
        options = templates.get(emotion, templates["展开"])
        return options[index % len(options)]

    def _sfx_hint(self, emotion: str, index: int) -> str:
        """音效提示"""
        hints = {
            "钩子": "whoosh/boom",
            "展开": "轻柔过渡",
            "高潮": "鼓点/冲击",
            "收束": "淡出/收尾",
            "平静": "环境音",
            "紧张": "心跳/riser",
            "欢快": "pop/ding",
            "神秘": "低频/氛围",
        }
        return hints.get(emotion, "")

    def list_styles(self) -> List[Dict[str, str]]:
        """列出可用风格"""
        return [{"key": k, "desc": v.get("bgm_mood", "")} for k, v in self.presets.items()]


# ==================== 便捷函数 ====================

def generate_storyboard(theme: str, style: str = "cinematic",
                        total_duration: float = 15.0, shot_count: int = 5,
                        **kwargs) -> Storyboard:
    """一键生成分镜脚本"""
    gen = StoryboardGenerator()
    return gen.generate(theme, style, total_duration, shot_count, **kwargs)


def list_storyboard_styles() -> List[Dict[str, str]]:
    """列出可用风格"""
    return StoryboardGenerator().list_styles()


# ==================== 多机位对话模式（P3-4增强） ====================

@dataclass
class DialogueShot:
    """对话分镜（多机位）"""
    shot_type: str  # 主镜头/正反打/过肩/反应/特写
    character: str  # 焦点角色
    other_character: str = ""  # 对话对象（过肩镜头用）
    duration: float = 3.0
    shot_size: str = "中近景"
    camera_move: str = "固定"
    notes: str = ""


class MultiCameraDialogue:
    """多机位对话分镜生成器

    标准对话场景镜头语言：
    1. 建立镜头（双人/全景）- 交代空间关系
    2. 主镜头（中近景）- 角色A说话
    3. 反打（中近景）- 角色B说话
    4. 过肩镜头 - 增强空间感
    5. 反应特写 - 情绪强调
    """

    def generate_dialogue_sequence(self,
                                     character_a: str,
                                     character_b: str,
                                     dialogue_a: str = "",
                                     dialogue_b: str = "",
                                     emotion: str = "平静",
                                     total_duration: float = 10.0) -> List[DialogueShot]:
        """生成对话场景的多机位分镜序列"""
        shots = []

        # 1. 建立镜头
        shots.append(DialogueShot(
            shot_type="建立镜头",
            character=character_a,
            other_character=character_b,
            duration=total_duration * 0.15,
            shot_size="全景",
            camera_move="固定",
            notes=f"交代{character_a}和{character_b}的空间关系",
        ))

        # 2. 角色A主镜头
        if dialogue_a:
            shots.append(DialogueShot(
                shot_type="主镜头",
                character=character_a,
                other_character=character_b,
                duration=total_duration * 0.30,
                shot_size="中近景",
                camera_move="固定",
                notes=f"{character_a}说话：{dialogue_a[:30]}",
            ))

        # 3. 角色B反打
        if dialogue_b:
            shots.append(DialogueShot(
                shot_type="反打",
                character=character_b,
                other_character=character_a,
                duration=total_duration * 0.30,
                shot_size="中近景",
                camera_move="固定",
                notes=f"{character_b}回应：{dialogue_b[:30]}",
            ))

        # 4. 过肩镜头（增强空间感）
        shots.append(DialogueShot(
            shot_type="过肩镜头",
            character=character_a,
            other_character=character_b,
            duration=total_duration * 0.15,
            shot_size="中景",
            camera_move="固定",
            notes=f"从{character_b}肩后拍{character_a}",
        ))

        # 5. 反应特写（情绪强调）
        if emotion in ["激动", "悲伤", "愤怒", "感动"]:
            shots.append(DialogueShot(
                shot_type="反应特写",
                character=character_b,
                other_character=character_a,
                duration=total_duration * 0.10,
                shot_size="特写",
                camera_move="固定",
                notes=f"{character_b}的情绪反应（{emotion}）",
            ))

        return shots


# ==================== 蒙太奇支持（P3-4增强） ====================

class MontageBuilder:
    """蒙太奇序列构建器

    蒙太奇类型：
    - 平行蒙太奇：两条线索同时发生，交替展示
    - 交叉蒙太奇：两条线索交替，最终汇合（制造紧张）
    - 隐喻蒙太奇：通过对比/象征表达含义
    - 节奏蒙太奇：通过节奏变化表达情绪
    - 连续蒙太奇：按时间顺序连续叙述
    """

    def build_parallel_montage(self,
                                  line_a: List[Dict[str, Any]],
                                  line_b: List[Dict[str, Any]],
                                  interval: int = 1) -> List[Dict[str, Any]]:
        """平行蒙太奇：两条线索交替展示

        Args:
            line_a: 线索A的镜头列表
            line_b: 线索B的镜头列表
            interval: 交替间隔（每几个镜头切换一次）

        Returns:
            交替后的镜头列表
        """
        result = []
        i, j = 0, 0
        while i < len(line_a) or j < len(line_b):
            for _ in range(interval):
                if i < len(line_a):
                    result.append({**line_a[i], "montage_line": "A", "montage_type": "平行蒙太奇"})
                    i += 1
            for _ in range(interval):
                if j < len(line_b):
                    result.append({**line_b[j], "montage_line": "B", "montage_type": "平行蒙太奇"})
                    j += 1
        return result

    def build_cross_montage(self,
                               line_a: List[Dict[str, Any]],
                               line_b: List[Dict[str, Any]],
                               convergence_point: int = -1) -> List[Dict[str, Any]]:
        """交叉蒙太奇：两条线索交替，节奏加快，最终汇合

        Args:
            line_a: 线索A的镜头列表
            line_b: 线索B的镜头列表
            convergence_point: 汇合点索引（-1表示最后汇合）

        Returns:
            交替后的镜头列表（节奏逐渐加快）
        """
        result = []
        i, j = 0, 0
        total = len(line_a) + len(line_b)
        step = 0

        while i < len(line_a) or j < len(line_b):
            # 节奏逐渐加快：从2个一组变为1个一组
            group_size = max(1, 2 - step // (total // 4))

            for _ in range(group_size):
                if i < len(line_a):
                    shot = {**line_a[i], "montage_line": "A", "montage_type": "交叉蒙太奇"}
                    if i == len(line_a) - 1 and convergence_point in [-1, i]:
                        shot["montage_convergence"] = True
                    result.append(shot)
                    i += 1
            for _ in range(group_size):
                if j < len(line_b):
                    shot = {**line_b[j], "montage_line": "B", "montage_type": "交叉蒙太奇"}
                    if j == len(line_b) - 1 and convergence_point in [-1, j]:
                        shot["montage_convergence"] = True
                    result.append(shot)
                    j += 1
            step += 1

        return result

    def build_montage_from_shots(self,
                                    shots: List[Dict[str, Any]],
                                    montage_type: str = "节奏蒙太奇",
                                    target_duration: float = 15.0) -> List[Dict[str, Any]]:
        """将普通镜头序列转换为蒙太奇序列

        Args:
            shots: 原始镜头列表
            montage_type: 蒙太奇类型
            target_duration: 目标总时长

        Returns:
            蒙太奇化的镜头列表
        """
        if not shots:
            return []

        # 节奏蒙太奇：前慢后快，制造情绪递进
        if montage_type == "节奏蒙太奇":
            n = len(shots)
            result = []
            for i, shot in enumerate(shots):
                # 前1/3慢，中间1/3中，后1/3快
                if i < n // 3:
                    duration = target_duration * 0.5 / (n // 3)
                elif i < 2 * n // 3:
                    duration = target_duration * 0.3 / (n // 3)
                else:
                    duration = target_duration * 0.2 / max(1, n - 2 * n // 3)
                result.append({
                    **shot,
                    "duration": round(duration, 2),
                    "montage_type": "节奏蒙太奇",
                    "montage_phase": "慢" if i < n // 3 else "中" if i < 2 * n // 3 else "快",
                })
            return result

        # 连续蒙太奇：保持原顺序，均匀时长
        elif montage_type == "连续蒙太奇":
            avg_duration = target_duration / len(shots)
            return [{**shot, "duration": round(avg_duration, 2), "montage_type": "连续蒙太奇"} for shot in shots]

        # 默认：标记蒙太奇类型
        return [{**shot, "montage_type": montage_type} for shot in shots]
