"""
智能增强模块 v3.0
整合智能导演决策引擎v3.0 + 多模态素材智能管理 + 自然语言创作增强v2.0：
1. 智能导演决策引擎v3.0（多skill能力路由+情绪曲线+镜头语言决策）
2. 多模态素材智能管理（素材库/去重/标签/智能推荐）
3. 自然语言创作增强v2.0（意图识别/参数提取/创意扩展）
"""

import os
import sys
import json
import time
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============ 智能导演决策引擎v3.0 ============

class DirectorDecisionEngineV3:
    """智能导演决策引擎v3.0 - 多skill能力路由+情绪曲线+镜头语言决策"""

    # Skill能力注册表
    SKILL_CAPABILITIES = {
        "comfyui": {
            "name": "ComfyUI",
            "strengths": ["image_generation", "video_generation", "tts", "upscaling", "inpainting"],
            "quality_score": 0.85,
            "speed_score": 0.6,
            "cost_score": 0.9,  # 本地免费
        },
        "jianying": {
            "name": "剪映",
            "strengths": ["editing", "transitions", "effects", "text", "audio_mix", "export"],
            "quality_score": 0.8,
            "speed_score": 0.9,
            "cost_score": 1.0,
        },
        "remotion": {
            "name": "Remotion",
            "strengths": ["code_animation", "transparent_bg", "precise_control", "ui_animation"],
            "quality_score": 0.75,
            "speed_score": 0.7,
            "cost_score": 1.0,
        },
        "blender": {
            "name": "Blender",
            "strengths": ["3d_animation", "physics", "rendering", "particle_effects"],
            "quality_score": 0.9,
            "speed_score": 0.4,
            "cost_score": 1.0,
        },
        "minimax_h3": {
            "name": "MiniMax H3",
            "strengths": ["video_generation", "motion_control", "camera_control", "native_audio"],
            "quality_score": 0.95,
            "speed_score": 0.5,
            "cost_score": 0.9,
        },
    }

    # 镜头语言决策库
    SHOT_LANGUAGE = {
        "establishing": {"shot_type": "远景", "duration": 3.0, "camera": "static", "purpose": "建立场景"},
        "wide": {"shot_type": "全景", "duration": 2.5, "camera": "slow_pan", "purpose": "展示环境"},
        "medium": {"shot_type": "中景", "duration": 2.0, "camera": "static", "purpose": "人物互动"},
        "close_up": {"shot_type": "近景", "duration": 1.5, "camera": "slow_push", "purpose": "情绪表达"},
        "extreme_close_up": {"shot_type": "特写", "duration": 1.0, "camera": "static", "purpose": "细节强调"},
        "over_the_shoulder": {"shot_type": "过肩", "duration": 2.0, "camera": "static", "purpose": "对话场景"},
        "point_of_view": {"shot_type": "主观", "duration": 1.5, "camera": "handheld", "purpose": "代入感"},
    }

    # 情绪→镜头语言映射
    EMOTION_SHOT_MAP = {
        "平静": ["medium", "wide"],
        "温馨": ["close_up", "medium"],
        "紧张": ["close_up", "extreme_close_up", "point_of_view"],
        "高潮": ["extreme_close_up", "wide"],
        "回忆": ["close_up", "wide"],
        "梦幻": ["wide", "close_up"],
        "动作": ["medium", "point_of_view"],
    }

    def route_task(self, task_type: str,
                    requirements: Dict = None) -> Dict[str, Any]:
        """
        智能路由任务到最合适的skill

        Args:
            task_type: 任务类型
            requirements: 需求 {quality, speed, cost}

        Returns:
            路由决策 {selected_skill, alternatives, reason, confidence}
        """
        requirements = requirements or {}
        target_quality = requirements.get("quality", 0.8)
        target_speed = requirements.get("speed", 0.5)
        target_cost = requirements.get("cost", 0.8)

        # 评分每个skill
        scores = {}
        for skill_id, skill in self.SKILL_CAPABILITIES.items():
            if task_type not in skill["strengths"]:
                continue
            # 加权评分
            score = (
                skill["quality_score"] * 0.4 +
                skill["speed_score"] * 0.3 +
                skill["cost_score"] * 0.3
            )
            # 需求匹配调整
            if target_quality > 0.9:
                score *= skill["quality_score"]
            if target_speed > 0.8:
                score *= skill["speed_score"]
            scores[skill_id] = score

        if not scores:
            return {
                "selected_skill": None,
                "alternatives": [],
                "reason": f"没有skill支持任务类型: {task_type}",
                "confidence": 0.0,
            }

        # 排序
        sorted_skills = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = sorted_skills[0][0]
        confidence = sorted_skills[0][1] / sum(scores.values()) if scores else 0

        return {
            "selected_skill": selected,
            "selected_name": self.SKILL_CAPABILITIES[selected]["name"],
            "alternatives": [{"id": s[0], "name": self.SKILL_CAPABILITIES[s[0]]["name"], "score": round(s[1], 3)}
                             for s in sorted_skills[1:4]],
            "reason": f"任务={task_type}, 质量需求={target_quality}, 速度需求={target_speed} → 选择{self.SKILL_CAPABILITIES[selected]['name']}",
            "confidence": round(confidence, 3),
            "all_scores": {k: round(v, 3) for k, v in scores.items()},
        }

    def decide_shot(self, emotion: str = "平静",
                     purpose: str = None,
                     duration_hint: float = None) -> Dict[str, Any]:
        """
        镜头语言决策

        Args:
            emotion: 情绪
            purpose: 目的（覆盖自动选择）
            duration_hint: 时长提示

        Returns:
            镜头决策
        """
        if purpose and purpose in self.SHOT_LANGUAGE:
            shot = self.SHOT_LANGUAGE[purpose].copy()
        else:
            # 根据情绪选择
            shot_types = self.EMOTION_SHOT_MAP.get(emotion, ["medium"])
            shot = self.SHOT_LANGUAGE[shot_types[0]].copy()

        if duration_hint:
            shot["duration"] = duration_hint

        shot["emotion"] = emotion
        return shot

    def generate_emotion_curve(self, duration: float,
                                 structure: str = "classic") -> List[Dict]:
        """
        生成情绪曲线

        Args:
            duration: 总时长（秒）
            structure: 结构类型（classic/three_act/five_beat）

        Returns:
            情绪时间线 [{start, end, emotion, intensity}]
        """
        if structure == "three_act":
            # 三幕结构：铺垫→冲突→解决
            segments = [
                {"emotion": "平静", "intensity": 0.4, "ratio": 0.25},
                {"emotion": "紧张", "intensity": 0.7, "ratio": 0.35},
                {"emotion": "高潮", "intensity": 0.9, "ratio": 0.2},
                {"emotion": "平静", "intensity": 0.5, "ratio": 0.2},
            ]
        elif structure == "five_beat":
            # 五拍结构
            segments = [
                {"emotion": "平静", "intensity": 0.3, "ratio": 0.15},
                {"emotion": "温馨", "intensity": 0.5, "ratio": 0.2},
                {"emotion": "紧张", "intensity": 0.7, "ratio": 0.25},
                {"emotion": "高潮", "intensity": 1.0, "ratio": 0.2},
                {"emotion": "温馨", "intensity": 0.6, "ratio": 0.2},
            ]
        else:
            # 经典结构
            segments = [
                {"emotion": "平静", "intensity": 0.4, "ratio": 0.2},
                {"emotion": "温馨", "intensity": 0.6, "ratio": 0.25},
                {"emotion": "紧张", "intensity": 0.75, "ratio": 0.25},
                {"emotion": "高潮", "intensity": 0.95, "ratio": 0.15},
                {"emotion": "平静", "intensity": 0.5, "ratio": 0.15},
            ]

        timeline = []
        current_time = 0.0
        for seg in segments:
            seg_duration = duration * seg["ratio"]
            timeline.append({
                "start": round(current_time, 2),
                "end": round(current_time + seg_duration, 2),
                "emotion": seg["emotion"],
                "intensity": seg["intensity"],
            })
            current_time += seg_duration

        return timeline

    def list_skills(self) -> List[Dict]:
        """列出所有注册的skill能力"""
        return [{"id": k, "name": v["name"], "strengths": v["strengths"]}
                for k, v in self.SKILL_CAPABILITIES.items()]


