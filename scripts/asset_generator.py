# -*- coding: utf-8 -*-
"""
ComfyUI素材生成执行器 (Asset Generator)
支持：角色图/场景图/道具图生成，工作流模板管理，批量生成，素材评级入库

核心设计：
- AssetType枚举：character/scene/prop/effect
- StylePreset：风格预设（写实/卡通/3D/动漫/像素）
- AssetGenerator：主生成器，封装ComfyClient
- AssetLibrary：素材库管理（评级/分类/检索）
"""

import os
import json
import time
import uuid
from typing import Optional, Dict, List, Any, Literal
from enum import Enum
from dataclasses import dataclass, field, asdict

# 导入ComfyUI客户端
import sys
_COMFY_DIR = os.path.join(os.path.dirname(__file__), "..", "capabilities", "cap_comfyui_runner")
sys.path.insert(0, os.path.abspath(_COMFY_DIR))
from comfy_client import ComfyClient, load_workflow_template


# ============================================================
# 枚举与数据类
# ============================================================

class AssetType(Enum):
    """素材类型"""
    CHARACTER = "character"  # 角色图
    SCENE = "scene"          # 场景图
    PROP = "prop"            # 道具图
    EFFECT = "effect"        # 特效图
    BACKGROUND = "background"  # 背景图


class StylePreset(Enum):
    """风格预设"""
    REALISTIC = "realistic"      # 写实
    CARTOON = "cartoon"          # 卡通
    ANIME = "anime"              # 动漫
    STYLE_3D = "3d"              # 3D渲染
    PIXEL = "pixel"              # 像素风
    INK = "ink"                  # 水墨
    OIL = "oil"                  # 油画


@dataclass
class AssetRequest:
    """素材生成请求"""
    asset_type: AssetType
    prompt: str                    # 正向提示词
    negative_prompt: str = ""      # 负向提示词
    style: StylePreset = StylePreset.REALISTIC
    width: int = 1024
    height: int = 1024
    batch_size: int = 1
    steps: int = 20
    cfg: float = 7.0
    sampler: str = "euler_ancestral"
    scheduler: str = "normal"
    seed: int = -1                 # -1=随机
    checkpoint: str = ""           # 空=自动选择
    lora: str = ""                 # LoRA名称
    lora_strength: float = 0.8
    transparent_background: bool = False  # 透明背景（道具图）
    reference_image: str = ""      # 参考图路径（图生图）
    denoise: float = 0.75          # 图生图重绘幅度
    output_dir: str = ""           # 输出目录
    tags: List[str] = field(default_factory=list)  # 标签
    description: str = ""          # 描述


