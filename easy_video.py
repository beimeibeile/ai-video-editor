"""
一键式视频生成入口 v1.0
========================
将复杂的双模式Pipeline封装为简单的函数调用和CLI命令。

使用方法：
    # Python API
    from easy_video import make_movie, make_short_video

    # 生成剧类视频（电影模式）
    result = make_movie(
        script="一个颓废的职场人发现了AI工具，经过努力后成功翻身",
        name="翻身",
        duration=15,
    )

    # 生成短视频（标签模式）
    result = make_short_video(
        topic="旅拍宣传片",
        tags=["旅行", "风景", "卡点"],
        duration=30,
    )

    # 命令行
    python easy_video.py --mode movie --script "剧本内容" --name 我的视频
    python easy_video.py --mode short --topic 旅拍 --tags 旅行,风景 --duration 30
"""

import os
import sys
import json
import argparse
import time
from typing import List, Dict, Any, Optional

# 确保skill根目录在path中
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)

from capabilities.cap_creative.dual_mode_pipeline import (
    DualModePipeline, PipelineConfig, ContentMode, PipelineResult
)
from core.resource_manager import ResourceManager, auto_cleanup


# 硬件配置预设
HARDWARE_PRESETS = {
    "rtx3080_12gb": {
        "description": "RTX 3080 12GB 推荐配置",
        "i2v_resolution": (720, 1280),
        "i2v_frames": 49,
        "i2v_steps": 10,
        "i2v_low_vram": True,
        "test_fps": 24,
        "delivery_fps": 48,
        "ref_image_steps": 4,
        "ref_image_resolution": (512, 768),
    },
    "rtx4090_24gb": {
        "description": "RTX 4090 24GB 推荐配置",
        "i2v_resolution": (1080, 1920),
        "i2v_frames": 81,
        "i2v_steps": 20,
        "i2v_low_vram": False,
        "test_fps": 30,
        "delivery_fps": 60,
        "ref_image_steps": 8,
        "ref_image_resolution": (768, 1152),
    },
    "low_end": {
        "description": "低显存配置（8GB以下）",
        "i2v_resolution": (480, 854),
        "i2v_frames": 25,
        "i2v_steps": 8,
        "i2v_low_vram": True,
        "test_fps": 24,
        "delivery_fps": 30,
        "ref_image_steps": 4,
        "ref_image_resolution": (384, 576),
    },
}


def detect_hardware() -> str:
    """
    自动检测GPU硬件，返回预设名称

    Returns:
        str: 硬件预设名称
    """
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            line = result.stdout.strip()
            if "3080" in line or ("12" in line and "288" not in line):
                return "rtx3080_12gb"
            elif "4090" in line or "24" in line:
                return "rtx4090_24gb"
            else:
                # 检查显存大小
                parts = line.split(",")
                if len(parts) >= 2:
                    try:
                        total_mb = int(parts[1].strip().replace("MiB", ""))
                        if total_mb >= 20000:
                            return "rtx4090_24gb"
                        elif total_mb >= 10000:
                            return "rtx3080_12gb"
                    except (ValueError, IndexError):
                        pass
    except Exception:
        pass
    return "low_end"


def get_hardware_config(hardware: str = None) -> dict:
    """
    获取硬件配置

    Args:
        hardware: 硬件预设名称（None则自动检测）

    Returns:
        dict: 硬件配置
    """
    if hardware is None:
        hardware = detect_hardware()
    return HARDWARE_PRESETS.get(hardware, HARDWARE_PRESETS["low_end"])


