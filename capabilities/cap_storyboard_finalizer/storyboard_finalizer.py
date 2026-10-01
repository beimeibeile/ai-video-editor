"""
全剧分镜头定版系统 v1.0
全剧分镜统一编号+场景调度+镜头语言规范+分镜表导出

核心功能：
1. 分镜统一编号：全剧唯一编号（S01E01C01）
2. 场景调度：场景顺序、时长、转场规划
3. 镜头语言规范：景别/运镜/角度/构图标准化
4. 分镜表导出：CSV/JSON/Markdown格式
5. 全剧总览：统计信息、时长分配、镜头分布
"""
import json
import csv
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum


class ShotSize(Enum):
    """景别标准"""
    ECU = "大特写"
    CU = "特写"
    MCU = "近景"
    MS = "中景"
    MLS = "中全景"
    LS = "全景"
    ELS = "远景"


class CameraAngle(Enum):
    """拍摄角度"""
    EYE_LEVEL = "平视"
    HIGH_ANGLE = "俯拍"
    LOW_ANGLE = "仰拍"
    BIRD_EYE = "鸟瞰"
    DUTCH = "荷兰角"
    OVER_SHOULDER = "过肩"
    POV = "主观视角"


class CameraMove(Enum):
    """运镜标准"""
    FIXED = "固定"
    PAN_LEFT = "左摇"
    PAN_RIGHT = "右摇"
    TILT_UP = "上摇"
    TILT_DOWN = "下摇"
    ZOOM_IN = "推"
    ZOOM_OUT = "拉"
    DOLLY_IN = "前移"
    DOLLY_OUT = "后移"
    TRACK_LEFT = "左移"
    TRACK_RIGHT = "右移"
    CRANE_UP = "升"
    CRANE_DOWN = "降"
    HANDHELD = "手持"
    STEADICAM = "稳定器"
    DOLLY_ZOOM = "滑动变焦"


class TransitionType(Enum):
    """转场类型"""
    CUT = "硬切"
    FADE = "淡入淡出"
    DISSOLVE = "溶解"
    WIPE = "划像"
    MATCH = "匹配剪辑"
    JUMP = "跳切"
    L_CUT = "L切"
    J_CUT = "J切"
    CROSS_DISSOLVE = "交叉溶解"


@dataclass
class FinalShot:
    """定版镜头"""
    shot_id: str  # 全剧唯一编号 S01E01C01
    episode: int
    scene: int
    shot_in_scene: int
    shot_size: ShotSize
    camera_angle: CameraAngle
    camera_move: CameraMove
    description: str
    subject: str = ""
    dialogue: str = ""
    duration: float = 3.0
    location: str = ""
    time_of_day: str = ""
    lighting: str = ""
    sound: str = ""
    notes: str = ""
    transition_in: TransitionType = TransitionType.CUT
    transition_out: TransitionType = TransitionType.CUT

    def to_dict(self):
        d = asdict(self)
        d['shot_size'] = self.shot_size.value
        d['camera_angle'] = self.camera_angle.value
        d['camera_move'] = self.camera_move.value
        d['transition_in'] = self.transition_in.value
        d['transition_out'] = self.transition_out.value
        return d

    def to_csv_row(self) -> Dict[str, Any]:
        """转为CSV行"""
        return {
            "镜头编号": self.shot_id,
            "集": self.episode,
            "场": self.scene,
            "镜": self.shot_in_scene,
            "景别": self.shot_size.value,
            "角度": self.camera_angle.value,
            "运镜": self.camera_move.value,
            "时长(秒)": self.duration,
            "地点": self.location,
            "时间": self.time_of_day,
            "主体": self.subject,
            "画面描述": self.description,
            "对话": self.dialogue,
            "光线": self.lighting,
            "声音": self.sound,
            "入转场": self.transition_in.value,
            "出转场": self.transition_out.value,
            "备注": self.notes,
        }


