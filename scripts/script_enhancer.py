"""
P23增强: 剧本深度语义理解
混合架构：LLM深度理解 + 规则增强兜底

功能：
1. 角色深度识别（角色关系、角色别名、角色性格）
2. 动作语义理解（复杂动作、动作链、施动者/受动者）
3. 情绪深度分析（上下文情绪、情绪变化、情绪强度）
4. 场景语义理解（场景氛围、场景转换、场景细节）
5. 剧情结构分析（开头/发展/高潮/结尾、节奏、冲突）
"""

import logging
logger = logging.getLogger(__name__)


import os
import re
import json
from typing import Dict, Any, List, Optional


class ScriptEnhancer:
    """剧本深度语义增强器"""

    # 共享钩子关键词列表（用于_detect_hooks和_generate_rhythm_suggestions）
    HOOK_KEYWORDS = [
        "你敢信", "万万没想到", "震惊", "离谱", "绝了", "太狠了",
        "千万别", "一定要看到最后", "不看后悔", "高能预警", "前方高能",
        "凭什么", "怎么回事", "到底为什么", "真相是", "结果竟然",
        "突然", "没想到", "谁知", "不料",
    ]

    def __init__(self, use_llm: bool = True):
        """
        初始化增强器

        Args:
            use_llm: 是否使用LLM（如果可用）
        """
        self.use_llm = use_llm
        self.llm_client = None

        if use_llm:
            try:
                from llm_client import LLMClient
                self.llm_client = LLMClient()
                if not self.llm_client.is_available:
                    logger.info("  ℹ️  LLM不可用，使用规则增强模式")
                    self.llm_client = None
            except ImportError:
                logger.info("  ℹ️  LLM客户端未安装，使用规则增强模式")

    @property
    def llm_available(self) -> bool:
        """LLM是否可用"""
        return self.llm_client is not None and self.llm_client.is_available

    def enhance(self, parsed_script: Dict[str, Any], raw_script: str = "") -> Dict[str, Any]:
        """
        增强剧本解析结果

        Args:
            parsed_script: P23原始解析结果
            raw_script: 原始剧本文本（可选，用于LLM深度理解）

        Returns:
            增强后的剧本解析结果
        """
        logger.info(f"\n[ScriptEnhancer] 深度语义增强...")
        logger.info(f"  LLM模式: {'开启' if self.llm_available else '规则增强'}")

        result = parsed_script.copy()

        # 1. 角色深度增强
        result["characters"] = self._enhance_characters(
            result.get("characters", []),
            raw_script
        )

        # 2. 分镜深度增强
        result["scenes"] = self._enhance_scenes(
            result.get("scenes", []),
            raw_script
        )

        # 3. 剧情结构分析
        result["structure"] = self._analyze_structure(
            result.get("scenes", []),
            raw_script
        )

        # 4. 深度语义分析（角色关系/情绪曲线/冲突/钩子/节奏）
        result["deep_analysis"] = self._deep_semantic_analysis(
            result.get("scenes", []),
            result.get("characters", []),
        )

        # 5. 如果LLM可用，进行深度理解
        if self.llm_available and raw_script:
            llm_result = self._llm_deep_understanding(raw_script)
            if llm_result:
                result = self._merge_llm_result(result, llm_result)

        # 统计
        char_count = len(result.get("characters", []))
        scene_count = len(result.get("scenes", []))
        logger.info(f"  ✅ 增强完成: {char_count}角色, {scene_count}分镜")
        if result.get("structure"):
            logger.info(f"  剧情结构: {result['structure'].get('summary', '')}")

        return result

    def _enhance_characters(self, characters: List[Dict], raw_script: str) -> List[Dict]:
        """角色深度增强"""
        enhanced = []
        for char in characters:
            enhanced_char = char.copy()

            # 推断角色性别
            name = enhanced_char.get("name", "")
            enhanced_char["gender"] = self._infer_gender(name, raw_script)

            # 推断角色性格（基于台词和动作）
            enhanced_char["personality"] = self._infer_personality(name, raw_script)

            # 角色重要性
            enhanced_char["importance"] = self._calc_importance(name, raw_script)

            enhanced.append(enhanced_char)

        # 按重要性排序
        enhanced.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return enhanced

    def _infer_gender(self, name: str, script: str) -> str:
        """推断角色性别"""
        # 基于名字的常见性别推断
        female_suffixes = ["娘", "姐", "妹", "女", "妈", "奶", "姨", "姑", "公主", "小姐", "夫人", "太太"]
        male_suffixes = ["哥", "弟", "男", "爸", "爷", "叔", "伯", "公子", "先生", "大爷", "老汉"]

        for suffix in female_suffixes:
            if suffix in name:
                return "female"
        for suffix in male_suffixes:
            if suffix in name:
                return "male"

        # 基于剧本中的代词
        female_pronouns = ["她", "姐姐", "妹妹", "女士", "小姐"]
        male_pronouns = ["他", "哥哥", "弟弟", "先生", "大叔"]

        # 简单统计：在角色名附近出现的代词
        female_count = 0
        male_count = 0
        for match in re.finditer(re.escape(name), script):
            context = script[max(0, match.start()-50):match.end()+50]
            female_count += sum(1 for p in female_pronouns if p in context)
            male_count += sum(1 for p in male_pronouns if p in context)

        if female_count > male_count:
            return "female"
        elif male_count > female_count:
            return "male"
        return "unknown"

    def _infer_personality(self, name: str, script: str) -> List[str]:
        """推断角色性格（基于关键词）"""
        personalities = []

        # 提取角色相关的台词和动作
        char_contexts = []
        for match in re.finditer(re.escape(name), script):
            context = script[max(0, match.start()-100):match.end()+100]
            char_contexts.append(context)

        context_text = " ".join(char_contexts)

        # 性格关键词映射
        personality_keywords = {
            "温柔": ["温柔", "轻声", "微笑", "安慰", "关心"],
            "暴躁": ["愤怒", "大吼", "咆哮", "摔", "砸", "怒"],
            "冷静": ["冷静", "平静", "淡定", "从容", "思考"],
            "活泼": ["活泼", "开心", "笑", "蹦", "跳", "兴奋"],
            "严肃": ["严肃", "严厉", "认真", "皱眉", "严肃"],
            "机智": ["机智", "聪明", "想", "计划", "办法", "主意"],
            "胆小": ["害怕", "恐惧", "颤抖", "退缩", "胆小"],
            "勇敢": ["勇敢", "冲", "挡", "保护", "不怕"],
        }

        for personality, keywords in personality_keywords.items():
            if any(kw in context_text for kw in keywords):
                personalities.append(personality)

        return personalities[:3]  # 最多3个性格标签

    def _calc_importance(self, name: str, script: str) -> float:
        """计算角色重要性（0-1）"""
        if not script:
            return 0.5

        # 基于出现次数
        count = len(re.findall(re.escape(name), script))
        # 基于台词数量
        dialogue_count = len(re.findall(re.escape(name) + r"[：:]", script))
        # 归一化
        importance = min(1.0, (count * 0.1 + dialogue_count * 0.3) / 10)
        return round(importance, 2)

    def _enhance_scenes(self, scenes: List[Dict], raw_script: str) -> List[Dict]:
        """分镜深度增强"""
        enhanced = []
        for i, scene in enumerate(scenes):
            enhanced_scene = scene.copy()

            # 场景氛围
            enhanced_scene["atmosphere"] = self._infer_atmosphere(scene, raw_script)

            # 场景情绪基调
            enhanced_scene["emotion_tone"] = self._infer_emotion_tone(scene)

            # 场景节奏（快/中/慢）
            enhanced_scene["pace"] = self._infer_pace(scene)

            # 场景在剧情中的位置
            if len(scenes) > 1:
                position = i / (len(scenes) - 1)
                if position < 0.2:
                    enhanced_scene["narrative_position"] = "opening"
                elif position < 0.5:
                    enhanced_scene["narrative_position"] = "rising"
                elif position < 0.8:
                    enhanced_scene["narrative_position"] = "climax"
                else:
                    enhanced_scene["narrative_position"] = "resolution"

            enhanced.append(enhanced_scene)

        return enhanced

    def _infer_atmosphere(self, scene: Dict, script: str) -> str:
        """推断场景氛围"""
        text = scene.get("description", "") + " " + scene.get("dialogue", "")

        atmosphere_keywords = {
            "紧张": ["紧张", "急促", "突然", "危险", "警报", "快跑"],
            "温馨": ["温馨", "温暖", "幸福", "微笑", "拥抱", "阳光"],
            "悲伤": ["悲伤", "难过", "哭泣", "眼泪", "失落", "孤独"],
            "欢快": ["欢快", "开心", "笑", "热闹", "庆祝", "欢乐"],
            "神秘": ["神秘", "黑暗", "迷雾", "未知", "诡异", "秘密"],
            "严肃": ["严肃", "正式", "会议", "审判", "宣誓"],
        }

        for atmosphere, keywords in atmosphere_keywords.items():
            if any(kw in text for kw in keywords):
                return atmosphere
        return "neutral"

    def _infer_emotion_tone(self, scene: Dict) -> str:
        """推断场景情绪基调"""
        actions = scene.get("actions", [])
        if isinstance(actions, list):
            action_text = " ".join(str(a) for a in actions)
        else:
            action_text = str(actions)

        positive = ["笑", "开心", "高兴", "兴奋", "拥抱", "庆祝", "成功"]
        negative = ["哭", "难过", "悲伤", "愤怒", "害怕", "失败", "受伤"]

        pos_count = sum(1 for kw in positive if kw in action_text)
        neg_count = sum(1 for kw in negative if kw in action_text)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    def _infer_pace(self, scene: Dict) -> str:
        """推断场景节奏"""
        actions = scene.get("actions", [])
        action_count = len(actions) if isinstance(actions, list) else 1
        duration = scene.get("duration", 5)

        if duration <= 0:
            return "medium"

        actions_per_second = action_count / duration

        if actions_per_second > 1.0:
            return "fast"
        elif actions_per_second > 0.3:
            return "medium"
        return "slow"

    def _analyze_structure(self, scenes: List[Dict], raw_script: str) -> Dict[str, Any]:
        """分析剧情结构"""
        if not scenes:
            return {}

        total_duration = sum(s.get("duration", 0) for s in scenes)

        # 识别高潮场景（情绪最强烈的场景）
        climax_scene = None
        max_intensity = 0
        for scene in scenes:
            intensity = self._calc_dramatic_intensity(scene)
            if intensity > max_intensity:
                max_intensity = intensity
                climax_scene = scene

        # 识别冲突
        conflicts = self._identify_conflicts(scenes, raw_script)

        # 剧情摘要
        summary = self._generate_structure_summary(scenes, climax_scene, conflicts)

        return {
            "total_duration": total_duration,
            "scene_count": len(scenes),
            "climax_scene": climax_scene.get("id") if climax_scene else None,
            "climax_intensity": max_intensity,
            "conflicts": conflicts,
            "summary": summary,
            "three_act_structure": self._three_act_analysis(scenes),
        }

    def _calc_dramatic_intensity(self, scene: Dict) -> float:
        """计算场景戏剧强度（0-1）"""
        intensity = 0.0

        # 基于动作数量
        actions = scene.get("actions", [])
        action_count = len(actions) if isinstance(actions, list) else 1
        intensity += min(0.4, action_count * 0.1)

        # 基于情绪关键词
        text = str(scene.get("description", "")) + str(scene.get("dialogue", ""))
        intense_keywords = ["突然", "紧急", "危险", "冲突", "战斗", "争吵", "爆发", "震惊", "秘密"]
        intensity += min(0.4, sum(1 for kw in intense_keywords if kw in text) * 0.1)

        # 基于场景位置（中间偏后通常是高潮）
        return round(min(1.0, intensity), 2)

    def _identify_conflicts(self, scenes: List[Dict], script: str) -> List[Dict]:
        """识别剧情冲突"""
        conflicts = []

        conflict_patterns = [
            {"type": "physical", "keywords": ["打", "揍", "踢", "摔", "战斗", "打架", "攻击"]},
            {"type": "verbal", "keywords": ["吵", "骂", "争", "辩论", "反驳", "质问"]},
            {"type": "emotional", "keywords": ["背叛", "欺骗", "误会", "伤心", "失望", "离开"]},
            {"type": "goal", "keywords": ["阻止", "阻止", "妨碍", "破坏", "抢夺", "争夺"]},
        ]

        for scene in scenes:
            text = str(scene.get("description", "")) + str(scene.get("dialogue", ""))
            for pattern in conflict_patterns:
                if any(kw in text for kw in pattern["keywords"]):
                    conflicts.append({
                        "scene_id": scene.get("id"),
                        "type": pattern["type"],
                        "description": f"场景{scene.get('id')}存在{pattern['type']}冲突",
                    })
                    break

        return conflicts

    def _generate_structure_summary(self, scenes: List[Dict], climax: Dict, conflicts: List[Dict]) -> str:
        """生成剧情结构摘要"""
        if not scenes:
            return "无场景"

        parts = []
        parts.append(f"共{len(scenes)}个场景")

        if climax:
            parts.append(f"高潮在场景{climax.get('id')}")

        if conflicts:
            conflict_types = set(c["type"] for c in conflicts)
            parts.append(f"包含{len(conflicts)}个冲突（{', '.join(conflict_types)}）")

        return "，".join(parts)

    def _three_act_analysis(self, scenes: List[Dict]) -> Dict[str, Any]:
        """三幕剧结构分析"""
        if len(scenes) < 3:
            return {}

        n = len(scenes)
        act1_end = max(1, n // 4)
        act2_end = max(act1_end + 1, 3 * n // 4)

        return {
            "act_1_setup": {
                "scenes": scenes[:act1_end],
                "description": "开端：建立背景、角色和初始冲突",
            },
            "act_2_confrontation": {
                "scenes": scenes[act1_end:act2_end],
                "description": "发展：冲突升级、角色面临挑战",
            },
            "act_3_resolution": {
                "scenes": scenes[act2_end:],
                "description": "结局：冲突解决、故事收尾",
            },
        }

    # ============ 深度语义分析（P23+增强） ============

    def _deep_semantic_analysis(self, scenes: List[Dict],
                                  characters: List[Dict]) -> Dict[str, Any]:
        """深度语义分析：角色关系/情绪曲线/冲突点/钩子/节奏优化/整体基调"""
        # 展平所有shots
        all_shots = []
        for scene in scenes:
            for shot in scene.get("shots", []):
                all_shots.append(shot)

        if not all_shots:
            # 兼容旧格式：scenes本身就是shots
            all_shots = scenes

        total_duration = 0
        if all_shots:
            total_duration = all_shots[-1].get("start", 0) + all_shots[-1].get("duration", 0)

        return {
            "character_relations": self._infer_character_relations(all_shots, characters),
            "emotion_curve": self._build_emotion_curve(all_shots),
            "conflict_points": self._identify_conflict_points(all_shots),
            "hooks": self._detect_hooks(all_shots, total_duration),
            "suspense": self._detect_suspense(all_shots, total_duration),
            "rhythm_suggestions": self._generate_rhythm_suggestions(all_shots, total_duration),
            "overall_tone": self._determine_overall_tone(all_shots),
            "conflict_level": self._calc_conflict_level(all_shots),
            "emotion_volatility": self._calc_emotion_volatility(all_shots),
        }

    def _infer_character_relations(self, shots: List[Dict],
                                     characters: List[Dict]) -> List[Dict]:
        """推断角色关系（对立/合作/上下级/服务/朋友）
        支持两种推断方式：
        1. 同框推断：两个角色在同一个shot中出现
        2. 对话推断：两个角色在相邻shot中进行对话交互（一问一答）
        """
        if len(characters) < 2:
            return []

        char_names = [c.get("name", "") for c in characters]
        char_id_to_name = {c.get("id", ""): c.get("name", "") for c in characters}
        relation_keywords = {
            "对立": ["吵", "骂", "打", "踢", "揍", "扇", "质问", "反驳", "抗议", "不满", "凭什么", "反对", "怒", "怎么回事"],
            "合作": ["一起", "共同", "合作", "帮忙", "协助", "配合", "商量", "讨论", "我们"],
            "上下级": ["老板", "经理", "主管", "员工", "下属", "领导", "命令", "汇报", "请示"],
            "服务": ["顾客", "客户", "客人", "服务员", "前台", "店员", "请问", "您好", "欢迎", "规定"],
            "朋友": ["朋友", "哥们", "姐妹", "闺蜜", "兄弟", "老友"],
        }

        relation_counts = {}  # (a,b) -> {type: count, evidence: []}

        # 方式1：同框推断
        for shot in shots:
            chars_in_shot = set()
            for ca in shot.get("characters", []):
                cid = ca.get("character_id", "")
                name = char_id_to_name.get(cid, "")
                if name:
                    chars_in_shot.add(name)

            if len(chars_in_shot) < 2:
                continue

            text = shot.get("description", "") + " " + " ".join(
                ca.get("dialogue", "") for ca in shot.get("characters", [])
            )

            char_list = sorted(chars_in_shot)
            for i in range(len(char_list)):
                for j in range(i + 1, len(char_list)):
                    key = (char_list[i], char_list[j])
                    if key not in relation_counts:
                        relation_counts[key] = {r: 0 for r in relation_keywords}
                        relation_counts[key]["evidence"] = []

                    for rel_type, keywords in relation_keywords.items():
                        if any(kw in text for kw in keywords):
                            relation_counts[key][rel_type] += 1
                            relation_counts[key]["evidence"].append(
                                f"[{shot.get('start', 0):.1f}s][同框] {text[:60]}"
                            )
                            break

        # 方式2：对话交互推断（相邻shot的角色对话）
        for i in range(len(shots) - 1):
            shot_a = shots[i]
            shot_b = shots[i + 1]

            # 获取两个shot的角色
            chars_a = set()
            for ca in shot_a.get("characters", []):
                name = char_id_to_name.get(ca.get("character_id", ""), "")
                if name:
                    chars_a.add(name)

            chars_b = set()
            for ca in shot_b.get("characters", []):
                name = char_id_to_name.get(ca.get("character_id", ""), "")
                if name:
                    chars_b.add(name)

            # 两个shot有不同角色，且都有台词 → 对话交互
            has_dialogue_a = any(ca.get("dialogue", "") for ca in shot_a.get("characters", []))
            has_dialogue_b = any(ca.get("dialogue", "") for ca in shot_b.get("characters", []))

            if chars_a and chars_b and chars_a != chars_b and has_dialogue_a and has_dialogue_b:
                # 取两个shot中不同的角色对
                for name_a in chars_a:
                    for name_b in chars_b:
                        if name_a == name_b:
                            continue
                        key = tuple(sorted([name_a, name_b]))
                        if key not in relation_counts:
                            relation_counts[key] = {r: 0 for r in relation_keywords}
                            relation_counts[key]["evidence"] = []

                        # 合并两个shot的文本进行关系判断
                        text = (shot_a.get("description", "") + " " +
                                " ".join(ca.get("dialogue", "") for ca in shot_a.get("characters", [])) + " " +
                                shot_b.get("description", "") + " " +
                                " ".join(ca.get("dialogue", "") for ca in shot_b.get("characters", [])))

                        for rel_type, keywords in relation_keywords.items():
                            if any(kw in text for kw in keywords):
                                relation_counts[key][rel_type] += 1
                                relation_counts[key]["evidence"].append(
                                    f"[{shot_a.get('start', 0):.1f}s][对话] {text[:60]}"
                                )
                                break
                        else:
                            # 没有匹配到关键词，默认标记为"对话"关系（最低置信度）
                            relation_counts[key]["对话"] = relation_counts[key].get("对话", 0) + 1
                            relation_counts[key]["evidence"].append(
                                f"[{shot_a.get('start', 0):.1f}s][对话交互] {name_a}↔{name_b}"
                            )

        # 汇总
        relations = []
        for (a, b), counts in relation_counts.items():
            evidence = counts.pop("evidence", [])
            total = sum(counts.values())
            if total == 0:
                continue

            # 优先选择具体关系类型（排除"对话"默认类型）
            specific_types = {k: v for k, v in counts.items() if k != "对话"}
            if specific_types:
                best_rel = max(specific_types, key=specific_types.get)
                confidence = specific_types[best_rel] / total
            else:
                best_rel = "对话"
                confidence = counts.get("对话", 0) / total

            relations.append({
                "char_a": a,
                "char_b": b,
                "relation_type": best_rel,
                "confidence": round(confidence, 2),
                "evidence_count": len(evidence),
                "evidence": evidence[:2],
            })

        return sorted(relations, key=lambda x: x["confidence"], reverse=True)

    def _build_emotion_curve(self, shots: List[Dict]) -> List[Dict]:
        """构建情绪曲线（每个shot每个角色的情绪点）"""
        emotion_intensity = {
            "愤怒": 0.9, "惊恐": 0.85, "惊讶": 0.7, "开心": 0.6,
            "得意": 0.55, "质问": 0.75, "冷笑": 0.6, "尴尬": 0.5,
            "委屈": 0.65, "悲伤": 0.7, "紧张": 0.6, "心慌意乱": 0.8,
            "结结巴巴": 0.55, "不紧不慢": 0.3, "低声下气": 0.45,
            "平静": 0.2, "严肃": 0.4, "无奈": 0.45, "坚定": 0.5,
            "害羞": 0.4, "happy": 0.6, "angry": 0.9, "sad": 0.7,
        }

        curve = []
        for shot in shots:
            time = shot.get("start", 0)
            for ca in shot.get("characters", []):
                emotion = ca.get("emotion", "平静")
                curve.append({
                    "time": round(time, 1),
                    "character_id": ca.get("character_id", ""),
                    "emotion": emotion,
                    "intensity": emotion_intensity.get(emotion, 0.4),
                })
        return curve

    def _identify_conflict_points(self, shots: List[Dict]) -> List[Dict]:
        """识别冲突点（带时间、类型、强度、角色）"""
        conflict_types = {
            "肢体冲突": {"keywords": ["打", "踢", "揍", "扇", "捶", "砸", "撞", "推", "扭打"], "intensity": 0.9},
            "言语冲突": {"keywords": ["吵", "骂", "质问", "质疑", "反驳", "顶嘴", "争辩", "抗议", "不满", "凭什么"], "intensity": 0.7},
            "情感冲突": {"keywords": ["误会", "误解", "委屈", "背叛", "欺骗", "隐瞒", "吃醋", "嫉妒"], "intensity": 0.65},
            "利益冲突": {"keywords": ["钱", "费", "价", "赔偿", "损失", "吃亏", "占便宜"], "intensity": 0.6},
            "权力冲突": {"keywords": ["规定", "制度", "权限", "命令", "服从", "反抗", "越权", "违规"], "intensity": 0.55},
        }

        conflicts = []
        for shot in shots:
            text = shot.get("description", "") + " " + " ".join(
                ca.get("dialogue", "") for ca in shot.get("characters", [])
            )
            chars = [ca.get("character_id", "") for ca in shot.get("characters", [])]

            for ctype, config in conflict_types.items():
                matched = [kw for kw in config["keywords"] if kw in text]
                if matched:
                    conflicts.append({
                        "time": round(shot.get("start", 0), 1),
                        "conflict_type": ctype,
                        "characters": chars,
                        "intensity": config["intensity"],
                        "keywords": matched[:3],
                        "description": text[:80],
                    })
                    break  # 每shot只识别一种主要冲突

        return conflicts

    def _detect_hooks(self, shots: List[Dict], total_duration: float) -> List[Dict]:
        """检测开头钩子（前20%内容）"""
        hooks = []
        hook_end = total_duration * 0.2 if total_duration > 0 else 5.0

        for shot in shots:
            if shot.get("start", 0) > hook_end:
                break
            text = shot.get("description", "") + " " + " ".join(
                ca.get("dialogue", "") for ca in shot.get("characters", [])
            )
            matched = [kw for kw in self.HOOK_KEYWORDS if kw in text]
            if matched:
                hooks.append({
                    "time": round(shot.get("start", 0), 1),
                    "keywords": matched[:3],
                    "description": text[:80],
                })
        return hooks

    def _detect_suspense(self, shots: List[Dict], total_duration: float) -> List[Dict]:
        """检测结尾悬念（后20%内容）"""
        suspense_keywords = [
            "未完待续", "敬请期待", "下集", "后续", "然后呢", "后来",
            "到底", "究竟", "真相", "秘密", "隐藏", "背后", "未知",
            "突然", "就在这时", "没想到",
        ]

        suspense_list = []
        suspense_start = total_duration * 0.8 if total_duration > 0 else 0

        for shot in shots:
            if shot.get("start", 0) < suspense_start:
                continue
            text = shot.get("description", "") + " " + " ".join(
                ca.get("dialogue", "") for ca in shot.get("characters", [])
            )
            matched = [kw for kw in suspense_keywords if kw in text]
            if matched:
                suspense_list.append({
                    "time": round(shot.get("start", 0), 1),
                    "keywords": matched[:3],
                    "description": text[:80],
                })
        return suspense_list

    def _generate_rhythm_suggestions(self, shots: List[Dict],
                                       total_duration: float) -> List[Dict]:
        """生成节奏优化建议"""
        suggestions = []

        if not shots:
            return suggestions

        # 1. 镜头时长均匀度检查
        durations = [s.get("duration", 0) for s in shots]
        avg_dur = sum(durations) / max(len(durations), 1)
        max_dur = max(durations) if durations else 0

        if max_dur > avg_dur * 2.5 and avg_dur > 0:
            idx = durations.index(max_dur)
            suggestions.append({
                "type": "时长优化",
                "priority": "medium",
                "description": f"第{idx+1}个镜头{max_dur:.1f}s超过平均值{avg_dur:.1f}s的2.5倍，建议拆分",
            })

        # 2. 开头钩子检查
        first_3s_shots = [s for s in shots if s.get("start", 0) < 3.0]
        if first_3s_shots:
            first_text = " ".join(
                s.get("description", "") + " " + " ".join(
                    ca.get("dialogue", "") for ca in s.get("characters", [])
                ) for s in first_3s_shots
            )
            if not any(w in first_text for w in self.HOOK_KEYWORDS):
                suggestions.append({
                    "type": "开头优化",
                    "priority": "high",
                    "description": "前3秒未检测到明确的钩子词，建议设置悬念或冲突以吸引观众",
                })

        # 3. 情绪波动检查
        emotions = []
        for s in shots:
            for ca in s.get("characters", []):
                emotions.append(ca.get("emotion", "平静"))
        if emotions:
            unique_emotions = len(set(emotions))
            if unique_emotions <= 2 and len(emotions) > 5:
                suggestions.append({
                    "type": "情绪节奏",
                    "priority": "low",
                    "description": f"全片仅{unique_emotions}种情绪，情绪变化偏少，建议增加情绪起伏",
                })

        # 4. 总时长检查
        if total_duration > 20:
            suggestions.append({
                "type": "时长控制",
                "priority": "medium",
                "description": f"总时长{total_duration:.1f}s超过短视频推荐时长（15-20s），建议精简",
            })

        return suggestions

    def _determine_overall_tone(self, shots: List[Dict]) -> str:
        """判断整体基调"""
        if not shots:
            return "中性"

        all_emotions = []
        for s in shots:
            for ca in s.get("characters", []):
                all_emotions.append(ca.get("emotion", "平静"))

        if not all_emotions:
            return "中性"

        # 统计情绪频率
        from collections import Counter
        emotion_counts = Counter(all_emotions)
        dominant = emotion_counts.most_common(1)[0][0]

        tone_map = {
            "愤怒": "紧张激烈", "惊恐": "惊悚紧张", "开心": "轻松愉快",
            "得意": "幽默诙谐", "委屈": "煽情催泪", "平静": "平淡叙事",
            "尴尬": "喜剧搞笑", "冷笑": "讽刺幽默", "happy": "轻松愉快",
            "angry": "紧张激烈",
        }
        return tone_map.get(dominant, "中性")

    def _calc_conflict_level(self, shots: List[Dict]) -> float:
        """计算整体冲突等级（0-1）"""
        conflicts = self._identify_conflict_points(shots)
        if not conflicts:
            return 0.0
        avg_intensity = sum(c["intensity"] for c in conflicts) / len(conflicts)
        # 冲突密度：每10秒一个冲突为正常
        total_dur = shots[-1].get("start", 0) + shots[-1].get("duration", 0) if shots else 1
        density = min(1.0, len(conflicts) / max(total_dur / 10, 1))
        return round(min(1.0, avg_intensity * 0.6 + density * 0.4), 2)

    def _calc_emotion_volatility(self, shots: List[Dict]) -> float:
        """计算情绪波动程度（0-1）"""
        emotions = []
        for s in shots:
            for ca in s.get("characters", []):
                emotions.append(ca.get("emotion", "平静"))

        if len(emotions) < 2:
            return 0.0

        changes = sum(1 for i in range(1, len(emotions)) if emotions[i] != emotions[i-1])
        return round(changes / (len(emotions) - 1), 2)

    def _llm_deep_understanding(self, script: str) -> Optional[Dict[str, Any]]:
        """使用LLM进行深度剧本理解"""
        if not self.llm_available:
            return None

        system_prompt = """你是一个专业的剧本分析师。请分析以下剧本，提取以下信息并以JSON格式回复：

{
  "characters": [
    {
      "name": "角色名",
      "gender": "male/female/unknown",
      "personality": ["性格标签1", "性格标签2"],
      "role": "主角/配角/反派/旁白",
      "relationships": [{"target": "其他角色名", "relation": "关系描述"}],
      "arc": "角色成长弧线描述"
    }
  ],
  "themes": ["主题1", "主题2"],
  "emotional_journey": ["开场情绪", "发展情绪", "高潮情绪", "结局情绪"],
  "key_moments": [
    {"time": "时间点", "description": "关键时刻描述", "emotion": "情绪"}
  ],
  "pacing": {"overall": "fast/medium/slow", "notes": "节奏分析"},
  "visual_suggestions": ["视觉风格建议1", "视觉风格建议2"]
}

请只返回JSON，不要包含其他文字。"""

        logger.info("  🤖 LLM深度理解中...")
        result = self.llm_client.chat_json(
            message=f"请分析以下剧本：\n\n{script[:5000]}",  # 限制长度
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=3000,
        )

        if result:
            logger.info("  ✅ LLM深度理解完成")
        else:
            logger.error("  ⚠️  LLM深度理解失败，使用规则增强结果")

        return result

    def _merge_llm_result(self, parsed: Dict, llm_result: Dict) -> Dict:
        """合并LLM理解结果到解析结果"""
        result = parsed.copy()

        # 合并角色信息
        if "characters" in llm_result and "characters" in result:
            llm_chars = {c["name"]: c for c in llm_result["characters"] if "name" in c}
            for char in result["characters"]:
                name = char.get("name", "")
                if name in llm_chars:
                    llm_char = llm_chars[name]
                    for key in ["gender", "personality", "role", "relationships", "arc"]:
                        if key in llm_char and key not in char:
                            char[key] = llm_char[key]

        # 合并主题
        if "themes" in llm_result:
            result["themes"] = llm_result["themes"]

        # 合并情绪旅程
        if "emotional_journey" in llm_result:
            result["emotional_journey"] = llm_result["emotional_journey"]

        # 合并关键时刻
        if "key_moments" in llm_result:
            result["key_moments"] = llm_result["key_moments"]

        # 合并节奏分析
        if "pacing" in llm_result:
            result["pacing_analysis"] = llm_result["pacing"]

        # 合并视觉建议
        if "visual_suggestions" in llm_result:
            result["visual_suggestions"] = llm_result["visual_suggestions"]

        # 标记使用了LLM
        result["enhanced_by_llm"] = True

        return result


if __name__ == "__main__":
    # 测试
    enhancer = ScriptEnhancer(use_llm=True)

    test_script = """
    豆包开心地走进房间，看到机器人正在等待。
    豆包说："你好，机器人！"
    机器人冷冷地回答："你好，豆包。"
    突然，女杀手从门外冲进来，大喊："你们都跑不掉！"
    豆包害怕地躲到机器人身后。
    机器人挡在豆包前面，严肃地说："我会保护你。"
    女杀手愤怒地冲了过来。
    """

    # 模拟P23解析结果
    parsed = {
        "title": "测试剧本",
        "characters": [
            {"name": "豆包", "description": "主角"},
            {"name": "机器人", "description": "配角"},
            {"name": "女杀手", "description": "反派"},
        ],
        "scenes": [
            {"id": 1, "description": "豆包走进房间", "duration": 3, "actions": ["走进"]},
            {"id": 2, "description": "对话", "duration": 4, "actions": ["说", "回答"]},
            {"id": 3, "description": "女杀手闯入", "duration": 3, "actions": ["冲进来", "大喊"]},
            {"id": 4, "description": "冲突", "duration": 5, "actions": ["躲", "挡", "说", "冲"]},
        ],
    }

    # 增强
    enhanced = enhancer.enhance(parsed, test_script)

    logger.info("\n增强结果:")
    logger.info(f"  角色数: {len(enhanced['characters'])}")
    for char in enhanced["characters"]:
        print(f"    {char['name']}: gender={char.get('gender')}, "
              f"personality={char.get('personality', [])}, "
              f"importance={char.get('importance')}")
    logger.info(f"  剧情结构: {enhanced.get('structure', {}).get('summary', '')}")
    logger.info(f"  LLM增强: {enhanced.get('enhanced_by_llm', False)}")
