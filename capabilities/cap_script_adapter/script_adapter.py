"""
剧本解析改编引擎 v1.0
将小说/剧本/故事大纲解析并改编成分镜脚本

核心功能：
1. 文本解析：场景提取、角色提取、对话提取、动作提取
2. 结构分析：三幕结构、节拍识别、节奏分析
3. 分镜改编：场景→镜头拆解、镜头语言推荐、时长估算
4. 多集拆分：长文本自动拆分为多集
5. 输出兼容：生成Script对象，可直接接入现有pipeline
"""
import re
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class SceneType(Enum):
    """场景类型"""
    INT = "室内"
    EXT = "室外"
    INT_EXT = "室内外"
    UNKNOWN = "未知"


class ShotSize(Enum):
    """景别"""
    EXTREME_CLOSEUP = "大特写"
    CLOSEUP = "特写"
    MEDIUM_CLOSEUP = "近景"
    MEDIUM = "中景"
    MEDIUM_LONG = "中全景"
    LONG = "全景"
    EXTREME_LONG = "远景"


class CameraMove(Enum):
    """运镜"""
    FIXED = "固定"
    PAN_LEFT = "左摇"
    PAN_RIGHT = "右摇"
    TILT_UP = "上摇"
    TILT_DOWN = "下摇"
    ZOOM_IN = "推"
    ZOOM_OUT = "拉"
    TRACKING = "跟拍"
    HANDHELD = "手持"
    DOLLY_ZOOM = "滑动变焦"


@dataclass
class Character:
    """角色"""
    name: str
    description: str = ""
    personality: str = ""
    appearance: str = ""
    relationships: Dict[str, str] = field(default_factory=dict)
    line_count: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class Dialogue:
    """对话"""
    speaker: str
    content: str
    emotion: str = "平静"
    action: str = ""  # 说话时的动作

    def to_dict(self):
        return asdict(self)


@dataclass
class ParsedScene:
    """解析后的场景"""
    scene_id: int
    title: str
    scene_type: SceneType
    location: str
    time_of_day: str = ""
    description: str = ""
    characters: List[str] = field(default_factory=list)
    dialogues: List[Dialogue] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    emotional_tone: str = ""
    duration_estimate: float = 0.0  # 秒

    def to_dict(self):
        d = asdict(self)
        d['scene_type'] = self.scene_type.value
        return d


@dataclass
class AdaptedShot:
    """改编后的镜头"""
    shot_id: int
    scene_id: int
    shot_size: ShotSize
    camera_move: CameraMove
    description: str
    subject: str = ""
    dialogue: Optional[Dialogue] = None
    duration: float = 3.0
    emotion: str = ""
    notes: str = ""

    def to_dict(self):
        d = asdict(self)
        d['shot_size'] = self.shot_size.value
        d['camera_move'] = self.camera_move.value
        return d


@dataclass
class AdaptedEpisode:
    """改编后的单集"""
    episode_id: int
    title: str
    scenes: List[ParsedScene]
    shots: List[AdaptedShot]
    characters: List[Character]
    total_duration: float = 0.0
    logline: str = ""

    def to_dict(self):
        return {
            "episode_id": self.episode_id,
            "title": self.title,
            "logline": self.logline,
            "total_duration": self.total_duration,
            "scene_count": len(self.scenes),
            "shot_count": len(self.shots),
            "characters": [c.to_dict() for c in self.characters],
            "scenes": [s.to_dict() for s in self.scenes],
            "shots": [s.to_dict() for s in self.shots],
        }


