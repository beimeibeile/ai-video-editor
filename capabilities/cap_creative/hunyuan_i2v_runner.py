"""
混元Video 1.5 I2V 运行器 v1.0
==============================
基于ComfyUI API的混元Video 1.5图生视频运行器。

依赖：
- ComfyUI在线（http://127.0.0.1:8188）
- 模型：hunyuanvideo1.5_720p_i2v_fp16.safetensors (15.5GB)
- VAE：hunyuanvideo15_vae_fp16.safetensors
- CLIP：qwen_2.5_vl_7b_fp8_scaled.safetensors + byt5_small_glyphxl_fp16.safetensors（DualCLIPLoader, type=hunyuan_video_15）
- 节点：HunyuanVideo15ImageToVideo, TextEncodeHunyuanVideo_ImageToVideo

使用方式：
    from hunyuan_i2v_runner import HunyuanI2VRunner
    runner = HunyuanI2VRunner()
    result = runner.generate(
        image_path="input.jpg",
        prompt="一个人在海边散步，夕阳西下",
        duration=5.0,  # 秒
        fps=24,
        output_path="output.webm",
    )
"""

import os
import sys
import json
import time
import uuid
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional

COMFYUI_URL = "http://127.0.0.1:8188"

# 模型配置（混元Video 1.5正确编码器：Qwen2.5-VL-7B + ByT5 Small）
MODEL_CONFIG = {
    "unet": "hunyuanvideo1.5_720p_i2v_fp16.safetensors",
    "clip1": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
    "clip2": "byt5_small_glyphxl_fp16.safetensors",
    "clip_type": "hunyuan_video_15",
    "vae": "hunyuanvideo15_vae_fp16.safetensors",
}


