"""
P23: 剧本结构化解析器（Script Parser）
导演引擎的第一模块：把人类自然语言剧本翻译成标准分镜JSON

核心能力：
1. 角色识别（名称、形象、情绪、关系）
2. 动作解析（谁在什么时间做什么）
3. 情绪标注（每个角色每个时刻的情绪状态）
4. 音效点识别（动作音效、环境音、转场音效）
5. 节奏分析（每个镜头时长、转场类型）
6. 场景识别（地点、时间、氛围）

输出标准：scene_schema.json（见director_engine_architecture.md）
"""

import json
import re
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict


# ============ 情绪词典 ============
EMOTION_KEYWORDS = {
    "开心": ["开心", "高兴", "快乐", "兴奋", "比耶", "笑", "得意", "蹦跶"],
    "委屈": ["委屈", "难过", "伤心", "哭", "摸头", "低头", "失落", "沮丧"],
    "愤怒": ["愤怒", "生气", "怒吼", "拍桌", "瞪眼", "火大", "暴怒"],
    "惊恐": ["惊恐", "害怕", "尖叫", "躲闪", "颤抖", "惊慌", "吓"],
    "得意": ["得意", "炫耀", "傲娇", "挑眉", "嘚瑟", "嚣张"],
    "平静": ["平静", "淡定", "冷静", "面无表情", "冷漠"],
    "惊讶": ["惊讶", "吃惊", "瞪眼", "张嘴", "意外", "震惊"],
    "害羞": ["害羞", "脸红", "扭捏", "不好意思"],
}

# ============ 动作词典 ============
ACTION_KEYWORDS = {
    "比耶": ["比耶", "剪刀手", "耶", "v字手"],
    "被打": ["被打", "挨打", "揍", "一拳", "一巴掌", "踢", "击中", "打飞"],
    "摸头": ["摸头", "捂头", "抱头", "头好痛"],
    "掉下": ["掉下", "掉出", "摔下", "跌出", "滚出"],
    "爬上": ["爬上", "爬回", "钻回", "探出头"],
    "说话": ["说", "道", "喊", "叫", "问", "答", "念"],
    "转身": ["转身", "回头", "扭过头"],
    "挥手": ["挥手", "招手", "摆手", "打招呼"],
    "弹弓": ["弹弓", "打弹弓", "射"],
}

# ============ 音效词典 ============
SFX_KEYWORDS = {
    "击打声": ["被打", "一拳", "一巴掌", "踢", "击中", "揍", "啪"],
    "闪白": ["被打", "击中", "一拳", "一巴掌"],
    "脚步声": ["走", "跑", "脚步", "踏"],
    "风声": ["风", "吹", "飘"],
    "笑声": ["笑", "哈哈", "嘿嘿"],
    "哭声": ["哭", "呜呜", "委屈"],
    "弹弓声": ["弹弓", "射", "嗖"],
    "玻璃碎": ["碎", "哗啦", "砰"],
}

# ============ 场景词典 ============
SCENE_KEYWORDS = {
    "头像框内": ["头像框", "头像", "框里", "框内", "圆形"],
    "抖音主页": ["抖音", "主页", "个人主页", "作品列表"],
    "商品橱窗": ["橱窗", "商品", "购物"],
    "室外": ["室外", "户外", "外面", "街", "路"],
    "室内": ["室内", "屋里", "房间", "办公室"],
}

# ============ 转场词典 ============
TRANSITION_KEYWORDS = {
    "硬切": ["切", "切换", "转到", "画面一转"],
    "叠化": ["叠化", "淡入淡出", "渐渐", "慢慢"],
    "闪白": ["闪", "白屏", "刺眼"],
    "缩放": ["放大", "缩小", "推近", "拉远"],
}


@dataclass
class Character:
    id: str
    name: str
    description: str = ""
    voice: str = ""
    emotion_default: str = "平静"