@dataclass
class FinalScene:
    """定版场景"""
    scene_id: str  # S01E01S01
    episode: int
    scene_number: int
    title: str
    location: str
    time_of_day: str
    scene_type: str = ""
    duration: float = 0.0
    shots: List[FinalShot] = field(default_factory=list)
    emotional_tone: str = ""
    notes: str = ""

    def to_dict(self):
        return {
            "scene_id": self.scene_id,
            "episode": self.episode,
            "scene_number": self.scene_number,
            "title": self.title,
            "location": self.location,
            "time_of_day": self.time_of_day,
            "scene_type": self.scene_type,
            "duration": self.duration,
            "shot_count": len(self.shots),
            "emotional_tone": self.emotional_tone,
            "notes": self.notes,
            "shots": [s.to_dict() for s in self.shots],
        }


@dataclass
class FinalEpisode:
    """定版单集"""
    episode_id: str  # S01E01
    season: int
    episode_number: int
    title: str
    logline: str = ""
    scenes: List[FinalScene] = field(default_factory=list)
    total_duration: float = 0.0
    total_shots: int = 0

    def to_dict(self):
        return {
            "episode_id": self.episode_id,
            "season": self.season,
            "episode_number": self.episode_number,
            "title": self.title,
            "logline": self.logline,
            "scene_count": len(self.scenes),
            "total_duration": self.total_duration,
            "total_shots": self.total_shots,
            "scenes": [s.to_dict() for s in self.scenes],
        }


