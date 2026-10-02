"""
真实BGM程序生成器 v1.0
多声部音乐生成：和弦进行 + 贝斯 + 旋律 + 节奏包络
替代330Hz正弦波占位音频

支持情绪：cyberpunk/retro/vlog/tech/dark/bright/minimal/ink/glitch/default
"""

import os
import sys
import subprocess
import tempfile
import numpy as np
from typing import Dict, List, Optional, Tuple

# 音符频率（A4=440Hz）
NOTE_FREQS = {
    "C2": 65.41, "D2": 73.42, "E2": 82.41, "F2": 87.31, "G2": 98.00, "A2": 110.00, "B2": 123.47,
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.00, "A3": 220.00, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "F5": 698.46, "G5": 783.99, "A5": 880.00, "B5": 987.77,
    "C6": 1046.50, "D6": 1174.66, "E6": 1318.51, "F6": 1396.91, "G6": 1567.98, "A6": 1760.00,
}

# 和弦进行预设（每个情绪对应一组和弦）
CHORD_PROGRESSIONS = {
    "cyberpunk": [
        ["A2", "C4", "E4", "G4"],  # Am
        ["F2", "A3", "C4", "F4"],  # F
        ["C2", "E3", "G3", "C4"],  # C
        ["G2", "B3", "D4", "G4"],  # G
    ],
    "retro": [
        ["C2", "E3", "G3", "C4"],  # C
        ["A2", "C4", "E4", "A4"],  # Am
        ["F2", "A3", "C4", "F4"],  # F
        ["G2", "B3", "D4", "G4"],  # G
    ],
    "vlog": [
        ["C2", "E3", "G3", "C4"],  # C
        ["G2", "B3", "D4", "G4"],  # G
        ["A2", "C4", "E4", "A4"],  # Am
        ["F2", "A3", "C4", "F4"],  # F
    ],
    "tech": [
        ["A2", "E3", "A3", "C4"],  # A5
        ["F2", "C3", "F3", "A3"],  # F5
        ["C2", "G2", "C3", "E3"],  # C
        ["G2", "D3", "G3", "B3"],  # G
    ],
    "dark": [
        ["A2", "C3", "E3", "A3"],  # Am
        ["G2", "A#2", "D3", "G3"],  # Gm
        ["F2", "G#2", "C3", "F3"],  # Fm
        ["E2", "G2", "B2", "E3"],  # Em
    ],
    "bright": [
        ["C2", "E3", "G3", "C4"],  # C
        ["D2", "F#3", "A3", "D4"],  # D
        ["G2", "B3", "D4", "G4"],  # G
        ["A2", "C#4", "E4", "A4"],  # A
    ],
    "minimal": [
        ["C2", "G2", "C3", "E3"],  # C
        ["F2", "C3", "F3", "A3"],  # F
    ],
    "ink": [
        ["D2", "A2", "D3", "F3"],  # Dm
        ["G2", "D3", "G3", "A#3"],  # Gm
        ["A2", "E3", "A3", "C4"],  # Am
        ["D2", "A2", "D3", "F3"],  # Dm
    ],
    "glitch": [
        ["A2", "A#2", "E3", "A3"],  # 不协和
        ["F2", "F#2", "C3", "F3"],  # 不协和
        ["C2", "C#2", "G2", "C3"],  # 不协和
        ["G2", "G#2", "D3", "G3"],  # 不协和
    ],
    "default": [
        ["C2", "E3", "G3", "C4"],  # C
        ["G2", "B3", "D4", "G4"],  # G
        ["A2", "C4", "E4", "A4"],  # Am
        ["F2", "A3", "C4", "F4"],  # F
    ],
}

# 旋律音阶（每个情绪对应一组旋律音符）
MELODY_SCALES = {
    "cyberpunk": ["A4", "C5", "D5", "E5", "G5", "A5"],
    "retro": ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5"],
    "vlog": ["C4", "D4", "E4", "G4", "A4", "C5"],
    "tech": ["A3", "C4", "D4", "E4", "G4", "A4", "C5"],
    "dark": ["A3", "C4", "D4", "E4", "G4", "A4"],
    "bright": ["C4", "D4", "E4", "F#4", "G4", "A4", "B4", "C5"],
    "minimal": ["C4", "E4", "G4", "C5"],
    "ink": ["D4", "F4", "G4", "A4", "C5", "D5"],
    "glitch": ["A3", "A#3", "E4", "A4", "C5", "C#5"],
    "default": ["C4", "D4", "E4", "G4", "A4", "C5"],
}


