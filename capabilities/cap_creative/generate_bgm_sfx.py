"""
只生成BGM和SFX（TTS已完成）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from sound_engine import SoundEngine

BGM_LIST = [
    ("bgm_melancholy", "melancholy", 30),
    ("bgm_tension", "tension", 15),
    ("bgm_curious", "curious", 12),
    ("bgm_hopeful", "hopeful", 15),
    ("bgm_uplifting", "uplifting", 20),
    ("bgm_triumphant", "triumphant", 25),
    ("bgm_inspiring", "inspiring", 25),
]

SFX_LIST = [
    ("sfx_keyboard", "keyboard", 3),
    ("sfx_mouse", "mouse_click", 2),
    ("sfx_notification", "notification", 2),
    ("sfx_applause", "applause", 5),
    ("sfx_whoosh", "whoosh", 2),
]

def main():
    engine = SoundEngine()
    output_dir = os.path.join(os.path.dirname(__file__), "audio_output", "fanshen_v4")
    os.makedirs(output_dir, exist_ok=True)

    # BGM
    print("[1/2] 生成BGM...")
    for i, (name, mood, duration) in enumerate(BGM_LIST):
        print(f"  [{i+1}/{len(BGM_LIST)}] {name} ({mood}, {duration}s)...")
        result = engine.generate_bgm_placeholder(
            mood=mood,
            duration=duration,
            output_file=os.path.join(output_dir, f"{name}.wav"),
        )
        if result:
            print(f"    ✅ {result}")
        else:
            print(f"    ❌ 失败")

    # SFX
    print("\n[2/2] 生成SFX...")
    for i, (name, sfx_type, duration) in enumerate(SFX_LIST):
        print(f"  [{i+1}/{len(SFX_LIST)}] {name} ({sfx_type})...")
        result = engine.generate_sfx_placeholder(
            sfx_type=sfx_type,
            duration=duration,
            output_file=os.path.join(output_dir, f"{name}.wav"),
        )
        if result:
            print(f"    ✅ {result}")
        else:
            print(f"    ❌ 失败")

    # 统计
    print("\n" + "=" * 60)
    files = os.listdir(output_dir)
    print(f"声音素材总数: {len(files)}")
    print(f"  旁白: {len([f for f in files if f.startswith('n')])}")
    print(f"  对话: {len([f for f in files if f.startswith('d')])}")
    print(f"  BGM: {len([f for f in files if f.startswith('bgm')])}")
    print(f"  SFX: {len([f for f in files if f.startswith('sfx')])}")
    print("✅ BGM+SFX生成完成")

if __name__ == "__main__":
    main()
