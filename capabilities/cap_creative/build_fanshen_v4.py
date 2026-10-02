"""
《翻身》v4 剪映工程构建
整合ComfyUI画面 + 声音引擎音频 + 文字标题 + 特效
"""
import sys
import os

# 路径配置
JY_SKILL = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor"
AVE_SKILL = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

from jy_wrapper import JyProject
import pyJianYingDraft as draft

# 素材路径
IMAGE_DIR = os.path.join(AVE_SKILL, "capabilities", "cap_creative", "image_output")
AUDIO_DIR = os.path.join(AVE_SKILL, "capabilities", "cap_creative", "audio_output", "fanshen_v4")
OUTPUT_DIR = r"D:\JianyingProDrafts\JianyingPro Drafts"

# 场景配置：(场景名, 画面文件, 旁白文件列表, BGM文件, 持续时间)
SCENES = [
    {
        "name": "S01_深夜加班",
        "image": "03_office_night.png",
        "narrations": ["n01.mp3", "n02.mp3", "n03.mp3"],
        "bgm": "bgm_melancholy.wav",
        "duration": 18,
        "title": "凌晨两点",
    },
    {
        "name": "S02_职场受挫",
        "image": "01_linmo_depressed.png",
        "narrations": ["n04.mp3", "n05.mp3"],
        "dialogues": ["d01_boss.mp3"],
        "bgm": "bgm_tension.wav",
        "duration": 15,
        "title": "第三十二次被打回",
    },
    {
        "name": "S03_偶然发现",
        "image": "04_home_computer.png",
        "narrations": ["n06.mp3", "n07.mp3"],
        "dialogues": ["d02_linmo.mp3"],
        "bgm": "bgm_curious.wav",
        "duration": 15,
        "title": "直到那天晚上",
    },
    {
        "name": "S04_初次尝试",
        "image": "04_home_computer.png",
        "narrations": ["n08.mp3", "n09.mp3", "n10.mp3"],
        "dialogues": ["d03_linmo.mp3"],
        "bgm": "bgm_hopeful.wav",
        "duration": 18,
        "title": "第一次尝试",
    },
    {
        "name": "S05_能力觉醒",
        "image": "02_linmo_confident.png",
        "narrations": ["n11.mp3", "n12.mp3", "n13.mp3", "n14.mp3"],
        "dialogues": ["d04_linmo.mp3"],
        "bgm": "bgm_uplifting.wav",
        "duration": 24,
        "title": "奇迹发生了",
    },
    {
        "name": "S06_职场逆袭",
        "image": "02_linmo_confident.png",
        "narrations": ["n15.mp3", "n16.mp3"],
        "dialogues": ["d05_linmo.mp3", "d06_boss.mp3", "d07_linmo.mp3"],
        "bgm": "bgm_triumphant.wav",
        "duration": 25,
        "title": "一个月后",
    },
    {
        "name": "S07_产品亮相",
        "image": "05_creative_space.png",
        "narrations": ["n17.mp3", "n18.mp3", "n19.mp3", "n20.mp3"],
        "dialogues": ["d08_linmo.mp3"],
        "bgm": "bgm_inspiring.wav",
        "duration": 30,
        "title": "ai-video-editor",
    },
]


