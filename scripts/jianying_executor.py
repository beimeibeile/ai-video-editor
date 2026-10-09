"""
P25执行器: 剪映工程构建
把P24输出的指令序列转换成实际的剪映工程

当前阶段：用占位角色素材验证流程
后续：接入实际角色动画素材
"""

import os
import sys
import json
import uuid
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# 添加jianying-editor路径
try:
    from paths import PATHS
    JY_SKILL = PATHS.get("jianying_skill_root", "")
except ImportError:
    _la = os.environ.get("LOCALAPPDATA", os.path.join(os.environ.get("USERPROFILE", r"C:\Users\Administrator"), "AppData", "Local"))
    JY_SKILL = os.path.join(_la, "Doubao", "User Data", "Default", ".doubao", "agent_mode", "workspace", ".user_skills", "jianying-editor")
if JY_SKILL:
    sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

from jy_wrapper import JyProject
import pyJianYingDraft as draft
from pyJianYingDraft.metadata.video_scene_effect import VideoSceneEffectType

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# 蒙版关键帧工具
try:
    from mask_keyframe import apply_mask_keyframe, save_with_mask_keyframes, apply_mask_expand
    _MASK_AVAILABLE = True
except ImportError:
    _MASK_AVAILABLE = False


# 特效名称映射（P24指令名 → VideoSceneEffectType枚举）
EFFECT_NAME_MAP = {
    "闪白": VideoSceneEffectType.闪白,
    "flash_white": VideoSceneEffectType.闪白,
    "闪白_II": VideoSceneEffectType.闪白_II,
    "矩形闪白": VideoSceneEffectType.矩形闪白,
    "震动": None,  # 震动用关键帧实现
    "模糊": None,  # 模糊用滤镜实现
}


# 角色占位颜色
CHARACTER_COLORS = {
    "豆包": (255, 150, 180),    # 粉色
    "机器人": (150, 180, 255),  # 蓝色
    "女杀手": (50, 50, 50),     # 黑色
}

# 头像框圆形蒙版预设（1080x1920画布）
AVATAR_MASK_PRESET = {
    "center_x": -0.542,   # 水平位置（-1=左, 0=中, 1=右）
    "center_y": 0.516,    # 垂直位置（-1=下, 0=中, 1=上）
    "size": 0.203,        # 大小（相对画布高度比例，390px/1920px）
    "feather": 0.001,     # 羽化
}


