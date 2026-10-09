#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BGM 智能匹配引擎
根据视频情绪/风格/节奏自动匹配最合适的背景音乐
"""
import os
import json
import random
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

BGM_DIR = r"D:\DobaoWork_Project\Ai_Video_Editor\material\bgm"
LIBRARY_FILE = os.path.join(BGM_DIR, "library.json")


class BGMMatcher:
    """BGM智能匹配引擎"""

    def __init__(self, library_path: str = None):
        self.library_path = library_path or LIBRARY_FILE
        self.tracks: List[Dict[str, Any]] = []
        self._load_library()

    def _load_library(self):
        """加载BGM标签库"""
        if not os.path.exists(self.library_path):
            logger.warning(f"BGM库不存在: {self.library_path}")
            return
        try:
            with open(self.library_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.tracks = data.get("tracks", [])
            logger.info(f"加载BGM库: {len(self.tracks)}首")
        except Exception as e:
            logger.error(f"加载BGM库失败: {e}")
            self.tracks = []

    def match(self, emotion: str = None, style: str = None,
              tempo: str = None, duration: float = None,
              keywords: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        智能匹配BGM
        Args:
            emotion: 情绪 (happy/sad/energetic/calm/romantic/tense/funny/inspiring)
            style: 风格 (cinematic/pop/electronic/acoustic/corporate/vlog/chinese/rock)
            tempo: 节奏 (slow/medium/fast)
            duration: 需要的时长（秒），用于过滤
            keywords: 关键词列表
        Returns:
            匹配的BGM曲目信息，包含完整路径
        """
        if not self.tracks:
            logger.warning("BGM库为空，无法匹配")
            return None

        candidates = self.tracks.copy()

        # 按情绪过滤
        if emotion:
            emotion = emotion.lower()
            scored = []
            for t in candidates:
                score = 0
                if emotion in t.get("emotions", []):
                    score += 10
                # 情绪标签相似度
                for e in t.get("emotions", []):
                    if emotion in e or e in emotion:
                        score += 3
                scored.append((score, t))
            scored.sort(key=lambda x: x[0], reverse=True)
            if scored and scored[0][0] > 0:
                max_score = scored[0][0]
                candidates = [t for s, t in scored if s == max_score]

        # 按风格过滤
        if style:
            style = style.lower()
            style_matches = [t for t in candidates if style in t.get("styles", [])]
            if style_matches:
                candidates = style_matches

        # 按节奏过滤
        if tempo:
            tempo = tempo.lower()
            tempo_matches = [t for t in candidates if t.get("tempo") == tempo]
            if tempo_matches:
                candidates = tempo_matches

        # 按时长过滤（需要比视频长或接近）
        if duration:
            duration_matches = [t for t in candidates if t.get("duration", 0) >= duration * 0.8]
            if duration_matches:
                candidates = duration_matches

        # 按关键词匹配
        if keywords:
            keyword_scores = []
            for t in candidates:
                score = 0
                tags = t.get("tags", []) + t.get("emotions", []) + t.get("styles", [])
                for kw in keywords:
                    kw_lower = kw.lower()
                    for tag in tags:
                        if kw_lower in str(tag).lower():
                            score += 2
                keyword_scores.append((score, t))
            keyword_scores.sort(key=lambda x: x[0], reverse=True)
            if keyword_scores and keyword_scores[0][0] > 0:
                max_score = keyword_scores[0][0]
                candidates = [t for s, t in keyword_scores if s == max_score]

        if not candidates:
            candidates = self.tracks  # 回退到全部

        # 随机选择一个（避免每次都一样）
        chosen = random.choice(candidates)

        # 补全完整路径
        result = dict(chosen)
        result["full_path"] = os.path.join(BGM_DIR, chosen["file"])
        return result

    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有BGM"""
        results = []
        for t in self.tracks:
            r = dict(t)
            r["full_path"] = os.path.join(BGM_DIR, t["file"])
            results.append(r)
        return results

    def get_by_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        """按ID获取BGM"""
        for t in self.tracks:
            if t["id"] == track_id:
                r = dict(t)
                r["full_path"] = os.path.join(BGM_DIR, t["file"])
                return r
        return None


# 全局单例
_matcher: Optional[BGMMatcher] = None


def get_matcher() -> BGMMatcher:
    global _matcher
    if _matcher is None:
        _matcher = BGMMatcher()
    return _matcher


def match_bgm(emotion: str = None, style: str = None,
              tempo: str = None, duration: float = None,
              keywords: List[str] = None) -> Optional[Dict[str, Any]]:
    """便捷函数：智能匹配BGM"""
    return get_matcher().match(emotion, style, tempo, duration, keywords)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    matcher = BGMMatcher()
    print(f"BGM库: {len(matcher.tracks)}首")
    print("\n--- 测试匹配 ---")
    for emotion in ["happy", "sad", "energetic", "calm", "romantic"]:
        result = matcher.match(emotion=emotion)
        if result:
            print(f"  {emotion:12s} -> {result['name']} ({result['file']})")
