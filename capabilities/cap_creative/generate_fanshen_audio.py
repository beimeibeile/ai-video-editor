"""
《翻身》v4 声音全流程生成
旁白TTS + 角色对话 + BGM + SFX
"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(__file__))
from sound_engine import SoundEngine

# 旁白内容
NARRATIONS = [
    ("n01", "凌晨两点，办公室只剩下他一个人。", "zh-CN-YunxiNeural"),
    ("n02", "第三十二次被打回的方案。", "zh-CN-YunxiNeural"),
    ("n03", "他开始怀疑，自己是不是真的不行。", "zh-CN-YunxiNeural"),
    ("n04", "他想反驳，却发现自己连一个能拿得出手的作品都没有。", "zh-CN-YunxiNeural"),
    ("n05", "三十岁，一事无成。这就是他的人生吗？", "zh-CN-YunxiNeural"),
    ("n06", "直到那天晚上，他刷到了一条视频。", "zh-CN-YunxiNeural"),
    ("n07", "一个叫ai-video-editor的工具，能让普通人也做出专业级视频。", "zh-CN-YunxiNeural"),
    ("n08", "他下载了软件，开始了第一次尝试。", "zh-CN-YunxiNeural"),
    ("n09", "输入一句话，AI自动写剧本、分镜、甚至生成画面素材。", "zh-CN-YunxiNeural"),
    ("n10", "那一晚，他忘记了时间。", "zh-CN-YunxiNeural"),
    ("n11", "一周后，他已经能熟练地用AI生成素材、配音、加特效。", "zh-CN-YunxiNeural"),
    ("n12", "第一条视频，画面精美，配音专业，特效到位。", "zh-CN-YunxiNeural"),
    ("n13", "他鼓起勇气，点击了发布。", "zh-CN-YunxiNeural"),
    ("n14", "然后，奇迹发生了。", "zh-CN-YunxiNeural"),
    ("n15", "一个月后，他像变了一个人。", "zh-CN-YunxiNeural"),
    ("n16", "掌声响起的那一刻，他知道，自己真的翻身了。", "zh-CN-YunxiNeural"),
    ("n17", "ai-video-editor，不只是一个工具。", "zh-CN-YunxiNeural"),
    ("n18", "它是你的剧本顾问、分镜导演、美术指导、音效师、剪辑师。", "zh-CN-YunxiNeural"),
    ("n19", "每个人都有创意，只是缺少一个把创意变成现实的工具。", "zh-CN-YunxiNeural"),
    ("n20", "ai-video-editor，让创意不再受限于技术。", "zh-CN-YunxiNeural"),
]

# 角色对话
DIALOGUES = [
    ("d01_boss", "这种东西也敢拿出来？重做！", "zh-CN-YunjianNeural"),  # 老板，严厉
    ("d02_linmo", "也许，可以试试？", "zh-CN-YunxiNeural"),  # 林默，犹豫
    ("d03_linmo", "这，这也太厉害了吧！", "zh-CN-YunxiNeural"),  # 林默，惊讶
    ("d04_linmo", "原来，我也可以。", "zh-CN-YunxiNeural"),  # 林默，哽咽
    ("d05_linmo", "这是我用ai-video-editor做的方案，大家看一下。", "zh-CN-YunxiNeural"),  # 林默，自信
    ("d06_boss", "这，这是你一个人做的？", "zh-CN-YunjianNeural"),  # 老板，惊讶
    ("d07_linmo", "是的。AI是工具，创意才是核心。", "zh-CN-YunxiNeural"),  # 林默，坚定
    ("d08_linmo", "你的翻身之作，从这里开始。", "zh-CN-YunxiNeural"),  # 林默，激励
]

# BGM情绪列表
BGM_LIST = [
    ("bgm_melancholy", "melancholy", 30),
    ("bgm_tension", "tension", 15),
    ("bgm_curious", "curious", 12),
    ("bgm_hopeful", "hopeful", 15),
    ("bgm_uplifting", "uplifting", 20),
    ("bgm_triumphant", "triumphant", 25),
    ("bgm_inspiring", "inspiring", 25),
]

# SFX列表
SFX_LIST = [
    ("sfx_keyboard", "keyboard", 3),
    ("sfx_mouse", "mouse_click", 2),
    ("sfx_notification", "notification", 2),
    ("sfx_applause", "applause", 5),
    ("sfx_whoosh", "whoosh", 2),
]


async def main():
    engine = SoundEngine()
    output_dir = os.path.join(os.path.dirname(__file__), "audio_output", "fanshen_v4")
    os.makedirs(output_dir, exist_ok=True)

    # 1. 生成旁白
    print("=" * 60)
    print("[1/4] 生成旁白TTS...")
    print("=" * 60)
    for i, (name, text, voice) in enumerate(NARRATIONS):
        print(f"  [{i+1}/{len(NARRATIONS)}] {name}: {text[:30]}...")
        result = await engine.generate_tts(
            text=text,
            voice=voice,
            output_file=os.path.join(output_dir, f"{name}.mp3"),
        )
        if result:
            print(f"    ✅ {result}")
        else:
            print(f"    ❌ 失败")

    # 2. 生成角色对话
    print("\n" + "=" * 60)
    print("[2/4] 生成角色对话TTS...")
    print("=" * 60)
    for i, (name, text, voice) in enumerate(DIALOGUES):
        print(f"  [{i+1}/{len(DIALOGUES)}] {name}: {text[:30]}...")
        result = await engine.generate_tts(
            text=text,
            voice=voice,
            output_file=os.path.join(output_dir, f"{name}.mp3"),
        )
        if result:
            print(f"    ✅ {result}")
        else:
            print(f"    ❌ 失败")

    # 3. 生成BGM
    print("\n" + "=" * 60)
    print("[3/4] 生成BGM...")
    print("=" * 60)
    for i, (name, mood, duration) in enumerate(BGM_LIST):
        print(f"  [{i+1}/{len(BGM_LIST)}] {name} ({mood}, {duration}s)...")
        result = engine.generate_bgm_placeholder(
            mood=mood,
            duration=duration,
            output_path=os.path.join(output_dir, f"{name}.wav"),
        )
        if result:
            print(f"    ✅ {result}")
        else:
            print(f"    ❌ 失败")

    # 4. 生成SFX
    print("\n" + "=" * 60)
    print("[4/4] 生成SFX...")
    print("=" * 60)
    for i, (name, sfx_type, duration) in enumerate(SFX_LIST):
        print(f"  [{i+1}/{len(SFX_LIST)}] {name} ({sfx_type})...")
        result = engine.generate_sfx_placeholder(
            sfx_type=sfx_type,
            duration=duration,
            output_path=os.path.join(output_dir, f"{name}.wav"),
        )
        if result:
            print(f"    ✅ {result}")
        else:
            print(f"    ❌ 失败")

    # 统计
    print("\n" + "=" * 60)
    print("声音生成完成！")
    print("=" * 60)
    files = os.listdir(output_dir)
    print(f"输出目录: {output_dir}")
    print(f"文件总数: {len(files)}")
    print(f"  旁白: {len([f for f in files if f.startswith('n')])}")
    print(f"  对话: {len([f for f in files if f.startswith('d')])}")
    print(f"  BGM: {len([f for f in files if f.startswith('bgm')])}")
    print(f"  SFX: {len([f for f in files if f.startswith('sfx')])}")


if __name__ == "__main__":
    asyncio.run(main())