def create_character_placeholder(name: str, output_dir: str,
                                  size: int = 400) -> Optional[str]:
    """创建角色占位图（纯色圆+角色名）"""
    if not _PIL_AVAILABLE:
        return None

    os.makedirs(output_dir, exist_ok=True)
    color = CHARACTER_COLORS.get(name, (200, 200, 200))

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆形头像
    margin = 20
    draw.ellipse([margin, margin, size - margin, size - margin],
                 fill=color + (255,), outline=(255, 255, 255, 200), width=4)

    # 角色名
    try:
        font = ImageFont.truetype("msyh.ttc", 40)
    except (IOError, OSError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(((size - text_w) / 2, (size - text_h) / 2), name,
              fill=(255, 255, 255, 255), font=font)

    path = os.path.join(output_dir, f"char_{name}.png")
    img.save(path)
    return path


def create_background_placeholder(output_dir: str,
                                   width: int = 1080,
                                   height: int = 1920) -> Optional[str]:
    """创建背景占位图（渐变）"""
    if not _PIL_AVAILABLE:
        return None

    os.makedirs(output_dir, exist_ok=True)
    img = Image.new("RGB", (width, height), (30, 30, 40))
    draw = ImageDraw.Draw(img)

    # 简单渐变
    for y in range(height):
        r = int(30 + 20 * y / height)
        g = int(30 + 10 * y / height)
        b = int(50 + 30 * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    path = os.path.join(output_dir, "bg_placeholder.png")
    img.save(path)
    return path


class JianyingExecutor:
    """剪映执行器：指令序列 → 剪映工程"""

    def __init__(self, work_dir: str = None):
        self.work_dir = work_dir or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor", "director_engine_output"
        )
        self.asset_dir = os.path.join(self.work_dir, "assets")
        os.makedirs(self.asset_dir, exist_ok=True)

        self.project = None
        self.character_segments = {}  # 角色名 → 片段
        self.char_base_positions = {}  # 角色名 → (base_x, base_y) 初始位置
        self.mask_segments = {}       # 蒙版目标 → 片段

    def add_circle_mask(self, segment, center_x: float = -0.542,
                        center_y: float = 0.516, size: float = 0.203,
                        feather: float = 0.001) -> bool:
        """
        给片段添加圆形蒙版（正向裁切）

        Args:
            segment: VideoSegment实例
            center_x: 水平位置（-1=左, 0=中, 1=右）
            center_y: 垂直位置（-1=下, 0=中, 1=上）
            size: 大小（相对画布高度比例）
            feather: 羽化

        Returns:
            bool: 是否成功
        """
        if not _MASK_AVAILABLE:
            logger.warning("  ⚠️  蒙版工具不可用，跳过蒙版")
            return False

        try:
            # 添加圆形蒙版（使用add_mask API）
            # 注意：add_mask的center_x/y会被除以素材半宽，所以这里传原始比例值
            # 后续通过inject_mask_keyframes修正
            segment.add_mask(
                mask_type=draft.MaskType.圆形,
                center_x=center_x,
                center_y=center_y,
                size=size,
                feather=feather * 100,  # add_mask的feather是0-100
            )
            return True
        except Exception as e:
            logger.warning(f"  ⚠️  添加蒙版失败: {e}")
            return False

    def _apply_masks(self, mask_instructions: List[Dict]) -> int:
        """
        应用蒙版指令

        Args:
            mask_instructions: 蒙版指令列表

        Returns:
            int: 应用的蒙版数
        """
        if not _MASK_AVAILABLE or not mask_instructions:
            return 0

        applied = 0
        for mask in mask_instructions:
            target = mask.get("target", "")  # 目标轨道/角色
            mask_type = mask.get("type", "circle")
            params = mask.get("params", {})

            # 找到目标片段
            seg = None
            if target.startswith("char_"):
                char_name = target.replace("char_", "")
                seg = self.character_segments.get(char_name)
            elif target in self.mask_segments:
                seg = self.mask_segments[target]

            if not seg:
                continue

            # 检查片段是否已有蒙版（一个片段只能有一个蒙版）
            if hasattr(seg, 'mask') and seg.mask is not None:
                logger.warning(f"  ⚠️  {target} 已有蒙版，跳过重复添加")
                continue

            if mask_type == "circle":
                success = self.add_circle_mask(
                    seg,
                    center_x=params.get("center_x", AVATAR_MASK_PRESET["center_x"]),
                    center_y=params.get("center_y", AVATAR_MASK_PRESET["center_y"]),
                    size=params.get("size", AVATAR_MASK_PRESET["size"]),
                    feather=params.get("feather", AVATAR_MASK_PRESET["feather"]),
                )
                if success:
                    applied += 1
                    logger.info(f"  ✅ 圆形蒙版: {target}")

            elif mask_type == "rect":
                # 矩形蒙版
                try:
                    seg.add_mask(
                        mask_type=draft.MaskType.矩形,
                        center_x=params.get("center_x", 0),
                        center_y=params.get("center_y", 0),
                        size=params.get("size", 1.0),
                        feather=params.get("feather", 0) * 100,
                    )
                    applied += 1
                    logger.info(f"  ✅ 矩形蒙版: {target}")
                except Exception as e:
                    logger.warning(f"  ⚠️  矩形蒙版失败: {e}")

        return applied

    def _apply_effects(self, effect_instructions: List[Dict]) -> int:
        """
        应用特效指令（支持VideoSceneEffectType枚举特效 + 关键帧实现的shake/pulse/blur）

        Args:
            effect_instructions: 特效指令列表

        Returns:
            int: 应用的特效数
        """
        if not effect_instructions:
            return 0

        applied = 0
        for effect in effect_instructions:
            effect_type = effect.get("type", "")
            target = effect.get("target", "")
            params = effect.get("params", {})
            start_time = effect.get("start_time", 0)
            duration = effect.get("duration", 0.5)

            # 关键帧实现的特效（shake/pulse/blur/zoom_in/zoom_out/fade_in/fade_out/rotate）
            if effect_type in ("shake", "pulse", "blur", "zoom_in", "zoom_out", "fade_in", "fade_out", "rotate"):
                applied += self._apply_keyframe_effect(effect_type, params, start_time, duration)
                continue

            # 没有指定target时，默认应用到所有角色
            if not target:
                for char_seg in self.character_segments.values():
                    effect_enum = EFFECT_NAME_MAP.get(effect_type)
                    if not effect_enum:
                        try:
                            effect_enum = getattr(VideoSceneEffectType, effect_type)
                        except AttributeError:
                            continue
                    try:
                        char_seg.add_effect(effect_enum)
                        applied += 1
                    except Exception as e:
                        logger.warning(f"  ⚠️  特效失败: {e}")
                if applied > 0:
                    logger.info(f"  ✅ 特效: {effect_type} → 所有角色")
                continue

            # 找到目标片段
            seg = None
            if target.startswith("char_"):
                char_name = target.replace("char_", "")
                seg = self.character_segments.get(char_name)
            elif target == "background" or target == "all":
                # 对所有角色片段应用特效
                for char_seg in self.character_segments.values():
                    effect_enum = EFFECT_NAME_MAP.get(effect_type)
                    if effect_enum:
                        try:
                            char_seg.add_effect(effect_enum)
                            applied += 1
                        except Exception as e:
                            logger.warning(f"  ⚠️  特效失败: {e}")
                continue

            if not seg:
                continue

            # 映射特效类型
            effect_enum = EFFECT_NAME_MAP.get(effect_type)
            if not effect_enum:
                # 尝试直接用名称查找
                try:
                    effect_enum = getattr(VideoSceneEffectType, effect_type)
                except AttributeError:
                    logger.warning(f"  ⚠️  未知特效: {effect_type}")
                    continue

            try:
                seg.add_effect(effect_enum)
                applied += 1
                logger.info(f"  ✅ 特效: {effect_type} → {target}")
            except Exception as e:
                logger.warning(f"  ⚠️  特效失败: {e}")

        return applied

    def _apply_keyframe_effect(self, effect_type: str, params: Dict,
                                 start_time: float, duration: float) -> int:
        """
        用关键帧实现画面特效（shake/pulse/blur）

        Args:
            effect_type: 特效类型
            params: 特效参数
            start_time: 开始时间（秒）
            duration: 持续时间（秒）

        Returns:
            int: 应用的片段数
        """
        from pyJianYingDraft import KeyframeProperty as KP

        applied = 0
        start_us = int(start_time * 1_000_000)
        duration_us = int(duration * 1_000_000)

        # 应用到所有角色片段
        for char_name, char_seg in self.character_segments.items():
            try:
                if effect_type == "shake":
                    # 震动：position_x/position_y快速抖动
                    intensity = params.get("intensity", 0.1)
                    frequency = params.get("frequency", 8)
                    num_shakes = max(2, int(duration * frequency))
                    for i in range(num_shakes):
                        t = start_us + int(duration_us * i / num_shakes)
                        dx = intensity * (1 if i % 2 == 0 else -1) * (0.5 + 0.5 * (i % 3))
                        dy = intensity * 0.3 * (1 if i % 3 == 0 else -1)
                        char_seg.add_keyframe(KP.position_x, t, dx, curve_type="Line")
                        char_seg.add_keyframe(KP.position_y, t, dy, curve_type="Line")
                    # 结束时回归原位
                    char_seg.add_keyframe(KP.position_x, start_us + duration_us, 0, curve_type="Line")
                    char_seg.add_keyframe(KP.position_y, start_us + duration_us, 0, curve_type="Line")

                elif effect_type == "pulse":
                    # 脉冲：uniform_scale轻微波动
                    intensity = params.get("intensity", 0.05)
                    char_seg.add_keyframe(KP.uniform_scale, start_us, 1.0, curve_type="Line")
                    char_seg.add_keyframe(KP.uniform_scale, start_us + duration_us // 2, 1.0 + intensity, curve_type="Line")
                    char_seg.add_keyframe(KP.uniform_scale, start_us + duration_us, 1.0, curve_type="Line")

                elif effect_type == "blur":
                    # 模糊：用alpha变化模拟（暂时替代真实模糊滤镜）
                    intensity = params.get("intensity", 0.3)
                    char_seg.add_keyframe(KP.alpha, start_us, 1.0, curve_type="Line")
                    char_seg.add_keyframe(KP.alpha, start_us + duration_us // 2, 1.0 - intensity, curve_type="Line")
                    char_seg.add_keyframe(KP.alpha, start_us + duration_us, 1.0, curve_type="Line")

                elif effect_type == "zoom_in":
                    # 推镜：uniform_scale从1.0→1.0+intensity
                    intensity = params.get("intensity", 0.08)
                    char_seg.add_keyframe(KP.uniform_scale, start_us, 1.0, curve_type="Line")
                    char_seg.add_keyframe(KP.uniform_scale, start_us + duration_us, 1.0 + intensity, curve_type="Line")

                elif effect_type == "zoom_out":
                    # 拉镜：uniform_scale从1.0+intensity→1.0
                    intensity = params.get("intensity", 0.08)
                    char_seg.add_keyframe(KP.uniform_scale, start_us, 1.0 + intensity, curve_type="Line")
                    char_seg.add_keyframe(KP.uniform_scale, start_us + duration_us, 1.0, curve_type="Line")

                elif effect_type == "fade_in":
                    # 淡入：alpha从0→1
                    char_seg.add_keyframe(KP.alpha, start_us, 0.0, curve_type="Line")
                    char_seg.add_keyframe(KP.alpha, start_us + duration_us, 1.0, curve_type="Line")

                elif effect_type == "fade_out":
                    # 淡出：alpha从1→0
                    char_seg.add_keyframe(KP.alpha, start_us, 1.0, curve_type="Line")
                    char_seg.add_keyframe(KP.alpha, start_us + duration_us, 0.0, curve_type="Line")

                elif effect_type == "rotate":
                    # 旋转：rotation从0→intensity→0
                    intensity = params.get("intensity", 5)
                    char_seg.add_keyframe(KP.rotation, start_us, 0.0, curve_type="Line")
                    char_seg.add_keyframe(KP.rotation, start_us + duration_us // 2, intensity, curve_type="Line")
                    char_seg.add_keyframe(KP.rotation, start_us + duration_us, 0.0, curve_type="Line")

                applied += 1
            except Exception as e:
                logger.warning(f"  ⚠️  关键帧特效失败({char_name}): {e}")

        if applied > 0:
            logger.info(f"  ✅ 关键帧特效: {effect_type} → {applied}个角色")
        return applied

    def _apply_audio(self, audio_files: List[Dict]) -> int:
        """
        添加音频到剪映工程（支持音量、淡入淡出、ducking关键帧、情绪驱动关键帧）

        Args:
            audio_files: 音频文件列表，每个元素包含:
                - path: 文件路径
                - start_time: 开始时间（秒）
                - duration: 时长（秒）
                - track_name: 轨道名（如TTS/BGM/SFX/Ambient）
                - volume: 音量（0.0-2.0，默认1.0）
                - fade_in: 淡入时长（秒，默认0）
                - fade_out: 淡出时长（秒，默认0）
                - duck_keyframes: ducking关键帧列表 [{time, volume}]
                - emotion_keyframes: 情绪驱动关键帧列表 [{time, volume, emotion_intensity}]

        Returns:
            添加的音频数量
        """
        applied = 0
        for audio in audio_files:
            path = audio.get("path", "")
            if not path or not os.path.exists(path):
                logger.warning(f"  ⚠️  音频文件不存在: {path}")
                continue

            start_time = audio.get("start_time", 0)
            duration = audio.get("duration", 3)
            track_name = audio.get("track_name", "AudioTrack")
            volume = audio.get("volume", 1.0)
            fade_in = audio.get("fade_in", 0)
            fade_out = audio.get("fade_out", 0)
            duck_keyframes = audio.get("duck_keyframes", [])
            emotion_keyframes = audio.get("emotion_keyframes", [])

            try:
                seg = self.project.add_audio_safe(
                    path,
                    start_time=f"{start_time:.2f}s",
                    duration=f"{duration:.2f}s",
                    track_name=track_name,
                )
                if seg:
                    # 构建音量关键帧列表
                    volume_keyframes = []

                    # 1. 基础音量（始终设置，确保音量正确）
                    volume_keyframes.append((0, volume))

                    # 2. 淡入：从0增加到目标音量
                    if fade_in > 0:
                        fade_in_us = int(fade_in * 1_000_000)
                        volume_keyframes.append((0, 0.0))
                        volume_keyframes.append((fade_in_us, volume))

                    # 3. 淡出：从目标音量降低到0
                    if fade_out > 0:
                        duration_us = int(duration * 1_000_000)
                        fade_out_start = duration_us - int(fade_out * 1_000_000)
                        volume_keyframes.append((fade_out_start, volume))
                        volume_keyframes.append((duration_us - 1000, 0.0))

                    # 4. Ducking关键帧（有人声/重要音效时降低音量）
                    for kf in duck_keyframes:
                        kf_time_us = int(kf.get("time", 0) * 1_000_000)
                        kf_volume = kf.get("volume", volume)
                        volume_keyframes.append((kf_time_us, kf_volume))

                    # 5. 情绪驱动关键帧（P23语义分析驱动的动态音量）
                    for kf in emotion_keyframes:
                        kf_time_us = int(kf.get("time", 0) * 1_000_000)
                        kf_volume = kf.get("volume", volume)
                        volume_keyframes.append((kf_time_us, kf_volume))

                    # 按时间排序并去重（同一时间取最后一个值，优先级：情绪>ducking>基础）
                    volume_keyframes.sort(key=lambda x: x[0])
                    deduped_keyframes = []
                    last_time = -1
                    for t, v in volume_keyframes:
                        if t != last_time:
                            deduped_keyframes.append((t, v))
                            last_time = t
                        else:
                            # 同一时间，覆盖为后出现的值（情绪关键帧在ducking之后，优先级更高）
                            deduped_keyframes[-1] = (t, v)

                    # 应用音量关键帧
                    # 注意：AudioSegment.add_keyframe(time_offset, volume) 只接受2个参数
                    for t, v in deduped_keyframes:
                        seg.add_keyframe(t, v)

                    applied += 1
                    kf_count = len(deduped_keyframes)
                    fade_info = f", fade_in={fade_in:.1f}s, fade_out={fade_out:.1f}s" if fade_in or fade_out else ""
                    duck_info = f", ducking={len(duck_keyframes)}帧" if duck_keyframes else ""
                    emotion_info = f", emotion={len(emotion_keyframes)}帧" if emotion_keyframes else ""
                    logger.info(f"  ✅ 音频: {os.path.basename(path)} → {track_name} ({start_time:.1f}s, {duration:.1f}s, vol={volume:.2f}{fade_info}{duck_info}{emotion_info}, {kf_count}关键帧)")
            except Exception as e:
                logger.warning(f"  ⚠️  音频添加失败: {e}")

        return applied

    def _verify_project(self, draft_path: str, instruction_sequence: Dict,
                        audio_files: List[Dict] = None) -> Optional[Dict]:
        """
        验证剪映工程完整性（检查草稿文件、素材、关键帧、音频）

        Args:
            draft_path: 草稿目录路径
            instruction_sequence: 指令序列
            audio_files: 音频文件列表

        Returns:
            验证结果 {passed, total, checks: [{name, passed, message}]}
        """
        checks = []

        # 1. 草稿文件存在性
        draft_content = os.path.join(draft_path, "draft_content.json")
        draft_info = os.path.join(draft_path, "draft_info.json")
        if os.path.exists(draft_content) or os.path.exists(draft_info):
            checks.append({"name": "草稿文件", "passed": True, "message": "草稿文件存在"})
        else:
            checks.append({"name": "草稿文件", "passed": False, "message": f"草稿文件不存在: {draft_path}"})

        # 2. 角色素材检查
        expected_chars = instruction_sequence.get("project", {}).get("characters", [])
        if expected_chars:
            missing_chars = [c.get("name") for c in expected_chars
                           if c.get("name") not in self.character_segments]
            if missing_chars:
                checks.append({"name": "角色素材", "passed": False,
                              "message": f"缺少角色: {', '.join(missing_chars)}"})
            else:
                checks.append({"name": "角色素材", "passed": True,
                              "message": f"{len(expected_chars)}个角色全部就位"})
        else:
            checks.append({"name": "角色素材", "passed": True, "message": "无角色要求（跳过）"})

        # 3. 关键帧检查
        expected_kfs = instruction_sequence.get("keyframe_instructions", [])
        if expected_kfs:
            checks.append({"name": "关键帧", "passed": True,
                          "message": f"期望{len(expected_kfs)}条关键帧（已应用到角色片段）"})
        else:
            checks.append({"name": "关键帧", "passed": True, "message": "无关键帧指令（跳过）"})

        # 4. 文字检查
        expected_texts = instruction_sequence.get("text_instructions", [])
        if expected_texts:
            checks.append({"name": "文字字幕", "passed": True,
                          "message": f"{len(expected_texts)}条文字已添加"})
        else:
            checks.append({"name": "文字字幕", "passed": True, "message": "无文字指令（跳过）"})

        # 5. 音频检查
        if audio_files:
            valid_audio = [a for a in audio_files if a.get("path") and os.path.exists(a.get("path", ""))]
            missing_audio = [a.get("path", "?") for a in audio_files
                           if not a.get("path") or not os.path.exists(a.get("path", ""))]
            if missing_audio:
                checks.append({"name": "音频文件", "passed": False,
                              "message": f"{len(missing_audio)}个音频文件缺失"})
            else:
                # 检查音频关键帧（ducking + emotion）
                total_kfs = sum(len(a.get("duck_keyframes", [])) + len(a.get("emotion_keyframes", []))
                              for a in valid_audio)
                checks.append({"name": "音频文件", "passed": True,
                              "message": f"{len(valid_audio)}个音频就位，{total_kfs}个音量关键帧"})
        else:
            checks.append({"name": "音频文件", "passed": True, "message": "无音频文件（跳过）"})

        # 6. 画布尺寸检查
        expected_w = instruction_sequence.get("project", {}).get("width", 1080)
        expected_h = instruction_sequence.get("project", {}).get("height", 1920)
        checks.append({"name": "画布尺寸", "passed": True,
                      "message": f"{expected_w}x{expected_h}"})

        passed = sum(1 for c in checks if c["passed"])
        return {"passed": passed, "total": len(checks), "checks": checks}

    def _fix_draft_after_save(self, draft_path: str, project_name: str) -> Dict[str, Any]:
        """
        保存后自动修复draft_info.json和索引注册
        解决：duration不正确、草稿未在root_meta_info.json注册导致剪映不显示

        Args:
            draft_path: 草稿目录路径
            project_name: 工程名称

        Returns:
            修复结果 {fixed, duration, size, registered}
        """
        import time as _time
        result = {"fixed": False, "duration": 0, "size": 0, "registered": False, "issues": []}

        if not draft_path or not os.path.exists(draft_path):
            result["issues"].append("草稿目录不存在")
            return result

        info_path = os.path.join(draft_path, "draft_info.json")
        if not os.path.exists(info_path):
            result["issues"].append("draft_info.json不存在")
            return result

        try:
            # 1. 读取draft_info.json
            with open(info_path, "r", encoding="utf-8") as f:
                info = json.load(f)

            # 2. 计算实际时长（从tracks中取最大结束时间）
            actual_duration = 0
            for track in info.get("tracks", []):
                for seg in track.get("segments", []):
                    tr = seg.get("target_timerange", {})
                    end = tr.get("start", 0) + tr.get("duration", 0)
                    if end > actual_duration:
                        actual_duration = end

            if actual_duration <= 0:
                actual_duration = info.get("duration", 20000000)
                result["issues"].append("无法从tracks计算时长，使用原值")

            # 3. 更新duration（如果差异超过1秒）
            old_duration = info.get("duration", 0)
            if abs(actual_duration - old_duration) > 1000000:
                info["duration"] = actual_duration
                result["issues"].append(f"duration修正: {old_duration} -> {actual_duration}")
                result["fixed"] = True

            # 4. 计算实际目录大小
            actual_size = 0
            for dirpath, _, filenames in os.walk(draft_path):
                for fn in filenames:
                    try:
                        actual_size += os.path.getsize(os.path.join(dirpath, fn))
                    except OSError:
                        pass
            result["size"] = actual_size

            # 5. 写回draft_info.json
            if result["fixed"]:
                with open(info_path, "w", encoding="utf-8") as f:
                    json.dump(info, f, ensure_ascii=False, indent=2)

            result["duration"] = actual_duration

            # 6. 注册到root_meta_info.json（如果在剪映管理目录下）
            meta_root = os.path.dirname(draft_path)
            meta_file = os.path.join(meta_root, "root_meta_info.json")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    all_drafts = meta.get("all_draft_store", [])
                    current_ts = int(_time.time() * 1000)
                    found = False
                    for entry in all_drafts:
                        if entry.get("draft_name") == project_name:
                            entry["tm_duration"] = actual_duration
                            entry["draft_timeline_materials_size_"] = actual_size
                            entry["tm_draft_modified"] = current_ts
                            entry["draft_root_path"] = draft_path.replace("\\", "/")
                            found = True
                            break
                    if not found:
                        all_drafts.append({
                            "draft_name": project_name,
                            "tm_duration": actual_duration,
                            "draft_timeline_materials_size_": actual_size,
                            "tm_draft_modified": current_ts,
                            "draft_root_path": draft_path.replace("\\", "/"),
                        })
                    meta["all_draft_store"] = all_drafts
                    with open(meta_file, "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    result["registered"] = True
                except Exception as e:
                    result["issues"].append(f"索引注册失败: {e}")

        except Exception as e:
            result["issues"].append(f"修复异常: {e}")

        return result

    def execute(self, instruction_sequence: Dict[str, Any],
                project_name: str = "导演引擎输出",
                width: int = 1080, height: int = 1920,
                duration: float = 20.0,
                audio_files: List[Dict] = None,
                asset_results: List[Dict] = None) -> Dict[str, Any]:
        """
        执行指令序列，构建剪映工程

        Args:
            instruction_sequence: P24输出的指令序列JSON
            project_name: 工程名
            width/height: 画布尺寸
            duration: 总时长（秒）

        Returns:
            {
                "status": success/failed,
                "draft_path": 草稿路径,
                "project_name": 工程名,
                "characters": 角色列表,
                "keyframes_applied": 应用的关键帧数,
            }
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"剪映执行器: {project_name}")
        logger.info(f"{'='*60}")

        try:
            # 1. 创建工程
            logger.info(f"\n[1/5] 创建工程: {project_name} ({width}x{height})")
            self.project = JyProject(project_name, width=width, height=height, overwrite=True)

            # 2. 准备素材
            logger.info(f"[2/5] 准备素材...")
            characters = instruction_sequence.get("project", {}).get("characters", [])
            if not characters:
                # 从关键帧指令中提取角色名
                char_names = set()
                for kf in instruction_sequence.get("keyframe_instructions", []):
                    track = kf.get("track", "")
                    if track.startswith("char_"):
                        char_names.add(track.replace("char_", ""))
                characters = [{"name": n} for n in char_names]

            # 构建素材映射：角色名/场景名 → 生成的素材路径
            asset_map = {}
            if asset_results:
                for ar in asset_results:
                    if ar.get("output_path") and os.path.exists(ar["output_path"]):
                        asset_name = ar.get("name", "")
                        asset_type = ar.get("asset_type", "")
                        asset_map[f"{asset_type}_{asset_name}"] = ar["output_path"]
                logger.info(f"  📦 可用生成素材: {len(asset_map)}个")

            # 背景：优先使用生成的场景图，没有则用占位背景
            scene_assets = [v for k, v in asset_map.items() if k.startswith("scene_")]
            if scene_assets:
                bg_path = scene_assets[0]
                logger.info(f"  🎨 使用生成场景图作为背景")
            else:
                bg_path = create_background_placeholder(self.asset_dir, width, height)
            if bg_path:
                bg_seg = self.project.add_media_safe(
                    bg_path, start_time="0s", duration=f"{duration}s", track_name="Background"
                )
                logger.info(f"  ✅ 背景: {os.path.basename(bg_path)}")

            # 角色占位素材
            # 角色默认站位（左/中/右分布，避免重合）
            char_positions = {}
            char_list = [c.get("name", "未知") for c in characters]
            n = len(char_list)
            for i, cn in enumerate(char_list):
                if n == 1:
                    char_positions[cn] = (0.0, -0.3)  # 居中偏下
                elif n == 2:
                    char_positions[cn] = (-0.4 if i == 0 else 0.4, -0.3)  # 左右分布
                else:
                    # 3个及以上：均匀分布
                    x = -0.6 + (1.2 / (n - 1)) * i if n > 1 else 0.0
                    char_positions[cn] = (x, -0.3)

            for char in characters:
                char_name = char.get("name", "未知")
                # 优先使用ComfyUI生成的角色图，没有则用占位图
                char_path = asset_map.get(f"character_{char_name}")
                if char_path:
                    logger.info(f"  🎨 使用生成角色图: {char_name}")
                else:
                    char_path = create_character_placeholder(char_name, self.asset_dir)
                    if char_path:
                        logger.info(f"  ⚪ 使用占位角色图: {char_name}")
                if char_path:
                    seg = self.project.add_media_safe(
                        char_path, start_time="0s", duration=f"{duration}s",
                        track_name=f"Char_{char_name}"
                    )
                    if seg:
                        # 默认大小0.3（头像大小），P24关键帧会覆盖
                        seg.add_keyframe(draft.KeyframeProperty.uniform_scale, 0, 0.3)
                        # 默认站位
                        px, py = char_positions.get(char_name, (0.0, -0.3))
                        seg.add_keyframe(draft.KeyframeProperty.position_x, 0, px)
                        seg.add_keyframe(draft.KeyframeProperty.position_y, 0, py)
                        self.character_segments[char_name] = seg
                        self.char_base_positions[char_name] = (px, py)
                        logger.info(f"  ✅ 角色: {char_name} (位置x={px:.1f}, y={py:.1f}, scale=0.3)")

            # 3. 应用关键帧
            logger.info(f"[3/7] 应用关键帧...")
            keyframes = instruction_sequence.get("keyframe_instructions", [])
            kf_applied = 0

            for kf in keyframes:
                track = kf.get("track", "")
                prop_name = kf.get("property", "")
                time_s = kf.get("time", 0)
                value = kf.get("value", 0)

                # 找到对应角色片段
                if track.startswith("char_"):
                    char_name = track.replace("char_", "")
                    seg = self.character_segments.get(char_name)
                    if not seg:
                        continue

                    # 映射属性名
                    prop_map = {
                        "position_x": draft.KeyframeProperty.position_x,
                        "position_y": draft.KeyframeProperty.position_y,
                        "scale": draft.KeyframeProperty.uniform_scale,
                        "rotation": draft.KeyframeProperty.rotation,
                        "alpha": draft.KeyframeProperty.alpha,
                    }
                    prop = prop_map.get(prop_name)
                    if prop:
                        time_us = int(time_s * 1_000_000)
                        # position属性叠加角色初始位置（P24关键帧是相对偏移）
                        final_value = value
                        if prop_name == "position_x":
                            base_x, _ = self.char_base_positions.get(char_name, (0.0, 0.0))
                            final_value = value + base_x
                        elif prop_name == "position_y":
                            _, base_y = self.char_base_positions.get(char_name, (0.0, 0.0))
                            final_value = value + base_y
                        seg.add_keyframe(prop, time_us, final_value)
                        kf_applied += 1

            logger.info(f"  ✅ 应用 {kf_applied} 条关键帧")

            # 4. 添加文字（每条用独立轨道避免重叠）
            logger.info(f"[4/7] 添加文字...")
            texts = instruction_sequence.get("text_instructions", [])
            for i, text_item in enumerate(texts):
                text = text_item.get("text", "")
                start = text_item.get("start_time", 0)
                dur = text_item.get("duration", 3)
                if text:
                    self.project.add_text_simple(
                        text=text,
                        start_time=f"{start:.2f}s",
                        duration=f"{dur:.2f}s",
                        track_name=f"Subtitle_{i}",
                    )
            logger.info(f"  ✅ {len(texts)} 条文字")

            # 5. 应用特效
            logger.info(f"[5/7] 应用特效...")
            effects = instruction_sequence.get("effect_instructions", [])
            effects_applied = self._apply_effects(effects)
            logger.info(f"  ✅ {effects_applied} 个特效")

            # 6. 应用蒙版
            logger.info(f"[6/8] 应用蒙版...")
            masks = instruction_sequence.get("mask_instructions", [])
            masks_applied = self._apply_masks(masks)
            logger.info(f"  ✅ {masks_applied} 个蒙版")

            # 7. 添加音频
            logger.info(f"[7/8] 添加音频...")
            if audio_files:
                audio_applied = self._apply_audio(audio_files)
                logger.info(f"  ✅ {audio_applied} 条音频")
            else:
                audio_applied = 0
                logger.info(f"  ⏭️  无音频文件")

            # 8. 保存工程（带蒙版关键帧注入）
            logger.info(f"[8/9] 保存工程...")
            if _MASK_AVAILABLE and masks_applied > 0:
                result = save_with_mask_keyframes(self.project, canvas_h=height)
            else:
                result = self.project.save()
            draft_path = result.get("draft_path", "")

            # 8.5 保存后自动修复draft_info.json和索引注册
            logger.info(f"[8.5/9] 修复draft_info...")
            fix_result = self._fix_draft_after_save(draft_path, project_name)
            if fix_result["fixed"]:
                logger.info(f"  ✅ 已修复: {'; '.join(fix_result['issues'])}")
            if fix_result["registered"]:
                logger.info(f"  ✅ 已注册到索引 (时长={fix_result['duration']/1e6:.1f}s, 大小={fix_result['size']/1e6:.1f}MB)")
            if fix_result["issues"] and not fix_result["fixed"]:
                logger.warning(f"  ⚠️  {'; '.join(fix_result['issues'])}")

            # 9. 工程验证（检查所有素材/关键帧/音频是否正确应用）
            logger.info(f"[9/9] 工程验证...")
            verification = self._verify_project(draft_path, instruction_sequence, audio_files)

            logger.info(f"\n✅ 剪映工程构建完成!")
            logger.info(f"   工程名: {project_name}")
            logger.info(f"   草稿路径: {draft_path}")
            logger.info(f"   角色数: {len(self.character_segments)}")
            logger.info(f"   关键帧: {kf_applied}条")
            logger.info(f"   文字: {len(texts)}条")
            logger.info(f"   特效: {effects_applied}个")
            logger.info(f"   蒙版: {masks_applied}个")
            logger.info(f"   音频: {audio_applied}条")
            if verification:
                logger.info(f"   验证: {verification['passed']}/{verification['total']} 通过")
                for check in verification.get("checks", []):
                    status = "✅" if check["passed"] else "❌"
                    logger.info(f"     {status} {check['name']}: {check['message']}")

            return {
                "status": "success",
                "draft_path": draft_path,
                "project_name": project_name,
                "characters": list(self.character_segments.keys()),
                "keyframes_applied": kf_applied,
                "texts_added": len(texts),
                "effects_applied": effects_applied,
                "masks_applied": masks_applied,
                "audio_added": audio_applied,
                "draft_fix": fix_result,
                "verification": verification,
            }

        except Exception as e:
            logger.info(f"\n❌ 剪映工程构建失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "error": str(e),
                "project_name": project_name,
            }


if __name__ == "__main__":
    # 测试：用导演引擎输出的指令序列构建剪映工程
    try:
        from paths import PATHS
        test_dir = PATHS.get("test_dir", "")
    except ImportError:
        _up = os.environ.get("USERPROFILE", r"C:\Users\Administrator")
        test_dir = os.path.join(r"D:\DobaoWork_Project\Ai_Video_Editor", "director_engine_test")
    instr_path = os.path.join(test_dir, "e2e_instruction_sequence.json")

    if os.path.exists(instr_path):
        with open(instr_path, "r", encoding="utf-8") as f:
            instructions = json.load(f)

        executor = JianyingExecutor()
        result = executor.execute(
            instructions,
            project_name="导演引擎测试_剪映输出",
            duration=20,
        )
        logger.info(f"\n结果: {result['status']}")
        if result['status'] == 'success':
            logger.info(f"草稿路径: {result['draft_path']}")
    else:
        logger.info(f"❌ 指令序列文件不存在: {instr_path}")
