#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用ComfyUI生成真实豆包头像，然后抠图得到透明背景
import logging
logger = logging.getLogger(__name__)
修复: 输出目录路径 + wait_for_completion逻辑 + 快速抠图替代rembg
"""

import json
import time
import urllib.request
import os
import shutil

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_OUTPUT = r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\output"
OUTPUT_DIR = r"D:\DobaoWork_Project\Ai_Video_Editor\animation_output\doubao_hit_v11"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def queue_prompt(workflow):
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_history(prompt_id):
    req = urllib.request.Request(f"{COMFYUI_URL}/history/{prompt_id}")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def wait_for_completion(prompt_id, timeout=120):
    """等待ComfyUI完成，返回outputs字典或None"""
    start = time.time()
    while time.time() - start < timeout:
        history = get_history(prompt_id)
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            if status.get("completed"):
                return entry.get("outputs", {})
        time.sleep(2)
    return None


def generate_doubao_avatar(prompt, filename, seed=42):
    """生成豆包头像，返回复制到项目目录的路径"""
    workflow = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "基础模型\\sd_xl_turbo_1.0_fp16.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "ugly, deformed, blurry, low quality, text, watermark, human, person, realistic photo", "clip": ["1", 1]}},
        "4": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 6, "cfg": 1.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["5", 0]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["4", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": filename, "images": ["6", 0]}},
    }

    logger.info(f"  生成: {filename}...")
    result = queue_prompt(workflow)
    prompt_id = result["prompt_id"]
    outputs = wait_for_completion(prompt_id)

    if outputs:
        for node_id, output in outputs.items():
            if "images" in output:
                for img in output["images"]:
                    src = os.path.join(COMFYUI_OUTPUT, img["filename"])
                    dst = os.path.join(OUTPUT_DIR, img["filename"])
                    if os.path.exists(src):
                        shutil.copy2(src, dst)
                        logger.info(f"    保存: {dst} ({os.path.getsize(dst)//1024}KB)")
                        return dst
                    else:
                        logger.warning(f"    警告: 输出文件不存在 {src}")
    logger.error("    生成失败")
    return None


def remove_bg_fast(image_path):
    """快速抠图（饱和度阈值法，不需要rembg大模型）"""
    try:
        from PIL import Image, ImageFilter
        import numpy as np
        from scipy import ndimage

        img = Image.open(image_path).convert("RGBA")
        arr = np.array(img)
        rgb = arr[:, :, :3].astype(np.float32) / 255.0
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        maxc = np.maximum(np.maximum(r, g), b)
        minc = np.minimum(np.minimum(r, g), b)
        delta = maxc - minc
        s = np.where(maxc > 0, delta / np.maximum(maxc, 1e-6), 0)
        l = (maxc + minc) / 2
        bg_mask = (s < 0.15) & (l > 0.6)
        fg_mask = ~bg_mask
        fg_mask = ndimage.binary_opening(fg_mask, iterations=2)
        fg_mask = ndimage.binary_closing(fg_mask, iterations=3)
        alpha = fg_mask.astype(np.float32) * 255
        alpha_img = Image.fromarray(alpha.astype(np.uint8), mode='L')
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.5))
        result = arr.copy()
        result[:, :, 3] = np.array(alpha_img)
        out = Image.fromarray(result)
        out_path = image_path.replace(".png", "_transparent.png")
        out.save(out_path)
        logger.info(f"    抠图: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"    抠图失败: {e}")
        return image_path


def main():
    logger.info("=" * 60)
    logger.info("ComfyUI生成真实豆包头像（修复版）")
    logger.info("=" * 60)

    avatars = [
        ("正常", "cute cartoon AI assistant character, round blue purple robot face, big friendly eyes, small smile, glossy 3D render, clean white background, product photography style, centered composition", 42),
        ("被打", "cute cartoon AI assistant character, round blue purple robot face, dazed expression, stars circling around head, dizzy look, glossy 3D render, clean white background, product photography style", 123),
        ("晕眩", "cute cartoon AI assistant character, round blue purple robot face, X shaped eyes, tongue out, dizzy confused expression, glossy 3D render, clean white background, product photography style", 456),
    ]

    results = {}
    for name, prompt, seed in avatars:
        path = generate_doubao_avatar(prompt, f"doubao_{name}", seed)
        if path:
            transparent = remove_bg_fast(path)
            results[name] = transparent

    logger.info("\n" + "=" * 60)
    logger.info("生成完成:")
    for name, path in results.items():
        logger.info(f"  {name}: {path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