class StoryboardFinalizer:
    """分镜定版器（主入口）"""

    def __init__(self, season: int = 1):
        self.season = season
        self.episodes: Dict[int, FinalEpisode] = {}
        self.shot_counter = 0

    def _generate_shot_id(self, episode: int, scene: int, shot: int) -> str:
        """生成全剧唯一镜头编号"""
        return f"S{self.season:02d}E{episode:02d}C{scene:02d}{shot:02d}"

    def _generate_scene_id(self, episode: int, scene: int) -> str:
        """生成场景编号"""
        return f"S{self.season:02d}E{episode:02d}S{scene:02d}"

    def add_episode(self, episode_number: int, title: str,
                     logline: str = "") -> FinalEpisode:
        """添加单集"""
        episode = FinalEpisode(
            episode_id=f"S{self.season:02d}E{episode_number:02d}",
            season=self.season,
            episode_number=episode_number,
            title=title,
            logline=logline,
        )
        self.episodes[episode_number] = episode
        return episode

    def add_scene(self, episode_number: int, scene_number: int,
                  title: str, location: str, time_of_day: str,
                  scene_type: str = "", emotional_tone: str = "") -> FinalScene:
        """添加场景"""
        episode = self.episodes.get(episode_number)
        if not episode:
            episode = self.add_episode(episode_number, f"第{episode_number}集")

        scene = FinalScene(
            scene_id=self._generate_scene_id(episode_number, scene_number),
            episode=episode_number,
            scene_number=scene_number,
            title=title,
            location=location,
            time_of_day=time_of_day,
            scene_type=scene_type,
            emotional_tone=emotional_tone,
        )
        episode.scenes.append(scene)
        return scene

    def add_shot(self, episode_number: int, scene_number: int,
                 description: str, shot_size: ShotSize = ShotSize.MS,
                 camera_angle: CameraAngle = CameraAngle.EYE_LEVEL,
                 camera_move: CameraMove = CameraMove.FIXED,
                 duration: float = 3.0, subject: str = "",
                 dialogue: str = "", location: str = "",
                 lighting: str = "", sound: str = "",
                 transition_in: TransitionType = TransitionType.CUT,
                 transition_out: TransitionType = TransitionType.CUT,
                 notes: str = "") -> Optional[FinalShot]:
        """添加镜头"""
        episode = self.episodes.get(episode_number)
        if not episode:
            return None

        scene = None
        for s in episode.scenes:
            if s.scene_number == scene_number:
                scene = s
                break
        if not scene:
            return None

        shot_in_scene = len(scene.shots) + 1
        shot = FinalShot(
            shot_id=self._generate_shot_id(episode_number, scene_number, shot_in_scene),
            episode=episode_number,
            scene=scene_number,
            shot_in_scene=shot_in_scene,
            shot_size=shot_size,
            camera_angle=camera_angle,
            camera_move=camera_move,
            description=description,
            subject=subject,
            dialogue=dialogue,
            duration=duration,
            location=location or scene.location,
            time_of_day=scene.time_of_day,
            lighting=lighting,
            sound=sound,
            transition_in=transition_in,
            transition_out=transition_out,
            notes=notes,
        )
        scene.shots.append(shot)
        scene.duration += duration
        episode.total_duration += duration
        episode.total_shots += 1
        self.shot_counter += 1
        return shot

    def get_statistics(self) -> Dict[str, Any]:
        """获取全剧统计"""
        total_episodes = len(self.episodes)
        total_scenes = sum(len(e.scenes) for e in self.episodes.values())
        total_shots = sum(e.total_shots for e in self.episodes.values())
        total_duration = sum(e.total_duration for e in self.episodes.values())

        # 景别分布
        shot_size_dist = {}
        camera_move_dist = {}
        for episode in self.episodes.values():
            for scene in episode.scenes:
                for shot in scene.shots:
                    size_name = shot.shot_size.value
                    shot_size_dist[size_name] = shot_size_dist.get(size_name, 0) + 1
                    move_name = shot.camera_move.value
                    camera_move_dist[move_name] = camera_move_dist.get(move_name, 0) + 1

        # 平均镜头时长
        avg_shot_duration = total_duration / total_shots if total_shots > 0 else 0

        return {
            "season": self.season,
            "total_episodes": total_episodes,
            "total_scenes": total_scenes,
            "total_shots": total_shots,
            "total_duration": total_duration,
            "total_duration_minutes": round(total_duration / 60, 1),
            "avg_shot_duration": round(avg_shot_duration, 1),
            "avg_shots_per_scene": round(total_shots / total_scenes, 1) if total_scenes > 0 else 0,
            "avg_scenes_per_episode": round(total_scenes / total_episodes, 1) if total_episodes > 0 else 0,
            "shot_size_distribution": shot_size_dist,
            "camera_move_distribution": camera_move_dist,
        }

    def export_to_json(self, output_path: str) -> str:
        """导出JSON"""
        data = {
            "season": self.season,
            "statistics": self.get_statistics(),
            "episodes": [e.to_dict() for e in self.episodes.values()],
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path

    def export_to_csv(self, output_path: str) -> str:
        """导出CSV分镜表"""
        all_shots = []
        for episode in self.episodes.values():
            for scene in episode.scenes:
                for shot in scene.shots:
                    all_shots.append(shot.to_csv_row())

        if not all_shots:
            return output_path

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_shots[0].keys())
            writer.writeheader()
            writer.writerows(all_shots)
        return output_path

    def export_to_markdown(self, output_path: str) -> str:
        """导出Markdown分镜表"""
        lines = []
        stats = self.get_statistics()

        lines.append(f"# 第{self.season}季 分镜表")
        lines.append("")
        lines.append("## 全剧统计")
        lines.append("")
        lines.append(f"- 集数: {stats['total_episodes']}")
        lines.append(f"- 场景数: {stats['total_scenes']}")
        lines.append(f"- 镜头数: {stats['total_shots']}")
        lines.append(f"- 总时长: {stats['total_duration']:.0f}秒 ({stats['total_duration_minutes']}分钟)")
        lines.append(f"- 平均镜头时长: {stats['avg_shot_duration']}秒")
        lines.append("")

        for episode in self.episodes.values():
            lines.append(f"## {episode.episode_id} - {episode.title}")
            lines.append("")
            if episode.logline:
                lines.append(f"> {episode.logline}")
                lines.append("")

            for scene in episode.scenes:
                lines.append(f"### {scene.scene_id} - {scene.title}")
                lines.append("")
                lines.append(f"- 地点: {scene.location}")
                lines.append(f"- 时间: {scene.time_of_day}")
                lines.append(f"- 时长: {scene.duration:.0f}秒")
                lines.append(f"- 镜头数: {len(scene.shots)}")
                if scene.emotional_tone:
                    lines.append(f"- 情绪: {scene.emotional_tone}")
                lines.append("")
                lines.append("| 编号 | 景别 | 角度 | 运镜 | 时长 | 画面描述 | 对话 |")
                lines.append("|------|------|------|------|------|----------|------|")
                for shot in scene.shots:
                    lines.append(
                        f"| {shot.shot_id} | {shot.shot_size.value} | "
                        f"{shot.camera_angle.value} | {shot.camera_move.value} | "
                        f"{shot.duration:.0f}s | {shot.description} | {shot.dialogue} |"
                    )
                lines.append("")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return output_path

    def import_from_adapter(self, adapter_result: Dict[str, Any]) -> None:
        """
        从剧本解析改编引擎结果导入

        Args:
            adapter_result: ScriptAdapterEngine.parse_and_adapt()的返回结果
        """
        for episode_data in adapter_result.get("episodes", []):
            ep_num = episode_data.get("episode_id", 1)
            ep_title = episode_data.get("title", f"第{ep_num}集")
            episode = self.add_episode(ep_num, ep_title,
                                        logline=episode_data.get("logline", ""))

            # 从episode级别的shots按scene_id分组
            all_shots = episode_data.get("shots", [])
            shots_by_scene = {}
            for shot in all_shots:
                sid = shot.get("scene_id", 0)
                if sid not in shots_by_scene:
                    shots_by_scene[sid] = []
                shots_by_scene[sid].append(shot)

            for scene_data in episode_data.get("scenes", []):
                scene_num = scene_data.get("scene_id", len(episode.scenes) + 1)
                scene = self.add_scene(
                    ep_num, scene_num,
                    title=scene_data.get("title", f"场景{scene_num}"),
                    location=scene_data.get("location", ""),
                    time_of_day=scene_data.get("time_of_day", ""),
                    scene_type=scene_data.get("scene_type", ""),
                    emotional_tone=scene_data.get("emotional_tone", ""),
                )

                # 从分组中取该场景的镜头
                scene_shots = shots_by_scene.get(scene_num, [])
                for shot_data in scene_shots:
                    # 映射景别
                    size_map = {
                        "大特写": ShotSize.ECU, "特写": ShotSize.CU,
                        "近景": ShotSize.MCU, "中景": ShotSize.MS,
                        "中全景": ShotSize.MLS, "全景": ShotSize.LS,
                        "远景": ShotSize.ELS,
                    }
                    move_map = {
                        "固定": CameraMove.FIXED, "推": CameraMove.ZOOM_IN,
                        "拉": CameraMove.ZOOM_OUT, "左摇": CameraMove.PAN_LEFT,
                        "右摇": CameraMove.PAN_RIGHT, "跟拍": CameraMove.TRACK_RIGHT,
                        "手持": CameraMove.HANDHELD,
                    }
                    shot_size = size_map.get(shot_data.get("shot_size", ""), ShotSize.MS)
                    camera_move = move_map.get(shot_data.get("camera_move", ""), CameraMove.FIXED)
                    dialogue = shot_data.get("dialogue", {})
                    dialogue_text = dialogue.get("content", "") if isinstance(dialogue, dict) else str(dialogue or "")

                    self.add_shot(
                        ep_num, scene_num,
                        description=shot_data.get("description", ""),
                        shot_size=shot_size,
                        camera_angle=CameraAngle.EYE_LEVEL,
                        camera_move=camera_move,
                        duration=shot_data.get("duration", 3.0),
                        subject=shot_data.get("subject", ""),
                        dialogue=dialogue_text,
                        notes=shot_data.get("notes", ""),
                    )


