"""
角色画面生成器 v1.0
根据角色设定自动生成ComfyUI提示词，生成角色特写/半身/全身+表情变体

核心能力：
1. 角色设定→英文提示词（外貌/服装/年龄/气质）
2. 三种画幅：特写(脸)/半身(胸像)/全身
3. 表情变体：平静/开心/悲伤/愤怒/惊讶/思考
4. 角色一致性：固定seed+特征描述
5. 批量生成+缓存管理
"""
import os
import json
import time
import requests
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ShotFraming(Enum):
    """角色画幅"""
    CLOSEUP = "特写"       # 脸部特写
    MEDIUM = "半身"        # 胸像/半身
    FULL = "全身"          # 全身


class Expression(Enum):
    """表情"""
    NEUTRAL = "平静"
    HAPPY = "开心"
    SAD = "悲伤"
    ANGRY = "愤怒"
    SURPRISED = "惊讶"
    THINKING = "思考"
    DETERMINED = "坚定"
    SHOCKED = "震惊"


# 表情→英文提示词
EXPRESSION_PROMPT = {
    Expression.NEUTRAL: "neutral expression, calm face",
    Expression.HAPPY: "smiling, happy expression, warm eyes",
    Expression.SAD: "sad expression, teary eyes, downcast",
    Expression.ANGRY: "angry expression, furrowed brows, clenched jaw",
    Expression.SURPRISED: "surprised expression, wide eyes, open mouth",
    Expression.THINKING: "thoughtful expression, looking away, pensive",
    Expression.DETERMINED: "determined expression, firm gaze, confident",
    Expression.SHOCKED: "shocked expression, disbelief, wide eyes",
}

# 画幅→英文提示词
FRAMING_PROMPT = {
    ShotFraming.CLOSEUP: "close-up shot, face portrait, detailed facial features",
    ShotFraming.MEDIUM: "medium shot, upper body portrait, chest up",
    ShotFraming.FULL: "full body shot, entire figure visible",
}


@dataclass
class CharacterVisualSpec:
    """角色视觉设定"""
    name: str
    age: int = 30
    gender: str = "male"  # male/female
    appearance: str = ""  # 外貌描述（中文）
    clothing: str = ""    # 服装描述
    hairstyle: str = ""   # 发型
    accessories: str = ""  # 配饰（眼镜等）
    aura: str = ""         # 气质
    base_seed: int = 42   # 基础seed（保证一致性）


@dataclass
class CharacterImage:
    """生成的角色图片"""
    character_name: str
    framing: str
    expression: str
    path: str
    prompt: str
    seed: int
    width: int
    height: int


