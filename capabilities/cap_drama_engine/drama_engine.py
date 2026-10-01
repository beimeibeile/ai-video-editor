"""
影视剧剧本引擎 v1.0
剧本解析改编 → 角色性格和分剧情重塑 → 全剧分镜头定版

核心流程：
1. 剧本解析：从文本/文件解析剧本，识别场景、角色、对话、动作
2. 角色管理：角色性格、关系、出场统计
3. 分剧情重塑：按场景/幕/集拆分，支持多轮打磨
4. 分镜头定版：每场戏拆分为镜头，输出标准化分镜表

使用方法：
    from drama_engine import DramaEngine
    engine = DramaEngine()
    script = engine.parse_script("剧本内容或文件路径")
    characters = engine.analyze_characters(script)
    storyboard = engine.generate_storyboard(script)
"""
import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class SceneType(Enum):
    """场景类型"""
    INTERIOR = "内景"
    EXTERIOR = "外景"
    MIXED = "内外景"


class ShotSize(Enum):
    """景别"""
    EXTREME_LONG = "大远景"
    LONG = "远景"
    FULL = "全景"
    MEDIUM = "中景"
    MEDIUM_CLOSE = "中近景"
    CLOSE = "近景"
    BIG_CLOSE = "特写"
    EXTREME_CLOSE = "大特写"


class CameraMove(Enum):
    """运镜"""
    FIXED = "固定"
    PAN = "摇"
    TILT = "移"
    DOLLY = "推拉"
    ZOOM = "变焦"
    HANDHELD = "手持"
    TRACKING = "跟拍"
    CRANE = "升降"


@dataclass
class Character:
    """角色"""
    name: str
    description: str = ""
    personality: str = ""
    appearance: str = ""
    relationships: Dict[str, str] = field(default_factory=dict)  # 角色名→关系
    line_count: int = 0
    scene_count: int = 0
    first_appearance: str = ""


@dataclass
class Dialogue:
    """对话"""
    character: str
    text: str
    emotion: str = ""
    action: str = ""  # 说话时的动作


@dataclass
class Action:
    """动作/场景描述"""
    text: str
    characters: List[str] = field(default_factory=list)


@dataclass
class Beat:
    """节拍（场景内的小单元）"""
    beat_type: str  # dialogue/action/transition/monologue
    content: str
    character: str = ""
    emotion: str = ""
    duration_estimate: float = 0  # 预估时长（秒）


@dataclass
class Scene:
    """场景"""
    scene_id: str
    title: str = ""
    scene_type: str = ""  # 内景/外景
    location: str = ""
    time_of_day: str = ""  # 日/夜/晨/昏
    characters: List[str] = field(default_factory=list)
    beats: List[Beat] = field(default_factory=list)
    summary: str = ""
    duration_estimate: float = 0


@dataclass
class Shot:
    """分镜"""
    shot_id: str
    scene_id: str
    shot_number: int
    shot_size: str  # 景别
    camera_move: str  # 运镜
    description: str  # 画面描述
    dialogue: str = ""
    character: str = ""
    duration: float = 3.0  # 时长（秒）
    notes: str = ""


