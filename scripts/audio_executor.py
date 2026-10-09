"""
P25执行器: 音频合成
基于ffmpeg生成BGM/音效/环境音
"""

import os
import subprocess
import random
from typing import Dict, Any, List, Optional
import logging
logger = logging.getLogger(__name__)


try:
    from paths import FFMPEG
except ImportError:
    FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"


class AudioExecutor:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor", "director_engine_output", "audio"
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def _run_ffmpeg(self, args: list, output_file: str) -> bool:
        cmd = [FFMPEG, "-y", "-loglevel", "error"] + args + ["-i", output_file]
        # 修正：输出文件应该在最后，不需要-i
        cmd = [FFMPEG, "-y", "-loglevel", "error"] + args + [output_file]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and os.path.exists(output_file):
                return True
            else:
                logger.info(f"  ⚠️  ffmpeg失败: {result.stderr[:100]}")
                return False
        except Exception as e:
            logger.info(f"  ⚠️  ffmpeg异常: {e}")
            return False

    def generate_hit(self, output_file: str = None, duration: float = 0.3) -> Optional[str]:
        """击打声：短促噪声爆发+低频冲击"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"hit_{int(duration*1000)}ms.mp3")
        # 使用anoisesrc生成噪声，加上低通滤波和包络
        args = [
            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=pink:r=44100",
            "-af", f"lowpass=f=800,volume=3,afade=t=out:st={duration*0.5}:d={duration*0.5}",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 击打声: {duration}s")
            return output_file
        return None

    def generate_whoosh(self, output_file: str = None, duration: float = 0.5) -> Optional[str]:
        """挥拳声：快速频率扫描"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"whoosh_{int(duration*1000)}ms.mp3")
        # 使用sine生成频率扫描
        args = [
            "-f", "lavfi", "-i", f"sine=frequency=200:duration={duration}",
            "-af", f"asetrate=44100*2,aresample=44100,afade=t=in:st=0:d={duration*0.3},afade=t=out:st={duration*0.5}:d={duration*0.5},volume=2",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 挥拳声: {duration}s")
            return output_file
        return None

    def generate_footstep(self, output_file: str = None, duration: float = 0.2) -> Optional[str]:
        """脚步声：短促低频噪声"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"footstep_{int(duration*1000)}ms.mp3")
        args = [
            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=brown:r=44100",
            "-af", f"lowpass=f=300,volume=4,afade=t=out:st={duration*0.3}:d={duration*0.7}",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 脚步声: {duration}s")
            return output_file
        return None

    def generate_flash_sound(self, output_file: str = None, duration: float = 0.15) -> Optional[str]:
        """闪白音效：短促高频噪声"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"flash_{int(duration*1000)}ms.mp3")
        args = [
            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=white:r=44100",
            "-af", f"highpass=f=2000,volume=2,afade=t=out:st={duration*0.3}:d={duration*0.7}",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 闪白音效: {duration}s")
            return output_file
        return None

    def generate_ambient(self, output_file: str = None, duration: float = 10.0,
                          ambient_type: str = "indoor") -> Optional[str]:
        """环境音：白噪声/粉噪声滤波"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"ambient_{ambient_type}_{int(duration)}s.mp3")
        noise_type = "pink" if ambient_type == "indoor" else "brown"
        low_freq = 500 if ambient_type == "indoor" else 300
        args = [
            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c={noise_type}:r=44100",
            "-af", f"lowpass=f={low_freq},volume=0.3",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 环境音({ambient_type}): {duration}s")
            return output_file
        return None

    def generate_bgm(self, output_file: str = None, duration: float = 30.0,
                     style: str = "neutral") -> Optional[str]:
        """BGM：简单的旋律循环（基于正弦波和弦）"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"bgm_{style}_{int(duration)}s.mp3")
        # 生成简单的和弦进行（C-G-Am-F）
        notes = [261.63, 392.00, 220.00, 349.23]  # C4, G4, A3, F4
        chord_duration = duration / len(notes)
        inputs = []
        filters = []
        for i, freq in enumerate(notes):
            inputs.extend(["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={chord_duration}"])
            filters.append(f"[{i}:a]volume=0.2,afade=t=in:st=0:d=0.5,afade=t=out:st={chord_duration-0.5}:d=0.5[a{i}]")
        filter_complex = ";".join(filters) + ";" + "".join([f"[a{i}]" for i in range(len(notes))]) + f"concat=n={len(notes)}:v=0:a=1[out]"
        args = inputs + ["-filter_complex", filter_complex, "-map", "[out]", "-ar", "44100", "-ac", "1"]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ BGM({style}): {duration}s")
            return output_file
        return None

    def generate_laugh(self, output_file: str = None, duration: float = 1.0) -> Optional[str]:
        """笑声：短促高频噪声脉冲（近似）"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"laugh_{int(duration*1000)}ms.mp3")
        args = [
            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=pink:r=44100",
            "-af", f"bandpass=f=500:width_type=h:w=200,volume=2,tremolo=f=8:d=0.8,afade=t=out:st={duration*0.7}:d={duration*0.3}",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 笑声: {duration}s")
            return output_file
        return None

    def generate_applause(self, output_file: str = None, duration: float = 2.0) -> Optional[str]:
        """掌声：密集白噪声脉冲"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"applause_{int(duration*1000)}ms.mp3")
        args = [
            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=white:r=44100",
            "-af", f"lowpass=f=4000,volume=1.5,tremolo=f=15:d=0.6,afade=t=in:st=0:d=0.3,afade=t=out:st={duration*0.7}:d={duration*0.3}",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 掌声: {duration}s")
            return output_file
        return None

    def generate_wind(self, output_file: str = None, duration: float = 3.0) -> Optional[str]:
        """风声：低频褐噪声+带通滤波"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"wind_{int(duration)}s.mp3")
        args = [
            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=brown:r=44100",
            "-af", f"bandpass=f=200:width_type=h:w=300,volume=2,afade=t=in:st=0:d=0.5,afade=t=out:st={duration-0.5}:d=0.5",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 风声: {duration}s")
            return output_file
        return None

    def generate_rain(self, output_file: str = None, duration: float = 3.0) -> Optional[str]:
        """雨声：高频白噪声+低通"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"rain_{int(duration)}s.mp3")
        args = [
            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=white:r=44100",
            "-af", f"lowpass=f=6000,volume=0.8,afade=t=in:st=0:d=0.5,afade=t=out:st={duration-0.5}:d=0.5",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 雨声: {duration}s")
            return output_file
        return None

    def generate_cheer(self, output_file: str = None, duration: float = 2.0) -> Optional[str]:
        """欢呼声：中频噪声+音量起伏"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"cheer_{int(duration*1000)}ms.mp3")
        args = [
            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=pink:r=44100",
            "-af", f"bandpass=f=800:width_type=h:w=600,volume=2,tremolo=f=4:d=0.4,afade=t=in:st=0:d=0.3,afade=t=out:st={duration*0.7}:d={duration*0.3}",
            "-ar", "44100", "-ac", "1"
        ]
        if self._run_ffmpeg(args, output_file):
            logger.info(f"  ✅ 欢呼声: {duration}s")
            return output_file
        return None

    # 音效类型映射
    SOUND_MAP = {
        "击打声": "hit",
        "挥拳声": "whoosh",
        "脚步声": "footstep",
        "闪白": "flash",
        "轻微室内音": "ambient_indoor",
        "通用BGM": "bgm",
        "餐厅嘈杂声": "ambient_indoor",
        "餐具碰撞": "hit",
        "笑声": "laugh",
        "掌声": "applause",
        "欢呼声": "cheer",
        "风声": "wind",
        "雨声": "rain",
        "环境音": "ambient_indoor",
        "BGM": "bgm",
    }

    def execute(self, audio_instructions: List[Dict]) -> Dict[str, Any]:
        logger.info(f"\n{'='*60}")
        logger.info(f"音频执行器: {len(audio_instructions)}条指令")
        logger.info(f"{'='*60}")
        results = []
        for i, instr in enumerate(audio_instructions):
            audio_type = instr.get("type", "")
            name = instr.get("name", "")
            duration = instr.get("duration", 1.0)
            volume = instr.get("volume", 1.0)
            output_file = os.path.join(self.output_dir, f"audio_{i:03d}_{name}.mp3")

            path = None
            sound_key = self.SOUND_MAP.get(name, "")
            if sound_key == "hit":
                path = self.generate_hit(output_file, duration)
            elif sound_key == "whoosh":
                path = self.generate_whoosh(output_file, duration)
            elif sound_key == "footstep":
                path = self.generate_footstep(output_file, duration)
            elif sound_key == "flash":
                path = self.generate_flash_sound(output_file, duration)
            elif sound_key == "ambient_indoor":
                path = self.generate_ambient(output_file, duration, "indoor")
            elif sound_key == "bgm":
                path = self.generate_bgm(output_file, duration, "neutral")
            elif sound_key == "laugh":
                path = self.generate_laugh(output_file, duration)
            elif sound_key == "applause":
                path = self.generate_applause(output_file, duration)
            elif sound_key == "cheer":
                path = self.generate_cheer(output_file, duration)
            elif sound_key == "wind":
                path = self.generate_wind(output_file, duration)
            elif sound_key == "rain":
                path = self.generate_rain(output_file, duration)
            else:
                # 默认生成短噪声
                path = self.generate_hit(output_file, min(duration, 0.5))

            results.append({
                "type": audio_type, "name": name, "duration": duration,
                "volume": volume, "output_path": path, "success": path is not None
            })

        success_count = sum(1 for r in results if r["success"])
        logger.info(f"\n  完成: {success_count}成功 / {len(results)-success_count}失败")
        return {
            "status": "success" if success_count == len(results) else "partial",
            "total": len(results), "success": success_count,
            "failed": len(results)-success_count, "output_dir": self.output_dir,
            "results": results
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    executor = AudioExecutor()
    test = [
        {"type": "sfx", "name": "击打声", "duration": 0.3, "volume": 1.0},
        {"type": "sfx", "name": "挥拳声", "duration": 0.5, "volume": 1.0},
        {"type": "sfx", "name": "脚步声", "duration": 0.2, "volume": 1.0},
        {"type": "ambient", "name": "轻微室内音", "duration": 5.0, "volume": 0.3},
    ]
    result = executor.execute(test)
    logger.info(f"结果: {result['status']}")
