"""
剧本引擎核心
输入一句话需求 → 输出有故事线的完整剧本(Script对象)

设计原则：
1. 三幕结构：钩子(开场) → 内容(发展) → 号召(结尾)
2. 情绪节奏：钩子→紧张→舒缓→高潮→收尾
3. 智能分镜：根据场景内容自动分配景别/机位/时长
4. 特效建议：每个镜头标注effect_hint供智能调度器使用
"""
import os
import sys
import json
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

from .models import Script, Scene, Shot, VideoGenre, Emotion, ShotSize

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


class ScriptEngine:
    """剧本生成引擎"""

    # 类型→默认参数映射
    GENRE_PRESETS = {
        VideoGenre.EXPLORATION: {
            "style": "快节奏+沉浸式",
            "bgm_mood": "轻快电子/城市流行",
            "hook_templates": [
                "这家店藏得太深了！",
                "99%的人不知道的宝藏店铺",
                "花XX元吃到撑是什么体验？",
            ],
            "cta_templates": [
                "地址放评论区了，快去打卡！",
                "关注我，带你吃遍全城！",
                "你还知道哪些宝藏店？评论区告诉我！",
            ],
        },
        VideoGenre.TALKING: {
            "style": "沉稳+信息密集",
            "bgm_mood": "轻柔钢琴/lo-fi",
            "hook_templates": [
                "90%的人都搞错了这件事",
                "一个被忽略的真相",
                "今天说点别人不敢说的",
            ],
            "cta_templates": [
                "点赞收藏，下次不迷路",
                "关注我，每天涨知识",
                "有问题评论区问我",
            ],
        },
        VideoGenre.ECOMMERCE: {
            "style": "快节奏+卖点突出",
            "bgm_mood": "动感电子/带货BGM",
            "hook_templates": [
                "这个价格真的离谱",
                "用了一周，真香",
                "别再买贵了！",
            ],
            "cta_templates": [
                "小黄车直接拍，手慢无",
                "点击下方链接，限时优惠",
                "库存不多了，赶紧冲",
            ],
        },
        VideoGenre.VLOG: {
            "style": "自然+生活感",
            "bgm_mood": "清新民谣/轻音乐",
            "hook_templates": [
                "普通的一天，不普通的记录",
                "跟我过一天",
                "今天发生了一件事",
            ],
            "cta_templates": [
                "下期想看什么？告诉我",
                "记录生活，感谢观看",
                "点赞是最大的支持",
            ],
        },
        VideoGenre.PROMO: {
            "style": "电影感+高燃",
            "bgm_mood": "史诗管弦/电子燃曲",
            "hook_templates": [
                "重新定义XX",
                "这一次，不一样",
                "你准备好了吗？",
            ],
            "cta_templates": [
                "立即体验，改变从现在开始",
                "免费试用，点击了解",
                "加入我们，一起创造",
            ],
        },
    }

    def __init__(self, templates_dir: str = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self._load_templates()

    def _load_templates(self):
        """加载场景模板"""
        self.templates = {}
        if os.path.exists(self.templates_dir):
            for f in os.listdir(self.templates_dir):
                if f.endswith(".json"):
                    name = f.replace(".json", "")
                    with open(os.path.join(self.templates_dir, f), "r", encoding="utf-8") as fp:
                        self.templates[name] = json.load(fp)

    def generate(
        self,
        idea: str,
        genre: VideoGenre = VideoGenre.CUSTOM,
        duration: float = 60.0,
        aspect_ratio: str = "9:16",
        title: str = None,
        target_audience: str = "",
        keywords: List[str] = None,
    ) -> Script:
        """
        从一句话需求生成完整剧本

        Args:
            idea: 用户的一句话需求，如"做一条探店视频，介绍一家火锅店"
            genre: 视频类型
            duration: 目标时长(秒)
            aspect_ratio: 画幅
            title: 标题(不填则自动生成)
            target_audience: 目标受众
            keywords: 关键词

        Returns:
            Script对象，包含完整的场景/分镜/字幕/特效建议
        """
        preset = self.GENRE_PRESETS.get(genre, self.GENRE_PRESETS[VideoGenre.TALKING])
        title = title or self._generate_title(idea, genre)
        hook = self._pick(preset["hook_templates"])
        cta = self._pick(preset["cta_templates"])

        script = Script(
            title=title,
            genre=genre,
            target_audience=target_audience or "短视频平台用户",
            total_duration=duration,
            aspect_ratio=aspect_ratio,
            style=preset["style"],
            hook=hook,
            cta=cta,
            keywords=keywords or self._extract_keywords(idea, genre),
            bgm_mood=preset["bgm_mood"],
            notes=f"基于需求生成: {idea}",
        )

        # 三幕结构分配时长
        scenes = self._build_three_act_structure(script, idea, preset)
        script.scenes = scenes

        return script

    def _generate_title(self, idea: str, genre: VideoGenre) -> str:
        """从需求生成标题"""
        # 简单策略：取idea前20字+类型标签
        clean = idea.strip().replace("\n", " ")
        if len(clean) > 20:
            clean = clean[:20] + "..."
        return f"{clean} | {genre.value}视频"

    def _extract_keywords(self, idea: str, genre: VideoGenre) -> List[str]:
        """从需求提取关键词"""
        kws = [genre.value]
        # 简单分词：按空格/标点分割，取长度>1的词
        import re
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', idea)
        kws.extend(words[:5])
        return list(dict.fromkeys(kws))  # 去重保序

    def _pick(self, options: List[str]) -> str:
        """从列表中选一个(简单取第一个，后续可加随机性)"""
        return options[0] if options else ""

    def _build_three_act_structure(self, script: Script, idea: str, preset: Dict) -> List[Scene]:
        """
        构建三幕结构：
        Act1 钩子(15%): 抓人注意力
        Act2 内容(70%): 主体内容，分3-4个场景
        Act3 号召(15%): 总结+行动号召
        """
        total = script.total_duration
        act1_dur = round(total * 0.15, 2)
        act3_dur = round(total * 0.15, 2)
        act2_dur = round(total - act1_dur - act3_dur, 2)

        scenes = []
        t = 0.0

        # === Act 1: 钩子 ===
        act1 = Scene(
            scene_id="act1_hook",
            title="第一幕·钩子",
            start_time=t,
            duration=act1_dur,
            emotion=Emotion.HOOK,
            description=f"用反常识/痛点/悬念抓住观众，前3秒必须留人。核心文案: {script.hook}",
            transition_in="硬切",
            transition_out="快切",
        )
        act1.shots = self._build_hook_shots(act1, script)
        scenes.append(act1)
        t += act1_dur

        # === Act 2: 内容主体(分3-4个场景) ===
        num_content_scenes = 3 if act2_dur < 45 else 4
        content_dur = round(act2_dur / num_content_scenes, 2)
        content_emotions = [Emotion.TENSION, Emotion.RELIEF, Emotion.CLIMAX, Emotion.RELIEF]

        for i in range(num_content_scenes):
            scene = Scene(
                scene_id=f"act2_scene{i+1}",
                title=f"第二幕·内容{i+1}",
                start_time=t,
                duration=content_dur,
                emotion=content_emotions[i % len(content_emotions)],
                description=self._generate_content_description(idea, i, num_content_scenes),
                transition_in="快切" if i > 0 else "快切",
                transition_out="快切" if i < num_content_scenes - 1 else "淡入淡出",
            )
            scene.shots = self._build_content_shots(scene, script, idea, i)
            scenes.append(scene)
            t += content_dur

        # === Act 3: 号召 ===
        act3 = Scene(
            scene_id="act3_cta",
            title="第三幕·号召",
            start_time=t,
            duration=act3_dur,
            emotion=Emotion.RESOLUTION,
            description=f"总结核心价值，引导行动。核心文案: {script.cta}",
            transition_in="淡入淡出",
            transition_out="淡出",
        )
        act3.shots = self._build_cta_shots(act3, script)
        scenes.append(act3)

        return scenes

    def _build_hook_shots(self, scene: Scene, script: Script) -> List[Shot]:
        """构建钩子镜头"""
        shots = []
        # 镜头1: 强视觉冲击(0-1.5s)
        shots.append(Shot(
            shot_id=f"{scene.scene_id}_s1",
            start_time=scene.start_time,
            duration=min(1.5, scene.duration * 0.4),
            shot_size=ShotSize.CLOSEUP,
            camera_move="快速推进",
            description="核心视觉元素大特写，配合快闪特效",
            subtitle=script.hook,
            effect_hint="蒙版快闪+发光轮廓",
            emotion=Emotion.HOOK,
            visual_ref="高对比度特写画面，冲击力强",
        ))
        # 镜头2: 问题抛出(1.5s-结束)
        shots.append(Shot(
            shot_id=f"{scene.scene_id}_s2",
            start_time=scene.start_time + shots[0].duration,
            duration=scene.duration - shots[0].duration,
            shot_size=ShotSize.MEDIUM,
            camera_move="固定",
            description="抛出问题/痛点，引发好奇",
            subtitle="你是不是也这样？",
            effect_hint="字幕条动画",
            emotion=Emotion.TENSION,
        ))
        return shots

    def _generate_content_description(self, idea: str, index: int, total: int) -> str:
        """生成内容场景描述"""
        templates = [
            f"引入主题，建立背景。围绕「{idea}」展开第一个核心点，用具体细节代替空泛描述。",
            f"深入展开，展示过程/对比/证据。用数据或真实体验增加可信度。",
            f"高潮部分，展示最精彩/最意外/最有价值的内容。情绪拉满。",
            f"补充细节，过渡到总结。回应开头抛出的问题。",
        ]
        return templates[index % len(templates)]

    def _build_content_shots(self, scene: Scene, script: Script, idea: str, index: int) -> List[Shot]:
        """构建内容场景镜头"""
        shots = []
        num_shots = 3 if scene.duration > 10 else 2
        shot_dur = round(scene.duration / num_shots, 2)
        shot_sizes = [ShotSize.WIDE, ShotSize.MEDIUM, ShotSize.CLOSEUP]
        camera_moves = ["缓慢推进", "固定", "环绕"]
        effects = ["背景滑入", "字幕条动画", "人物介绍卡", "文字擦开"]

        for i in range(num_shots):
            shots.append(Shot(
                shot_id=f"{scene.scene_id}_s{i+1}",
                start_time=scene.start_time + i * shot_dur,
                duration=shot_dur,
                shot_size=shot_sizes[i % len(shot_sizes)],
                camera_move=camera_moves[i % len(camera_moves)],
                description=f"内容点{index+1}.{i+1}: 展示{idea}的相关画面",
                subtitle=f"核心信息点{index+1}.{i+1}",
                effect_hint=effects[(index + i) % len(effects)],
                emotion=scene.emotion,
                visual_ref=f"与{idea}相关的高质量画面",
            ))
        return shots

    def _build_cta_shots(self, scene: Scene, script: Script) -> List[Shot]:
        """构建号召镜头"""
        shots = []
        # 镜头1: 总结
        shots.append(Shot(
            shot_id=f"{scene.scene_id}_s1",
            start_time=scene.start_time,
            duration=scene.duration * 0.5,
            shot_size=ShotSize.MEDIUM,
            camera_move="缓慢拉远",
            description="一句话总结核心价值",
            subtitle="以上就是全部内容",
            effect_hint="文字擦开",
            emotion=Emotion.RESOLUTION,
        ))
        # 镜头2: 号召行动
        shots.append(Shot(
            shot_id=f"{scene.scene_id}_s2",
            start_time=scene.start_time + scene.duration * 0.5,
            duration=scene.duration * 0.5,
            shot_size=ShotSize.CLOSEUP,
            camera_move="固定",
            description="引导点赞/关注/评论",
            subtitle=script.cta,
            effect_hint="蒙版快闪+发光轮廓",
            emotion=Emotion.CLIMAX,
        ))
        return shots

    def save(self, script: Script, output_dir: str) -> str:
        """保存剧本为JSON+Markdown"""
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.join(output_dir, f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        # JSON
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump(script.to_dict(), f, ensure_ascii=False, indent=2)

        # Markdown
        with open(base + ".md", "w", encoding="utf-8") as f:
            f.write(script.to_markdown())

        return base

    def validate(self, script: Script) -> Dict[str, Any]:
        """验证剧本质量"""
        issues = []
        warnings = []

        # 检查总时长
        if abs(script.actual_duration - script.total_duration) > 1.0:
            warnings.append(f"实际时长({script.actual_duration:.1f}s)与目标({script.total_duration:.1f}s)偏差>1s")

        # 检查钩子
        if not script.hook or len(script.hook) < 5:
            issues.append("钩子文案缺失或过短")

        # 检查号召
        if not script.cta:
            issues.append("号召行动文案缺失")

        # 检查镜头数
        if script.total_shots < 5:
            warnings.append(f"镜头数过少({script.total_shots}个)，建议≥5")

        # 检查每场景有镜头
        for s in script.scenes:
            if not s.shots:
                issues.append(f"场景{s.scene_id}没有镜头")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_scenes": len(script.scenes),
            "total_shots": script.total_shots,
            "actual_duration": script.actual_duration,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("剧本引擎 cap_script_engine")
    print("=" * 60)
    engine = ScriptEngine()

    # 测试：生成一个探店视频剧本
    print("\n[测试] 生成探店视频剧本...")
    script = engine.generate(
        idea="做一条探店视频，介绍一家藏在巷子里的火锅店",
        genre=VideoGenre.EXPLORATION,
        duration=60.0,
        target_audience="本地美食爱好者",
    )

    print(f"\n标题: {script.title}")
    print(f"类型: {script.genre.value}")
    print(f"时长: {script.total_duration:.0f}s (实际{script.actual_duration:.1f}s)")
    print(f"场景数: {len(script.scenes)}")
    print(f"镜头数: {script.total_shots}")
    print(f"钩子: {script.hook}")
    print(f"号召: {script.cta}")

    print("\n场景结构:")
    for s in script.scenes:
        print(f"  {s.title}: {s.start_time:.1f}s-{s.end_time:.1f}s ({s.duration:.1f}s) [{s.emotion.value}] {len(s.shots)}镜头")

    # 验证
    result = engine.validate(script)
    print(f"\n验证: {'通过' if result['valid'] else '未通过'}")
    if result['issues']:
        print(f"  问题: {result['issues']}")
    if result['warnings']:
        print(f"  警告: {result['warnings']}")

    # 保存
    out = engine.save(script, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "script_outputs"))
    print(f"\n已保存: {out}.json / .md")