@dataclass
class DramaScript:
    """影视剧剧本"""
    title: str = ""
    author: str = ""
    genre: str = ""
    logline: str = ""  # 一句话故事
    synopsis: str = ""  # 故事梗概
    characters: Dict[str, Character] = field(default_factory=dict)
    scenes: List[Scene] = field(default_factory=list)
    acts: List[Dict[str, Any]] = field(default_factory=list)  # 幕结构
    total_duration_estimate: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DramaEngine:
    """影视剧剧本引擎"""

    def __init__(self):
        self.script: Optional[DramaScript] = None

    def parse_script(self, input_data: str) -> DramaScript:
        """
        解析剧本

        Args:
            input_data: 剧本文本内容或文件路径

        Returns:
            DramaScript 对象
        """
        # 如果是文件路径，读取文件
        if os.path.exists(input_data):
            with open(input_data, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            text = input_data

        script = DramaScript()

        # 1. 提取标题和元信息
        script = self._extract_metadata(text, script)

        # 2. 按场景分割
        script.scenes = self._split_scenes(text)

        # 3. 分析角色
        script.characters = self._analyze_characters_from_scenes(script.scenes)

        # 4. 估算总时长
        script.total_duration_estimate = sum(s.duration_estimate for s in script.scenes)

        self.script = script
        print(f"✅ 剧本解析完成: {script.title or '未命名'}")
        print(f"   场景数: {len(script.scenes)}")
        print(f"   角色数: {len(script.characters)}")
        print(f"   预估时长: {script.total_duration_estimate:.0f}秒 ({script.total_duration_estimate/60:.1f}分钟)")

        return script

    def _extract_metadata(self, text: str, script: DramaScript) -> DramaScript:
        """提取剧本元信息"""
        lines = text.split("\n")

        for i, line in enumerate(lines[:30]):  # 只看前30行
            line = line.strip()
            if not line:
                continue

            # 标题
            if i == 0 and not script.title:
                script.title = line
                continue

            # 作者
            if re.match(r'^(作者|编剧|Author|Written by)\s*[:：]', line, re.I):
                script.author = re.sub(r'^(作者|编剧|Author|Written by)\s*[:：]\s*', '', line, flags=re.I)
                continue

            # 类型
            if re.match(r'^(类型|题材|Genre)\s*[:：]', line, re.I):
                script.genre = re.sub(r'^(类型|题材|Genre)\s*[:：]\s*', '', line, flags=re.I)
                continue

            # 一句话故事
            if re.match(r'^(一句话|故事梗概|Logline|Synopsis)\s*[:：]', line, re.I):
                script.logline = re.sub(r'^(一句话|故事梗概|Logline|Synopsis)\s*[:：]\s*', '', line, flags=re.I)
                continue

        return script

    def _split_scenes(self, text: str) -> List[Scene]:
        """按场景分割剧本"""
        scenes = []

        # 场景标题模式：内景/外景 + 地点 + 时间
        # 例如：内景 咖啡馆 - 日
        scene_pattern = re.compile(
            r'^(内景|外景|内外景|INT\.|EXT\.|INT/EXT)\s+(.+?)(?:\s*[-—–]\s*(日|夜|晨|昏|黎明|黄昏))?\s*$',
            re.MULTILINE | re.IGNORECASE
        )

        matches = list(scene_pattern.finditer(text))

        if not matches:
            # 没有标准场景标题，按空行分割
            blocks = re.split(r'\n\s*\n', text)
            for i, block in enumerate(blocks):
                if block.strip():
                    scene = Scene(
                        scene_id=f"S{i+1:03d}",
                        title=f"场景{i+1}",
                        beats=self._parse_beats(block),
                    )
                    scene.duration_estimate = sum(b.duration_estimate for b in scene.beats)
                    scenes.append(scene)
            return scenes

        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            scene_text = text[start:end].strip()

            scene_type = match.group(1)
            location = match.group(2).strip()
            time_of_day = match.group(3) or ""

            scene = Scene(
                scene_id=f"S{i+1:03d}",
                title=f"{scene_type} {location}",
                scene_type=scene_type,
                location=location,
                time_of_day=time_of_day,
                beats=self._parse_beats(scene_text),
            )
            scene.duration_estimate = sum(b.duration_estimate for b in scene.beats)
            scenes.append(scene)

        return scenes

    def _parse_beats(self, text: str) -> List[Beat]:
        """解析场景内的节拍"""
        beats = []
        lines = text.split("\n")

        current_character = ""
        current_dialogue = []

        for line in lines:
            line = line.strip()
            if not line:
                if current_dialogue and current_character:
                    beats.append(Beat(
                        beat_type="dialogue",
                        content=" ".join(current_dialogue),
                        character=current_character,
                        duration_estimate=len(" ".join(current_dialogue)) * 0.2,  # 每字约0.2秒
                    ))
                    current_dialogue = []
                    current_character = ""
                continue

            # 角色名（全大写或中文角色名，后面可能跟括号情绪）
            char_match = re.match(r'^([A-Z\u4e00-\u9fa5]{2,10})(?:\s*[（(](.+?)[）)])?\s*$', line)
            if char_match and len(line) < 20:
                if current_dialogue and current_character:
                    beats.append(Beat(
                        beat_type="dialogue",
                        content=" ".join(current_dialogue),
                        character=current_character,
                        duration_estimate=len(" ".join(current_dialogue)) * 0.2,
                    ))
                    current_dialogue = []
                current_character = char_match.group(1)
                emotion = char_match.group(2) or ""
                continue

            # 动作描述（括号内或普通段落）
            if line.startswith("(") or line.startswith("（"):
                beats.append(Beat(
                    beat_type="action",
                    content=line.strip("()（）"),
                    duration_estimate=2.0,
                ))
                continue

            # 对话内容
            if current_character:
                current_dialogue.append(line)
            else:
                # 场景描述
                beats.append(Beat(
                    beat_type="action",
                    content=line,
                    duration_estimate=3.0,
                ))

        # 处理最后一段对话
        if current_dialogue and current_character:
            beats.append(Beat(
                beat_type="dialogue",
                content=" ".join(current_dialogue),
                character=current_character,
                duration_estimate=len(" ".join(current_dialogue)) * 0.2,
            ))

        return beats

    def _analyze_characters_from_scenes(self, scenes: List[Scene]) -> Dict[str, Character]:
        """从场景中分析角色"""
        characters = {}

        for scene in scenes:
            scene_chars = set()
            for beat in scene.beats:
                if beat.character and beat.character not in characters:
                    characters[beat.character] = Character(
                        name=beat.character,
                        first_appearance=scene.scene_id,
                    )
                if beat.character:
                    characters[beat.character].line_count += 1
                    scene_chars.add(beat.character)

            for char_name in scene_chars:
                if char_name in characters:
                    characters[char_name].scene_count += 1

        return characters

    def analyze_characters(self, script: DramaScript = None) -> Dict[str, Character]:
        """分析角色（可扩展性格和关系）"""
        if script is None:
            script = self.script
        if script is None:
            return {}
        return script.characters

    def generate_storyboard(self, script: DramaScript = None,
                            shot_duration: float = 3.0) -> List[Shot]:
        """
        生成分镜表

        Args:
            script: 剧本对象
            shot_duration: 默认单镜时长

        Returns:
            分镜列表
        """
        if script is None:
            script = self.script
        if script is None:
            return []

        shots = []
        shot_counter = 1

        for scene in script.scenes:
            for beat in scene.beats:
                if beat.beat_type == "dialogue":
                    # 对话：中近景或近景，根据情绪调整
                    shot_size = "近景" if beat.emotion in ["激动", "愤怒", "哭泣"] else "中近景"
                    shots.append(Shot(
                        shot_id=f"SH{shot_counter:04d}",
                        scene_id=scene.scene_id,
                        shot_number=shot_counter,
                        shot_size=shot_size,
                        camera_move="固定",
                        description=f"{beat.character}说话：{beat.content[:30]}...",
                        dialogue=beat.content,
                        character=beat.character,
                        duration=max(shot_duration, beat.duration_estimate),
                    ))
                    shot_counter += 1

                elif beat.beat_type == "action":
                    # 动作：全景或中景，可能需要运镜
                    shots.append(Shot(
                        shot_id=f"SH{shot_counter:04d}",
                        scene_id=scene.scene_id,
                        shot_number=shot_counter,
                        shot_size="全景" if "环境" in beat.content or "场景" in beat.content else "中景",
                        camera_move="移" if len(beat.content) > 20 else "固定",
                        description=beat.content[:50],
                        duration=max(shot_duration, beat.duration_estimate),
                    ))
                    shot_counter += 1

        print(f"✅ 分镜生成: {len(shots)}个镜头")
        return shots

    def export_to_json(self, output_path: str, script: DramaScript = None):
        """导出剧本为JSON"""
        if script is None:
            script = self.script
        if script is None:
            return

        data = asdict(script)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 剧本已导出: {output_path}")

    def export_storyboard_to_json(self, output_path: str, shots: List[Shot]):
        """导出分镜表为JSON"""
        data = [asdict(s) for s in shots]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 分镜表已导出: {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("影视剧剧本引擎 v1.0")
    print("=" * 60)

    # 测试用例
    test_script = """测试剧本
作者: 测试编剧
类型: 剧情

内景 咖啡馆 - 日

小明
（紧张）
你好，我是小明。

小红
（微笑）
你好，很高兴认识你。

（两人握手，气氛融洽）

外景 公园 - 黄昏

小明
这里的风景真美。

小红
是啊，我们常来这里散步。
"""

    engine = DramaEngine()
    script = engine.parse_script(test_script)

    print("\n角色分析:")
    for name, char in script.characters.items():
        print(f"  {name}: {char.line_count}句台词, {char.scene_count}个场景")

    shots = engine.generate_storyboard(script)
    print(f"\n分镜数: {len(shots)}")
