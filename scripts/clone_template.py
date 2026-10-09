"""
AI短视频剪辑 - 模式B：仿制模板 剪映工程创建脚本模板（多轨道原始素材版）

核心原则：只导入原始素材（图片/视频/音频/贴纸/文字），不加任何特效/转场/滤镜/关键帧/蒙版。
所有特效在阶段5通过剪映GUI操作实现。

使用方法：
1. 复制本脚本到项目根目录
2. 修改下方 CONFIG 区域的参数（多轨道配置）
3. 运行: python clone_template.py

依赖：jianying-editor skill, ffmpeg, Python 3.11+
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import subprocess

# ==================== CONFIG（修改这里） ====================

ORIGINAL_VIDEO = "original.mp4"     # 原视频路径（用于提取BGM和裁剪占位片段）
PROJECT_NAME = "仿制_模板"            # 工程名
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clone_output")

# ==================== 多轨道配置（核心） ====================
# 所有素材只放原始件，不加特效/转场/滤镜/关键帧/蒙版

# 主轨道：(文件路径或"shot:N", 起始时间, 持续时长) — 可替换
# "shot:N" 表示从原视频裁剪第N个镜头作为占位
MAIN_TRACK = [
    # ("shot:1", "0s", "2.17s"),
    # ("shot:2", "2.17s", "1s"),
    # ("shot:3", "3.17s", "0.5s"),
    # ("shot:4", "3.67s", "4.36s"),
    # ("shot:5", "8.03s", "3s"),
]

# 画中画轨道（多层）：每层是一个列表，元素为(文件路径或"shot:N", 起始时间, 持续时长) — 可替换
PIP_TRACKS = [
    # [  # 画中画轨道1
    #     ("shot:2", "2.17s", "1s"),
    # ],
    # [  # 画中画轨道2
    #     ("placeholder_phone.png", "0s", "11s"),
    # ],
]

# 文字轨道：(文本, 起始时间, 持续时长, Y位置, 字号, 颜色RGB) — 固定
TEXT_TRACK = [
    # ("对未来的真正慷慨", "0.3s", "2s", -0.7, 10.0, (1, 1, 1)),
    # ("是把一切献给现在", "2.5s", "2s", -0.7, 10.0, (1, 1, 1)),
]

# 贴纸轨道：(文件路径, 起始时间, 持续时长) — 固定（透明PNG/动图）
STICKER_TRACK = [
    # ("phone_frame.png", "0s", "11s"),
]

# 音频轨道（多轨）：BGM/旁白/音效
AUDIO_TRACKS = {
    "BGM": [
        # ("bgm.mp3", "0s", None),  # None表示使用完整时长
    ],
    "Narration": [
        # ("narration.mp3", "0.5s", None),
    ],
    "SFX": [
        # ("sfx_whoosh.mp3", "2.17s", "0.3s"),
    ],
}

# 是否从原视频提取BGM
EXTRACT_BGM_FROM_ORIGINAL = True

# ==================== 特效实现清单（供阶段5 GUI操作） ====================
# 这些不在脚本中实现，只生成清单供剪映GUI操作
EFFECTS_CHECKLIST = [
    # {"type": "转场", "time": "2.17s", "detail": "镜头1→镜头2 叠化 0.4s"},
    # {"type": "滤镜", "time": "全片", "detail": "青灰统一色调"},
    # {"type": "关键帧", "time": "0-2.17s", "detail": "主轨道缩放1.0→1.15"},
    # {"type": "蒙版", "time": "2.17-8.03s", "detail": "画中画1 矩形蒙版 612×1088 居中"},
    # {"type": "特效", "time": "0-11s", "detail": "金色粒子 特效轨道"},
    # {"type": "混合模式", "time": "0-11s", "detail": "画中画2 滤色"},
]

# ==================== 可替换素材标记 ====================
# 发布模板时在"片段设置"中勾选这些素材
REPLACEABLE_MARKERS = [
    # {"track": "主轨道", "time": "0-2.17s", "type": "图片/视频", "suggestion": "建议1080×1920"},
    # {"track": "画中画1", "time": "2.17-3.17s", "type": "图片/视频", "suggestion": "建议720×1280"},
]

# ==================== 镜头列表（用于裁剪占位片段） ====================
SHOTS = [
    # ("0s", "2.17s"),
    # ("2.17s", "3.17s"),
    # ("3.17s", "3.67s"),
    # ("3.67s", "8.03s"),
    # ("8.03s", "11.03s"),
]

# ==================== 初始化（不要修改） ====================

skill_root = next((p for p in [
    os.getenv("JY_SKILL_ROOT", "").strip(),
    r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor",
    r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor",
] if p and os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py"))), None)

if not skill_root:
    raise ImportError("Could not find jianying-editor skill root.")

sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject, draft


def time_to_seconds(t):
    """将时间字符串转为秒"""
    if isinstance(t, (int, float)):
        return float(t)
    t = str(t).strip().lower()
    if t.endswith("s"):
        return float(t[:-1])
    if ":" in t:
        parts = t.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
    return float(t)


def probe_video(path):
    """探测视频分辨率和帧率"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "csv=p=0",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    parts = result.stdout.strip().split(",")
    width = int(parts[0]) if len(parts) > 0 and parts[0] else 1080
    height = int(parts[1]) if len(parts) > 1 and parts[1] else 1920
    return width, height


