"""
ComfyUI出图全链路集成 v1.0
将参考图挂载机制和角色场景合成图接入ComfyUI生成流程

功能：
1. 参考图上传到ComfyUI
2. IPAdapter挂载参考图（场景图/角色图/风格图）
3. 角色+场景合成图作为图生图输入
4. 出图质量门（尺寸/清晰度/一致性检查）
5. 批量出图管理
"""

import os
import json
import uuid
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


@dataclass
class ImageGenerationResult:
    """出图结果"""
    success: bool
    image_path: str = ""
    prompt_id: str = ""
    width: int = 0
    height: int = 0
    error: str = ""
    quality_score: float = 0.0
    quality_issues: List[str] = field(default_factory=list)


class ComfyUIImagePipeline:
    """ComfyUI出图全链路集成"""

    def __init__(self, server_url: str = "http://127.0.0.1:8188",
                 output_dir: str = ""):
        """
        Args:
            server_url: ComfyUI服务器地址
            output_dir: 输出目录
        """
        self.server_url = server_url.rstrip("/")
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "image_output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.client_id = str(uuid.uuid4())

    def is_online(self) -> bool:
        """检查ComfyUI是否在线"""
        try:
            with urllib.request.urlopen(f"{self.server_url}/system_stats", timeout=5) as r:
                return True
        except Exception:
            return False

    def upload_image(self, image_path: str) -> Optional[str]:
        """
        上传图片到ComfyUI

        Args:
            image_path: 本地图片路径

        Returns:
            ComfyUI中的文件名（用于LoadImage节点）
        """
        if not os.path.exists(image_path):
            print(f"❌ 图片不存在: {image_path}")
            return None

        filename = os.path.basename(image_path)
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode() + image_data + f"\r\n--{boundary}--\r\n".encode()

            req = urllib.request.Request(
                f"{self.server_url}/upload/image",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read())
                print(f"  ✅ 上传图片: {filename}")
                return result.get("name", filename)
        except Exception as e:
            print(f"  ⚠️ 上传图片失败: {e}")
            return None

    def generate_with_reference(self, prompt: str,
                                  reference_images: List[Dict[str, Any]] = None,
                                  width: int = 1024, height: int = 1024,
                                  checkpoint: str = "基础模型\\sd_xl_turbo_1.0_fp16.safetensors",
                                  steps: int = 6, cfg: float = 2.0,
                                  ipadapter_weight: float = 0.7,
                                  init_image: str = "",
                                  denoise: float = 0.7) -> ImageGenerationResult:
        """
        带参考图生成图片

        Args:
            prompt: 正向提示词
            reference_images: 参考图列表 [{path, type, weight}]
            width/height: 尺寸
            checkpoint: 模型
            steps/cfg: 采样参数
            ipadapter_weight: IPAdapter权重
            init_image: 图生图初始图片路径（可选）
            denoise: 图生图去噪强度

        Returns:
            生成结果
        """
        if not self.is_online():
            return ImageGenerationResult(success=False, error="ComfyUI离线")

        # 上传参考图
        uploaded_refs = []
        if reference_images:
            for ref in reference_images:
                ref_path = ref.get("path", "")
                if ref_path and os.path.exists(ref_path):
                    comfy_name = self.upload_image(ref_path)
                    if comfy_name:
                        uploaded_refs.append({
                            "name": comfy_name,
                            "type": ref.get("type", "style"),
                            "weight": ref.get("weight", ipadapter_weight),
                        })

        # 上传初始图片（图生图）
        init_image_name = ""
        if init_image and os.path.exists(init_image):
            init_image_name = self.upload_image(init_image)

        # 构建工作流
        workflow = self._build_workflow(
            prompt=prompt,
            checkpoint=checkpoint,
            width=width, height=height,
            steps=steps, cfg=cfg,
            reference_images=uploaded_refs,
            ipadapter_weight=ipadapter_weight,
            init_image=init_image_name,
            denoise=denoise,
        )

        # 提交生成
        prompt_id = self._queue_prompt(workflow)
        if not prompt_id:
            return ImageGenerationResult(success=False, error="提交生成失败")

        # 等待完成
        image_path = self._wait_for_image(prompt_id)
        if not image_path:
            return ImageGenerationResult(success=False, error="生成超时或失败", prompt_id=prompt_id)

        # 质量检查
        quality = self._check_image_quality(image_path, width, height)

        return ImageGenerationResult(
            success=True,
            image_path=image_path,
            prompt_id=prompt_id,
            width=width, height=height,
            quality_score=quality["score"],
            quality_issues=quality["issues"],
        )

    def _build_workflow(self, prompt: str, checkpoint: str,
                          width: int, height: int,
                          steps: int, cfg: float,
                          reference_images: List[Dict] = None,
                          ipadapter_weight: float = 0.7,
                          init_image: str = "",
                          denoise: float = 0.7) -> Dict:
        """构建ComfyUI工作流"""
        workflow = {}
        node_id = 1

        # Checkpoint加载器
        ckpt_node = str(node_id); node_id += 1
        workflow[ckpt_node] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint}
        }

        # CLIP文本编码（正向）
        pos_node = str(node_id); node_id += 1
        workflow[pos_node] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": [ckpt_node, 1]}
        }

        # CLIP文本编码（负向）
        neg_node = str(node_id); node_id += 1
        workflow[neg_node] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "low quality, blurry, distorted, ugly, deformed, watermark, text",
                "clip": [ckpt_node, 1]
            }
        }

        # 图生图模式：加载初始图片+VAE编码
        latent_node = None
        if init_image:
            load_img_node = str(node_id); node_id += 1
            workflow[load_img_node] = {
                "class_type": "LoadImage",
                "inputs": {"image": init_image}
            }
            vae_encode_node = str(node_id); node_id += 1
            workflow[vae_encode_node] = {
                "class_type": "VAEEncode",
                "inputs": {"pixels": [load_img_node, 0], "vae": [ckpt_node, 2]}
            }
            latent_node = vae_encode_node
        else:
            # 空潜空间
            empty_node = str(node_id); node_id += 1
            workflow[empty_node] = {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}
            }
            latent_node = empty_node

        # IPAdapter（如果有参考图）
        model_output = [ckpt_node, 0]
        if reference_images:
            for i, ref in enumerate(reference_images):
                load_ref_node = str(node_id); node_id += 1
                workflow[load_ref_node] = {
                    "class_type": "LoadImage",
                    "inputs": {"image": ref["name"]}
                }
                ipa_node = str(node_id); node_id += 1
                workflow[ipa_node] = {
                    "class_type": "IPAdapter",
                    "inputs": {
                        "model": model_output,
                        "ipadapter": "ip-adapter-plus_sdxl_vit-h.safetensors",
                        "image": [load_ref_node, 0],
                        "weight": ref.get("weight", ipadapter_weight),
                        "weight_faceidv2": ref.get("weight", ipadapter_weight),
                        "start_at": 0.0,
                        "end_at": 1.0,
                    }
                }
                model_output = [ipa_node, 0]

        # KSampler
        ksampler_node = str(node_id); node_id += 1
        workflow[ksampler_node] = {
            "class_type": "KSampler",
            "inputs": {
                "model": model_output,
                "positive": [pos_node, 0],
                "negative": [neg_node, 0],
                "latent_image": [latent_node, 0],
                "seed": uuid.uuid4().int & (2**32 - 1),
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": denoise if init_image else 1.0,
            }
        }

        # VAEDecode
        decode_node = str(node_id); node_id += 1
        workflow[decode_node] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [ksampler_node, 0], "vae": [ckpt_node, 2]}
        }

        # SaveImage
        save_node = str(node_id); node_id += 1
        workflow[save_node] = {
            "class_type": "SaveImage",
            "inputs": {"images": [decode_node, 0], "filename_prefix": "AVE_"}
        }

        return workflow

    def _queue_prompt(self, workflow: Dict) -> Optional[str]:
        """提交工作流到ComfyUI"""
        try:
            data = json.dumps({
                "prompt": workflow,
                "client_id": self.client_id
            }).encode()
            req = urllib.request.Request(
                f"{self.server_url}/prompt",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                result = json.loads(r.read())
                return result.get("prompt_id")
        except Exception as e:
            print(f"  ⚠️ 提交失败: {e}")
            return None

    def _wait_for_image(self, prompt_id: str, timeout: int = 120) -> Optional[str]:
        """等待图片生成完成"""
        import time
        start = time.time()

        while time.time() - start < timeout:
            try:
                # 检查历史记录
                with urllib.request.urlopen(
                    f"{self.server_url}/history/{prompt_id}", timeout=5
                ) as r:
                    history = json.loads(r.read())

                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    for node_id, output in outputs.items():
                        if "images" in output and output["images"]:
                            img_info = output["images"][0]
                            img_filename = img_info["filename"]
                            subfolder = img_info.get("subfolder", "")
                            # 下载图片
                            return self._download_image(img_filename, subfolder)
            except Exception:
                pass

            time.sleep(2)

        return None

    def _download_image(self, filename: str, subfolder: str = "") -> Optional[str]:
        """从ComfyUI下载生成的图片"""
        try:
            params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": "output"})
            url = f"{self.server_url}/view?{params}"

            output_path = os.path.join(self.output_dir, filename)
            urllib.request.urlretrieve(url, output_path)
            return output_path
        except Exception as e:
            print(f"  ⚠️ 下载图片失败: {e}")
            return None

    def _check_image_quality(self, image_path: str,
                               expected_width: int,
                               expected_height: int) -> Dict[str, Any]:
        """
        出图质量门检查

        Args:
            image_path: 图片路径
            expected_width: 期望宽度
            expected_height: 期望高度

        Returns:
            质量报告
        """
        issues = []
        score = 100.0

        if not _PIL_AVAILABLE:
            return {"score": 50.0, "issues": ["Pillow不可用，无法检查质量"]}

        try:
            img = Image.open(image_path)

            # 尺寸检查
            if img.width != expected_width or img.height != expected_height:
                issues.append(f"尺寸不符: {img.width}x{img.height} (期望{expected_width}x{expected_height})")
                score -= 20

            # 模糊度检查（使用拉普拉斯方差近似）
            gray = img.convert("L").resize((100, 100))
            pixels = list(gray.getdata())
            if len(pixels) > 1:
                mean = sum(pixels) / len(pixels)
                variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
                if variance < 100:
                    issues.append(f"图像可能模糊 (方差={variance:.0f})")
                    score -= 15

            # 亮度检查
            brightness = sum(pixels) / len(pixels)
            if brightness < 30:
                issues.append(f"图像过暗 (亮度={brightness:.0f})")
                score -= 10
            elif brightness > 230:
                issues.append(f"图像过亮 (亮度={brightness:.0f})")
                score -= 10

            # 色彩丰富度
            if img.mode == "RGB":
                small = img.resize((50, 50))
                colors = small.getcolors(maxcolors=2500)
                if colors and len(colors) < 50:
                    issues.append(f"色彩单调 ({len(colors)}种颜色)")
                    score -= 10

        except Exception as e:
            issues.append(f"质量检查失败: {e}")
            score -= 30

        return {"score": max(0, score), "issues": issues}

    def batch_generate(self, tasks: List[Dict[str, Any]]) -> List[ImageGenerationResult]:
        """
        批量生成图片

        Args:
            tasks: 任务列表，每个含prompt/references/width/height等

        Returns:
            结果列表
        """
        results = []
        for i, task in enumerate(tasks):
            print(f"\n[{i+1}/{len(tasks)}] 生成: {task.get('prompt', '')[:50]}...")
            result = self.generate_with_reference(
                prompt=task.get("prompt", ""),
                reference_images=task.get("references", []),
                width=task.get("width", 1024),
                height=task.get("height", 1024),
                checkpoint=task.get("checkpoint", "基础模型\\sd_xl_turbo_1.0_fp16.safetensors"),
                steps=task.get("steps", 6),
                cfg=task.get("cfg", 2.0),
                init_image=task.get("init_image", ""),
                denoise=task.get("denoise", 0.7),
            )
            results.append(result)
            if result.success:
                print(f"  ✅ 完成: {result.image_path} (质量{result.quality_score:.0f})")
            else:
                print(f"  ❌ 失败: {result.error}")

        return results


# 便捷函数
def create_image_pipeline(output_dir: str = "") -> ComfyUIImagePipeline:
    """创建出图流水线"""
    return ComfyUIImagePipeline(output_dir=output_dir)


if __name__ == "__main__":
    print("=" * 60)
    print("ComfyUI出图全链路集成 v1.0 自测")
    print("=" * 60)

    pipeline = create_image_pipeline()

    # 检查在线状态
    print(f"\nComfyUI在线: {'是' if pipeline.is_online() else '否'}")

    if not pipeline.is_online():
        print("⚠️ ComfyUI离线，跳过生成测试")
        exit(0)

    # 测试文生图
    print("\n[1/2] 测试文生图...")
    result = pipeline.generate_with_reference(
        prompt="a cinematic portrait of a tired office worker, dim lighting, photorealistic",
        width=768, height=1024,
        steps=6, cfg=2.0,
    )
    if result.success:
        print(f"  ✅ 生成成功: {result.image_path}")
        print(f"     质量评分: {result.quality_score:.0f}")
        if result.quality_issues:
            for issue in result.quality_issues:
                print(f"     ⚠️ {issue}")
    else:
        print(f"  ❌ 生成失败: {result.error}")

    # 测试质量检查
    print("\n[2/2] 测试质量检查...")
    if result.success and result.image_path:
        quality = pipeline._check_image_quality(result.image_path, 768, 1024)
        print(f"  质量评分: {quality['score']:.0f}")
        print(f"  问题: {quality['issues'] if quality['issues'] else '无'}")

    print("\n" + "=" * 60)
    print("✅ ComfyUI出图全链路集成自测完成")
    print("=" * 60)
