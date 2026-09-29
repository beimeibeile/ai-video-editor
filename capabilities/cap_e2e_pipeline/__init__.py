"""
端到端视频生成流程模块 (cap_e2e_pipeline)
整合：分镜引擎 → 素材加工(LTX-2.5/ffmpeg) → 剪映合成

一键API:
    from cap_e2e_pipeline import create_video
    result = create_video("城市夜景", style="cinematic", duration=15, shot_count=5)

流程：
1. 分镜生成（cap_storyboard_engine）
2. 素材加工（LTX-2.5 I2V / ffmpeg Ken Burns，自动降级）
3. 剪映合成（转场+字幕+音效+BGM）
4. 可选片头（cap_intro_generator）
"""
from .pipeline import E2EPipeline, create_video

__all__ = ["E2EPipeline", "create_video"]
