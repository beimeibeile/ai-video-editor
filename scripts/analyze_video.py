"""
AI短视频剪辑 - 模式B：视频分析脚本

分析参考视频的基础信息、镜头分割、抽帧、音轨，输出分析报告。

使用方法：
    python analyze_video.py input.mp4 [--output output_dir] [--threshold 0.3]

依赖：ffmpeg/ffprobe, Python 3.11+
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import json
import argparse
import subprocess
import re


def run_cmd(cmd):
    """运行命令并返回stdout"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr


def probe_basic(video_path):
    """探测基础信息"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_format", "-show_streams",
        "-of", "json",
        video_path
    ]
    output = run_cmd(cmd)
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return {}

    info = {"file": os.path.basename(video_path)}
    fmt = data.get("format", {})
    info["duration"] = float(fmt.get("duration", 0))
    info["size"] = int(fmt.get("size", 0))
    info["bit_rate"] = int(fmt.get("bit_rate", 0))

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            info["video_codec"] = stream.get("codec_name")
            info["width"] = stream.get("width")
            info["height"] = stream.get("height")
            info["fps"] = stream.get("r_frame_rate")
            info["pix_fmt"] = stream.get("pix_fmt")
        elif stream.get("codec_type") == "audio":
            info["audio_codec"] = stream.get("codec_name")
            info["channels"] = stream.get("channels")
            info["sample_rate"] = stream.get("sample_rate")

    return info


def detect_scenes(video_path, threshold=0.3):
    """镜头分割（场景检测）"""
    cmd = [
        "ffmpeg", "-i", video_path,
        "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-"
    ]
    output = run_cmd(cmd)

    # 解析 pts_time
    times = []
    for line in output.split("\n"):
        match = re.search(r"pts_time:([\d.]+)", line)
        if match:
            times.append(float(match.group(1)))

    return sorted(set(times))


def extract_shots(video_path, scene_times, duration, output_dir):
    """根据场景时间点生成镜头列表"""
    shots = []
    boundaries = [0.0] + scene_times + [duration]

    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        shot_duration = end - start
        if shot_duration < 0.1:
            continue

        shot = {
            "index": i + 1,
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(shot_duration, 2),
            "is_quick_cut": shot_duration < 0.5,
        }

        # 抽帧（中间位置）
        mid = (start + end) / 2
        frame_path = os.path.join(output_dir, f"shot_{i+1}.png")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(mid),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            frame_path
        ]
        run_cmd(cmd)
        if os.path.exists(frame_path):
            shot["frame"] = frame_path

        shots.append(shot)

    return shots


def extract_audio_info(video_path):
    """音频信息探测"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_name,channels,sample_rate,duration",
        "-of", "json",
        video_path
    ]
    output = run_cmd(cmd)
    try:
        data = json.loads(output)
        streams = data.get("streams", [])
        if streams:
            return streams[0]
    except json.JSONDecodeError:
        pass
    return {}


