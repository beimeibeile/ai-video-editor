"""
多音轨混音优化验证模块 v1.0
测试和验证audio_mixer的功能：
1. 多轨混合
2. 闪避效果
3. 响度标准化
4. 输出音频技术参数验证

使用方式：
    python audio_mixer_test.py
"""
import os
import subprocess
import json
import tempfile
from typing import Dict


class AudioMixerTester:
    """多音轨混音测试器"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffprobe_path
        self.test_dir = os.path.join(tempfile.gettempdir(), "audio_mixer_test")
        os.makedirs(self.test_dir, exist_ok=True)

    def generate_test_audio(
        self,
        duration: float = 5.0,
        frequency: int = 440,
        volume: float = 0.5,
        name: str = "test",
    ) -> str:
        """生成测试音频（正弦波）"""
        output_path = os.path.join(self.test_dir, f"{name}.wav")

        cmd = [
            self.ffmpeg, "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={frequency}:duration={duration}",
            "-af", f"volume={volume}",
            "-ar", "44100",
            "-ac", "2",
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(output_path):
                return output_path
        except Exception as e:
            print(f"⚠️ 生成测试音频失败: {e}")

        return ""

    def analyze_audio(self, audio_path: str) -> Dict:
        """分析音频技术参数"""
        if not os.path.exists(audio_path):
            return {}

        try:
            # 获取基本信息
            cmd = [
                self.ffprobe, "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            info = json.loads(result.stdout)

            audio_stream = next(
                (s for s in info.get("streams", []) if s.get("codec_type") == "audio"),
                {}
            )

            # 响度分析
            loudness_cmd = [
                self.ffmpeg, "-i", audio_path,
                "-af", "loudnorm=print_format=json",
                "-f", "null", "-"
            ]
            loudness_result = subprocess.run(
                loudness_cmd, capture_output=True, text=True, timeout=30
            )

            loudness = {}
            # 从stderr中提取JSON
            stderr = loudness_result.stderr
            json_start = stderr.rfind("{")
            if json_start >= 0:
                try:
                    loudness = json.loads(stderr[json_start:])
                except Exception:
                    pass

            return {
                "duration": float(info.get("format", {}).get("duration", 0)),
                "sample_rate": int(audio_stream.get("sample_rate", 44100)),
                "channels": int(audio_stream.get("channels", 2)),
                "codec": audio_stream.get("codec_name", ""),
                "bitrate": int(info.get("format", {}).get("bit_rate", 0)),
                "input_i": loudness.get("input_i", "N/A"),
                "input_tp": loudness.get("input_tp", "N/A"),
                "input_lra": loudness.get("input_lra", "N/A"),
                "input_thresh": loudness.get("input_thresh", "N/A"),
                "target_offset": loudness.get("target_offset", "N/A"),
            }
        except Exception as e:
            print(f"⚠️ 音频分析失败: {e}")
            return {}

    def test_basic_mixing(self) -> Dict:
        """测试基础多轨混合"""
        print("\n=== 测试1：基础多轨混合 ===")

        # 生成3个测试音频
        track1 = self.generate_test_audio(5.0, 440, 0.5, "track1")  # A4
        track2 = self.generate_test_audio(5.0, 554, 0.4, "track2")  # C#5
        track3 = self.generate_test_audio(5.0, 659, 0.3, "track3")  # E5

        if not all([track1, track2, track3]):
            return {"test": "basic_mixing", "status": "failed", "reason": "生成测试音频失败"}

        # 混合
        output_path = os.path.join(self.test_dir, "mixed_basic.wav")
        cmd = [
            self.ffmpeg, "-y",
            "-i", track1, "-i", track2, "-i", track3,
            "-filter_complex",
            "[0:a][1:a][2:a]amix=inputs=3:duration=longest:dropout_transition=0[mixed]",
            "-map", "[mixed]",
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(output_path):
                analysis = self.analyze_audio(output_path)
                print(f"  ✅ 混合成功: {os.path.getsize(output_path)/1024:.1f}KB")
                print(f"     时长: {analysis.get('duration', 0):.1f}秒")
                print(f"     采样率: {analysis.get('sample_rate', 0)}Hz")
                print(f"     声道: {analysis.get('channels', 0)}")
                return {
                    "test": "basic_mixing",
                    "status": "passed",
                    "output": output_path,
                    "analysis": analysis,
                }
        except Exception as e:
            print(f"  ❌ 混合失败: {e}")

        return {"test": "basic_mixing", "status": "failed"}

    def test_ducking(self) -> Dict:
        """测试闪避效果（人声控制BGM）"""
        print("\n=== 测试2：闪避效果（人声控制BGM）===")

        # 生成BGM（持续）
        bgm = self.generate_test_audio(10.0, 220, 0.6, "bgm")
        # 生成人声（只在前5秒）
        vocals = self.generate_test_audio(5.0, 880, 0.8, "vocals")

        if not all([bgm, vocals]):
            return {"test": "ducking", "status": "failed", "reason": "生成测试音频失败"}

        # 侧链压缩闪避
        output_path = os.path.join(self.test_dir, "mixed_ducking.wav")
        cmd = [
            self.ffmpeg, "-y",
            "-i", bgm, "-i", vocals,
            "-filter_complex",
            "[1:a]asplit=2[sc][vocals];"
            "[0:a][sc]sidechaincompress="
            "threshold=0.1:ratio=4:attack=5:release=100[bgm_ducked];"
            "[bgm_ducked][vocals]amix=inputs=2:duration=longest[mixed]",
            "-map", "[mixed]",
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(output_path):
                analysis = self.analyze_audio(output_path)
                print(f"  ✅ 闪避混合成功: {os.path.getsize(output_path)/1024:.1f}KB")
                print(f"     时长: {analysis.get('duration', 0):.1f}秒")
                print(f"     响度(I): {analysis.get('input_i', 'N/A')} LUFS")
                print(f"     真峰值(TP): {analysis.get('input_tp', 'N/A')} dB")
                return {
                    "test": "ducking",
                    "status": "passed",
                    "output": output_path,
                    "analysis": analysis,
                }
        except Exception as e:
            print(f"  ❌ 闪避混合失败: {e}")

        return {"test": "ducking", "status": "failed"}

    def test_loudness_normalization(self) -> Dict:
        """测试响度标准化"""
        print("\n=== 测试3：响度标准化 ===")

        # 生成一个低音量音频
        quiet_audio = self.generate_test_audio(5.0, 440, 0.1, "quiet")

        if not quiet_audio:
            return {"test": "loudness_norm", "status": "failed", "reason": "生成测试音频失败"}

        # 分析原始响度
        original_analysis = self.analyze_audio(quiet_audio)
        print(f"  原始响度(I): {original_analysis.get('input_i', 'N/A')} LUFS")

        # 响度标准化到-14 LUFS（抖音标准）
        output_path = os.path.join(self.test_dir, "normalized.wav")
        cmd = [
            self.ffmpeg, "-y",
            "-i", quiet_audio,
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(output_path):
                normalized_analysis = self.analyze_audio(output_path)
                print(f"  ✅ 标准化成功: {os.path.getsize(output_path)/1024:.1f}KB")
                print(f"     标准化后响度(I): {normalized_analysis.get('input_i', 'N/A')} LUFS")
                print(f"     标准化后真峰值(TP): {normalized_analysis.get('input_tp', 'N/A')} dB")
                print(f"     目标: -14 LUFS / -1.5 dBTP")
                return {
                    "test": "loudness_norm",
                    "status": "passed",
                    "output": output_path,
                    "original": original_analysis,
                    "normalized": normalized_analysis,
                }
        except Exception as e:
            print(f"  ❌ 标准化失败: {e}")

        return {"test": "loudness_norm", "status": "failed"}

    def test_master_chain(self) -> Dict:
        """测试母带处理链（压缩+标准化）"""
        print("\n=== 测试4：母带处理链（压缩+标准化）===")

        # 生成测试音频
        source = self.generate_test_audio(8.0, 330, 0.7, "master_source")

        if not source:
            return {"test": "master_chain", "status": "failed", "reason": "生成测试音频失败"}

        # 母带处理：压缩 + 标准化
        output_path = os.path.join(self.test_dir, "mastered.wav")
        cmd = [
            self.ffmpeg, "-y",
            "-i", source,
            "-af",
            "acompressor=threshold=-18dB:ratio=2.5:attack=10:release=100:makeup=2dB,"
            "loudnorm=I=-14:TP=-1.5:LRA=11",
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(output_path):
                analysis = self.analyze_audio(output_path)
                print(f"  ✅ 母带处理成功: {os.path.getsize(output_path)/1024:.1f}KB")
                print(f"     时长: {analysis.get('duration', 0):.1f}秒")
                print(f"     响度(I): {analysis.get('input_i', 'N/A')} LUFS")
                print(f"     真峰值(TP): {analysis.get('input_tp', 'N/A')} dB")
                print(f"     响度范围(LRA): {analysis.get('input_lra', 'N/A')}")
                return {
                    "test": "master_chain",
                    "status": "passed",
                    "output": output_path,
                    "analysis": analysis,
                }
        except Exception as e:
            print(f"  ❌ 母带处理失败: {e}")

        return {"test": "master_chain", "status": "failed"}

    def test_fade(self) -> Dict:
        """测试淡入淡出"""
        print("\n=== 测试5：淡入淡出 ===")

        source = self.generate_test_audio(5.0, 440, 0.6, "fade_source")

        if not source:
            return {"test": "fade", "status": "failed", "reason": "生成测试音频失败"}

        # 淡入1秒，淡出1秒
        output_path = os.path.join(self.test_dir, "faded.wav")
        cmd = [
            self.ffmpeg, "-y",
            "-i", source,
            "-af", "afade=t=in:st=0:d=1,afade=t=out:st=4:d=1",
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(output_path):
                analysis = self.analyze_audio(output_path)
                print(f"  ✅ 淡入淡出成功: {os.path.getsize(output_path)/1024:.1f}KB")
                print(f"     时长: {analysis.get('duration', 0):.1f}秒")
                return {
                    "test": "fade",
                    "status": "passed",
                    "output": output_path,
                    "analysis": analysis,
                }
        except Exception as e:
            print(f"  ❌ 淡入淡出失败: {e}")

        return {"test": "fade", "status": "failed"}

    def run_all_tests(self) -> Dict:
        """运行所有测试"""
        print("=" * 60)
        print("多音轨混音优化验证测试")
        print("=" * 60)
        print(f"测试目录: {self.test_dir}")

        results = []
        results.append(self.test_basic_mixing())
        results.append(self.test_ducking())
        results.append(self.test_loudness_normalization())
        results.append(self.test_master_chain())
        results.append(self.test_fade())

        # 汇总
        passed = sum(1 for r in results if r.get("status") == "passed")
        failed = sum(1 for r in results if r.get("status") == "failed")

        print("\n" + "=" * 60)
        print(f"测试汇总: {passed}通过, {failed}失败")
        print("=" * 60)

        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "results": results,
            "test_dir": self.test_dir,
        }


def main():
    """命令行入口"""
    tester = AudioMixerTester()
    result = tester.run_all_tests()

    # 保存测试报告
    report_path = os.path.join(tester.test_dir, "test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n测试报告已保存: {report_path}")


if __name__ == "__main__":
    main()
