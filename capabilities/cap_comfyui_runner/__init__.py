"""
cap_comfyui_runner — 本地ComfyUI操作能力模块
用于批量、耗时、耗算力的任务：图片超分、人脸统一、图生视频、抠图、ControlNet、Qwen图像编辑等
"""
from .comfy_client import ComfyClient, load_workflow_template
from .api import (
    upscale_image, upscale_batch, check_comfyui_ready,
    matting_image, matting_batch,
    face_unify_image, face_unify_batch,
    controlnet_generate, generate_pose_skeleton, generate_character_views,
    generate_character_views_qwen, QWEN_VIEW_PROMPTS,
    txt2img_zimage, ZIMAGE_MODELS,
    UPSCALE_MODELS, MATTING_MODELS, CONTROLNET_MODELS,
    FACE_UNIFY_CHECKPOINTS, FACE_UNIFY_IPADAPTER_MODELS,
)

__all__ = [
    "ComfyClient", "load_workflow_template",
    "upscale_image", "upscale_batch", "check_comfyui_ready",
    "matting_image", "matting_batch",
    "face_unify_image", "face_unify_batch",
    "controlnet_generate", "generate_pose_skeleton", "generate_character_views",
    "generate_character_views_qwen", "QWEN_VIEW_PROMPTS",
    "txt2img_zimage", "ZIMAGE_MODELS",
    "UPSCALE_MODELS", "MATTING_MODELS", "CONTROLNET_MODELS",
    "FACE_UNIFY_CHECKPOINTS", "FACE_UNIFY_IPADAPTER_MODELS",
]