def cut_shot(input_path, start, end, output_path):
    """按镜头裁剪视频片段，并预处理为画布分辨率+H264+yuv420p+无音频"""
    # 先裁剪
    temp_path = output_path + ".temp.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ss", str(start),
        "-to", str(end),
        "-c", "copy",
        temp_path
    ]
    subprocess.run(cmd, capture_output=True)

    # 再预处理（去除音频，统一编码）
    width, height = probe_video(input_path)
    cmd2 = [
        "ffmpeg", "-y",
        "-i", temp_path,
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
        "-an", "-r", "30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        output_path
    ]
    subprocess.run(cmd2, capture_output=True)

    if os.path.exists(temp_path):
        os.remove(temp_path)
    return output_path


def extract_bgm(input_path, output_path):
    """从原视频提取音轨为mp3"""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "2",
        output_path
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path


def resolve_media(media_ref, shots_dir, shot_cache):
    """解析素材引用：文件路径直接返回，"shot:N"裁剪原视频第N个镜头"""
    if isinstance(media_ref, str) and media_ref.startswith("shot:"):
        shot_idx = int(media_ref.split(":")[1]) - 1
        if shot_idx < len(SHOTS) and shot_idx not in shot_cache:
            start, end = SHOTS[shot_idx]
            output = os.path.join(shots_dir, f"shot_{shot_idx+1}.mp4")
            cut_shot(ORIGINAL_VIDEO, time_to_seconds(start), time_to_seconds(end), output)
            shot_cache[shot_idx] = output
        return shot_cache.get(shot_idx, media_ref)
    return media_ref


