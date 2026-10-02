"""
短视频标签模式 Pipeline v1.0
标签驱动的短视频全自动生成：标签输入 → 素材生成 → 特效匹配 → 卡点合成 → 剪映工程

与剧类电影模式的区别：
- 短视频：碎片剪辑组合再创作，标签驱动，特效库+转场+卡点+文字动画
- 剧类：镜头语言的电影模式，I2V真正动态视频，分镜量化字段
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional

# 路径配置
SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
JY_SKILL = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities", "cap_creative"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

from tag_engine import TagEngine
from real_bgm_generator import RealBGMGenerator


class ShortVideoPipeline:
    """短视频标签模式pipeline"""

    def __init__(self, output_dir: str = None):
        self.tag_engine = TagEngine()
        self.bgm_gen = RealBGMGenerator()
        if output_dir is None:
            output_dir = os.path.join(SKILL_ROOT, "capabilities", "cap_creative", "short_video_output")
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run(self, tags: List[str], duration: float = 15.0,
            text_lines: List[str] = None, project_name: str = "ShortVideo") -> Dict[str, Any]:
        """
        执行短视频标签模式全流程

        Args:
            tags: 标签列表（如["赛博朋克", "卡点", "发光", "大字报"]）
            duration: 视频时长（秒）
            text_lines: 文字内容列表（每段一个文字）
            project_name: 工程名

        Returns:
            完整产出信息
        """
        print(f"\n{'='*60}")
        print(f"短视频标签模式 Pipeline v1.0")
        print(f"{'='*60}")
        print(f"标签: {tags}")
        print(f"时长: {duration}s")

        # Step 1: 标签匹配
        print(f"\n[Step 1/5] 标签匹配...")
        preset = self.tag_engine.generate_preset(tags, duration)
        print(f"  风格: {preset['style']}")
        print(f"  剪辑数: {preset['num_cuts']}")
        print(f"  特效: {preset['effects']}")
        print(f"  BGM情绪: {preset['bgm_mood']}")

        # Step 2: 生成BGM
        print(f"\n[Step 2/5] 生成真实BGM...")
        bgm_path = os.path.join(self.output_dir, f"{project_name}_bgm.wav")
        bgm_result = self.bgm_gen.generate(
            mood=preset["bgm_mood"],
            duration=duration,
            bpm=120,
            output_path=bgm_path
        )
        if bgm_result and os.path.exists(bgm_result):
            print(f"  ✅ BGM: {bgm_result} ({os.path.getsize(bgm_result)//1024}KB)")
        else:
            print(f"  ⚠️ BGM生成失败")

        # Step 3: 生成文字素材（如果有文字内容）
        text_assets = []
        if text_lines:
            print(f"\n[Step 3/5] 生成文字素材...")
            for i, text in enumerate(text_lines):
                print(f"  文字{i+1}: {text}")
                text_assets.append({"text": text, "index": i})

        # Step 4: 构建剪映工程
        print(f"\n[Step 4/5] 构建剪映工程...")
        draft_path = self._build_jianying_project(
            project_name=project_name,
            preset=preset,
            duration=duration,
            text_lines=text_lines or [],
            bgm_path=bgm_result,
        )

        # Step 5: 输出报告
        print(f"\n[Step 5/5] 生成报告...")
        report = {
            "project_name": project_name,
            "tags": tags,
            "normalized_tags": preset.get("tags", []),
            "style": preset["style"],
            "duration": duration,
            "num_cuts": preset["num_cuts"],
            "effects": preset["effects"],
            "transition": preset["transition"],
            "text_style": preset["text_style"],
            "bgm_mood": preset["bgm_mood"],
            "bgm_path": bgm_result,
            "draft_path": draft_path,
            "text_assets": text_assets,
            "status": "success",
        }

        report_path = os.path.join(self.output_dir, f"{project_name}_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"✅ 短视频标签模式完成")
        print(f"  工程: {draft_path}")
        print(f"  BGM: {bgm_result}")
        print(f"  报告: {report_path}")
        print(f"{'='*60}")

        return report

    def _build_jianying_project(self, project_name: str, preset: Dict,
                                 duration: float, text_lines: List[str],
                                 bgm_path: str) -> str:
        """构建剪映工程"""
        try:
            from jy_wrapper import JyProject
            import pyJianYingDraft as draft
        except ImportError:
            print("  ⚠️ jianying-editor不可用，跳过工程构建")
            return ""

        try:
            project = JyProject(project_name, width=1080, height=1920, overwrite=True)

            cut_interval = preset.get("cut_interval", 2.0)
            num_cuts = preset.get("num_cuts", max(1, int(duration / cut_interval)))
            actual_cut = duration / num_cuts

            # 添加背景色块（占位，实际使用时替换为素材）
            from PIL import Image
            bg_colors = [
                (20, 20, 30), (30, 20, 40), (20, 30, 40),
                (40, 20, 30), (30, 30, 20), (20, 40, 30),
            ]
            for i in range(num_cuts):
                color = bg_colors[i % len(bg_colors)]
                bg_path = os.path.join(self.output_dir, f"bg_{i}.png")
                img = Image.new("RGB", (1080, 1920), color)
                img.save(bg_path)

                start = i * actual_cut
                seg = project.add_media_safe(
                    bg_path,
                    start_time=f"{start:.2f}s",
                    duration=f"{actual_cut:.2f}s",
                    track_name="VideoMain",
                )

                # 运镜
                if seg:
                    camera_move = preset.get("camera_move", "缓推")
                    move_map = {
                        "快推": ("zoom_in", 0.2), "缓推": ("zoom_in", 0.08),
                        "缓拉": ("zoom_out", 0.08), "手持": ("handheld", 0.1),
                    }
                    move_type, intensity = move_map.get(camera_move, ("zoom_in", 0.08))
                    try:
                        from camera_moves import add_camera_move
                        add_camera_move(seg, move_type, int(actual_cut * 1e6), intensity)
                    except Exception:
                        pass

            # 添加文字
            if text_lines:
                text_dur = duration / len(text_lines)
                text_style = preset.get("text_style", {})
                text_params = text_style.get("params", {})
                font_size = text_params.get("size", 12.0)

                for i, text in enumerate(text_lines):
                    start = i * text_dur
                    text_seg = project.add_text_simple(
                        text=text,
                        start_time=f"{start:.2f}s",
                        duration=f"{text_dur:.2f}s",
                        track_name=f"Text_{i}",
                        style=draft.TextStyle(size=font_size, color=(1.0, 1.0, 1.0)),
                        anim_in="弹入",
                    )

            # 添加BGM
            if bgm_path and os.path.exists(bgm_path):
                try:
                    project.add_audio_safe(bgm_path, start_time="0s", track_name="BGM")
                except Exception as e:
                    print(f"  ⚠️ BGM添加失败: {e}")

            # 保存
            result = project.save()
            draft_path = result.get("draft_path", "")
            print(f"  ✅ 工程已构建: {draft_path}")
            print(f"     {num_cuts}个片段, {len(text_lines)}条文字, BGM={'有' if bgm_path else '无'}")
            return draft_path

        except Exception as e:
            print(f"  ❌ 工程构建失败: {e}")
            import traceback
            traceback.print_exc()
            return ""


if __name__ == "__main__":
    pipeline = ShortVideoPipeline()

    # 测试：赛博朋克卡点短视频
    report = pipeline.run(
        tags=["赛博朋克", "卡点", "发光", "大字报"],
        duration=15.0,
        text_lines=["AI视频编辑", "标签驱动", "特效自动匹配", "一键出片"],
        project_name="CyberPunk_Demo",
    )
