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

# 创意引擎（可选，用于自动生成创意字幕）
try:
    from cap_creative_engine import CreativeEngine
    _CREATIVE_ENGINE_AVAILABLE = True
except ImportError:
    _CREATIVE_ENGINE_AVAILABLE = False


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
            use_flf2v: bool = False,
            flf2v_shots: List[int] = None,
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
        if flf2v_shots is None:
            flf2v_shots = []

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

        # 创意引擎字幕优化（如果用户未提供自定义字幕）
        if custom_subtitles is None and _CREATIVE_ENGINE_AVAILABLE:
            try:
                creative = CreativeEngine()
                creative_sb = creative.generate_storyboard(
                    theme=theme, num_shots=shot_count,
                    hook=hook_text, use_hot_trends=True,
                )
                creative_subtitles = [s.subtitle for s in creative_sb.shots if s.subtitle]
                if creative_subtitles:
                    for i, shot in enumerate(sb.shots):
                        if i < len(creative_subtitles):
                            shot.subtitle = creative_subtitles[i]
                    print(f"  创意字幕: 已优化 {len(creative_subtitles)} 个镜头字幕")
            except Exception as e:
                print(f"  创意字幕优化跳过: {e}")

        print(sb.summary())

        # 保存分镜
        sb_path = os.path.join(self.work_dir, f"{project_name}_storyboard.json")
        with open(sb_path, 'w', encoding='utf-8') as f:
            f.write(sb.to_json())

        # ==================== 步骤2：素材准备 ====================
        print("\n[2/4] 素材加工")
        video_clips = self._prepare_materials(
            sb, input_images, width, height, use_ltx, ltx_shots,
            use_flf2v, flf2v_shots, project_name
        )

        # ==================== 步骤3：剪映合成（含片头） ====================
        print("\n[3/4] 剪映合成")
        intro_duration = 2.0 if add_intro else 0.0
        result = self._build_jianying(
            sb, video_clips, project_name, width, height, add_bgm,
            add_intro=add_intro, intro_duration=intro_duration,
            intro_style=sb.intro_style,
        )

        print(f"\n[4/4] {'片头已集成' if add_intro else '跳过片头'}")

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
                           ltx_shots: List[int], use_flf2v: bool = False,
                           flf2v_shots: List[int] = None, project_name: str = "") -> List[str]:
        if flf2v_shots is None:
            flf2v_shots = []
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

        # 批量LTX优化：收集所有需要LTX的镜头，一次性批量生成
        ltx_shot_indices = [i for i in range(len(sb.shots)) if use_ltx and i in ltx_shots]
        ltx_results = {}  # {shot_index: output_path}
        if len(ltx_shot_indices) > 1:
            print(f"  批量LTX: {len(ltx_shot_indices)}个镜头将批量生成")
            ltx_results = self._batch_ltx_i2v(sb, input_images, ltx_shot_indices, width, height, project_name)

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

            if use_flf2v and i in flf2v_shots:
                # FLF2V首尾帧：首帧=当前图，尾帧=下一镜头图（最后一镜头尾帧=当前图）
                last_img = input_images[i+1] if (input_images and i+1 < len(input_images)) else img_path
                flf_success = self._try_flf2v(img_path, last_img, out_path, shot, width, height)
                if not flf_success:
                    print(f"  镜头{i}: FLF2V失败，降级Ken Burns")
                    fm.image_to_ken_burns(
                        img_path, out_path, duration=shot.duration,
                        move_type=move_type, intensity=shot.move_intensity,
                        width=width, height=height, fps=30
                    )
            elif use_ltx and i in ltx_shots:
                # 优先使用批量结果
                if i in ltx_results and ltx_results[i] and os.path.exists(ltx_results[i]):
                    out_path = ltx_results[i]
                    print(f"  镜头{i}: 使用批量LTX结果")
                else:
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

        # 素材质检
        print(f"\n  素材质检:")
        for i, clip in enumerate(video_clips):
            qc = self._validate_clip(clip)
            if qc.get("valid"):
                print(f"    镜头{i}: ✅ {qc['width']}x{qc['height']} {qc['fps']}fps {qc['duration']:.1f}s {qc['size_mb']}MB")
            else:
                print(f"    镜头{i}: ❌ {qc.get('reason', '未知')}")

        return video_clips

    def _add_intro_to_project(self, project, sb: Storyboard,
                               duration: float, style: str,
                               width: int, height: int, draft) -> float:
        """在剪映工程中添加片头轨道，返回片头时长（秒）"""
        import subprocess

        # 片头风格配置
        intro_styles = {
            "impact": {"bg_color": "#0a0a1a", "accent": "#ff4444", "main_size": 16, "main_color": (1, 0.9, 0.3), "anim": "放大", "y": 0.3},
            "cute": {"bg_color": "#1a0a1a", "accent": "#ff88cc", "main_size": 13, "main_color": (1, 0.7, 0.9), "anim": "弹入", "y": 0.2},
            "funny": {"bg_color": "#1a1a0a", "accent": "#ffcc00", "main_size": 14, "main_color": (1, 0.9, 0.2), "anim": "弹性伸缩", "y": 0.25},
            "minimal": {"bg_color": "#0a0a0a", "accent": "#888888", "main_size": 11, "main_color": (1, 1, 1), "anim": "渐显", "y": 0.1},
            "suspense": {"bg_color": "#050510", "accent": "#4444ff", "main_size": 12, "main_color": (0.7, 0.8, 1), "anim": "打字机_I", "y": 0.15},
        }
        cfg = intro_styles.get(style, intro_styles["minimal"])

        # 1. 生成片头背景（优先素材库，降级ffmpeg）
        bg_path = None
        best = self.asset_lib.get_best_match("background", context="片头背景", style=style)
        if best:
            bg_path = self.asset_lib.get_path(best["id"])

        if not bg_path or not os.path.exists(bg_path):
            # ffmpeg生成渐变背景+Ken Burns
            bg_path = os.path.join(self.work_dir, "output", f"{project.name}_intro_bg.mp4")
            temp_img = bg_path + ".png"
            subprocess.run([
                self.ffmpeg, "-y",
                "-f", "lavfi", "-i", f"color=c={cfg['bg_color']}:s={width}x{height}:d=1",
                "-vf", f"drawbox=x=0:y=0:w=iw:h=ih/4:color={cfg['accent']}@0.2:t=fill,"
                       f"drawbox=x=0:y=ih*3/4:w=iw:h=ih/4:color={cfg['accent']}@0.15:t=fill",
                "-frames:v", "1", temp_img
            ], capture_output=True)

            from cap_ffmpeg_motion.ffmpeg_motion import FFmpegMotion
            fm = FFmpegMotion(ffmpeg_path=self.ffmpeg)
            fm.image_to_ken_burns(
                temp_img, bg_path, duration=duration,
                move_type="zoom_in", intensity=0.08,
                width=width, height=height, fps=30
            )
            if os.path.exists(temp_img):
                os.remove(temp_img)

        # 2. 背景轨道
        if bg_path and os.path.exists(bg_path):
            project.add_media_safe(bg_path, start_time="0s", duration=f"{duration}s", track_name="IntroBG")

        # 3. 主标题
        title = sb.hook_text or sb.theme
        project.add_text_simple(
            title,
            start_time="0.3s", duration=f"{max(duration - 0.5, 0.5)}s",
            font_size=cfg["main_size"],
            color_rgb=cfg["main_color"],
            style=draft.TextStyle(size=cfg["main_size"], bold=True),
            border=draft.TextBorder(color=(0, 0, 0), width=50),
            shadow=draft.TextShadow(color=(0, 0, 0), distance=8, diffuse=15),
            clip_settings=draft.ClipSettings(transform_y=cfg["y"]),
            anim_in=cfg["anim"],
            track_name="IntroTitle",
        )

        # 4. 副标题（主题）
        project.add_text_simple(
            sb.theme,
            start_time="0.8s", duration=f"{max(duration - 1.0, 0.5)}s",
            font_size=6.0,
            color_rgb=(0.8, 0.8, 0.8),
            clip_settings=draft.ClipSettings(transform_y=cfg["y"] - 0.25),
            anim_in="渐显",
            track_name="IntroSub",
        )

        # 5. 片头音效
        sfx_best = self.asset_lib.get_best_match("sfx", context="片头冲击", style=style)
        if sfx_best:
            sfx_path = self.asset_lib.get_path(sfx_best["id"])
            try:
                project.add_media_safe(sfx_path, start_time="0.1s", duration="0.5s", track_name="IntroSFX")
            except Exception:
                pass

        return duration

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
                steps=10, seed=None,  # None=内部生成随机种子（LTX不接受-1）
                strength=0.7,
                server_addr=self.comfyui_addr,
                timeout=300,
            )
            return result and os.path.exists(out_path)
        except Exception as e:
            print(f"  LTX I2V异常: {e}")
            return False

    def _batch_ltx_i2v(self, sb: Storyboard, input_images: List[str],
                        shot_indices: List[int], width: int, height: int,
                        project_name: str) -> Dict[int, str]:
        """批量LTX I2V：一次性生成多个镜头的视频（减少模型加载开销）"""
        try:
            from cap_comfyui_runner.api import batch_img2video_ltx25, check_comfyui_ready
            if not check_comfyui_ready(self.comfyui_addr):
                return {}

            ltx_w = (width // 32) * 32
            ltx_h = (height // 32) * 32

            # 收集图片和提示词
            images = []
            prompts = []
            for idx in shot_indices:
                if input_images and idx < len(input_images):
                    img_path = input_images[idx]
                else:
                    img_path = os.path.join(self.work_dir, "input", f"{project_name}_shot_{idx:02d}.png")
                if os.path.exists(img_path):
                    images.append(img_path)
                    shot = sb.shots[idx]
                    prompts.append(f"{shot.subtitle}，{shot.emotion}氛围，{shot.shot_size}，电影感")
                else:
                    images.append(None)
                    prompts.append("")

            # 过滤掉不存在的图片
            valid_pairs = [(idx, img, p) for idx, img, p in zip(shot_indices, images, prompts) if img]
            if not valid_pairs:
                return {}

            valid_indices = [p[0] for p in valid_pairs]
            valid_images = [p[1] for p in valid_pairs]
            valid_prompts = [p[2] for p in valid_pairs]

            output_dir = os.path.join(self.work_dir, "output")
            results = batch_img2video_ltx25(
                image_paths=valid_images,
                output_dir=output_dir,
                prompt="cinematic, high quality",
                per_image_prompts=valid_prompts,
                width=ltx_w, height=ltx_h,
                frames=97, fps=24, steps=10,
                strength=0.7,
                server_addr=self.comfyui_addr,
                timeout_per_video=300,
            )

            # 映射回镜头索引
            ltx_results = {}
            for idx, result in zip(valid_indices, results):
                if result and os.path.exists(result):
                    ltx_results[idx] = result
            return ltx_results
        except Exception as e:
            print(f"  批量LTX异常: {e}")
            return {}

    def _validate_clip(self, video_path: str) -> Dict:
        """素材质检：验证生成的视频片段"""
        try:
            from cap_comfyui_runner.api import get_video_info
            if not os.path.exists(video_path):
                return {"valid": False, "reason": "文件不存在"}
            info = get_video_info(video_path)
            v = info.get("video", {})
            return {
                "valid": True,
                "width": v.get("width", 0),
                "height": v.get("height", 0),
                "fps": v.get("fps", 0),
                "duration": info.get("duration_sec", 0),
                "size_mb": info.get("size_mb", 0),
            }
        except Exception as e:
            return {"valid": False, "reason": str(e)}

    def _try_flf2v(self, first_img: str, last_img: str, out_path: str,
                   shot, width: int, height: int) -> bool:
        """尝试LTX-2.5 FLF2V首尾帧视频，失败返回False"""
        try:
            from cap_comfyui_runner.api import flf2video_ltx25_v2, check_comfyui_ready
            if not check_comfyui_ready(self.comfyui_addr):
                return False

            # FLF2V尺寸限制（必须能被32整除）
            flf_w = (width // 32) * 32
            flf_h = (height // 32) * 32
            frames = max(int(shot.duration * 24), 48)

            result = flf2video_ltx25_v2(
                first_image_path=first_img,
                last_image_path=last_img,
                output_path=out_path,
                prompt=f"{shot.subtitle}，{shot.emotion}氛围，平滑过渡，电影感运镜",
                width=flf_w, height=flf_h,
                frames=frames, fps=24,
                steps=10, seed=None,
                first_strength=1.0, last_strength=1.0,
                server_addr=self.comfyui_addr,
                timeout=300,
            )
            return result and os.path.exists(out_path)
        except Exception as e:
            print(f"  FLF2V异常: {e}")
            return False

    def _build_jianying(self, sb: Storyboard, video_clips: List[str],
                        project_name: str, width: int, height: int,
                        add_bgm: bool, add_intro: bool = False,
                        intro_duration: float = 2.0,
                        intro_style: str = "impact") -> Dict:
        """剪映合成（含片头集成）"""
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

        # 0. 片头（在正片之前）
        intro_offset = 0.0
        if add_intro:
            intro_offset = self._add_intro_to_project(
                project, sb, intro_duration, intro_style, width, height, draft
            )
            print(f"  片头: {intro_duration}s ({intro_style})")

        # 1. 添加视频片段（从片头后开始）
        segments = []
        current_time = intro_offset
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
        print(f"  添加 {len(segments)} 个视频片段 (偏移{intro_offset}s)")

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

        # 3. 字幕（从片头后开始）
        sub_count = 0
        current_time = intro_offset
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

        # 4. 音效（从片头后开始）
        sfx_count = 0
        current_time = intro_offset
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

        # 5. BGM（覆盖片头+正片）
        if add_bgm and sb.bgm_mood:
            total_dur = intro_offset + sb.total_duration
            try:
                project.add_cloud_music(
                    sb.bgm_mood, start_time="0s",
                    duration=f"{total_dur}s", track_name="BGM"
                )
                print(f"  BGM: {sb.bgm_mood} ({total_dur:.1f}s)")
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
