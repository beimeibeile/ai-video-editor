"""
easy_build.py — 一键成片入口（创意引擎增强版）
新手友好：上传素材+指定主题，自动生成专业分镜+剪映工程

使用方法：
    python easy_build.py --input ./素材 --theme 国风 --output 我的视频

功能：
    1. 自动扫描素材（图片+视频）
    2. 创意引擎生成专业分镜脚本（景别/运镜/转场/字幕/音效/调色）
    3. 根据分镜导入素材、添加关键帧运镜
    4. 自动添加转场（应用在前一个片段上）
    5. 自动添加艺术字幕（钩子+分镜字幕）
    6. 自动添加BGM和音效
    7. 输出剪映工程草稿 + 分镜脚本(JSON/MD)
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

from capabilities.cap_keyframe_engine import auto_keyframe_for_still_image, add_ken_burns
from capabilities.cap_subtitle_designer import add_artistic_subtitle, add_hook_title
from capabilities.cap_effect_library import get_style_preset, auto_add_transitions, add_transition
from capabilities.cap_creative_engine import CreativeEngine, Storyboard, Shot


# ==================== 素材扫描 ====================
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def scan_materials(input_dir: str, recursive: bool = True) -> tuple:
    """扫描素材目录，返回(图片列表, 视频列表)"""
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


def match_materials_to_shots(images: list, videos: list, num_shots: int) -> list:
    """
    将素材匹配到分镜镜头
    优先使用图片，图片不够时用视频补充
    """
    all_materials = [{"path": p, "type": "image"} for p in images] + \
                    [{"path": p, "type": "video"} for p in videos]

    matched = []
    for i in range(num_shots):
        if i < len(all_materials):
            matched.append(all_materials[i])
        elif all_materials:
            # 素材不够时循环使用
            matched.append(all_materials[i % len(all_materials)])
        else:
            matched.append(None)

    return matched


# ==================== 主流程 ====================
def easy_build(input_dir: str, theme: str = "极简", output_name: str = None,
               width: int = 1080, height: int = 1920,
               hook_text: str = None, bgm_query: str = None,
               num_shots: int = None, output_dir: str = None):
    """
    一键成片主函数（创意引擎增强版）

    Args:
        input_dir: 素材目录
        theme: 主题（国风/治愈/卡点/电影/赛博/极简/复古）
        output_name: 输出工程名
        width: 画布宽
        height: 画布高
        hook_text: 开篇钩子文案
        bgm_query: BGM关键词
        num_shots: 镜头数量（默认根据素材数量自动确定）
        output_dir: 分镜脚本输出目录
    """
    # 1. 扫描素材
    print(f"[1/8] 扫描素材: {input_dir}")
    images, videos = scan_materials(input_dir)
    print(f"  图片: {len(images)}张, 视频: {len(videos)}个")

    if not images and not videos:
        raise ValueError("素材目录中没有找到图片或视频")

    # 确定镜头数量
    if num_shots is None:
        total = len(images) + len(videos)
        num_shots = min(total, 8) if total > 0 else 6
        num_shots = max(num_shots, 3)

    # 2. 创意引擎生成分镜
    print(f"[2/8] 创意引擎生成分镜: {theme}主题, {num_shots}个镜头")
    engine = CreativeEngine()
    storyboard = engine.generate_storyboard(
        theme=theme,
        num_shots=num_shots,
        title=output_name or f"{theme}主题视频",
        hook=hook_text,
    )

    # 输出分镜脚本
    if output_dir is None:
        output_dir = str(SKILL_ROOT / "output" / (output_name or f"{theme}_一键成片"))
    os.makedirs(output_dir, exist_ok=True)
    storyboard.save(os.path.join(output_dir, "storyboard.json"), fmt="json")
    storyboard.save(os.path.join(output_dir, "storyboard.md"), fmt="md")
    print(f"  ✅ 分镜脚本已保存: {output_dir}")
    print(f"  节奏: {storyboard.rhythm}, 总时长: {storyboard.total_duration:.1f}秒")

    # 改进建议
    suggestions = engine.get_improvement_suggestions(storyboard)
    if suggestions:
        print("  💡 创意建议:")
        for s in suggestions[:3]:
            print(f"     - {s}")

    # 3. 匹配素材到镜头
    print("[3/8] 匹配素材到镜头")
    matched = match_materials_to_shots(images, videos, num_shots)
    for i, m in enumerate(matched):
        if m:
            print(f"  镜头{i+1}: {Path(m['path']).name} ({m['type']})")

    # 4. 匹配风格
    print(f"[4/8] 匹配风格: {theme}")
    style = get_style_preset(theme)

    # 5. 创建工程
    project_name = output_name or f"{theme}_一键成片"
    print(f"[5/8] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 6. 导入素材+根据分镜添加运镜
    print("[6/8] 导入素材并添加分镜运镜")
    segments = []
    current_time = 0  # 微秒

    for i, shot in enumerate(storyboard.shots):
        material = matched[i] if i < len(matched) else None
        if not material:
            continue

        # 使用整数微秒避免浮点数精度问题（3.6s会被解析为3599999us导致重叠）
        duration_us = int(round(shot.duration * 1000000))
        # 确保起始时间与前一片段不重叠（加1us缓冲）
        start_us = current_time + 1 if current_time > 0 else 0

        try:
            seg = project.add_media_safe(
                material["path"],
                start_time=start_us,
                duration=duration_us
            )
            if seg:
                segments.append(seg)

                # 根据分镜的运镜方式添加关键帧
                if material["type"] == "image":
                    add_ken_burns(
                        seg, current_time, duration_us,
                        move_type=shot.camera_move,
                        intensity=1.0
                    )

                print(f"  ✅ [{i+1}] {Path(material['path']).name} "
                      f"({shot.duration:.1f}s, {shot.shot_type}, {shot.camera_move})")
        except Exception as e:
            print(f"  ⚠️  [{i+1}] 导入失败: {Path(material['path']).name} - {e}")

        current_time += duration_us

    total_duration = current_time / 1000000

    # 7. 添加转场+字幕+BGM
    print("[7/8] 添加转场/字幕/BGM")

    # 转场（根据分镜的转场序列，应用在前一个片段上）
    if len(segments) > 1:
        transition_count = 0
        for i in range(len(segments) - 1):
            shot = storyboard.shots[i] if i < len(storyboard.shots) else None
            trans_type = shot.transition_out if shot else style["transition"]
            if trans_type and trans_type != "none":
                try:
                    add_transition(project, segments[i], transition_type=trans_type)
                    transition_count += 1
                except Exception:
                    pass
        if transition_count == 0:
            auto_add_transitions(project, segments, transition_type=style["transition"])
            transition_count = len(segments) - 1
        print(f"  ✅ 转场: {transition_count}个")

    # 钩子标题
    hook = storyboard.hook or f"{theme}｜一键成片"
    add_hook_title(project, hook, start_time="0s", duration="2.5s", style=style["subtitle"])
    print(f"  ✅ 钩子标题: {hook}")

    # 分镜字幕（每个镜头的字幕）
    subtitle_count = 0
    for i, shot in enumerate(storyboard.shots):
        if shot.subtitle and i < len(segments):
            try:
                start_us = sum(int(round(s.duration * 1000000)) for s in storyboard.shots[:i])
                duration_us = int(round(shot.duration * 1000000))
                project.add_text_simple(
                    shot.subtitle,
                    start_time=start_us,
                    duration=duration_us,
                    font_size=6.0,
                    color_rgb=(1.0, 1.0, 1.0),
                    clip_settings=draft.ClipSettings(transform_y=-0.7),
                    anim_in="渐显",
                    track_name="ShotSubtitle",
                )
                subtitle_count += 1
            except Exception:
                pass
    if subtitle_count > 0:
        print(f"  ✅ 分镜字幕: {subtitle_count}条")

    # BGM
    bgm_kw = bgm_query or style["bgm"]
    try:
        project.add_cloud_music(bgm_kw, start_time="0s", duration=f"{total_duration:.0f}s", track_name="BGM")
        print(f"  ✅ BGM: {bgm_kw}")
    except Exception as e:
        print(f"  ⚠️  BGM添加失败: {e}")

    # 开头音效
    try:
        project.add_cloud_media("叮", start_time="0s", duration="0.5s", track_name="SFX")
        print(f"  ✅ 开头音效")
    except Exception:
        pass

    # 8. 保存
    print("[8/8] 保存工程")
    project.save()

    draft_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "JianyingPro",
                               "User Data", "Projects", "com.lveditor.draft", project_name)

    print(f"\n{'='*50}")
    print(f"✅ 一键成片完成！")
    print(f"   工程名: {project_name}")
    print(f"   片段数: {len(segments)}")
    print(f"   时长: 约{total_duration:.0f}秒")
    print(f"   风格: {theme}")
    print(f"   节奏: {storyboard.rhythm}")
    print(f"   草稿路径: {draft_path}")
    print(f"   分镜脚本: {output_dir}")
    print(f"\n💡 后续可在剪映中手动优化：")
    print(f"   - 套统一滤镜（推荐: {style['filter']}）")
    print(f"   - 调整字幕位置和内容")
    print(f"   - 导出视频")
    print(f"{'='*50}")

    return project_name, draft_path, storyboard


# ==================== CLI入口 ====================
def main():
    parser = argparse.ArgumentParser(description="AI Video Editor - 一键成片（创意引擎增强版）")
    parser.add_argument("--input", "-i", required=True, help="素材目录")
    parser.add_argument("--theme", "-t", default="极简",
                        choices=["国风", "治愈", "卡点", "电影", "赛博", "极简", "复古"],
                        help="视频主题风格")
    parser.add_argument("--output", "-o", default=None, help="输出工程名")
    parser.add_argument("--width", type=int, default=1080, help="画布宽")
    parser.add_argument("--height", type=int, default=1920, help="画布高")
    parser.add_argument("--hook", default=None, help="开篇钩子文案")
    parser.add_argument("--bgm", default=None, help="BGM关键词")
    parser.add_argument("--shots", type=int, default=None, help="镜头数量")
    parser.add_argument("--storyboard-dir", default=None, help="分镜脚本输出目录")

    args = parser.parse_args()

    easy_build(
        input_dir=args.input,
        theme=args.theme,
        output_name=args.output,
        width=args.width,
        height=args.height,
        hook_text=args.hook,
        bgm_query=args.bgm,
        num_shots=args.shots,
        output_dir=args.storyboard_dir,
    )


if __name__ == "__main__":
    main()
