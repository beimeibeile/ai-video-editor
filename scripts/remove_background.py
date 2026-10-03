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

# ComfyUI配置
COMFYUI_URL = "http://127.0.0.1:8188"
RMBG_MODEL_DIR = r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\models\RMBG"


def check_rmbg_available() -> bool:
    """检查ComfyUI RMBG模型是否可用"""
    if not os.path.exists(RMBG_MODEL_DIR):
        return False
    models = [f for f in os.listdir(RMBG_MODEL_DIR) if f.endswith(('.pth', '.safetensors', '.ckpt'))]
    return len(models) > 0


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
        print("  ⚠️ ComfyUI RMBG模型不可用，回退到Pillow")
        return None

    # TODO: 实现ComfyUI RMBG API调用
    # 需要先上传图片到ComfyUI，然后运行RMBG工作流，再下载结果
    print("  ⚠️ ComfyUI RMBG接口待实现，回退到Pillow")
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
        if check_rmbg_available():
            method = "comfyui"
        else:
            method = "pillow"
        print(f"  自动选择: {method}")

    if method == "comfyui":
        result = remove_bg_comfyui(input_path, output_path, **kwargs)
        if result:
            return result
        print("  回退到Pillow")

    if method == "pillow":
        return remove_bg_pillow(input_path, output_path, **kwargs)

    print(f"❌ 未知方法: {method}")
    return None


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
