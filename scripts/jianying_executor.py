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

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# 角色占位颜色
CHARACTER_COLORS = {
    "豆包": (255, 150, 180),    # 粉色
    "机器人": (150, 180, 255),  # 蓝色
    "女杀手": (50, 50, 50),     # 黑色
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
            print(f"[3/5] 应用关键帧...")
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
            print(f"[4/5] 添加文字...")
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

            # 5. 保存工程
            print(f"[5/5] 保存工程...")
            result = self.project.save()
            draft_path = result.get("draft_path", "")

            print(f"\n✅ 剪映工程构建完成!")
            print(f"   工程名: {project_name}")
            print(f"   草稿路径: {draft_path}")
            print(f"   角色数: {len(self.character_segments)}")
            print(f"   关键帧: {kf_applied}条")
            print(f"   文字: {len(texts)}条")

            return {
                "status": "success",
                "draft_path": draft_path,
                "project_name": project_name,
                "characters": list(self.character_segments.keys()),
                "keyframes_applied": kf_applied,
                "texts_added": len(texts),
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
