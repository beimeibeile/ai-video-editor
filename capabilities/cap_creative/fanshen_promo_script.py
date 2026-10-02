"""
《翻身》真实风格宣传视频 - 剧本v2
目标：抖音60秒短视频，真实电影感，情感共鸣
"""

SCRIPT_V2 = {
    "title": "一个普通人的翻身故事",
    "duration": 60,
    "platform": "抖音竖屏 9:16",
    "style": "真实电影感 / 暖色调 / 手持运镜",
    "logline": "凌晨三点的办公室，一个被生活压垮的普通人，偶然发现了改变命运的工具。",
    "scenes": [
        {
            "id": "S01",
            "name": "深夜加班",
            "duration": 8,
            "emotion": "压抑 / 疲惫",
            "image_prompt": "cinematic photo, tired young asian man sitting at office desk at 3am, messy hair, dark circles under eyes, glowing computer screen, empty coffee cups, dim office lighting, shallow depth of field, film grain, moody atmosphere, photorealistic, 8k",
            "narration": "凌晨三点，办公室只剩他一个人。",
            "bgm": "melancholy",
            "sfx": ["keyboard", "clock_tick"],
        },
        {
            "id": "S02",
            "name": "被打回",
            "duration": 7,
            "emotion": "屈辱 / 无力",
            "image_prompt": "cinematic close-up, phone screen showing rejected work email, boss's angry message, hand trembling, dark background, dramatic lighting, photorealistic, film grain",
            "narration": "第三十二次，方案被打回。",
            "dialogue": {"speaker": "老板", "text": "这做的什么东西？重做！"},
            "bgm": "tension",
            "sfx": ["notification"],
        },
        {
            "id": "S03",
            "name": "偶然发现",
            "duration": 8,
            "emotion": "好奇 / 希望萌芽",
            "image_prompt": "cinematic over-shoulder shot, man looking at computer screen with AI video editor interface, eyes widening, warm glow from screen reflecting on face, dark room, hopeful atmosphere, photorealistic",
            "narration": "直到那天晚上，他偶然刷到了它。",
            "bgm": "curious",
            "sfx": ["mouse_click"],
        },
        {
            "id": "S04",
            "name": "第一次尝试",
            "duration": 8,
            "emotion": "兴奋 / 惊喜",
            "image_prompt": "cinematic photo, man leaning forward at computer, hands typing rapidly, screen showing AI generating video, expression of surprise and excitement, warm lighting, dynamic angle, photorealistic",
            "narration": "输入一句话，三分钟，一条完整的视频就出来了。",
            "dialogue": {"speaker": "林默", "text": "这...这也太快了吧？"},
            "bgm": "hopeful",
            "sfx": ["whoosh"],
        },
        {
            "id": "S05",
            "name": "逆袭",
            "duration": 10,
            "emotion": "自信 / 从容",
            "image_prompt": "cinematic portrait, confident young man in modern creative studio, arms crossed, slight smile, professional attire, bright natural lighting, clean modern background, success aura, photorealistic, 8k",
            "narration": "一个月后，他的视频账号涨粉十万。老板反过来求他带团队。",
            "dialogue": {"speaker": "老板", "text": "小林啊，这个项目还是你牵头吧。"},
            "bgm": "triumphant",
            "sfx": ["applause"],
        },
        {
            "id": "S06",
            "name": "产品亮相",
            "duration": 10,
            "emotion": "激励 / 希望",
            "image_prompt": "cinematic wide shot, modern creative studio with multiple monitors showing AI video editing interface, warm golden hour lighting through windows, professional atmosphere, futuristic but warm, photorealistic",
            "narration": "ai-video-editor，让每个人都能做出专业级视频。你的翻身，从今天开始。",
            "bgm": "inspiring",
            "sfx": [],
            "text_overlay": "ai-video-editor\nAI智能视频剪辑平台",
        },
        {
            "id": "S07",
            "name": "行动号召",
            "duration": 9,
            "emotion": "激励 / 行动",
            "image_prompt": "cinematic photo, hand reaching toward glowing screen with play button, dramatic lighting, hopeful atmosphere, dark background with warm glow, photorealistic, close-up",
            "narration": "别再熬夜了，让AI帮你干活。点击下方，免费体验。",
            "bgm": "uplifting",
            "sfx": [],
            "text_overlay": "立即体验\nai-video-editor",
        },
    ],
}

if __name__ == "__main__":
    print("=" * 60)
    print("《翻身》真实风格宣传视频 - 剧本v2")
    print("=" * 60)
    total = sum(s["duration"] for s in SCRIPT_V2["scenes"])
    print(f"总时长: {total}秒")
    print(f"场景数: {len(SCRIPT_V2['scenes'])}")
    for s in SCRIPT_V2["scenes"]:
        print(f"  {s['id']} ({s['duration']}s) {s['name']} - {s['emotion']}")