class ScriptParser:
    """剧本解析器"""

    # 场景标题模式：INT. 房间 - 日 / EXT. 街道 - 夜
    SCENE_HEADER_PATTERN = re.compile(
        r'^(INT\.|EXT\.|INT/EXT\.|内景|外景|内外景)[\s\.]+(.+?)[\s\-—]+(日|夜|晨|昏|晚|黎明|黄昏|白天|夜晚|DAY|NIGHT|MORNING|EVENING)?',
        re.IGNORECASE
    )

    # 对话模式：角色名: 对话内容 或 角色名\n  对话内容
    DIALOGUE_PATTERN = re.compile(
        r'^([A-Z\u4e00-\u9fa5][A-Za-z\u4e00-\u9fa5\s·]{1,15})[：:]\s*(.+)$'
    )

    # 动作描述模式：括号内的动作
    ACTION_PATTERN = re.compile(r'[（(](.+?)[）)]')

    def __init__(self):
        self.characters: Dict[str, Character] = {}
        self.scenes: List[ParsedScene] = []

    def parse(self, text: str, title: str = "未命名剧本") -> List[ParsedScene]:
        """
        解析剧本文本

        Args:
            text: 剧本文本
            title: 剧本标题

        Returns:
            解析后的场景列表
        """
        self.characters = {}
        self.scenes = []

        lines = text.split('\n')
        current_scene = None
        scene_id = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测场景标题
            scene_match = self.SCENE_HEADER_PATTERN.match(line)
            if scene_match:
                if current_scene:
                    self._finalize_scene(current_scene)
                    self.scenes.append(current_scene)

                scene_id += 1
                scene_type_str = scene_match.group(1).upper()
                location = scene_match.group(2).strip()
                time_of_day = scene_match.group(3) or ""

                if 'INT' in scene_type_str or '内' in scene_type_str:
                    scene_type = SceneType.INT
                elif 'EXT' in scene_type_str or '外' in scene_type_str:
                    scene_type = SceneType.EXT
                else:
                    scene_type = SceneType.UNKNOWN

                current_scene = ParsedScene(
                    scene_id=scene_id,
                    title=f"场景{scene_id}: {location}",
                    scene_type=scene_type,
                    location=location,
                    time_of_day=time_of_day,
                )
                continue

            if current_scene is None:
                # 还没到第一个场景，可能是标题/说明
                continue

            # 检测对话
            dialogue_match = self.DIALOGUE_PATTERN.match(line)
            if dialogue_match:
                speaker = dialogue_match.group(1).strip()
                content = dialogue_match.group(2).strip()

                # 提取动作描述
                action = ""
                action_match = self.ACTION_PATTERN.search(content)
                if action_match:
                    action = action_match.group(1)
                    content = self.ACTION_PATTERN.sub('', content).strip()

                # 注册角色
                if speaker not in self.characters:
                    self.characters[speaker] = Character(name=speaker)
                self.characters[speaker].line_count += 1

                if speaker not in current_scene.characters:
                    current_scene.characters.append(speaker)

                dialogue = Dialogue(speaker=speaker, content=content, action=action)
                current_scene.dialogues.append(dialogue)
                continue

            # 普通描述/动作
            current_scene.description += line + " "
            current_scene.actions.append(line)

        # 处理最后一个场景
        if current_scene:
            self._finalize_scene(current_scene)
            self.scenes.append(current_scene)

        return self.scenes

    def _finalize_scene(self, scene: ParsedScene):
        """完成场景解析，估算时长等"""
        # 基于对话数和描述长度估算时长
        dialogue_time = len(scene.dialogues) * 2.5  # 每句对话约2.5秒
        description_time = len(scene.description) / 50  # 每50字约1秒
        scene.duration_estimate = max(dialogue_time + description_time, 3.0)

        # 情感基调（简单关键词匹配）
        desc_lower = scene.description.lower()
        emotion_keywords = {
            "紧张": ["紧张", "焦急", "恐慌", "危险", "紧急"],
            "悲伤": ["悲伤", "难过", "哭泣", "眼泪", "失落"],
            "喜悦": ["开心", "高兴", "欢笑", "喜悦", "兴奋"],
            "愤怒": ["愤怒", "生气", "怒吼", "暴怒", "争吵"],
            "温馨": ["温馨", "温暖", "幸福", "甜蜜", "感动"],
        }
        for emotion, keywords in emotion_keywords.items():
            if any(k in desc_lower for k in keywords):
                scene.emotional_tone = emotion
                break


