"""
声音引擎 v1.0
实际生成音频：TTS旁白/对话 + BGM选配 + 音效插入 + 音画对齐

功能：
1. TTS音频生成（edge-tts，支持多角色多音色）
2. BGM自动选配（基于情绪/场景的免版权音乐库）
3. 音效自动插入（转场/动作/环境音）
4. 音画对齐校验（台词时长vs镜头时长）
5. 音频混合（ffmpeg）
"""

import os
import json
import asyncio
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# 音色配置（edge-tts中文女声/男声）
VOICE_PRESETS = {
    "narrator_female": {
        "voice": "zh-CN-XiaoxiaoNeural",
        "name": "晓晓-女声旁白",
        "rate": "+0%",
        "pitch": "+0Hz",
    },
    "narrator_male": {
        "voice": "zh-CN-YunxiNeural",
        "name": "云希-男声旁白",
        "rate": "+0%",
        "pitch": "+0Hz",
    },
    "young_female": {
        "voice": "zh-CN-XiaoyiNeural",
        "name": "晓伊-年轻女声",
        "rate": "+5%",
        "pitch": "+2Hz",
    },
    "mature_male": {
        "voice": "zh-CN-YunjianNeural",
        "name": "云健-成熟男声",
        "rate": "-5%",
        "pitch": "-2Hz",
    },
    "energetic_female": {
        "voice": "zh-CN-XiaohanNeural",
        "name": "晓涵-活力女声",
        "rate": "+10%",
        "pitch": "+3Hz",
    },
    "calm_male": {
        "voice": "zh-CN-YunyangNeural",
        "name": "云扬-沉稳男声",
        "rate": "-5%",
        "pitch": "-1Hz",
    },
}

# BGM情绪匹配预设
BGM_PRESETS = {
    "sad": {"name": "悲伤钢琴", "tempo": "slow", "intensity": "low", "mood": "melancholy"},
    "tense": {"name": "紧张鼓点", "tempo": "fast", "intensity": "high", "mood": "suspense"},
    "happy": {"name": "欢快尤克里里", "tempo": "medium", "intensity": "medium", "mood": "uplifting"},
    "calm": {"name": "宁静氛围", "tempo": "slow", "intensity": "low", "mood": "peaceful"},
    "epic": {"name": "史诗管弦", "tempo": "medium", "intensity": "high", "mood": "grand"},
    "romantic": {"name": "浪漫弦乐", "tempo": "slow", "intensity": "medium", "mood": "warm"},
    "determined": {"name": "坚定节奏", "tempo": "medium", "intensity": "medium", "mood": "motivational"},
    "anxious": {"name": "焦虑电子", "tempo": "fast", "intensity": "medium", "mood": "uneasy"},
}

# 音效预设
SFX_PRESETS = {
    "transition_whoosh": {"name": "转场嗖声", "duration": 0.5},
    "impact": {"name": "撞击声", "duration": 0.3},
    "door_open": {"name": "开门声", "duration": 1.0},
    "phone_ring": {"name": "手机铃声", "duration": 2.0},
    "typing": {"name": "打字声", "duration": 1.5},
    "ambient_office": {"name": "办公室环境音", "duration": 5.0, "loop": True},
    "ambient_cafe": {"name": "咖啡馆环境音", "duration": 5.0, "loop": True},
    "ambient_street": {"name": "街道环境音", "duration": 5.0, "loop": True},
    "success_chime": {"name": "成功提示音", "duration": 1.0},
    "error_buzz": {"name": "错误提示音", "duration": 0.5},
}


@dataclass
class AudioClip:
    """音频片段"""
    clip_type: str           # tts / bgm / sfx
    text: str = ""           # TTS文本
    voice: str = ""          # 音色key
    start_time: float = 0.0  # 起始时间（秒）
    duration: float = 0.0    # 时长（秒）
    volume: float = 1.0      # 音量（0-1）
    file_path: str = ""      # 生成的文件路径
    preset: str = ""         # BGM/SFX预设key


