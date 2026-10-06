"""
P25执行器: 多音轨混音器 v2.0
负责人声 + 音乐 + 环境音 + 音效的智能音量平衡

v2.0 新增功能：
1. P23深度语义集成 - 根据情绪曲线/冲突点/整体基调动态调节音量
2. 场景感知音量预设 - 紧张/平静/搞笑等场景自动调整
3. 情绪驱动音量曲线 - 高潮时音量提升，平静时降低
4. 多轨优先级管理 - 人声 > 重要音效 > BGM > 环境音
5. 音效闪避增强 - 重要音效出现时BGM也适当降低
6. 响度标准化 - 基于峰值的智能音量调节
7. 混音报告增强 - 详细的混音分析

基础功能：
- 音量预设（根据音频类型自动设置）
- 自动音量平衡（Ducking：有人声时BGM自动降低）
- 音频淡入淡出
- 音频标准化
"""

import os
from typing import Dict, Any, List, Optional, Tuple


# ============ 音量预设（根据音频类型） ============
VOLUME_PRESETS = {
    "tts": {
        "volume": 1.0,
        "fade_in": 0.05,
        "fade_out": 0.1,
        "duck_target": None,
        "priority": 1,  # 最高优先级
    },
    "vocals": {
        "volume": 1.0,
        "fade_in": 0.05,
        "fade_out": 0.1,
        "duck_target": None,
        "priority": 1,
    },
    "bgm": {
        "volume": 0.4,
        "fade_in": 1.0,
        "fade_out": 1.5,
        "duck_target": 0.2,
        "priority": 3,
    },
    "music": {
        "volume": 0.4,
        "fade_in": 1.0,
        "fade_out": 1.5,
        "duck_target": 0.2,
        "priority": 3,
    },
    "ambient": {
        "volume": 0.3,
        "fade_in": 2.0,
        "fade_out": 2.0,
        "duck_target": 0.15,
        "priority": 4,
    },
    "sfx": {
        "volume": 0.85,
        "fade_in": 0.01,
        "fade_out": 0.1,
        "duck_target": None,
        "priority": 2,  # 音效优先级高于BGM
    },
    "effect": {
        "volume": 0.85,
        "fade_in": 0.01,
        "fade_out": 0.1,
        "duck_target": None,
        "priority": 2,
    },
}

# 默认预设（未知类型）
DEFAULT_PRESET = {
    "volume": 0.6,
    "fade_in": 0.1,
    "fade_out": 0.2,
    "duck_target": None,
    "priority": 3,
}

# ============ 场景感知音量调整 ============
# 根据整体基调调整各类型音量的系数
SCENE_TONE_ADJUST = {
    "紧张激烈": {"tts": 1.0, "bgm": 1.3, "ambient": 1.2, "sfx": 1.1},
    "惊悚紧张": {"tts": 1.0, "bgm": 1.2, "ambient": 1.5, "sfx": 1.2},
    "轻松愉快": {"tts": 1.0, "bgm": 1.0, "ambient": 0.8, "sfx": 0.9},
    "幽默诙谐": {"tts": 1.0, "bgm": 0.9, "ambient": 0.7, "sfx": 1.0},
    "喜剧搞笑": {"tts": 1.0, "bgm": 0.9, "ambient": 0.7, "sfx": 1.1},
    "煽情催泪": {"tts": 1.05, "bgm": 1.1, "ambient": 0.9, "sfx": 0.8},
    "平淡叙事": {"tts": 1.0, "bgm": 0.8, "ambient": 1.0, "sfx": 0.9},
    "中性": {"tts": 1.0, "bgm": 1.0, "ambient": 1.0, "sfx": 1.0},
}

# 情绪强度对应的整体音量调整
EMOTION_VOLUME_MAP = {
    0.0: 0.85,  # 极平静
    0.2: 0.90,
    0.4: 0.95,
    0.6: 1.00,
    0.7: 1.05,
    0.8: 1.10,
    0.9: 1.15,
    1.0: 1.20,  # 极激烈
}