def generate_report(info, shots, audio_info, output_path):
    """生成分析报告"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 原视频分析报告\n\n")

        # 基础信息
        f.write("## 基础信息\n\n")
        f.write(f"- 文件: {info.get('file', 'N/A')}\n")
        f.write(f"- 时长: {info.get('duration', 0):.2f}秒\n")
        f.write(f"- 分辨率: {info.get('width', '?')}x{info.get('height', '?')}\n")
        f.write(f"- 帧率: {info.get('fps', '?')}\n")
        f.write(f"- 视频编码: {info.get('video_codec', '?')}\n")
        f.write(f"- 音频编码: {info.get('audio_codec', '无')}\n")
        f.write(f"- 音轨数: {info.get('channels', 0)}\n")
        f.write(f"- 码率: {info.get('bit_rate', 0) // 1000} kbps\n\n")

        # 镜头列表
        f.write("## 镜头列表\n\n")
        f.write("| # | 起始 | 结束 | 时长 | 快切 | 抽帧 |\n")
        f.write("|---|---|---|---|---|---|\n")
        for shot in shots:
            quick = "✅" if shot["is_quick_cut"] else ""
            frame = os.path.basename(shot.get("frame", "")) if shot.get("frame") else "无"
            f.write(f"| {shot['index']} | {shot['start']}s | {shot['end']}s | {shot['duration']}s | {quick} | {frame} |\n")
        f.write("\n")

        # 音频信息
        f.write("## 音频信息\n\n")
        if audio_info:
            f.write(f"- 编码: {audio_info.get('codec_name', '?')}\n")
            f.write(f"- 声道: {audio_info.get('channels', '?')}\n")
            f.write(f"- 采样率: {audio_info.get('sample_rate', '?')}\n")
        else:
            f.write("- 无音轨\n")
        f.write("\n")

        # 待人工分析项
        f.write("## 待人工分析（Read抽帧后判断）\n\n")
        f.write("对每个镜头的抽帧图片进行Read，分析以下维度：\n\n")
        f.write("| # | 景别 | 主体 | 构图 | 色调 | 运镜 | 字幕 | 转场 | 特效 |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for shot in shots:
            f.write(f"| {shot['index']} | ? | ? | ? | ? | ? | ? | ? | ? |\n")
        f.write("\n")

        # 仿制分镜表模板
        f.write("## 仿制分镜表（填写后使用）\n\n")
        f.write("| 镜头# | 时间 | 时长 | 景别 | 运镜 | 主体/内容 | 字幕 | 转场 | 需替换素材 | 可自动还原 |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for shot in shots:
            f.write(f"| {shot['index']} | {shot['start']}-{shot['end']}s | {shot['duration']}s | ? | ? | ? | ? | ? | 图片{shot['index']} | ? |\n")
        f.write("\n")

        f.write("## 手动补充项\n\n")
        f.write("- 蒙版：复杂蒙版路径需剪映里手动调整\n")
        f.write("- 关键帧：缩放/位置关键帧需剪映里手动添加\n")
        f.write("- 粒子特效：星光/金粉等特效需剪映里手动添加\n")
        f.write("- 贴纸样式：免费贴纸样式有限，可手动换VIP贴纸\n")
        f.write("- 滤镜：全片统一滤镜需剪映里手动套\n")


def main():
    parser = argparse.ArgumentParser(description="视频分析脚本（模式B）")
    parser.add_argument("video", help="输入视频路径")
    parser.add_argument("--output", "-o", default="analysis_output", help="输出目录")
    parser.add_argument("--threshold", "-t", type=float, default=0.3, help="场景检测阈值（默认0.3）")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        logger.info(f"❌ 视频不存在: {args.video}")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)
    frames_dir = os.path.join(args.output, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    # 1. 基础信息
    logger.info("[1/4] 探测基础信息...")
    info = probe_basic(args.video)
    logger.info(f"  时长: {info.get('duration', 0):.2f}s, 分辨率: {info.get('width')}x{info.get('height')}")

    # 2. 镜头分割
    logger.info(f"[2/4] 镜头分割（阈值={args.threshold}）...")
    scene_times = detect_scenes(args.video, args.threshold)
    logger.info(f"  检测到 {len(scene_times)} 个场景切换点")

    # 3. 抽帧
    logger.info("[3/4] 抽取关键帧...")
    duration = info.get("duration", 10)
    shots = extract_shots(args.video, scene_times, duration, frames_dir)
    logger.info(f"  生成 {len(shots)} 个镜头")

    # 4. 音频信息
    logger.info("[4/4] 探测音频信息...")
    audio_info = extract_audio_info(args.video)

    # 生成报告
    report_path = os.path.join(args.output, "分析报告.md")
    generate_report(info, shots, audio_info, report_path)

    # 输出JSON
    json_path = os.path.join(args.output, "analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"info": info, "shots": shots, "audio": audio_info}, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 分析完成!")
    logger.info(f"  报告: {report_path}")
    logger.info(f"  JSON: {json_path}")
    logger.info(f"  抽帧: {frames_dir}/")
    logger.info(f"\n下一步: Read 每个抽帧图片，填写分析报告中的景别/主体/运镜等维度，然后生成仿制分镜表。")


if __name__ == "__main__":
    main()