class RealBGMGenerator:
    """真实BGM程序生成器"""

    def __init__(self, ffmpeg_path: str = None, sample_rate: int = 44100):
        if ffmpeg_path is None:
            ffmpeg_path = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
        self.ffmpeg = ffmpeg_path
        self.sr = sample_rate

    def _generate_tone(self, freq: float, duration: float, volume: float = 0.3,
                       waveform: str = "sine", attack: float = 0.02,
                       release: float = 0.1) -> np.ndarray:
        """生成单个音符波形"""
        t = np.linspace(0, duration, int(self.sr * duration), endpoint=False)

        if waveform == "sine":
            wave = np.sin(2 * np.pi * freq * t)
        elif waveform == "triangle":
            wave = 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1
        elif waveform == "sawtooth":
            wave = 2 * (t * freq - np.floor(t * freq + 0.5))
        elif waveform == "square":
            wave = np.sign(np.sin(2 * np.pi * freq * t))
        else:
            wave = np.sin(2 * np.pi * freq * t)

        # ADSR包络
        n = len(wave)
        env = np.ones(n)
        attack_n = int(attack * self.sr)
        release_n = int(release * self.sr)
        if attack_n > 0:
            env[:attack_n] = np.linspace(0, 1, attack_n)
        if release_n > 0 and release_n < n:
            env[-release_n:] = np.linspace(1, 0, release_n)

        return wave * env * volume

    def _generate_chord(self, notes: List[str], duration: float,
                        volume: float = 0.15) -> np.ndarray:
        """生成和弦（多音符叠加）"""
        chord = np.zeros(int(self.sr * duration))
        for note in notes:
            freq = NOTE_FREQS.get(note, 440)
            chord += self._generate_tone(freq, duration, volume / len(notes), "triangle", 0.05, 0.2)
        return chord

    def _generate_bass(self, root_note: str, duration: float,
                       volume: float = 0.2) -> np.ndarray:
        """生成贝斯线"""
        freq = NOTE_FREQS.get(root_note, 110)
        return self._generate_tone(freq, duration, volume, "sawtooth", 0.01, 0.05)

    def _generate_melody(self, scale: List[str], duration: float,
                         bpm: int = 120, volume: float = 0.12,
                         chords: List[List[str]] = None) -> np.ndarray:
        """生成旋律线（音乐理论驱动：和弦音优先+动机重复+级进进行）"""
        beat_dur = 60.0 / bpm
        num_beats = int(duration / beat_dur)
        melody = np.zeros(int(self.sr * duration))

        # 构建动机（4拍），然后重复+变化
        np.random.seed(42)
        motif = []
        prev_note_idx = len(scale) // 2
        for i in range(4):
            if np.random.random() < 0.8:  # 80%有音符
                # 70%和弦音（如果提供了chords），30%音阶内级进
                if chords and i < len(chords):
                    chord_notes = [n for n in chords[i % len(chords)] if n in scale]
                    if chord_notes and np.random.random() < 0.7:
                        note = np.random.choice(chord_notes)
                    else:
                        # 级进：上下1-2度
                        step = np.random.choice([-2, -1, 1, 2])
                        prev_note_idx = max(0, min(len(scale)-1, prev_note_idx + step))
                        note = scale[prev_note_idx]
                else:
                    step = np.random.choice([-2, -1, 0, 1, 2])
                    prev_note_idx = max(0, min(len(scale)-1, prev_note_idx + step))
                    note = scale[prev_note_idx]
                motif.append((note, beat_dur * (0.5 if np.random.random() < 0.3 else 1.0)))
            else:
                motif.append((None, beat_dur))

        # 重复动机，每4小节变化一次
        current_time = 0.0
        bar_count = 0
        while current_time < duration - 0.01:
            for note, note_dur in motif:
                if current_time + note_dur > duration:
                    current_time = duration
                    break
                if note:
                    # 副歌段（bar_count % 4 >= 2）提高八度
                    actual_note = note
                    if bar_count % 4 >= 2 and note[-1].isdigit():
                        octave = int(note[-1]) + 1
                        actual_note = note[:-1] + str(octave)
                        if actual_note not in NOTE_FREQS:
                            actual_note = note
                    freq = NOTE_FREQS.get(actual_note, 440)
                    start = int(current_time * self.sr)
                    end = min(start + int(note_dur * self.sr), len(melody))
                    tone = self._generate_tone(freq, (end - start) / self.sr, volume, "sine", 0.02, 0.15)
                    melody[start:end] += tone[:end - start]
                current_time += note_dur
            bar_count += 1
            # 每2小节变化动机的最后一个音
            if bar_count % 2 == 0 and motif:
                last = motif[-1]
                if last[0]:
                    step = np.random.choice([-1, 1])
                    idx = scale.index(last[0]) if last[0] in scale else len(scale)//2
                    new_idx = max(0, min(len(scale)-1, idx + step))
                    motif[-1] = (scale[new_idx], last[1])

        return melody

    def _generate_drums(self, duration: float, bpm: int = 120,
                        volume: float = 0.15) -> np.ndarray:
        """生成鼓点（底鼓+军鼓+踩镲，主歌/副歌节奏变化）"""
        beat_dur = 60.0 / bpm
        drums = np.zeros(int(self.sr * duration))

        num_beats = int(duration / beat_dur)
        for i in range(num_beats):
            bar_pos = i % 4  # 小节内位置
            is_chorus = (i // 4) % 2 == 1  # 偶数小节主歌，奇数小节副歌

            # 底鼓：主歌1、3拍；副歌1、2&、3、4&
            kick_beats = [0, 2] if not is_chorus else [0, 1.5, 2, 3.5]
            for kb in kick_beats:
                kick_start = int((i + kb) * beat_dur * self.sr)
                kick_dur = int(0.12 * self.sr)
                if kick_start + kick_dur < len(drums):
                    t = np.linspace(0, 0.12, kick_dur, endpoint=False)
                    kick = np.sin(2 * np.pi * (90 - 50 * t) * t) * np.exp(-t * 25)
                    drums[kick_start:kick_start + kick_dur] += kick * volume * (1.2 if is_chorus else 1.0)

            # 军鼓：2、4拍（副歌更重）
            snare_beats = [1, 3]
            for sb in snare_beats:
                snare_start = int((i + sb) * beat_dur * self.sr)
                snare_dur = int(0.15 * self.sr)
                if snare_start + snare_dur < len(drums):
                    noise = np.random.randn(snare_dur) * 0.5
                    tone = np.sin(2 * np.pi * 200 * np.linspace(0, 0.15, snare_dur)) * 0.3
                    snare = (noise + tone) * np.exp(-np.linspace(0, 8, snare_dur))
                    drums[snare_start:snare_start + snare_dur] += snare * volume * (1.3 if is_chorus else 0.8)

            # 踩镲：八分音符（副歌更密）
            hat_interval = 0.5 if not is_chorus else 0.25
            h = 0.0
            while h < 1.0:
                hat_start = int((i + h) * beat_dur * self.sr)
                hat_dur = int(0.04 * self.sr)
                if hat_start + hat_dur < len(drums):
                    noise = np.random.randn(hat_dur) * 0.2
                    hat = noise * np.exp(-np.linspace(0, 15, hat_dur))
                    drums[hat_start:hat_start + hat_dur] += hat * volume * 0.4
                h += hat_interval

        return drums

    def generate(self, mood: str = "default", duration: float = 30.0,
                 bpm: int = 120, output_path: str = None) -> Optional[str]:
        """
        生成完整BGM

        Args:
            mood: 情绪风格（cyberpunk/retro/vlog/tech/dark/bright/minimal/ink/glitch/default）
            duration: 时长（秒）
            bpm: 速度
            output_path: 输出路径

        Returns:
            输出文件路径或None
        """
        if output_path is None:
            output_path = os.path.join(tempfile.gettempdir(), f"bgm_{mood}_{int(duration)}s.wav")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        chords = CHORD_PROGRESSIONS.get(mood, CHORD_PROGRESSIONS["default"])
        scale = MELODY_SCALES.get(mood, MELODY_SCALES["default"])

        # 每个和弦持续4拍
        chord_dur = 4 * 60.0 / bpm
        num_chords = int(np.ceil(duration / chord_dur))

        # 生成各声部
        full_len = int(self.sr * duration)
        chord_track = np.zeros(full_len)
        bass_track = np.zeros(full_len)
        melody_track = np.zeros(full_len)
        drum_track = np.zeros(full_len)

        for i in range(num_chords):
            chord = chords[i % len(chords)]
            start = int(i * chord_dur * self.sr)
            end = min(start + int(chord_dur * self.sr), full_len)
            seg_dur = (end - start) / self.sr

            # 和弦
            chord_seg = self._generate_chord(chord, seg_dur, 0.12)
            chord_track[start:end] += chord_seg[:end - start]

            # 贝斯（根音）
            bass_note = chord[0]
            bass_seg = self._generate_bass(bass_note, seg_dur, 0.18)
            bass_track[start:end] += bass_seg[:end - start]

        # 旋律（全曲，和弦音优先）
        melody_track = self._generate_melody(scale, duration, bpm, 0.1, chords)

        # 琶音（分解和弦，副歌段更明显）
        arp_track = np.zeros(full_len)
        for i in range(num_chords):
            chord = chords[i % len(chords)]
            start = int(i * chord_dur * self.sr)
            end = min(start + int(chord_dur * self.sr), full_len)
            seg_dur = (end - start) / self.sr
            is_chorus = (i % 2 == 1)
            if is_chorus:  # 副歌加琶音
                note_dur = chord_dur / 4
                for j, note in enumerate(chord * 2):
                    n_start = int((i * chord_dur + j * note_dur) * self.sr)
                    n_end = min(n_start + int(note_dur * self.sr), full_len)
                    if n_start < full_len:
                        freq = NOTE_FREQS.get(note, 440)
                        tone = self._generate_tone(freq, (n_end - n_start) / self.sr, 0.06, "triangle", 0.01, 0.05)
                        arp_track[n_start:n_end] += tone[:n_end - n_start]

        # 鼓点（minimal/ink不加鼓）
        if mood not in ["minimal", "ink"]:
            drum_track = self._generate_drums(duration, bpm, 0.12)

        # 混合
        mix = chord_track + bass_track + melody_track + drum_track + arp_track

        # 归一化
        peak = np.max(np.abs(mix))
        if peak > 0:
            mix = mix / peak * 0.85

        # 淡入淡出
        fade_n = int(0.5 * self.sr)
        if fade_n < full_len:
            mix[:fade_n] *= np.linspace(0, 1, fade_n)
            mix[-fade_n:] *= np.linspace(1, 0, fade_n)

        # 写WAV
        self._write_wav(output_path, mix)
        return output_path

    def _write_wav(self, path: str, data: np.ndarray):
        """写WAV文件"""
        import struct
        data_int = (data * 32767).astype(np.int16)
        with open(path, "wb") as f:
            # RIFF header
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + len(data_int) * 2))
            f.write(b"WAVE")
            # fmt chunk
            f.write(b"fmt ")
            f.write(struct.pack("<I", 16))
            f.write(struct.pack("<H", 1))  # PCM
            f.write(struct.pack("<H", 1))  # mono
            f.write(struct.pack("<I", self.sr))
            f.write(struct.pack("<I", self.sr * 2))
            f.write(struct.pack("<H", 2))
            f.write(struct.pack("<H", 16))
            # data chunk
            f.write(b"data")
            f.write(struct.pack("<I", len(data_int) * 2))
            f.write(data_int.tobytes())

    def list_moods(self) -> List[str]:
        return list(CHORD_PROGRESSIONS.keys())


if __name__ == "__main__":
    print("=" * 60)
    print("真实BGM生成器 v1.0")
    print("=" * 60)

    gen = RealBGMGenerator()
    print(f"\n可用情绪: {gen.list_moods()}")

    # 测试生成3种风格
    test_moods = ["vlog", "cyberpunk", "dark"]
    for mood in test_moods:
        out = gen.generate(mood, duration=10, bpm=120)
        if out and os.path.exists(out):
            size = os.path.getsize(out)
            print(f"  ✅ {mood}: {out} ({size//1024}KB)")
        else:
            print(f"  ❌ {mood}: 生成失败")
