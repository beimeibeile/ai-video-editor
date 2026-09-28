"""
easy_build.py — 一键成片入口
新手友好：上传素材+指定主题，自动生成剪映工程

使用方法：
    python easy_build.py --input ./素材 --theme 国风 --output 我的视频

功能：
    1. 自动扫描素材（图片+视频）
    2. 根据主题匹配风格（转场/滤镜/字幕/BGM）
    3. 自动生成分镜（合理时长）
    4. 自动添加转场
    5. 自动添加关键帧运镜（Ken Burns）
    6. 自动添加艺术字幕
    7. 自动添加BGM
    8. 输出剪映工程草稿
"""
import os
import sys
import argparse
from pathlib import Path

# ==================== 路径配置 ====================
SKILL_ROOT = Path(__file__).parent
JY_SKILL_ROOT = Path(r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor")

# 确保可导入
sys.path.insert(0, str(JY_SKILL_ROOT / "scripts"))
sys.path.insert(0, str(SKILL_ROOT))

from jy_wrapper import JyProject
import pyJianYingDraft as draft

from capabilities.cap_keyframe_engine import auto_keyframe_for_still_image, add_fade_in_out
from capabilities.cap_subtitle_designer import add_artistic_subtitle, add_hook_title
from capabilities.cap_effect_library import get_style_preset, auto_add_transitions, add_transition
from capabilities.cap_audio_designer import add_bgm, add_sfx, match_bgm


# ==================== 素材扫描 ====================
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def scan_materials(input_dir: str, recursive: bool = True) -> tuple:
    """
    扫描素材目录，返回(图片列表, 视频列表)
    按文件名排序，支持递归扫描子目录

    Args:
        input_dir: 素材目录
        recursive: 是否递归扫描子目录
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"素材目录不存在: {input_dir}")

    images = []
    videos = []

    if recursive:
        files = sorted(input_path.rglob("*"))
    else:
        files = sorted(input_path.iterdir())

    for f in files:
        if f.is_file():
            ext = f.suffix.lower()
            if ext in IMAGE_EXTS:
                images.append(str(f))
            elif ext in VIDEO_EXTS:
                videos.append(str(f))

    return images, videos


# ==================== 分镜生成 ====================
def generate_storyboard(images: list, videos: list, theme: str) -> list:
    """
    生成分镜表

    Returns:
        [{"path": ..., "type": "image"/"video", "duration": "3s", "index": 0}, ...]
    """
    clips = []
    idx = 0

    # 图片：每张2.5-3.5秒
    for img in images:
        duration = "3s" if len(images) <= 6 else "2.5s"
        clips.append({"path": img, "type": "image", "duration": duration, "index": idx})
        idx += 1

    # 视频：每个3-5秒（取前几秒）
    for vid in videos:
        clips.append({"path": vid, "type": "video", "duration": "4s", "index": idx})
        idx += 1

    return clips


# ==================== 主流程 ====================
def easy_build(input_dir: str, theme: str = "极简", output_name: str = None,
               width: int = 1080, height: int = 1920,
               hook_text: str = None, bgm_query: str = None):
    """
    一键成片主函数

    Args:
        input_dir: 素材目录
        theme: 主题（国风/治愈/卡点/电影/赛博/极简/复古）
        output_name: 输出工程名（默认：主题_一键成片）
        width: 画布宽
        height: 画布高
        hook_text: 开篇钩子文案（默认根据主题生成）
        bgm_query: BGM关键词（默认根据主题匹配）
    """
    # 1. 扫描素材
    print(f"[1/7] 扫描素材: {input_dir}")
    images, videos = scan_materials(input_dir)
    print(f"  图片: {len(images)}张, 视频: {len(videos)}个")

    if not images and not videos:
        raise ValueError("素材目录中没有找到图片或视频")

    # 2. 匹配风格
    print(f"[2/7] 匹配风格: {theme}")
    style = get_style_preset(theme)
    print(f"  转场: {style['transition']}, 滤镜: {style['filter']}, 字幕: {style['subtitle']}, BGM: {style['bgm']}")

    # 3. 生成分镜
    print("[3/7] 生成分镜")
    clips = generate_storyboard(images, videos, theme)
    total_duration = len(clips) * 3
    print(f"  共{len(clips)}个片段，约{total_duration}秒")

    # 4. 创建工程
    project_name = output_name or f"{theme}_一键成片"
    print(f"[4/7] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 5. 导入素材+添加关键帧
    print("[5/7] 导入素材并添加运镜")
    segments = []
    current_time = 0  # 微秒

    for clip in clips:
        # 计算时间
        duration_us = 3000000 if clip["duration"] == "3s" else 2500000
        start_str = f"{current_time / 1000000}s"

        # 导入素材
        try:
            seg = project.add_media_safe(
                clip["path"],
                start_time=start_str,
                duration=clip["duration"]
            )
            if seg:
                segments.append(seg)

                # 静态图片添加关键帧运镜
                if clip["type"] == "image":
                    auto_keyframe_for_still_image(seg, current_time, duration_us, index=clip["index"])

                print(f"  ✅ [{clip['index']+1}] {Path(clip['path']).name} ({clip['duration']})")
        except Exception as e:
            print(f"  ⚠️  [{clip['index']+1}] 导入失败: {Path(clip['path']).name} - {e}")

        current_time += duration_us

    # 6. 添加转场+字幕+BGM
    print("[6/7] 添加转场/字幕/BGM")

    # 转场
    if len(segments) > 1:
        auto_add_transitions(project, segments[1:], transition_type=style["transition"])
        print(f"  ✅ 转场: {style['transition']} x{len(segments)-1}")

    # 钩子标题
    hook = hook_text or f"{theme}｜一键成片"
    add_hook_title(project, hook, start_time="0s", duration="2.5s", style=style["subtitle"])
    print(f"  ✅ 钩子标题: {hook}")

    # BGM（使用音频设计模块自动匹配）
    bgm_kw = bgm_query or style["bgm"]
    bgm_result = add_bgm(project, theme, start_time="0s", duration=f"{total_duration}s")
    if bgm_result:
        print(f"  ✅ BGM: {bgm_result}")
    else:
        print(f"  ⚠️  BGM添加失败（可手动补）")

    # 开头强调音效
    sfx_result = add_sfx(project, "强调", start_time="0s", duration="0.5s")
    if sfx_result:
        print(f"  ✅ 开头音效: {sfx_result}")

    # 7. 保存
    print("[7/7] 保存工程")
    project.save()

    draft_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "JianyingPro",
                               "User Data", "Projects", "com.lveditor.draft", project_name)

    print(f"\n{'='*50}")
    print(f"✅ 一键成片完成！")
    print(f"   工程名: {project_name}")
    print(f"   片段数: {len(segments)}")
    print(f"   时长: 约{total_duration}秒")
    print(f"   风格: {theme}")
    print(f"   草稿路径: {draft_path}")
    print(f"\n💡 后续可在剪映中手动优化：")
    print(f"   - 套统一滤镜（推荐: {style['filter']}）")
    print(f"   - 调整字幕位置和内容")
    print(f"   - 导出视频")
    print(f"{'='*50}")

    return project_name, draft_path


# ==================== CLI入口 ====================
def main():
    parser = argparse.ArgumentParser(description="AI Video Editor - 一键成片")
    parser.add_argument("--input", "-i", required=True, help="素材目录")
    parser.add_argument("--theme", "-t", default="极简",
                        choices=["国风", "治愈", "卡点", "电影", "赛博", "极简", "复古"],
                        help="视频主题风格")
    parser.add_argument("--output", "-o", default=None, help="输出工程名")
    parser.add_argument("--width", type=int, default=1080, help="画布宽")
    parser.add_argument("--height", type=int, default=1920, help="画布高")
    parser.add_argument("--hook", default=None, help="开篇钩子文案")
    parser.add_argument("--bgm", default=None, help="BGM关键词")

    args = parser.parse_args()

    easy_build(
        input_dir=args.input,
        theme=args.theme,
        output_name=args.output,
        width=args.width,
        height=args.height,
        hook_text=args.hook,
        bgm_query=args.bgm,
    )


if __name__ == "__main__":
    main()