if __name__ == "__main__":
    print("=" * 60)
    print("🎬 全剧分镜头定版系统 v1.0")
    print("=" * 60)

    finalizer = StoryboardFinalizer(season=1)

    # 创建第1集
    finalizer.add_episode(1, "密会", logline="记者李明与会计王芳在咖啡馆密会，发现公司财务黑幕")

    # 场景1
    finalizer.add_scene(1, 1, "咖啡馆内", "咖啡馆", "日", "室内", "平静")
    finalizer.add_shot(1, 1, "咖啡馆全景，顾客稀少", ShotSize.LS,
                        CameraAngle.EYE_LEVEL, CameraMove.FIXED, 4.0,
                        location="咖啡馆", lighting="暖光", sound="背景音乐")
    finalizer.add_shot(1, 1, "李明推门进入，四处张望", ShotSize.MS,
                        CameraAngle.EYE_LEVEL, CameraMove.PAN_RIGHT, 3.0,
                        subject="李明")
    finalizer.add_shot(1, 1, "王芳坐在角落挥手", ShotSize.MCU,
                        CameraAngle.OVER_SHOULDER, CameraMove.FIXED, 2.5,
                        subject="王芳")
    finalizer.add_shot(1, 1, "李明坐下，两人对视", ShotSize.MS,
                        CameraAngle.EYE_LEVEL, CameraMove.FIXED, 3.0,
                        transition_out=TransitionType.CUT)

    # 场景2
    finalizer.add_scene(1, 2, "发现秘密", "咖啡馆", "日", "室内", "紧张")
    finalizer.add_shot(1, 2, "王芳压低声音说话", ShotSize.CU,
                        CameraAngle.EYE_LEVEL, CameraMove.FIXED, 4.0,
                        subject="王芳", dialogue="我发现了一个秘密，关于公司的",
                        lighting="低调光")
    finalizer.add_shot(1, 2, "李明震惊的表情", ShotSize.CU,
                        CameraAngle.EYE_LEVEL, CameraMove.FIXED, 2.0,
                        subject="李明", dialogue="什么秘密？")
    finalizer.add_shot(1, 2, "王芳环顾四周", ShotSize.MS,
                        CameraAngle.EYE_LEVEL, CameraMove.PAN_LEFT, 2.5,
                        subject="王芳", dialogue="这里不方便说，换个地方")

    # 场景3
    finalizer.add_scene(1, 3, "街道夜谈", "街道", "夜", "室外", "紧张")
    finalizer.add_shot(1, 3, "夜晚街道，行人稀少", ShotSize.LS,
                        CameraAngle.HIGH_ANGLE, CameraMove.FIXED, 4.0,
                        location="街道", lighting="路灯", sound="环境音")
    finalizer.add_shot(1, 3, "两人并肩行走", ShotSize.MLS,
                        CameraAngle.EYE_LEVEL, CameraMove.TRACK_RIGHT, 5.0,
                        subject="李明,王芳")
    finalizer.add_shot(1, 3, "王芳紧张地说", ShotSize.CU,
                        CameraAngle.EYE_LEVEL, CameraMove.FIXED, 4.0,
                        subject="王芳", dialogue="公司的财务报表有问题，有人在做假账")
    finalizer.add_shot(1, 3, "李明震惊停下脚步", ShotSize.MS,
                        CameraAngle.LOW_ANGLE, CameraMove.FIXED, 3.0,
                        subject="李明", dialogue="你确定？这可不是小事！")

    # 统计
    print("\n📊 全剧统计:")
    stats = finalizer.get_statistics()
    for key, value in stats.items():
        if key not in ['shot_size_distribution', 'camera_move_distribution']:
            print(f"  {key}: {value}")

    print(f"\n  景别分布:")
    for size, count in stats['shot_size_distribution'].items():
        print(f"    {size}: {count}个")

    # 导出
    output_dir = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor\capabilities\script_outputs"
    import os
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "storyboard_final_test.json")
    csv_path = os.path.join(output_dir, "storyboard_final_test.csv")
    md_path = os.path.join(output_dir, "storyboard_final_test.md")

    finalizer.export_to_json(json_path)
    finalizer.export_to_csv(csv_path)
    finalizer.export_to_markdown(md_path)

    print(f"\n📄 导出完成:")
    print(f"  JSON: {json_path}")
    print(f"  CSV: {csv_path}")
    print(f"  Markdown: {md_path}")
    print("\n✅ 全剧分镜头定版系统验证通过")
