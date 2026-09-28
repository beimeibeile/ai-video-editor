"""
分镜脚本生成器 - 专业分镜设计

每个镜头包含：
- 景别（特写/近景/中景/全景/远景）
- 运镜方式（zoom_in/zoom_out/pan_left/pan_right等）
- 转场类型
- 字幕内容和风格
- 音效提示
- 调色建议
- 素材选择建议
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from .templates import get_template


def align_to_frame(seconds: float, fps: int = 30) -> float:
    """
    将时长对齐到帧边界，返回秒数（保留3位小数）
    
    视频平台标准帧率：30fps或60fps
    30fps: 每帧=1/30秒≈0.0333秒
    60fps: 每帧=1/60秒≈0.0167秒
    
    这样可以确保所有片段时长是帧的整数倍，避免浮点数精度导致的重叠或间隙。
    """
    frame_duration = 1.0 / fps
    total_frames = round(seconds / frame_duration)
    return round(total_frames * frame_duration, 3)


def align_to_frame_us(seconds: float, fps: int = 30) -> int:
    """将时长对齐到帧边界，返回微秒整数"""
    return int(round(align_to_frame(seconds, fps) * 1000000))


@dataclass
class Shot:
    """单个镜头"""
    index: int
    duration: float  # 秒
    shot_type: str  # 特写/近景/中景/全景/远景
    camera_move: str  # 运镜方式
    transition_in: str  # 入点转场
    transition_out: str  # 出点转场
    subtitle: str = ""  # 字幕内容
    subtitle_style: str = "minimal"  # 字幕风格
    sfx: str = ""  # 音效关键词
    bgm_mood: str = ""  # BGM情绪
    material_hint: str = ""  # 素材选择建议
    color_grade: str = ""  # 调色建议
    notes: str = ""  # 备注


@dataclass
class Storyboard:
    """分镜脚本"""
    title: str
    hook: str
    theme: str
    style: str
    total_duration: float
    rhythm: str  # 快切/舒缓/递进/混合
    shots: List[Shot] = field(default_factory=list)
    bgm_recommendation: str = ""
    color_grade_overall: str = ""
    creative_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "hook": self.hook,
            "theme": self.theme,
            "style": self.style,
            "total_duration": self.total_duration,
            "rhythm": self.rhythm,
            "bgm_recommendation": self.bgm_recommendation,
            "color_grade_overall": self.color_grade_overall,
            "creative_notes": self.creative_notes,
            "shots": [asdict(s) for s in self.shots],
        }

    def to_markdown(self) -> str:
        """导出为Markdown格式，供用户审阅"""
        lines = [
            f"# 分镜脚本：{self.title}",
            "",
            f"**主题**：{self.theme}  ",
            f"**风格**：{self.style}  ",
            f"**节奏**：{self.rhythm}  ",
            f"**总时长**：{self.total_duration:.1f}秒  ",
            f"**开篇钩子**：{self.hook}  ",
            f"**BGM建议**：{self.bgm_recommendation}  ",
            f"**整体调色**：{self.color_grade_overall}  ",
            "",
        ]

        if self.creative_notes:
            lines.extend([
                "## 创意说明",
                "",
                self.creative_notes,
                "",
            ])

        lines.extend([
            "## 分镜表",
            "",
            "| 镜号 | 时长 | 景别 | 运镜 | 转场(入/出) | 字幕 | 音效 | 素材建议 |",
            "|------|------|------|------|-------------|------|------|----------|",
        ])

        for shot in self.shots:
            trans = f"{shot.transition_in}/{shot.transition_out}"
            lines.append(
                f"| {shot.index+1} | {shot.duration:.1f}s | {shot.shot_type} | "
                f"{shot.camera_move} | {trans} | {shot.subtitle} | {shot.sfx} | {shot.material_hint} |"
            )

        lines.extend(["", "## 详细说明", ""])
        for shot in self.shots:
            lines.extend([
                f"### 镜头 {shot.index+1}（{shot.duration:.1f}秒）",
                f"- **景别**：{shot.shot_type}",
                f"- **运镜**：{shot.camera_move}",
                f"- **转场**：入={shot.transition_in}, 出={shot.transition_out}",
                f"- **字幕**：{shot.subtitle}（风格：{shot.subtitle_style}）",
                f"- **音效**：{shot.sfx}",
                f"- **素材建议**：{shot.material_hint}",
                f"- **调色**：{shot.color_grade}",
            ])
            if shot.notes:
                lines.append(f"- **备注**：{shot.notes}")
            lines.append("")

        return "\n".join(lines)

    def save(self, output_path: str, fmt: str = "json"):
        """保存分镜脚本到文件"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        if fmt == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        elif fmt == "md":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_markdown())


