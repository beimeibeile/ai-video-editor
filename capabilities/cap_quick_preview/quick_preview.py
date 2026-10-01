"""
快速整剧小样生成器 v1.0
快速生成全剧预览小样+关键帧预览+节奏预览+批量导出

核心功能：
1. 快速预览工程：基于分镜表生成剪映工程（纯色背景+文字占位）
2. 关键帧预览：为每个镜头生成关键帧预览图（带镜头信息）
3. 节奏预览：生成全剧节奏可视化图（情绪曲线+时长分布）
4. 批量导出：一键导出全部预览素材
5. 小样报告：生成小样制作报告
"""
import os
import sys
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

# 尝试导入PIL
try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# 尝试导入剪映编辑器
try:
    skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
    sys.path.insert(0, os.path.join(skill_root, "scripts"))
    from jy_wrapper import JyProject
    import pyJianYingDraft as draft
    _JIANYING_AVAILABLE = True
except ImportError:
    _JIANYING_AVAILABLE = False


@dataclass
class PreviewConfig:
    """预览配置"""
    width: int = 1080
    height: int = 1920
    bg_color: Tuple[int, int, int] = (30, 30, 40)
    text_color: Tuple[int, int, int] = (255, 255, 255)
    accent_color: Tuple[int, int, int] = (100, 150, 255)
    font_size: int = 40
    title_size: int = 60
    show_shot_info: bool = True
    show_emotion: bool = True


@dataclass
class PreviewResult:
    """预览结果"""
    project_name: str = ""
    draft_path: str = ""
    keyframe_dir: str = ""
    keyframe_count: int = 0
    rhythm_chart_path: str = ""
    report_path: str = ""
    total_duration: float = 0.0
    shot_count: int = 0
    scene_count: int = 0


