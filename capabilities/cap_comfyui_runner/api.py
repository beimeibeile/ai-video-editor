"""
ComfyUI高级场景API
封装常用任务：图片超分、批量超分等
"""
import os
import time
from typing import List, Optional
from .comfy_client import ComfyClient, load_workflow_template

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "workflow_templates")

# 可用超分模型（根据用户本地实际安装）
UPSCALE_MODELS = [
    "RealESRGAN_x4plus.pth",
    "RealESRGAN_x4plus_anime_6B.pth",
    "4x-UltraSharp.pth",
    "4x_NMKD-Superscale-SP_178000_G.pth",
    "8x_NMKD-Superscale_150000_G.pth",
    "ESRGAN_4x.pth",
    "BSRGAN.pth",
    "SwinIR_4x.pth",
    "fooocus_upscaler_s409985e5.bin",
]


def upscale_image(
    input_path: str,
    output_path: str = None,
    model_name: str = "RealESRGAN_x4plus.pth",
    server_addr: str = "127.0.0.1:8188",
    timeout: int = 300,
) -> str:
    """
    单张图片超分（4x）

    Args:
        input_path: 输入图片路径
        output_path: 输出路径（None则自动命名）
        model_name: 超分模型文件名
        server_addr: ComfyUI地址
        timeout: 超时秒数

    Returns:
        输出文件路径
    """
    client = ComfyClient(server_addr)
    if not client.is_running():
        raise ConnectionError("ComfyUI未运行，请先启动ComfyUI")

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_upscaled{ext}"

    # 加载工作流模板
    timestamp = int(time.time())
    workflow = load_workflow_template(
        os.path.join(TEMPLATE_DIR, "upscale_esrgan.json"),
        input_image=os.path.basename(input_path),
        model_name=model_name,
        timestamp=timestamp,
    )

    # 执行
    input_images = {os.path.basename(input_path): input_path}
    output_dir = os.path.dirname(output_path) or "."
    results = client.run_workflow(
        workflow, input_images=input_images,
        output_dir=output_dir, timeout=timeout
    )

    # 重命名为指定输出名
    if results and os.path.exists(results[0]) and results[0] != output_path:
        os.replace(results[0], output_path)

    return output_path


def img2video_ltx25(
    image_path: str,
    output_path: str,
    prompt: str = "smooth camera movement, cinematic, high quality",
    negative_prompt: str = "blurry, low quality, distorted, static, no motion",
    width: int = 768,
    height: int = 448,
    frames: int = 97,
    fps: int = 24,
    steps: int = 42,
    seed: int = None,
    cfg: float = 1.0,
    strength: float = 1.0,
    model: str = "int8_distilled",
    lora_strength: float = 1.0,
    generate_audio: bool = False,
    server_addr: str = "127.0.0.1:8188",
    timeout: int = 600,
) -> str:
    """
    LTX-2.5 INT8 图生视频（Image-to-Video）

    将静态图片转化为动态视频，支持运镜、动作生成。
    核心节点：LTXVImgToVideo（一次性生成conditioning+latent）。

    重要：height必须能被32整除（如448/480/512），
    不能用432（会导致VAE编码维度错误）。

    Args:
        image_path: 输入图片路径（本地文件）
        output_path: 输出视频路径（.mp4）
        prompt: 运动描述提示词（英文效果最佳）
        negative_prompt: 负向提示词
        width/height: 输出分辨率（height必须能被32整除）
        frames: 帧数（97帧≈4秒@24fps，必须为8n+1）
        fps: 帧率
        steps: 采样步数
        seed: 随机种子（None为随机）
        cfg: CFG值（LTX-2.5用1.0）
        strength: 图像引导强度（1.0=完全遵循原图，0.5=更自由创作）
        model: 模型版本 "int8_distilled" 或 "int8_dev_lora"
        lora_strength: LoRA强度（仅dev_lora模式）
        generate_audio: 是否同时生成音频（默认False）
        server_addr: ComfyUI地址
        timeout: 超时秒数

    Returns:
        输出视频文件路径
    """
    import os as _os
    import uuid as _uuid
    import urllib.request as _urllib_request

    if not _os.path.exists(image_path):
        raise FileNotFoundError(f"输入图片不存在: {image_path}")

    # height必须能被32整除
    if height % 32 != 0:
        height = (height // 32) * 32
        print(f"  ⚠️ height调整为{height}（必须能被32整除）")

    if seed is None:
        seed = int(_uuid.uuid4().int % (2**31))

    cfg_models = LTX25_MODELS.get(model, LTX25_MODELS["int8_distilled"])
    use_lora = cfg_models.get("lora") is not None

    # 上传图片到ComfyUI
    img_filename = _os.path.basename(image_path)
    with open(image_path, "rb") as f:
        img_data = f.read()
    boundary = "----WebKitFormBoundary" + _uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"image\"; filename=\"{img_filename}\"\r\n"
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + img_data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = _urllib_request.Request(
        f"http://{server_addr}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with _urllib_request.urlopen(req, timeout=30) as resp:
        upload_result = json.loads(resp.read())
    comfy_img_name = upload_result.get("name", img_filename)
    print(f"  图片已上传: {comfy_img_name}")

    # 构建工作流
    if use_lora:
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {
                "unet_name": cfg_models["unet"], "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {
                "clip_name": cfg_models["clip"], "type": "ltxv"}},
            "3": {"class_type": "LoraLoader", "inputs": {
                "model": ["1", 0], "clip": ["2", 0],
                "lora_name": cfg_models["lora"],
                "strength_model": lora_strength, "strength_clip": lora_strength}},
            "4": {"class_type": "VAELoader", "inputs": {
                "vae_name": cfg_models["vae"]}},
            "5": {"class_type": "LoadImage", "inputs": {"image": comfy_img_name}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {
                "text": prompt, "clip": ["3", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {
                "text": negative_prompt, "clip": ["3", 1]}},
            "8": {"class_type": "LTXVImgToVideo", "inputs": {
                "positive": ["6", 0], "negative": ["7", 0],
                "vae": ["4", 0], "image": ["5", 0],
                "width": width, "height": height, "length": frames,
                "batch_size": 1, "strength": strength}},
            "9": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler_ancestral_cfg_pp", "scheduler": "sgm_uniform",
                "denoise": 1.0, "model": ["3", 0],
                "positive": ["8", 0], "negative": ["8", 1],
                "latent_image": ["8", 2]}},
            "10": {"class_type": "LTXVTiledVAEDecode", "inputs": {
                "latents": ["9", 0], "vae": ["4", 0],
                "horizontal_tiles": 1, "vertical_tiles": 1,
                "overlap": 6, "last_frame_fix": False}},
            "11": {"class_type": "CreateVideo", "inputs": {
                "images": ["10", 0], "fps": fps}},
            "12": {"class_type": "SaveVideo", "inputs": {
                "video": ["11", 0], "filename_prefix": "ltx25_i2v",
                "format": "auto", "codec": "auto"}},
        }
    else:
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {
                "unet_name": cfg_models["unet"], "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {
                "clip_name": cfg_models["clip"], "type": "ltxv"}},
            "3": {"class_type": "VAELoader", "inputs": {
                "vae_name": cfg_models["vae"]}},
            "4": {"class_type": "LoadImage", "inputs": {"image": comfy_img_name}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {
                "text": prompt, "clip": ["2", 0]}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {
                "text": negative_prompt, "clip": ["2", 0]}},
            "7": {"class_type": "LTXVImgToVideo", "inputs": {
                "positive": ["5", 0], "negative": ["6", 0],
                "vae": ["3", 0], "image": ["4", 0],
                "width": width, "height": height, "length": frames,
                "batch_size": 1, "strength": strength}},
            "8": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler_ancestral_cfg_pp", "scheduler": "sgm_uniform",
                "denoise": 1.0, "model": ["1", 0],
                "positive": ["7", 0], "negative": ["7", 1],
                "latent_image": ["7", 2]}},
            "9": {"class_type": "LTXVTiledVAEDecode", "inputs": {
                "latents": ["8", 0], "vae": ["3", 0],
                "horizontal_tiles": 1, "vertical_tiles": 1,
                "overlap": 6, "last_frame_fix": False}},
            "10": {"class_type": "CreateVideo", "inputs": {
                "images": ["9", 0], "fps": fps}},
            "11": {"class_type": "SaveVideo", "inputs": {
                "video": ["10", 0], "filename_prefix": "ltx25_i2v",
                "format": "auto", "codec": "auto"}},
        }

    # 提交并等待
    prompt_id = _submit_workflow(workflow, server_addr)
    print(f"  任务已提交: {prompt_id}")
    result = _wait_for_completion(prompt_id, server_addr, timeout)

    # 下载输出视频
    output_dir = _os.path.dirname(output_path)
    if output_dir:
        _os.makedirs(output_dir, exist_ok=True)

    for node_id, node_output in result.get("outputs", {}).items():
        if "images" in node_output:
            for img_info in node_output["images"]:
                if img_info.get("type") == "output":
                    vid_url = f"http://{server_addr}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder', '')}&type=output"
                    _urllib_request.urlretrieve(vid_url, output_path)
                    print(f"  视频已保存: {output_path}")
                    return output_path

    raise RuntimeError("未找到输出视频")