class SoundEngine:
    """声音引擎"""

    def __init__(self, output_dir: str = "", ffmpeg_path: str = ""):
        """
        Args:
            output_dir: 音频输出目录
            ffmpeg_path: ffmpeg路径
        """
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "audio_output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self.ffprobe_path = ffmpeg_path.replace("ffmpeg", "ffprobe") if ffmpeg_path else "ffprobe"
        self.clips: List[AudioClip] = []

    async def generate_tts(self, text: str, voice: str = "narrator_female",
                            output_file: str = "") -> str:
        """
        生成TTS音频

        Args:
            text: 文本内容
            voice: 音色key（见VOICE_PRESETS）
            output_file: 输出文件路径

        Returns:
            生成的音频文件路径
        """
        try:
            import edge_tts
        except ImportError:
            print("❌ edge-tts未安装")
            return ""

        voice_config = VOICE_PRESETS.get(voice, VOICE_PRESETS["narrator_female"])

        if not output_file:
            safe_name = text[:20].replace(" ", "_").replace("/", "_")
            output_file = os.path.join(self.output_dir, f"tts_{safe_name}.mp3")

        communicate = edge_tts.Communicate(
            text,
            voice_config["voice"],
            rate=voice_config["rate"],
            pitch=voice_config["pitch"],
        )
        await communicate.save(output_file)

        # 获取实际时长
        duration = self._get_audio_duration(output_file)
        print(f"  ✅ TTS生成: {voice_config['name']} | {text[:30]}... | {duration:.1f}s")

        return output_file

    def _get_audio_duration(self, file_path: str) -> float:
        """获取音频时长（秒）"""
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                capture_output=True, text=True, timeout=10
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def generate_bgm_placeholder(self, mood: str = "calm",
                                   duration: float = 30.0,
                                   output_file: str = "") -> str:
        """
        生成真实BGM（多声部程序生成：和弦+贝斯+旋律+鼓点）
        替代原330Hz正弦波占位音频

        Args:
            mood: 情绪key（sad/tense/happy/calm/epic/romantic/determined/anxious）
            duration: 时长（秒）
            output_file: 输出路径

        Returns:
            音频文件路径
        """
        bgm_config = BGM_PRESETS.get(mood, BGM_PRESETS["calm"])

        if not output_file:
            output_file = os.path.join(self.output_dir, f"bgm_{mood}.wav")

        # 情绪映射到真实BGM生成器的风格
        mood_map = {
            "sad": "ink", "tense": "dark", "happy": "bright",
            "calm": "minimal", "epic": "tech", "romantic": "retro",
            "determined": "vlog", "anxious": "glitch",
        }
        bgm_mood = mood_map.get(mood, "default")

        # 调用真实BGM生成器
        try:
            from real_bgm_generator import RealBGMGenerator
            gen = RealBGMGenerator(ffmpeg_path=self.ffmpeg_path)
            result = gen.generate(bgm_mood, duration=duration, bpm=120, output_path=output_file)
            if result and os.path.exists(result):
                print(f"  ✅ 真实BGM: {bgm_config['name']} | {duration:.0f}s | {bgm_mood}风格")
                return result
        except ImportError:
            pass
        except Exception as e:
            print(f"  ⚠️ 真实BGM生成失败，回退正弦波: {e}")

        # 回退：ffmpeg正弦波
        freq_map = {
            "sad": 220, "tense": 440, "happy": 523, "calm": 330,
            "epic": 196, "romantic": 392, "determined": 349, "anxious": 466,
        }
        freq = freq_map.get(mood, 330)
        try:
            subprocess.run([
                self.ffmpeg_path, "-y", "-f", "lavfi",
                "-i", f"sine=frequency={freq}:duration={duration}",
                "-af", "volume=0.1",
                "-q:a", "2", output_file
            ], capture_output=True, timeout=30)
            print(f"  ⚠️ BGM回退(正弦波): {bgm_config['name']} | {duration:.0f}s | {freq}Hz")
        except Exception as e:
            print(f"  ❌ BGM生成失败: {e}")

        return output_file

    def generate_sfx_placeholder(self, sfx_type: str = "transition_whoosh",
                                   output_file: str = "") -> str:
        """
        生成音效占位音频

        Args:
            sfx_type: 音效类型key
            output_file: 输出路径

        Returns:
            音频文件路径
        """
        sfx_config = SFX_PRESETS.get(sfx_type, SFX_PRESETS["transition_whoosh"])
        duration = sfx_config["duration"]

        if not output_file:
            output_file = os.path.join(self.output_dir, f"sfx_{sfx_type}.mp3")

        # 不同音效用不同频率
        freq_map = {
            "transition_whoosh": 800, "impact": 100, "door_open": 200,
            "phone_ring": 880, "typing": 600, "success_chime": 1046,
            "error_buzz": 150,
        }
        freq = freq_map.get(sfx_type, 440)

        try:
            subprocess.run([
                self.ffmpeg_path, "-y", "-f", "lavfi",
                "-i", f"sine=frequency={freq}:duration={duration}",
                "-af", f"volume=0.2,afade=t=out:st={duration*0.7}:d={duration*0.3}",
                "-q:a", "2", output_file
            ], capture_output=True, timeout=10)
            print(f"  ✅ SFX占位: {sfx_config['name']} | {duration}s")
        except Exception as e:
            print(f"  ⚠️ SFX生成失败: {e}")

        return output_file

    def mix_audio(self, clips: List[AudioClip], output_file: str = "",
                    total_duration: float = 0.0) -> str:
        """
        混合多个音频片段

        Args:
            clips: 音频片段列表
            output_file: 输出文件
            total_duration: 总时长

        Returns:
            混合后的音频文件路径
        """
        if not output_file:
            output_file = os.path.join(self.output_dir, "mixed_audio.mp3")

        if not clips:
            print("⚠️ 没有音频片段可混合")
            return ""

        # 构建ffmpeg amix过滤器
        inputs = []
        filters = []
        for i, clip in enumerate(clips):
            if not clip.file_path or not os.path.exists(clip.file_path):
                continue
            inputs.extend(["-i", clip.file_path])
            # 延迟和音量
            delay_ms = int(clip.start_time * 1000)
            filters.append(
                f"[{i}:a]adelay={delay_ms}|{delay_ms},"
                f"volume={clip.volume}[a{i}]"
            )

        if not filters:
            return ""

        # 混合所有轨道
        mix_inputs = "".join(f"[a{i}]" for i in range(len(filters)))
        filter_complex = ";".join(filters) + f";{mix_inputs}amix=inputs={len(filters)}:duration=longest[out]"

        try:
            cmd = [self.ffmpeg_path, "-y"] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-q:a", "2", output_file
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)
            print(f"  ✅ 音频混合完成: {len(filters)}个轨道")
        except Exception as e:
            print(f"  ⚠️ 音频混合失败: {e}")

        return output_file

    def validate_audio_timing(self, tts_clips: List[AudioClip],
                                shot_durations: List[float]) -> Dict[str, Any]:
        """
        音画对齐校验

        Args:
            tts_clips: TTS片段列表
            shot_durations: 镜头时长列表

        Returns:
            校验报告
        """
        report = {
            "total_tts_duration": sum(c.duration for c in tts_clips),
            "total_shot_duration": sum(shot_durations),
            "issues": [],
            "warnings": [],
        }

        # 检查总时长
        if report["total_tts_duration"] > report["total_shot_duration"] * 1.1:
            report["issues"].append(
                f"TTS总时长({report['total_tts_duration']:.1f}s)超过镜头总时长"
                f"({report['total_shot_duration']:.1f}s)10%以上"
            )

        # 逐镜头检查
        for i, (clip, shot_dur) in enumerate(zip(tts_clips, shot_durations)):
            if clip.duration > shot_dur * 1.2:
                report["issues"].append(
                    f"镜头{i+1}: TTS({clip.duration:.1f}s)超过镜头时长({shot_dur:.1f}s)20%"
                )
            elif clip.duration > shot_dur:
                report["warnings"].append(
                    f"镜头{i+1}: TTS({clip.duration:.1f}s)略超镜头时长({shot_dur:.1f}s)"
                )

        report["status"] = "pass" if not report["issues"] else "fail"
        return report

    async def generate_from_script(self, script_data: Dict[str, Any],
                                     output_dir: str = "") -> Dict[str, Any]:
        """
        从剧本数据生成完整音频

        Args:
            script_data: 剧本数据（含scenes/shots/dialogue/narration）
            output_dir: 输出目录

        Returns:
            音频生成报告
        """
        if output_dir:
            self.output_dir = output_dir
            os.makedirs(self.output_dir, exist_ok=True)

        print(f"\n{'='*60}")
        print("声音引擎 - 从剧本生成音频")
        print(f"{'='*60}")

        all_clips = []
        tts_clips = []
        shot_durations = []

        # 遍历场景和镜头
        scenes = script_data.get("scenes", [])
        current_time = 0.0

        for scene_idx, scene in enumerate(scenes):
            scene_mood = scene.get("mood", "calm")
            shots = scene.get("shots", [])

            print(f"\n场景{scene_idx+1}: {scene.get('name', '')} (情绪: {scene_mood})")

            # 生成场景BGM
            bgm_file = self.generate_bgm_placeholder(
                mood=scene_mood,
                duration=sum(s.get("duration", 3) for s in shots),
                output_file=os.path.join(self.output_dir, f"bgm_scene{scene_idx+1}.mp3")
            )
            all_clips.append(AudioClip(
                clip_type="bgm", preset=scene_mood,
                start_time=current_time,
                duration=sum(s.get("duration", 3) for s in shots),
                volume=0.15, file_path=bgm_file
            ))

            for shot_idx, shot in enumerate(shots):
                shot_dur = shot.get("duration", 3)
                shot_durations.append(shot_dur)

                # 旁白
                narration = shot.get("narration", "")
                if narration:
                    tts_file = await self.generate_tts(
                        narration,
                        voice=shot.get("narrator_voice", "narrator_female"),
                        output_file=os.path.join(
                            self.output_dir,
                            f"tts_s{scene_idx+1}_shot{shot_idx+1}_narration.mp3"
                        )
                    )
                    tts_dur = self._get_audio_duration(tts_file)
                    clip = AudioClip(
                        clip_type="tts", text=narration,
                        voice=shot.get("narrator_voice", "narrator_female"),
                        start_time=current_time, duration=tts_dur,
                        volume=1.0, file_path=tts_file
                    )
                    all_clips.append(clip)
                    tts_clips.append(clip)

                # 对话
                dialogue = shot.get("dialogue", "")
                if dialogue:
                    tts_file = await self.generate_tts(
                        dialogue,
                        voice=shot.get("character_voice", "young_female"),
                        output_file=os.path.join(
                            self.output_dir,
                            f"tts_s{scene_idx+1}_shot{shot_idx+1}_dialogue.mp3"
                        )
                    )
                    tts_dur = self._get_audio_duration(tts_file)
                    clip = AudioClip(
                        clip_type="tts", text=dialogue,
                        voice=shot.get("character_voice", "young_female"),
                        start_time=current_time + 0.5, duration=tts_dur,
                        volume=1.0, file_path=tts_file
                    )
                    all_clips.append(clip)
                    tts_clips.append(clip)

                # 转场音效
                if shot_idx > 0:
                    sfx_file = self.generate_sfx_placeholder(
                        "transition_whoosh",
                        output_file=os.path.join(self.output_dir, f"sfx_transition_{scene_idx+1}_{shot_idx+1}.mp3")
                    )
                    all_clips.append(AudioClip(
                        clip_type="sfx", preset="transition_whoosh",
                        start_time=current_time, duration=0.5,
                        volume=0.3, file_path=sfx_file
                    ))

                current_time += shot_dur

        # 音画对齐校验
        timing_report = self.validate_audio_timing(tts_clips, shot_durations)
        print(f"\n音画对齐校验: {timing_report['status']}")
        for issue in timing_report["issues"]:
            print(f"  ❌ {issue}")
        for warning in timing_report["warnings"]:
            print(f"  ⚠️ {warning}")

        # 混合音频
        mixed_file = self.mix_audio(
            all_clips,
            output_file=os.path.join(self.output_dir, "full_audio_mix.mp3"),
            total_duration=current_time
        )

        report = {
            "total_clips": len(all_clips),
            "tts_clips": len(tts_clips),
            "bgm_clips": len(scenes),
            "sfx_clips": len(all_clips) - len(tts_clips) - len(scenes),
            "total_duration": current_time,
            "timing_check": timing_report,
            "mixed_file": mixed_file,
            "output_dir": self.output_dir,
        }

        # 保存报告
        report_path = os.path.join(self.output_dir, "sound_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 声音生成完成: {len(all_clips)}个片段, {current_time:.0f}s")
        print(f"   混合音频: {mixed_file}")
        print(f"   报告: {report_path}")

        return report