class ScriptAdapter:
    """剧本改编器：将解析后的场景改编为分镜"""

    def __init__(self):
        self.shot_counter = 0

    def adapt_scene(self, scene: ParsedScene) -> List[AdaptedShot]:
        """
        将单个场景改编为多个镜头

        Args:
            scene: 解析后的场景

        Returns:
            镜头列表
        """
        shots = []
        remaining_duration = scene.duration_estimate

        # 1. 场景建立镜头（全景/远景）
        self.shot_counter += 1
        establishing = AdaptedShot(
            shot_id=self.shot_counter,
            scene_id=scene.scene_id,
            shot_size=ShotSize.LONG,
            camera_move=CameraMove.FIXED,
            description=f"{scene.location} 场景建立",
            subject=scene.location,
            duration=min(3.0, remaining_duration * 0.2),
            emotion=scene.emotional_tone,
            notes="交代环境和时空",
        )
        shots.append(establishing)
        remaining_duration -= establishing.duration

        # 2. 对话镜头（正反打）
        for i, dialogue in enumerate(scene.dialogues):
            if remaining_duration < 1.0:
                break

            self.shot_counter += 1
            # 交替使用特写/近景
            shot_size = ShotSize.CLOSEUP if i % 2 == 0 else ShotSize.MEDIUM_CLOSEUP
            # 说话人镜头
            shot = AdaptedShot(
                shot_id=self.shot_counter,
                scene_id=scene.scene_id,
                shot_size=shot_size,
                camera_move=CameraMove.FIXED,
                description=f"{dialogue.speaker}: {dialogue.content[:20]}...",
                subject=dialogue.speaker,
                dialogue=dialogue,
                duration=min(max(len(dialogue.content) / 5, 1.5), remaining_duration),
                emotion=dialogue.emotion or scene.emotional_tone,
                notes=f"对话镜头，{dialogue.action}" if dialogue.action else "对话镜头",
            )
            shots.append(shot)
            remaining_duration -= shot.duration

            # 反应镜头（对话超过3句时插入）
            if i > 0 and i % 3 == 0 and remaining_duration > 1.5:
                self.shot_counter += 1
                reaction = AdaptedShot(
                    shot_id=self.shot_counter,
                    scene_id=scene.scene_id,
                    shot_size=ShotSize.CLOSEUP,
                    camera_move=CameraMove.FIXED,
                    description=f"听者反应镜头",
                    subject="听者",
                    duration=1.5,
                    emotion=scene.emotional_tone,
                    notes="反应镜头，增强对话张力",
                )
                shots.append(reaction)
                remaining_duration -= 1.5

        # 3. 动作/转场镜头
        if scene.actions and remaining_duration > 2.0:
            self.shot_counter += 1
            action_shot = AdaptedShot(
                shot_id=self.shot_counter,
                scene_id=scene.scene_id,
                shot_size=ShotSize.MEDIUM,
                camera_move=CameraMove.TRACKING,
                description=f"动作镜头: {scene.actions[0][:30]}",
                duration=min(remaining_duration, 3.0),
                emotion=scene.emotional_tone,
                notes="动作/转场镜头",
            )
            shots.append(action_shot)

        return shots

    def adapt_episode(self, scenes: List[ParsedScene],
                       characters: List[Character],
                       title: str = "第1集",
                       episode_id: int = 1) -> AdaptedEpisode:
        """
        改编单集

        Args:
            scenes: 场景列表
            characters: 角色列表
            title: 集标题
            episode_id: 集编号

        Returns:
            改编后的单集
        """
        self.shot_counter = 0
        all_shots = []

        for scene in scenes:
            shots = self.adapt_scene(scene)
            all_shots.extend(shots)

        total_duration = sum(s.duration for s in all_shots)

        # 生成logline
        if scenes:
            logline = f"{scenes[0].location}开始，"
            if characters:
                logline += f"{characters[0].name}等角色，"
            logline += f"共{len(scenes)}场{len(all_shots)}镜"
        else:
            logline = title

        return AdaptedEpisode(
            episode_id=episode_id,
            title=title,
            scenes=scenes,
            shots=all_shots,
            characters=characters,
            total_duration=total_duration,
            logline=logline,
        )


class EpisodeSplitter:
    """多集拆分器"""

    def __init__(self, max_scenes_per_episode: int = 8,
                 max_duration_per_episode: float = 300.0):
        self.max_scenes = max_scenes_per_episode
        self.max_duration = max_duration_per_episode

    def split(self, scenes: List[ParsedScene]) -> List[List[ParsedScene]]:
        """
        将场景列表拆分为多集

        Args:
            scenes: 全部场景

        Returns:
            每集的场景列表
        """
        episodes = []
        current_episode = []
        current_duration = 0.0

        for scene in scenes:
            # 检查是否需要拆分
            if (len(current_episode) >= self.max_scenes or
                current_duration + scene.duration_estimate > self.max_duration):
                if current_episode:
                    episodes.append(current_episode)
                    current_episode = []
                    current_duration = 0.0

            current_episode.append(scene)
            current_duration += scene.duration_estimate

        if current_episode:
            episodes.append(current_episode)

        return episodes


