"""
AI短视频剪辑 - 模式A：制作视频 剪映工程创建脚本模板

使用方法：
1. 复制本脚本到项目根目录
2. 修改下方 CONFIG 区域的参数
3. 运行: python build_video.py

依赖：jianying-editor skill, ffmpeg, Python 3.11+
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys

# ==================== CONFIG（修改这里） ====================

PROJECT_NAME = "我的视频"          # 工程名
WIDTH = 1080                        # 画布宽（9:16=1080, 1:1=1080, 16:9=1920）
HEIGHT = 1920                       # 画布高（9:16=1920, 1:1=1080, 16:9=1080）
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")  # 素材目录

# 分镜表：(文件名, 起始时间, 持续时长)
# 时间格式: "0s", "2.5s", "00:00:02.500"
CLIPS = [
    ("img_01.jpg", "0s", "2.5s"),
    ("img_02.jpg", "2.5s", "0.5s"),
    ("img_03.jpg", "3.0s", "0.5s"),
    ("img_04.jpg", "3.5s", "0.5s"),
    ("img_05.jpg", "4.0s", "0.5s"),
    ("video_01.mp4", "4.5s", "5s"),
    ("img_06.jpg", "9.5s", "2.5s"),
]

# 旁白文案：(文案, 起始时间, 音色)
NARRATIONS = [
    # ("旁白文案第一句", "0.5s", "zh_female_xiaopengyou"),
    # ("旁白文案第二句", "3s", "zh_female_xiaopengyou"),
]

# BGM 关键词
BGM_QUERY = "国风"
BGM_START = "0s"
BGM_DURATION = "15s"

# 字幕：(文本, 起始时间, 持续时长, Y位置, 字号, 颜色RGB)
SUBTITLES = [
    # ("钩子文案", "0.3s", "2s", -0.7, 10.0, (1, 1, 1)),
    # ("slogan", "12s", "3s", 0.2, 14.0, (1, 0.2, 0.2)),
]

# 音效：(关键词, 起始时间, 持续时长) — 全片≤6个
SFX = [
    # ("鼓点", "2.5s", "0.3s"),
    # ("转场", "4.5s", "0.3s"),
]

# 贴纸：(关键词, 起始时间, 持续时长) — 全片≤3个
STICKERS = [
    # ("手机框", "0s", "10s"),
]

# 自动转场
AUTO_TRANSITION = True
TRANSITION_TYPE = "叠化"
TRANSITION_DURATION = "0.4s"

# ==================== 初始化（不要修改） ====================

# 探测 jianying-editor skill 路径
skill_root = next((p for p in [
    os.getenv("JY_SKILL_ROOT", "").strip(),
    r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor",
    r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jianying-editor"),
] if p and os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py"))), None)

if not skill_root:
    raise ImportError("Could not find jianying-editor skill root. Please set JY_SKILL_ROOT env var.")

sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject, draft

# ==================== 主流程 ====================

def main():
    logger.info(f"[1/6] 创建工程: {PROJECT_NAME} ({WIDTH}x{HEIGHT})")
    project = JyProject(PROJECT_NAME, width=WIDTH, height=HEIGHT, overwrite=True)

    # 2. 导入视图素材
    logger.info(f"[2/6] 导入 {len(CLIPS)} 个视图素材")
    segments = []
    for i, (filename, start, duration) in enumerate(CLIPS):
        path = os.path.join(ASSETS_DIR, filename)
        if not os.path.exists(path):
            logger.warning(f"  ⚠️  素材不存在，跳过: {path}")
            continue
        seg = project.add_media_safe(path, start_time=start, duration=duration)
        if seg:
            segments.append(seg)
            logger.info(f"  ✅ [{i+1}] {filename} ({start}, {duration})")

    # 3. 自动转场（注意：转场必须加在前一个片段上）
    if AUTO_TRANSITION and len(segments) > 1:
        logger.info(f"[3/6] 添加自动转场: {TRANSITION_TYPE} ({TRANSITION_DURATION})")
        for i in range(1, len(segments)):
            try:
                project.add_transition_simple(
                    TRANSITION_TYPE,
                    video_segment=segments[i-1],  # 转场加在前一个片段末尾
                    duration=TRANSITION_DURATION
                )
                logger.info(f"  ✅ 转场 [{i}]")
            except Exception as e:
                logger.error(f"  ⚠️  转场 [{i}] 失败: {e}")

    # 4. 多音轨
    logger.info("[4/6] 添加音轨")
    # 旁白
    for text, start, speaker in NARRATIONS:
        try:
            project.add_tts_intelligent(text, speaker=speaker, start_time=start, track_name="Narration")
            logger.info(f"  ✅ 旁白: {text[:20]}...")
        except Exception as e:
            logger.error(f"  ⚠️  旁白失败: {e}")

    # BGM
    if BGM_QUERY:
        try:
            project.add_cloud_music(BGM_QUERY, start_time=BGM_START, duration=BGM_DURATION, track_name="BGM")
            logger.info(f"  ✅ BGM: {BGM_QUERY}")
        except Exception as e:
            logger.error(f"  ⚠️  BGM失败（手动补）: {e}")

    # 音效
    for query, start, duration in SFX:
        try:
            project.add_cloud_media(query, start_time=start, duration=duration, track_name="SFX")
            logger.info(f"  ✅ 音效: {query}")
        except Exception as e:
            logger.error(f"  ⚠️  音效失败: {e}")

    # 5. 字幕 + 贴纸
    logger.info("[5/6] 添加字幕和贴纸")
    for text, start, duration, y, size, color in SUBTITLES:
        try:
            project.add_text_simple(
                text, start_time=start, duration=duration,
                clip_settings=draft.ClipSettings(transform_y=y),
                font_size=size, color_rgb=color
            )
            logger.info(f"  ✅ 字幕: {text[:20]}")
        except Exception as e:
            logger.error(f"  ⚠️  字幕失败: {e}")

    for query, start, duration in STICKERS:
        try:
            project.add_cloud_media(query, start_time=start, duration=duration, track_name="Sticker")
            logger.info(f"  ✅ 贴纸: {query}")
        except Exception as e:
            logger.error(f"  ⚠️  贴纸失败: {e}")

    # 6. 保存
    logger.info("[6/6] 保存工程")
    project.save()
    logger.info(f"\n✅ 工程创建完成: {PROJECT_NAME}")
    logger.info(f"   草稿路径: {os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'JianyingPro', 'User Data', 'Projects', 'com.lveditor.draft', PROJECT_NAME)}")
    logger.info("\n手动补充项:")
    logger.info("  - 滤镜: 剪映里手动套统一滤镜")
    logger.info("  - 关键帧: ≥2秒静态图加缩放1.0→1.15（剪映里手动加）")
    logger.info("  - 特效: 粒子/光效等特殊特效（剪映里手动加）")
    logger.info("  - 导出: 剪映里手动导出，或运行 auto_exporter.py")


if __name__ == "__main__":
    main()
