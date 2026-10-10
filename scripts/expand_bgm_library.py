#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BGM库扩充脚本 - 生成更多合成BGM并修复标签库
"""
import os
import json
import struct
import math
import random
import wave
import subprocess

BGM_DIR = r"D:\DobaoWork_Project\Ai_Video_Editor\material\bgm"
FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
SAMPLE_RATE = 44100
DURATION = 30  # 秒

os.makedirs(BGM_DIR, exist_ok=True)


def generate_wav(filename, frequency=440, tempo=120, style="pop", emotion="happy"):
    """生成合成BGM WAV文件"""
    wav_path = os.path.join(BGM_DIR, filename.replace(".mp3", ".wav"))
    n_samples = SAMPLE_RATE * DURATION

    # 根据情绪和风格设置参数
    params = {
        "happy": {"base_freq": 523, "harmonics": [1, 2, 3], "amplitude": 0.3, "rhythm": 0.5},
        "sad": {"base_freq": 293, "harmonics": [1, 1.5, 2], "amplitude": 0.2, "rhythm": 0.2},
        "energetic": {"base_freq": 440, "harmonics": [1, 2, 3, 4], "amplitude": 0.35, "rhythm": 0.7},
        "calm": {"base_freq": 349, "harmonics": [1, 1.5], "amplitude": 0.15, "rhythm": 0.1},
        "romantic": {"base_freq": 392, "harmonics": [1, 2, 2.5], "amplitude": 0.25, "rhythm": 0.3},
        "tense": {"base_freq": 220, "harmonics": [1, 1.25, 1.5], "amplitude": 0.25, "rhythm": 0.6},
        "funny": {"base_freq": 587, "harmonics": [1, 2, 3, 5], "amplitude": 0.25, "rhythm": 0.8},
        "inspiring": {"base_freq": 440, "harmonics": [1, 2, 3], "amplitude": 0.3, "rhythm": 0.4},
        "mysterious": {"base_freq": 261, "harmonics": [1, 1.33, 1.5], "amplitude": 0.2, "rhythm": 0.3},
        "epic": {"base_freq": 330, "harmonics": [1, 2, 3, 4, 5], "amplitude": 0.35, "rhythm": 0.5},
    }
    p = params.get(emotion, params["happy"])

    samples = []
    beat_interval = 60.0 / tempo

    for i in range(n_samples):
        t = i / SAMPLE_RATE
        beat_pos = (t % beat_interval) / beat_interval

        # 基础旋律
        value = 0
        for h, amp_ratio in zip(p["harmonics"], [1.0, 0.5, 0.3, 0.2, 0.1]):
            freq = p["base_freq"] * h
            value += math.sin(2 * math.pi * freq * t) * p["amplitude"] * amp_ratio

        # 节奏包络
        if beat_pos < 0.1:
            envelope = 1.0
        elif beat_pos < 0.3:
            envelope = 0.7
        else:
            envelope = 0.4 + p["rhythm"] * 0.3

        value *= envelope

        # 缓慢的音量变化（避免单调）
        value *= 0.8 + 0.2 * math.sin(2 * math.pi * 0.1 * t)

        # 淡入淡出
        if t < 1.0:
            value *= t
        elif t > DURATION - 1.0:
            value *= (DURATION - t)

        samples.append(int(max(-32767, min(32767, value * 32767))))

    # 写入WAV
    with wave.open(wav_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))

    return wav_path


def wav_to_mp3(wav_path, mp3_path):
    """WAV转MP3"""
    cmd = [FFMPEG, "-y", "-i", wav_path, "-codec:a", "libmp3lame",
           "-b:a", "128k", mp3_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if os.path.exists(mp3_path):
        os.remove(wav_path)
        return True
    return False


# 新增20首BGM配置
NEW_BGMS = [
    # 情绪扩展
    {"id": "11_mysterious_ambient", "name": "神秘氛围", "emotion": "mysterious", "style": "ambient", "tempo": 80, "bpm": 80, "emotions": ["mysterious", "tense", "calm"], "styles": ["ambient", "cinematic"], "tags": ["神秘", "悬疑", "氛围", "探索"]},
    {"id": "12_epic_orchestral", "name": "史诗管弦", "emotion": "epic", "style": "orchestral", "tempo": 90, "bpm": 90, "emotions": ["epic", "energetic", "inspiring"], "styles": ["cinematic", "orchestral"], "tags": ["史诗", "大气", "震撼", "电影"]},
    {"id": "13_chill_lofi", "name": "Chill Lo-Fi", "emotion": "calm", "style": "lofi", "tempo": 75, "bpm": 75, "emotions": ["calm", "sad", "romantic"], "styles": ["lofi", "electronic"], "tags": ["放松", "慵懒", "学习", "治愈"]},
    {"id": "14_action_punch", "name": "动作冲击", "emotion": "energetic", "style": "electronic", "tempo": 140, "bpm": 140, "emotions": ["energetic", "tense"], "styles": ["electronic", "rock"], "tags": ["动作", "紧张", "战斗", "速度"]},
    {"id": "15_nostalgic_piano", "name": "怀旧钢琴", "emotion": "sad", "style": "acoustic", "tempo": 65, "bpm": 65, "emotions": ["sad", "calm", "romantic"], "styles": ["acoustic", "cinematic"], "tags": ["怀旧", "回忆", "抒情", "钢琴"]},
    {"id": "16_summer_pop", "name": "夏日流行", "emotion": "happy", "style": "pop", "tempo": 120, "bpm": 120, "emotions": ["happy", "energetic", "funny"], "styles": ["pop", "vlog"], "tags": ["夏日", "清新", "活力", "阳光"]},
    {"id": "17_horror_creepy", "name": "恐怖诡异", "emotion": "tense", "style": "ambient", "tempo": 60, "bpm": 60, "emotions": ["tense", "mysterious"], "styles": ["ambient", "cinematic"], "tags": ["恐怖", "诡异", "惊悚", "黑暗"]},
    {"id": "18_motivation_rock", "name": "励志摇滚", "emotion": "inspiring", "style": "rock", "tempo": 125, "bpm": 125, "emotions": ["inspiring", "energetic"], "styles": ["rock", "corporate"], "tags": ["励志", "热血", "奋斗", "力量"]},
    {"id": "19_jazz_smooth", "name": "顺滑爵士", "emotion": "calm", "style": "jazz", "tempo": 95, "bpm": 95, "emotions": ["calm", "romantic", "happy"], "styles": ["jazz", "acoustic"], "tags": ["爵士", "优雅", "咖啡", "放松"]},
    {"id": "20_future_bass", "name": "未来贝斯", "emotion": "energetic", "style": "electronic", "tempo": 150, "bpm": 150, "emotions": ["energetic", "happy"], "styles": ["electronic", "edm"], "tags": ["电子", "未来", "炫酷", "潮流"]},
    # 风格扩展
    {"id": "21_chinese_traditional", "name": "中国风", "emotion": "calm", "style": "chinese", "tempo": 85, "bpm": 85, "emotions": ["calm", "romantic", "sad"], "styles": ["chinese", "cinematic"], "tags": ["中国风", "古风", "古筝", "民族"]},
    {"id": "22_travel_adventure", "name": "旅行冒险", "emotion": "happy", "style": "vlog", "tempo": 110, "bpm": 110, "emotions": ["happy", "inspiring", "energetic"], "styles": ["vlog", "pop"], "tags": ["旅行", "冒险", "自由", "探索"]},
    {"id": "23_tech_corporate", "name": "科技商务", "emotion": "inspiring", "style": "corporate", "tempo": 115, "bpm": 115, "emotions": ["inspiring", "calm", "energetic"], "styles": ["corporate", "electronic"], "tags": ["科技", "商务", "未来", "专业"]},
    {"id": "24_dreamy_atmosphere", "name": "梦幻氛围", "emotion": "romantic", "style": "ambient", "tempo": 70, "bpm": 70, "emotions": ["romantic", "calm", "mysterious"], "styles": ["ambient", "electronic"], "tags": ["梦幻", "空灵", "治愈", "幻想"]},
    {"id": "25_comedy_slapstick", "name": "喜剧搞怪", "emotion": "funny", "style": "pop", "tempo": 135, "bpm": 135, "emotions": ["funny", "happy"], "styles": ["pop", "vlog"], "tags": ["搞笑", "滑稽", "俏皮", "欢乐"]},
    {"id": "26_deep_house", "name": "Deep House", "emotion": "energetic", "style": "electronic", "tempo": 122, "bpm": 122, "emotions": ["energetic", "calm"], "styles": ["electronic", "edm"], "tags": ["电子", "律动", "夜店", "节奏"]},
    {"id": "27_acoustic_guitar", "name": "原声吉他", "emotion": "calm", "style": "acoustic", "tempo": 80, "bpm": 80, "emotions": ["calm", "romantic", "sad"], "styles": ["acoustic", "folk"], "tags": ["吉他", "民谣", "清新", "自然"]},
    {"id": "28_cinematic_trailer", "name": "电影预告", "emotion": "epic", "style": "cinematic", "tempo": 100, "bpm": 100, "emotions": ["epic", "tense", "inspiring"], "styles": ["cinematic", "orchestral"], "tags": ["预告", "大片", "紧张", "震撼"]},
    {"id": "29_meditation_zen", "name": "冥想禅意", "emotion": "calm", "style": "ambient", "tempo": 55, "bpm": 55, "emotions": ["calm"], "styles": ["ambient", "chinese"], "tags": ["冥想", "禅意", "静心", "瑜伽"]},
    {"id": "30_urban_hiphop", "name": "都市嘻哈", "emotion": "energetic", "style": "hiphop", "tempo": 95, "bpm": 95, "emotions": ["energetic", "funny", "inspiring"], "styles": ["hiphop", "electronic"], "tags": ["嘻哈", "都市", "潮流", "节奏"]},
]


def main():
    print("=== BGM库扩充 ===")
    print(f"目标: 10首 -> 30首")

    # 生成新BGM
    success_count = 0
    for bgm in NEW_BGMS:
        mp3_file = f"{bgm['id']}.mp3"
        mp3_path = os.path.join(BGM_DIR, mp3_file)

        if os.path.exists(mp3_path):
            print(f"  跳过(已存在): {mp3_file}")
            success_count += 1
            continue

        print(f"  生成: {bgm['name']} ({bgm['id']})...", end=" ")
        try:
            wav_path = generate_wav(
                mp3_file,
                tempo=bgm["bpm"],
                emotion=bgm["emotion"],
                style=bgm["style"],
            )
            if wav_to_mp3(wav_path, mp3_path):
                print("✅")
                success_count += 1
            else:
                print("❌ MP3转换失败")
        except Exception as e:
            print(f"❌ {e}")

    print(f"\n生成完成: {success_count}/{len(NEW_BGMS)}")

    # 重建library.json（修复编码）
    print("\n重建library.json...")

    # 原有10首的正确元数据
    original_tracks = [
        {"id": "01_happy_upbeat", "file": "01_happy_upbeat.mp3", "name": "欢快 upbeat", "duration": 30, "emotions": ["happy", "energetic", "funny"], "styles": ["pop", "vlog"], "tempo": "fast", "bpm": 128, "copyright": "synthetic", "tags": ["开心", "欢快", "活力", "日常", "vlog"]},
        {"id": "02_sad_emotional", "file": "02_sad_emotional.mp3", "name": "抒情 emotional", "duration": 30, "emotions": ["sad", "calm", "romantic"], "styles": ["cinematic", "acoustic"], "tempo": "slow", "bpm": 70, "copyright": "synthetic", "tags": ["悲伤", "抒情", "感人", "治愈", "电影感"]},
        {"id": "03_energetic_epic", "file": "03_energetic_epic.mp3", "name": "激情 epic", "duration": 30, "emotions": ["energetic", "inspiring", "tense"], "styles": ["cinematic", "rock", "electronic"], "tempo": "fast", "bpm": 140, "copyright": "synthetic", "tags": ["激情", "热血", "震撼", "大片", "燃"]},
        {"id": "04_calm_relaxing", "file": "04_calm_relaxing.mp3", "name": "平静 relaxing", "duration": 30, "emotions": ["calm", "sad"], "styles": ["ambient", "acoustic", "corporate"], "tempo": "slow", "bpm": 65, "copyright": "synthetic", "tags": ["平静", "舒缓", "放松", "治愈", "安静", "冥想"]},
        {"id": "05_romantic_sweet", "file": "05_romantic_sweet.mp3", "name": "浪漫 sweet", "duration": 30, "emotions": ["romantic", "happy", "calm"], "styles": ["pop", "acoustic"], "tempo": "medium", "bpm": 90, "copyright": "synthetic", "tags": ["浪漫", "甜蜜", "爱情", "温馨", "幸福"]},
        {"id": "06_tense_suspense", "file": "06_tense_suspense.mp3", "name": "悬疑 suspense", "duration": 30, "emotions": ["tense", "energetic"], "styles": ["cinematic", "electronic"], "tempo": "medium", "bpm": 100, "copyright": "synthetic", "tags": ["紧张", "悬疑", "惊悚", "压迫", "神秘"]},
        {"id": "07_funny_comedy", "file": "07_funny_comedy.mp3", "name": "搞笑 comedy", "duration": 30, "emotions": ["funny", "happy"], "styles": ["pop", "vlog"], "tempo": "fast", "bpm": 130, "copyright": "synthetic", "tags": ["搞笑", "幽默", "滑稽", "俏皮", "轻松"]},
        {"id": "08_inspiring_corporate", "file": "08_inspiring_corporate.mp3", "name": "激励 corporate", "duration": 30, "emotions": ["inspiring", "energetic", "calm"], "styles": ["corporate", "cinematic"], "tempo": "medium", "bpm": 110, "copyright": "synthetic", "tags": ["激励", "励志", "正能量", "大气", "商务", "企业"]},
        {"id": "09_cinematic_epic", "file": "09_cinematic_epic.mp3", "name": "电影感 cinematic", "duration": 30, "emotions": ["energetic", "inspiring", "tense"], "styles": ["cinematic", "orchestral"], "tempo": "slow", "bpm": 80, "copyright": "synthetic", "tags": ["电影", "影视", "大片", "史诗", "震撼", "叙事"]},
        {"id": "10_vlog_lifestyle", "file": "10_vlog_lifestyle.mp3", "name": "日常 vlog", "duration": 30, "emotions": ["happy", "calm", "funny"], "styles": ["vlog", "pop", "lifestyle"], "tempo": "medium", "bpm": 105, "copyright": "synthetic", "tags": ["日常", "生活", "旅行", "vlog", "轻松", "记录"]},
    ]

    # 合并所有曲目
    all_tracks = original_tracks + NEW_BGMS

    library = {
        "version": "2.0",
        "updated": "2026-10-10",
        "total": len(all_tracks),
        "tracks": all_tracks,
    }

    lib_path = os.path.join(BGM_DIR, "library.json")
    with open(lib_path, "w", encoding="utf-8") as f:
        json.dump(library, f, ensure_ascii=False, indent=2)

    print(f"library.json已重建: {len(all_tracks)}首BGM")

    # 统计
    emotions_count = {}
    styles_count = {}
    for t in all_tracks:
        for e in t["emotions"]:
            emotions_count[e] = emotions_count.get(e, 0) + 1
        for s in t["styles"]:
            styles_count[s] = styles_count.get(s, 0) + 1

    print(f"\n情绪覆盖: {len(emotions_count)}种")
    for e, c in sorted(emotions_count.items(), key=lambda x: -x[1]):
        print(f"  {e}: {c}首")
    print(f"\n风格覆盖: {len(styles_count)}种")
    for s, c in sorted(styles_count.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}首")


if __name__ == "__main__":
    main()