def flf2video_ltx25(
    first_image_path: str,
    last_image_path: str,
    output_path: str,
    prompt: str = "smooth transition, cinematic camera movement, high quality",
    negative_prompt: str = "blurry, low quality, distorted, static",
    width: int = 768,
    height: int = 448,
    frames: int = 97,
    fps: int = 24,
    steps: int = 42,
    seed: int = None,
    cfg: float = 1.0,
    first_strength: float = 1.0,
    last_strength: float = 1.0,
    model: str = "int8_distilled",
    lora_strength: float = 1.0,
    server_addr: str = "127.0.0.1:8188",
    timeout: int = 600,
) -> str:
    """
    LTX-2.5 首尾帧视频（First-Last Frame to Video, FLF2V）

    提供首帧和尾帧两张图片，模型自动生成中间的过渡视频。
    使用LTXVAddGuide节点在frame 0和frame N-1添加图像引导。

    Args:
        first_image_path: 首帧图片路径
        last_image_path: 尾帧图片路径
        output_path: 输出视频路径
        prompt: 运动/过渡描述提示词
        negative_prompt: 负向提示词
        width/height: 输出分辨率（height必须能被32整除）
        frames: 帧数（97帧≈4秒@24fps）
        fps: 帧率
        steps: 采样步数
        seed: 随机种子
        cfg: CFG值
        first_strength: 首帧引导强度（1.0=完全遵循）
        last_strength: 尾帧引导强度
        model: 模型版本 "int8_distilled" 或 "int8_dev_lora"
        lora_strength: LoRA强度
        server_addr: ComfyUI地址
        timeout: 超时秒数

    Returns:
        输出视频文件路径
    """
    import os as _os
    import uuid as _uuid
    import urllib.request as _urllib_request

    if not _os.path.exists(first_image_path):
        raise FileNotFoundError(f"首帧图片不存在: {first_image_path}")
    if not _os.path.exists(last_image_path):
        raise FileNotFoundError(f"尾帧图片不存在: {last_image_path}")

    if height % 32 != 0:
        height = (height // 32) * 32

    if seed is None:
        seed = int(_uuid.uuid4().int % (2**31))

    cfg_models = LTX25_MODELS.get(model, LTX25_MODELS["int8_distilled"])
    use_lora = cfg_models.get("lora") is not None

    # 上传两张图片
    def _upload_img(path):
        fname = _os.path.basename(path)
        with open(path, "rb") as f:
            data = f.read()
        boundary = "----WebKitFormBoundary" + _uuid.uuid4().hex
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{fname}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = _urllib_request.Request(
            f"http://{server_addr}/upload/image",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        with _urllib_request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()).get("name", fname)

    first_img = _upload_img(first_image_path)
    last_img = _upload_img(last_image_path)
    print(f"  首帧: {first_img}, 尾帧: {last_img}")

    # 构建工作流
    if use_lora:
        base = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": cfg_models["unet"], "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": cfg_models["clip"], "type": "ltxv"}},
            "3": {"class_type": "LoraLoader", "inputs": {"model": ["1", 0], "clip": ["2", 0], "lora_name": cfg_models["lora"], "strength_model": lora_strength, "strength_clip": lora_strength}},
            "4": {"class_type": "VAELoader", "inputs": {"vae_name": cfg_models["vae"]}},
            "5": {"class_type": "LoadImage", "inputs": {"image": first_img}},
            "6": {"class_type": "LoadImage", "inputs": {"image": last_img}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["3", 1]}},
            "8": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt, "clip": ["3", 1]}},
            "9": {"class_type": "LTXVConditioning", "inputs": {"positive": ["7", 0], "negative": ["8", 0], "frame_rate": fps}},
            "10": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": width, "height": height, "length": frames, "batch_size": 1}},
            "11": {"class_type": "LTXVAddGuide", "inputs": {"positive": ["9", 0], "negative": ["9", 1], "vae": ["4", 0], "latent": ["10", 0], "image": ["5", 0], "frame_idx": 0, "strength": first_strength}},
            "12": {"class_type": "LTXVAddGuide", "inputs": {"positive": ["11", 0], "negative": ["11", 1], "vae": ["4", 0], "latent": ["11", 2], "image": ["6", 0], "frame_idx": frames - 1, "strength": last_strength}},
            "13": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler_ancestral_cfg_pp", "scheduler": "sgm_uniform", "denoise": 1.0, "model": ["3", 0], "positive": ["12", 0], "negative": ["12", 1], "latent_image": ["12", 2]}},
            "14": {"class_type": "LTXVTiledVAEDecode", "inputs": {"latents": ["13", 0], "vae": ["4", 0], "horizontal_tiles": 1, "vertical_tiles": 1, "overlap": 6, "last_frame_fix": False}},
            "15": {"class_type": "CreateVideo", "inputs": {"images": ["14", 0], "fps": fps}},
            "16": {"class_type": "SaveVideo", "inputs": {"video": ["15", 0], "filename_prefix": "ltx25_flf2v", "format": "auto", "codec": "auto"}},
        }
    else:
        base = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": cfg_models["unet"], "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": cfg_models["clip"], "type": "ltxv"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": cfg_models["vae"]}},
            "4": {"class_type": "LoadImage", "inputs": {"image": first_img}},
            "5": {"class_type": "LoadImage", "inputs": {"image": last_img}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt, "clip": ["2", 0]}},
            "8": {"class_type": "LTXVConditioning", "inputs": {"positive": ["6", 0], "negative": ["7", 0], "frame_rate": fps}},
            "9": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": width, "height": height, "length": frames, "batch_size": 1}},
            "10": {"class_type": "LTXVAddGuide", "inputs": {"positive": ["8", 0], "negative": ["8", 1], "vae": ["3", 0], "latent": ["9", 0], "image": ["4", 0], "frame_idx": 0, "strength": first_strength}},
            "11": {"class_type": "LTXVAddGuide", "inputs": {"positive": ["10", 0], "negative": ["10", 1], "vae": ["3", 0], "latent": ["10", 2], "image": ["5", 0], "frame_idx": frames - 1, "strength": last_strength}},
            "12": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler_ancestral_cfg_pp", "scheduler": "sgm_uniform", "denoise": 1.0, "model": ["1", 0], "positive": ["11", 0], "negative": ["11", 1], "latent_image": ["11", 2]}},
            "13": {"class_type": "LTXVTiledVAEDecode", "inputs": {"latents": ["12", 0], "vae": ["3", 0], "horizontal_tiles": 1, "vertical_tiles": 1, "overlap": 6, "last_frame_fix": False}},
            "14": {"class_type": "CreateVideo", "inputs": {"images": ["13", 0], "fps": fps}},
            "15": {"class_type": "SaveVideo", "inputs": {"video": ["14", 0], "filename_prefix": "ltx25_flf2v", "format": "auto", "codec": "auto"}},
        }

    prompt_id = _submit_workflow(base, server_addr)
    print(f"  任务已提交: {prompt_id}")
    result = _wait_for_completion(prompt_id, server_addr, timeout)

    output_dir = _os.path.dirname(output_path)
    if output_dir:
        _os.makedirs(output_dir, exist_ok=True)

    for node_id, node_output in result.get("outputs", {}).items():
        if "images" in node_output:
            for img_info in node_output["images"]:
                if img_info.get("type") == "output":
                    vid_url = f"http://{server_addr}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder', '')}&type=output"
                    _urllib_request.urlretrieve(vid_url, output_path)
                    print(f"  视频已保存: {output_path}")
                    return output_path

    raise RuntimeError("未找到输出视频")