@dataclass
class CharacterAction:
    character_id: str
    action: str
    emotion: str = "平静"
    position: str = ""
    dialogue: str = ""


@dataclass
class Shot:
    id: str
    start: float
    duration: float
    camera: str = "固定"
    characters: List[CharacterAction] = field(default_factory=list)
    sfx: List[str] = field(default_factory=list)
    environment: str = ""


@dataclass
class Scene:
    id: str
    start: float
    duration: float
    location: str = ""
    atmosphere: str = ""
    shots: List[Shot] = field(default_factory=list)
    transition: str = "硬切"


@dataclass
class AudioMix:
    bgm: str = ""
    ambient: List[str] = field(default_factory=list)
    sfx_timeline: List[Dict] = field(default_factory=list)


@dataclass
class TextLayout:
    logo: Dict = field(default_factory=dict)
    subtitles: List[Dict] = field(default_factory=list)


@dataclass
class ScriptProject:
    title: str
    duration: float = 20.0
    fps: int = 30
    resolution: List[int] = field(default_factory=lambda: [1080, 1920])
    style: str = ""
    characters: List[Character] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    audio_mix: AudioMix = field(default_factory=AudioMix)
    text_layout: TextLayout = field(default_factory=TextLayout)


class ScriptParser:
    """剧本结构化解析器"""

    def __init__(self):
        self.characters = {}
        self.scenes = []
        self.project = None

    def parse(self, script_text: str, title: str = "未命名项目",
              duration: float = 20.0, style: str = "") -> Dict[str, Any]:
        """
        解析自然语言剧本，输出标准分镜JSON

        Args:
            script_text: 自然语言剧本
            title: 项目标题
            duration: 总时长（秒）
            style: 视频风格

        Returns:
            标准分镜JSON字典
        """
        self.project = ScriptProject(
            title=title,
            duration=duration,
            style=style,
        )

        # 1. 识别角色
        self._extract_characters(script_text)

        # 2. 分句/分段
        sentences = self._split_sentences(script_text)

        # 3. 逐句解析动作、情绪、音效
        parsed_shots = []
        current_time = 0.0
        for i, sent in enumerate(sentences):
            shot = self._parse_sentence(sent, i, current_time)
            if shot:
                parsed_shots.append(shot)
                current_time += shot.duration

        # 4. 聚合为场景
        self._group_into_scenes(parsed_shots)

        # 5. 生成音轨混合
        self._generate_audio_mix(parsed_shots)

        # 6. 生成文字排版
        self._generate_text_layout(script_text)

        # 7. 输出JSON
        return self._to_json()

    def _extract_characters(self, text: str):
        """从文本中识别角色"""
        # 已知角色映射（优先匹配）
        known_chars = {
            "豆包": {"name": "豆包", "description": "短发红围巾黑西装女性", "voice": "年轻女性/活泼"},
            "机器人": {"name": "机器人", "description": "银灰钢铁侠风格机器人", "voice": "机械音/低沉"},
            "女杀手": {"name": "女杀手", "description": "全身黑西装高跟鞋女性", "voice": "冷艳女性"},
        }

        # 非角色名黑名单（常见的动词/副词/量词/连接词/短语）
        blacklist = {
            "一脚", "一拳", "一巴掌", "一下", "一次", "结果", "然后", "突然",
            "这时", "接着", "最后", "终于", "于是", "所以", "因为",
            "如果", "虽然", "但是", "而且", "并且", "或者", "还是", "不是",
            "结果又", "然后又", "突然又", "这时又", "接着又",
            "委屈地", "开心地", "愤怒地", "惊恐地", "得意地", "平静地",
            "惊讶地", "害羞地", "难过地", "高兴地", "兴奋地", "激动地",
            "家打招呼", "打招呼", "大家好", "你们好", "大家", "你们",
            "我们", "他们", "她们", "它们", "这个", "那个", "这些", "那些",
            "什么", "怎么", "为什么", "哪里", "哪个", "谁", "怎么回事",
            "向大家", "对大家", "跟大家", "和大家", "给大家",
            "手一脚", "手一拳", "手一巴掌", "头一撞", "脚一踢",
        }

        found_names = set()
        # 先匹配已知角色
        for name in known_chars:
            if name in text:
                found_names.add(name)

        # 再尝试识别其他角色名（2-3个中文字，后面跟着说/道/被/把等，且不在黑名单）
        other_matches = re.findall(r'([\u4e00-\u9fa5]{2,3})(?=说|道|喊|问|答|笑|哭|被|把|将)', text)
        for m in other_matches:
            if m not in blacklist and m not in known_chars and len(m) >= 2:
                # 额外过滤：不以"地/的/了/着/过"结尾
                if m[-1] not in "地的了着过":
                    found_names.add(m)

        char_id = 0
        for name in found_names:
            if name in known_chars:
                info = known_chars[name]
                char = Character(
                    id=f"char_{char_id}",
                    name=info["name"],
                    description=info["description"],
                    voice=info["voice"],
                )
            else:
                char = Character(
                    id=f"char_{char_id}",
                    name=name,
                    description="",
                    voice="",
                )
            self.characters[name] = char
            self.project.characters.append(char)
            char_id += 1

    def _split_sentences(self, text: str) -> List[str]:
        """按标点分句"""
        # 按句号、问号、感叹号、分号分句
        sentences = re.split(r'[。！？；\n]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _parse_sentence(self, sentence: str, index: int, start_time: float) -> Optional[Shot]:
        """解析单句，识别角色、动作、情绪、音效"""
        if not sentence:
            return None

        # 识别角色
        chars_in_sentence = []
        for name, char in self.characters.items():
            if name in sentence:
                chars_in_sentence.append(char)

        # 识别动作
        actions = []
        for action, keywords in ACTION_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence:
                    actions.append(action)
                    break

        # 识别情绪
        emotions = []
        for emotion, keywords in EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence:
                    emotions.append(emotion)
                    break

        # 识别音效
        sfx = []
        for sfx_type, keywords in SFX_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence:
                    sfx.append(sfx_type)
                    break

        # 识别场景
        location = ""
        for scene, keywords in SCENE_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence:
                    location = scene
                    break
            if location:
                break

        # 识别转场
        transition = "硬切"
        for trans, keywords in TRANSITION_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence:
                    transition = trans
                    break
            if transition != "硬切":
                break

        # 识别台词（引号内的内容）
        dialogue = ""
        dialogue_match = re.search(r'[「『"](.+?)[」』"]', sentence)
        if dialogue_match:
            dialogue = dialogue_match.group(1)

        # 构建角色动作（施动者/受动者区分）
        char_actions = []

        # 判断是否有被动/主动结构
        has_passive = "被" in sentence
        has_active = "把" in sentence or "将" in sentence

        # 攻击类动作关键词
        attack_keywords = ["打", "踢", "揍", "扇", "捶", "砸", "撞", "推"]
        is_attack_scene = any(kw in sentence for kw in attack_keywords)

        # 预计算所有角色位置（按位置排序）
        char_positions = [(c.name, sentence.find(c.name)) for c in chars_in_sentence]
        char_positions.sort(key=lambda x: x[1])

        # 确定受动者和施动者
        patient_name = None  # 受动者（被打）
        agent_name = None    # 施动者（攻击）

        if is_attack_scene and len(chars_in_sentence) >= 2:
            if has_passive:
                # "A被B打" 或 "..., A被打得..." → A是受动者
                bei_pos = sentence.find("被")
                # 找"被"字前面最近的角色
                for name, pos in reversed(char_positions):
                    if pos < bei_pos:
                        patient_name = name
                        break
                # 找"被"字后面的角色（如果有）作为施动者
                for name, pos in char_positions:
                    if pos > bei_pos:
                        agent_name = name
                        break
                # 如果"被"字后面没有角色，第一个出现的角色（非受动者）是施动者
                if not agent_name:
                    for name, _ in char_positions:
                        if name != patient_name:
                            agent_name = name
                            break
            elif has_active:
                # "A把B打" → A是施动者，B是受动者
                ba_pos = sentence.find("把")
                if ba_pos == -1:
                    ba_pos = sentence.find("将")
                for name, pos in char_positions:
                    if pos < ba_pos:
                        agent_name = name
                    elif pos > ba_pos and not patient_name:
                        patient_name = name
            else:
                # "A打B" → 第一个是施动者，后面的是受动者
                agent_name = char_positions[0][0]
                if len(char_positions) > 1:
                    patient_name = char_positions[1][0]

        for char in chars_in_sentence:
            action = actions[0] if actions else "站立"
            emotion = emotions[0] if emotions else char.emotion_default

            # 应用动作归属
            if is_attack_scene and len(chars_in_sentence) >= 2:
                if char.name == patient_name:
                    action = "被打"
                elif char.name == agent_name:
                    action = "攻击"

            char_actions.append(CharacterAction(
                character_id=char.id,
                action=action,
                emotion=emotion,
                dialogue=dialogue if dialogue else "",
            ))

        # 估算时长（基于动作数量和台词长度）
        base_duration = 2.0
        if dialogue:
            base_duration += len(dialogue) * 0.15
        if "被打" in actions:
            base_duration = 1.0
        if "比耶" in actions:
            base_duration = 3.0

        shot = Shot(
            id=f"shot_{index:03d}",
            start=start_time,
            duration=round(base_duration, 1),
            camera="固定",
            characters=char_actions,
            sfx=sfx,
            environment=location,
        )
        return shot

    def _group_into_scenes(self, shots: List[Shot]):
        """把镜头聚合为场景（按位置/环境分组）"""
        if not shots:
            return

        current_scene = None
        scene_id = 0

        for shot in shots:
            location = shot.environment or "未指定"

            if current_scene is None or current_scene.location != location:
                # 新场景
                if current_scene:
                    current_scene.duration = round(
                        shot.start - current_scene.start, 1
                    )
                    self.project.scenes.append(current_scene)

                current_scene = Scene(
                    id=f"scene_{scene_id:02d}",
                    start=shot.start,
                    duration=0,
                    location=location,
                    atmosphere=self._infer_atmosphere(location),
                    transition="硬切",
                )
                scene_id += 1

            current_scene.shots.append(shot)

        if current_scene:
            last_shot = shots[-1]
            current_scene.duration = round(
                last_shot.start + last_shot.duration - current_scene.start, 1
            )
            self.project.scenes.append(current_scene)

    def _infer_atmosphere(self, location: str) -> str:
        """根据场景推断氛围"""
        atmosphere_map = {
            "头像框内": "轻松/搞笑",
            "抖音主页": "日常",
            "商品橱窗": "商业",
            "室外": "开阔",
            "室内": "温馨",
        }
        return atmosphere_map.get(location, "中性")

    def _generate_audio_mix(self, shots: List[Shot]):
        """生成音轨混合方案"""
        # 收集所有音效点
        sfx_timeline = []
        for shot in shots:
            for sfx in shot.sfx:
                sfx_timeline.append({
                    "time": shot.start,
                    "type": sfx,
                    "intensity": 0.7,
                })

        # 根据风格推断BGM
        bgm_map = {
            "旅拍": "轻松旅拍BGM",
            "短剧": "剧情向BGM",
            "搞笑": "欢快搞笑BGM",
            "广告": "商业宣传BGM",
        }
        bgm = bgm_map.get(self.project.style, "通用BGM")

        # 根据场景推断环境音
        ambient = []
        for scene in self.project.scenes:
            if scene.location == "室外":
                ambient.append("户外环境音")
            elif scene.location == "室内":
                ambient.append("室内环境音")
            elif "头像框" in scene.location:
                ambient.append("轻微室内音")

        self.project.audio_mix = AudioMix(
            bgm=bgm,
            ambient=list(set(ambient)),
            sfx_timeline=sfx_timeline,
        )

    def _generate_text_layout(self, script_text: str):
        """生成文字排版方案"""
        # 根据风格推断排版
        if self.project.style == "旅拍":
            self.project.text_layout = TextLayout(
                logo={"text": self.project.title, "position": "左上", "style": "手写体"},
                subtitles=[],
            )
        elif self.project.style == "短剧":
            self.project.text_layout = TextLayout(
                logo={},
                subtitles=[],
            )
        else:
            self.project.text_layout = TextLayout(
                logo={},
                subtitles=[],
            )

    def _to_json(self) -> Dict[str, Any]:
        """转换为标准JSON"""
        return {
            "project": {
                "title": self.project.title,
                "duration": self.project.duration,
                "fps": self.project.fps,
                "resolution": self.project.resolution,
                "style": self.project.style,
            },
            "characters": [asdict(c) for c in self.project.characters],
            "scenes": [
                {
                    "id": s.id,
                    "start": s.start,
                    "duration": s.duration,
                    "location": s.location,
                    "atmosphere": s.atmosphere,
                    "shots": [
                        {
                            "id": sh.id,
                            "start": sh.start,
                            "duration": sh.duration,
                            "camera": sh.camera,
                            "characters": [asdict(ca) for ca in sh.characters],
                            "sfx": sh.sfx,
                            "environment": sh.environment,
                        }
                        for sh in s.shots
                    ],
                    "transition": s.transition,
                }
                for s in self.project.scenes
            ],
            "audio_mix": asdict(self.project.audio_mix),
            "text_layout": asdict(self.project.text_layout),
        }

    def save_json(self, output_path: str):
        """保存解析结果到JSON文件"""
        result = self._to_json()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 分镜JSON已保存: {output_path}")
        return output_path

    def print_summary(self):
        """打印解析摘要"""
        result = self._to_json()
        print(f"\n{'='*60}")
        print(f"剧本解析摘要")
        print(f"{'='*60}")
        print(f"项目: {result['project']['title']}")
        print(f"时长: {result['project']['duration']}秒")
        print(f"风格: {result['project']['style']}")
        print(f"\n角色 ({len(result['characters'])}):")
        for c in result['characters']:
            print(f"  - {c['name']}: {c['description']}")
        print(f"\n场景 ({len(result['scenes'])}):")
        for s in result['scenes']:
            print(f"  {s['id']}: {s['location']} ({s['start']}s-{s['start']+s['duration']}s) "
                  f"[{s['atmosphere']}] {len(s['shots'])}镜头")
            for sh in s['shots']:
                chars = ", ".join([f"{ca['character_id']}:{ca['action']}({ca['emotion']})"
                                   for ca in sh['characters']])
                print(f"    {sh['id']}: {sh['duration']}s | {chars} | SFX:{sh['sfx']}")
        print(f"\n音效点: {len(result['audio_mix']['sfx_timeline'])}个")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # 测试：豆包被打案例
    test_script = """
    豆包在抖音主页的头像框里开心地比耶，向大家打招呼。
    突然机器人一拳打在豆包脸上，豆包被打得飞出去，委屈地摸头。
    豆包从头像框里掉出来，摔在作品列表上。
    女杀手出现，一脚把豆包踢回头像框里。
    豆包爬回头像框，得意地比耶，结果又被机器人打了一拳。
    """

    parser = ScriptParser()
    result = parser.parse(
        script_text=test_script,
        title="豆包被打",
        duration=20.0,
        style="搞笑短剧",
    )
    parser.print_summary()

    # 保存
    out = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\director_engine_test\parsed_script.json"
    parser.save_json(out)
