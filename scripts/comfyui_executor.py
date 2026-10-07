"""
ComfyUI素材生成执行器
基于ComfyUI API生成角色图、场景图、道具图等素材

支持：
- 角色图生成（character）
- 场景图生成（scene）
- 道具图生成（prop）
- 批量生成

使用Qwen-Image模型（FP8量化，RTX 3080 12GB可跑）
"""
import os
import sys
import json
import copy
import time
from typing import Optional, Dict, List, Any

# 添加cap_comfyui_runner到路径
CAP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "capabilities", "cap_comfyui_runner")
if os.path.exists(CAP_DIR):
    sys.path.insert(0, CAP_DIR)

from comfy_client import ComfyClient


# 素材类型配置
ASSET_CONFIGS = {
    "character": {
        "width": 768,
        "height": 1024,
        "prefix": "char_",
        "default_negative": "low quality, blurry, distorted, deformed, bad anatomy, extra limbs, missing limbs, watermark, text, signature",
        "style_prefix": "portrait of ",
    },
    "scene": {
        "width": 1280,
        "height": 720,
        "prefix": "scene_",
        "default_negative": "low quality, blurry, distorted, deformed, watermark, text, signature, people, characters",
        "style_prefix": "background scene, ",
    },
    "prop": {
        "width": 512,
        "height": 512,
        "prefix": "prop_",
        "default_negative": "low quality, blurry, distorted, deformed, watermark, text, signature, background, scene",
        "style_prefix": "single object, product photo, white background, ",
    },
}