# ==================== 工具函数 ====================

def upscale_batch(
    input_paths: List[str],
    output_dir: str,
    model_name: str = "RealESRGAN_x4plus.pth",
    server_addr: str = "127.0.0.1:8188",
    timeout_per_image: int = 300,
) -> List[str]:
    """
    批量图片超分（串行执行，避免显存溢出）

    Args:
        input_paths: 输入图片路径列表
        output_dir: 输出目录
        model_name: 超分模型
        server_addr: ComfyUI地址
        timeout_per_image: 单张超时

    Returns:
        输出文件路径列表
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []
    total = len(input_paths)

    for i, input_path in enumerate(input_paths):
        print(f"[{i+1}/{total}] 超分: {os.path.basename(input_path)}")
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f"{base}_upscaled.png")
        try:
            result = upscale_image(
                input_path, output_path=output_path,
                model_name=model_name, server_addr=server_addr,
                timeout=timeout_per_image,
            )
            results.append(result)
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            results.append(None)

    return results


def check_comfyui_ready(server_addr: str = "127.0.0.1:8188") -> dict:
    """
    检查ComfyUI运行状态和GPU信息

    Returns:
        {"running": bool, "gpu": str, "vram_free_gb": float, "vram_total_gb": float}
    """
    client = ComfyClient(server_addr)
    if not client.is_running():
        return {"running": False}
    stats = client.get_system_stats()
    device = stats.get("devices", [{}])[0]
    return {
        "running": True,
        "gpu": device.get("name", "unknown"),
        "vram_free_gb": round(device.get("vram_free", 0) / (1024**3), 1),
        "vram_total_gb": round(device.get("vram_total", 0) / (1024**3), 1),
    }


# ==================== 批量抠图 ====================

MATTING_MODELS = [
    "BiRefNet-general",
    "BiRefNet-HR",
    "BiRefNet-portrait",
    "BiRefNet-matting",
    "BiRefNet-HR-matting",
    "BiRefNet_lite",
    "BiRefNet_lite-2K",
    "BiRefNet_lite-matting",
    "BiRefNet_dynamic",
    "BiRefNet_toonout",
    "Lucida",
    "RMBG-2.0",
]


def matting_image(
    input_path: str,
    output_path: str = None,
    model_name: str = "BiRefNet-general",
    server_addr: str = "127.0.0.1:8188",
    timeout: int = 120,
) -> str:
    """单张图片抠图（去背景，输出带透明通道PNG）"""
    client = ComfyClient(server_addr)
    if not client.is_running():
        raise ConnectionError("ComfyUI未运行，请先启动ComfyUI")

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_matted.png"

    use_rmbg = model_name in ["RMBG-2.0", "INSPYRENET", "BEN", "BEN2"]
    template_file = "matting_rmbg.json" if use_rmbg else "matting_birefnet.json"

    timestamp = int(time.time())
    workflow = load_workflow_template(
        os.path.join(TEMPLATE_DIR, template_file),
        input_image=os.path.basename(input_path),
        model_name=model_name,
        timestamp=timestamp,
    )

    input_images = {os.path.basename(input_path): input_path}
    output_dir = os.path.dirname(output_path) or "."
    results = client.run_workflow(
        workflow, input_images=input_images,
        output_dir=output_dir, timeout=timeout
    )

    if results and os.path.exists(results[0]) and results[0] != output_path:
        os.replace(results[0], output_path)

    return output_path


def matting_batch(
    input_paths: List[str],
    output_dir: str,
    model_name: str = "BiRefNet-general",
    server_addr: str = "127.0.0.1:8188",
    timeout_per_image: int = 120,
) -> List[str]:
    """批量图片抠图（串行执行）"""
    os.makedirs(output_dir, exist_ok=True)
    results = []
    total = len(input_paths)

    for i, input_path in enumerate(input_paths):
        print(f"[{i+1}/{total}] 抠图: {os.path.basename(input_path)}")
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f"{base}_matted.png")
        try:
            result = matting_image(
                input_path, output_path=output_path,
                model_name=model_name, server_addr=server_addr,
                timeout=timeout_per_image,
            )
            results.append(result)
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            results.append(None)

    return results


# ==================== 人脸统一 ====================

FACE_UNIFY_CHECKPOINTS = [
    "majicmixRealistic_v7.safetensors",
    "dreamshaper_631BakedVae.safetensors",
    "cyberrealistic_v41BackToBasics.safetensors",
]

# 图生图方案不需要IP-Adapter模型，保留常量供未来参考
FACE_UNIFY_IPADAPTER_MODELS = [
    "sd15\\ip-adapter-plus-face_sd15.bin",
    "sd15\\ip-adapter-full-face_sd15.bin",
]

FACE_UNIFY_CLIP_VISION = [
    "SD15-CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
]


def face_unify_image(
    source_image: str,
    target_image: str = None,
    output_path: str = None,
    swap_model: str = "inswapper_128.onnx",
    facedetection: str = "retinaface_resnet50",
    face_restore_model: str = "none",
    face_restore_visibility: float = 1.0,
    codeformer_weight: float = 0.5,
    server_addr: str = "127.0.0.1:8188",
    timeout: int = 120,
    # 以下参数保留兼容（ReActor方案不使用）
    reference_image: str = None,
    checkpoint: str = None,
    ipadapter_model: str = None,
    positive_prompt: str = None,
    negative_prompt: str = None,
    width: int = None,
    height: int = None,
    seed: int = None,
    steps: int = None,
    cfg: float = None,
    face_weight: float = None,
    denoise: float = None,
) -> str:
    """
    单张人脸统一：将源脸的人脸特征交换到目标图上（ReActor方案）

    Args:
        source_image: 源脸参考图路径（提供人脸特征）
        target_image: 目标图路径（需要换脸的图，保留服装/背景/构图）
                     若为None，则source_image同时作为源脸和目标图（自换脸，无意义）
        output_path: 输出路径（None则自动命名）
        swap_model: 人脸交换模型（默认inswapper_128.onnx）
        facedetection: 人脸检测模型（retinaface_resnet50/retinaface_mobile0.25/YOLOv5l/YOLOv5n）
        face_restore_model: 人脸修复模型（none/GFPGANv1.4.pth/codeformer.pth）
        face_restore_visibility: 人脸修复可见度（0.1-1.0）
        codeformer_weight: CodeFormer权重（0-1，仅face_restore_model=codeformer时生效）
        server_addr: ComfyUI地址
        timeout: 超时秒数

    Returns:
        输出文件路径
    """
    client = ComfyClient(server_addr)
    if not client.is_running():
        raise ConnectionError("ComfyUI未运行，请先启动ComfyUI")

    # 兼容旧调用：如果只传了reference_image，用它作为source和target
    if reference_image is not None and source_image is None:
        source_image = reference_image
    if target_image is None:
        target_image = source_image

    if output_path is None:
        base = os.path.splitext(target_image)[0]
        output_path = f"{base}_faceunified.png"

    timestamp = int(time.time())
    workflow = load_workflow_template(
        os.path.join(TEMPLATE_DIR, "face_unify_reactor.json"),
        source_image=os.path.basename(source_image),
        target_image=os.path.basename(target_image),
        swap_model=swap_model,
        facedetection=facedetection,
        face_restore_model=face_restore_model,
        face_restore_visibility=face_restore_visibility,
        codeformer_weight=codeformer_weight,
        timestamp=timestamp,
    )

    input_images = {
        os.path.basename(source_image): source_image,
        os.path.basename(target_image): target_image,
    }
    output_dir = os.path.dirname(output_path) or "."
    results = client.run_workflow(
        workflow, input_images=input_images,
        output_dir=output_dir, timeout=timeout
    )

    if results and os.path.exists(results[0]) and results[0] != output_path:
        os.replace(results[0], output_path)

    return output_path


def face_unify_batch(
    source_image: str,
    target_images: List[str],
    output_dir: str,
    **kwargs,
) -> List[str]:
    """
    批量人脸统一：以同一源脸统一多张目标图片的人脸（ReActor方案）

    Args:
        source_image: 源脸参考图路径
        target_images: 目标图片路径列表
        output_dir: 输出目录
        **kwargs: 传递给face_unify_image的参数（swap_model, facedetection等）

    Returns:
        输出文件路径列表
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []
    total = len(target_images)
    for i, target in enumerate(target_images):
        print(f"[{i+1}/{total}] 人脸统一: {os.path.basename(target)}")
        out_name = os.path.splitext(os.path.basename(target))[0] + "_faceunified.png"
        out_path = os.path.join(output_dir, out_name)
        try:
            result = face_unify_image(
                source_image=source_image,
                target_image=target,
                output_path=out_path,
                **kwargs,
            )
            results.append(result)
        except Exception as e:
            print(f"  ⚠️ 失败: {e}")
    return results

