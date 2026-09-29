"""
端到端视频生成流程 (E2E Pipeline)
整合：分镜引擎 → 素材加工(LTX-2.5/ffmpeg) → 剪映合成

流程：
1. 创意文案生成（cap_creative_engine）
2. 分镜生成（cap_storyboard_engine）
3. 素材加工（LTX-2.5 I2V / ffmpeg Ken Burns）
4. 剪映合成（转场+字幕+音效+BGM）
"""
import os
import sys
import json
from typing import List, Dict, Optional, Any

# 模块路径
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL_ROOT)

from cap_storyboard_engine import generate_storyboard, Storyboard
from cap_asset_library import get_library


class E2EPipeline:
    """端到端视频生成流程"""

    def __init__(self,
                 project_dir: str = None,
                 jianying_skill_path: str = None,
                 ffmpeg_path: str = None,
                 comfyui_addr: str = "http://127.0.0.1:8188"):
        # 项目目录
        if project_dir is None:
            project_dir = os.path.join(os.path.expanduser("~"), "Videos", "剪映导出", "Doubao_Jianying-editor")
        self.project_dir = project_dir
        self.work_dir = os.path.join(project_dir, "debug", "e2e_pipeline")
        os.makedirs(os.path.join(self.work_dir, "input"), exist_ok=True)
        os.makedirs(os.path.join(self.work_dir, "output"), exist_ok=True)

        # 剪映
        if jianying_skill_path is None:
            jianying_skill_path = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
        self.jy_skill = jianying_skill_path

        # ffmpeg
        self.ffmpeg = ffmpeg_path or r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

        # ComfyUI
        self.comfyui_addr = comfyui_addr

        # 素材库
        self.asset_lib = get_library()

    def run(self,
            theme: str,
            style: str = "cinematic",
            duration: float = 15.0,
            shot_count: int = 5,
            project_name: str = None,
            width: int = 1080,
            height: int = 1920,
            hook_text: str = "",
            ending_text: str = "",
            custom_subtitles: List[str] = None,
            input_images: List[str] = None,
            use_ltx: bool = True,
            ltx_shots: List[int] = None,
            add_bgm: bool = True,
            add_intro: bool = False) -> Dict[str, Any]:
        """
        执行端到端流程

        Args:
            theme: 视频主题
            style: 风格 cinematic/vlog/tutorial/thriller/emotional
            duration: 总时长（秒）
            shot_count: 镜头数量
            project_name: 剪映工程名
            width/height: 画布尺寸
            hook_text: 钩子文案
            ending_text: 结尾文案
            custom_subtitles: 自定义字幕列表
            input_images: 用户素材图片路径列表
            use_ltx: 是否使用LTX-2.5 I2V（需要ComfyUI运行）
            ltx_shots: 使用LTX的镜头索引列表（默认[0]，即第一个镜头）
            add_bgm: 是否添加BGM
            add_intro: 是否添加片头

        Returns:
            {"status": "success", "project_name": ..., "storyboard": ..., "video_clips": [...]}
        """
        if project_name is None:
            project_name = f"E2E_{theme}_{style}"

        if ltx_shots is None:
            ltx_shots = [0] if use_ltx else []

        print(f"{'='*60}")
        print(f"端到端视频生成: {theme}")
        print(f"风格: {style} | 时长: {duration}s | 镜头: {shot_count}")
        print(f"{'='*60}")

        # ==================== 步骤1：分镜生成 ====================
        print("\n[1/4] 分镜生成")
        sb = generate_storyboard(
            theme=theme, style=style, total_duration=duration,
            shot_count=shot_count, hook_text=hook_text,
            ending_text=ending_text, custom_subtitles=custom_subtitles,
        )
        print(sb.summary())

        # 保存分镜
        sb_path = os.path.join(self.work_dir, f"{project_name}_storyboard.json")
        with open(sb_path, 'w', encoding='utf-8') as f:
            f.write(sb.to_json())

        # ==================== 步骤2：素材准备 ====================
        print("\n[2/4] 素材加工")
        video_clips = self._prepare_materials(
            sb, input_images, width, height, use_ltx, ltx_shots, project_name
        )

        # ==================== 步骤3：剪映合成 ====================
        print("\n[3/4] 剪映合成")
        result = self._build_jianying(
            sb, video_clips, project_name, width, height, add_bgm
        )

        # ==================== 步骤4：片头（可选） ====================
        if add_intro:
            print("\n[4/4] 添加片头")
            # 片头生成逻辑（调用cap_intro_generator）
            pass
        else:
            print("\n[4/4] 跳过片头")

        print(f"\n{'='*60}")
        print(f"完成: {project_name}")
        print(f"{'='*60}")

        return {
            "status": "success",
            "project_name": project_name,
            "storyboard": sb.to_dict(),
            "storyboard_path": sb_path,
            "video_clips": video_clips,
            "work_dir": self.work_dir,
        }

    def _prepare_materials(self, sb: Storyboard, input_images: List[str],
                           width: int, height: int, use_ltx: bool,
                           ltx_shots: List[int], project_name: str) -> List[str]:
        """素材加工：生成/动态化每个镜头的视频"""
        from cap_ffmpeg_motion.ffmpeg_motion import FFmpegMotion
        fm = FFmpegMotion(ffmpeg_path=self.ffmpeg)

        # 色调对应的基础颜色
        tone_colors = {
            "冷": "#1a2a3a", "暖": "#3a2a1a", "中性": "#2a2a2a",
            "高对比": "#0a0a0a", "低饱和": "#3a3a3a",
        }

        # 运镜映射
        move_map = {
            "推": "zoom_in", "拉": "zoom_out", "快推": "zoom_in",
            "缓推": "zoom_in", "缓拉": "zoom_out",
            "移右": "pan_right", "移左": "pan_left",
            "固定": "zoom_in", "快切": "zoom_in",
        }

        video_clips = []
        for i, shot in enumerate(sb.shots):
            out_path = os.path.join(self.work_dir, "output", f"{project_name}_shot_{i:02d}.mp4")

            # 确定输入图片
            if input_images and i < len(input_images):
                img_path = input_images[i]
            else:
                # 生成占位图
                img_path = os.path.join(self.work_dir, "input", f"{project_name}_shot_{i:02d}.png")
                if not os.path.exists(img_path):
                    import subprocess
                    color = tone_colors.get(shot.color_tone, "#2a2a2a")
                    subprocess.run([
                        self.ffmpeg, "-y",
                        "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:d=1",
                        "-vf", "drawbox=x=0:y=0:w=iw:h=ih/3:color=ffffff@0.05:t=fill,"
                               "drawbox=x=0:y=ih*2/3:w=iw:h=ih/3:color=000000@0.2:t=fill",
                        "-frames:v", "1", img_path
                    ], capture_output=True)

            # 动态化
            move_type = move_map.get(shot.camera_move, "zoom_in")

            if use_ltx and i in ltx_shots:
                # LTX-2.5 I2V（需要ComfyUI运行）
                ltx_success = self._try_ltx_i2v(img_path, out_path, shot, width, height)
                if not ltx_success:
                    # 降级为Ken Burns
                    print(f"  镜头{i}: LTX失败，降级Ken Burns")
                    fm.image_to_ken_burns(
                        img_path, out_path, duration=shot.duration,
                        move_type=move_type, intensity=shot.move_intensity,
                        width=width, height=height, fps=30
                    )
            else:
                fm.image_to_ken_burns(
                    img_path, out_path, duration=shot.duration,
                    move_type=move_type, intensity=shot.move_intensity,
                    width=width, height=height, fps=30
                )

            video_clips.append(out_path)
            size_kb = os.path.getsize(out_path) // 1024 if os.path.exists(out_path) else 0
            print(f"  镜头{i}: {shot.camera_move}({move_type}) 强度{shot.move_intensity} -> {size_kb}KB")

        return video_clips

    def _try_ltx_i2v(self, img_path: str, out_path: str, shot,
                     width: int, height: int) -> bool:
        """尝试LTX-2.5 I2V，失败返回False"""
        try:
            from cap_comfyui_runner.api import img2video_ltx25, check_comfyui_ready
            if not check_comfyui_ready(self.comfyui_addr):
                return False

            # LTX-2.5尺寸限制（必须能被32整除）
            ltx_w = (width // 32) * 32
            ltx_h = (height // 32) * 32
            frames = max(int(shot.duration * 24), 24)

            result = img2video_ltx25(
                image_path=img_path,
                output_path=out_path,
                prompt=f"{shot.subtitle}，{shot.emotion}氛围，{shot.shot_size}，电影感",
                width=ltx_w, height=ltx_h,
                frames=frames, fps=24,
                steps=10, seed=-1,
                strength=0.7,
                server_addr=self.comfyui_addr,
                timeout=300,
            )
            return result and os.path.exists(out_path)
        except Exception as e:
            print(f"  LTX I2V异常: {e}")
            return False

    def _build_jianying(self, sb: Storyboard, video_clips: List[str],
                        project_name: str, width: int, height: int,
                        add_bgm: bool) -> Dict:
        """剪映合成"""
        sys.path.insert(0, os.path.join(self.jy_skill, "scripts"))
        from jy_wrapper import JyProject
        import pyJianYingDraft as draft

        # 艺术字幕
        sys.path.insert(0, os.path.join(SKILL_ROOT, "..", "scripts"))
        try:
            from artistic_subtitle import add_artistic_subtitle
        except ImportError:
            add_artistic_subtitle = None

        project = JyProject(project_name, width=width, height=height, overwrite=True)

        # 1. 添加视频片段
        segments = []
        current_time = 0.0
        for i, shot in enumerate(sb.shots):
            if i >= len(video_clips):
                break
            seg = project.add_media_safe(
                video_clips[i],
                start_time=f"{current_time:.2f}s",
                duration=f"{shot.duration:.2f}s"
            )
            if seg:
                segments.append(seg)
            current_time += shot.duration
        print(f"  添加 {len(segments)} 个视频片段")

        # 2. 转场（加在前一个片段末尾）
        trans_count = 0
        for i in range(1, len(segments)):
            shot = sb.shots[i]
            if shot.transition_in == "无":
                continue
            try:
                trans_map = {
                    "叠化": "叠化", "快切": "闪黑", "闪白": "闪白",
                    "黑场": "渐黑", "淡入": "淡入淡出",
                }
                trans_type = trans_map.get(shot.transition_in, "叠化")
                segments[i-1].add_transition(
                    getattr(draft.TransitionType, trans_type, draft.TransitionType.叠化),
                    duration=int(shot.transition_duration * 1_000_000)
                )
                trans_count += 1
            except Exception as e:
                print(f"  转场{i}失败: {e}")
        print(f"  添加 {trans_count} 个转场")

        # 3. 字幕
        sub_count = 0
        current_time = 0.0
        for i, shot in enumerate(sb.shots):
            if shot.subtitle and add_artistic_subtitle:
                add_artistic_subtitle(
                    project,
                    main_text=shot.subtitle,
                    start_time=f"{current_time + 0.2:.2f}s",
                    duration=f"{max(shot.duration - 0.4, 0.5):.2f}s",
                    style=shot.subtitle_style,
                )
                sub_count += 1
            current_time += shot.duration
        print(f"  添加 {sub_count} 个字幕")

        # 4. 音效（从素材库智能匹配）
        sfx_count = 0
        current_time = 0.0
        for i, shot in enumerate(sb.shots):
            if shot.sfx_hint:
                best = self.asset_lib.get_best_match(
                    "sfx", context=shot.sfx_hint, style=sb.intro_style
                )
                if best:
                    sfx_path = self.asset_lib.get_path(best["id"])
                    try:
                        project.add_media_safe(
                            sfx_path, start_time=f"{current_time:.2f}s",
                            duration="0.5s", track_name="SFX"
                        )
                        sfx_count += 1
                    except Exception:
                        pass
            current_time += shot.duration
        print(f"  添加 {sfx_count} 个音效")

        # 5. BGM
        if add_bgm and sb.bgm_mood:
            try:
                project.add_cloud_music(
                    sb.bgm_mood, start_time="0s",
                    duration=f"{sb.total_duration}s", track_name="BGM"
                )
                print(f"  BGM: {sb.bgm_mood}")
            except Exception as e:
                print(f"  BGM失败: {e}")

        # 保存
        result = project.save()
        return {"status": "success", "segments": len(segments), "transitions": trans_count}


# ==================== 便捷函数 ====================

def create_video(theme: str, style: str = "cinematic",
                 duration: float = 15.0, shot_count: int = 5,
                 **kwargs) -> Dict[str, Any]:
    """一键生成视频"""
    pipeline = E2EPipeline()
    return pipeline.run(theme, style, duration, shot_count, **kwargs)
