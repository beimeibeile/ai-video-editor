#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速抠图：基于饱和度阈值分离主体和背景，不需要rembg大模型"""

import os
from PIL import Image, ImageFilter
import numpy as np


import logging
logger = logging.getLogger(__name__)
def remove_bg_fast(image_path, output_path=None):
    """
    快速抠图：背景是浅灰/白色（低饱和度），主体是彩色（高饱和度）
    用HSV饱和度通道做阈值分割
    """
    img = Image.open(image_path).convert("RGBA")
    arr = np.array(img)

    # 转换到HSV
    rgb = arr[:, :, :3].astype(np.float32) / 255.0
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]

    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    v = maxc
    delta = maxc - minc

    # 饱和度
    s = np.where(maxc > 0, delta / np.maximum(maxc, 1e-6), 0)

    # 亮度
    l = (maxc + minc) / 2

    # 背景：低饱和度 + 高明度
    bg_mask = (s < 0.15) & (l > 0.6)

    # 主体：高饱和度 或 低明度（深色部分）
    fg_mask = ~bg_mask

    # 形态学优化：先膨胀再腐蚀，去除噪点
    from scipy import ndimage
    fg_mask = ndimage.binary_opening(fg_mask, iterations=2)
    fg_mask = ndimage.binary_closing(fg_mask, iterations=3)

    # 高斯模糊边缘，实现抗锯齿
    alpha = fg_mask.astype(np.float32) * 255
    alpha_img = Image.fromarray(alpha.astype(np.uint8), mode='L')
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.5))
    alpha = np.array(alpha_img)

    # 应用alpha通道
    result = arr.copy()
    result[:, :, 3] = alpha

    out = Image.fromarray(result)
    if output_path:
        out.save(output_path)
        logger.info(f"  抠图完成: {output_path}")
    return out


def main():
    base_dir = r"D:\DobaoWork_Project\Ai_Video_Editor\animation_output\doubao_hit_v11"
    files = ["doubao_正常_00001_.png", "doubao_被打_00001_.png", "doubao_晕眩_00001_.png"]

    for f in files:
        src = os.path.join(base_dir, f)
        if os.path.exists(src):
            dst = os.path.join(base_dir, f.replace(".png", "_transparent.png"))
            remove_bg_fast(src, dst)
        else:
            logger.info(f"  文件不存在: {src}")


if __name__ == "__main__":
    main()