# ═══════════════════════════════════════════════════════════════
# ControlNet 能力
# ═══════════════════════════════════════════════════════════════

CONTROLNET_MODELS = [
    "control_v11p_sd15_openpose.pth",
    "control_v11p_sd15_canny_fp16.safetensors",
    "control_v11f1p_sd15_depth.pth",
    "control_v11p_sd15_lineart_fp16.safetensors",
    "control_v11p_sd15_softedge_fp16.safetensors",
    "control_v11p_sd15_seg.pth",
    "control_v11p_sd15_inpaint.pth",
    "control_v11f1e_sd15_tile.pth",
]


def controlnet_generate(
    control_image: str,
    positive_prompt: str,
    output_path: str = None,
    controlnet_model: str = "control_v11p_sd15_openpose.pth",
    strength: float = 0.85,
    checkpoint: str = "majicmixRealistic_v7.safetensors",
    negative_prompt: str = "worst quality, low quality, deformed, ugly, blurry, watermark, text",
    width: int = 768,
    height: int = 1024,
    seed: int = None,
    steps: int = 35,
    cfg: float = 7.5,
    sampler_name: str = "dpmpp_2m",
    scheduler: str = "karras",
    server_addr: str = "127.0.0.1:8188",
    timeout: int = 180,
) -> str:
    """
    ControlNet文生图：用控制图（openpose/canny/depth等）引导生成

    Args:
        control_image: 控制图路径（姿态骨架/边缘图/深度图等）
        positive_prompt: 正面提示词
        output_path: 输出路径
        controlnet_model: ControlNet模型名
        strength: 控制强度（0-1，越大越遵循控制图）
        checkpoint: 底模
        negative_prompt: 负面提示词
        width/height: 输出尺寸
        seed: 随机种子
        steps/cfg: 采样参数
        sampler_name/scheduler: 采样器
        server_addr: ComfyUI地址
        timeout: 超时

    Returns:
        输出文件路径
    """
    client = ComfyClient(server_addr)
    if not client.is_running():
        raise ConnectionError("ComfyUI未运行")

    if seed is None:
        import random
        seed = random.randint(0, 2**31 - 1)

    if output_path is None:
        output_path = os.path.join(os.path.dirname(control_image) or ".", "controlnet_output.png")

    timestamp = int(time.time())
    workflow = load_workflow_template(
        os.path.join(TEMPLATE_DIR, "controlnet_txt2img.json"),
        checkpoint=checkpoint,
        control_image=os.path.basename(control_image),
        controlnet_model=controlnet_model,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        strength=strength,
        width=width,
        height=height,
        seed=seed,
        steps=steps,
        cfg=cfg,
        sampler_name=sampler_name,
        scheduler=scheduler,
        timestamp=timestamp,
    )

    input_images = {os.path.basename(control_image): control_image}
    output_dir = os.path.dirname(output_path) or "."
    results = client.run_workflow(
        workflow, input_images=input_images,
        output_dir=output_dir, timeout=timeout
    )

    if results and os.path.exists(results[0]) and results[0] != output_path:
        os.replace(results[0], output_path)

    return output_path


