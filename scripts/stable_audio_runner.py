"""
Stable Audio 3 独立推理脚本
不依赖ComfyUI节点，直接用diffusers加载模型生成音效

用法:
    python stable_audio_runner.py --prompt "雨声" --duration 3 --output output.wav
"""

import logging
logger = logging.getLogger(__name__)

import argparse
import os
import sys
import torch
import numpy as np
import soundfile as sf


def generate_audio(prompt: str, duration: float = 3.0, output_path: str = "output.wav",
                   model_path: str = None, num_steps: int = 50):
    """
    用Stable Audio 3生成音频

    Args:
        prompt: 文本提示词（英文效果更好）
        duration: 音频时长（秒）
        output_path: 输出路径
        model_path: 模型路径（目录或单个safetensors文件）
        num_steps: 推理步数
    """
    from diffusers import StableAudio3Pipeline

    # 默认模型路径
    if model_path is None:
        model_path = r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\models\checkpoints\stable-audio-3-small-sfx.safetensors"

    logger.info(f"加载模型: {model_path}")
    logger.info(f"提示词: {prompt}")
    logger.info(f"时长: {duration}s")

    # 检查模型路径
    if not os.path.exists(model_path):
        logger.info(f"❌ 模型文件不存在: {model_path}")
        logger.info("  请下载Stable Audio 3模型到指定路径")
        return None

    # 检查diffusers版本
    try:
        import diffusers
        version = getattr(diffusers, "__version__", "unknown")
        logger.info(f"diffusers版本: {version}")
    except ImportError:
        logger.info("❌ diffusers未安装，请运行: pip install diffusers")
        return None

    # 加载模型
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"设备: {device}")

    try:
        if os.path.isdir(model_path):
            # 检查是否为diffusers格式
            model_index = os.path.join(model_path, "model_index.json")
            if not os.path.exists(model_index):
                logger.info(f"❌ 模型目录不是diffusers格式（缺少model_index.json）: {model_path}")
                logger.info("  当前模型为Stability原始格式，需转换为diffusers格式")
                logger.info("  降级方案：使用层1(TTS拟声词)或层2(ffmpeg合成)")
                return None
            pipe = StableAudio3Pipeline.from_pretrained(
                model_path, torch_dtype=torch.float16
            )
        else:
            # 单个safetensors文件 - StableAudio3Pipeline不支持from_single_file
            logger.info(f"❌ StableAudio3Pipeline不支持from_single_file加载单个safetensors")
            logger.info(f"  模型文件: {model_path}")
            logger.info("  需要diffusers格式的完整模型目录（含model_index.json）")
            logger.info("  降级方案：使用层1(TTS拟声词)或层2(ffmpeg合成)")
            return None
        pipe = pipe.to(device)

        logger.info("模型加载完成，开始生成...")

        # 生成音频
        with torch.no_grad():
            output = pipe(
                prompt,
                num_inference_steps=num_steps,
                audio_end_in_s=duration,
            )

        # 保存音频
        audio = output.audios[0]
        # audio shape: (channels, samples)
        if audio.ndim == 1:
            audio = audio.unsqueeze(0)

        # 转numpy
        audio_np = audio.cpu().numpy().T  # (samples, channels)
        sample_rate = getattr(pipe, "sample_rate", 44100)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        sf.write(output_path, audio_np, sample_rate)

        logger.info(f"✅ 音频已保存: {output_path}")
        logger.info(f"   采样率: {sample_rate} Hz")
        logger.info(f"   时长: {len(audio_np) / sample_rate:.1f}s")
        logger.info(f"   声道: {audio_np.shape[1] if audio_np.ndim > 1 else 1}")

        return output_path

    except Exception as e:
        logger.error(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stable Audio 3 音效生成")
    parser.add_argument("--prompt", type=str, required=True, help="文本提示词")
    parser.add_argument("--duration", type=float, default=3.0, help="音频时长（秒）")
    parser.add_argument("--output", type=str, default="output.wav", help="输出路径")
    parser.add_argument("--model", type=str, default=None, help="模型路径")
    parser.add_argument("--steps", type=int, default=50, help="推理步数")

    args = parser.parse_args()
    generate_audio(args.prompt, args.duration, args.output, args.model, args.steps)