class HunyuanI2VRunner:
    """混元Video 1.5 I2V运行器"""

    def __init__(self, comfyui_url: str = COMFYUI_URL):
        self.comfyui_url = comfyui_url.rstrip("/")
        self.model_config = MODEL_CONFIG.copy()

    def _get_comfyui_output_dir(self) -> str:
        """获取ComfyUI输出目录（从API或默认路径）"""
        try:
            resp = urllib.request.urlopen(f"{self.comfyui_url}/settings", timeout=5)
            settings = json.loads(resp.read())
            output_dir = settings.get("output_directory", "")
            if output_dir and os.path.isabs(output_dir):
                return output_dir
        except Exception:
            pass
        # 默认路径
        return r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\output"

    def check_available(self) -> Dict[str, Any]:
        """检查混元I2V是否可用"""
        result = {
            "comfyui_online": False,
            "model_available": False,
            "clip_available": False,
            "vae_available": False,
            "nodes_available": False,
            "details": {},
        }

        try:
            # 检查ComfyUI在线
            urllib.request.urlopen(f"{self.comfyui_url}/system_stats", timeout=5)
            result["comfyui_online"] = True

            # 检查节点和模型
            r = urllib.request.urlopen(f"{self.comfyui_url}/object_info", timeout=10)
            data = json.loads(r.read())

            # 检查专用节点
            required_nodes = [
                "HunyuanVideo15ImageToVideo",
                "TextEncodeHunyuanVideo_ImageToVideo",
                "EmptyHunyuanVideo15Latent",
            ]
            result["nodes_available"] = all(n in data for n in required_nodes)
            result["details"]["missing_nodes"] = [n for n in required_nodes if n not in data]

            # 检查模型
            if "UNETLoader" in data:
                unets = data["UNETLoader"]["input"]["required"]["unet_name"][0]
                result["model_available"] = self.model_config["unet"] in unets
            if "DualCLIPLoader" in data:
                clips = data["DualCLIPLoader"]["input"]["required"]["clip_name1"][0]
                result["clip_available"] = (self.model_config["clip1"] in clips and
                                            self.model_config["clip2"] in clips)
                result["details"]["clip1"] = self.model_config["clip1"] in clips
                result["details"]["clip2"] = self.model_config["clip2"] in clips
            if "VAELoader" in data:
                vaes = data["VAELoader"]["input"]["required"]["vae_name"][0]
                result["vae_available"] = self.model_config["vae"] in vaes

        except Exception as e:
            result["details"]["error"] = str(e)

        result["ready"] = all([
            result["comfyui_online"],
            result["model_available"],
            result["clip_available"],
            result["vae_available"],
            result["nodes_available"],
        ])
        return result

    def _upload_image(self, image_path: str) -> str:
        """上传图像到ComfyUI"""
        filename = os.path.basename(image_path)
        with open(image_path, "rb") as f:
            image_data = f.read()

        boundary = uuid.uuid4().hex
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode() + image_data + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"{self.comfyui_url}/upload/image",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        return result.get("name", filename)

    def _build_workflow(self, image_name: str, prompt: str,
                        negative_prompt: str = "",
                        width: int = 720, height: int = 1280,
                        num_frames: int = 81, fps: int = 24,
                        steps: int = 30, cfg: float = 6.0,
                        seed: int = -1,
                        low_vram: bool = False) -> Dict[str, Any]:
        """构建混元I2V工作流（显存优化版：fp8量化+Tiled VAE）"""
        workflow = {}
        node_id = 1

        def add_node(class_type, inputs):
            nonlocal node_id
            nid = str(node_id)
            workflow[nid] = {"class_type": class_type, "inputs": inputs}
            node_id += 1
            return nid

        # 1. 加载UNET（显存优化：fp8量化）
        unet_dtype = "fp8_e4m3fn" if low_vram else "default"
        unet_id = add_node("UNETLoader", {
            "unet_name": self.model_config["unet"],
            "weight_dtype": unet_dtype,
        })

        # 2. 加载双CLIP（混元Video 1.5需要Qwen2.5-VL + ByT5 Small）
        clip_id = add_node("DualCLIPLoader", {
            "clip_name1": self.model_config["clip1"],
            "clip_name2": self.model_config["clip2"],
            "type": self.model_config["clip_type"],
        })

        # 3. 加载CLIPVision（混元I2V需要）
        clip_vision_id = add_node("CLIPVisionLoader", {
            "clip_name": "SD15-CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
        })

        # 4. 加载VAE
        vae_id = add_node("VAELoader", {
            "vae_name": self.model_config["vae"],
        })

        # 5. 加载首帧图像
        image_id = add_node("LoadImage", {
            "image": image_name,
        })

        # 6. CLIPVision编码图像
        clip_vision_out_id = add_node("CLIPVisionEncode", {
            "clip_vision": [clip_vision_id, 0],
            "image": [image_id, 0],
            "crop": "center",
        })

        # 7. 文本编码（正向）
        pos_text_id = add_node("TextEncodeHunyuanVideo_ImageToVideo", {
            "clip": [clip_id, 0],
            "clip_vision_output": [clip_vision_out_id, 0],
            "prompt": prompt,
            "image_interleave": 2,
        })

        # 8. 文本编码（负向）
        neg_text_id = add_node("TextEncodeHunyuanVideo_ImageToVideo", {
            "clip": [clip_id, 0],
            "clip_vision_output": [clip_vision_out_id, 0],
            "prompt": negative_prompt or "blurry, low quality, distorted, watermark, text",
            "image_interleave": 2,
        })

        # 9. 空latent
        latent_id = add_node("EmptyHunyuanVideo15Latent", {
            "width": width,
            "height": height,
            "length": num_frames,
            "batch_size": 1,
        })

        # 10. 混元I2V条件处理（输出positive, negative, latent）
        hunyuan_id = add_node("HunyuanVideo15ImageToVideo", {
            "positive": [pos_text_id, 0],
            "negative": [neg_text_id, 0],
            "vae": [vae_id, 0],
            "width": width,
            "height": height,
            "length": num_frames,
            "batch_size": 1,
            "start_image": [image_id, 0],
        })

        # 11. KSampler采样
        sampler_id = add_node("KSampler", {
            "model": [unet_id, 0],
            "positive": [hunyuan_id, 0],  # Hunyuan输出的positive
            "negative": [hunyuan_id, 1],  # Hunyuan输出的negative
            "latent_image": [hunyuan_id, 2],  # Hunyuan输出的latent
            "seed": seed if seed >= 0 else 42,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1.0,
        })

        # 12. VAE解码（显存优化：Tiled VAE）
        if low_vram:
            decode_id = add_node("VAEDecodeTiled", {
                "samples": [sampler_id, 0],
                "vae": [vae_id, 0],
                "tile_size": 256,
                "overlap": 64,
                "temporal_size": 16,
                "temporal_overlap": 4,
            })
        else:
            decode_id = add_node("VAEDecode", {
                "samples": [sampler_id, 0],
                "vae": [vae_id, 0],
            })

        # 13. 保存
        save_id = add_node("SaveAnimatedWEBP", {
            "images": [decode_id, 0],
            "filename_prefix": "hunyuan_i2v",
            "fps": fps,
            "lossless": False,
            "quality": 80,
            "method": "default",
        })

        return workflow

    def generate(self, image_path: str, prompt: str,
                 negative_prompt: str = "",
                 duration: float = 3.0, fps: int = 24,
                 width: int = 720, height: int = 1280,
                 steps: int = 30, cfg: float = 6.0,
                 seed: int = -1,
                 output_dir: str = None,
                 timeout: int = 1800,
                 low_vram: bool = False) -> Dict[str, Any]:
        """
        生成I2V视频

        Args:
            image_path: 首帧图像路径
            prompt: 正向提示词
            negative_prompt: 负向提示词
            duration: 视频时长（秒）
            fps: 帧率
            width/height: 分辨率
            steps: 采样步数
            cfg: CFG scale
            seed: 随机种子（-1随机）
            output_dir: 输出目录
            timeout: 超时时间（秒）
            low_vram: 显存优化模式（fp8量化+Tiled VAE，12GB显卡建议开启）

        Returns:
            生成结果字典
        """
        print(f"\n{'='*60}")
        print(f"混元Video 1.5 I2V 生成")
        print(f"{'='*60}")
        print(f"图像: {image_path}")
        print(f"提示词: {prompt[:50]}...")
        print(f"时长: {duration}s, 帧率: {fps}fps, 分辨率: {width}x{height}")
        print(f"显存优化: {'开启 (fp8+TiledVAE)' if low_vram else '关闭'}")

        # 检查可用性
        avail = self.check_available()
        if not avail["ready"]:
            print(f"❌ 混元I2V不可用: {avail}")
            return {"status": "failed", "reason": "环境不可用", "details": avail}

        # 计算帧数（混元要求特定帧数，如81帧=3.375秒@24fps）
        num_frames = int(duration * fps)
        # 混元Video 1.5支持的帧数：13, 25, 49, 81, 129等（2^n+1）
        valid_frames = [13, 25, 49, 81, 129]
        num_frames = min(valid_frames, key=lambda x: abs(x - num_frames))
        actual_duration = num_frames / fps
        print(f"帧数: {num_frames} (实际时长: {actual_duration:.2f}s)")

        # 上传图像
        print(f"\n[1/4] 上传图像...")
        image_name = self._upload_image(image_path)
        print(f"  ✅ 已上传: {image_name}")

        # 构建工作流
        print(f"[2/4] 构建工作流...")
        workflow = self._build_workflow(
            image_name=image_name,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width, height=height,
            num_frames=num_frames, fps=fps,
            steps=steps, cfg=cfg, seed=seed,
            low_vram=low_vram,
        )

        # 提交任务
        print(f"[3/4] 提交生成任务...")
        client_id = str(uuid.uuid4())
        payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
        req = urllib.request.Request(
            f"{self.comfyui_url}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        prompt_data = json.loads(resp.read())
        prompt_id = prompt_data["prompt_id"]
        print(f"  ✅ 任务ID: {prompt_id}")

        # 等待完成
        print(f"[4/4] 等待生成完成（最长{timeout}秒）...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                history_resp = urllib.request.urlopen(
                    f"{self.comfyui_url}/history/{prompt_id}", timeout=10
                )
                history = json.loads(history_resp.read())
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    # 查找输出文件（images字段，animated字段是布尔值标记）
                    for node_out in outputs.values():
                        if "images" in node_out and node_out["images"]:
                            output_file = node_out["images"][0]["filename"]
                            # 从ComfyUI output目录复制到目标output_dir
                            comfyui_output_dir = self._get_comfyui_output_dir()
                            src_path = os.path.join(comfyui_output_dir, output_file)
                            dst_dir = output_dir or os.path.dirname(image_path)
                            os.makedirs(dst_dir, exist_ok=True)
                            output_path = os.path.join(dst_dir, output_file)
                            if os.path.exists(src_path) and src_path != output_path:
                                import shutil
                                shutil.copy2(src_path, output_path)
                            print(f"  ✅ 生成完成: {output_file}")
                            return {
                                "status": "success",
                                "prompt_id": prompt_id,
                                "output_file": output_file,
                                "output_path": output_path,
                                "num_frames": num_frames,
                                "duration": actual_duration,
                                "fps": fps,
                                "resolution": f"{width}x{height}",
                            }
            except Exception:
                pass

            # 检查进度
            try:
                prog_resp = urllib.request.urlopen(
                    f"{self.comfyui_url}/progress", timeout=5
                )
                prog = json.loads(prog_resp.read())
                if prog.get("value", 0) > 0:
                    pct = prog["value"] / prog.get("max", 1) * 100
                    print(f"  进度: {pct:.1f}%", end="\r")
            except Exception:
                pass

            time.sleep(3)

        print(f"\n  ⚠️ 超时（{timeout}秒），最后检查一次任务状态...")
        # 超时后再检查一次任务是否实际完成
        try:
            history_resp = urllib.request.urlopen(
                f"{self.comfyui_url}/history/{prompt_id}", timeout=10
            )
            history = json.loads(history_resp.read())
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for node_out in outputs.values():
                    if "images" in node_out and node_out["images"]:
                        output_file = node_out["images"][0]["filename"]
                        # 从ComfyUI output目录复制到目标output_dir
                        comfyui_output_dir = self._get_comfyui_output_dir()
                        src_path = os.path.join(comfyui_output_dir, output_file)
                        dst_dir = output_dir or os.path.dirname(image_path)
                        os.makedirs(dst_dir, exist_ok=True)
                        output_path = os.path.join(dst_dir, output_file)
                        if os.path.exists(src_path) and src_path != output_path:
                            import shutil
                            shutil.copy2(src_path, output_path)
                        print(f"  ✅ 任务实际已完成: {output_file}")
                        return {
                            "status": "success",
                            "prompt_id": prompt_id,
                            "output_file": output_file,
                            "output_path": output_path,
                            "num_frames": num_frames,
                            "duration": actual_duration,
                            "fps": fps,
                            "resolution": f"{width}x{height}",
                            "note": "超时后检测到任务已完成",
                        }
        except Exception as e:
            print(f"  检查失败: {e}")

        return {"status": "timeout", "prompt_id": prompt_id}

    def cleanup(self) -> bool:
        """
        释放ComfyUI显存资源（卸载模型）

        注意：批量生成时不要在每个generate后调用，
        应在全部生成完成后统一调用一次。

        Returns:
            bool: 是否成功
        """
        try:
            # 清空队列
            try:
                req = urllib.request.Request(
                    f"{self.comfyui_url}/queue",
                    data=json.dumps({"clear": True}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass

            # 卸载模型
            req = urllib.request.Request(
                f"{self.comfyui_url}/free",
                data=json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    print("  ✅ ComfyUI模型已卸载，显存已释放")
                    time.sleep(2)
                    return True
        except Exception as e:
            print(f"  ⚠️ 资源清理失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("混元Video 1.5 I2V 运行器 v1.0")
    print("=" * 60)

    runner = HunyuanI2VRunner()

    # 检查可用性
    avail = runner.check_available()
    print(f"\n环境检查:")
    print(f"  ComfyUI在线: {'✅' if avail['comfyui_online'] else '❌'}")
    print(f"  模型可用: {'✅' if avail['model_available'] else '❌'}")
    print(f"  CLIP可用: {'✅' if avail['clip_available'] else '❌'}")
    print(f"  VAE可用: {'✅' if avail['vae_available'] else '❌'}")
    print(f"  节点可用: {'✅' if avail['nodes_available'] else '❌'}")
    print(f"  缺失节点: {avail['details'].get('missing_nodes', [])}")
    print(f"  总体状态: {'✅ 就绪' if avail['ready'] else '❌ 不可用'}")
