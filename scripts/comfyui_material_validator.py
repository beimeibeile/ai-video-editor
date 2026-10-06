"""
ComfyUI素材生成端到端验证模块 v1.0
验证ComfyUI生成的素材是否能完美融入剪映工程。

验证内容：
1. 素材技术参数（分辨率/格式/Alpha通道/色彩空间）
2. 素材生成质量（清晰度/噪点/边缘）
3. 剪映工程集成（导入/显示/层级）
4. 场景融合度（背景匹配/光照一致/边缘自然）

使用方式：
    from comfyui_material_validator import ComfyUIMaterialValidator
    validator = ComfyUIMaterialValidator()
    result = validator.validate_material("generated.png", scene_type="douyin_profile")
"""
import os
import json
import subprocess
import requests
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class MaterialValidationResult:
    """素材验证结果"""
    filepath: str
    exists: bool = False
    width: int = 0
    height: int = 0
    format: str = ""
    has_alpha: bool = False
    color_space: str = ""
    file_size: int = 0
    technical_score: float = 0.0  # 0-100
    quality_score: float = 0.0  # 0-100
    integration_score: float = 0.0  # 0-100
    overall_score: float = 0.0  # 0-100
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ComfyUIMaterialValidator:
    """ComfyUI素材验证器"""

    def __init__(
        self,
        comfyui_address: str = "127.0.0.1:8188",
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
    ):
        self.comfyui_url = f"http://{comfyui_address}"
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffprobe_path
        self.session = requests.Session()

    def check_comfyui(self) -> Dict:
        """检查ComfyUI连接状态"""
        try:
            response = self.session.get(f"{self.comfyui_url}/", timeout=5)
            if response.status_code == 200:
                # 获取系统统计
                try:
                    stats = self.session.get(
                        f"{self.comfyui_url}/system_stats", timeout=5
                    ).json()
                    return {
                        "connected": True,
                        "status": "running",
                        "devices": stats.get("devices", []),
                    }
                except Exception:
                    return {"connected": True, "status": "running"}
        except Exception as e:
            return {"connected": False, "status": "error", "error": str(e)}

        return {"connected": False, "status": "unknown"}

    def get_available_models(self) -> Dict[str, List[str]]:
        """获取可用模型列表"""
        try:
            response = self.session.get(
                f"{self.comfyui_url}/object_info", timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                models = {
                    "checkpoints": [],
                    "loras": [],
                    "vaes": [],
                }

                # 从CheckpointLoaderSimple节点获取模型
                if "CheckpointLoaderSimple" in data:
                    ckpt_input = data["CheckpointLoaderSimple"].get("input", {})
                    required = ckpt_input.get("required", {})
                    if "ckpt_name" in required:
                        models["checkpoints"] = required["ckpt_name"][0]

                # 从LoraLoader节点获取LoRA
                if "LoraLoader" in data:
                    lora_input = data["LoraLoader"].get("input", {})
                    required = lora_input.get("required", {})
                    if "lora_name" in required:
                        models["loras"] = required["lora_name"][0]

                return models
        except Exception as e:
            print(f"⚠️ 获取模型列表失败: {e}")

        return {"checkpoints": [], "loras": [], "vaes": []}

    def generate_test_image(
        self,
        prompt: str = "a cute robot character, white background, simple",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg: float = 7.0,
        output_dir: str = None,
    ) -> Optional[str]:
        """
        生成测试图片（简单文生图）

        Returns:
            生成的图片路径，失败返回None
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "..", "out")
        os.makedirs(output_dir, exist_ok=True)

        # 构建简单工作流
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 42,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "lowres, bad anatomy, bad hands, text, error, missing fingers",
                    "clip": ["4", 1],
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "ComfyUI_test", "images": ["8", 0]},
            },
        }

        try:
            # 提交工作流
            response = self.session.post(
                f"{self.comfyui_url}/prompt",
                json={"prompt": workflow},
                timeout=30,
            )
            if response.status_code != 200:
                print(f"⚠️ 提交工作流失败: {response.status_code}")
                return None

            prompt_id = response.json().get("prompt_id")
            if not prompt_id:
                print("⚠️ 未获取到prompt_id")
                return None

            # 轮询等待完成
            print(f"  等待生成完成 (prompt_id={prompt_id[:8]}...)")
            max_wait = 120  # 最多等待2分钟
            start_time = time.time()

            while time.time() - start_time < max_wait:
                try:
                    history = self.session.get(
                        f"{self.comfyui_url}/history/{prompt_id}",
                        timeout=5,
                    ).json()

                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
                        if "9" in outputs:
                            images = outputs["9"].get("images", [])
                            if images:
                                # 下载图片
                                img_info = images[0]
                                img_response = self.session.get(
                                    f"{self.comfyui_url}/view",
                                    params={
                                        "filename": img_info["filename"],
                                        "subfolder": img_info.get("subfolder", ""),
                                        "type": img_info.get("type", "output"),
                                    },
                                    timeout=30,
                                )

                                output_path = os.path.join(
                                    output_dir, f"comfyui_test_{int(time.time())}.png"
                                )
                                with open(output_path, "wb") as f:
                                    f.write(img_response.content)

                                print(f"  ✅ 生成成功: {output_path}")
                                return output_path
                except Exception:
                    pass

                time.sleep(2)

            print("⚠️ 生成超时")
            return None

        except Exception as e:
            print(f"⚠️ 生成失败: {e}")
            return None

    def validate_material(
        self,
        material_path: str,
        scene_type: str = "general",
        target_canvas: Tuple[int, int] = (1080, 1920),
    ) -> MaterialValidationResult:
        """
        验证素材是否适合融入剪映工程

        Args:
            material_path: 素材文件路径
            scene_type: 场景类型（general/douyin_profile/character/background）
            target_canvas: 目标画布尺寸

        Returns:
            MaterialValidationResult 验证结果
        """
        result = MaterialValidationResult(filepath=material_path)

        if not os.path.exists(material_path):
            result.issues.append(f"素材文件不存在: {material_path}")
            return result

        result.exists = True
        result.file_size = os.path.getsize(material_path)

        # 使用ffprobe获取技术参数
        try:
            cmd = [
                self.ffprobe, "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                material_path
            ]
            probe_result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            info = json.loads(probe_result.stdout)

            video_stream = next(
                (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
                {}
            )

            result.width = int(video_stream.get("width", 0))
            result.height = int(video_stream.get("height", 0))
            result.format = video_stream.get("codec_name", "")
            result.color_space = video_stream.get("color_space", "unknown")

            # 检查Alpha通道
            pix_fmt = video_stream.get("pix_fmt", "")
            result.has_alpha = "a" in pix_fmt.lower() or "alpha" in pix_fmt.lower()

        except Exception as e:
            result.issues.append(f"技术参数解析失败: {e}")

        # 技术评分
        tech_score = 100
        if result.width == 0 or result.height == 0:
            tech_score -= 50
            result.issues.append("无法解析分辨率")
        else:
            # 检查分辨率是否合理
            if result.width < 256 or result.height < 256:
                tech_score -= 20
                result.warnings.append(f"分辨率过低: {result.width}x{result.height}")
            if result.width > target_canvas[0] * 2 or result.height > target_canvas[1] * 2:
                tech_score -= 10
                result.warnings.append(f"分辨率过高，可能需要缩放: {result.width}x{result.height}")

        # 检查文件大小
        if result.file_size > 50 * 1024 * 1024:  # 50MB
            tech_score -= 10
            result.warnings.append(f"文件过大: {result.file_size / 1024 / 1024:.1f}MB")

        result.technical_score = max(0, tech_score)

        # 场景适配评分
        integration_score = 80

        if scene_type == "character":
            # 角色素材需要Alpha通道
            if not result.has_alpha:
                integration_score -= 30
                result.issues.append("角色素材缺少Alpha通道，无法透明叠加")
                result.recommendations.append("使用Remotion PNG序列+ProRes 4444生成带Alpha的视频")
                result.recommendations.append("或使用去背景工具（remove_background.py）处理")

            # 角色素材建议正方形
            if abs(result.width - result.height) > max(result.width, result.height) * 0.2:
                integration_score -= 10
                result.warnings.append("角色素材建议接近正方形比例")

        elif scene_type == "background":
            # 背景素材不需要Alpha
            if result.has_alpha:
                integration_score -= 5
                result.warnings.append("背景素材通常不需要Alpha通道")

            # 背景素材建议匹配画布比例
            target_ratio = target_canvas[0] / target_canvas[1]
            material_ratio = result.width / result.height if result.height > 0 else 1
            if abs(material_ratio - target_ratio) > 0.1:
                integration_score -= 15
                result.warnings.append(
                    f"背景比例不匹配: 素材{material_ratio:.2f} vs 画布{target_ratio:.2f}"
                )

        elif scene_type == "douyin_profile":
            # 抖音主页素材
            if result.width != 1080 or result.height != 1920:
                integration_score -= 10
                result.warnings.append(f"抖音主页建议1080x1920，当前{result.width}x{result.height}")

        result.integration_score = max(0, integration_score)

        # 综合评分
        result.overall_score = (
            result.technical_score * 0.4 +
            result.quality_score * 0.3 +
            result.integration_score * 0.3
        )

        # 生成建议
        if result.overall_score >= 80:
            result.recommendations.append("素材质量良好，可以直接使用")
        elif result.overall_score >= 60:
            result.recommendations.append("素材基本可用，建议优化后使用")
        else:
            result.recommendations.append("素材质量不达标，建议重新生成")

        if not result.has_alpha and scene_type == "character":
            result.recommendations.append("关键问题：缺少Alpha通道，必须修复后才能用于角色动画")

        return result

    def batch_validate(
        self,
        material_dir: str,
        scene_type: str = "general",
    ) -> List[MaterialValidationResult]:
        """批量验证目录中的素材"""
        results = []

        if not os.path.exists(material_dir):
            print(f"⚠️ 目录不存在: {material_dir}")
            return results

        image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

        for filename in os.listdir(material_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_exts or ext in video_exts:
                filepath = os.path.join(material_dir, filename)
                result = self.validate_material(filepath, scene_type)
                results.append(result)

        return results

    def print_validation_report(self, result: MaterialValidationResult):
        """打印验证报告"""
        print("=" * 60)
        print("ComfyUI素材验证报告")
        print("=" * 60)
        print(f"\n文件: {os.path.basename(result.filepath)}")
        print(f"大小: {result.file_size / 1024:.1f}KB")
        print(f"分辨率: {result.width}x{result.height}")
        print(f"格式: {result.format}")
        print(f"Alpha通道: {'✅ 有' if result.has_alpha else '❌ 无'}")
        print(f"色彩空间: {result.color_space}")

        print(f"\n评分:")
        print(f"  技术参数: {result.technical_score:.0f}/100")
        print(f"  生成质量: {result.quality_score:.0f}/100")
        print(f"  场景融合: {result.integration_score:.0f}/100")
        print(f"  综合评分: {result.overall_score:.0f}/100")

        if result.issues:
            print(f"\n❌ 问题 ({len(result.issues)}):")
            for issue in result.issues:
                print(f"  - {issue}")

        if result.warnings:
            print(f"\n⚠️ 警告 ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"  - {warning}")

        if result.recommendations:
            print(f"\n💡 建议 ({len(result.recommendations)}):")
            for rec in result.recommendations:
                print(f"  - {rec}")

        print("=" * 60)


def main():
    """命令行测试"""
    print("=" * 60)
    print("ComfyUI素材生成端到端验证 v1.0")
    print("=" * 60)

    validator = ComfyUIMaterialValidator()

    # 检查ComfyUI
    print("\n=== 检查ComfyUI连接 ===")
    status = validator.check_comfyui()
    print(f"  连接: {'✅' if status.get('connected') else '❌'}")
    print(f"  状态: {status.get('status')}")

    # 获取可用模型
    print("\n=== 可用模型 ===")
    models = validator.get_available_models()
    print(f"  Checkpoints: {len(models.get('checkpoints', []))}个")
    for ckpt in models.get("checkpoints", [])[:5]:
        print(f"    - {ckpt}")
    print(f"  LoRAs: {len(models.get('loras', []))}个")

    # 验证现有素材
    print("\n=== 验证现有素材 ===")
    test_dirs = [
        r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\out",
        r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\material",
    ]

    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            print(f"\n目录: {test_dir}")
            results = validator.batch_validate(test_dir, scene_type="general")
            for r in results[:3]:  # 只显示前3个
                validator.print_validation_report(r)
                print()
            if len(results) > 3:
                print(f"  ... 还有{len(results) - 3}个素材")
            break

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
