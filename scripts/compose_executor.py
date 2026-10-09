"""
P25执行器: 最终合成
收集TTS/音频/文字/素材执行器的输出，合成到一个剪映工程中
"""

import os
import sys
import json
import subprocess
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


RUNTIME_DIR = r"D:\DobaoWork_Project\Ai_Video_Editor\ai-video-editor-runtime\scripts"
sys.path.insert(0, RUNTIME_DIR)

try:
    from paths import FFPROBE
except ImportError:
    FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"


def get_audio_duration(audio_path: str) -> float:
    """用ffprobe获取音频实际时长（秒）"""
    if not os.path.exists(audio_path):
        return 3.0
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_format", audio_path],
            capture_output=True, text=True, timeout=10
        )
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 3.0))
    except Exception:
        return 3.0


class ComposeExecutor:
    def __init__(self, work_dir: str = None):
        self.work_dir = work_dir or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor", "director_engine_output"
        )
        self.tts_dir = os.path.join(self.work_dir, "tts")
        self.audio_dir = os.path.join(self.work_dir, "audio")
        self.text_dir = os.path.join(self.work_dir, "text")
        self.asset_dir = os.path.join(self.work_dir, "assets")

    def collect_tts_files(self, tts_results: List[Dict] = None) -> List[Dict]:
        """收集TTS语音文件"""
        audio_files = []
        if tts_results:
            for i, result in enumerate(tts_results):
                path = result.get("output_path", "")
                if path and os.path.exists(path):
                    audio_files.append({
                        "path": path,
                        "start_time": result.get("start_time", i * 3),
                        "duration": result.get("duration", 3),
                        "track_name": "TTS",
                        "volume": 1.0,
                    })
        else:
            # 从目录扫描
            if os.path.exists(self.tts_dir):
                for i, f in enumerate(sorted(os.listdir(self.tts_dir))):
                    if f.endswith(".mp3"):
                        audio_files.append({
                            "path": os.path.join(self.tts_dir, f),
                            "start_time": i * 3,
                            "duration": 3,
                            "track_name": "TTS",
                            "volume": 1.0,
                        })
        return audio_files

    def collect_audio_files(self, audio_results: List[Dict] = None) -> List[Dict]:
        """收集音频文件（BGM/音效/环境音）"""
        audio_files = []
        if audio_results:
            for result in audio_results:
                path = result.get("output_path", "")
                if path and os.path.exists(path):
                    audio_type = result.get("type", "sfx")
                    track_map = {"bgm": "BGM", "ambient": "Ambient", "sfx": "SFX"}
                    audio_files.append({
                        "path": path,
                        "start_time": result.get("start_time", 0),
                        "duration": result.get("duration", 5),
                        "track_name": track_map.get(audio_type, "SFX"),
                        "volume": result.get("volume", 0.4 if audio_type == "bgm" else (0.3 if audio_type == "ambient" else 0.85)),
                    })
        else:
            # 从目录扫描
            if os.path.exists(self.audio_dir):
                for i, f in enumerate(sorted(os.listdir(self.audio_dir))):
                    if f.endswith(".mp3"):
                        track = "BGM" if "bgm" in f.lower() else ("Ambient" if "ambient" in f.lower() else "SFX")
                        audio_files.append({
                            "path": os.path.join(self.audio_dir, f),
                            "start_time": 0,
                            "duration": 5,
                            "track_name": track,
                            "volume": 0.4 if track == "BGM" else (0.3 if track == "Ambient" else 0.85),
                        })
        return audio_files

    def collect_sfx_files(self, sfx_results: List[Dict] = None) -> List[Dict]:
        """收集音效文件（SFX）"""
        sfx_files = []
        if sfx_results:
            for result in sfx_results:
                path = result.get("sfx_path", "")
                if path and os.path.exists(path):
                    sfx_files.append({
                        "path": path,
                        "start_time": result.get("start_time", 0),
                        "duration": result.get("duration", 1.0),
                        "track_name": "SFX",
                        "volume": result.get("volume", 0.85),
                        "name": result.get("name", ""),
                        "rating": result.get("rating", "C"),
                    })
        return sfx_files

    def execute(self, instruction_sequence: Dict[str, Any],
                project_name: str = "最终合成",
                width: int = 1080, height: int = 1920,
                duration: float = 20.0,
                tts_results: List[Dict] = None,
                audio_results: List[Dict] = None,
                sfx_results: List[Dict] = None,
                asset_results: List[Dict] = None,
                text_results: List[Dict] = None,
                deep_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行最终合成

        Args:
            instruction_sequence: P24输出的指令序列
            project_name: 工程名
            width/height: 画布尺寸
            duration: 总时长
            tts_results: TTS执行器的输出结果
            audio_results: 音频执行器的输出结果
            sfx_results: 音效执行器的输出结果
            asset_results: 素材生成执行器的输出结果
            text_results: 文字执行器的输出结果
            deep_analysis: P23深度语义分析结果（用于智能混音）

        Returns:
            合成结果
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"最终合成执行器: {project_name}")
        logger.info(f"{'='*60}")

        try:
            from jianying_executor import JianyingExecutor
            from audio_mixer import AudioMixer

            # 1. 收集所有音频文件
            logger.info(f"\n[1/4] 收集音频文件...")
            all_audio = []
            tts_files = self.collect_tts_files(tts_results)
            audio_files = self.collect_audio_files(audio_results)
            sfx_files = self.collect_sfx_files(sfx_results)

            # 关键修复：用instruction_sequence中的TTS指令修正时间轴
            # TTS执行器结果可能不含start_time，必须从指令序列获取
            tts_instructions = instruction_sequence.get("tts_instructions", [])
            if tts_instructions and len(tts_files) == len(tts_instructions):
                for i, tts_file in enumerate(tts_files):
                    instr = tts_instructions[i]
                    tts_file["start_time"] = instr.get("start_time", i * 3)
                    # 用ffprobe获取实际音频时长，避免截断
                    actual_dur = get_audio_duration(tts_file["path"])
                    tts_file["duration"] = actual_dur
                    tts_file["character"] = instr.get("character", "")
                    tts_file["text"] = instr.get("text", "")
                    # 同步文字字幕duration到TTS实际时长
                    text_instrs = instruction_sequence.get("text_instructions", [])
                    if i < len(text_instrs):
                        text_instrs[i]["duration"] = actual_dur
                logger.info(f"  ✅ TTS时间轴已同步，实际时长已ffprobe探测，文字duration已同步 ({len(tts_files)}条)")
            elif tts_instructions:
                logger.info(f"  ⚠️  TTS文件数({len(tts_files)})与指令数({len(tts_instructions)})不匹配，使用默认时间轴")

            all_audio.extend(tts_files)
            all_audio.extend(audio_files)
            all_audio.extend(sfx_files)
            logger.info(f"  ✅ TTS: {len(tts_files)}条, 音频: {len(audio_files)}条, 音效: {len(sfx_files)}条, 总计: {len(all_audio)}条")

            # 计算实际总时长（覆盖所有音频和文字的结束时间）
            max_end = duration
            for a in all_audio:
                end = a.get("start_time", 0) + a.get("duration", 3)
                if end > max_end:
                    max_end = end
            for t in instruction_sequence.get("text_instructions", []):
                end = t.get("start_time", 0) + t.get("duration", 3)
                if end > max_end:
                    max_end = end
            if max_end > duration:
                logger.info(f"  📐 实际总时长: {max_end:.1f}s (原参数: {duration:.1f}s)")
                duration = max_end

            # 2. 多音轨混音（音量平衡+淡入淡出+ducking）
            logger.info(f"\n[2/4] 多音轨混音...")
            mixer = AudioMixer(ducking_enabled=True, normalize_enabled=True)

            # 构建TTS片段列表（用于ducking）
            tts_segments = []
            for tts in tts_files:
                tts_segments.append({
                    "start_time": tts.get("start_time", 0),
                    "duration": tts.get("duration", 3),
                })

            mixed_audio = mixer.mix(
                audio_files=all_audio,
                tts_segments=tts_segments,
                total_duration=duration,
                deep_analysis=deep_analysis,
            )

            # 生成混音报告
            mix_report = mixer.generate_mix_report(mixed_audio)
            logger.info(f"  ✅ 混音完成: {mix_report['by_type']}")
            logger.info(f"  🎚️  Ducking应用: {mix_report['ducking_applied']}个音频")
            logger.info(f"  📊 音量范围: {mix_report['volume_range']['min']:.2f} - {mix_report['volume_range']['max']:.2f}")

            # 3. 调用剪映执行器构建工程（包含混音后的音频和生成的素材）
            logger.info(f"\n[3/4] 构建剪映工程（含混音音频）...")
            executor = JianyingExecutor(work_dir=self.work_dir)
            result = executor.execute(
                instruction_sequence=instruction_sequence,
                project_name=project_name,
                width=width,
                height=height,
                duration=duration,
                audio_files=mixed_audio,
                asset_results=asset_results,
            )

            # 4. 汇总结果
            logger.info(f"\n[4/4] 合成完成")
            logger.info(f"  ✅ 工程: {result.get('project_name')}")
            logger.info(f"  ✅ 草稿: {result.get('draft_path')}")
            logger.info(f"  ✅ 角色: {len(result.get('characters', []))}个")
            logger.info(f"  ✅ 关键帧: {result.get('keyframes_applied', 0)}条")
            logger.info(f"  ✅ 文字: {result.get('texts_added', 0)}条")
            logger.info(f"  ✅ 特效: {result.get('effects_applied', 0)}个")
            logger.info(f"  ✅ 音频: {result.get('audio_added', 0)}条")

            return {
                "status": "success",
                "draft_path": result.get("draft_path"),
                "project_name": project_name,
                "tts_count": len(tts_files),
                "audio_count": len(audio_files),
                "total_audio": len(all_audio),
                "characters": result.get("characters", []),
                "keyframes": result.get("keyframes_applied", 0),
                "texts": result.get("texts_added", 0),
                "effects": result.get("effects_applied", 0),
                "audio_added": result.get("audio_added", 0),
                "mix_report": mix_report,
            }

        except Exception as e:
            logger.info(f"\n❌ 最终合成失败: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    executor = ComposeExecutor()
    logger.info("最终合成执行器已加载")
    logger.info(f"工作目录: {executor.work_dir}")
