"""
视频缩略图生成工具
将视频的多个关键帧拼接成一张预览大图
"""
import os
import sys
import subprocess
from typing import List, Optional

# 导入image_utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from image_utils import concat_images, get_image_info


def generate_video_thumbnail(
    video_path: str,
    output_path: str = None,
    grid_cols: int = 4,
    grid_rows: int = 3,
    gap: int = 8,
    background: tuple = (20, 20, 20),
    include_info: bool = True,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    生成视频缩略图（抽帧+网格拼接）

    Args:
        video_path: 输入视频路径
        output_path: 输出图片路径（None则自动命名）
        grid_cols: 网格列数
        grid_rows: 网格行数
        gap: 图片间距（像素）
        background: 背景颜色（RGB）
        include_info: 是否包含视频信息文字
        ffmpeg_path: ffmpeg路径

    Returns:
        输出图片路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}_thumbnail.jpg"

    # 创建临时目录
    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="video_thumb_")

    try:
        # 获取视频时长
        from ffmpeg_utils import get_video_info_simple
        info = get_video_info_simple(video_path, ffprobe_path=ffmpeg_path.replace("ffmpeg", "ffprobe"))
        duration = info.get("duration", 0)

        if duration <= 0:
            raise ValueError("无法获取视频时长")

        # 计算抽帧时间点
        num_frames = grid_cols * grid_rows
        # 跳过开头和结尾的5%
        start_time = duration * 0.05
        end_time = duration * 0.95
        interval = (end_time - start_time) / max(num_frames - 1, 1)

        frame_paths = []
        for i in range(num_frames):
            t = start_time + i * interval
            frame_path = os.path.join(tmp_dir, f"frame_{i:03d}.jpg")
            # 使用ffmpeg抽帧
            cmd = [
                ffmpeg_path, "-y",
                "-ss", f"{t:.2f}",
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "3",
                frame_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(frame_path):
                frame_paths.append(frame_path)

        if not frame_paths:
            raise RuntimeError("抽帧失败")

        # 拼接成网格
        result = concat_images(
            frame_paths,
            output_path,
            direction="grid",
            gap=gap,
            background=background,
        )

        return result

    finally:
        # 清理临时文件
        import shutil
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


def batch_generate_thumbnails(
    video_paths: List[str],
    output_dir: str,
    grid_cols: int = 4,
    grid_rows: int = 3,
) -> List[str]:
    """批量生成视频缩略图"""
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for vp in video_paths:
        fname = os.path.splitext(os.path.basename(vp))[0]
        out = os.path.join(output_dir, f"{fname}_thumb.jpg")
        try:
            results.append(generate_video_thumbnail(vp, out, grid_cols, grid_rows))
        except Exception as e:
            print(f"  ⚠️  {vp}: {e}")
    return results


__all__ = ["generate_video_thumbnail", "batch_generate_thumbnails"]


if __name__ == "__main__":
    print("视频缩略图生成工具已加载")
