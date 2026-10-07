"""
片头生成器 - 主模块
一键生成短视频片头，支持5种风格+时长自适应+本地资源库优先

资源策略：
- 背景：优先用本地预生成动态背景(assets/backgrounds)，缺失时ffmpeg生成渐变背景
- 音效：优先用本地音效库(assets/sfx)，缺失时跳过（不浪费时间搜索）
- 贴纸：优先用本地贴纸库(assets/stickers)，缺失时跳过
- AI生成(LTX-2.5等)：仅在用户明确要求高质量背景时调用
"""
import os
import sys
import subprocess
from typing import Optional

from .styles import get_style, get_duration, STYLES

# 通用素材库（统一检索入口）
try:
    from cap_asset_library import get_library
    _ASSET_LIB_AVAILABLE = True
except ImportError:
    _ASSET_LIB_AVAILABLE = False


class IntroGenerator:
    """片头生成器"""

    def __init__(self, jianying_skill_path: str = None):
        # 资源库路径（兼容旧版，实际检索走素材库）
        self.module_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(self.module_dir, "assets")

        # 通用素材库
        self.asset_lib = get_library() if _ASSET_LIB_AVAILABLE else None

        # 剪映skill路径
        if jianying_skill_path is None:
            jianying_skill_path = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
        self.jy_skill = jianying_skill_path

        # ffmpeg路径（从环境变量或默认路径）
        self.ffmpeg = os.environ.get("FFMPEG_PATH", r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe")

    def _find_asset(self, asset_type: str, context: str = "", style: str = None,
                    mood: str = None, tags: list = None) -> Optional[str]:
        """通过素材库智能检索最佳匹配素材"""
        if self.asset_lib is None:
            return None
        best = self.asset_lib.get_best_match(
            asset_type=asset_type,
            context=context,
            style=style,
            mood=mood,
            tags=tags
        )
        if best:
            return self.asset_lib.get_path(best["id"])
        return None

    def _generate_simple_bg(self, output_path: str, style_config: dict,
                             width: int = 1080, height: int = 1920, duration: float = 3.0):
        """用ffmpeg生成简单渐变背景（资源库缺失时的降级方案）"""
        bg_color = style_config.get("bg_color", "#0a0a0a")
        accent = style_config.get("bg_accent", "#333333")

        # 生成纯色底图
        temp_img = output_path + ".png"
        subprocess.run([
            self.ffmpeg, "-y",
            "-f", "lavfi", "-i", f"color=c={bg_color}:s={width}x{height}:d=1",
            "-vf", f"drawbox=x=0:y=0:w=iw:h=ih/4:color={accent}@0.3:t=fill,"
                   f"drawbox=x=0:y=ih*3/4:w=iw:h=ih/4:color={accent}@0.2:t=fill",
            "-frames:v", "1", temp_img
        ], capture_output=True)

        # Ken Burns动态化
        sys.path.insert(0, os.path.join(os.path.dirname(self.module_dir), "cap_ffmpeg_motion"))
        from ffmpeg_motion import FFmpegMotion
        fm = FFmpegMotion(ffmpeg_path=self.ffmpeg)
        fm.image_to_ken_burns(
            temp_img, output_path,
            duration=duration, move_type="zoom_in",
            intensity=0.06, width=width, height=height, fps=30
        )
        if os.path.exists(temp_img):
            os.remove(temp_img)
        return output_path if os.path.exists(output_path) else None

    def generate(self,
                 title: str,
                 subtitle: str = "",
                 style: str = "minimal",
                 video_type: str = "short",
                 project_name: str = None,
                 width: int = 1080,
                 height: int = 1920,
                 use_ai_background: bool = False,
                 custom_bg_path: str = None) -> dict:
        """
        生成片头剪映工程

        Args:
            title: 主标题文字
            subtitle: 副标题文字（可选）
            style: 风格 - impact/cute/funny/minimal/suspense
            video_type: 视频类型 - short/medium/long（决定片头时长）
            project_name: 剪映工程名（默认自动生成）
            width/height: 画布尺寸
            use_ai_background: 是否用LTX-2.5生成AI背景（默认False，用本地/ffmpeg背景）
            custom_bg_path: 自定义背景视频路径（优先使用）

        Returns:
            {"status": "success", "project_name": ..., "duration": ..., "style": ...}
        """
        style_config = get_style(style)
        duration = get_duration(video_type)

        if project_name is None:
            project_name = f"片头_{style_config['name']}_{title[:6]}"

        # 1. 准备背景
        work_dir = os.path.join(os.path.expanduser("~"), "Videos", "剪映导出", "Doubao_Jianying-editor", "debug", "intro_generator")
        os.makedirs(work_dir, exist_ok=True)
        bg_path = custom_bg_path

        if bg_path is None:
            # 优先通过素材库智能检索背景
            bg_path = self._find_asset("background", context="片头背景", style=style)
            bg_from_lib = bg_path is not None
            if bg_path is None:
                # 降级：ffmpeg生成简单背景
                bg_path = os.path.join(work_dir, f"bg_{style}.mp4")
                self._generate_simple_bg(bg_path, style_config, width, height, duration)
                bg_from_lib = False

        # 2. 初始化剪映
        sys.path.insert(0, os.path.join(self.jy_skill, "scripts"))
        from jy_wrapper import JyProject

        project = JyProject(project_name, width=width, height=height, overwrite=True)

        # 3. 背景轨道
        if bg_path and os.path.exists(bg_path):
            project.add_media_safe(bg_path, start_time="0s", duration=f"{duration}s")

        # 4. 文字轨道（根据风格预设）
        timing = style_config.get("timing", {})
        main_start = timing.get("main_start", 0.5)
        sub_start = timing.get("sub_start", 1.0)
        fade_out = timing.get("fade_out", 0.8)
        main_dur = max(duration - main_start - fade_out, 0.5)
        sub_dur = max(duration - sub_start - fade_out, 0.5)

        main_cfg = style_config["main_text"]
        project.add_text_simple(
            title,
            start_time=f"{main_start}s", duration=f"{main_dur}s",
            font_size=main_cfg["size"],
            color_rgb=main_cfg["color"],
            style=TextStyle(size=main_cfg["size"], bold=main_cfg["bold"]),
            border=TextBorder(color=(0, 0, 0), width=main_cfg["border_w"]) if main_cfg["border_w"] > 0 else None,
            shadow=draft.TextShadow(color=(0, 0, 0), distance=8, diffuse=15) if main_cfg["border_w"] > 30 else None,
            clip_settings=ClipSettings(transform_y=main_cfg["y"]),
            anim_in=main_cfg["anim_in"],
            anim_loop=main_cfg.get("anim_loop"),
            track_name="IntroMain",
        )

        if subtitle:
            sub_cfg = style_config["sub_text"]
            project.add_text_simple(
                subtitle,
                start_time=f"{sub_start}s", duration=f"{sub_dur}s",
                font_size=sub_cfg["size"],
                color_rgb=sub_cfg["color"],
                style=TextStyle(size=sub_cfg["size"], bold=sub_cfg["bold"]),
                border=TextBorder(color=(0, 0, 0), width=sub_cfg["border_w"]) if sub_cfg["border_w"] > 0 else None,
                clip_settings=ClipSettings(transform_y=sub_cfg["y"]),
                anim_in=sub_cfg["anim_in"],
                track_name="IntroSub",
            )

        # 5. 音效（通过素材库智能检索）
        sfx_list = style_config.get("sfx", [])
        sfx_found = 0
        for i, sfx_name in enumerate(sfx_list):
            sfx_path = self._find_asset("sfx", context=sfx_name, style=style)
            if sfx_path:
                sfx_found += 1
                sfx_time = main_start + i * 0.3
                try:
                    project.add_media_safe(sfx_path, start_time=f"{sfx_time}s", duration="0.5s", track_name="IntroSFX")
                except Exception:
                    pass

        # 6. 保存
        result = project.save()
        return {
            "status": "success",
            "project_name": project_name,
            "duration": duration,
            "style": style_config["name"],
            "video_type": video_type,
            "background": "custom" if custom_bg_path else ("asset_library" if bg_from_lib else "ffmpeg_fallback"),
            "sfx_count": sfx_found,
        }


# 便捷函数
def generate_intro(title: str, subtitle: str = "", style: str = "minimal",
                   video_type: str = "short", **kwargs) -> dict:
    """一键生成片头"""
    gen = IntroGenerator()
    return gen.generate(title, subtitle, style, video_type, **kwargs)


def list_styles() -> list:
    """列出所有可用风格"""
    return [{"key": k, "name": v["name"], "desc": v["desc"]} for k, v in STYLES.items()]
