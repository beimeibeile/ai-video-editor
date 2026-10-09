#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BGM库质量优化工具
- 过滤非BGM文件（TTS语音、短音效等）
- 改进标签系统（基于文件名+音频特征）
- 重新标签所有BGM文件
- 保存优化后的BGM库
"""

import sys
import os
import json
import logging
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# 添加skill路径
SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

from p3_bgm_library import BGMLibrary, BGMTrack


# 非BGM文件关键词（过滤掉这些）
NON_BGM_KEYWORDS = [
    "qwen3", "tts", "narration", "voice", "speech", "配音", "旁白", "语音",
    "emotion_", "comfyui_000", "周鸿祎", "知我",
]

# 增强版情绪关键词（中英文混合）
ENHANCED_EMOTION_KEYWORDS = {
    "happy": ["happy", "joy", "upbeat", "cheerful", "开心", "快乐", "欢快", "愉悦", "轻松", "欢乐", "喜悦", "明快", "活泼", "sunny", "bright"],
    "sad": ["sad", "melancholy", "emotional", "悲伤", "伤感", "忧郁", "抒情", "感人", "忧伤", "哀愁", "tear", "cry", "blue"],
    "energetic": ["energetic", "powerful", "epic", "intense", "激情", "热血", "震撼", "力量", "燃", "动感", "劲爆", "激昂", "action", "beat", "drum"],
    "calm": ["calm", "peaceful", "relaxing", "ambient", "平静", "舒缓", "放松", "治愈", "安静", "柔和", "宁静", "piano", "soft", "gentle", "slow"],
    "romantic": ["romantic", "love", "sweet", "浪漫", "甜蜜", "爱情", "温馨", "柔情", "romance", "heart"],
    "tense": ["tense", "suspense", "thriller", "紧张", "悬疑", "惊悚", "压迫", "dark", "mysterious", "horror", "fear", "imprisoned"],
    "funny": ["funny", "comedy", "humor", "搞笑", "幽默", "滑稽", "俏皮", "fun", "silly", "cartoon"],
    "inspiring": ["inspiring", "motivational", "corporate", "激励", "励志", "正能量", "大气", "hope", "dream", "success", "winner"],
    "neutral": ["neutral", "general", "bgm", "background", "背景", "通用", "default"],
}

# 增强版风格关键词
ENHANCED_STYLE_KEYWORDS = {
    "cinematic": ["cinematic", "film", "movie", "电影", "影视", "大片", "trailer", "teaser"],
    "pop": ["pop", "流行", "时尚", "潮流", "modern", "dance"],
    "electronic": ["electronic", "edm", "synth", "电子", "电音", "合成器", "techno", "house"],
    "acoustic": ["acoustic", "guitar", "piano", "原声", "吉他", "钢琴", "不插电", "folk"],
    "corporate": ["corporate", "business", "presentation", "商务", "企业", "演示", "office"],
    "vlog": ["vlog", "lifestyle", "travel", "生活", "旅行", "日常", "youtube"],
    "chinese": ["chinese", "guzheng", "erhu", "中国风", "古风", "古筝", "二胡", "民族", "traditional"],
    "rock": ["rock", "metal", "punk", "摇滚", "金属", "朋克", "guitar"],
    "hiphop": ["hiphop", "hip-hop", "rap", "嘻哈", "说唱", "beat"],
    "jazz": ["jazz", "爵士", "blues", "蓝调", "saxophone"],
    "ambient": ["ambient", "环境", "氛围", "space", "atmosphere"],
    "orchestral": ["orchestral", "orchestra", "交响乐", "管弦", "strings", "violin", "cello"],
}


class BGMLibraryOptimizer:
    """BGM库质量优化器"""

    def __init__(self, library: BGMLibrary = None):
        self.library = library or BGMLibrary()
        self.original_count = len(self.library.tracks)
        self.removed_count = 0
        self.relabeled_count = 0

    def is_bgm_file(self, track: BGMTrack) -> bool:
        """判断是否为真正的BGM文件"""
        fname = track.file_name.lower()
        fpath = track.file_path.lower()

        # 过滤非BGM关键词
        for kw in NON_BGM_KEYWORDS:
            if kw.lower() in fname or kw.lower() in fpath:
                return False

        # 过滤过短的文件（小于2秒可能是音效）
        if track.duration < 2.0:
            return False

        return True

    def filter_non_bgm(self) -> int:
        """过滤非BGM文件"""
        to_remove = []
        for path, track in self.library.tracks.items():
            if not self.is_bgm_file(track):
                to_remove.append(path)

        for path in to_remove:
            del self.library.tracks[path]
            self.removed_count += 1

        logger.info(f"过滤非BGM文件: 移除{self.removed_count}首，剩余{len(self.library.tracks)}首")
        return self.removed_count

    def enhanced_label(self, track: BGMTrack) -> BGMTrack:
        """增强版标签"""
        fname = track.file_name.lower()
        fpath = track.file_path.lower()
        text = f"{fname} {fpath}"

        # 情绪标签
        emotions = self._match_keywords(text, ENHANCED_EMOTION_KEYWORDS)
        if not emotions:
            # 根据音频特征默认分类
            if track.duration > 60:
                emotions = ["calm"]
            elif track.bitrate > 192000:
                emotions = ["energetic"]
            else:
                emotions = ["neutral"]

        # 风格标签
        styles = self._match_keywords(text, ENHANCED_STYLE_KEYWORDS)
        if not styles:
            styles = ["general"]

        # 更新标签
        track.emotions = emotions
        track.styles = styles
        self.relabeled_count += 1

        return track

    def _match_keywords(self, text: str, keyword_map: Dict[str, List[str]]) -> List[str]:
        """关键词匹配"""
        matched = []
        text_lower = text.lower()
        for tag, keywords in keyword_map.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    matched.append(tag)
                    break
        return matched

    def relabel_all(self) -> int:
        """重新标签所有BGM文件"""
        for path, track in self.library.tracks.items():
            self.enhanced_label(track)
        logger.info(f"重新标签: {self.relabeled_count}首")
        return self.relabeled_count

    def optimize(self) -> Dict[str, Any]:
        """执行完整优化流程"""
        logger.info("=" * 50)
        logger.info("BGM库质量优化开始")
        logger.info(f"原始曲目数: {self.original_count}")

        # 1. 过滤非BGM
        self.filter_non_bgm()

        # 2. 重新标签
        self.relabel_all()

        # 3. 保存
        self.library.save()

        # 4. 统计
        stats = self.library.get_stats()

        result = {
            "original_count": self.original_count,
            "removed_count": self.removed_count,
            "relabeled_count": self.relabeled_count,
            "final_count": len(self.library.tracks),
            "stats": stats,
        }

        logger.info("=" * 50)
        logger.info("BGM库质量优化完成")
        logger.info(f"  原始: {self.original_count}首")
        logger.info(f"  移除: {self.removed_count}首")
        logger.info(f"  重标签: {self.relabeled_count}首")
        logger.info(f"  最终: {len(self.library.tracks)}首")
        logger.info(f"  情绪分布: {stats['emotions']}")
        logger.info(f"  风格分布: {stats['styles']}")

        return result

    def print_summary(self):
        """打印优化摘要"""
        stats = self.library.get_stats()
        print("\n=== BGM库优化摘要 ===")
        print(f"原始曲目: {self.original_count}")
        print(f"移除非BGM: {self.removed_count}")
        print(f"重新标签: {self.relabeled_count}")
        print(f"最终曲目: {len(self.library.tracks)}")
        print(f"平均时长: {stats['avg_duration']:.1f}秒")
        print("\n情绪分布:")
        for e, c in sorted(stats['emotions'].items(), key=lambda x: -x[1]):
            print(f"  {e}: {c}首")
        print("\n风格分布:")
        for s, c in sorted(stats['styles'].items(), key=lambda x: -x[1]):
            print(f"  {s}: {c}首")


if __name__ == "__main__":
    optimizer = BGMLibraryOptimizer()
    result = optimizer.optimize()
    optimizer.print_summary()
