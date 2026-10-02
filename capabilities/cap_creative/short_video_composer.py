"""
短视频碎片剪辑合成器 v1.0
==========================
基于真实素材的碎片剪辑组合再创作：
- 素材导入（视频/图片混合）
- BGM卡点检测与自动切分
- 转场自动添加（叠化/闪白/滑动/模糊）
- 特效应用（基于标签匹配）
- 文字动画（字幕条/大字报/文字擦开）
- 多轨道剪映工程合成

与short_video_pipeline的区别：
- pipeline = 标签驱动的全自动生成（无素材也能出片，用占位/生成素材）
- composer = 基于真实素材的碎片剪辑合成（用户提供素材，自动卡点剪辑）
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

# 路径配置
SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
JY_SKILL = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor"
FFMPEG_DIR = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin"

sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities", "cap_creative"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))


@dataclass
class ClipSegment:
    """素材片段"""
    path: str
    start_time: float = 0.0  # 在时间线上的起始时间（秒）
    duration: float = 3.0    # 片段持续时间（秒）
    source_start: float = 0.0  # 素材内的起始点（秒）
    media_type: str = "video"  # video/image
    transition_in: str = ""    # 入场转场
    transition_out: str = ""   # 出场转场
    camera_move: str = "缓推"  # 运镜类型
    effect: str = ""           # 特效名称


@dataclass
class TextOverlay:
    """文字叠加层"""
    text: str
    start_time: float = 0.0
    duration: float = 3.0
    style: str = "subtitle_bar"  # subtitle_bar/big_title/text_wipe/character_card
    position_y: float = -0.7  # -1~1, 0=中心
    font_size: float = 10.0
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    anim_in: str = "弹入"


class ShortVideoComposer:
    """短视频碎片剪辑合成器"""

    # 转场类型映射
    TRANSITION_MAP = {
        "叠化": "叠化",
        "闪白": "渐隐",
        "闪黑": "渐隐",
        "左滑": "向左滑动",
        "右滑": "向右滑动",
        "上滑": "向上滑动",
        "下滑": "向下滑动",
        "模糊": "模糊",
        "缩放": "放大",
    }

    # 运镜映射
    CAMERA_MOVE_MAP = {
        "快推": ("zoom_in", 0.2),
        "缓推": ("zoom_in", 0.08),
        "缓拉": ("zoom_out", 0.08),
        "快拉": ("zoom_out", 0.15),
        "左摇": ("pan_left", 0.1),
        "右摇": ("pan_right", 0.1),
        "手持": ("handheld", 0.1),
        "呼吸": ("pulse", 0.05),
        "固定": ("pulse", 0.02),
    }

    def __init__(self, project_name: str = "ShortVideo",
                 width: int = 1080, height: int = 1920,
                 output_dir: str = None):
        self.project_name = project_name
        self.width = width
        self.height = height
        if output_dir is None:
            output_dir = os.path.join(SKILL_ROOT, "capabilities", "cap_creative", "composer_output")
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.clips: List[ClipSegment] = []
        self.texts: List[TextOverlay] = []
        self.bgm_path: str = ""
        self._project = None

    def add_clip(self, path: str, duration: float = 3.0,
                 source_start: float = 0.0, transition_in: str = "",
                 camera_move: str = "缓推", effect: str = "") -> ClipSegment:
        """添加素材片段"""
        media_type = "image" if path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) else "video"
        clip = ClipSegment(
            path=path,
            duration=duration,
            source_start=source_start,
            media_type=media_type,
            transition_in=transition_in,
            camera_move=camera_move,
            effect=effect,
        )
        self.clips.append(clip)
        return clip

    def add_text(self, text: str, start_time: float = 0.0,
                 duration: float = 3.0, style: str = "subtitle_bar",
                 font_size: float = 10.0, position_y: float = -0.7,
                 anim_in: str = "弹入") -> TextOverlay:
        """添加文字叠加"""
        t = TextOverlay(
            text=text,
            start_time=start_time,
            duration=duration,
            style=style,
            font_size=font_size,
            position_y=position_y,
            anim_in=anim_in,
        )
        self.texts.append(t)
        return t

    def set_bgm(self, bgm_path: str):
        """设置BGM"""
        self.bgm_path = bgm_path

    def auto_arrange_by_beats(self, beats: List[float], total_duration: float = None):
        """
        根据节拍点自动排列素材
        Args:
            beats: 节拍时间点列表（秒）
            total_duration: 总时长（秒），None则用最后一个节拍
        """
        if not self.clips:
            return

        if total_duration is None:
            total_duration = beats[-1] if beats else sum(c.duration for c in self.clips)

        # 生成切点：节拍点 + 起止
        cut_points = [0.0] + [b for b in beats if 0 < b < total_duration] + [total_duration]
        cut_points = sorted(set(cut_points))
        num_segments = len(cut_points) - 1

        # 素材不足时循环复制
        if len(self.clips) < num_segments:
            original = list(self.clips)
            while len(self.clips) < num_segments:
                src = original[len(self.clips) % len(original)]
                self.clips.append(ClipSegment(
                    path=src.path,
                    media_type=src.media_type,
                    transition_in=src.transition_in,
                    camera_move=src.camera_move,
                    effect=src.effect,
                ))

        # 分配素材到每个时间段
        for i in range(num_segments):
            seg_start = cut_points[i]
            seg_end = cut_points[i + 1]
            self.clips[i].start_time = seg_start
            self.clips[i].duration = seg_end - seg_start

            # 转场：非第一个片段添加入场转场
            if i > 0:
                self.clips[i].transition_in = self.clips[i].transition_in or "叠化"

        print(f"  ✅ 自动排列: {len(self.clips)}个片段, {num_segments}个切点")

    def detect_beats(self, audio_path: str, threshold: float = 0.6,
                     min_interval: float = 0.3) -> List[float]:
        """
        从音频检测节拍点
        Returns: 节拍时间点列表（秒）
        """
        try:
            from auto_beat import generate_beat_timeline
            result = generate_beat_timeline(audio_path, threshold=threshold, min_interval=min_interval)
            return result.get("beats", [])
        except Exception as e:
            print(f"  ⚠️ 节拍检测失败: {e}")
            return []

    def build(self) -> Dict[str, Any]:
        """
        构建剪映工程
        Returns: 工程信息字典
        """
        print(f"\n{'='*60}")
        print(f"短视频碎片剪辑合成器")
        print(f"{'='*60}")
        print(f"工程: {self.project_name} ({self.width}x{self.height})")
        print(f"素材: {len(self.clips)}个, 文字: {len(self.texts)}个, BGM: {'有' if self.bgm_path else '无'}")

        try:
            from jy_wrapper import JyProject
            import pyJianYingDraft as draft
        except ImportError:
            return {"status": "failed", "reason": "jianying-editor不可用"}

        try:
            # 1. 创建工程
            print(f"\n[1/4] 创建工程...")
            self._project = JyProject(self.project_name, width=self.width, height=self.height, overwrite=True)

            # 2. 添加素材片段
            print(f"[2/4] 添加素材片段...")
            segments = []
            current_time = 0.0
            for i, clip in enumerate(self.clips):
                if not os.path.exists(clip.path):
                    print(f"  ⚠️ 素材不存在: {clip.path}")
                    continue

                # 自动计算起始时间（如果未设置）
                start = clip.start_time if clip.start_time > 0 else current_time

                seg = self._project.add_media_safe(
                    clip.path,
                    start_time=f"{start:.2f}s",
                    duration=f"{clip.duration:.2f}s",
                    track_name="VideoMain",
                )
                if seg:
                    segments.append(seg)
                    current_time = start + clip.duration
                    # 运镜
                    self._apply_camera_move(seg, clip)
                    # 转场
                    if clip.transition_in and i > 0:
                        self._apply_transition(seg, clip.transition_in)

            print(f"  ✅ {len(segments)}/{len(self.clips)}个片段已添加")

            # 3. 添加文字
            print(f"[3/4] 添加文字叠加...")
            text_count = 0
            for t in self.texts:
                self._add_text_overlay(t)
                text_count += 1
            print(f"  ✅ {text_count}个文字已添加")

            # 4. 添加BGM
            print(f"[4/4] 添加BGM...")
            if self.bgm_path and os.path.exists(self.bgm_path):
                try:
                    self._project.add_audio_safe(self.bgm_path, start_time="0s", track_name="BGM")
                    print(f"  ✅ BGM已添加")
                except Exception as e:
                    print(f"  ⚠️ BGM添加失败: {e}")

            # 保存
            result = self._project.save()
            draft_path = result.get("draft_path", "")

            # 计算实际总时长（使用排列后的时间）
            actual_end = 0.0
            t = 0.0
            for c in self.clips:
                start = c.start_time if c.start_time > 0 else t
                actual_end = max(actual_end, start + c.duration)
                t = start + c.duration

            print(f"\n✅ 工程构建完成")
            print(f"   草稿: {draft_path}")
            print(f"   时长: {actual_end:.1f}s")
            print(f"   片段: {len(segments)}个, 文字: {text_count}个")

            return {
                "status": "success",
                "project_name": self.project_name,
                "draft_path": draft_path,
                "duration": actual_end,
                "clips": len(segments),
                "texts": text_count,
                "bgm": self.bgm_path,
            }

        except Exception as e:
            print(f"  ❌ 工程构建失败: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "failed", "reason": str(e)}

    def _apply_camera_move(self, seg, clip: ClipSegment):
        """应用运镜"""
        move_type, intensity = self.CAMERA_MOVE_MAP.get(clip.camera_move, ("zoom_in", 0.08))
        try:
            from camera_moves import add_camera_move
            add_camera_move(seg, move_type, int(clip.duration * 1e6), intensity)
        except Exception:
            pass

    def _apply_transition(self, seg, transition_name: str):
        """应用转场"""
        try:
            import pyJianYingDraft as draft
            trans_type = self.TRANSITION_MAP.get(transition_name, "叠化")
            trans_enum = getattr(draft.TransitionType, trans_type, draft.TransitionType.叠化)
            seg.add_transition(trans_enum, duration=int(0.3 * 1e6))
        except Exception:
            pass

    def _add_text_overlay(self, t: TextOverlay):
        """添加文字叠加层"""
        try:
            import pyJianYingDraft as draft
            style = draft.TextStyle(size=t.font_size, color=t.color)

            if t.style == "big_title":
                # 大字报：大字号居中
                style = draft.TextStyle(size=t.font_size * 1.5, color=t.color)
                seg = self._project.add_text_simple(
                    text=t.text,
                    start_time=f"{t.start_time:.2f}s",
                    duration=f"{t.duration:.2f}s",
                    track_name="BigTitle",
                    style=style,
                    anim_in=t.anim_in,
                )
                if seg:
                    seg.add_keyframe(draft.KeyframeProperty.position_y, 0, t.position_y)

            elif t.style == "text_wipe":
                # 文字擦开：使用蒙版关键帧
                seg = self._project.add_text_simple(
                    text=t.text,
                    start_time=f"{t.start_time:.2f}s",
                    duration=f"{t.duration:.2f}s",
                    track_name="TextWipe",
                    style=style,
                )
                if seg:
                    try:
                        from mask_keyframe import apply_mask_keyframe
                        wipe_dur = int(t.duration * 0.4 * 1e6)
                        apply_mask_keyframe(self._project, seg, "size_x", 0, 0.001, "EASE_OUT")
                        apply_mask_keyframe(self._project, seg, "size_x", wipe_dur, 1.0, "EASE_OUT")
                        apply_mask_keyframe(self._project, seg, "position_x", 0, -1.0, "EASE_OUT")
                        apply_mask_keyframe(self._project, seg, "position_x", wipe_dur, 0.0, "EASE_OUT")
                    except Exception:
                        pass

            else:
                # 默认字幕条
                seg = self._project.add_text_simple(
                    text=t.text,
                    start_time=f"{t.start_time:.2f}s",
                    duration=f"{t.duration:.2f}s",
                    track_name="Subtitle",
                    style=style,
                    anim_in=t.anim_in,
                )
                if seg:
                    seg.add_keyframe(draft.KeyframeProperty.position_y, 0, t.position_y)

        except Exception as e:
            print(f"  ⚠️ 文字添加失败: {e}")

    def export_report(self, output_path: str = None) -> str:
        """导出合成报告"""
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"{self.project_name}_report.json")

        report = {
            "project_name": self.project_name,
            "resolution": f"{self.width}x{self.height}",
            "clips": [
                {"path": c.path, "start": c.start_time, "duration": c.duration,
                 "type": c.media_type, "transition": c.transition_in, "camera": c.camera_move}
                for c in self.clips
            ],
            "texts": [
                {"text": t.text, "start": t.start_time, "duration": t.duration, "style": t.style}
                for t in self.texts
            ],
            "bgm": self.bgm_path,
            "total_duration": max((c.start_time + c.duration) for c in self.clips) if self.clips else 0,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return output_path


# ===== 便捷函数 =====

def compose_from_materials(
    material_paths: List[str],
    bgm_path: str = "",
    text_lines: List[str] = None,
    project_name: str = "ShortVideo",
    duration: float = 15.0,
    use_beat_detection: bool = True,
    transition: str = "叠化",
    camera_move: str = "缓推",
    width: int = 1080,
    height: int = 1920,
) -> Dict[str, Any]:
    """
    便捷函数：从素材列表一键合成短视频

    Args:
        material_paths: 素材路径列表（视频/图片混合）
        bgm_path: BGM路径
        text_lines: 文字内容列表
        project_name: 工程名
        duration: 目标时长
        use_beat_detection: 是否使用BGM卡点检测
        transition: 默认转场类型
        camera_move: 默认运镜类型
        width/height: 分辨率

    Returns:
        合成结果字典
    """
    composer = ShortVideoComposer(project_name, width, height)

    # 计算每个素材的平均时长
    avg_dur = duration / max(len(material_paths), 1)

    # 添加素材
    for i, path in enumerate(material_paths):
        composer.add_clip(
            path=path,
            duration=avg_dur,
            transition_in=transition if i > 0 else "",
            camera_move=camera_move,
        )

    # 卡点检测
    if use_beat_detection and bgm_path and os.path.exists(bgm_path):
        print(f"\n检测BGM节拍...")
        beats = composer.detect_beats(bgm_path)
        if beats:
            composer.auto_arrange_by_beats(beats, duration)
        else:
            # 无节拍则均匀排列
            for i, clip in enumerate(composer.clips):
                clip.start_time = i * avg_dur
    else:
        # 均匀排列
        for i, clip in enumerate(composer.clips):
            clip.start_time = i * avg_dur

    # 添加文字
    if text_lines:
        text_dur = duration / len(text_lines)
        for i, text in enumerate(text_lines):
            composer.add_text(
                text=text,
                start_time=i * text_dur,
                duration=text_dur,
                style="subtitle_bar",
                position_y=-0.7,
            )

    # 设置BGM
    if bgm_path:
        composer.set_bgm(bgm_path)

    # 构建工程
    result = composer.build()

    # 导出报告
    composer.export_report()

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("短视频碎片剪辑合成器 v1.0")
    print("=" * 60)
    print("\n使用方式:")
    print("  from short_video_composer import compose_from_materials")
    print("  result = compose_from_materials(")
    print("    material_paths=['clip1.mp4', 'clip2.mp4', 'photo.jpg'],")
    print("    bgm_path='bgm.wav',")
    print("    text_lines=['标题1', '标题2'],")
    print("    project_name='MyVideo',")
    print("    duration=15.0,")
    print("  )")
    print("\n核心类: ShortVideoComposer")
    print("  - add_clip(path, duration, transition_in, camera_move)")
    print("  - add_text(text, start_time, duration, style)")
    print("  - set_bgm(path)")
    print("  - detect_beats(audio_path) -> [节拍点]")
    print("  - auto_arrange_by_beats(beats, duration)")
    print("  - build() -> 工程信息")