@auto_cleanup
def make_movie(
    script: str,
    name: str = "movie",
    duration: float = 15.0,
    output_dir: str = None,
    hardware: str = None,
    quality: str = "test",  # test / delivery
    verbose: bool = True,
) -> PipelineResult:
    """
    一键生成剧类视频（电影模式）

    流程：剧本解析 → 分镜生成 → 参考图生成 → I2V视频生成 → 剪映工程构建 → 资源清理

    Args:
        script: 剧本内容（一句话概括或完整剧本）
        name: 项目名称
        duration: 目标时长（秒）
        output_dir: 输出目录（None则自动创建）
        hardware: 硬件预设（None则自动检测）
        quality: 质量模式 - test(24fps,低分辨率) / delivery(48fps,高分辨率)
        verbose: 是否打印详细信息

    Returns:
        PipelineResult: 执行结果
    """
    hw = get_hardware_config(hardware)
    fps = hw["test_fps"] if quality == "test" else hw["delivery_fps"]

    if verbose:
        print(f"\n{'='*60}")
        print(f"  一键生成 - 电影模式")
        print(f"{'='*60}")
        print(f"  项目: {name}")
        print(f"  时长: {duration}秒")
        print(f"  帧率: {fps}fps ({quality}模式)")
        print(f"  硬件: {hw['description']}")
        print(f"  剧本: {script[:50]}...")
        print(f"{'='*60}\n")

    # 自动创建输出目录
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(SKILL_ROOT),
            "user_outputs",
            f"movie_{name}_{int(time.time())}"
        )
    os.makedirs(output_dir, exist_ok=True)

    # 保存剧本到文件
    script_path = os.path.join(output_dir, "script.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    # 构建配置
    config = PipelineConfig(
        mode=ContentMode.MOVIE,
        project_name=name,
        width=hw["i2v_resolution"][0],
        height=hw["i2v_resolution"][1],
        duration=duration,
        fps=fps,
        script_path=script_path,
        use_i2v=True,
        output_dir=output_dir,
    )

    # 执行Pipeline
    pipeline = DualModePipeline(skill_root=SKILL_ROOT)
    result = pipeline.run(config)

    if verbose:
        print(f"\n{'='*60}")
        print(f"  生成完成")
        print(f"  状态: {result.status}")
        print(f"  工程: {result.draft_path}")
        if result.errors:
            print(f"  错误: {result.errors}")
        print(f"{'='*60}\n")

    return result


@auto_cleanup
def make_short_video(
    topic: str,
    tags: List[str] = None,
    name: str = "short_video",
    duration: float = 30.0,
    material_paths: List[str] = None,
    text_lines: List[str] = None,
    bgm_mood: str = "energetic",
    output_dir: str = None,
    hardware: str = None,
    quality: str = "test",
    verbose: bool = True,
) -> PipelineResult:
    """
    一键生成短视频（标签模式）

    流程：标签解析 → 素材整理 → 卡点检测 → 特效应用 → 剪映工程构建 → 资源清理

    Args:
        topic: 视频主题
        tags: 标签列表（如["旅行", "风景", "卡点"]）
        name: 项目名称
        duration: 目标时长（秒）
        material_paths: 素材路径列表
        text_lines: 文字内容列表
        bgm_mood: BGM情绪风格
        output_dir: 输出目录
        hardware: 硬件预设
        quality: 质量模式
        verbose: 是否打印详细信息

    Returns:
        PipelineResult: 执行结果
    """
    hw = get_hardware_config(hardware)
    fps = hw["test_fps"] if quality == "test" else hw["delivery_fps"]

    if tags is None:
        tags = []
    if material_paths is None:
        material_paths = []
    if text_lines is None:
        text_lines = []

    if verbose:
        print(f"\n{'='*60}")
        print(f"  一键生成 - 短视频模式")
        print(f"{'='*60}")
        print(f"  主题: {topic}")
        print(f"  标签: {tags}")
        print(f"  时长: {duration}秒")
        print(f"  帧率: {fps}fps ({quality}模式)")
        print(f"  硬件: {hw['description']}")
        print(f"{'='*60}\n")

    # 自动创建输出目录
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(SKILL_ROOT),
            "user_outputs",
            f"short_{name}_{int(time.time())}"
        )
    os.makedirs(output_dir, exist_ok=True)

    # 构建配置
    config = PipelineConfig(
        mode=ContentMode.SHORT_VIDEO,
        project_name=name,
        width=1080,
        height=1920,
        duration=duration,
        fps=fps,
        tags=tags,
        text_lines=text_lines,
        material_paths=material_paths,
        bgm_mood=bgm_mood,
        use_beat_detection=True,
        output_dir=output_dir,
    )

    # 执行Pipeline
    pipeline = DualModePipeline(skill_root=SKILL_ROOT)
    result = pipeline.run(config)

    if verbose:
        print(f"\n{'='*60}")
        print(f"  生成完成")
        print(f"  状态: {result.status}")
        print(f"  工程: {result.draft_path}")
        if result.errors:
            print(f"  错误: {result.errors}")
        print(f"{'='*60}\n")

    return result


def main():
    """CLI命令行入口"""
    parser = argparse.ArgumentParser(
        description="ai-video-editor 一键式视频生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 电影模式
  python easy_video.py --mode movie --script "一个人翻身的故事" --name 翻身 --duration 15

  # 短视频模式
  python easy_video.py --mode short --topic 旅拍 --tags 旅行,风景,卡点 --duration 30

  # 高质量交付模式
  python easy_video.py --mode movie --script "..." --name 成品 --quality delivery
        """
    )

    parser.add_argument("--mode", choices=["movie", "short", "auto"], default="auto",
                        help="内容模式: movie(剧类/电影), short(短视频), auto(自动)")
    parser.add_argument("--script", type=str, default="",
                        help="剧本内容（电影模式）")
    parser.add_argument("--topic", type=str, default="",
                        help="视频主题（短视频模式）")
    parser.add_argument("--tags", type=str, default="",
                        help="标签列表，逗号分隔（短视频模式）")
    parser.add_argument("--name", type=str, default="video",
                        help="项目名称")
    parser.add_argument("--duration", type=float, default=15.0,
                        help="目标时长（秒）")
    parser.add_argument("--quality", choices=["test", "delivery"], default="test",
                        help="质量模式: test(快速测试), delivery(高质量交付)")
    parser.add_argument("--hardware", type=str, default=None,
                        choices=["rtx3080_12gb", "rtx4090_24gb", "low_end"],
                        help="硬件预设（默认自动检测）")
    parser.add_argument("--output", type=str, default=None,
                        help="输出目录")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="不自动清理资源（调试用）")

    args = parser.parse_args()

    # 解析标签
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    # 自动检测模式
    mode = args.mode
    if mode == "auto":
        if args.script:
            mode = "movie"
        else:
            mode = "short"

    if mode == "movie":
        if not args.script:
            print("❌ 电影模式需要提供 --script 参数")
            sys.exit(1)
        result = make_movie(
            script=args.script,
            name=args.name,
            duration=args.duration,
            output_dir=args.output,
            hardware=args.hardware,
            quality=args.quality,
        )
    else:
        result = make_short_video(
            topic=args.topic or args.name,
            tags=tags,
            name=args.name,
            duration=args.duration,
            output_dir=args.output,
            hardware=args.hardware,
            quality=args.quality,
        )

    # 输出结果
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if result.status != "success":
        sys.exit(1)


if __name__ == "__main__":
    main()
