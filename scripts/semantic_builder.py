"""
语义驱动工程构建器 v1.0 (P22-4)
整合角色语义理解+圆形蒙版+混合模式，构建有"故事感"的角色剧工程。

解决v9的核心问题：
- v9只是静态PNG平移，没有角色动作/情绪/故事
- v10根据语义卡自动生成：角色动作+蒙版裁切+混合模式光影+音效对齐

使用方法：
    python semantic_builder.py --semantic semantic_card.json --output 豆包被打_v10
"""
import os
import sys
import json
import argparse
from typing import Dict, List, Any, Optional

SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(SKILL, "scripts"))
sys.path.insert(0, os.path.join(SKILL, "scripts", "vendor"))

from jy_wrapper import JyProject
import pyJianYingDraft as draft

# 导入P22工具
P22_SKILL = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor\scripts"
sys.path.insert(0, P22_SKILL)
from circle_mask import add_circle_mask, add_avatar_frame_mask, add_mask_shake_keyframes
from blend_mode import set_blend_mode, add_blend_flash, apply_impact_effects

# 头像框坐标（已验证）
AVATAR_X = -0.653
AVATAR_Y = 0.561
AVATAR_R = 0.22


class SemanticBuilder:
    """语义驱动工程构建器"""

    def __init__(self, semantic_card_path: str, assets_dir: str):
        with open(semantic_card_path, 'r', encoding='utf-8') as f:
            self.semantic = json.load(f)
        self.assets_dir = assets_dir
        self.project = None
        self.segments = {}  # {角色名: segment对象}
        self.segment_ids = {}  # {角色名: 片段ID}

    def build(self, project_name: str, width: int = 1080, height: int = 1920) -> str:
        """构建完整工程"""
        duration = self.semantic.get("duration", 20.0)

        print(f"\n{'='*60}")
        print(f"  语义驱动构建: {project_name}")
        print(f"{'='*60}")
        print(f"  时长: {duration:.1f}s")
        print(f"  角色: {[c['name'] for c in self.semantic['characters']]}")
        print(f"  叙事弧线: {self.semantic['narrative_arc']}")

        # 1. 创建工程+背景
        self._create_project(project_name, width, height, duration)

        # 2. 创建角色层
        self._create_characters(duration)

        # 3. 应用动作关键帧
        self._apply_actions()

        # 4. 应用蒙版
        self._apply_masks()

        # 5. 应用混合模式
        self._apply_blend_modes()

        # 6. 应用音效
        self._apply_audio(duration)

        # 7. 保存
        result = self.project.save()
        draft_path = result.get("draft_path", "")
        print(f"\n✅ 工程已保存: {draft_path}")

        # 复制到D盘
        import shutil
        target = os.path.join(r"D:\JianyingProDrafts\JianyingPro Drafts", project_name)
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.copytree(draft_path, target)
        print(f"✅ 已复制到: {target}")

        return target

    def _create_project(self, name: str, w: int, h: int, duration: float):
        """创建工程+背景"""
        print(f"\n[1/7] 创建工程+背景")
        self.project = JyProject(name, width=w, height=h, overwrite=True)

        bg_path = os.path.join(self.assets_dir, "clean_bg_1080.png")
        if os.path.exists(bg_path):
            bg = self.project.add_media_safe(bg_path, "0s", f"{duration}s", "BG")
            bg.add_keyframe(draft.KeyframeProperty.position_x, 0, 0)
            bg.add_keyframe(draft.KeyframeProperty.position_y, 0, 0)
            bg.add_keyframe(draft.KeyframeProperty.uniform_scale, 0, 1.0)
            bg.add_keyframe(draft.KeyframeProperty.alpha, 0, 1.0)
            print(f"  ✅ 背景: {os.path.basename(bg_path)}")
        else:
            print(f"  ⚠️ 背景不存在: {bg_path}")

    def _create_characters(self, duration: float):
        """创建角色层"""
        print(f"\n[2/7] 创建角色层")
        char_files = {
            "豆包": "doubao.png",
            "机器人": "robot.png",
            "女杀手": "killer.png",
        }

        for char in self.semantic["characters"]:
            name = char["name"]
            filename = char_files.get(name, f"{name}.png")
            path = os.path.join(self.assets_dir, "characters", filename)

            if not os.path.exists(path):
                print(f"  ⚠️ {name}素材不存在: {path}")
                continue

            # 确定初始位置
            if name == "豆包":
                init_x, init_y, init_scale = AVATAR_X, AVATAR_Y, 0.3
                init_alpha = 1.0
            elif name == "机器人":
                init_x, init_y, init_scale = 1.5, AVATAR_Y, 0.25
                init_alpha = 0.0
            elif name == "女杀手":
                init_x, init_y, init_scale = -0.5, -1.5, 0.2
                init_alpha = 0.0
            else:
                init_x, init_y, init_scale = 0, 0, 0.3
                init_alpha = 1.0

            seg = self.project.add_media_safe(path, "0s", f"{duration}s", f"Char_{name}")
            seg.add_keyframe(draft.KeyframeProperty.position_x, 0, init_x)
            seg.add_keyframe(draft.KeyframeProperty.position_y, 0, init_y)
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, 0, init_scale)
            seg.add_keyframe(draft.KeyframeProperty.alpha, 0, init_alpha)
            seg.add_keyframe(draft.KeyframeProperty.rotation, 0, 0.0)

            self.segments[name] = seg
            self.segment_ids[name] = seg.id if hasattr(seg, 'id') else str(id(seg))
            print(f"  ✅ {name}: ({init_x:.3f}, {init_y:.3f}) scale={init_scale} alpha={init_alpha}")

    def _apply_actions(self):
        """应用动作关键帧"""
        print(f"\n[3/7] 应用动作关键帧")
        for char in self.semantic["characters"]:
            name = char["name"]
            if name not in self.segments:
                continue
            seg = self.segments[name]
            actions = char.get("actions", [])

            for action in actions:
                action_type = action.get("action_type", "idle")
                t = action.get("time", 0)
                intensity = action.get("intensity", 0.5)
                dur = action.get("duration", 0.5)
                direction = action.get("direction", "")
                emotion = action.get("emotion", "neutral")

                t_us = int(t * 1e6)
                dur_us = int(dur * 1e6)

                if name == "豆包":
                    self._apply_doubao_action(seg, action_type, t_us, dur_us, intensity, direction)
                elif name == "机器人":
                    self._apply_robot_action(seg, action_type, t_us, dur_us, intensity, direction)
                elif name == "女杀手":
                    self._apply_killer_action(seg, action_type, t_us, dur_us, intensity, direction)

            print(f"  ✅ {name}: {len(actions)}个动作")

    def _apply_doubao_action(self, seg, action_type, t_us, dur_us, intensity, direction):
        """豆包动作"""
        if action_type == "idle":
            # 呼吸动画
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, t_us, 0.30)
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, t_us + dur_us // 2, 0.31)
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, t_us + dur_us, 0.30)

        elif action_type == "impact":
            # 被打：震动+下沉+旋转+缩放
            base_y = AVATAR_Y - 0.05 * intensity
            # 震动
            for i, (dx, dy) in enumerate([(0.03, 0.02), (-0.02, -0.03), (0.02, 0.01), (0, 0)]):
                tt = t_us + int(dur_us * i / 4)
                seg.add_keyframe(draft.KeyframeProperty.position_x, tt, AVATAR_X + dx * intensity)
                seg.add_keyframe(draft.KeyframeProperty.position_y, tt, base_y + dy * intensity)
            # 旋转
            rot = (-1 if direction == "left" else 1) * (10 + intensity * 20)
            seg.add_keyframe(draft.KeyframeProperty.rotation, t_us, 0)
            seg.add_keyframe(draft.KeyframeProperty.rotation, t_us + dur_us // 3, rot)
            seg.add_keyframe(draft.KeyframeProperty.rotation, t_us + dur_us, 0)
            # 缩放（被打压缩）
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, t_us, 0.30)
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, t_us + dur_us // 3, 0.30 - 0.06 * intensity)
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, t_us + dur_us, 0.30)

        elif action_type == "recover":
            # 恢复
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us, AVATAR_Y - 0.03)
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us + dur_us, AVATAR_Y)
            seg.add_keyframe(draft.KeyframeProperty.rotation, t_us, 5)
            seg.add_keyframe(draft.KeyframeProperty.rotation, t_us + dur_us, 0)

        elif action_type == "fall":
            # 倒地（在框内下沉+旋转）
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us, AVATAR_Y)
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us + dur_us, AVATAR_Y - 0.08)
            seg.add_keyframe(draft.KeyframeProperty.rotation, t_us, 0)
            seg.add_keyframe(draft.KeyframeProperty.rotation, t_us + dur_us, -30)
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, t_us, 0.30)
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, t_us + dur_us, 0.25)

    def _apply_robot_action(self, seg, action_type, t_us, dur_us, intensity, direction):
        """机器人动作"""
        if action_type == "enter":
            # 从右侧滑入
            seg.add_keyframe(draft.KeyframeProperty.alpha, t_us, 0)
            seg.add_keyframe(draft.KeyframeProperty.alpha, t_us + 300_000, 1.0)
            seg.add_keyframe(draft.KeyframeProperty.position_x, t_us, 1.5)
            seg.add_keyframe(draft.KeyframeProperty.position_x, t_us + dur_us, -0.35)

        elif action_type == "attack":
            # 出拳：快速前冲+收回
            seg.add_keyframe(draft.KeyframeProperty.position_x, t_us, -0.35)
            seg.add_keyframe(draft.KeyframeProperty.position_x, t_us + int(dur_us * 0.3), -0.55)
            seg.add_keyframe(draft.KeyframeProperty.position_x, t_us + dur_us, -0.35)

        elif action_type == "exit":
            # 退出
            seg.add_keyframe(draft.KeyframeProperty.alpha, t_us, 1.0)
            seg.add_keyframe(draft.KeyframeProperty.alpha, t_us + dur_us, 0)
            seg.add_keyframe(draft.KeyframeProperty.position_x, t_us, -0.35)
            seg.add_keyframe(draft.KeyframeProperty.position_x, t_us + dur_us, 1.5)

    def _apply_killer_action(self, seg, action_type, t_us, dur_us, intensity, direction):
        """女杀手动作"""
        if action_type == "enter":
            # 从下方升起
            seg.add_keyframe(draft.KeyframeProperty.alpha, t_us, 0)
            seg.add_keyframe(draft.KeyframeProperty.alpha, t_us + 300_000, 1.0)
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us, -1.5)
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us + dur_us, 0.15)

        elif action_type == "attack":
            # 出拳：向上冲
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us, 0.15)
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us + int(dur_us * 0.3), 0.25)
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us + dur_us, 0.15)

        elif action_type == "exit":
            # 退出
            seg.add_keyframe(draft.KeyframeProperty.alpha, t_us, 1.0)
            seg.add_keyframe(draft.KeyframeProperty.alpha, t_us + dur_us, 0)
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us, 0.15)
            seg.add_keyframe(draft.KeyframeProperty.position_y, t_us + dur_us, -1.5)

    def _apply_masks(self):
        """应用圆形蒙版"""
        print(f"\n[4/7] 应用圆形蒙版")
        if "豆包" in self.segments:
            seg = self.segments["豆包"]
            # 豆包添加圆形蒙版（头像框裁切）
            result = add_avatar_frame_mask(
                self.project, seg,
                avatar_x=AVATAR_X,
                avatar_y=AVATAR_Y,
                avatar_radius=AVATAR_R,
                feather=3.0,
            )
            print(f"  ✅ 豆包: 圆形蒙版 (status={result['status']})")

            # 被打时蒙版震动
            impact_times = [9.5, 11.8, 14.9, 15.2, 15.5, 15.9]
            for t in impact_times:
                add_mask_shake_keyframes(
                    self.project, seg,
                    start_us=int(t * 1e6),
                    duration_us=300_000,
                    intensity=0.02,
                    base_x=AVATAR_X,
                    base_y=AVATAR_Y,
                )
            print(f"  ✅ 豆包: {len(impact_times)}个蒙版震动")

    def _apply_blend_modes(self):
        """应用混合模式（保存后注入）"""
        print(f"\n[5/7] 应用混合模式（保存后注入）")
        # 这一步在save后执行，先记录需要应用的效果
        self._pending_blend = {
            "impact_times": [9.5, 11.8, 14.9, 15.2, 15.5, 15.9],
            "segments": dict(self.segment_ids),
        }

    def _apply_audio(self, duration: float):
        """应用音效"""
        print(f"\n[6/7] 应用音效")
        audio_path = os.path.join(self.assets_dir, "ref_detail", "audio.wav")
        if os.path.exists(audio_path):
            try:
                self.project.add_audio(audio_path, "0s", f"{duration}s")
                print(f"  ✅ 原视频音频: {os.path.basename(audio_path)}")
            except Exception as e:
                print(f"  ⚠️ 音频添加失败: {e}")
        else:
            print(f"  ⚠️ 音频不存在: {audio_path}")

    def post_save(self, draft_path: str):
        """保存后处理：注入混合模式关键帧"""
        print(f"\n[7/7] 保存后处理：注入混合模式")
        if not hasattr(self, '_pending_blend'):
            return

        impact_times = self._pending_blend["impact_times"]
        segments = self._pending_blend["segments"]

        # 豆包被打时闪白
        if "豆包" in segments:
            for t in impact_times:
                add_blend_flash(
                    draft_path,
                    segments["豆包"],
                    start_us=int(t * 1e6),
                    duration_us=200_000,
                    flash_mode="screen",
                    base_mode="normal",
                )
            print(f"  ✅ 豆包: {len(impact_times)}次闪白")

        # 闪白层
        flash_path = os.path.join(self.assets_dir, "flash_white.png")
        if os.path.exists(flash_path):
            # 闪白层在15.8-16.2s
            pass


def main():
    parser = argparse.ArgumentParser(description="语义驱动工程构建器")
    parser.add_argument("--semantic", required=True, help="语义卡JSON路径")
    parser.add_argument("--assets", required=True, help="素材目录")
    parser.add_argument("--name", default="语义驱动工程", help="工程名")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    args = parser.parse_args()

    builder = SemanticBuilder(args.semantic, args.assets)
    draft_path = builder.build(args.name, args.width, args.height)
    builder.post_save(draft_path)
    print(f"\n🎉 构建完成: {draft_path}")


if __name__ == "__main__":
    main()