def generate_pose_skeleton(
    view: str = "front",
    output_path: str = None,
    width: int = 512,
    height: int = 768,
) -> str:
    """
    生成标准站立姿态的OpenPose骨架图

    Args:
        view: 视角 - "front"(正面), "side"(侧面), "back"(背面)
        output_path: 输出路径
        width/height: 骨架图尺寸

    Returns:
        骨架图文件路径
    """
    from PIL import Image, ImageDraw

    if output_path is None:
        output_path = os.path.join(os.getcwd(), f"pose_{view}.png")

    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = width // 2
    colors = [(255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),(85,255,0),
              (0,255,0),(0,255,85),(0,255,170),(0,255,255),(0,170,255),(0,85,255),
              (0,0,255),(85,0,255),(170,0,255),(255,0,255),(255,0,170),(255,0,85)]
    connections = [(0,1),(1,2),(2,3),(3,4),(1,5),(5,6),(6,7),(1,8),(8,9),(9,10),
                   (1,11),(11,12),(12,13),(0,14),(0,15),(14,16),(15,17)]

    # 标准站立姿态关键点
    if view == "front":
        kp = [(cx,120),(cx,170),(cx-70,180),(cx-85,280),(cx-90,380),(cx+70,180),
              (cx+85,280),(cx+90,380),(cx-40,380),(cx-45,530),(cx-45,680),(cx+40,380),
              (cx+45,530),(cx+45,680),(cx-12,110),(cx+12,110),(cx-22,125),(cx+22,125)]
    elif view == "side":
        sx = cx - 30
        kp = [(sx,120),(sx,170),(sx+10,180),(sx+15,280),(sx+20,380),(sx-10,180),
              (sx-15,280),(sx-20,380),(sx+5,380),(sx+10,530),(sx+10,680),(sx-5,380),
              (sx-10,530),(sx-10,680),(sx-15,110),None,None,(sx+15,120)]
    elif view == "back":
        kp = [(cx,120),(cx,170),(cx-70,180),(cx-85,280),(cx-90,380),(cx+70,180),
              (cx+85,280),(cx+90,380),(cx-40,380),(cx-45,530),(cx-45,680),(cx+40,380),
              (cx+45,530),(cx+45,680),None,None,(cx-22,125),(cx+22,125)]
    else:
        raise ValueError(f"未知视角: {view}，应为 front/side/back")

    # 画连接线
    for (i, j) in connections:
        if i < len(kp) and j < len(kp) and kp[i] and kp[j]:
            draw.line([kp[i], kp[j]], fill=colors[i], width=4)

    # 画关键点
    for i, p in enumerate(kp):
        if p:
            r = 5
            draw.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=colors[i], outline=(255,255,255))

    # 面部椭圆
    if kp[0]:
        nx, ny = kp[0]
        draw.ellipse([nx-25, ny-35, nx+25, ny+20], outline=(255,255,255), width=2)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path)
    return output_path