class CharacterVisualGenerator:
    """角色画面生成器"""

    def __init__(self, comfy_url: str = "http://127.0.0.1:8188",
                 output_dir: str = None,
                 checkpoint: str = "基础模型\\sd_xl_turbo_1.0_fp16.safetensors"):
        self.comfy_url = comfy_url
        self.checkpoint = checkpoint
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "character_assets"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self.cache = {}  # (name, framing, expression) -> path

    def _build_prompt(self, spec: CharacterVisualSpec, framing: ShotFraming,
                      expression: Expression, background: str = "") -> str:
        """
        构建ComfyUI英文提示词

        Args:
            spec: 角色设定
            framing: 画幅
            expression: 表情
            background: 背景描述

        Returns:
            英文提示词
        """
        parts = []

        # 画幅
        parts.append(FRAMING_PROMPT[framing])

        # 性别+年龄
        gender_word = "man" if spec.gender == "male" else "woman"
        parts.append(f"a {spec.age} year old {gender_word}")

        # 外貌（简单翻译关键词）
        if spec.appearance:
            # 中文外貌关键词→英文
            appearance_map = {
                "瘦": "thin", "胖": "chubby", "高": "tall", "矮": "short",
                "英俊": "handsome", "漂亮": "beautiful", "普通": "average looking",
                "颓废": "haggard", "精神": "energetic", "戴眼镜": "wearing glasses",
                "黑框眼镜": "wearing black-rimmed glasses",
                "胡子": "with beard", "短发": "short hair", "长发": "long hair",
                "黑发": "black hair", "白发": "gray hair",
            }
            for cn, en in appearance_map.items():
                if cn in spec.appearance:
                    parts.append(en)

        # 发型
        if spec.hairstyle:
            parts.append(spec.hairstyle)

        # 服装
        if spec.clothing:
            clothing_map = {
                "西装": "wearing business suit", "衬衫": "wearing shirt",
                "格子衬衫": "wearing plaid shirt", "T恤": "wearing t-shirt",
                "休闲": "casual clothing", "正式": "formal clothing",
                "大腹便便": "portly build",
            }
            for cn, en in clothing_map.items():
                if cn in spec.clothing:
                    parts.append(en)

        # 配饰
        if spec.accessories:
            parts.append(spec.accessories)

        # 表情
        parts.append(EXPRESSION_PROMPT[expression])

        # 气质
        if spec.aura:
            aura_map = {
                "内向": "introverted aura", "敏感": "sensitive look",
                "傲慢": "arrogant expression", "自信": "confident demeanor",
                "疲惫": "tired look", "有韧性": "resilient look",
            }
            for cn, en in aura_map.items():
                if cn in spec.aura:
                    parts.append(en)

        # 背景
        if background:
            parts.append(f"{background} background")
        else:
            parts.append("simple background")

        # 画质增强
        parts.append("photorealistic, high detail, cinematic lighting, 8k")

        return ", ".join(parts)

    def _comfy_generate(self, prompt: str, output_path: str,
                        width: int = 1024, height: int = 1024,
                        seed: int = 42, steps: int = 6, cfg: float = 2.0) -> Optional[str]:
        """调用ComfyUI生成图片"""
        workflow = {
            "3": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                "latent_image": ["5", 0]}},
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": self.checkpoint}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {
                "text": "blurry, low quality, distorted, ugly, watermark, text, extra fingers, deformed",
                "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "char", "images": ["8", 0]}},
        }

        try:
            r = requests.post(f"{self.comfy_url}/prompt", json={"prompt": workflow}, timeout=10)
            if r.status_code != 200:
                return None
            prompt_id = r.json()["prompt_id"]

            for _ in range(60):
                time.sleep(2)
                hist = requests.get(f"{self.comfy_url}/history/{prompt_id}", timeout=5).json()
                if prompt_id in hist:
                    outputs = hist[prompt_id].get("outputs", {})
                    if "9" in outputs:
                        img_info = outputs["9"]["images"][0]
                        img_filename = img_info["filename"]
                        img_subfolder = img_info.get("subfolder", "")
                        img_url = f"{self.comfy_url}/view?filename={img_filename}&subfolder={img_subfolder}&type=output"
                        img_data = requests.get(img_url, timeout=10).content
                        with open(output_path, "wb") as f:
                            f.write(img_data)
                        return output_path
            return None
        except Exception as e:
            print(f"  ComfyUI生成失败: {e}")
            return None

    def generate_character(self, spec: CharacterVisualSpec,
                           framing: ShotFraming = ShotFraming.MEDIUM,
                           expression: Expression = Expression.NEUTRAL,
                           background: str = "",
                           force_regenerate: bool = False) -> CharacterImage:
        """
        生成单张角色图片

        Args:
            spec: 角色设定
            framing: 画幅
            expression: 表情
            background: 背景描述
            force_regenerate: 是否强制重新生成

        Returns:
            CharacterImage
        """
        cache_key = (spec.name, framing.value, expression.value, background)
        if cache_key in self.cache and not force_regenerate:
            cached_path = self.cache[cache_key]
            if os.path.exists(cached_path):
                return CharacterImage(
                    character_name=spec.name, framing=framing.value,
                    expression=expression.value, path=cached_path,
                    prompt="(cached)", seed=spec.base_seed, width=1024, height=1024,
                )

        # 画幅决定尺寸
        if framing == ShotFraming.CLOSEUP:
            width, height = 768, 1024  # 竖版特写
        elif framing == ShotFraming.MEDIUM:
            width, height = 896, 1152  # 竖版半身
        else:
            width, height = 832, 1216  # 竖版全身

        prompt = self._build_prompt(spec, framing, expression, background)
        seed = spec.base_seed + hash(framing.value + expression.value) % 10000

        # 文件名
        safe_name = spec.name.replace(" ", "_")
        filename = f"{safe_name}_{framing.value}_{expression.value}.png"
        output_path = os.path.join(self.output_dir, filename)

        if os.path.exists(output_path) and not force_regenerate:
            self.cache[cache_key] = output_path
            return CharacterImage(
                character_name=spec.name, framing=framing.value,
                expression=expression.value, path=output_path,
                prompt=prompt, seed=seed, width=width, height=height,
            )

        print(f"  生成角色图: {spec.name} [{framing.value}/{expression.value}]")
        result = self._comfy_generate(prompt, output_path, width, height, seed)

        if result:
            self.cache[cache_key] = output_path
            return CharacterImage(
                character_name=spec.name, framing=framing.value,
                expression=expression.value, path=output_path,
                prompt=prompt, seed=seed, width=width, height=height,
            )
        else:
            # 生成失败，返回占位
            return CharacterImage(
                character_name=spec.name, framing=framing.value,
                expression=expression.value, path="",
                prompt=prompt, seed=seed, width=width, height=height,
            )

    def generate_character_set(self, spec: CharacterVisualSpec,
                                framings: List[ShotFraming] = None,
                                expressions: List[Expression] = None,
                                background: str = "") -> List[CharacterImage]:
        """
        批量生成角色图片集

        Args:
            spec: 角色设定
            framings: 画幅列表（默认特写+半身）
            expressions: 表情列表（默认平静+开心+悲伤+坚定）
            background: 背景描述

        Returns:
            CharacterImage列表
        """
        if framings is None:
            framings = [ShotFraming.CLOSEUP, ShotFraming.MEDIUM]
        if expressions is None:
            expressions = [Expression.NEUTRAL, Expression.HAPPY,
                          Expression.SAD, Expression.DETERMINED]

        results = []
        for framing in framings:
            for expression in expressions:
                img = self.generate_character(spec, framing, expression, background)
                results.append(img)

        return results

    def get_character_image_for_emotion(self, spec: CharacterVisualSpec,
                                          emotion: str,
                                          framing: ShotFraming = ShotFraming.CLOSEUP,
                                          background: str = "") -> CharacterImage:
        """
        根据情绪自动选择表情并生成角色图

        Args:
            spec: 角色设定
            emotion: 情绪（中文：平静/开心/悲伤/愤怒/惊讶/思考/坚定/震惊）
            framing: 画幅
            background: 背景

        Returns:
            CharacterImage
        """
        emotion_map = {
            "平静": Expression.NEUTRAL,
            "开心": Expression.HAPPY,
            "快乐": Expression.HAPPY,
            "悲伤": Expression.SAD,
            "难过": Expression.SAD,
            "愤怒": Expression.ANGRY,
            "生气": Expression.ANGRY,
            "惊讶": Expression.SURPRISED,
            "震惊": Expression.SHOCKED,
            "思考": Expression.THINKING,
            "坚定": Expression.DETERMINED,
            "紧张": Expression.THINKING,
            "焦虑": Expression.THINKING,
            "冲突": Expression.ANGRY,
            "高潮": Expression.SHOCKED,
            "释然": Expression.HAPPY,
        }
        expression = emotion_map.get(emotion, Expression.NEUTRAL)
        return self.generate_character(spec, framing, expression, background)


if __name__ == "__main__":
    print("=" * 60)
    print("角色画面生成器 v1.0")
    print("=" * 60)

    generator = CharacterVisualGenerator()

    # 测试：陈默
    chenmo = CharacterVisualSpec(
        name="陈默", age=28, gender="male",
        appearance="瘦, 戴黑框眼镜, 短发, 黑发, 颓废",
        clothing="格子衬衫",
        hairstyle="short black hair",
        accessories="black-rimmed glasses",
        aura="内向, 敏感, 有韧性",
        base_seed=1001,
    )

    print("\n生成陈默角色图（特写，4种表情）:")
    images = generator.generate_character_set(
        chenmo,
        framings=[ShotFraming.CLOSEUP],
        expressions=[Expression.NEUTRAL, Expression.SAD,
                     Expression.SURPRISED, Expression.DETERMINED],
    )

    for img in images:
        status = "✅" if img.path else "❌"
        print(f"  {status} {img.character_name} [{img.framing}/{img.expression}]: {img.path}")

    print("\n提示词示例:")
    test_prompt = generator._build_prompt(chenmo, ShotFraming.CLOSEUP, Expression.DETERMINED)
    print(f"  {test_prompt}")