def build_project():
    print("=" * 60)
    print("《翻身》v4 剪映工程构建")
    print("=" * 60)

    # 创建工程
    project = JyProject("Fanshen_v4", width=1080, height=1920, overwrite=True)
    print(f"\n工程创建: Fanshen_v4 (1080x1920)")

    current_time = 0.0

    for i, scene in enumerate(SCENES):
        scene_start = current_time
        scene_end = current_time + scene["duration"]
        print(f"\n[{i+1}/{len(SCENES)}] {scene['name']} ({scene['duration']}s, {scene_start:.1f}-{scene_end:.1f}s)")

        # 1. 添加画面
        img_path = os.path.join(IMAGE_DIR, scene["image"])
        if os.path.exists(img_path):
            img_seg = project.add_media_safe(
                img_path,
                start_time=f"{scene_start:.2f}s",
                duration=f"{scene['duration']:.2f}s",
                track_name="Video",
            )
            if img_seg:
                # 淡入淡出
                img_seg.add_keyframe(draft.KeyframeProperty.alpha, int(scene_start * 1e6), 0.0, **draft.Keyframe.EASE_OUT)
                img_seg.add_keyframe(draft.KeyframeProperty.alpha, int((scene_start + 0.5) * 1e6), 1.0, **draft.Keyframe.EASE_OUT)
                img_seg.add_keyframe(draft.KeyframeProperty.alpha, int((scene_end - 0.5) * 1e6), 1.0, **draft.Keyframe.EASE_OUT)
                img_seg.add_keyframe(draft.KeyframeProperty.alpha, int(scene_end * 1e6), 0.0, **draft.Keyframe.EASE_OUT)
                print(f"  ✅ 画面: {scene['image']}")
            else:
                print(f"  ❌ 画面添加失败")
        else:
            print(f"  ⚠️ 画面不存在: {img_path}")

        # 2. 添加BGM
        bgm_path = os.path.join(AUDIO_DIR, scene["bgm"])
        if os.path.exists(bgm_path):
            bgm_seg = project.add_media_safe(
                bgm_path,
                start_time=f"{scene_start:.2f}s",
                duration=f"{scene['duration']:.2f}s",
                track_name="BGM",
            )
            if bgm_seg:
                print(f"  ✅ BGM: {scene['bgm']}")
        else:
            print(f"  ⚠️ BGM不存在: {bgm_path}")

        # 3. 添加旁白（均匀分布在场景内）
        narrations = scene.get("narrations", [])
        if narrations:
            nar_interval = scene["duration"] / (len(narrations) + 1)
            for j, nar_file in enumerate(narrations):
                nar_path = os.path.join(AUDIO_DIR, nar_file)
                if os.path.exists(nar_path):
                    nar_time = scene_start + nar_interval * (j + 1)
                    nar_seg = project.add_media_safe(
                        nar_path,
                        start_time=f"{nar_time:.2f}s",
                        duration="5s",
                        track_name=f"Narration_{i}",
                    )
                    if nar_seg:
                        print(f"  ✅ 旁白{j+1}: {nar_file} @ {nar_time:.1f}s")

        # 4. 添加对话
        dialogues = scene.get("dialogues", [])
        if dialogues:
            dlg_interval = scene["duration"] / (len(dialogues) + 1)
            for j, dlg_file in enumerate(dialogues):
                dlg_path = os.path.join(AUDIO_DIR, dlg_file)
                if os.path.exists(dlg_path):
                    dlg_time = scene_start + dlg_interval * (j + 1) + nar_interval * 0.5
                    dlg_seg = project.add_media_safe(
                        dlg_path,
                        start_time=f"{dlg_time:.2f}s",
                        duration="5s",
                        track_name=f"Dialogue_{i}",
                    )
                    if dlg_seg:
                        print(f"  ✅ 对话{j+1}: {dlg_file} @ {dlg_time:.1f}s")

        # 5. 添加场景标题文字
        title_text = scene.get("title", "")
        if title_text:
            title_seg = project.add_text_simple(
                text=title_text,
                start_time=f"{scene_start + 0.5:.2f}s",
                duration="3s",
                track_name=f"Title_{i}",
                style=draft.TextStyle(size=10.0, color=(1.0, 1.0, 1.0)),
                anim_in="渐显",
            )
            if title_seg:
                print(f"  ✅ 标题: {title_text}")

        current_time = scene_end

    # 总时长
    total_duration = current_time
    print(f"\n总时长: {total_duration:.1f}s ({total_duration/60:.1f}分钟)")

    # 保存工程
    print("\n保存工程...")
    result = project.save()
    draft_path = result.get("draft_path", "")
    print(f"草稿路径: {draft_path}")

    # 复制到D盘剪映草稿目录
    if draft_path and os.path.exists(draft_path):
        import shutil
        dest_path = os.path.join(OUTPUT_DIR, "Fanshen_v4")
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(draft_path, dest_path)
        print(f"已复制到: {dest_path}")

    print("\n" + "=" * 60)
    print("✅ 剪映工程构建完成")
    print("=" * 60)
    print(f"场景数: {len(SCENES)}")
    print(f"总时长: {total_duration:.1f}s")
    print(f"画面: {len(SCENES)}个场景")
    print(f"旁白: {sum(len(s.get('narrations',[])) for s in SCENES)}条")
    print(f"对话: {sum(len(s.get('dialogues',[])) for s in SCENES)}条")
    print(f"BGM: {len(SCENES)}段")
    return result


if __name__ == "__main__":
    build_project()
