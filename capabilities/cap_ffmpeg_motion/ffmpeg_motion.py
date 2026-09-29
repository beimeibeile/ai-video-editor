"""
FFmpeg 动效工具集
轻量级视频动效处理，零GPU消耗，秒级生成

核心能力：
- Ken Burns效果（图片→动态视频）
- 转场/淡入淡出
- 画中画/多轨合成
- 动态文字条
- 变速/慢动作
- 视频拼接/裁剪
- 抽帧/图片序列
"""
import os
import subprocess
import tempfile
from typing import List, Optional, Tuple, Union


class FFmpegMotion:
    """FFmpeg动效工具类"""

    def __init__(self, ffmpeg_path: str = None):
        if ffmpeg_path is None:
            ffmpeg_path = self._find_ffmpeg()
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")

    @staticmethod
    def _find_ffmpeg() -> str:
        """自动查找ffmpeg路径"""
        import shutil
        path = shutil.which("ffmpeg")
        if path:
            return path
        # 常见路径
        candidates = [
            r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        raise FileNotFoundError("未找到ffmpeg，请安装或指定路径")

    def _run(self, cmd: List[str], timeout: int = 120) -> bool:
        """执行ffmpeg命令"""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace"
            )
            if result.returncode != 0:
                print(f"  ⚠️  ffmpeg错误: {result.stderr[-500:]}")
                return False
            return True
        except subprocess.TimeoutExpired:
            print("  ⚠️  ffmpeg超时")
            return False
        except Exception as e:
            print(f"  ⚠️  ffmpeg异常: {e}")
            return False

    # ==================== Ken Burns 图片动态化 ====================

    def image_to_ken_burns(
        self,
        image_path: str,
        output_path: str,
        duration: float = 3.0,
        move_type: str = "zoom_in",
        intensity: float = 0.15,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
    ) -> str:
        """
        图片→Ken Burns动态视频

        Args:
            image_path: 输入图片路径
            output_path: 输出视频路径
            duration: 视频时长（秒）
            move_type: 运镜类型 zoom_in/zoom_out/pan_left/pan_right/pan_up/pan_down
            intensity: 运动强度（0.05-0.3）
            width/height: 输出分辨率
            fps: 帧率
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # zoompan滤镜参数
        # base_zoom=1.1确保图片始终填满画布（安全边距，防止比例不匹配导致黑边）
        total_frames = int(duration * fps)
        base_zoom = 1.1

        if move_type == "zoom_in":
            zoom_expr = f"min({base_zoom}+{intensity}*on/{total_frames}, 1.5)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif move_type == "zoom_out":
            zoom_expr = f"max({base_zoom}+{intensity}*(1-on/{total_frames}), {base_zoom})"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif move_type == "pan_left":
            zoom_expr = f"{base_zoom}+{intensity}"
            x_expr = f"iw/2-(iw/zoom/2)-{intensity*0.5}*on/{total_frames}*iw"
            y_expr = "ih/2-(ih/zoom/2)"
        elif move_type == "pan_right":
            zoom_expr = f"{base_zoom}+{intensity}"
            x_expr = f"iw/2-(iw/zoom/2)+{intensity*0.5}*on/{total_frames}*iw"
            y_expr = "ih/2-(ih/zoom/2)"
        elif move_type == "pan_up":
            zoom_expr = f"{base_zoom}+{intensity}"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = f"ih/2-(ih/zoom/2)-{intensity*0.5}*on/{total_frames}*ih"
        elif move_type == "pan_down":
            zoom_expr = f"{base_zoom}+{intensity}"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = f"ih/2-(ih/zoom/2)+{intensity*0.5}*on/{total_frames}*ih"
        else:
            zoom_expr = f"min({base_zoom}+{intensity}*on/{total_frames}, 1.5)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"

        vf = (
            f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
            f"d={total_frames}:s={width}x{height}:fps={fps}"
        )

        cmd = [
            self.ffmpeg, "-y",
            "-loop", "1", "-i", image_path,
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-t", str(duration),
            "-r", str(fps),
            output_path,
        ]

        if self._run(cmd):
            return output_path
        return None

    # ==================== 淡入淡出 ====================

    def add_fade_in_out(
        self,
        input_path: str,
        output_path: str,
        fade_in: float = 0.3,
        fade_out: float = 0.3,
        duration: float = None,
    ) -> str:
        """添加淡入淡出效果"""
        if duration is None:
            duration = self._get_duration(input_path)

        fade_out_start = duration - fade_out if duration > fade_out else 0

        vf = f"fade=t=in:st=0:d={fade_in},fade=t=out:st={fade_out_start}:d={fade_out}"

        cmd = [
            self.ffmpeg, "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            output_path,
        ]

        if self._run(cmd):
            return output_path
        return None

    # ==================== 视频拼接 ====================

    def concat_videos(
        self,
        video_paths: List[str],
        output_path: str,
        transition: str = None,
        transition_duration: float = 0.5,
    ) -> str:
        """
        拼接多个视频，可选转场效果

        Args:
            video_paths: 视频路径列表
            output_path: 输出路径
            transition: 转场类型 None/fade/slideleft/slideright/wiperight/wipeleft
            transition_duration: 转场时长
        """
        if len(video_paths) < 2:
            return video_paths[0] if video_paths else None

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if transition is None:
            # 无转场，直接concat
            list_file = output_path + ".txt"
            with open(list_file, "w", encoding="utf-8") as f:
                for p in video_paths:
                    f.write(f"file '{p}'\n")

            cmd = [
                self.ffmpeg, "-y",
                "-f", "concat", "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                output_path,
            ]
            result = self._run(cmd)
            os.remove(list_file) if os.path.exists(list_file) else None
            return output_path if result else None
        else:
            # xfade转场
            return self._concat_with_transition(video_paths, output_path, transition, transition_duration)

    def _concat_with_transition(
        self,
        video_paths: List[str],
        output_path: str,
        transition: str,
        transition_duration: float,
    ) -> str:
        """使用xfade滤镜拼接带转场的视频"""
        # 先获取每个视频时长
        durations = [self._get_duration(p) for p in video_paths]

        # 构建复杂的xfade滤镜链
        # 对于n个视频，需要n-1个xfade
        inputs = []
        for p in video_paths:
            inputs.extend(["-i", p])

        # 构建滤镜图
        filter_parts = []
        current_offset = 0

        for i in range(len(video_paths) - 1):
            if i == 0:
                # 第一个转场：[0][1]xfade
                offset = durations[0] - transition_duration
                filter_parts.append(
                    f"[0:v][1:v]xfade=transition={transition}:duration={transition_duration}:offset={offset}[v1]"
                )
                current_offset = offset
            else:
                # 后续转场：[v_prev][i+1]xfade
                prev_label = f"v{i}"
                next_label = f"v{i+1}" if i < len(video_paths) - 2 else "vout"
                offset = current_offset + durations[i] - transition_duration
                filter_parts.append(
                    f"[{prev_label}][{i+1}:v]xfade=transition={transition}:duration={transition_duration}:offset={offset}[{next_label}]"
                )
                current_offset = offset

        filter_complex = ";".join(filter_parts)
        final_label = f"v{len(video_paths)-2}" if len(video_paths) > 2 else "v1"

        cmd = [
            self.ffmpeg, "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", f"[{final_label}]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path,
        ]

        if self._run(cmd, timeout=300):
            return output_path
        return None

    # ==================== 画中画 ====================

    def picture_in_picture(
        self,
        background_path: str,
        overlay_path: str,
        output_path: str,
        position: str = "bottom_right",
        scale: float = 0.3,
        margin: int = 40,
    ) -> str:
        """
        画中画效果

        Args:
            position: top_left/top_right/bottom_left/bottom_right/center
            scale: 画中画缩放比例（相对于背景宽度）
            margin: 边距（像素）
        """
        # 计算overlay位置
        pos_map = {
            "top_left": f"{margin}:{margin}",
            "top_right": f"W-w-{margin}:{margin}",
            "bottom_left": f"{margin}:H-h-{margin}",
            "bottom_right": f"W-w-{margin}:H-h-{margin}",
            "center": "(W-w)/2:(H-h)/2",
        }
        pos = pos_map.get(position, pos_map["bottom_right"])

        vf = f"[1:v]scale=iw*{scale}:-1[ov];[0:v][ov]overlay={pos}"

        cmd = [
            self.ffmpeg, "-y",
            "-i", background_path,
            "-i", overlay_path,
            "-filter_complex", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            output_path,
        ]

        if self._run(cmd):
            return output_path
        return None

    # ==================== 变速 ====================

    def change_speed(
        self,
        input_path: str,
        output_path: str,
        speed: float = 2.0,
    ) -> str:
        """
        变速播放

        Args:
            speed: 速度倍数（0.5=慢动作一半速度，2.0=2倍速）
        """
        # 视频变速：setpts，音频变速：atempo
        video_speed = 1.0 / speed  # setpts是反向的
        audio_speed = speed

        # 检测是否有音频流
        has_audio = self._has_audio_stream(input_path)

        # atempo只支持0.5-2.0，超出需要链式
        if audio_speed > 2.0:
            audio_filter = f"atempo=2.0,atempo={audio_speed/2.0}"
        elif audio_speed < 0.5:
            audio_filter = f"atempo=0.5,atempo={audio_speed/0.5}"
        else:
            audio_filter = f"atempo={audio_speed}"

        if has_audio:
            cmd = [
                self.ffmpeg, "-y",
                "-i", input_path,
                "-filter_complex",
                f"[0:v]setpts={video_speed}*PTS[v];[0:a]{audio_filter}[a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path,
            ]
        else:
            cmd = [
                self.ffmpeg, "-y",
                "-i", input_path,
                "-filter:v", f"setpts={video_speed}*PTS",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-an",
                output_path,
            ]

        if self._run(cmd):
            return output_path
        return None

    def _has_audio_stream(self, video_path: str) -> bool:
        """检测视频是否有音频流"""
        try:
            result = subprocess.run(
                [self.ffprobe, "-v", "error", "-select_streams", "a",
                 "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
                capture_output=True, text=True, timeout=10
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    # ==================== 动态文字条 ====================

    def add_animated_text_bar(
        self,
        input_path: str,
        output_path: str,
        text: str,
        position: str = "bottom",
        bar_color: str = "black@0.6",
        text_color: str = "white",
        font_size: int = 48,
        start_time: float = 0,
        duration: float = None,
        animate: bool = True,
    ) -> str:
        """
        添加动态文字条（半透明背景条+文字）

        Args:
            position: top/bottom/center
            bar_color: 背景条颜色（支持透明度）
            animate: 是否启用滑入动画
        """
        if duration is None:
            duration = self._get_duration(input_path) - start_time

        # 文字位置
        if position == "top":
            y_pos = "40"
            bar_y = "0"
        elif position == "center":
            y_pos = "(h-text_h)/2"
            bar_y = "(h-text_h-40)/2"
        else:  # bottom
            y_pos = "h-text_h-40"
            bar_y = "h-text_h"

        # 构建滤镜
        filters = []

        # 背景条
        bar_h = font_size + 40
        filters.append(
            f"drawbox=x=0:y=h-{bar_h}:w=iw:h={bar_h}:color={bar_color}:t=fill"
        )

        # 文字（带滑入动画）
        if animate:
            # 从左滑入
            text_expr = (
                f"drawtext=text='{text}':fontsize={font_size}:fontcolor={text_color}:"
                f"x='if(lt(t,{start_time}),-w,min(40,(t-{start_time})*200))':"
                f"y={y_pos}"
            )
        else:
            text_expr = (
                f"drawtext=text='{text}':fontsize={font_size}:fontcolor={text_color}:"
                f"x=40:y={y_pos}:enable='between(t,{start_time},{start_time+duration})'"
            )

        filters.append(text_expr)
        vf = ",".join(filters)

        cmd = [
            self.ffmpeg, "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            output_path,
        ]

        if self._run(cmd):
            return output_path
        return None

    # ==================== 裁剪 ====================

    def crop_video(
        self,
        input_path: str,
        output_path: str,
        start_time: float = 0,
        duration: float = None,
    ) -> str:
        """裁剪视频片段"""
        cmd = [
            self.ffmpeg, "-y",
            "-ss", str(start_time),
            "-i", input_path,
        ]
        if duration:
            cmd.extend(["-t", str(duration)])
        cmd.extend(["-c", "copy", output_path])

        if self._run(cmd):
            return output_path
        return None

    # ==================== 抽帧 ====================

    def extract_frames(
        self,
        input_path: str,
        output_dir: str,
        fps: int = 1,
        prefix: str = "frame",
    ) -> List[str]:
        """从视频中抽取帧"""
        os.makedirs(output_dir, exist_ok=True)
        output_pattern = os.path.join(output_dir, f"{prefix}_%04d.png")

        cmd = [
            self.ffmpeg, "-y",
            "-i", input_path,
            "-vf", f"fps={fps}",
            output_pattern,
        ]

        if self._run(cmd):
            frames = sorted([
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if f.startswith(prefix) and f.endswith(".png")
            ])
            return frames
        return []

    # ==================== 工具函数 ====================

    def _get_duration(self, video_path: str) -> float:
        """获取视频时长（秒）"""
        try:
            cmd = [
                self.ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except Exception:
            return 5.0  # 默认5秒

    def get_video_info(self, video_path: str) -> dict:
        """获取视频详细信息"""
        try:
            cmd = [
                self.ffprobe, "-v", "error",
                "-show_entries", "stream=width,height,r_frame_rate,duration,codec_name",
                "-show_entries", "format=duration,size,bit_rate",
                "-of", "json",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            import json
            return json.loads(result.stdout)
        except Exception as e:
            return {"error": str(e)}


# 全局单例
_ffmpeg_motion = None

def get_ffmpeg_motion() -> FFmpegMotion:
    """获取FFmpegMotion单例"""
    global _ffmpeg_motion
    if _ffmpeg_motion is None:
        _ffmpeg_motion = FFmpegMotion()
    return _ffmpeg_motion