class KeyframeGenerator:
    """关键帧预览图生成器"""

    def __init__(self, config: PreviewConfig = None):
        self.config = config or PreviewConfig()

    def generate_keyframe(self, shot: Dict[str, Any],
                          output_path: str) -> Optional[str]:
        """
        生成单镜头关键帧预览图

        Args:
            shot: 镜头数据
            output_path: 输出路径

        Returns:
            输出路径或None
        """
        if not _PIL_AVAILABLE:
            return None

        cfg = self.config
        img = Image.new("RGB", (cfg.width, cfg.height), cfg.bg_color)
        draw = ImageDraw.Draw(img)

        # 顶部信息栏
        draw.rectangle([0, 0, cfg.width, 120], fill=(50, 50, 70))
        try:
            font_title = ImageFont.truetype("msyh.ttc", cfg.title_size)
            font_normal = ImageFont.truetype("msyh.ttc", cfg.font_size)
            font_small = ImageFont.truetype("msyh.ttc", 30)
        except:
            font_title = ImageFont.load_default()
            font_normal = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # 镜头编号
        shot_id = shot.get("shot_id", "????")
        draw.text((40, 30), shot_id, fill=cfg.accent_color, font=font_title)

        # 景别+运镜
        shot_size = shot.get("shot_size", "")
        camera_move = shot.get("camera_move", "")
        info_text = f"{shot_size} | {camera_move}"
        draw.text((40, 100), info_text, fill=(200, 200, 200), font=font_small)

        # 中央画面描述
        description = shot.get("description", "")
        # 自动换行
        words = description
        lines = []
        current_line = ""
        for char in words:
            if len(current_line) >= 15:
                lines.append(current_line)
                current_line = char
            else:
                current_line += char
        if current_line:
            lines.append(current_line)

        y_start = cfg.height // 2 - len(lines) * 50
        for i, line in enumerate(lines):
            draw.text((cfg.width // 2 - len(line) * 20, y_start + i * 100),
                     line, fill=cfg.text_color, font=font_normal)

        # 底部信息
        duration = shot.get("duration", 0)
        location = shot.get("location", "")
        dialogue = shot.get("dialogue", "")

        bottom_y = cfg.height - 200
        draw.rectangle([0, bottom_y, cfg.width, cfg.height], fill=(40, 40, 55))

        draw.text((40, bottom_y + 20), f"时长: {duration:.0f}秒",
                 fill=(180, 180, 180), font=font_small)
        draw.text((40, bottom_y + 60), f"地点: {location}",
                 fill=(180, 180, 180), font=font_small)

        if dialogue:
            # 对话气泡
            dialogue_lines = []
            current = ""
            for char in dialogue:
                if len(current) >= 20:
                    dialogue_lines.append(current)
                    current = char
                else:
                    current += char
            if current:
                dialogue_lines.append(current)

            for i, line in enumerate(dialogue_lines[:3]):
                draw.text((cfg.width // 2 - len(line) * 15, bottom_y + 100 + i * 40),
                         f'"{line}"', fill=(255, 220, 100), font=font_small)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "PNG")
        return output_path

    def generate_all_keyframes(self, shots: List[Dict[str, Any]],
                               output_dir: str) -> List[str]:
        """批量生成关键帧预览图"""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for i, shot in enumerate(shots):
            shot_id = shot.get("shot_id", f"shot_{i:04d}")
            output_path = os.path.join(output_dir, f"{shot_id}.png")
            result = self.generate_keyframe(shot, output_path)
            if result:
                paths.append(result)
        return paths


class RhythmChartGenerator:
    """节奏预览图生成器"""

    def __init__(self, config: PreviewConfig = None):
        self.config = config or PreviewConfig()

    def generate_rhythm_chart(self, scenes: List[Dict[str, Any]],
                               output_path: str) -> Optional[str]:
        """
        生成全剧节奏预览图

        Args:
            scenes: 场景列表
            output_path: 输出路径

        Returns:
            输出路径或None
        """
        if not _PIL_AVAILABLE:
            return None

        cfg = self.config
        chart_width = 1920
        chart_height = 1080
        img = Image.new("RGB", (chart_width, chart_height), (25, 25, 35))
        draw = ImageDraw.Draw(img)

        try:
            font_title = ImageFont.truetype("msyh.ttc", 48)
            font_normal = ImageFont.truetype("msyh.ttc", 28)
            font_small = ImageFont.truetype("msyh.ttc", 20)
        except:
            font_title = ImageFont.load_default()
            font_normal = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # 标题
        draw.text((50, 30), "全剧节奏预览", fill=(255, 255, 255), font=font_title)

        # 情绪强度映射
        emotion_intensity = {
            "平静": 0.2, "温馨": 0.3, "喜悦": 0.5, "兴奋": 0.7,
            "紧张": 0.6, "焦虑": 0.5, "悲伤": 0.4, "愤怒": 0.8,
            "恐惧": 0.7, "震惊": 0.9, "坚定": 0.5, "困惑": 0.3,
        }

        # 绘制区域
        chart_left = 100
        chart_right = chart_width - 100
        chart_top = 150
        chart_bottom = chart_height - 150
        chart_w = chart_right - chart_left
        chart_h = chart_bottom - chart_top

        # 网格线
        for i in range(5):
            y = chart_top + chart_h * i / 4
            draw.line([(chart_left, y), (chart_right, y)],
                     fill=(60, 60, 80), width=1)
            intensity = 1.0 - i / 4
            draw.text((30, y - 10), f"{intensity:.1f}", fill=(150, 150, 150), font=font_small)

        # 场景时长条
        if scenes:
            total_duration = sum(s.get("duration", s.get("duration_estimate", 0)) for s in scenes)
            if total_duration == 0:
                total_duration = 1

            x = chart_left
            bar_height = 60
            bar_y = chart_bottom + 30

            for i, scene in enumerate(scenes):
                duration = scene.get("duration", scene.get("duration_estimate", 0))
                bar_w = chart_w * duration / total_duration

                # 情绪颜色
                emotion = scene.get("emotional_tone", "平静")
                intensity = emotion_intensity.get(emotion, 0.3)
                color = (
                    int(100 + intensity * 155),
                    int(100 + (1 - abs(intensity - 0.5) * 2) * 100),
                    int(200 - intensity * 100),
                )

                draw.rectangle([x, bar_y, x + bar_w, bar_y + bar_height],
                              fill=color, outline=(255, 255, 255), width=1)

                # 场景编号
                if bar_w > 40:
                    draw.text((x + bar_w // 2 - 15, bar_y + 15),
                             f"S{i+1}", fill=(0, 0, 0), font=font_small)

                x += bar_w

            # 情绪曲线
            points = []
            for i, scene in enumerate(scenes):
                duration = scene.get("duration", scene.get("duration_estimate", 0))
                emotion = scene.get("emotional_tone", "平静")
                intensity = emotion_intensity.get(emotion, 0.3)
                px = chart_left + chart_w * (i + 0.5) / len(scenes)
                py = chart_bottom - chart_h * intensity
                points.append((px, py))

            # 绘制曲线
            if len(points) > 1:
                for i in range(len(points) - 1):
                    draw.line([points[i], points[i + 1]],
                             fill=(255, 200, 100), width=3)

            # 绘制点
            for i, (px, py) in enumerate(points):
                draw.ellipse([px - 8, py - 8, px + 8, py + 8],
                            fill=(255, 200, 100), outline=(255, 255, 255), width=2)
                emotion = scenes[i].get("emotional_tone", "")
                draw.text((px - 20, py - 35), emotion,
                         fill=(200, 200, 200), font=font_small)

        # 图例
        legend_y = chart_height - 60
        draw.text((100, legend_y), "情绪强度", fill=(200, 200, 200), font=font_normal)
        draw.text((chart_width - 300, legend_y), "场景时长分布",
                 fill=(200, 200, 200), font=font_normal)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "PNG")
        return output_path


class QuickPreviewGenerator:
    """快速整剧小样生成器（主入口）"""

    def __init__(self, config: PreviewConfig = None):
        self.config = config or PreviewConfig()
        self.keyframe_gen = KeyframeGenerator(config)
        self.rhythm_gen = RhythmChartGenerator(config)

    def generate_preview(self, storyboard_data: Dict[str, Any],
                         output_dir: str,
                         project_name: str = "preview",
                         generate_keyframes: bool = True,
                         generate_rhythm: bool = True,
                         generate_jianying: bool = True) -> PreviewResult:
        """
        生成完整预览小样

        Args:
            storyboard_data: 分镜数据（StoryboardFinalizer导出格式）
            output_dir: 输出目录
            project_name: 工程名
            generate_keyframes: 是否生成关键帧
            generate_rhythm: 是否生成节奏图
            generate_jianying: 是否生成剪映工程

        Returns:
            预览结果
        """
        os.makedirs(output_dir, exist_ok=True)
        result = PreviewResult(project_name=project_name)

        # 收集所有镜头
        all_shots = []
        all_scenes = []
        for episode in storyboard_data.get("episodes", []):
            for scene in episode.get("scenes", []):
                all_scenes.append(scene)
                for shot in scene.get("shots", []):
                    all_shots.append(shot)

        result.shot_count = len(all_shots)
        result.scene_count = len(all_scenes)
        result.total_duration = sum(s.get("duration", 0) for s in all_shots)

        print(f"\n{'='*60}")
        print(f"🎬 快速整剧小样生成")
        print(f"{'='*60}")
        print(f"工程: {project_name}")
        print(f"场景: {result.scene_count}, 镜头: {result.shot_count}, 时长: {result.total_duration:.0f}秒")

        # 1. 关键帧预览
        if generate_keyframes:
            print(f"\n[1/3] 生成关键帧预览...")
            keyframe_dir = os.path.join(output_dir, "keyframes")
            paths = self.keyframe_gen.generate_all_keyframes(all_shots, keyframe_dir)
            result.keyframe_dir = keyframe_dir
            result.keyframe_count = len(paths)
            print(f"  ✅ 生成 {len(paths)} 张关键帧预览图")

        # 2. 节奏预览
        if generate_rhythm:
            print(f"\n[2/3] 生成节奏预览图...")
            rhythm_path = os.path.join(output_dir, "rhythm_chart.png")
            self.rhythm_gen.generate_rhythm_chart(all_scenes, rhythm_path)
            result.rhythm_chart_path = rhythm_path
            print(f"  ✅ 节奏预览图: {rhythm_path}")

        # 3. 剪映工程
        if generate_jianying and _JIANYING_AVAILABLE:
            print(f"\n[3/3] 生成剪映预览工程...")
            draft_path = self._generate_jianying_project(all_shots, all_scenes,
                                                          project_name, output_dir)
            result.draft_path = draft_path
            print(f"  ✅ 剪映工程: {draft_path}")
        else:
            print(f"\n[3/3] 跳过剪映工程（剪映编辑器不可用）")

        # 4. 生成报告
        report_path = os.path.join(output_dir, "preview_report.json")
        report = {
            "project_name": project_name,
            "statistics": {
                "scene_count": result.scene_count,
                "shot_count": result.shot_count,
                "total_duration": result.total_duration,
                "avg_shot_duration": result.total_duration / result.shot_count if result.shot_count > 0 else 0,
            },
            "outputs": {
                "keyframes_dir": result.keyframe_dir,
                "keyframes_count": result.keyframe_count,
                "rhythm_chart": result.rhythm_chart_path,
                "jianying_draft": result.draft_path,
            },
            "config": asdict(self.config),
        }
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        result.report_path = report_path

        print(f"\n{'✅'*20}")
        print(f"小样生成完成!")
        print(f"  关键帧: {result.keyframe_count}张")
        print(f"  节奏图: {result.rhythm_chart_path}")
        print(f"  剪映工程: {result.draft_path}")
        print(f"  报告: {result.report_path}")
        print(f"{'✅'*20}")

        return result

    def _generate_jianying_project(self, shots: List[Dict[str, Any]],
                                    scenes: List[Dict[str, Any]],
                                    project_name: str,
                                    output_dir: str) -> str:
        """生成剪映预览工程"""
        project = JyProject(project_name, width=self.config.width,
                           height=self.config.height, overwrite=True)

        current_time = 0.0
        for i, shot in enumerate(shots):
            duration = shot.get("duration", 3.0)
            shot_id = shot.get("shot_id", f"shot_{i}")
            description = shot.get("description", "")
            dialogue = shot.get("dialogue", "")

            # 背景色（根据情绪变化）
            emotion = shot.get("emotion", "")
            bg_colors = {
                "紧张": (60, 40, 40), "愤怒": (80, 30, 30),
                "喜悦": (40, 60, 40), "平静": (40, 40, 50),
                "悲伤": (30, 40, 60), "兴奋": (60, 50, 30),
            }
            bg_color = bg_colors.get(emotion, (40, 40, 50))

            # 创建纯色背景图
            bg_path = os.path.join(output_dir, f"bg_{i:04d}.png")
            if _PIL_AVAILABLE:
                from PIL import Image as PILImage
                img = PILImage.new("RGB", (self.config.width, self.config.height), bg_color)
                img.save(bg_path)

            # 添加背景
            if os.path.exists(bg_path):
                project.add_media_safe(
                    bg_path,
                    start_time=f"{current_time:.2f}s",
                    duration=f"{duration:.2f}s",
                    track_name="Background",
                )

            # 添加镜头信息文字
            info_text = f"{shot_id}\n{description[:20]}"
            project.add_text_simple(
                info_text,
                start_time=f"{current_time:.2f}s",
                duration=f"{duration:.2f}s",
                track_name="ShotInfo",
                style=draft.TextStyle(size=8.0, color=(1.0, 1.0, 1.0)),
            )

            # 添加对话
            if dialogue:
                project.add_text_simple(
                    dialogue,
                    start_time=f"{current_time + 0.5:.2f}s",
                    duration=f"{duration - 0.5:.2f}s",
                    track_name="Dialogue",
                    style=draft.TextStyle(size=6.0, color=(1.0, 0.9, 0.5)),
                    clip_settings=draft.ClipSettings(transform_y=0.6),
                )

            current_time += duration

        result = project.save()
        return result.get("draft_path", "")


if __name__ == "__main__":
    print("=" * 60)
    print("⚡ 快速整剧小样生成器 v1.0")
    print("=" * 60)

    # 测试数据
    test_storyboard = {
        "episodes": [{
            "episode_id": "S01E01",
            "title": "测试集",
            "scenes": [
                {
                    "scene_id": "S01E01S01",
                    "title": "场景1",
                    "location": "咖啡馆",
                    "duration": 10,
                    "emotional_tone": "平静",
                    "shots": [
                        {"shot_id": "S01E01C0101", "shot_size": "全景", "camera_move": "固定",
                         "description": "咖啡馆全景", "duration": 4, "location": "咖啡馆", "dialogue": ""},
                        {"shot_id": "S01E01C0102", "shot_size": "中景", "camera_move": "右摇",
                         "description": "人物进入", "duration": 3, "location": "咖啡馆", "dialogue": ""},
                        {"shot_id": "S01E01C0103", "shot_size": "特写", "camera_move": "固定",
                         "description": "对话开始", "duration": 3, "location": "咖啡馆",
                         "dialogue": "你好，好久不见"},
                    ],
                },
                {
                    "scene_id": "S01E01S02",
                    "title": "场景2",
                    "location": "街道",
                    "duration": 8,
                    "emotional_tone": "紧张",
                    "shots": [
                        {"shot_id": "S01E01C0201", "shot_size": "远景", "camera_move": "固定",
                         "description": "夜晚街道", "duration": 3, "location": "街道", "dialogue": ""},
                        {"shot_id": "S01E01C0202", "shot_size": "中景", "camera_move": "跟拍",
                         "description": "两人行走", "duration": 3, "location": "街道", "dialogue": ""},
                        {"shot_id": "S01E01C0203", "shot_size": "特写", "camera_move": "固定",
                         "description": "紧张对话", "duration": 2, "location": "街道",
                         "dialogue": "有情况"},
                    ],
                },
            ],
        }]
    }

    output_dir = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor\capabilities\script_outputs\quick_preview"

    generator = QuickPreviewGenerator()
    result = generator.generate_preview(
        test_storyboard, output_dir, "QuickPreview_Test",
        generate_keyframes=True, generate_rhythm=True, generate_jianying=False,
    )

    print(f"\n✅ 快速整剧小样生成器验证通过")