class StoryboardGenerator:
    """分镜脚本生成器"""

    # 景别定义
    SHOT_TYPES = ["特写", "近景", "中景", "全景", "远景"]

    # 运镜方式
    CAMERA_MOVES = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "static"]

    def __init__(self, theme: str = "极简"):
        # 标准化主题名（解析别名）
        from .templates import THEME_ALIASES
        self.theme = THEME_ALIASES.get(theme, theme)
        self.template = get_template(theme)

    def generate(self,
                 num_shots: int = 6,
                 title: str = "",
                 hook: str = "",
                 total_duration: Optional[float] = None,
                 custom_subtitles: Optional[List[str]] = None,
                 ) -> Storyboard:
        """
        生成分镜脚本

        Args:
            num_shots: 镜头数量
            title: 视频标题
            hook: 开篇钩子
            total_duration: 总时长（None则根据模板自动计算）
            custom_subtitles: 自定义字幕列表
        """
        template = self.template
        shot_duration = template.get("duration_per_shot", 3.0)

        if total_duration is None:
            total_duration = num_shots * shot_duration

        # 计算每个镜头的时长（根据节奏调整）
        rhythm = template.get("rhythm", "舒缓")
        durations = self._calculate_durations(num_shots, shot_duration, rhythm)

        # 生成镜头序列
        shot_seq = self._cycle_sequence(template.get("shot_sequence", self.SHOT_TYPES), num_shots)
        camera_seq = self._cycle_sequence(template.get("camera_sequence", ["zoom_in"]), num_shots)
        trans_seq = self._cycle_sequence(template.get("transition_sequence", ["dissolve"]), num_shots - 1)

        # 生成字幕
        subtitles = custom_subtitles or self._generate_subtitles(num_shots, template)

        shots = []
        for i in range(num_shots):
            trans_in = "none" if i == 0 else trans_seq[i - 1]
            trans_out = trans_seq[i] if i < num_shots - 1 else "none"

            shot = Shot(
                index=i,
                duration=durations[i],
                shot_type=shot_seq[i],
                camera_move=camera_seq[i],
                transition_in=trans_in,
                transition_out=trans_out,
                subtitle=subtitles[i] if i < len(subtitles) else "",
                subtitle_style=template.get("subtitle_style", "minimal"),
                sfx=template.get("sfx_hints", [""])[i % len(template.get("sfx_hints", [""]))],
                bgm_mood=template.get("bgm_mood", ""),
                material_hint=self._generate_material_hint(i, num_shots, shot_seq[i]),
                color_grade=template.get("color_grade", ""),
            )
            shots.append(shot)

        storyboard = Storyboard(
            title=title or f"{self.theme}主题视频",
            hook=hook or template.get("hook_templates", ["视觉盛宴"])[0],
            theme=self.theme,
            style=template.get("name", self.theme),
            total_duration=total_duration,
            rhythm=rhythm,
            shots=shots,
            bgm_recommendation=template.get("bgm_mood", ""),
            color_grade_overall=template.get("color_grade", ""),
            creative_notes=self._generate_creative_notes(template, num_shots),
        )

        return storyboard

    def _calculate_durations(self, num_shots: int, base_duration: float, rhythm: str) -> List[float]:
        """根据节奏计算每个镜头的时长（帧对齐到30fps）"""
        if rhythm == "快切":
            raw = [base_duration * 0.7] * num_shots
        elif rhythm == "舒缓":
            raw = [base_duration * 1.2] * num_shots
        elif rhythm == "递进":
            # 从慢到快
            raw = [base_duration * (1.3 - i * 0.1) for i in range(num_shots)]
        else:  # 混合
            raw = []
            for i in range(num_shots):
                if i == 0:
                    raw.append(base_duration * 1.3)  # 开篇稍长
                elif i == num_shots - 1:
                    raw.append(base_duration * 1.2)  # 结尾稍长
                else:
                    raw.append(base_duration * 0.9)  # 中间紧凑
        # 帧对齐到30fps，确保时长是帧的整数倍
        return [align_to_frame(d, fps=30) for d in raw]

    def _cycle_sequence(self, seq: List[str], count: int) -> List[str]:
        """循环序列到指定长度"""
        if not seq:
            return ["static"] * count
        return [seq[i % len(seq)] for i in range(count)]

    def _generate_subtitles(self, num_shots: int, template: Dict) -> List[str]:
        """生成字幕内容"""
        # 基于主题生成简单字幕
        theme = self.theme
        base_phrases = {
            "赛博朋克": ["未来已来", "霓虹之下", "机械之心", "赛博纪元", "都市迷幻", "科技觉醒"],
            "国风": ["东方美学", "山水之间", "诗意东方", "千年风雅", "国潮新生", "古韵今风"],
            "治愈": ["温柔时光", "小确幸", "慢下来", "感受美好", "生活碎片", "治愈系"],
            "卡点": ["节奏控", "踩点狂魔", "极度舒适", "节拍之上", "视觉冲击", "卡点盛宴"],
            "电影感": ["光影叙事", "帧帧如画", "视觉诗", "电影质感", " cinematic", "大片既视感"],
            "极简": ["少即是多", "留白之美", "简约不简单", "纯净视觉", "极简主义", "本质之美"],
            "复古": ["时光倒流", "旧时光", "胶片记忆", "年代感", "复古回潮", "怀旧经典"],
        }
        phrases = base_phrases.get(theme, ["视觉盛宴", "精彩瞬间", "美好时刻", "光影记录", "帧帧如画", "完美呈现"])
        return phrases[:num_shots]

    def _generate_material_hint(self, index: int, total: int, shot_type: str) -> str:
        """生成素材选择建议"""
        hints = {
            "特写": "选择细节丰富、有视觉冲击力的素材",
            "近景": "选择主体突出、表情/动作清晰的素材",
            "中景": "选择环境与主体平衡的素材",
            "全景": "选择场景宏大、有空间感的素材",
            "远景": "选择气势磅礴、有氛围感的素材",
        }
        base = hints.get(shot_type, "选择与主题匹配的素材")

        # 位置建议
        if index == 0:
            return f"开篇镜头：{base}，建议最有冲击力的素材"
        elif index == total - 1:
            return f"结尾镜头：{base}，建议有余韵的素材"
        else:
            return f"过渡镜头：{base}"

    def _generate_creative_notes(self, template: Dict, num_shots: int) -> str:
        """生成创意说明"""
        rhythm = template.get("rhythm", "舒缓")
        notes = [
            f"本片采用{rhythm}节奏，共{num_shots}个镜头。",
            f"整体风格为{template.get('name', self.theme)}，调色建议：{template.get('color_grade', '标准调色')}。",
            f"BGM建议选择{template.get('bgm_mood', '轻音乐')}风格。",
        ]

        if rhythm == "快切":
            notes.append("快切节奏要求每个镜头都有明确的视觉焦点，转场要干脆利落。")
        elif rhythm == "舒缓":
            notes.append("舒缓节奏注重情绪铺垫，运镜要平稳流畅，给观众留足感受时间。")
        elif rhythm == "递进":
            notes.append("递进节奏从慢到快，情绪逐步升温，结尾达到高潮。")

        return "\n".join(notes)