# ============ 多模态素材智能管理器 ============

class MultimodalAssetManager:
    """多模态素材智能管理器 - 素材库/去重/标签/智能推荐"""

    def __init__(self, library_dir: str = None):
        self.library_dir = library_dir or os.path.join(
            os.path.expanduser("~"), "Videos", "剪映导出", "ai-video-editor", "asset_library"
        )
        os.makedirs(self.library_dir, exist_ok=True)
        self.index_file = os.path.join(self.library_dir, "asset_index.json")
        self.assets = self._load_index()

    def _load_index(self) -> Dict:
        """加载素材索引"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"images": {}, "videos": {}, "audio": {}, "total": 0}

    def _save_index(self) -> None:
        """保存素材索引"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.assets, f, ensure_ascii=False, indent=2)

    def _compute_hash(self, file_path: str) -> str:
        """计算文件哈希（用于去重）"""
        if not os.path.exists(file_path):
            return ""
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # 只读取前1MB用于快速哈希
                chunk = f.read(1024 * 1024)
                hasher.update(chunk)
                # 加上文件大小
                hasher.update(str(os.path.getsize(file_path)).encode())
        except Exception:
            pass
        return hasher.hexdigest()

    def add_asset(self, file_path: str,
                  asset_type: str = "image",
                  tags: List[str] = None,
                  metadata: Dict = None) -> Dict[str, Any]:
        """
        添加素材到库

        Args:
            file_path: 文件路径
            asset_type: 类型（image/video/audio）
            tags: 标签列表
            metadata: 元数据

        Returns:
            添加结果
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": "文件不存在"}

        # 计算哈希去重
        file_hash = self._compute_hash(file_path)
        type_key = f"{asset_type}s" if asset_type.endswith("s") else f"{asset_type}s"
        if type_key not in self.assets:
            self.assets[type_key] = {}

        # 检查重复
        for existing in self.assets[type_key].values():
            if existing.get("hash") == file_hash:
                return {
                    "success": False,
                    "error": "重复素材",
                    "existing_asset": existing,
                }

        # 添加素材
        asset_id = f"{asset_type}_{len(self.assets[type_key]) + 1:04d}"
        asset_info = {
            "id": asset_id,
            "path": os.path.abspath(file_path),
            "filename": os.path.basename(file_path),
            "type": asset_type,
            "hash": file_hash,
            "size": os.path.getsize(file_path),
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": time.time(),
            "use_count": 0,
            "rating": 0,
        }
        self.assets[type_key][asset_id] = asset_info
        self.assets["total"] = self.assets.get("total", 0) + 1
        self._save_index()

        return {"success": True, "asset_id": asset_id, "asset": asset_info}

    def search(self, keyword: str = None,
               asset_type: str = None,
               tags: List[str] = None,
               min_rating: float = 0,
               limit: int = 20) -> List[Dict]:
        """
        搜索素材

        Args:
            keyword: 关键词（匹配文件名/标签/元数据）
            asset_type: 类型过滤
            tags: 标签过滤
            min_rating: 最低评分
            limit: 返回数量

        Returns:
            匹配的素材列表
        """
        results = []
        type_keys = [f"{asset_type}s"] if asset_type else ["images", "videos", "audios"]

        for type_key in type_keys:
            for asset in self.assets.get(type_key, {}).values():
                # 评分过滤
                if asset.get("rating", 0) < min_rating:
                    continue
                # 标签过滤
                if tags and not all(t in asset.get("tags", []) for t in tags):
                    continue
                # 关键词过滤
                if keyword:
                    search_text = f"{asset['filename']} {' '.join(asset.get('tags', []))} {json.dumps(asset.get('metadata', {}))}"
                    if keyword.lower() not in search_text.lower():
                        continue
                results.append(asset)
                if len(results) >= limit:
                    return results

        return results

    def recommend(self, context: str = None,
                  asset_type: str = "image",
                  count: int = 5) -> List[Dict]:
        """
        智能推荐素材（基于使用频率和评分）

        Args:
            context: 上下文（用于标签匹配）
            asset_type: 类型
            count: 推荐数量

        Returns:
            推荐素材列表
        """
        type_key = f"{asset_type}s"
        assets = list(self.assets.get(type_key, {}).values())

        # 评分：使用频率*0.4 + 评分*0.6
        for asset in assets:
            asset["_score"] = asset.get("use_count", 0) * 0.4 + asset.get("rating", 0) * 0.6
            # 上下文匹配加分
            if context:
                for tag in asset.get("tags", []):
                    if context.lower() in tag.lower():
                        asset["_score"] += 0.5

        assets.sort(key=lambda x: x["_score"], reverse=True)
        return assets[:count]

    def get_stats(self) -> Dict:
        """获取素材库统计"""
        return {
            "total": self.assets.get("total", 0),
            "images": len(self.assets.get("images", {})),
            "videos": len(self.assets.get("videos", {})),
            "audios": len(self.assets.get("audios", {})),
            "library_dir": self.library_dir,
        }


# ============ 自然语言创作增强v2.0 ============

class NLCreativeEnhancerV2:
    """自然语言创作增强v2.0 - 意图识别/参数提取/创意扩展"""

    # 意图类型库
    INTENT_TYPES = {
        "create_video": {
            "name": "创建视频",
            "keywords": ["做视频", "生成视频", "创建视频", "制作视频", "拍视频", "出片"],
            "required_params": ["topic"],
            "optional_params": ["style", "duration", "resolution", "template"],
        },
        "generate_image": {
            "name": "生成图片",
            "keywords": ["生成图", "做图", "画图", "生成图片", "AI画图", "文生图"],
            "required_params": ["prompt"],
            "optional_params": ["style", "size", "model"],
        },
        "edit_video": {
            "name": "编辑视频",
            "keywords": ["剪辑", "编辑", "加特效", "加字幕", "加音乐", "调色"],
            "required_params": ["video_path"],
            "optional_params": ["effect", "filter", "transition"],
        },
        "add_subtitle": {
            "name": "添加字幕",
            "keywords": ["字幕", "加字幕", "字幕条", "文字"],
            "required_params": ["text"],
            "optional_params": ["style", "position", "animation"],
        },
        "add_music": {
            "name": "添加音乐",
            "keywords": ["音乐", "BGM", "配乐", "背景音乐", "加音乐"],
            "required_params": [],
            "optional_params": ["emotion", "style", "volume"],
        },
        "generate_tts": {
            "name": "生成配音",
            "keywords": ["配音", "TTS", "语音", "朗读", "旁白"],
            "required_params": ["text"],
            "optional_params": ["emotion", "voice", "speed"],
        },
        "export": {
            "name": "导出视频",
            "keywords": ["导出", "渲染", "输出", "生成mp4"],
            "required_params": ["draft_path"],
            "optional_params": ["resolution", "fps", "format"],
        },
        "query_status": {
            "name": "查询状态",
            "keywords": ["状态", "进度", "怎么样了", "完成了吗"],
            "required_params": [],
            "optional_params": ["task_id"],
        },
    }

    # 风格关键词映射
    STYLE_KEYWORDS = {
        "cinematic": ["电影", "电影感", "cinematic", "大片", "院线"],
        "anime": ["动漫", "动画", "anime", "二次元"],
        "realistic": ["真实", "写实", "realistic", "真人"],
        "cyberpunk": ["赛博朋克", "cyberpunk", "未来", "科幻"],
        "vintage": ["复古", "怀旧", "vintage", "老电影"],
        "minimal": ["极简", "简约", "minimal", "干净"],
        "vibrant": ["鲜艳", "活力", "vibrant", "明亮"],
        "dark": ["暗黑", "黑暗", "dark", "阴郁"],
    }

    def parse_instruction(self, instruction: str) -> Dict[str, Any]:
        """
        解析自然语言指令

        Args:
            instruction: 自然语言指令

        Returns:
            解析结果 {intent, confidence, params, raw}
        """
        instruction_lower = instruction.lower()

        # 意图识别
        intent_scores = {}
        for intent_id, intent in self.INTENT_TYPES.items():
            score = 0
            for keyword in intent["keywords"]:
                if keyword.lower() in instruction_lower:
                    score += 1
            if score > 0:
                intent_scores[intent_id] = score

        if not intent_scores:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "params": {},
                "raw": instruction,
                "suggestion": "未能识别意图，请明确说明要做什么（如：做视频/生成图片/加字幕）",
            }

        # 选择得分最高的意图
        selected_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[selected_intent] / sum(intent_scores.values())

        # 参数提取
        params = self._extract_params(instruction, selected_intent)

        return {
            "intent": selected_intent,
            "intent_name": self.INTENT_TYPES[selected_intent]["name"],
            "confidence": round(confidence, 3),
            "params": params,
            "raw": instruction,
            "all_intents": {k: v for k, v in intent_scores.items()},
        }

    def _extract_params(self, instruction: str, intent: str) -> Dict[str, Any]:
        """提取参数"""
        params = {}
        instruction_lower = instruction.lower()

        # 风格提取
        for style_id, keywords in self.STYLE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in instruction_lower:
                    params["style"] = style_id
                    break
            if "style" in params:
                break

        # 时长提取（"30秒"、"1分钟"）
        import re
        duration_match = re.search(r'(\d+(?:\.\d+)?)\s*(秒|s|分钟|min|分)', instruction_lower)
        if duration_match:
            value = float(duration_match.group(1))
            unit = duration_match.group(2)
            if unit in ["分钟", "min", "分"]:
                value *= 60
            params["duration"] = value

        # 分辨率提取
        if "竖屏" in instruction or "9:16" in instruction:
            params["resolution"] = "portrait"
        elif "横屏" in instruction or "16:9" in instruction:
            params["resolution"] = "landscape"
        elif "方形" in instruction or "1:1" in instruction:
            params["resolution"] = "square"

        # 情绪提取
        emotions = ["开心", "悲伤", "紧张", "平静", "温馨", "愤怒", "惊讶", "激励", "浪漫", "神秘"]
        for emotion in emotions:
            if emotion in instruction:
                params["emotion"] = emotion
                break

        # 主题提取（创建视频时）
        if intent == "create_video":
            # 尝试提取"关于XX"、"XX主题"
            topic_match = re.search(r'(?:关于|主题是|做一个|生成一个|制作一个)\s*(.+?)(?:的|视频|$)', instruction)
            if topic_match:
                params["topic"] = topic_match.group(1).strip()

        return params

    def expand_creative(self, base_idea: str,
                         direction: str = "general") -> List[str]:
        """
        创意扩展 - 基于基础想法生成多个创意方向

        Args:
            base_idea: 基础想法
            direction: 扩展方向（general/emotional/technical/narrative）

        Returns:
            创意方向列表
        """
        expansions = []

        if direction in ["general", "emotional"]:
            # 情绪维度扩展
            emotions = ["温馨", "紧张", "欢乐", "感动", "神秘", "激励"]
            for emotion in emotions[:3]:
                expansions.append(f"{base_idea} - {emotion}情绪版")

        if direction in ["general", "narrative"]:
            # 叙事结构扩展
            structures = ["倒叙开头", "悬念引入", "对比冲突", "第一人称", "时间线"]
            for structure in structures[:3]:
                expansions.append(f"{base_idea} - {structure}结构")

        if direction in ["general", "technical"]:
            # 技术风格扩展
            styles = ["电影感", "动漫风", "复古胶片", "赛博朋克", "极简风"]
            for style in styles[:3]:
                expansions.append(f"{base_idea} - {style}风格")

        return expansions

    def list_intents(self) -> List[Dict]:
        """列出所有支持的意图"""
        return [{"id": k, "name": v["name"], "keywords": v["keywords"]}
                for k, v in self.INTENT_TYPES.items()]


# ============ 全局单例 ============

_director_v3 = None
_asset_manager = None
_nl_enhancer = None


def get_director_v3() -> DirectorDecisionEngineV3:
    global _director_v3
    if _director_v3 is None:
        _director_v3 = DirectorDecisionEngineV3()
    return _director_v3


def get_asset_manager() -> MultimodalAssetManager:
    global _asset_manager
    if _asset_manager is None:
        _asset_manager = MultimodalAssetManager()
    return _asset_manager


def get_nl_enhancer() -> NLCreativeEnhancerV2:
    global _nl_enhancer
    if _nl_enhancer is None:
        _nl_enhancer = NLCreativeEnhancerV2()
    return _nl_enhancer


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=== 智能增强模块 v3.0 测试 ===\n")

    # 智能导演决策引擎v3.0
    print("--- 智能导演决策引擎v3.0 ---")
    director = get_director_v3()
    print(f"注册Skill: {[s['name'] for s in director.list_skills()]}")

    # 任务路由测试
    for task in ["video_generation", "editing", "3d_animation", "code_animation"]:
        route = director.route_task(task, requirements={"quality": 0.8, "speed": 0.5})
        print(f"  {task}: {route.get('selected_name', '无')} (置信度{route.get('confidence', 0)})")

    # 镜头语言决策
    for emotion in ["平静", "紧张", "高潮"]:
        shot = director.decide_shot(emotion=emotion)
        print(f"  {emotion}镜头: {shot['shot_type']} ({shot['duration']}s, {shot['camera']})")

    # 情绪曲线
    curve = director.generate_emotion_curve(30, structure="three_act")
    print(f"  情绪曲线(30s三幕): {len(curve)}段")

    # 多模态素材管理
    print("\n--- 多模态素材智能管理 ---")
    asset_mgr = get_asset_manager()
    stats = asset_mgr.get_stats()
    print(f"素材库: {stats['total']}个 (图{stats['images']}/视频{stats['videos']}/音频{stats['audios']})")

    # 自然语言创作增强
    print("\n--- 自然语言创作增强v2.0 ---")
    nl = get_nl_enhancer()
    print(f"支持意图: {len(nl.list_intents())}种")

    # 指令解析测试
    test_instructions = [
        "帮我做一个关于旅行的电影感视频，30秒竖屏",
        "生成一张赛博朋克风格的图片",
        "给这个视频加一个温馨的BGM",
    ]
    for inst in test_instructions:
        result = nl.parse_instruction(inst)
        print(f"  指令: {inst[:30]}...")
        print(f"    → 意图: {result.get('intent_name', '未知')} (置信度{result.get('confidence', 0)})")
        if result.get("params"):
            print(f"    → 参数: {result['params']}")

    # 创意扩展
    expansions = nl.expand_creative("城市夜景", direction="general")
    print(f"\n  创意扩展(城市夜景): {len(expansions)}个方向")
    for exp in expansions[:3]:
        print(f"    - {exp}")

    print("\n✅ 所有模块测试通过")
