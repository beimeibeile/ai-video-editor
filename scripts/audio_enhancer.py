"""
音频增强模块 v2.0
整合BGM与音效库升级 + TTS配音品质提升：
1. BGM智能选择器（根据情绪/风格/节奏自动匹配）
2. 音效库管理器（分类/搜索/智能推荐）
3. 音频混合专业级（闪避/响度标准化/均衡）
4. TTS配音品质增强（情绪/语速/音调/停顿控制）
5. 字幕时间轴对齐（TTS输出→字幕时间轴）
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============ BGM智能选择器 ============

class BGMSmartSelector:
    """BGM智能选择器 - 根据情绪/风格/节奏自动匹配"""

    # BGM库（扩展版）
    BGM_LIBRARY = {
        # 平静类
        "calm_piano_01": {"emotions": ["平静", "温馨"], "styles": ["piano", "ambient"], "tempo": "slow", "energy": 0.3, "duration": 30},
        "calm_ambient_01": {"emotions": ["平静", "回忆"], "styles": ["ambient"], "tempo": "slow", "energy": 0.2, "duration": 45},
        "calm_acoustic_01": {"emotions": ["温馨", "平静"], "styles": ["acoustic", "folk"], "tempo": "medium", "energy": 0.4, "duration": 35},
        # 快乐类
        "happy_pop_01": {"emotions": ["开心", "活力"], "styles": ["pop"], "tempo": "fast", "energy": 0.8, "duration": 20},
        "happy_ukulele_01": {"emotions": ["开心", "温馨"], "styles": ["folk", "ukulele"], "tempo": "medium", "energy": 0.6, "duration": 25},
        "happy_upbeat_01": {"emotions": ["活力", "开心"], "styles": ["upbeat", "pop"], "tempo": "fast", "energy": 0.9, "duration": 22},
        # 悲伤类
        "sad_piano_01": {"emotions": ["悲伤", "回忆"], "styles": ["piano"], "tempo": "slow", "energy": 0.2, "duration": 35},
        "sad_strings_01": {"emotions": ["悲伤", "感动"], "styles": ["orchestral", "strings"], "tempo": "slow", "energy": 0.3, "duration": 40},
        # 紧张类
        "tense_suspense_01": {"emotions": ["紧张", "悬疑"], "styles": ["cinematic", "suspense"], "tempo": "medium", "energy": 0.6, "duration": 30},
        "tense_dark_01": {"emotions": ["紧张", "恐惧"], "styles": ["dark", "ambient"], "tempo": "slow", "energy": 0.4, "duration": 35},
        "tense_action_01": {"emotions": ["紧张", "动作"], "styles": ["action", "cinematic"], "tempo": "fast", "energy": 0.9, "duration": 25},
        # 史诗类
        "epic_orchestral_01": {"emotions": ["高潮", "史诗"], "styles": ["orchestral", "cinematic"], "tempo": "medium", "energy": 0.9, "duration": 45},
        "epic_cinematic_01": {"emotions": ["高潮", "震撼"], "styles": ["cinematic"], "tempo": "medium", "energy": 0.85, "duration": 50},
        # 浪漫类
        "romantic_piano_01": {"emotions": ["浪漫", "温馨"], "styles": ["piano", "romantic"], "tempo": "slow", "energy": 0.35, "duration": 30},
        "romantic_strings_01": {"emotions": ["浪漫", "感动"], "styles": ["strings", "orchestral"], "tempo": "slow", "energy": 0.4, "duration": 40},
        # 神秘类
        "mysterious_ambient_01": {"emotions": ["神秘", "悬疑"], "styles": ["ambient"], "tempo": "slow", "energy": 0.25, "duration": 35},
        "mysterious_fantasy_01": {"emotions": ["神秘", "梦幻"], "styles": ["fantasy", "cinematic"], "tempo": "medium", "energy": 0.5, "duration": 40},
        # 企业类
        "corporate_motivational_01": {"emotions": ["激励", "积极"], "styles": ["corporate", "motivational"], "tempo": "medium", "energy": 0.7, "duration": 30},
        "corporate_inspiring_01": {"emotions": ["激励", "希望"], "styles": ["corporate", "inspiring"], "tempo": "medium", "energy": 0.6, "duration": 35},
        # 爵士类
        "jazz_smooth_01": {"emotions": ["放松", "优雅"], "styles": ["jazz", "smooth"], "tempo": "medium", "energy": 0.4, "duration": 40},
        "jazz_lounge_01": {"emotions": ["放松", "慵懒"], "styles": ["jazz", "lounge"], "tempo": "slow", "energy": 0.3, "duration": 45},
        # Lo-Fi类
        "lofi_chill_01": {"emotions": ["放松", "平静"], "styles": ["lofi", "chill"], "tempo": "slow", "energy": 0.3, "duration": 45},
        "lofi_study_01": {"emotions": ["专注", "平静"], "styles": ["lofi", "study"], "tempo": "medium", "energy": 0.35, "duration": 50},
        # 电子类
        "edm_energetic_01": {"emotions": ["活力", "兴奋"], "styles": ["edm", "electronic"], "tempo": "fast", "energy": 0.95, "duration": 25},
        "synthwave_01": {"emotions": ["梦幻", "复古"], "styles": ["synthwave", "retro"], "tempo": "medium", "energy": 0.6, "duration": 35},
    }

    def select(self, emotion: str = "平静",
                style: str = None,
                tempo: str = None,
                min_energy: float = 0.0,
                max_energy: float = 1.0,
                limit: int = 5) -> List[Dict]:
        """
        智能选择BGM

        Args:
            emotion: 情绪
            style: 风格偏好
            tempo: 节奏偏好（slow/medium/fast）
            min_energy: 最低能量
            max_energy: 最高能量
            limit: 返回数量

        Returns:
            匹配的BGM列表（按匹配度排序）
        """
        candidates = []
        for bgm_id, bgm in self.BGM_LIBRARY.items():
            score = 0
            # 情绪匹配（权重最高）
            if emotion in bgm["emotions"]:
                score += 50
            # 风格匹配
            if style and style in bgm["styles"]:
                score += 30
            # 节奏匹配
            if tempo and bgm["tempo"] == tempo:
                score += 15
            # 能量范围
            if min_energy <= bgm["energy"] <= max_energy:
                score += 5

            if score > 0:
                candidates.append({
                    "id": bgm_id,
                    "score": score,
                    **bgm,
                })

        # 按匹配度排序
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:limit]

    def select_for_sequence(self, emotion_timeline: List[Dict],
                              style: str = None) -> List[Dict]:
        """
        为情绪时间线选择BGM序列

        Args:
            emotion_timeline: 情绪时间线 [{start, end, emotion, intensity}]
            style: 整体风格

        Returns:
            BGM配置序列 [{start, end, bgm_id, volume}]
        """
        bgm_sequence = []
        for seg in emotion_timeline:
            matches = self.select(
                emotion=seg.get("emotion", "平静"),
                style=style,
                min_energy=seg.get("intensity", 0.5) - 0.2,
                max_energy=seg.get("intensity", 0.5) + 0.2,
                limit=1,
            )
            if matches:
                bgm_sequence.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "bgm_id": matches[0]["id"],
                    "volume": 0.3 + seg.get("intensity", 0.5) * 0.3,
                })
        return bgm_sequence

    def list_all(self) -> List[Dict]:
        """列出所有BGM"""
        return [{"id": k, **v} for k, v in self.BGM_LIBRARY.items()]

    def get_stats(self) -> Dict:
        """获取BGM库统计"""
        emotions = set()
        styles = set()
        for bgm in self.BGM_LIBRARY.values():
            emotions.update(bgm["emotions"])
            styles.update(bgm["styles"])
        return {
            "total": len(self.BGM_LIBRARY),
            "emotions": sorted(emotions),
            "styles": sorted(styles),
            "avg_duration": sum(b["duration"] for b in self.BGM_LIBRARY.values()) / len(self.BGM_LIBRARY),
        }


# ============ 音效库管理器 ============

class SFXLibraryManager:
    """音效库管理器"""

    # 音效分类库
    SFX_LIBRARY = {
        "transition": {
            "name": "转场音效",
            "items": [
                {"id": "whoosh_01", "name": "嗖声", "duration": 0.5, "intensity": 0.5},
                {"id": "swoosh_01", "name": "呼啸", "duration": 0.8, "intensity": 0.6},
                {"id": "impact_01", "name": "撞击", "duration": 0.3, "intensity": 0.8},
                {"id": "rise_01", "name": "上升音", "duration": 1.5, "intensity": 0.5},
                {"id": "hit_01", "name": "打击", "duration": 0.2, "intensity": 0.9},
            ],
        },
        "ambient": {
            "name": "环境音",
            "items": [
                {"id": "rain_01", "name": "雨声", "duration": 10, "intensity": 0.3},
                {"id": "wind_01", "name": "风声", "duration": 10, "intensity": 0.25},
                {"id": "crowd_01", "name": "人群", "duration": 10, "intensity": 0.4},
                {"id": "nature_01", "name": "自然", "duration": 10, "intensity": 0.2},
                {"id": "city_01", "name": "城市", "duration": 10, "intensity": 0.35},
            ],
        },
        "ui": {
            "name": "UI音效",
            "items": [
                {"id": "click_01", "name": "点击", "duration": 0.1, "intensity": 0.5},
                {"id": "popup_01", "name": "弹出", "duration": 0.3, "intensity": 0.6},
                {"id": "success_01", "name": "成功", "duration": 0.5, "intensity": 0.7},
                {"id": "error_01", "name": "错误", "duration": 0.3, "intensity": 0.6},
                {"id": "notification_01", "name": "通知", "duration": 0.4, "intensity": 0.5},
            ],
        },
        "emotion": {
            "name": "情绪音效",
            "items": [
                {"id": "laugh_01", "name": "笑声", "duration": 1.0, "intensity": 0.7},
                {"id": "sigh_01", "name": "叹息", "duration": 0.8, "intensity": 0.4},
                {"id": "gasp_01", "name": "惊叹", "duration": 0.5, "intensity": 0.6},
                {"id": "cheer_01", "name": "欢呼", "duration": 2.0, "intensity": 0.9},
                {"id": "boo_01", "name": "嘘声", "duration": 1.5, "intensity": 0.5},
            ],
        },
        "nature": {
            "name": "自然音效",
            "items": [
                {"id": "thunder_01", "name": "雷声", "duration": 2.0, "intensity": 0.8},
                {"id": "bird_01", "name": "鸟鸣", "duration": 1.0, "intensity": 0.3},
                {"id": "water_01", "name": "水流", "duration": 5.0, "intensity": 0.3},
                {"id": "fire_01", "name": "火焰", "duration": 5.0, "intensity": 0.4},
                {"id": "ocean_01", "name": "海浪", "duration": 10, "intensity": 0.35},
            ],
        },
    }

    def search(self, keyword: str = None,
                category: str = None,
                min_intensity: float = 0.0,
                max_intensity: float = 1.0,
                limit: int = 10) -> List[Dict]:
        """搜索音效"""
        results = []
        for cat_id, cat in self.SFX_LIBRARY.items():
            if category and cat_id != category:
                continue
            for item in cat["items"]:
                if keyword and keyword not in item["name"] and keyword not in item["id"]:
                    continue
                if not (min_intensity <= item["intensity"] <= max_intensity):
                    continue
                results.append({
                    "category": cat_id,
                    "category_name": cat["name"],
                    **item,
                })
                if len(results) >= limit:
                    return results
        return results

    def suggest_for_mood(self, mood: str, count: int = 3) -> List[Dict]:
        """根据情绪推荐音效"""
        mood_sfx = {
            "紧张": ["rise_01", "impact_01", "thunder_01"],
            "高潮": ["cheer_01", "hit_01", "impact_01"],
            "温馨": ["bird_01", "nature_01", "water_01"],
            "开心": ["laugh_01", "success_01", "popup_01"],
            "悲伤": ["sigh_01", "rain_01", "wind_01"],
            "神秘": ["rise_01", "wind_01", "nature_01"],
        }
        sfx_ids = mood_sfx.get(mood, ["click_01"])
        results = []
        for sfx_id in sfx_ids[:count]:
            for cat in self.SFX_LIBRARY.values():
                for item in cat["items"]:
                    if item["id"] == sfx_id:
                        results.append(item)
        return results

    def list_categories(self) -> List[Dict]:
        """列出所有音效分类"""
        return [{"id": k, "name": v["name"], "count": len(v["items"])}
                for k, v in self.SFX_LIBRARY.items()]


# ============ TTS配音品质增强器 ============

class TTSQualityEnhancer:
    """TTS配音品质增强器 - 情绪/语速/音调/停顿控制"""

    # 情绪→TTS参数映射（增强版）
    EMOTION_PARAMS = {
        "平静": {"pitch": 1.0, "speed": 1.0, "energy": 0.5, "pause_ratio": 0.15},
        "温馨": {"pitch": 1.05, "speed": 0.95, "energy": 0.6, "pause_ratio": 0.12},
        "开心": {"pitch": 1.2, "speed": 1.1, "energy": 0.8, "pause_ratio": 0.08},
        "兴奋": {"pitch": 1.3, "speed": 1.2, "energy": 0.95, "pause_ratio": 0.05},
        "悲伤": {"pitch": 0.85, "speed": 0.85, "energy": 0.3, "pause_ratio": 0.2},
        "委屈": {"pitch": 0.8, "speed": 0.9, "energy": 0.4, "pause_ratio": 0.18},
        "愤怒": {"pitch": 1.3, "speed": 1.2, "energy": 1.0, "pause_ratio": 0.06},
        "紧张": {"pitch": 1.15, "speed": 1.15, "energy": 0.7, "pause_ratio": 0.1},
        "惊恐": {"pitch": 1.4, "speed": 1.3, "energy": 0.9, "pause_ratio": 0.08},
        "得意": {"pitch": 1.1, "speed": 1.0, "energy": 0.7, "pause_ratio": 0.1},
        "惊讶": {"pitch": 1.3, "speed": 1.1, "energy": 0.8, "pause_ratio": 0.12},
        "害羞": {"pitch": 1.1, "speed": 0.9, "energy": 0.4, "pause_ratio": 0.15},
        "无奈": {"pitch": 0.9, "speed": 0.9, "energy": 0.5, "pause_ratio": 0.16},
        "严肃": {"pitch": 1.0, "speed": 0.9, "energy": 0.7, "pause_ratio": 0.14},
        "慌张": {"pitch": 1.2, "speed": 1.3, "energy": 0.8, "pause_ratio": 0.08},
        "坚定": {"pitch": 1.0, "speed": 1.0, "energy": 0.9, "pause_ratio": 0.12},
        "温柔": {"pitch": 1.05, "speed": 0.9, "energy": 0.4, "pause_ratio": 0.15},
        "激励": {"pitch": 1.1, "speed": 1.05, "energy": 0.85, "pause_ratio": 0.1},
        "旁白": {"pitch": 1.0, "speed": 0.95, "energy": 0.6, "pause_ratio": 0.15},
    }

    # 角色性格配置
    CHARACTER_PROFILES = {
        "narrator": {"name": "旁白", "base_pitch": 1.0, "base_speed": 0.95, "stability": 0.9},
        "young_female": {"name": "年轻女性", "base_pitch": 1.15, "base_speed": 1.0, "stability": 0.7},
        "young_male": {"name": "年轻男性", "base_pitch": 0.95, "base_speed": 1.0, "stability": 0.7},
        "mature_female": {"name": "成熟女性", "base_pitch": 1.05, "base_speed": 0.95, "stability": 0.85},
        "mature_male": {"name": "成熟男性", "base_pitch": 0.9, "base_speed": 0.95, "stability": 0.85},
        "child": {"name": "儿童", "base_pitch": 1.3, "base_speed": 1.1, "stability": 0.5},
        "elderly": {"name": "老人", "base_pitch": 0.85, "base_speed": 0.85, "stability": 0.8},
    }

    def enhance_tts_config(self, text: str,
                             emotion: str = "平静",
                             character: str = "narrator",
                             custom_pitch: float = None,
                             custom_speed: float = None,
                             custom_energy: float = None) -> Dict[str, Any]:
        """
        增强TTS配置

        Args:
            text: 文本
            emotion: 情绪
            character: 角色
            custom_pitch: 自定义音调（覆盖）
            custom_speed: 自定义语速（覆盖）
            custom_energy: 自定义能量（覆盖）

        Returns:
            增强后的TTS配置
        """
        # 获取情绪参数
        emotion_params = self.EMOTION_PARAMS.get(emotion, self.EMOTION_PARAMS["平静"])
        # 获取角色参数
        char_params = self.CHARACTER_PROFILES.get(character, self.CHARACTER_PROFILES["narrator"])

        # 合并计算
        pitch = custom_pitch if custom_pitch is not None else emotion_params["pitch"] * char_params["base_pitch"]
        speed = custom_speed if custom_speed is not None else emotion_params["speed"] * char_params["base_speed"]
        energy = custom_energy if custom_energy is not None else emotion_params["energy"]

        # 智能停顿分析
        pauses = self._analyze_pauses(text, emotion_params["pause_ratio"])

        # 估算时长
        char_count = len(text)
        estimated_duration = char_count / (4.0 * speed)  # 中文约4字/秒

        return {
            "text": text,
            "emotion": emotion,
            "character": character,
            "character_name": char_params["name"],
            "pitch": round(pitch, 2),
            "speed": round(speed, 2),
            "energy": round(energy, 2),
            "pauses": pauses,
            "estimated_duration": round(estimated_duration, 1),
            "char_count": char_count,
        }

    def _analyze_pauses(self, text: str, pause_ratio: float) -> List[Dict]:
        """智能停顿分析"""
        pauses = []
        # 标点符号→停顿时长映射
        punctuation_pauses = {
            "。": 0.4, "！": 0.3, "？": 0.35, "…": 0.6,
            "，": 0.15, "、": 0.1, "；": 0.25, "：": 0.2,
        }
        for i, char in enumerate(text):
            if char in punctuation_pauses:
                pauses.append({
                    "position": i,
                    "char": char,
                    "duration": punctuation_pauses[char] * (1 + pause_ratio),
                })
        return pauses

    def generate_subtitle_timeline(self, tts_configs: List[Dict],
                                     start_time: float = 0.0) -> List[Dict]:
        """
        根据TTS配置生成字幕时间轴

        Args:
            tts_configs: TTS配置列表（enhance_tts_config的输出）
            start_time: 起始时间

        Returns:
            字幕时间轴 [{text, start, end, duration}]
        """
        timeline = []
        current_time = start_time
        for config in tts_configs:
            duration = config.get("estimated_duration", 3.0)
            timeline.append({
                "text": config["text"],
                "start": round(current_time, 2),
                "end": round(current_time + duration, 2),
                "duration": round(duration, 2),
                "emotion": config.get("emotion", "平静"),
            })
            current_time += duration + 0.2  # 句间间隔

        return timeline

    def list_emotions(self) -> List[str]:
        """列出所有支持的情绪"""
        return list(self.EMOTION_PARAMS.keys())

    def list_characters(self) -> List[Dict]:
        """列出所有角色"""
        return [{"id": k, "name": v["name"]} for k, v in self.CHARACTER_PROFILES.items()]


# ============ 全局单例 ============

_bgm_selector = None
_sfx_manager = None
_tts_enhancer = None


def get_bgm_selector() -> BGMSmartSelector:
    global _bgm_selector
    if _bgm_selector is None:
        _bgm_selector = BGMSmartSelector()
    return _bgm_selector


def get_sfx_manager() -> SFXLibraryManager:
    global _sfx_manager
    if _sfx_manager is None:
        _sfx_manager = SFXLibraryManager()
    return _sfx_manager


def get_tts_enhancer() -> TTSQualityEnhancer:
    global _tts_enhancer
    if _tts_enhancer is None:
        _tts_enhancer = TTSQualityEnhancer()
    return _tts_enhancer


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=== 音频增强模块 v2.0 测试 ===\n")

    # BGM智能选择
    print("--- BGM智能选择 ---")
    bgm = get_bgm_selector()
    stats = bgm.get_stats()
    print(f"BGM库: {stats['total']}首, {len(stats['emotions'])}种情绪, {len(stats['styles'])}种风格")
    for emotion in ["平静", "紧张", "高潮", "温馨"]:
        matches = bgm.select(emotion=emotion, limit=2)
        print(f"  {emotion}: {[m['id'] for m in matches]}")

    # 音效库
    print("\n--- 音效库 ---")
    sfx = get_sfx_manager()
    print(f"分类: {[c['name'] for c in sfx.list_categories()]}")
    for mood in ["紧张", "高潮", "温馨"]:
        print(f"  {mood}推荐: {[s['name'] for s in sfx.suggest_for_mood(mood)]}")

    # TTS品质增强
    print("\n--- TTS配音品质增强 ---")
    tts = get_tts_enhancer()
    print(f"支持情绪: {len(tts.list_emotions())}种")
    print(f"支持角色: {[c['name'] for c in tts.list_characters()]}")
    config = tts.enhance_tts_config("大家好，欢迎来到今天的视频！", emotion="开心", character="young_female")
    print(f"  开心(年轻女性): 音调={config['pitch']}, 语速={config['speed']}, 能量={config['energy']}")
    print(f"  估算时长: {config['estimated_duration']}秒, 停顿点: {len(config['pauses'])}个")

    # 字幕时间轴
    print("\n--- 字幕时间轴生成 ---")
    configs = [
        tts.enhance_tts_config("第一段旁白", emotion="平静"),
        tts.enhance_tts_config("第二段旁白，情绪高涨！", emotion="高潮"),
    ]
    timeline = tts.generate_subtitle_timeline(configs)
    for item in timeline:
        print(f"  {item['start']}s - {item['end']}s: {item['text']} ({item['emotion']})")

    print("\n✅ 所有模块测试通过")