# ==================== 主流程 ====================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    shots_dir = os.path.join(OUTPUT_DIR, "shots")
    os.makedirs(shots_dir, exist_ok=True)

    shot_cache = {}  # 缓存已裁剪的镜头

    # 1. 探测原视频
    logger.info(f"[1/7] 探测原视频: {ORIGINAL_VIDEO}")
    width, height = probe_video(ORIGINAL_VIDEO)
    logger.info(f"  分辨率: {width}x{height}")

    # 2. 提取BGM
    bgm_path = None
    if EXTRACT_BGM_FROM_ORIGINAL:
        logger.info("[2/7] 提取原视频BGM")
        bgm_path = os.path.join(OUTPUT_DIR, "bgm.mp3")
        extract_bgm(ORIGINAL_VIDEO, bgm_path)
        if os.path.exists(bgm_path):
            logger.info(f"  ✅ BGM已提取: {bgm_path}")
        else:
            logger.error("  ⚠️  BGM提取失败")

    # 3. 创建剪映工程
    logger.info(f"[3/7] 创建剪映工程: {PROJECT_NAME} ({width}x{height})")
    project = JyProject(PROJECT_NAME, width=width, height=height, overwrite=True)

    # 4. 多轨道导入原始素材
    logger.info("[4/7] 多轨道导入原始素材（不加特效）")

    # 主轨道
    logger.info(f"  主轨道: {len(MAIN_TRACK)} 个素材")
    for media_ref, start, duration in MAIN_TRACK:
        path = resolve_media(media_ref, shots_dir, shot_cache)
        if os.path.exists(path):
            seg = project.add_media_safe(path, start_time=start, duration=duration, track_name="VideoTrack")
            if seg:
                logger.info(f"    ✅ {os.path.basename(path)} ({start}, {duration})")

    # 画中画轨道（多层）
    for pip_idx, pip_clips in enumerate(PIP_TRACKS):
        track_name = f"PIP_{pip_idx+1}"
        logger.info(f"  画中画轨道{pip_idx+1}: {len(pip_clips)} 个素材")
        for media_ref, start, duration in pip_clips:
            path = resolve_media(media_ref, shots_dir, shot_cache)
            if os.path.exists(path):
                seg = project.add_media_safe(path, start_time=start, duration=duration, track_name=track_name)
                if seg:
                    logger.info(f"    ✅ {os.path.basename(path)} ({start}, {duration})")

    # 文字轨道
    logger.info(f"  文字轨道: {len(TEXT_TRACK)} 条字幕")
    for text, start, duration, y, size, color in TEXT_TRACK:
        try:
            project.add_text_simple(
                text, start_time=start, duration=duration,
                clip_settings=draft.ClipSettings(transform_y=y),
                font_size=size, color_rgb=color
            )
            logger.info(f"    ✅ {text[:20]}")
        except Exception as e:
            logger.error(f"    ⚠️  字幕失败: {e}")

    # 贴纸轨道
    logger.info(f"  贴纸轨道: {len(STICKER_TRACK)} 个贴纸")
    for path, start, duration in STICKER_TRACK:
        if os.path.exists(path):
            seg = project.add_media_safe(path, start_time=start, duration=duration, track_name="Sticker")
            if seg:
                logger.info(f"    ✅ {os.path.basename(path)}")

    # 音频轨道（多轨）
    for track_name, clips in AUDIO_TRACKS.items():
        logger.info(f"  音频轨道[{track_name}]: {len(clips)} 个音频")
        for path, start, duration in clips:
            if os.path.exists(path):
                seg = project.add_media_safe(path, start_time=start, duration=duration, track_name=track_name)
                if seg:
                    logger.info(f"    ✅ {os.path.basename(path)}")

    # 如果配置了从原视频提取BGM且BGM轨道为空，自动添加
    if EXTRACT_BGM_FROM_ORIGINAL and bgm_path and not AUDIO_TRACKS.get("BGM"):
        try:
            project.add_media_safe(bgm_path, start_time="0s", track_name="BGM")
            logger.info("    ✅ 原视频BGM自动添加到BGM轨道")
        except Exception as e:
            logger.error(f"    ⚠️  BGM自动添加失败: {e}")

    # 5. 保存工程
    logger.info("[5/7] 保存工程")
    project.save()

    # 6. 生成特效实现清单（供阶段5 GUI操作）
    logger.info("[6/7] 生成特效实现清单")
    effects_path = os.path.join(OUTPUT_DIR, "特效实现清单.md")
    with open(effects_path, "w", encoding="utf-8") as f:
        f.write(f"# {PROJECT_NAME} 特效实现清单\n\n")
        f.write("> 以下特效/转场/滤镜/关键帧/蒙版需在剪映里通过GUI操作实现。\n")
        f.write("> 脚本只导入了原始素材，未添加任何特效。\n\n")
        if EFFECTS_CHECKLIST:
            f.write("| 序号 | 类型 | 时间 | 详情 | 状态 |\n")
            f.write("|---|---|---|---|---|\n")
            for i, eff in enumerate(EFFECTS_CHECKLIST, 1):
                f.write(f"| {i} | {eff['type']} | {eff['time']} | {eff['detail']} | ⬜待实现 |\n")
        else:
            f.write("（暂无特效需要实现）\n")
        f.write("\n## 操作顺序建议\n\n")
        f.write("1. 转场（片段连接处）\n")
        f.write("2. 全片滤镜（最上层轨道）\n")
        f.write("3. 关键帧（缩放/位移/旋转/透明度）\n")
        f.write("4. 蒙版（画中画轨道）\n")
        f.write("5. 画面特效（特效轨道）\n")
        f.write("6. 混合模式（画中画轨道）\n")
        f.write("7. 抠像（画中画轨道）\n")
        f.write("8. 贴纸/文字动画\n")
    logger.info(f"  ✅ 特效实现清单: {effects_path}")

    # 7. 生成模板发布指引 + 替换素材指引
    logger.info("[7/7] 生成模板发布指引和替换素材指引")

    publish_path = os.path.join(OUTPUT_DIR, "模板发布指引.md")
    with open(publish_path, "w", encoding="utf-8") as f:
        f.write(f"# {PROJECT_NAME} 模板发布指引\n\n")
        f.write("## 一、发布前检查\n\n")
        f.write("- [ ] 所有特效已按《特效实现清单》完成\n")
        f.write("- [ ] 播放预览无异常\n")
        f.write("- [ ] 音频同步正常\n")
        f.write("- [ ] 可替换素材已确认\n\n")
        f.write("## 二、发布步骤\n\n")
        f.write("1. 剪映里点击右上角「导出」\n")
        f.write("2. 导出完成后点击「发布模板」\n")
        f.write("3. 填写模板标题、描述、话题\n")
        f.write("4. 设置模板封面\n")
        f.write("5. 打开「片段设置」，勾选以下可替换素材：\n\n")
        if REPLACEABLE_MARKERS:
            for marker in REPLACEABLE_MARKERS:
                f.write(f"   - [{marker['track']}] {marker['time']} ({marker['type']})\n")
        else:
            f.write("   （请在剪映里手动确认可替换素材）\n")
        f.write("\n6. 首发声明（如素材为原创）\n")
        f.write("7. 付费设置（免费/付费解锁）\n")
        f.write("8. 发布\n\n")
        f.write("## 三、可替换素材清单\n\n")
        f.write("| 轨道 | 时间 | 类型 | 建议尺寸 |\n")
        f.write("|---|---|---|---|\n")
        if REPLACEABLE_MARKERS:
            for marker in REPLACEABLE_MARKERS:
                f.write(f"| {marker['track']} | {marker['time']} | {marker['type']} | {marker.get('suggestion', '-')} |\n")
        else:
            f.write("| 主轨道 | 全片 | 图片/视频 | 画布分辨率 |\n")
        f.write("\n## 四、固定元素（不可替换）\n\n")
        f.write("- 文字/字幕\n")
        f.write("- 贴纸\n")
        f.write("- 特效/滤镜\n")
        f.write("- 转场\n")
        f.write("- 关键帧/蒙版\n")
        f.write("- BGM/音效\n")

    replace_path = os.path.join(OUTPUT_DIR, "替换素材指引.md")
    with open(replace_path, "w", encoding="utf-8") as f:
        f.write(f"# {PROJECT_NAME} 替换素材指引（给模板使用者）\n\n")
        f.write("## 使用说明\n\n")
        f.write("打开模板后，按提示依次选择图片或视频替换即可。\n")
        f.write("替换后特效、转场、滤镜、文字、音乐自动保留。\n\n")
        f.write("## 需要准备的素材\n\n")
        if REPLACEABLE_MARKERS:
            f.write(f"共需要 **{len(REPLACEABLE_MARKERS)}** 个素材：\n\n")
            f.write("| 序号 | 类型 | 建议尺寸 | 出现位置 |\n")
            f.write("|---|---|---|---|\n")
            for i, marker in enumerate(REPLACEABLE_MARKERS, 1):
                f.write(f"| {i} | {marker['type']} | {marker.get('suggestion', '-')} | {marker['time']} |\n")
        else:
            f.write("请在模板中查看需要替换的素材数量。\n")
        f.write("\n## 注意事项\n\n")
        f.write("- 长视频会自动裁剪，建议选择精彩部分\n")
        f.write("- 图片建议提前裁剪到模板比例（避免关键内容被裁掉）\n")
        f.write("- 替换后可预览效果，满意后导出\n")

    logger.info(f"  ✅ 模板发布指引: {publish_path}")
    logger.info(f"  ✅ 替换素材指引: {replace_path}")

    # 完成
    logger.info(f"\n{'='*50}")
    logger.info(f"✅ 仿制草稿创建完成: {PROJECT_NAME}")
    logger.info(f"   工程分辨率: {width}x{height}")
    logger.info(f"   输出目录: {OUTPUT_DIR}")
    logger.info(f"\n生成的文件:")
    logger.info(f"  - 特效实现清单: {effects_path}")
    logger.info(f"  - 模板发布指引: {publish_path}")
    logger.info(f"  - 替换素材指引: {replace_path}")
    if os.path.exists(shots_dir):
        logger.info(f"  - 占位镜头片段: {shots_dir}/")
    logger.info(f"\n下一步:")
    logger.info(f"  1. 在剪映里打开工程「{PROJECT_NAME}」")
    logger.info(f"  2. 按《特效实现清单》通过GUI操作添加特效/转场/滤镜/关键帧/蒙版")
    logger.info(f"  3. 预览确认效果")
    logger.info(f"  4. 按《模板发布指引》发布模板")


if __name__ == "__main__":
    main()
