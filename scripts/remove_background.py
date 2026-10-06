"""
去背景模块 v1.0
支持多种去背景方案，自动选择最佳可用方案：
1. ComfyUI RMBG（专业级，需模型）
2. Pillow改进版（颜色容差+边缘羽化，兜底）

使用方法：
    from remove_background import remove_bg
    result = remove_bg("input.png", "output.png", method="auto")
"""
import os
import sys
import json
import urllib.request
from typing import Optional, Tuple

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
RMBG_MODEL_DIR = r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\models\RMBG"


def check_rmbg_available() -> bool:
    """检查ComfyUI RMBG模型是否可用"""
    if not os.path.exists(RMBG_MODEL_DIR):
        return False
    models = [f for f in os.listdir(RMBG_MODEL_DIR) if f.endswith(('.pth', '.safetensors', '.ckpt'))]
    return len(models) > 0


def check_comfyui_birefnet() -> bool:
    """检查ComfyUI中BiRefNet节点是否可用"""
    try:
        req = urllib.request.Request(f"{COMFYUI_URL}/object_info/BiRefNet")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        return bool(data.get("BiRefNet"))
    except Exception:
        return False


def remove_bg_pillow(
    input_path: str,
    output_path: str,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    tolerance: int = 30,
    feather: int = 2,
) -> Optional[str]:
    """
    Pillow改进版去背景：颜色容差+边缘羽化

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        bg_color: 背景色（默认白色）
        tolerance: 颜色容差（0-255，越大去除越多）
        feather: 边缘羽化半径（像素）

    Returns:
        输出路径或None
    """
    if not PIL_OK:
        print("❌ Pillow不可用")
        return None

    try:
        img = Image.open(input_path).convert("RGBA")
        pixels = img.load()
        w, h = img.size

        # 创建mask
        mask = Image.new("L", (w, h), 0)
        mask_pixels = mask.load()

        br, bg, bb = bg_color
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                # 计算与背景色的距离
                dist = ((r - br) ** 2 + (g - bg) ** 2 + (b - bb) ** 2) ** 0.5
                if dist < tolerance:
                    mask_pixels[x, y] = 0  # 背景
                else:
                    # 边缘渐变：距离越近，透明度越低
                    edge_factor = min(1.0, (dist - tolerance) / (tolerance * 0.5))
                    mask_pixels[x, y] = int(255 * edge_factor)

        # 羽化边缘
        if feather > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))

        # 应用mask
        result = img.copy()
        result.putalpha(mask)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        result.save(output_path, "PNG")
        print(f"  ✅ Pillow去背景: {os.path.basename(output_path)} (容差={tolerance}, 羽化={feather})")
        return output_path
    except Exception as e:
        print(f"  ❌ Pillow去背景失败: {e}")
        return None