def generate_character_views(
    reference_image: str,
    output_dir: str,
    character_prompt: str = None,
    views: List[str] = None,
    controlnet_strength: float = 0.85,
    face_unify: bool = True,
    **kwargs,
) -> dict:
    """
    生成角色三视图（正面/侧面/背面）

    Args:
        reference_image: 参考人物图（用于人脸统一）
        output_dir: 输出目录
        character_prompt: 角色描述提示词（None则用默认老年女性模板）
        views: 要生成的视角列表，默认["front","side","back"]
        controlnet_strength: ControlNet姿态控制强度
        face_unify: 是否用ReActor统一人脸
        **kwargs: 传递给controlnet_generate的参数

    Returns:
        {view: output_path} 字典
    """
    if views is None:
        views = ["front", "side", "back"]

    os.makedirs(output_dir, exist_ok=True)
    pose_dir = os.path.join(output_dir, "_poses")
    os.makedirs(pose_dir, exist_ok=True)

    if character_prompt is None:
        character_prompt = (
            "best quality, masterpiece, ultra detailed, photorealistic, 8k, "
            "single person, solo, only one person, "
            "full body portrait, standing straight, arms relaxed at sides, "
            "pure white background, studio lighting, soft shadow under feet"
        )

    negative = kwargs.pop("negative_prompt",
        "worst quality, low quality, deformed, ugly, blurry, watermark, text, "
        "multiple people, two people, three people, multiple views, reference sheet, "
        "extra fingers, bad anatomy, missing limbs, cropped, "
        "cane, walking stick, sitting, crouching, bending, arms raised, "
        "park, trees, outdoor, cartoon, anime, illustration, 3d render"
    )

    results = {}
    for view in views:
        print(f"[{view}] 生成姿态骨架...")
        pose_path = os.path.join(pose_dir, f"pose_{view}.png")
        generate_pose_skeleton(view, pose_path)

        view_prompt = character_prompt
        if view == "front":
            view_prompt += ", front view, facing camera directly"
        elif view == "side":
            view_prompt += ", side view, profile view, facing left"
        elif view == "back":
            view_prompt += ", back view, from directly behind, facing away"

        print(f"[{view}] ControlNet生成...")
        raw_path = os.path.join(output_dir, f"{view}_raw.png")
        controlnet_generate(
            control_image=pose_path,
            positive_prompt=view_prompt,
            output_path=raw_path,
            strength=controlnet_strength,
            negative_prompt=negative,
            **kwargs,
        )

        if face_unify:
            print(f"[{view}] ReActor人脸统一...")
            final_path = os.path.join(output_dir, f"{view}_final.png")
            face_unify_image(
                source_image=reference_image,
                target_image=raw_path,
                output_path=final_path,
                face_restore_model="none",
            )
            results[view] = final_path
        else:
            results[view] = raw_path

        print(f"[{view}] ✅ {results[view]}")

    return results

# ═══════════════════════════════════════════════════════════════
# Qwen 图像编辑 — 角色三视图（最佳方案）
# ═══════════════════════════════════════════════════════════════

QWEN_VIEW_PROMPTS = {
    "front": "获取人物全景像白底图，人物站立，双臂自然下垂，不需要摆出姿势，看向前方",
    "side": "获取人物左侧面白底图，人物全身站立，双臂自然下垂，面朝左方，纯白背景",
    "back": "获取人物背面白底图，人物全身站立，双臂自然下垂，纯白背景",
    "half": "获取人物上半身白底图，面向观众，身体正直",
}


