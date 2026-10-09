"""
去背景模块 v2.0
支持多种去背景方案，自动选择最佳可用方案：
1. ComfyUI BiRefNet（专业级，大模型语义抠图）
2. 背景差分+ROI（视频序列，适合固定背景的角色动画）
3. OpenCV GrabCut（单图，半自动）
4. Pillow颜色容差（兜底）

新增能力（v2.0）：
- 视频帧序列批量抠图
- 背景差分+分段ROI（豆包被打案例验证）
- BiRefNet精抠（解决UI误抠）
- 混合抠图（背景差分+BiRefNet分段）
- ProRes 4444透明视频合成
- Alpha通道自动验证

使用方法：
    from remove_background import remove_bg, matting_video, compose_prores
    result = remove_bg("input.png", "output.png", method="auto")
    matting_video("frames/", "matted/", method="birefnet")
    compose_prores("matted/", "output.mov", fps=24)
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import json
import time
import uuid
import shutil
import urllib.request
from typing import Optional, Tuple, List, Dict

try:
    from PIL import Image, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import cv2
    import numpy as np
    OPENCV_OK = True
except ImportError:
    OPENCV_OK = False

# ComfyUI配置
COMFYUI_URL = "http://127.0.0.1:8188"
BIREFNET_MODEL_DIR = r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\models\rmbg\BiRefNet"
FFMPEG_PATH = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

# BiRefNet可选模型
BIREFNET_MODELS = [
    "BiRefNet-general", "BiRefNet_512x512", "BiRefNet-HR",
    "BiRefNet-portrait", "BiRefNet-matting", "BiRefNet-HR-matting",
    "BiRefNet_lite", "BiRefNet_lite-2K", "BiRefNet_dynamic",
    "BiRefNet_lite-matting", "BiRefNet_toonout", "Lucida"
]


# ═══════════════════════════════════════════════════════════════
# 环境检测
# ═══════════════════════════════════════════════════════════════

def check_birefnet_available() -> bool:
    """检查BiRefNet模型是否可用"""
    if not os.path.exists(BIREFNET_MODEL_DIR):
        return False
    models = [f for f in os.listdir(BIREFNET_MODEL_DIR)
              if f.endswith(('.safetensors', '.pth', '.ckpt'))]
    return len(models) > 0


def check_comfyui_alive() -> bool:
    """检查ComfyUI是否运行"""
    try:
        urllib.request.urlopen(COMFYUI_URL, timeout=3)
        return True
    except Exception:
        return False


def check_birefnet_node() -> bool:
    """检查ComfyUI中BiRefNetRMBG节点是否可用"""
    try:
        req = urllib.request.Request(f"{COMFYUI_URL}/object_info/BiRefNetRMBG")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        return bool(data.get("BiRefNetRMBG"))
    except Exception:
        return False


def get_available_methods() -> List[str]:
    """获取可用的去背景方法列表"""
    methods = []
    if PIL_OK:
        methods.append("pillow")
    if OPENCV_OK:
        methods.append("opencv")
    if check_comfyui_alive() and check_birefnet_available() and check_birefnet_node():
        methods.append("birefnet")
    return methods


# ═══════════════════════════════════════════════════════════════
# 方法1: Pillow颜色容差（兜底）
# ═══════════════════════════════════════════════════════════════

def remove_bg_pillow(
    input_path: str,
    output_path: str,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    tolerance: int = 30,
    feather: int = 2,
) -> Optional[str]:
    """Pillow改进版去背景：颜色容差+边缘羽化"""
    if not PIL_OK:
        return None
    try:
        img = Image.open(input_path).convert("RGBA")
        pixels = img.load()
        w, h = img.size
        mask = Image.new("L", (w, h), 0)
        mask_pixels = mask.load()
        br, bg, bb = bg_color
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                dist = ((r - br) ** 2 + (g - bg) ** 2 + (b - bb) ** 2) ** 0.5
                if dist < tolerance:
                    mask_pixels[x, y] = 0
                else:
                    edge_factor = min(1.0, (dist - tolerance) / (tolerance * 0.5))
                    mask_pixels[x, y] = int(255 * edge_factor)
        if feather > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
        result = img.copy()
        result.putalpha(mask)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        result.save(output_path, "PNG")
        return output_path
    except Exception as e:
        logger.error(f"  Pillow失败: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# 方法2: OpenCV GrabCut
# ═══════════════════════════════════════════════════════════════

def remove_bg_opencv(
    input_path: str,
    output_path: str,
    iterations: int = 5,
) -> Optional[str]:
    """OpenCV GrabCut去背景"""
    if not OPENCV_OK:
        return None
    try:
        img = cv2.imdecode(np.fromfile(input_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return None
        h, w = img.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        rect = (int(w * 0.05), int(h * 0.05), int(w * 0.9), int(h * 0.9))
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        cv2.grabCut(img, mask, rect, bgd_model, fgd_model, iterations, cv2.GC_INIT_WITH_RECT)
        alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        b, g, r = cv2.split(img)
        rgba = cv2.merge([r, g, b, alpha])
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        ext = os.path.splitext(output_path)[1] or '.png'
        success, buf = cv2.imencode(ext, rgba)
        if success:
            buf.tofile(output_path)
        return output_path
    except Exception as e:
        logger.error(f"  OpenCV失败: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# 方法3: ComfyUI BiRefNet（专业级语义抠图）
# ═══════════════════════════════════════════════════════════════

def _comfyui_upload_image(input_path: str) -> str:
    """上传图片到ComfyUI，返回文件名"""
    with open(input_path, 'rb') as f:
        img_data = f.read()
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = (f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="image"; filename="input.png"\r\n'
            f'Content-Type: image/png\r\n\r\n').encode() + img_data + f'\r\n--{boundary}--\r\n'.encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/upload/image",
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read())
    return result.get('name', 'input.png')


def _comfyui_wait_result(prompt_id: str, timeout: int = 120) -> Optional[Dict]:
    """等待ComfyUI工作流完成"""
    for _ in range(timeout):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5) as r:
                history = json.loads(r.read())
            if prompt_id in history:
                return history[prompt_id].get('outputs', {})
        except Exception:
            continue
    return None


def remove_bg_birefnet(
    input_path: str,
    output_path: str,
    model: str = "BiRefNet-general",
) -> Optional[str]:
    """
    ComfyUI BiRefNet去背景（专业级语义抠图）

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        model: BiRefNet模型名（BiRefNet-general/BiRefNet-portrait/BiRefNet-matting等）

    Returns:
        输出路径或None
    """
    if not check_comfyui_alive():
        logger.info("  ComfyUI未运行")
        return None
    if not check_birefnet_available():
        logger.info("  BiRefNet模型不可用")
        return None

    try:
        client_id = str(uuid.uuid4())

        # 1. 上传图片
        uploaded_name = _comfyui_upload_image(input_path)

        # 2. 构建工作流（BiRefNetRMBG节点，显式设置所有可选参数避免插件bug）
        workflow = {
            "1": {"class_type": "LoadImage", "inputs": {"image": uploaded_name}},
            "2": {"class_type": "BiRefNetRMBG", "inputs": {
                "image": ["1", 0],
                "model": model,
                "sensitivity": 1.0,
                "mask_blur": 2,
                "mask_offset": 0,
                "invert_output": False,
                "refine_foreground": True,
                "background": "Alpha",
                "background_color": "#222222",
            }},
            "3": {"class_type": "SaveImage", "inputs": {
                "images": ["2", 0],
                "filename_prefix": "birefnet_output",
            }},
        }

        # 3. 提交工作流
        prompt_data = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
        req = urllib.request.Request(
            f"{COMFYUI_URL}/prompt",
            data=prompt_data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            prompt_result = json.loads(r.read())
        prompt_id = prompt_result.get('prompt_id')

        # 4. 等待结果
        outputs = _comfyui_wait_result(prompt_id, timeout=120)
        if not outputs:
            logger.info("  BiRefNet超时")
            return None

        # 5. 下载结果
        for node_id, node_out in outputs.items():
            if 'images' in node_out:
                img_info = node_out['images'][0]
                img_url = (f"{COMFYUI_URL}/view?filename={img_info['filename']}"
                           f"&subfolder={img_info.get('subfolder', '')}"
                           f"&type={img_info.get('type', 'output')}")
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                urllib.request.urlretrieve(img_url, output_path)
                return output_path

        return None
    except Exception as e:
        logger.error(f"  BiRefNet失败: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# 方法4: 背景差分+ROI（视频序列）
# ═══════════════════════════════════════════════════════════════

def _imread_unicode(path: str) -> Optional[np.ndarray]:
    """读取图片（支持中文路径）"""
    if not OPENCV_OK:
        return None
    try:
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def remove_bg_bgdiff(
    input_path: str,
    output_path: str,
    background_path: str,
    roi: Optional[Tuple[int, int, int, int]] = None,
    threshold: int = 30,
    morph_iter: int = 2,
    feather: int = 2,
) -> Optional[str]:
    """
    背景差分去背景（适合固定背景的视频帧）

    Args:
        input_path: 当前帧路径
        output_path: 输出路径
        background_path: 背景帧路径（第一帧或中值背景）
        roi: 感兴趣区域 (x1, y1, x2, y2)，None则全图
        threshold: 差分阈值
        morph_iter: 形态学操作迭代次数
        feather: 边缘羽化半径

    Returns:
        输出路径或None
    """
    if not OPENCV_OK:
        return None
    try:
        frame = _imread_unicode(input_path)
        bg = _imread_unicode(background_path)
        if frame is None or bg is None:
            return None

        h, w = frame.shape[:2]

        # 计算差分
        diff = cv2.absdiff(frame, bg)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

        # ROI限制
        if roi:
            x1, y1, x2, y2 = roi
            roi_mask = np.zeros((h, w), np.uint8)
            roi_mask[y1:y2, x1:x2] = 255
            mask = cv2.bitwise_and(mask, roi_mask)

        # 形态学操作（去噪+填充）
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=morph_iter)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=morph_iter)

        # 只保留最大连通区域（去除小噪点）
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            mask = np.zeros((h, w), np.uint8)
            cv2.drawContours(mask, [largest], -1, 255, -1)

        # 边缘羽化
        if feather > 0:
            mask = cv2.GaussianBlur(mask, (feather * 2 + 1, feather * 2 + 1), 0)

        # 合成RGBA
        b, g, r = cv2.split(frame)
        rgba = cv2.merge([r, g, b, mask])

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        ext = os.path.splitext(output_path)[1] or '.png'
        success, buf = cv2.imencode(ext, rgba)
        if success:
            buf.tofile(output_path)
        return output_path
    except Exception as e:
        logger.error(f"  背景差分失败: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════════════════════

def remove_bg(
    input_path: str,
    output_path: str = None,
    method: str = "auto",
    **kwargs,
) -> Optional[str]:
    """
    去背景统一入口

    Args:
        input_path: 输入图片路径
        output_path: 输出路径（None则自动生成）
        method: auto / birefnet / opencv / pillow / bgdiff
        **kwargs: 传递给具体方法的参数
            - birefnet: model="BiRefNet-general"
            - bgdiff: background_path, roi, threshold, morph_iter, feather
            - pillow: bg_color, tolerance, feather
            - opencv: iterations

    Returns:
        输出路径或None
    """
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_nobg{ext}"

    logger.info(f"\n去背景: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")
    logger.info(f"  方法: {method}")

    if method == "auto":
        available = get_available_methods()
        if "birefnet" in available:
            method = "birefnet"
        elif "opencv" in available:
            method = "opencv"
        else:
            method = "pillow"
        logger.info(f"  自动选择: {method}")

    if method == "birefnet":
        birefnet_kwargs = {k: v for k, v in kwargs.items() if k in ("model",)}
        result = remove_bg_birefnet(input_path, output_path, **birefnet_kwargs)
        if result:
            return result
        logger.error("  BiRefNet失败，回退OpenCV")
        method = "opencv"

    if method == "bgdiff":
        return remove_bg_bgdiff(input_path, output_path, **kwargs)

    if method in ("birefnet", "opencv"):
        opencv_kwargs = {k: v for k, v in kwargs.items() if k in ("iterations",)}
        result = remove_bg_opencv(input_path, output_path, **opencv_kwargs)
        if result:
            return result
        logger.error("  OpenCV失败，回退Pillow")

    pillow_kwargs = {k: v for k, v in kwargs.items() if k in ("bg_color", "tolerance", "feather")}
    return remove_bg_pillow(input_path, output_path, **pillow_kwargs)


# ═══════════════════════════════════════════════════════════════
# 视频帧序列批量抠图
# ═══════════════════════════════════════════════════════════════

def matting_video(
    frames_dir: str,
    output_dir: str,
    method: str = "birefnet",
    background_path: str = None,
    roi_list: Optional[List[Tuple[int, Tuple[int, int, int, int]]]] = None,
    birefnet_roi: Optional[Tuple[int, int, int, int]] = None,
    model: str = "BiRefNet-general",
    frame_pattern: str = "frame_%04d.png",
    start_frame: int = 1,
    end_frame: int = None,
    **kwargs,
) -> List[str]:
    """
    视频帧序列批量抠图

    Args:
        frames_dir: 输入帧目录
        output_dir: 输出目录
        method: birefnet / bgdiff / hybrid
        background_path: 背景帧路径（bgdiff/hybrid需要）
        roi_list: 分段ROI列表 [(frame_end, (x1,y1,x2,y2)), ...]（bgdiff用）
        birefnet_roi: BiRefNet处理前的裁剪区域 (x1,y1,x2,y2)（减少计算量）
        model: BiRefNet模型名
        frame_pattern: 文件名模式
        start_frame: 起始帧号
        end_frame: 结束帧号
        **kwargs: 其他参数

    Returns:
        成功处理的帧路径列表
    """
    os.makedirs(output_dir, exist_ok=True)

    # 确定帧范围
    if end_frame is None:
        existing = [f for f in os.listdir(frames_dir) if f.endswith('.png')]
        end_frame = len(existing)

    results = []
    total = end_frame - start_frame + 1
    t0 = time.time()

    logger.info(f"\n批量抠图: {total}帧, 方法={method}")
    logger.info(f"  输入: {frames_dir}")
    logger.info(f"  输出: {output_dir}")

    for i, frame_num in enumerate(range(start_frame, end_frame + 1)):
        input_path = os.path.join(frames_dir, frame_pattern % frame_num)
        output_path = os.path.join(output_dir, frame_pattern.replace('%04d', '%04d_matted') % frame_num)

        if not os.path.exists(input_path):
            continue

        if method == "birefnet":
            # BiRefNet精抠（可选ROI裁剪加速）
            if birefnet_roi:
                # 先裁剪ROI，抠图后再放回原图大小
                result = _matting_birefnet_with_roi(
                    input_path, output_path, birefnet_roi, model
                )
            else:
                result = remove_bg_birefnet(input_path, output_path, model=model)

        elif method == "bgdiff":
            # 确定当前帧的ROI
            current_roi = None
            if roi_list:
                for frame_end, roi in roi_list:
                    if frame_num <= frame_end:
                        current_roi = roi
                        break
            result = remove_bg_bgdiff(
                input_path, output_path,
                background_path=background_path,
                roi=current_roi,
                **kwargs
            )

        elif method == "hybrid":
            # 混合模式：需要调用方指定分段逻辑
            # 这里简化为前半段bgdiff，后半段birefnet
            mid = (start_frame + end_frame) // 2
            if frame_num <= mid:
                current_roi = None
                if roi_list:
                    for frame_end, roi in roi_list:
                        if frame_num <= frame_end:
                            current_roi = roi
                            break
                result = remove_bg_bgdiff(
                    input_path, output_path,
                    background_path=background_path,
                    roi=current_roi,
                    **kwargs
                )
            else:
                if birefnet_roi:
                    result = _matting_birefnet_with_roi(
                        input_path, output_path, birefnet_roi, model
                    )
                else:
                    result = remove_bg_birefnet(input_path, output_path, model=model)
        else:
            result = remove_bg(input_path, output_path, method=method, **kwargs)

        if result:
            results.append(result)

        # 进度
        if (i + 1) % 10 == 0 or i == total - 1:
            elapsed = time.time() - t0
            speed = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total - i - 1) / speed if speed > 0 else 0
            logger.info(f"  进度: {i+1}/{total} ({speed:.1f}帧/s, ETA {eta:.0f}s)")

    elapsed = time.time() - t0
    logger.info(f"\n✅ 批量抠图完成: {len(results)}/{total}帧, 耗时{elapsed:.1f}秒")
    return results


def _matting_birefnet_with_roi(
    input_path: str,
    output_path: str,
    roi: Tuple[int, int, int, int],
    model: str = "BiRefNet-general",
) -> Optional[str]:
    """BiRefNet抠图+ROI裁剪加速：裁剪ROI区域抠图后放回原图"""
    if not OPENCV_OK or not PIL_OK:
        return remove_bg_birefnet(input_path, output_path, model=model)

    try:
        img = Image.open(input_path).convert("RGBA")
        w, h = img.size
        x1, y1, x2, y2 = roi
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        # 裁剪ROI
        roi_img = img.crop((x1, y1, x2, y2))
        roi_path = output_path + ".roi_tmp.png"
        roi_img.save(roi_path)

        # BiRefNet抠图
        matted_roi_path = output_path + ".roi_matted.png"
        result = remove_bg_birefnet(roi_path, matted_roi_path, model=model)

        # 清理临时文件
        try:
            os.remove(roi_path)
        except Exception:
            pass

        if not result:
            return None

        # 放回原图大小（ROI区域为抠图结果，其余为透明）
        matted_roi = Image.open(matted_roi_path).convert("RGBA")
        result_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        result_img.paste(matted_roi, (x1, y1), matted_roi)

        try:
            os.remove(matted_roi_path)
        except Exception:
            pass

        result_img.save(output_path, "PNG")
        return output_path
    except Exception as e:
        logger.error(f"  ROI+BiRefNet失败: {e}")
        return remove_bg_birefnet(input_path, output_path, model=model)


# ═══════════════════════════════════════════════════════════════
# ProRes 4444透明视频合成
# ═══════════════════════════════════════════════════════════════

def compose_prores(
    frames_dir: str,
    output_path: str,
    fps: int = 24,
    frame_pattern: str = "frame_%04d_matted.png",
    profile: str = "4444",
    pix_fmt: str = "yuva444p10le",
) -> Optional[str]:
    """
    将抠图帧序列合成为ProRes 4444透明视频

    Args:
        frames_dir: 帧序列目录
        output_path: 输出视频路径
        fps: 帧率
        frame_pattern: 文件名模式
        profile: ProRes配置（4444/422/422hq）
        pix_fmt: 像素格式（yuva444p10le/yuva444p12le）

    Returns:
        输出路径或None
    """
    if not os.path.exists(FFMPEG_PATH):
        logger.info(f"  ffmpeg不可用: {FFMPEG_PATH}")
        return None

    input_pattern = os.path.join(frames_dir, frame_pattern)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    cmd = [
        FFMPEG_PATH, "-y",
        "-framerate", str(fps),
        "-i", input_pattern,
        "-c:v", "prores_ks",
        "-profile:v", profile,
        "-pix_fmt", pix_fmt,
        "-vendor", "ap10",
        "-q:v", "4",
        output_path
    ]

    logger.info(f"\n合成ProRes视频: {os.path.basename(output_path)}")
    logger.info(f"  输入: {input_pattern}")
    logger.info(f"  帧率: {fps}fps, 编码: ProRes {profile}, {pix_fmt}")

    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        logger.info(f"  ✅ 合成成功: {size_mb:.1f}MB")
        return output_path
    else:
        logger.error(f"  ❌ 合成失败: {result.stderr[-500:] if result.stderr else '未知错误'}")
        return None


def verify_alpha(video_path: str, sample_frame: int = 0) -> Dict:
    """
    验证视频的Alpha通道

    Args:
        video_path: 视频路径
        sample_frame: 采样帧号

    Returns:
        验证结果字典
    """
    import subprocess
    import io

    result = {
        "path": video_path,
        "exists": os.path.exists(video_path),
        "has_alpha": False,
        "transparent_ratio": 0.0,
        "codec": "",
        "pix_fmt": "",
        "width": 0,
        "height": 0,
    }

    if not result["exists"]:
        return result

    # ffprobe获取编码信息
    ffprobe = FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe")
    if os.path.exists(ffprobe):
        try:
            probe = subprocess.run([
                ffprobe, "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_name,width,height,pix_fmt",
                "-of", "default=noprint_wrappers=1", video_path
            ], capture_output=True, text=True)
            for line in probe.stdout.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k == "codec_name":
                        result["codec"] = v
                    elif k == "pix_fmt":
                        result["pix_fmt"] = v
                    elif k == "width":
                        result["width"] = int(v)
                    elif k == "height":
                        result["height"] = int(v)
            result["has_alpha"] = "a" in result["pix_fmt"].lower()
        except Exception:
            pass

    # 抽取帧验证透明像素
    if result["has_alpha"] and PIL_OK:
        try:
            frame_result = subprocess.run([
                FFMPEG_PATH, "-y", "-i", video_path,
                "-vf", f"select=eq(n\\,{sample_frame})",
                "-frames:v", "1", "-f", "image2pipe",
                "-vcodec", "png", "-"
            ], capture_output=True)
            if frame_result.stdout:
                img = Image.open(io.BytesIO(frame_result.stdout)).convert("RGBA")
                arr = np.array(img) if OPENCV_OK else None
                if arr is not None:
                    transparent = np.sum(arr[:, :, 3] == 0)
                    total = arr.shape[0] * arr.shape[1]
                    result["transparent_ratio"] = transparent / total
        except Exception:
            pass

    return result


# ═══════════════════════════════════════════════════════════════
# 批量去背景
# ═══════════════════════════════════════════════════════════════

def batch_remove_bg(
    input_dir: str,
    output_dir: str,
    method: str = "auto",
    **kwargs,
) -> List[str]:
    """批量去背景（单图目录）"""
    os.makedirs(output_dir, exist_ok=True)
    results = []
    files = [f for f in os.listdir(input_dir)
             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

    for fname in files:
        input_path = os.path.join(input_dir, fname)
        output_path = os.path.join(output_dir, fname)
        result = remove_bg(input_path, output_path, method, **kwargs)
        if result:
            results.append(result)

    logger.info(f"\n✅ 批量去背景完成: {len(results)}/{len(files)}")
    return results


# ═══════════════════════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("去背景模块 v2.0")
    logger.info("=" * 60)

    logger.info(f"\n环境检测:")
    logger.info(f"  Pillow: {'✅' if PIL_OK else '❌'}")
    logger.info(f"  OpenCV: {'✅' if OPENCV_OK else '❌'}")
    logger.info(f"  ComfyUI: {'✅' if check_comfyui_alive() else '❌ (未运行)'}")
    logger.info(f"  BiRefNet模型: {'✅' if check_birefnet_available() else '❌ (未下载)'}")
    logger.info(f"  BiRefNet节点: {'✅' if check_birefnet_node() else '❌ (插件未装)'}")
    logger.info(f"  ffmpeg: {'✅' if os.path.exists(FFMPEG_PATH) else '❌'}")

    logger.info(f"\n可用方法: {get_available_methods()}")

    logger.info(f"\n使用示例:")
    logger.info(f"  # 单图去背景（自动选择最佳方法）")
    logger.info(f"  remove_bg('input.png', 'output.png', method='auto')")
    logger.info(f"")
    logger.info(f"  # BiRefNet专业抠图")
    logger.info(f"  remove_bg('input.png', 'output.png', method='birefnet', model='BiRefNet-general')")
    logger.info(f"")
    logger.info(f"  # 视频帧序列批量抠图（BiRefNet）")
    logger.info(f"  matting_video('frames/', 'matted/', method='birefnet', birefnet_roi=(0,0,580,1280))")
    logger.info(f"")
    logger.info(f"  # 背景差分抠图（固定背景视频）")
    logger.info(f"  matting_video('frames/', 'matted/', method='bgdiff', background_path='bg.png',")
    logger.info(f"                roi_list=[(216,(0,130,280,500)), (288,(0,430,400,1000))])")
    logger.info(f"")
    logger.info(f"  # 合成ProRes 4444透明视频")
    logger.info(f"  compose_prores('matted/', 'output.mov', fps=24)")
    logger.info(f"")
    logger.info(f"  # 验证Alpha通道")
    logger.info(f"  verify_alpha('output.mov', sample_frame=100)")