@dataclass
class AssetRecord:
    """素材记录（入库用）"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    asset_type: str = ""
    style: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    file_path: str = ""
    width: int = 0
    height: int = 0
    seed: int = -1
    checkpoint: str = ""
    rating: int = 0                # 1-5星评级
    tags: List[str] = field(default_factory=list)
    description: str = ""
    created_at: float = field(default_factory=time.time)
    used_count: int = 0            # 使用次数
    workflow_snapshot: Dict = field(default_factory=dict)  # 工作流快照


# ============================================================
# 风格→模型/提示词映射
# ============================================================

STYLE_CONFIG = {
    StylePreset.REALISTIC: {
        "checkpoint_keywords": ["majicmix", "cyberrealistic", "realistic", "dreamshaper"],
        "prompt_prefix": "photorealistic, masterpiece, best quality, ultra detailed, 8k, ",
        "negative_suffix": "cartoon, anime, drawing, painting, illustration, 3d render, ",
    },
    StylePreset.CARTOON: {
        "checkpoint_keywords": ["revAnimated", "toon", "cartoon", "dreamshaper"],
        "prompt_prefix": "cartoon style, flat colors, clean lines, vector art, ",
        "negative_suffix": "photorealistic, realistic, 3d, photo, ",
    },
    StylePreset.ANIME: {
        "checkpoint_keywords": ["anime", "anything", "nai", "ghost", "cosxl"],
        "prompt_prefix": "anime style, masterpiece, best quality, highly detailed, ",
        "negative_suffix": "photorealistic, realistic, 3d, photo, ",
    },
    StylePreset.STYLE_3D: {
        "checkpoint_keywords": ["revAnimated", "3d", "pixar", "disney"],
        "prompt_prefix": "3d render, pixar style, octane render, volumetric lighting, ",
        "negative_suffix": "photorealistic, 2d, flat, cartoon, ",
    },
    StylePreset.PIXEL: {
        "checkpoint_keywords": ["pixel", "dreamshaper"],
        "prompt_prefix": "pixel art, 16-bit, retro game style, ",
        "negative_suffix": "photorealistic, 3d, realistic, ",
    },
    StylePreset.INK: {
        "checkpoint_keywords": ["ink", "chinese", "dreamshaper"],
        "prompt_prefix": "chinese ink painting, sumi-e, brush strokes, minimalist, ",
        "negative_suffix": "photorealistic, 3d, colorful, ",
    },
    StylePreset.OIL: {
        "checkpoint_keywords": ["oil", "classical", "dreamshaper"],
        "prompt_prefix": "oil painting, impasto, rich textures, classical art, ",
        "negative_suffix": "photorealistic, 3d, anime, ",
    },
}

# 素材类型→默认尺寸
ASSET_DEFAULT_SIZE = {
    AssetType.CHARACTER: (768, 1024),    # 竖版角色
    AssetType.SCENE: (1280, 720),        # 横版场景
    AssetType.PROP: (512, 512),          # 方形道具
    AssetType.EFFECT: (512, 512),        # 方形特效
    AssetType.BACKGROUND: (1920, 1080),  # 全屏背景
}

# 素材类型→默认提示词前缀
ASSET_TYPE_PREFIX = {
    AssetType.CHARACTER: "full body portrait, character design, ",
    AssetType.SCENE: "wide shot, environment design, cinematic composition, ",
    AssetType.PROP: "single object, product photography, centered, ",
    AssetType.EFFECT: "special effect, particle effect, isolated, ",
    AssetType.BACKGROUND: "background, scenery, no people, ",
}


# ============================================================
# 素材生成器
# ============================================================

class AssetGenerator:
    """ComfyUI素材生成执行器"""

    def __init__(self, server_addr: str = "127.0.0.1:8188",
                 output_root: str = "",
                 library_path: str = ""):
        self.client = ComfyClient(server_addr)
        self.output_root = output_root or os.path.join(
            os.path.dirname(__file__), "..", "..", "generated_assets"
        )
        self.library_path = library_path or os.path.join(
            self.output_root, "asset_library.json"
        )
        self._checkpoints_cache = None
        self._object_info_cache = None

    def is_available(self) -> bool:
        """检查ComfyUI是否可用"""
        return self.client.is_running()

    def get_available_checkpoints(self) -> List[str]:
        """获取可用的checkpoint列表"""
        if self._checkpoints_cache is None:
            info = self.client.get_object_info("CheckpointLoaderSimple")
            self._checkpoints_cache = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        return self._checkpoints_cache

    def select_checkpoint(self, style: StylePreset, asset_type: AssetType) -> str:
        """根据风格和素材类型自动选择checkpoint"""
        available = self.get_available_checkpoints()
        config = STYLE_CONFIG.get(style, STYLE_CONFIG[StylePreset.REALISTIC])

        # 按关键词匹配
        for keyword in config["checkpoint_keywords"]:
            for ckpt in available:
                if keyword.lower() in ckpt.lower():
                    return ckpt

        # 默认返回第一个
        return available[0] if available else ""

    def build_text_to_image_workflow(self, req: AssetRequest) -> Dict:
        """构建文生图工作流"""
        checkpoint = req.checkpoint or self.select_checkpoint(req.style, req.asset_type)
        config = STYLE_CONFIG.get(req.style, STYLE_CONFIG[StylePreset.REALISTIC])

        # 组合提示词
        positive = ASSET_TYPE_PREFIX.get(req.asset_type, "") + config["prompt_prefix"] + req.prompt
        if req.transparent_background:
            positive += "transparent background, "
        negative = config["negative_suffix"] + req.negative_prompt
        if not req.transparent_background:
            negative += "text, watermark, signature, "

        # 默认尺寸
        if req.width == 1024 and req.height == 1024:
            default_w, default_h = ASSET_DEFAULT_SIZE.get(req.asset_type, (1024, 1024))
            width, height = default_w, default_h
        else:
            width, height = req.width, req.height

        seed = req.seed if req.seed >= 0 else int(time.time() * 1000) % (2**32)

        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint}
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": positive, "clip": ["1", 1]}
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative, "clip": ["1", 1]}
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": req.batch_size}
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": req.steps,
                    "cfg": req.cfg,
                    "sampler_name": req.sampler,
                    "scheduler": req.scheduler,
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0]
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": f"asset_{req.asset_type.value}", "images": ["6", 0]}
            }
        }

        # LoRA
        if req.lora:
            workflow["1"]["inputs"]["ckpt_name"] = checkpoint
            workflow["8"] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": req.lora,
                    "strength_model": req.lora_strength,
                    "strength_clip": req.lora_strength,
                    "model": ["1", 0],
                    "clip": ["1", 1]
                }
            }
            workflow["5"]["inputs"]["model"] = ["8", 0]
            workflow["2"]["inputs"]["clip"] = ["8", 1]
            workflow["3"]["inputs"]["clip"] = ["8", 1]

        return workflow, seed, positive, negative

    def build_image_to_image_workflow(self, req: AssetRequest) -> Dict:
        """构建图生图工作流"""
        if not req.reference_image:
            raise ValueError("图生图需要reference_image")

        checkpoint = req.checkpoint or self.select_checkpoint(req.style, req.asset_type)
        config = STYLE_CONFIG.get(req.style, STYLE_CONFIG[StylePreset.REALISTIC])

        positive = ASSET_TYPE_PREFIX.get(req.asset_type, "") + config["prompt_prefix"] + req.prompt
        negative = config["negative_suffix"] + req.negative_prompt
        seed = req.seed if req.seed >= 0 else int(time.time() * 1000) % (2**32)

        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint}
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": positive, "clip": ["1", 1]}
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative, "clip": ["1", 1]}
            },
            "4": {
                "class_type": "LoadImage",
                "inputs": {"image": os.path.basename(req.reference_image)}
            },
            "5": {
                "class_type": "VAEEncode",
                "inputs": {"pixels": ["4", 0], "vae": ["1", 2]}
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": req.steps,
                    "cfg": req.cfg,
                    "sampler_name": req.sampler,
                    "scheduler": req.scheduler,
                    "denoise": req.denoise,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["5", 0]
                }
            },
            "7": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["6", 0], "vae": ["1", 2]}
            },
            "8": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": f"asset_{req.asset_type.value}_i2i", "images": ["7", 0]}
            }
        }
        return workflow, seed, positive, negative

    def generate(self, req: AssetRequest) -> List[AssetRecord]:
        """
        生成素材

        Args:
            req: 素材生成请求

        Returns:
            生成的素材记录列表
        """
        if not self.is_available():
            raise RuntimeError("ComfyUI未运行")

        # 输出目录
        output_dir = req.output_dir or os.path.join(
            self.output_root, req.asset_type.value, req.style.value
        )
        os.makedirs(output_dir, exist_ok=True)

        # 构建工作流
        if req.reference_image:
            workflow, seed, positive, negative = self.build_image_to_image_workflow(req)
            input_images = {os.path.basename(req.reference_image): req.reference_image}
        else:
            workflow, seed, positive, negative = self.build_text_to_image_workflow(req)
            input_images = None

        print(f"  生成: {req.asset_type.value} / {req.style.value}")
        print(f"  提示词: {positive[:80]}...")
        print(f"  尺寸: {req.width}x{req.height}, steps={req.steps}, cfg={req.cfg}")

        # 执行
        saved_paths = self.client.run_workflow(
            workflow,
            input_images=input_images,
            output_dir=output_dir,
            timeout=600,
        )

        # 入库
        records = []
        for path in saved_paths:
            record = AssetRecord(
                asset_type=req.asset_type.value,
                style=req.style.value,
                prompt=positive,
                negative_prompt=negative,
                file_path=os.path.abspath(path),
                width=req.width,
                height=req.height,
                seed=seed,
                checkpoint=req.checkpoint or self.select_checkpoint(req.style, req.asset_type),
                tags=req.tags,
                description=req.description,
                workflow_snapshot=workflow,
            )
            records.append(record)
            self._save_to_library(record)
            print(f"  已入库: {record.id} -> {os.path.basename(path)}")

        return records

    def generate_batch(self, requests: List[AssetRequest]) -> List[AssetRecord]:
        """批量生成素材"""
        all_records = []
        for i, req in enumerate(requests):
            print(f"\n[{i+1}/{len(requests)}] ", end="")
            try:
                records = self.generate(req)
                all_records.extend(records)
            except Exception as e:
                print(f"  失败: {e}")
        return all_records

    # ============================================================
    # 素材库管理
    # ============================================================

    def _load_library(self) -> List[Dict]:
        """加载素材库"""
        if os.path.exists(self.library_path):
            with open(self.library_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_to_library(self, record: AssetRecord):
        """保存到素材库"""
        library = self._load_library()
        library.append(asdict(record))
        os.makedirs(os.path.dirname(self.library_path), exist_ok=True)
        with open(self.library_path, "w", encoding="utf-8") as f:
            json.dump(library, f, ensure_ascii=False, indent=2)

    def rate_asset(self, asset_id: str, rating: int):
        """给素材评级（1-5星）"""
        library = self._load_library()
        for item in library:
            if item["id"] == asset_id:
                item["rating"] = max(1, min(5, rating))
                with open(self.library_path, "w", encoding="utf-8") as f:
                    json.dump(library, f, ensure_ascii=False, indent=2)
                print(f"  已评级: {asset_id} -> {rating}星")
                return
        print(f"  未找到: {asset_id}")

    def search_assets(self, asset_type: str = "", style: str = "",
                      tags: List[str] = None, min_rating: int = 0,
                      keyword: str = "") -> List[Dict]:
        """检索素材库"""
        library = self._load_library()
        results = []
        for item in library:
            if asset_type and item["asset_type"] != asset_type:
                continue
            if style and item["style"] != style:
                continue
            if min_rating and item.get("rating", 0) < min_rating:
                continue
            if tags and not any(t in item.get("tags", []) for t in tags):
                continue
            if keyword and keyword.lower() not in item.get("prompt", "").lower() \
               and keyword.lower() not in item.get("description", "").lower():
                continue
            results.append(item)
        return results

    def get_library_stats(self) -> Dict:
        """获取素材库统计"""
        library = self._load_library()
        stats = {
            "total": len(library),
            "by_type": {},
            "by_style": {},
            "by_rating": {},
            "avg_rating": 0,
        }
        ratings = []
        for item in library:
            t = item["asset_type"]
            s = item["style"]
            r = item.get("rating", 0)
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
            stats["by_style"][s] = stats["by_style"].get(s, 0) + 1
            if r > 0:
                stats["by_rating"][str(r)] = stats["by_rating"].get(str(r), 0) + 1
                ratings.append(r)
        if ratings:
            stats["avg_rating"] = round(sum(ratings) / len(ratings), 2)
        return stats


# ============================================================
# 快捷生成函数
# ============================================================

def quick_character(prompt: str, style: StylePreset = StylePreset.REALISTIC,
                    **kwargs) -> AssetRequest:
    """快捷创建角色图请求"""
    return AssetRequest(
        asset_type=AssetType.CHARACTER,
        prompt=prompt,
        style=style,
        **kwargs
    )

def quick_scene(prompt: str, style: StylePreset = StylePreset.REALISTIC,
                **kwargs) -> AssetRequest:
    """快捷创建场景图请求"""
    return AssetRequest(
        asset_type=AssetType.SCENE,
        prompt=prompt,
        style=style,
        **kwargs
    )

def quick_prop(prompt: str, style: StylePreset = StylePreset.REALISTIC,
               **kwargs) -> AssetRequest:
    """快捷创建道具图请求（默认透明背景）"""
    return AssetRequest(
        asset_type=AssetType.PROP,
        prompt=prompt,
        style=style,
        transparent_background=True,
        **kwargs
    )


if __name__ == "__main__":
    print("=" * 60)
    print("ComfyUI素材生成执行器 v1.0")
    print("=" * 60)

    gen = AssetGenerator()
    print(f"ComfyUI可用: {gen.is_available()}")
    if gen.is_available():
        print(f"可用模型: {len(gen.get_available_checkpoints())}个")
        print(f"素材库统计: {gen.get_library_stats()}")

    print("\n支持的素材类型:", [t.value for t in AssetType])
    print("支持的风格:", [s.value for s in StylePreset])