def remove_bg_opencv(
    input_path: str,
    output_path: str,
    iterations: int = 5,
) -> Optional[str]:
    """
    OpenCV GrabCut去背景（比Pillow颜色容差更准确）

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        iterations: GrabCut迭代次数（越多越精细但越慢）

    Returns:
        输出路径或None
    """
    if not OPENCV_OK:
        print("  ⚠️ OpenCV不可用，回退到Pillow")
        return None

    try:
        # OpenCV imread不支持中文路径，用numpy.fromfile + imdecode
        img = cv2.imdecode(np.fromfile(input_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"  ❌ 无法读取图片: {input_path}")
            return None

        h, w = img.shape[:2]
        mask = np.zeros((h, w), np.uint8)

        # 初始化：假设中心区域为前景，边缘为背景
        rect = (int(w * 0.05), int(h * 0.05),
                int(w * 0.9), int(h * 0.9))

        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        cv2.grabCut(img, mask, rect, bgd_model, fgd_model,
                    iterations, cv2.GC_INIT_WITH_RECT)

        # 生成alpha通道：确定前景+可能前景=不透明
        alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

        # 边缘羽化
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

        # 合并为RGBA
        b, g, r = cv2.split(img)
        rgba = cv2.merge([r, g, b, alpha])

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        # cv2.imwrite不支持中文路径，用imencode + tofile
        ext = os.path.splitext(output_path)[1] or '.png'
        success, buf = cv2.imencode(ext, rgba)
        if success:
            buf.tofile(output_path)
        else:
            cv2.imwrite(output_path, rgba)
        print(f"  ✅ OpenCV GrabCut去背景: {os.path.basename(output_path)} (迭代={iterations})")
        return output_path
    except Exception as e:
        print(f"  ❌ OpenCV去背景失败: {e}")
        return None


def remove_bg_comfyui(
    input_path: str,
    output_path: str,
    model_name: str = None,
) -> Optional[str]:
    """
    ComfyUI RMBG去背景（专业级）

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        model_name: RMBG模型名（None则自动选择）

    Returns:
        输出路径或None
    """
    if not check_rmbg_available():
        print("  ⚠️ ComfyUI RMBG模型不可用")
        return None

    if not check_comfyui_birefnet():
        print("  ⚠️ ComfyUI BiRefNet节点未安装，回退到OpenCV")
        return None

    # ComfyUI RMBG API调用（BiRefNet节点可用时）
    try:
        import uuid
        client_id = str(uuid.uuid4())

        # 1. 上传图片
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
            upload_result = json.loads(r.read())
        uploaded_name = upload_result.get('name', 'input.png')

        # 2. 构建工作流
        workflow = {
            "1": {"class_type": "LoadImage", "inputs": {"image": uploaded_name}},
            "2": {"class_type": "BiRefNet", "inputs": {
                "image": ["1", 0],
                "device": "cuda",
            }},
            "3": {"class_type": "SaveImage", "inputs": {
                "images": ["2", 0],
                "filename_prefix": "rmbg_output",
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

        # 4. 轮询结果
        import time
        for _ in range(60):  # 最多等60秒
            time.sleep(1)
            try:
                with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5) as r:
                    history = json.loads(r.read())
                if prompt_id in history:
                    outputs = history[prompt_id].get('outputs', {})
                    for node_id, node_out in outputs.items():
                        if 'images' in node_out:
                            img_info = node_out['images'][0]
                            img_url = f"{COMFYUI_URL}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder', '')}&type={img_info.get('type', 'output')}"
                            urllib.request.urlretrieve(img_url, output_path)
                            print(f"  ✅ ComfyUI RMBG去背景: {os.path.basename(output_path)}")
                            return output_path
                    break
            except Exception:
                continue

        print("  ⚠️ ComfyUI RMBG超时，回退到OpenCV")
        return None
    except Exception as e:
        print(f"  ❌ ComfyUI RMBG失败: {e}，回退到OpenCV")
        return None


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
        method: auto / pillow / comfyui
        **kwargs: 传递给具体方法的参数

    Returns:
        输出路径或None
    """
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_nobg{ext}"

    print(f"\n去背景: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")
    print(f"  方法: {method}")

    if method == "auto":
        if check_rmbg_available() and check_comfyui_birefnet():
            method = "comfyui"
        elif OPENCV_OK:
            method = "opencv"
        else:
            method = "pillow"
        print(f"  自动选择: {method}")

    if method == "comfyui":
        result = remove_bg_comfyui(input_path, output_path, **kwargs)
        if result:
            return result
        print("  回退到OpenCV")

    if method in ("comfyui", "opencv"):
        result = remove_bg_opencv(input_path, output_path, **kwargs)
        if result:
            return result
        print("  回退到Pillow")

    # 最终兜底：Pillow
    return remove_bg_pillow(input_path, output_path, **kwargs)


def batch_remove_bg(
    input_dir: str,
    output_dir: str,
    method: str = "auto",
    **kwargs,
) -> list:
    """
    批量去背景

    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        method: 去背景方法
        **kwargs: 传递给具体方法的参数

    Returns:
        成功的输出路径列表
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for fname in os.listdir(input_dir):
        if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            input_path = os.path.join(input_dir, fname)
            output_path = os.path.join(output_dir, fname)
            result = remove_bg(input_path, output_path, method, **kwargs)
            if result:
                results.append(result)

    print(f"\n✅ 批量去背景完成: {len(results)}/{len(os.listdir(input_dir))}")
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("去背景模块 v1.0")
    print("=" * 60)
    print(f"\nPillow: {'✅' if PIL_OK else '❌'}")
    print(f"ComfyUI RMBG: {'✅' if check_rmbg_available() else '❌ (模型未下载)'}")
    print(f"\n可用方法: auto / pillow / comfyui")
    print(f"\n使用示例:")
    print(f"  remove_bg('input.png', 'output.png', method='auto', tolerance=40, feather=3)")
    print(f"  batch_remove_bg('inputs/', 'outputs/', method='pillow')")
    print(f"\nRMBG模型下载地址:")
    print(f"  https://huggingface.co/briaai/RMBG-1.4")
    print(f"  放到: {RMBG_MODEL_DIR}")
