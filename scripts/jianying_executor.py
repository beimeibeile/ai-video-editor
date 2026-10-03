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
from typing import Dict, Any, List, Optional

# 添加jianying-editor路径
JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
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
            os.path.expanduser("~"), "Videos", "剪映导出",
            "Doubao_Jianying-editor", "director_engine_output"
        )
        self.asset_dir = os.path.join(self.work_dir, "assets")
        os.makedirs(self.asset_dir, exist_ok=True)

        self.project = None
        self.character_segments = {}  # 角色名 → 片段
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
            print("  ⚠️  蒙版工具不可用，跳过蒙版")
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
            print(f"  ⚠️  添加蒙版失败: {e}")
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
                print(f"  ⚠️  {target} 已有蒙版，跳过重复添加")
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
                    print(f"  ✅ 圆形蒙版: {target}")

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
                    print(f"  ✅ 矩形蒙版: {target}")
                except Exception as e:
                    print(f"  ⚠️  矩形蒙版失败: {e}")

        return applied

    def _apply_effects(self, effect_instructions: List[Dict]) -> int:
        """
        应用特效指令

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
                            print(f"  ⚠️  特效失败: {e}")
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
                    print(f"  ⚠️  未知特效: {effect_type}")
                    continue

            try:
                seg.add_effect(effect_enum)
                applied += 1
                print(f"  ✅ 特效: {effect_type} → {target}")
            except Exception as e:
                print(f"  ⚠️  特效失败: {e}")

        return applied

    def execute(self, instruction_sequence: Dict[str, Any],
                project_name: str = "导演引擎输出",
                width: int = 1080, height: int = 1920,
                duration: float = 20.0) -> Dict[str, Any]:
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
        print(f"\n{'='*60}")
        print(f"剪映执行器: {project_name}")
        print(f"{'='*60}")

        try:
            # 1. 创建工程
            print(f"\n[1/5] 创建工程: {project_name} ({width}x{height})")
            self.project = JyProject(project_name, width=width, height=height, overwrite=True)

            # 2. 准备素材
            print(f"[2/5] 准备素材...")
            characters = instruction_sequence.get("project", {}).get("characters", [])
            if not characters:
                # 从关键帧指令中提取角色名
                char_names = set()
                for kf in instruction_sequence.get("keyframe_instructions", []):
                    track = kf.get("track", "")
                    if track.startswith("char_"):
                        char_names.add(track.replace("char_", ""))
                characters = [{"name": n} for n in char_names]

            # 背景
            bg_path = create_background_placeholder(self.asset_dir, width, height)
            if bg_path:
                bg_seg = self.project.add_media_safe(
                    bg_path, start_time="0s", duration=f"{duration}s", track_name="Background"
                )
                print(f"  ✅ 背景: {os.path.basename(bg_path)}")

            # 角色占位素材
            for char in characters:
                char_name = char.get("name", "未知")
                char_path = create_character_placeholder(char_name, self.asset_dir)
                if char_path:
                    seg = self.project.add_media_safe(
                        char_path, start_time="0s", duration=f"{duration}s",
                        track_name=f"Char_{char_name}"
                    )
                    if seg:
                        # 默认大小（P24关键帧会覆盖）
                        seg.add_keyframe(draft.KeyframeProperty.uniform_scale, 0, 1.0)
                        self.character_segments[char_name] = seg
                        print(f"  ✅ 角色: {char_name}")

            # 3. 应用关键帧
            print(f"[3/7] 应用关键帧...")
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
                        seg.add_keyframe(prop, time_us, value)
                        kf_applied += 1

            print(f"  ✅ 应用 {kf_applied} 条关键帧")

            # 4. 添加文字（每条用独立轨道避免重叠）
            print(f"[4/7] 添加文字...")
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
            print(f"  ✅ {len(texts)} 条文字")

            # 5. 应用特效
            print(f"[5/7] 应用特效...")
            effects = instruction_sequence.get("effect_instructions", [])
            effects_applied = self._apply_effects(effects)
            print(f"  ✅ {effects_applied} 个特效")

            # 6. 应用蒙版
            print(f"[6/7] 应用蒙版...")
            masks = instruction_sequence.get("mask_instructions", [])
            masks_applied = self._apply_masks(masks)
            print(f"  ✅ {masks_applied} 个蒙版")

            # 7. 保存工程（带蒙版关键帧注入）
            print(f"[7/7] 保存工程...")
            if _MASK_AVAILABLE and masks_applied > 0:
                result = save_with_mask_keyframes(self.project, canvas_h=height)
            else:
                result = self.project.save()
            draft_path = result.get("draft_path", "")

            print(f"\n✅ 剪映工程构建完成!")
            print(f"   工程名: {project_name}")
            print(f"   草稿路径: {draft_path}")
            print(f"   角色数: {len(self.character_segments)}")
            print(f"   关键帧: {kf_applied}条")
            print(f"   文字: {len(texts)}条")
            print(f"   特效: {effects_applied}个")
            print(f"   蒙版: {masks_applied}个")

            return {
                "status": "success",
                "draft_path": draft_path,
                "project_name": project_name,
                "characters": list(self.character_segments.keys()),
                "keyframes_applied": kf_applied,
                "texts_added": len(texts),
                "effects_applied": effects_applied,
                "masks_applied": masks_applied,
            }

        except Exception as e:
            print(f"\n❌ 剪映工程构建失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "error": str(e),
                "project_name": project_name,
            }


if __name__ == "__main__":
    # 测试：用导演引擎输出的指令序列构建剪映工程
    instr_path = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\director_engine_test\e2e_instruction_sequence.json"

    if os.path.exists(instr_path):
        with open(instr_path, "r", encoding="utf-8") as f:
            instructions = json.load(f)

        executor = JianyingExecutor()
        result = executor.execute(
            instructions,
            project_name="导演引擎测试_剪映输出",
            duration=20,
        )
        print(f"\n结果: {result['status']}")
        if result['status'] == 'success':
            print(f"草稿路径: {result['draft_path']}")
    else:
        print(f"❌ 指令序列文件不存在: {instr_path}")