class ComfyUIAssetExecutor:
    """ComfyUI素材生成执行器"""

    def __init__(self, work_dir: str = None, server_addr: str = "127.0.0.1:8188"):
        """
        初始化执行器

        Args:
            work_dir: 工作目录（输出素材保存位置）
            server_addr: ComfyUI服务器地址
        """
        self.work_dir = work_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "director_engine_output", "assets")
        os.makedirs(self.work_dir, exist_ok=True)

        self.client = ComfyClient(server_addr=server_addr)
        self.workflow_template_path = os.path.join(CAP_DIR, "workflow_templates", "qwen_txt2img.json")

        # 加载工作流模板
        with open(self.workflow_template_path, "r", encoding="utf-8") as f:
            self.workflow_template = json.load(f)

    def is_available(self) -> bool:
        """检查ComfyUI是否可用"""
        return self.client.is_running()

    def generate_asset(
        self,
        description: str,
        asset_type: str = "character",
        name: str = None,
        negative_prompt: str = None,
        width: int = None,
        height: int = None,
        seed: int = None,
        steps: int = 30,
        cfg: float = 4.0,
    ) -> Dict[str, Any]:
        """
        生成单个素材

        Args:
            description: 素材描述（自然语言）
            asset_type: 素材类型（character/scene/prop）
            name: 素材名称（用于文件名）
            negative_prompt: 负面提示词（默认使用类型预设）
            width: 宽度（默认使用类型预设）
            height: 高度（默认使用类型预设）
            seed: 随机种子（默认随机）
            steps: 采样步数（默认30）
            cfg: CFG scale（默认4.0）

        Returns:
            {
                "success": bool,
                "asset_type": str,
                "name": str,
                "description": str,
                "output_path": str,
                "width": int,
                "height": int,
                "seed": int,
                "duration": float,
                "error": str (仅失败时)
            }
        """
        start_time = time.time()

        # 获取类型配置
        config = ASSET_CONFIGS.get(asset_type, ASSET_CONFIGS["character"])
        name = name or f"{asset_type}_{int(time.time())}"
        width = width or config["width"]
        height = height or config["height"]
        negative_prompt = negative_prompt or config["default_negative"]
        seed = seed if seed is not None else int(time.time() * 1000) % (2**32)

        # 构建提示词
        positive_prompt = f"{config['style_prefix']}{description}, high quality, detailed, masterpiece"

        print(f"\n[ComfyUI] 生成{asset_type}素材: {name}")
        print(f"  描述: {description[:50]}...")
        print(f"  尺寸: {width}x{height}, 步数: {steps}, seed: {seed}")

        try:
            # 检查ComfyUI是否运行
            if not self.is_available():
                raise Exception("ComfyUI未运行")

            # 构建工作流
            workflow = copy.deepcopy(self.workflow_template)

            # 替换提示词
            workflow["8"]["inputs"]["text"] = positive_prompt
            workflow["9"]["inputs"]["text"] = negative_prompt

            # 设置尺寸
            workflow["7"]["inputs"]["width"] = width
            workflow["7"]["inputs"]["height"] = height

            # 设置采样参数
            workflow["11"]["inputs"]["seed"] = seed
            workflow["11"]["inputs"]["steps"] = steps
            workflow["11"]["inputs"]["cfg"] = cfg

            # 设置输出文件名前缀
            workflow["13"]["inputs"]["filename_prefix"] = f"{config['prefix']}{name}"

            # 执行工作流
            output_files = self.client.run_workflow(
                workflow=workflow,
                output_dir=self.work_dir,
                timeout=600,
            )

            if not output_files:
                raise Exception("未生成输出文件")

            output_path = output_files[0]
            duration = time.time() - start_time

            print(f"  ✅ 生成成功: {os.path.basename(output_path)}")
            print(f"  耗时: {duration:.1f}s")

            return {
                "success": True,
                "asset_type": asset_type,
                "name": name,
                "description": description,
                "output_path": output_path,
                "width": width,
                "height": height,
                "seed": seed,
                "duration": duration,
            }

        except Exception as e:
            duration = time.time() - start_time
            print(f"  ❌ 生成失败: {e}")
            return {
                "success": False,
                "asset_type": asset_type,
                "name": name,
                "description": description,
                "output_path": None,
                "width": width,
                "height": height,
                "seed": seed,
                "duration": duration,
                "error": str(e),
            }

    def generate_character(
        self,
        name: str,
        description: str,
        appearance: str = "",
        clothing: str = "",
        expression: str = "neutral",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        生成角色图

        Args:
            name: 角色名称
            description: 角色描述
            appearance: 外貌特征
            clothing: 服装
            expression: 表情
            **kwargs: 其他参数传给generate_asset

        Returns:
            同generate_asset
        """
        full_desc = description
        if appearance:
            full_desc += f", {appearance}"
        if clothing:
            full_desc += f", wearing {clothing}"
        if expression and expression != "neutral":
            full_desc += f", {expression} expression"

        return self.generate_asset(
            description=full_desc,
            asset_type="character",
            name=name,
            **kwargs,
        )

    def generate_scene(
        self,
        name: str,
        description: str,
        time_of_day: str = "",
        atmosphere: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        生成场景图

        Args:
            name: 场景名称
            description: 场景描述
            time_of_day: 时间（day/night/sunset等）
            atmosphere: 氛围
            **kwargs: 其他参数传给generate_asset

        Returns:
            同generate_asset
        """
        full_desc = description
        if time_of_day:
            full_desc += f", {time_of_day}"
        if atmosphere:
            full_desc += f", {atmosphere} atmosphere"

        return self.generate_asset(
            description=full_desc,
            asset_type="scene",
            name=name,
            **kwargs,
        )

    def generate_prop(
        self,
        name: str,
        description: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        生成道具图

        Args:
            name: 道具名称
            description: 道具描述
            **kwargs: 其他参数传给generate_asset

        Returns:
            同generate_asset
        """
        return self.generate_asset(
            description=description,
            asset_type="prop",
            name=name,
            **kwargs,
        )

    def generate_batch(
        self,
        assets: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        批量生成素材

        Args:
            assets: 素材列表，每个元素包含type/name/description等字段

        Returns:
            生成结果列表
        """
        results = []
        for i, asset in enumerate(assets):
            print(f"\n[{i+1}/{len(assets)}] 批量生成进度")
            asset_type = asset.get("type", "character")
            name = asset.get("name", f"{asset_type}_{i}")
            description = asset.get("description", "")

            if asset_type == "character":
                result = self.generate_character(name=name, description=description, **{k: v for k, v in asset.items() if k not in ["type", "name", "description"]})
            elif asset_type == "scene":
                result = self.generate_scene(name=name, description=description, **{k: v for k, v in asset.items() if k not in ["type", "name", "description"]})
            else:
                result = self.generate_prop(name=name, description=description, **{k: v for k, v in asset.items() if k not in ["type", "name", "description"]})

            results.append(result)

        # 汇总
        success_count = sum(1 for r in results if r["success"])
        print(f"\n[ComfyUI] 批量生成完成: {success_count}/{len(results)} 成功")

        return results


if __name__ == "__main__":
    # 测试
    executor = ComfyUIAssetExecutor()
    print(f"ComfyUI可用: {executor.is_available()}")

    if executor.is_available():
        # 测试生成角色图（低分辨率快速测试）
        result = executor.generate_character(
            name="test_character",
            description="a young woman with short brown hair",
            width=512,
            height=512,
            steps=10,
        )
        print(f"\n测试结果: {result['success']}")
        if result["success"]:
            print(f"输出: {result['output_path']}")