def _build_qwen_views_workflow(
    unet_name, lora_name, vae_name, clip_name,
    input_image_name, longer_edge, seed, steps, cfg,
    prompts, views,
):
    """动态构建Qwen三视图工作流（支持任意视图组合）"""
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": unet_name, "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"lora_name": lora_name, "strength_model": 1.0, "model": ["1", 0]}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": vae_name}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": clip_name, "type": "qwen_image", "device": "default"}},
        "5": {"class_type": "LoadImage", "inputs": {"image": input_image_name}},
        "6": {"class_type": "ResizeImagesByLongerEdge", "inputs": {"longer_edge": longer_edge, "images": ["5", 0]}},
        "7": {"class_type": "VAEEncode", "inputs": {"pixels": ["6", 0], "vae": ["3", 0]}},
    }

    base_id = 10
    for i, view in enumerate(views):
        nid = str(base_id + i * 4)
        wf[nid] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {
            "prompt": prompts.get(view, ""), "clip": ["4", 0], "vae": ["3", 0], "image1": ["6", 0]}}
        wf[str(int(nid)+1)] = {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": [nid, 0]}}
        wf[str(int(nid)+2)] = {"class_type": "KSampler", "inputs": {
            "seed": seed, "control_after_generate": "randomize",
            "steps": steps, "cfg": cfg, "sampler_name": "euler_ancestral", "scheduler": "simple", "denoise": 1.0,
            "model": ["2", 0], "positive": [nid, 0], "negative": [str(int(nid)+1), 0], "latent_image": ["7", 0]}}
        wf[str(int(nid)+3)] = {"class_type": "VAEDecode", "inputs": {"samples": [str(int(nid)+2), 0], "vae": ["3", 0]}}
        save_id = str(100 + i)
        wf[save_id] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": "qwen_" + view, "images": [str(int(nid)+3), 0]}}

    return wf


def _apply_crop(image_path, crop_top=0, crop_sides=0):
    """留白裁剪：裁剪上方和两侧像素，数值越大留白越少"""
    if crop_top <= 0 and crop_sides <= 0:
        return image_path
    from PIL import Image
    img = Image.open(image_path)
    w, h = img.size
    left = crop_sides
    right = w - crop_sides
    top = crop_top
    bottom = h
    if left >= right or top >= bottom:
        return image_path
    cropped = img.crop((left, top, right, bottom))
    cropped.save(image_path, quality=95)
    return image_path


def generate_character_views_qwen(
    input_image: str,
    output_dir: str,
    views: List[str] = None,
    longer_edge: int = 2048,
    seed: int = None,
    steps: int = 5,
    cfg: float = 1.0,
    unet_name: str = "千问\\qwen_image_edit_2511_fp8.safetensors",
    lora_name: str = "千问\\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",
    vae_name: str = "qwen_image_vae.safetensors",
    clip_name: str = "qwen_2.5_vl_7b_fp8_scaled.safetensors",
    custom_prompt: str = "",
    custom_prompts: dict = None,
    crop_top: int = 0,
    crop_sides: int = 0,
    concat_output: bool = True,
    server_addr: str = "127.0.0.1:8188",
    timeout: int = 600,
) -> dict:
    """
    基于千问Qwen-Image-Edit模型生成角色三视图（最佳方案）

    原理：图像编辑模型直接从原图生成不同角度视图，天然保持人物特征和服装一致，
    无需额外人脸统一步骤。4步Lightning LoRA极速生成。

    Args:
        input_image: 输入人物图片路径
        output_dir: 输出目录
        views: 视角列表，默认["front","side","back"]，可选"half"(上半身)
        longer_edge: 图像长边尺寸（16GB显存以上用2048，不足用1024或1536）
        seed: 随机种子
        steps: 采样步数（Lightning模型用5步）
        cfg: CFG值（Qwen模型用1.0）
        unet_name/lora_name/vae_name/clip_name: 模型名称
        custom_prompt: 自定义补充提示词，追加到所有视图提示词后（如"黑色鞋子，蓝色裤子"）
        custom_prompts: 自定义提示词字典，覆盖特定视图的默认提示词
        crop_top: 裁剪上方像素数（控制上方留白，越大留白越少）
        crop_sides: 裁剪两侧像素数（控制两侧留白，越大留白越少）
        concat_output: 是否输出横向拼接图
        server_addr: ComfyUI地址
        timeout: 超时

    Returns:
        {view: output_path} 字典，包含"concat"拼接图（如果启用）
    """
    import random
    from PIL import Image

    if views is None:
        views = ["front", "side", "back"]

    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    os.makedirs(output_dir, exist_ok=True)
    client = ComfyClient(server_addr)
    if not client.is_running():
        raise ConnectionError("ComfyUI未运行")

    # 构建提示词：默认 + 自定义补充 + 特定视图覆盖
    prompts = {}
    for view in views:
        p = QWEN_VIEW_PROMPTS.get(view, "")
        if custom_prompt:
            p = p + "，" + custom_prompt
        prompts[view] = p
    if custom_prompts:
        prompts.update(custom_prompts)

    # 动态构建工作流
    workflow = _build_qwen_views_workflow(
        unet_name, lora_name, vae_name, clip_name,
        os.path.basename(input_image), longer_edge, seed, steps, cfg,
        prompts, views,
    )

    results = client.run_workflow(
        workflow,
        input_images={os.path.basename(input_image): input_image},
        output_dir=output_dir, timeout=timeout
    )

    # 整理输出 + 留白裁剪
    output = {}
    for r in results:
        basename = os.path.basename(r)
        for view in views:
            if basename.startswith("qwen_" + view):
                out_path = os.path.join(output_dir, view + ".png")
                if r != out_path:
                    os.replace(r, out_path)
                if crop_top > 0 or crop_sides > 0:
                    _apply_crop(out_path, crop_top, crop_sides)
                output[view] = out_path

    # 横向拼接
    if concat_output and len(output) >= 2:
        ordered_views = [v for v in ["front", "side", "back", "half"] if v in output]
        images = [Image.open(output[v]) for v in ordered_views]
        h = max(img.height for img in images)
        w = sum(img.width for img in images)
        concat = Image.new("RGB", (w, h), (255, 255, 255))
        x = 0
        for img in images:
            concat.paste(img, (x, 0))
            x += img.width
        concat_path = os.path.join(output_dir, "three_views_concat.png")
        concat.save(concat_path, quality=95)
        output["concat"] = concat_path

    return output

# ═══════════════════════════════════════════════════════════════
# Z-Image-Turbo 极速文生图（默认生图方案）
# ═══════════════════════════════════════════════════════════════

ZIMAGE_MODELS = {
    "bf16": "Z-Image\\z_image_turbo_bf16.safetensors",
    "fp8": "Z-Image\\z-image-turbo-fp8-e4m3fn.safetensors",
}


def txt2img_zimage(
    prompt: str,
    output_path: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    seed: int = None,
    cfg: float = 1.0,
    model: str = "bf16",
    negative_prompt: str = "",
    shift: float = 3.0,
    server_addr: str = "127.0.0.1:8188",
    timeout: int = 180,
) -> str:
    """
    Z-Image-Turbo 极速文生图（默认生图方案）

    原理：阿里通义千问Z-Image模型 + Turbo加速，4步即可生成高质量图片。
    基于MMDiT架构，使用qwen_3_4b CLIP(lumina2) + ae.safetensors VAE。

    Args:
        prompt: 正向提示词
        output_path: 输出图片路径
        width/height: 图片尺寸（默认1024x1024）
        steps: 采样步数（4步极速，8步高质量）
        seed: 随机种子（None为随机）
        cfg: CFG值（Z-Image用1.0）
        model: 模型版本 "bf16"(推荐，8秒) 或 "fp8"(显存小)
        negative_prompt: 负向提示词（Z-Image通常用空字符串+ConditioningZeroOut）
        shift: ModelSamplingAuraFlow shift参数（默认3.0）
        server_addr: ComfyUI地址
        timeout: 超时

    Returns:
        输出图片路径
    """
    import random

    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    unet_name = ZIMAGE_MODELS.get(model, ZIMAGE_MODELS["bf16"])
    weight_dtype = "default" if model == "bf16" else "fp8_e4m3fn"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    client = ComfyClient(server_addr)
    if not client.is_running():
        raise ConnectionError("ComfyUI未运行")

    workflow = {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": unet_name, "weight_dtype": weight_dtype}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen_3_4b.safetensors", "type": "lumina2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {
            "text": prompt, "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {
            "text": negative_prompt, "clip": ["2", 0]}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {
            "width": width, "height": height, "batch_size": 1}},
        "8": {"class_type": "ModelSamplingAuraFlow", "inputs": {
            "shift": shift, "model": ["1", 0]}},
        "9": {"class_type": "KSampler", "inputs": {
            "seed": seed, "control_after_generate": "randomize",
            "steps": steps, "cfg": cfg,
            "sampler_name": "res_multistep", "scheduler": "simple", "denoise": 1.0,
            "model": ["8", 0], "positive": ["4", 0], "negative": ["6", 0],
            "latent_image": ["7", 0]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": "zimage_txt2img", "images": ["10", 0]}}
    }

    output_dir = os.path.dirname(output_path)
    results = client.run_workflow(workflow, output_dir=output_dir, timeout=timeout)

    if results:
        if results[0] != output_path:
            os.replace(results[0], output_path)
        return output_path
    raise RuntimeError("Z-Image-Turbo生成失败，无输出")

# ═══════════════════════════════════════════════════════════════
# LTX-2.5 INT8 文生视频（高质量动效素材生成）
# ═══════════════════════════════════════════════════════════════

LTX25_MODELS = {
    "int8_distilled": {
        "unet": "ltx\\ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors",
        "clip": "ltx\\gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors",
        "vae": "ltx\\ltx-2.5-video-vae-bf16.safetensors",
        "lora": None,
    },
    "int8_dev_lora": {
        "unet": "ltx\\ltx-2.5-22b-dev-transformer-comfy-int8-convrot.safetensors",
        "clip": "ltx\\gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors",
        "vae": "ltx\\ltx-2.5-video-vae-bf16.safetensors",
        "lora": "ltx\\ltx-2.5-22b-distilled-lora-450-bf16.safetensors",
    },
}
# 兼容旧调用
LTX25_MODELS["int8"] = LTX25_MODELS["int8_distilled"]

LTX25_PRESETS = {
    "480p": {"width": 768, "height": 432, "frames": 97},
    "720p": {"width": 1280, "height": 720, "frames": 97},
    "5s":   {"width": 768, "height": 432, "frames": 121},
}


def txt2video_ltx25(
    prompt: str,
    output_path: str,
    width: int = 768,
    height: int = 432,
    frames: int = 97,
    fps: float = 24.0,
    steps: int = 42,
    seed: int = None,
    cfg: float = 1.0,
    negative_prompt: str = "blurry, low quality, distorted, ugly, watermark, text",
    model: str = "int8_distilled",
    lora_strength: float = 1.0,
    generate_audio: bool = False,
    server_addr: str = "127.0.0.1:8188",
    timeout: int = 600,
) -> str:
    """
    LTX-2.5 INT8 文生视频（Lightricks开源，22B参数，INT8量化）

    核心优势：动作控制精准、支持快慢变速切换、电影级画质。
    两种模型模式：
    - int8_distilled: 直接使用distilled主模型（20GB，简单快速）
    - int8_dev_lora: dev基础模型 + distilled LoRA（20GB+8.3GB，可切换LoRA更灵活）
    经RTX 3080 12GB验证：768x432@97帧可稳定运行。

    Args:
        prompt: 正向提示词（英文效果最佳）
        output_path: 输出视频路径（.mp4）
        width/height: 分辨率（默认768x432，12GB显存推荐）
        frames: 帧数（97帧≈4秒@24fps，帧数必须为8n+1）
        fps: 帧率（默认24）
        steps: 采样步数（42步 distilled模型）
        seed: 随机种子（None为随机）
        cfg: CFG值（LTX-2.5 distilled用1.0）
        negative_prompt: 负向提示词
        model: 模型版本 "int8_distilled" 或 "int8_dev_lora"
        lora_strength: LoRA强度（仅dev_lora模式有效，默认1.0）
        generate_audio: 是否同时生成音频（默认False，True时输出带音频的视频）
        server_addr: ComfyUI地址
        timeout: 超时秒数（默认600）

    Returns:
        输出视频文件路径
    """
    import random

    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    cfg_models = LTX25_MODELS.get(model, LTX25_MODELS["int8"])

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    client = ComfyClient(server_addr)
    if not client.is_running():
        raise ConnectionError("ComfyUI未运行，请先启动ComfyUI")

    use_lora = cfg_models.get("lora") is not None

    if use_lora:
        # dev主模型 + LoRA 模式
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {
                "unet_name": cfg_models["unet"], "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {
                "clip_name": cfg_models["clip"], "type": "ltxv"}},
            "3": {"class_type": "LoraLoader", "inputs": {
                "model": ["1", 0], "clip": ["2", 0],
                "lora_name": cfg_models["lora"],
                "strength_model": lora_strength, "strength_clip": lora_strength}},
            "4": {"class_type": "VAELoader", "inputs": {
                "vae_name": cfg_models["vae"]}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {
                "text": prompt, "clip": ["3", 1]}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {
                "text": negative_prompt, "clip": ["3", 1]}},
            "7": {"class_type": "LTXVConditioning", "inputs": {
                "positive": ["5", 0], "negative": ["6", 0], "frame_rate": fps}},
            "8": {"class_type": "EmptyLTXVLatentVideo", "inputs": {
                "width": width, "height": height, "length": frames, "batch_size": 1}},
            "9": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler_ancestral_cfg_pp", "scheduler": "sgm_uniform",
                "denoise": 1.0, "model": ["3", 0],
                "positive": ["7", 0], "negative": ["7", 1],
                "latent_image": ["8", 0]}},
            "10": {"class_type": "LTXVTiledVAEDecode", "inputs": {
                "latents": ["9", 0], "vae": ["4", 0],
                "horizontal_tiles": 1, "vertical_tiles": 1,
                "overlap": 6, "last_frame_fix": False}},
            "11": {"class_type": "CreateVideo", "inputs": {
                "images": ["10", 0], "fps": fps}},
            "12": {"class_type": "SaveVideo", "inputs": {
                "video": ["11", 0], "filename_prefix": "ltx25_txt2video",
                "format": "auto", "codec": "auto"}},
        }
    else:
        # distilled主模型直连模式
        workflow = {
            "1": {"class_type": "UNETLoader", "inputs": {
                "unet_name": cfg_models["unet"], "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {
                "clip_name": cfg_models["clip"], "type": "ltxv"}},
            "3": {"class_type": "VAELoader", "inputs": {
                "vae_name": cfg_models["vae"]}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {
                "text": prompt, "clip": ["2", 0]}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {
                "text": negative_prompt, "clip": ["2", 0]}},
            "6": {"class_type": "LTXVConditioning", "inputs": {
                "positive": ["4", 0], "negative": ["5", 0], "frame_rate": fps}},
            "7": {"class_type": "EmptyLTXVLatentVideo", "inputs": {
                "width": width, "height": height, "length": frames, "batch_size": 1}},
            "8": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler_ancestral_cfg_pp", "scheduler": "sgm_uniform",
                "denoise": 1.0, "model": ["1", 0],
                "positive": ["6", 0], "negative": ["6", 1],
                "latent_image": ["7", 0]}},
            "9": {"class_type": "LTXVTiledVAEDecode", "inputs": {
                "latents": ["8", 0], "vae": ["3", 0],
                "horizontal_tiles": 1, "vertical_tiles": 1,
                "overlap": 6, "last_frame_fix": False}},
            "10": {"class_type": "CreateVideo", "inputs": {
                "images": ["9", 0], "fps": fps}},
            "11": {"class_type": "SaveVideo", "inputs": {
                "video": ["10", 0], "filename_prefix": "ltx25_txt2video",
                "format": "auto", "codec": "auto"}},
        }

    output_dir = os.path.dirname(output_path) or "."
    results = client.run_workflow(workflow, output_dir=output_dir, timeout=timeout)

    if results:
        if results[0] != output_path:
            os.replace(results[0], output_path)
        return output_path
    raise RuntimeError("LTX-2.5文生视频失败，无输出")