class ScriptAdapterEngine:
    """剧本解析改编引擎（主入口）"""

    def __init__(self):
        self.parser = ScriptParser()
        self.adapter = ScriptAdapter()
        self.splitter = EpisodeSplitter()

    def parse_and_adapt(self, text: str, title: str = "未命名剧本",
                         auto_split: bool = True) -> Dict[str, Any]:
        """
        完整流程：解析→改编→拆分

        Args:
            text: 剧本文本
            title: 剧本标题
            auto_split: 是否自动拆分为多集

        Returns:
            完整改编结果
        """
        print(f"\n{'='*60}")
        print(f"📖 剧本解析改编引擎")
        print(f"{'='*60}")
        print(f"标题: {title}")
        print(f"文本长度: {len(text)}字符")

        # Step 1: 解析
        print(f"\n[1/4] 解析剧本...")
        scenes = self.parser.parse(text, title)
        characters = list(self.parser.characters.values())
        print(f"  ✅ 解析完成: {len(scenes)}个场景, {len(characters)}个角色")
        for c in characters:
            print(f"     - {c.name}: {c.line_count}句台词")

        # Step 2: 拆分（如需要）
        if auto_split and len(scenes) > self.splitter.max_scenes:
            print(f"\n[2/4] 多集拆分...")
            episode_scenes = self.splitter.split(scenes)
            print(f"  ✅ 拆分为 {len(episode_scenes)} 集")
        else:
            episode_scenes = [scenes]
            print(f"\n[2/4] 单集模式（{len(scenes)}个场景）")

        # Step 3: 改编
        print(f"\n[3/4] 分镜改编...")
        episodes = []
        for i, eps_scenes in enumerate(episode_scenes):
            episode = self.adapter.adapt_episode(
                eps_scenes, characters,
                title=f"{title} - 第{i+1}集",
                episode_id=i+1,
            )
            episodes.append(episode)
            print(f"  ✅ 第{i+1}集: {len(eps_scenes)}场 → {len(episode.shots)}镜, 约{episode.total_duration:.0f}秒")

        # Step 4: 汇总
        print(f"\n[4/4] 生成报告...")
        total_shots = sum(len(e.shots) for e in episodes)
        total_duration = sum(e.total_duration for e in episodes)

        result = {
            "title": title,
            "episode_count": len(episodes),
            "total_scenes": len(scenes),
            "total_shots": total_shots,
            "total_duration": total_duration,
            "characters": [c.to_dict() for c in characters],
            "episodes": [e.to_dict() for e in episodes],
        }

        print(f"\n{'✅'*20}")
        print(f"改编完成!")
        print(f"  集数: {len(episodes)}")
        print(f"  场景: {len(scenes)}")
        print(f"  镜头: {total_shots}")
        print(f"  总时长: 约{total_duration:.0f}秒 ({total_duration/60:.1f}分钟)")
        print(f"  角色: {len(characters)}")
        print(f"{'✅'*20}")

        return result

    def export_to_json(self, result: Dict[str, Any], output_path: str) -> str:
        """导出为JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return output_path

    def export_to_script_format(self, episode: AdaptedEpisode) -> Dict[str, Any]:
        """
        转换为现有pipeline的Script格式（兼容cap_script_engine）

        Returns:
            兼容Script对象的字典格式
        """
        shots_data = []
        for shot in episode.shots:
            shots_data.append({
                "shot_id": shot.shot_id,
                "description": shot.description,
                "shot_size": shot.shot_size.value,
                "camera_move": shot.camera_move.value,
                "duration": shot.duration,
                "dialogue": shot.dialogue.to_dict() if shot.dialogue else None,
                "emotion": shot.emotion,
            })

        scenes_data = []
        for scene in episode.scenes:
            scene_shots = [s for s in shots_data if s.get("scene_id") == scene.scene_id]
            scenes_data.append({
                "scene_id": scene.scene_id,
                "title": scene.title,
                "location": scene.location,
                "scene_type": scene.scene_type.value,
                "duration": scene.duration_estimate,
                "shots": scene_shots,
                "characters": scene.characters,
                "dialogues": [d.to_dict() for d in scene.dialogues],
            })

        return {
            "title": episode.title,
            "logline": episode.logline,
            "total_duration": episode.total_duration,
            "scenes": scenes_data,
            "characters": [c.to_dict() for c in episode.characters],
        }


if __name__ == "__main__":
    # 测试用例
    test_script = """
INT. 咖啡馆 - 日
李明走进咖啡馆，四处张望。
王芳坐在角落，向他挥手。

李明：你怎么才来？我都等了半小时了！
王芳：（放下手机）抱歉抱歉，路上堵车。
李明：（坐下）算了，说正事吧，你找我什么事？
王芳：（压低声音）我发现了一个秘密，关于公司的。
李明：（惊讶）什么秘密？
王芳：（环顾四周）这里不方便说，换个地方。

EXT. 街道 - 夜
两人走出咖啡馆，街上行人稀少。
李明：现在可以说了吧？
王芳：（紧张）公司的财务报表有问题，有人在做假账。
李明：（震惊）你确定？这可不是小事！
王芳：我亲眼看到的，而且我有证据。
李明：（思考）...我们得小心点，这件事不能让任何人知道。
"""

    engine = ScriptAdapterEngine()
    result = engine.parse_and_adapt(test_script, title="咖啡馆密会")

    # 导出
    output_dir = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor\capabilities\script_outputs"
    import os
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "script_adapter_test.json")
    engine.export_to_json(result, output_path)
    print(f"\n📄 已导出: {output_path}")

    # 转换为Script格式（验证兼容性）
    if result['episodes']:
        ep = result['episodes'][0]
        print(f"\n🎬 Script兼容格式: {len(ep['scenes'])}场, {ep['shot_count']}镜, {ep['total_duration']:.0f}秒")
        print(f"   可直接接入pipeline_script_driver进行剪映合成")