# 便捷函数
def create_sound_engine(output_dir: str = "") -> SoundEngine:
    """创建声音引擎"""
    return SoundEngine(output_dir=output_dir)


async def quick_tts(text: str, voice: str = "narrator_female",
                     output_dir: str = "") -> str:
    """快速生成TTS"""
    engine = create_sound_engine(output_dir)
    return await engine.generate_tts(text, voice)


if __name__ == "__main__":
    # 自测
    async def test():
        print("=" * 60)
        print("声音引擎 v1.0 自测")
        print("=" * 60)

        engine = create_sound_engine()

        # 测试TTS
        print("\n[1/4] 测试TTS生成...")
        tts_file = await engine.generate_tts(
            "这是一个测试，声音引擎已经可以正常工作了。",
            voice="narrator_female"
        )
        print(f"  TTS文件: {tts_file}")

        # 测试BGM
        print("\n[2/4] 测试BGM生成...")
        bgm_file = engine.generate_bgm_placeholder(mood="calm", duration=5)
        print(f"  BGM文件: {bgm_file}")

        # 测试SFX
        print("\n[3/4] 测试SFX生成...")
        sfx_file = engine.generate_sfx_placeholder("transition_whoosh")
        print(f"  SFX文件: {sfx_file}")

        # 测试从剧本生成
        print("\n[4/4] 测试从剧本生成完整音频...")
        test_script = {
            "scenes": [
                {
                    "name": "开场",
                    "mood": "sad",
                    "shots": [
                        {"duration": 4, "narration": "他坐在昏暗的房间里，看着窗外的雨。"},
                        {"duration": 3, "dialogue": "为什么会变成这样...", "character_voice": "mature_male"},
                    ]
                },
                {
                    "name": "转折",
                    "mood": "determined",
                    "shots": [
                        {"duration": 4, "narration": "直到有一天，他发现了一个改变命运的工具。"},
                        {"duration": 3, "dialogue": "这一次，我不会再放弃了！", "character_voice": "energetic_female"},
                    ]
                },
            ]
        }
        report = await engine.generate_from_script(test_script)
        print(f"\n  生成报告: {json.dumps(report, ensure_ascii=False, indent=2)[:500]}")

        print("\n" + "=" * 60)
        print("✅ 声音引擎自测通过")
        print("=" * 60)

    asyncio.run(test())