class AudioMixer:
    """多音轨混音器 v2.0 - 支持P23深度语义驱动的智能混音"""

    def __init__(self, ducking_enabled: bool = True, normalize_enabled: bool = True,
                 semantic_enabled: bool = True):
        """
        初始化混音器

        Args:
            ducking_enabled: 是否启用自动音量平衡（ducking）
            normalize_enabled: 是否启用音频标准化
            semantic_enabled: 是否启用P23深度语义驱动的智能混音
        """
        self.ducking_enabled = ducking_enabled
        self.normalize_enabled = normalize_enabled
        self.semantic_enabled = semantic_enabled

    def get_preset(self, audio_type: str) -> Dict[str, Any]:
        """获取音频类型的音量预设"""
        return VOLUME_PRESETS.get(audio_type.lower(), DEFAULT_PRESET)

    def mix(
        self,
        audio_files: List[Dict[str, Any]],
        tts_segments: List[Dict[str, Any]] = None,
        total_duration: float = 30.0,
        deep_analysis: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        混音处理：对所有音频文件进行音量平衡、淡入淡出、ducking、语义驱动调节

        Args:
            audio_files: 音频文件列表，每个包含path/start_time/duration/track_name/volume
            tts_segments: TTS人声片段列表（用于ducking），每个包含start_time/duration
            total_duration: 总时长（秒）
            deep_analysis: P23深度语义分析结果（character_relations/emotion_curve/
                           conflict_points/hooks/overall_tone/conflict_level/emotion_volatility）

        Returns:
            处理后的音频文件列表（增加了fade_in/fade_out/duck_keyframes/semantic_adjust等字段）
        """
        print(f"\n[AudioMixer] 混音处理: {len(audio_files)}个音频文件")
        if deep_analysis and self.semantic_enabled:
            tone = deep_analysis.get("overall_tone", "中性")
            conflict = deep_analysis.get("conflict_level", 0)
            volatility = deep_analysis.get("emotion_volatility", 0)
            print(f"  🧠 语义驱动: 基调={tone}, 冲突等级={conflict}, 情绪波动={volatility}")

        # 1. 应用音量预设和淡入淡出
        mixed_files = []
        for audio in audio_files:
            track_name = audio.get("track_name", "unknown")
            audio_type = self._infer_audio_type(track_name, audio.get("type", ""))
            preset = self.get_preset(audio_type)

            # 应用音量（如果用户没有显式设置）
            volume = audio.get("volume", None)
            if volume is None or volume == 1.0:
                volume = preset["volume"]

            # 淡入淡出
            fade_in = min(preset["fade_in"], audio.get("duration", 1.0) * 0.3)
            fade_out = min(preset["fade_out"], audio.get("duration", 1.0) * 0.3)

            mixed_audio = {
                **audio,
                "audio_type": audio_type,
                "volume": volume,
                "fade_in": fade_in,
                "fade_out": fade_out,
                "base_volume": volume,
                "duck_target": preset["duck_target"],
                "priority": preset.get("priority", 3),
            }
            mixed_files.append(mixed_audio)

        # 2. P23深度语义驱动的音量调整
        if self.semantic_enabled and deep_analysis:
            mixed_files = self._apply_semantic_adjustment(mixed_files, deep_analysis, total_duration)

        # 3. 自动音量平衡（Ducking）- 人声触发
        if self.ducking_enabled and tts_segments:
            mixed_files = self._apply_ducking(mixed_files, tts_segments, total_duration, trigger_type="tts")

        # 4. 音效闪避 - 重要音效触发BGM降低
        if self.ducking_enabled:
            sfx_segments = [
                {"start_time": a.get("start_time", 0), "duration": a.get("duration", 0.5)}
                for a in mixed_files
                if a.get("audio_type") in ("sfx", "effect") and a.get("priority", 3) <= 2
            ]
            if sfx_segments:
                mixed_files = self._apply_ducking(mixed_files, sfx_segments, total_duration,
                                                    trigger_type="sfx", duck_factor=0.85)

        # 5. 音频标准化
        if self.normalize_enabled:
            mixed_files = self._normalize(mixed_files)

        # 统计
        type_counts = {}
        for f in mixed_files:
            t = f.get("audio_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        print(f"  ✅ 混音完成: {type_counts}")

        return mixed_files

    def _infer_audio_type(self, track_name: str, audio_type: str = "") -> str:
        """从轨道名推断音频类型"""
        if audio_type:
            return audio_type.lower()

        track_lower = track_name.lower()
        if "tts" in track_lower or "vocal" in track_lower or "voice" in track_lower or "人声" in track_name:
            return "tts"
        elif "bgm" in track_lower or "music" in track_lower or "音乐" in track_name:
            return "bgm"
        elif "ambient" in track_lower or "环境" in track_name:
            return "ambient"
        elif "sfx" in track_lower or "effect" in track_lower or "音效" in track_name:
            return "sfx"
        else:
            return "unknown"

    def _apply_semantic_adjustment(
        self,
        audio_files: List[Dict[str, Any]],
        deep_analysis: Dict[str, Any],
        total_duration: float,
    ) -> List[Dict[str, Any]]:
        """
        P23深度语义驱动的音量调整

        根据：
        1. 整体基调 - 调整各类型音量系数
        2. 情绪曲线 - 构建时间相关的音量调整关键帧
        3. 冲突点 - 冲突时刻音量提升
        4. 冲突等级 - 整体音量偏移
        """
        overall_tone = deep_analysis.get("overall_tone", "中性")
        emotion_curve = deep_analysis.get("emotion_curve", [])
        conflict_points = deep_analysis.get("conflict_points", [])
        conflict_level = deep_analysis.get("conflict_level", 0)

        # 1. 整体基调调整
        tone_adjust = SCENE_TONE_ADJUST.get(overall_tone, SCENE_TONE_ADJUST["中性"])
        print(f"  🎭 基调调整: {overall_tone} -> {tone_adjust}")

        for audio in audio_files:
            audio_type = audio.get("audio_type", "unknown")
            base_vol = audio.get("base_volume", audio.get("volume", 0.5))

            # 应用基调系数
            tone_factor = tone_adjust.get(audio_type, 1.0)
            adjusted_vol = base_vol * tone_factor

            # 冲突等级整体偏移（BGM和环境音受影响更大）
            if audio_type in ("bgm", "ambient"):
                conflict_factor = 1.0 + conflict_level * 0.3
                adjusted_vol *= conflict_factor

            # 限制在合理范围
            adjusted_vol = max(0.05, min(1.0, adjusted_vol))
            audio["volume"] = adjusted_vol
            audio["semantic_adjust"] = {
                "tone_factor": tone_factor,
                "conflict_factor": 1.0 + conflict_level * 0.3 if audio_type in ("bgm", "ambient") else 1.0,
                "original_volume": base_vol,
            }

        # 2. 情绪曲线驱动的动态音量关键帧（仅对BGM和环境音）
        if emotion_curve and total_duration > 0:
            # 构建时间-情绪强度映射
            emotion_timeline = self._build_emotion_timeline(emotion_curve, total_duration)

            for audio in audio_files:
                audio_type = audio.get("audio_type", "")
                if audio_type not in ("bgm", "ambient"):
                    continue  # 只对BGM和环境音应用动态音量

                base_vol = audio.get("volume", 0.5)
                audio_start = audio.get("start_time", 0)
                audio_duration = audio.get("duration", 5)

                # 生成情绪驱动的音量关键帧
                emotion_keyframes = []
                sample_interval = max(0.5, audio_duration / 8)  # 最多8个采样点
                t = 0
                while t <= audio_duration:
                    abs_time = audio_start + t
                    emotion_intensity = self._get_emotion_at_time(emotion_timeline, abs_time)
                    vol_factor = self._emotion_to_volume_factor(emotion_intensity)
                    emotion_keyframes.append({
                        "time": round(t, 2),
                        "volume": round(base_vol * vol_factor, 3),
                        "emotion_intensity": emotion_intensity,
                    })
                    t += sample_interval

                if emotion_keyframes:
                    audio["emotion_keyframes"] = emotion_keyframes

        # 3. 冲突点音量提升（对BGM和音效）
        if conflict_points:
            print(f"  ⚔️  冲突点音量提升: {len(conflict_points)}个冲突点")
            for audio in audio_files:
                audio_type = audio.get("audio_type", "")
                if audio_type not in ("bgm", "sfx", "effect"):
                    continue

                base_vol = audio.get("volume", 0.5)
                audio_start = audio.get("start_time", 0)
                audio_duration = audio.get("duration", 5)
                audio_end = audio_start + audio_duration

                conflict_keyframes = []
                for conflict in conflict_points:
                    conflict_time = conflict.get("time", 0)
                    if conflict_time < audio_start or conflict_time > audio_end:
                        continue
                    rel_time = conflict_time - audio_start
                    intensity = conflict.get("intensity", 0.5)
                    boost = 1.0 + intensity * 0.2  # 冲突时提升0-20%

                    # 冲突前0.3秒开始提升，冲突后0.5秒恢复
                    conflict_keyframes.append({
                        "time": max(0, rel_time - 0.3),
                        "volume": base_vol,
                    })
                    conflict_keyframes.append({
                        "time": rel_time,
                        "volume": round(base_vol * boost, 3),
                    })
                    conflict_keyframes.append({
                        "time": min(audio_duration, rel_time + 0.5),
                        "volume": base_vol,
                    })

                if conflict_keyframes:
                    # 合并到emotion_keyframes或单独存储
                    existing = audio.get("emotion_keyframes", [])
                    existing.extend(conflict_keyframes)
                    existing.sort(key=lambda x: x["time"])
                    audio["emotion_keyframes"] = existing

        return audio_files

    def _build_emotion_timeline(self, emotion_curve: List[Dict], total_duration: float) -> List[Dict]:
        """构建时间-情绪强度时间线（合并同时刻的情绪，取最大值）"""
        timeline = {}
        for point in emotion_curve:
            time = point.get("time", 0)
            intensity = point.get("intensity", 0.5)
            if time not in timeline or intensity > timeline[time]:
                timeline[time] = intensity

        # 转为有序列表
        sorted_timeline = [{"time": t, "intensity": i} for t, i in sorted(timeline.items())]

        # 如果没有情绪点，添加默认值
        if not sorted_timeline:
            sorted_timeline = [{"time": 0, "intensity": 0.5}]

        return sorted_timeline

    def _get_emotion_at_time(self, timeline: List[Dict], time: float) -> float:
        """获取某时刻的情绪强度（线性插值）"""
        if not timeline:
            return 0.5

        # 找到前后两个点
        prev_point = timeline[0]
        next_point = timeline[-1]

        for point in timeline:
            if point["time"] <= time:
                prev_point = point
            if point["time"] >= time:
                next_point = point
                break

        # 线性插值
        if next_point["time"] == prev_point["time"]:
            return prev_point["intensity"]

        ratio = (time - prev_point["time"]) / (next_point["time"] - prev_point["time"])
        ratio = max(0, min(1, ratio))
        return prev_point["intensity"] + (next_point["intensity"] - prev_point["intensity"]) * ratio

    def _emotion_to_volume_factor(self, emotion_intensity: float) -> float:
        """情绪强度转音量系数"""
        # 找到最近的映射点
        keys = sorted(EMOTION_VOLUME_MAP.keys())
        for i in range(len(keys) - 1):
            if keys[i] <= emotion_intensity <= keys[i + 1]:
                ratio = (emotion_intensity - keys[i]) / (keys[i + 1] - keys[i])
                return EMOTION_VOLUME_MAP[keys[i]] + (EMOTION_VOLUME_MAP[keys[i + 1]] - EMOTION_VOLUME_MAP[keys[i]]) * ratio

        if emotion_intensity <= keys[0]:
            return EMOTION_VOLUME_MAP[keys[0]]
        return EMOTION_VOLUME_MAP[keys[-1]]

    def _apply_ducking(
        self,
        audio_files: List[Dict[str, Any]],
        trigger_segments: List[Dict[str, Any]],
        total_duration: float,
        trigger_type: str = "tts",
        duck_factor: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        应用自动音量平衡（Ducking）
        当有触发音频（人声/重要音效）时，BGM和环境音自动降低音量

        Args:
            audio_files: 音频文件列表
            trigger_segments: 触发片段列表（人声或重要音效）
            total_duration: 总时长
            trigger_type: 触发类型（tts/sfx）
            duck_factor: ducking强度系数（1.0=正常，0.85=音效触发时较弱）
        """
        if not trigger_segments:
            return audio_files

        # 构建触发时间轴
        buffer = 0.3 if trigger_type == "tts" else 0.15
        trigger_time_segments = []
        for seg in trigger_segments:
            start = max(0, seg.get("start_time", 0) - buffer)
            end = min(total_duration, seg.get("start_time", 0) + seg.get("duration", 3) + buffer)
            trigger_time_segments.append((start, end))

        # 合并重叠的触发片段
        trigger_time_segments.sort()
        merged_trigger = []
        for start, end in trigger_time_segments:
            if merged_trigger and start <= merged_trigger[-1][1]:
                merged_trigger[-1] = (merged_trigger[-1][0], max(merged_trigger[-1][1], end))
            else:
                merged_trigger.append((start, end))

        # 对需要duck的音频应用关键帧
        ducked_count = 0
        for audio in audio_files:
            duck_target = audio.get("duck_target")
            if duck_target is None:
                continue  # 不需要duck

            # 音效触发时，duck_target要乘以duck_factor（降低幅度更小）
            actual_duck_target = duck_target * duck_factor + audio.get("base_volume", 0.5) * (1 - duck_factor)
            actual_duck_target = max(0.05, actual_duck_target)

            base_volume = audio.get("volume", audio.get("base_volume", 0.5))
            audio_start = audio.get("start_time", 0)
            audio_duration = audio.get("duration", 5)
            audio_end = audio_start + audio_duration

            # 找出与触发片段重叠的时间段
            duck_keyframes = []
            for trig_start, trig_end in merged_trigger:
                overlap_start = max(audio_start, trig_start)
                overlap_end = min(audio_end, trig_end)
                if overlap_start >= overlap_end:
                    continue

                rel_start = overlap_start - audio_start
                rel_end = overlap_end - audio_start

                # 添加ducking关键帧（平滑过渡）
                fade_time = 0.2 if trigger_type == "tts" else 0.1
                duck_start = max(0, rel_start - fade_time)
                duck_end = min(audio_duration, rel_end + fade_time)

                duck_keyframes.append({"time": duck_start, "volume": base_volume})
                duck_keyframes.append({"time": rel_start, "volume": actual_duck_target})
                duck_keyframes.append({"time": rel_end, "volume": actual_duck_target})
                duck_keyframes.append({"time": duck_end, "volume": base_volume})

            if duck_keyframes:
                # 按时间排序并合并相邻关键帧
                duck_keyframes.sort(key=lambda x: x["time"])
                # 去重（时间差小于0.01秒的合并）
                merged = []
                for kf in duck_keyframes:
                    if merged and abs(kf["time"] - merged[-1]["time"]) < 0.01:
                        merged[-1]["volume"] = (merged[-1]["volume"] + kf["volume"]) / 2
                    else:
                        merged.append(kf)
                audio["duck_keyframes"] = merged
                ducked_count += 1

        trigger_label = "人声" if trigger_type == "tts" else "音效"
        print(f"  🎚️  Ducking({trigger_label}触发): {ducked_count}个音频应用了自动音量平衡")
        return audio_files

    def _normalize(self, audio_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        音频标准化：确保所有音频的音量在合理范围内
        v2.0: 基于优先级的智能标准化，高优先级音频音量上限更高
        """
        normalized_count = 0
        for audio in audio_files:
            volume = audio.get("volume", 0.5)
            priority = audio.get("priority", 3)

            # 高优先级（人声）允许更高音量上限
            max_vol = 1.0 if priority <= 1 else 0.9
            min_vol = 0.05

            if volume < min_vol:
                audio["volume"] = min_vol
                normalized_count += 1
            elif volume > max_vol:
                audio["volume"] = max_vol
                normalized_count += 1

        if normalized_count > 0:
            print(f"  📊 标准化: {normalized_count}个音频音量被调整到合理范围")

        return audio_files

    def generate_mix_report(self, audio_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成混音报告 v2.0 - 更详细的分析"""
        report = {
            "total": len(audio_files),
            "by_type": {},
            "by_priority": {},
            "volume_range": {"min": 1.0, "max": 0.0},
            "ducking_applied": 0,
            "semantic_adjusted": 0,
            "emotion_keyframes": 0,
            "has_fade": 0,
            "average_volume": 0.0,
        }

        total_vol = 0
        for audio in audio_files:
            audio_type = audio.get("audio_type", "unknown")
            report["by_type"][audio_type] = report["by_type"].get(audio_type, 0) + 1

            priority = audio.get("priority", 3)
            report["by_priority"][priority] = report["by_priority"].get(priority, 0) + 1

            volume = audio.get("volume", 0.5)
            total_vol += volume
            report["volume_range"]["min"] = min(report["volume_range"]["min"], volume)
            report["volume_range"]["max"] = max(report["volume_range"]["max"], volume)

            if audio.get("duck_keyframes"):
                report["ducking_applied"] += 1
            if audio.get("semantic_adjust"):
                report["semantic_adjusted"] += 1
            if audio.get("emotion_keyframes"):
                report["emotion_keyframes"] += len(audio.get("emotion_keyframes", []))
            if audio.get("fade_in", 0) > 0 or audio.get("fade_out", 0) > 0:
                report["has_fade"] += 1

        if report["total"] > 0:
            report["average_volume"] = round(total_vol / report["total"], 3)

        return report


if __name__ == "__main__":
    # 测试 v2.0
    mixer = AudioMixer(ducking_enabled=True, normalize_enabled=True, semantic_enabled=True)

    # 模拟音频文件
    audio_files = [
        {"path": "tts_001.mp3", "start_time": 0, "duration": 3, "track_name": "TTS", "volume": 1.0},
        {"path": "tts_002.mp3", "start_time": 5, "duration": 3, "track_name": "TTS", "volume": 1.0},
        {"path": "bgm_001.mp3", "start_time": 0, "duration": 10, "track_name": "BGM", "volume": 1.0},
        {"path": "ambient_001.mp3", "start_time": 0, "duration": 10, "track_name": "Ambient", "volume": 1.0},
        {"path": "sfx_001.mp3", "start_time": 2, "duration": 0.3, "track_name": "SFX", "volume": 1.0},
    ]

    # 模拟TTS片段
    tts_segments = [
        {"start_time": 0, "duration": 3},
        {"start_time": 5, "duration": 3},
    ]

    # 模拟P23深度语义分析结果
    deep_analysis = {
        "overall_tone": "紧张激烈",
        "conflict_level": 0.7,
        "emotion_volatility": 0.8,
        "emotion_curve": [
            {"time": 0, "character_id": "char_1", "emotion": "愤怒", "intensity": 0.9},
            {"time": 3, "character_id": "char_0", "emotion": "平静", "intensity": 0.2},
            {"time": 5, "character_id": "char_1", "emotion": "愤怒", "intensity": 0.9},
        ],
        "conflict_points": [
            {"time": 2, "conflict_type": "权力冲突", "intensity": 0.7},
        ],
    }

    # 混音
    result = mixer.mix(audio_files, tts_segments, total_duration=10, deep_analysis=deep_analysis)

    # 打印结果
    print("\n" + "=" * 60)
    print("混音结果:")
    print("=" * 60)
    for audio in result:
        print(f"\n  {audio['track_name']} ({audio['audio_type']}, priority={audio['priority']}):")
        print(f"    volume={audio['volume']:.3f}, base={audio['base_volume']:.3f}")
        print(f"    fade_in={audio['fade_in']:.2f}s, fade_out={audio['fade_out']:.2f}s")
        if audio.get("semantic_adjust"):
            print(f"    语义调整: tone_factor={audio['semantic_adjust']['tone_factor']:.2f}")
        if audio.get("duck_keyframes"):
            print(f"    Ducking关键帧: {len(audio['duck_keyframes'])}个")
        if audio.get("emotion_keyframes"):
            print(f"    情绪驱动关键帧: {len(audio['emotion_keyframes'])}个")

    # 生成报告
    report = mixer.generate_mix_report(result)
    print(f"\n{'=' * 60}")
    print("混音报告:")
    print(f"  总音频数: {report['total']}")
    print(f"  按类型: {report['by_type']}")
    print(f"  按优先级: {report['by_priority']}")
    print(f"  音量范围: {report['volume_range']['min']:.3f} - {report['volume_range']['max']:.3f}")
    print(f"  平均音量: {report['average_volume']:.3f}")
    print(f"  Ducking应用: {report['ducking_applied']}个")
    print(f"  语义调整: {report['semantic_adjusted']}个")
    print(f"  情绪关键帧总数: {report['emotion_keyframes']}")
    print(f"  淡入淡出: {report['has_fade']}个")
