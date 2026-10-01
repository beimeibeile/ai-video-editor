"""
角色+场景合成图生成器 v1.0
将角色图叠加在场景图上，带光照匹配和边缘融合

功能：
1. 角色图叠加到场景图的指定位置（左/中/右，上/中/下）
2. 光照匹配：根据场景图的平均亮度/色温调整角色图
3. 边缘融合：羽化边缘，避免硬边
4. 支持多角色合成
5. 输出合成后的图片，可用于ComfyUI图生视频的参考图
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


@dataclass
class CharacterPlacement:
    """角色放置配置"""
    char_image_path: str
    position_x: float = 0.5      # 水平位置（0-1，0=左，0.5=中，1=右）
    position_y: float = 0.7      # 垂直位置（0-1，0=上，0.5=中，1=下）
    scale: float = 0.4           # 角色大小比例（相对场景图宽度）
    feather: float = 0.05        # 边缘羽化比例（0-0.2）
    brightness_adjust: float = 0.0  # 亮度调整（-1到1，0=自动匹配）
    contrast_adjust: float = 0.0    # 对比度调整（-1到1，0=自动匹配）
    color_temperature: float = 0.0  # 色温调整（-1到1，-1=冷，1=暖，0=自动）


class CharacterSceneComposer:
    """角色+场景合成图生成器"""

    def __init__(self):
        if not _PIL_AVAILABLE:
            raise ImportError("Pillow未安装，无法使用合成图生成器")

    def _get_average_brightness(self, img: Image.Image) -> float:
        """获取图片平均亮度（0-255）"""
        gray = img.convert("L")
        histogram = gray.histogram()
        total = sum(histogram)
        if total == 0:
            return 128
        brightness = sum(i * w for i, w in enumerate(histogram)) / total
        return brightness

    def _get_average_color(self, img: Image.Image) -> Tuple[float, float, float]:
        """获取图片平均颜色（RGB，0-255）"""
        small = img.resize((50, 50))
        pixels = list(small.getdata())
        if not pixels:
            return (128, 128, 128)
        r = sum(p[0] for p in pixels) / len(pixels)
        g = sum(p[1] for p in pixels) / len(pixels)
        b = sum(p[2] for p in pixels) / len(pixels)
        return (r, g, b)

    def _match_lighting(self, char_img: Image.Image,
                          scene_img: Image.Image,
                          placement: CharacterPlacement) -> Image.Image:
        """
        匹配角色图和场景图的光照

        Args:
            char_img: 角色图（RGBA）
            scene_img: 场景图（RGB）
            placement: 放置配置

        Returns:
            光照匹配后的角色图
        """
        # 获取场景图和角色图的平均亮度
        scene_brightness = self._get_average_brightness(scene_img)
        char_brightness = self._get_average_brightness(char_img.convert("RGB"))

        # 自动亮度匹配
        if placement.brightness_adjust == 0.0:
            brightness_factor = scene_brightness / max(char_brightness, 1)
            brightness_factor = max(0.5, min(1.5, brightness_factor))
        else:
            brightness_factor = 1.0 + placement.brightness_adjust

        # 自动对比度匹配
        if placement.contrast_adjust == 0.0:
            # 简单的对比度匹配
            contrast_factor = 1.0
        else:
            contrast_factor = 1.0 + placement.contrast_adjust

        # 应用亮度和对比度
        result = char_img.copy()
        if brightness_factor != 1.0:
            enhancer = ImageEnhance.Brightness(result)
            result = enhancer.enhance(brightness_factor)

        if contrast_factor != 1.0:
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(contrast_factor)

        # 色温匹配
        if placement.color_temperature == 0.0:
            scene_color = self._get_average_color(scene_img)
            char_color = self._get_average_color(char_img.convert("RGB"))
            # 简单的色温调整：如果场景偏暖，角色也偏暖
            scene_warmth = (scene_color[0] - scene_color[2]) / 255
            char_warmth = (char_color[0] - char_color[2]) / 255
            warmth_diff = scene_warmth - char_warmth
            if abs(warmth_diff) > 0.05:
                # 应用色温调整
                r, g, b, a = result.split()
                if warmth_diff > 0:
                    # 场景偏暖，角色增加红，减少蓝
                    r = r.point(lambda x: min(255, int(x * (1 + warmth_diff * 0.3))))
                    b = b.point(lambda x: max(0, int(x * (1 - warmth_diff * 0.3))))
                else:
                    # 场景偏冷，角色增加蓝，减少红
                    r = r.point(lambda x: max(0, int(x * (1 + warmth_diff * 0.3))))
                    b = b.point(lambda x: min(255, int(x * (1 - warmth_diff * 0.3))))
                result = Image.merge("RGBA", (r, g, b, a))
        else:
            # 手动色温调整
            r, g, b, a = result.split()
            if placement.color_temperature > 0:
                r = r.point(lambda x: min(255, int(x * (1 + placement.color_temperature * 0.3))))
                b = b.point(lambda x: max(0, int(x * (1 - placement.color_temperature * 0.3))))
            else:
                r = r.point(lambda x: max(0, int(x * (1 + placement.color_temperature * 0.3))))
                b = b.point(lambda x: min(255, int(x * (1 - placement.color_temperature * 0.3))))
            result = Image.merge("RGBA", (r, g, b, a))

        return result

    def _apply_feather(self, img: Image.Image, feather_ratio: float = 0.05) -> Image.Image:
        """
        应用边缘羽化

        Args:
            img: 图片（RGBA）
            feather_ratio: 羽化比例（0-0.2）

        Returns:
            羽化后的图片
        """
        if feather_ratio <= 0:
            return img

        # 获取alpha通道
        r, g, b, a = img.split()

        # 对alpha通道进行高斯模糊实现羽化
        feather_pixels = max(1, int(min(img.size) * feather_ratio))
        a_blurred = a.filter(ImageFilter.GaussianBlur(radius=feather_pixels))

        return Image.merge("RGBA", (r, g, b, a_blurred))

    def compose(self, scene_image_path: str,
                character_placements: List[CharacterPlacement],
                output_path: str = "") -> Image.Image:
        """
        合成角色+场景图

        Args:
            scene_image_path: 场景图路径
            character_placements: 角色放置配置列表
            output_path: 输出路径（可选）

        Returns:
            合成后的图片
        """
        # 打开场景图
        scene_img = Image.open(scene_image_path).convert("RGBA")
        scene_w, scene_h = scene_img.size

        # 创建结果图
        result = scene_img.copy()

        # 逐个合成角色
        for placement in character_placements:
            # 打开角色图
            char_img = Image.open(placement.char_image_path).convert("RGBA")

            # 调整角色大小
            target_w = int(scene_w * placement.scale)
            char_ratio = char_img.height / char_img.width
            target_h = int(target_w * char_ratio)
            char_img = char_img.resize((target_w, target_h), Image.LANCZOS)

            # 光照匹配
            char_img = self._match_lighting(char_img, scene_img, placement)

            # 边缘羽化
            char_img = self._apply_feather(char_img, placement.feather)

            # 计算位置
            pos_x = int(scene_w * placement.position_x - target_w / 2)
            pos_y = int(scene_h * placement.position_y - target_h / 2)

            # 确保位置在画布内
            pos_x = max(0, min(scene_w - target_w, pos_x))
            pos_y = max(0, min(scene_h - target_h, pos_y))

            # 粘贴角色图
            result.paste(char_img, (pos_x, pos_y), char_img)

        # 保存
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            result.convert("RGB").save(output_path, "PNG")

        return result

    def compose_from_dict(self, config: Dict[str, Any], output_path: str = "") -> Image.Image:
        """
        从字典配置合成

        Args:
            config: 配置字典，含scene_image_path和characters列表
            output_path: 输出路径

        Returns:
            合成后的图片
        """
        scene_path = config.get("scene_image_path", "")
        characters = config.get("characters", [])

        placements = []
        for char in characters:
            placements.append(CharacterPlacement(
                char_image_path=char.get("path", ""),
                position_x=char.get("position_x", 0.5),
                position_y=char.get("position_y", 0.7),
                scale=char.get("scale", 0.4),
                feather=char.get("feather", 0.05),
                brightness_adjust=char.get("brightness", 0.0),
                contrast_adjust=char.get("contrast", 0.0),
                color_temperature=char.get("color_temperature", 0.0),
            ))

        return self.compose(scene_path, placements, output_path)


# 便捷函数
def create_composer() -> CharacterSceneComposer:
    """创建合成器"""
    return CharacterSceneComposer()


def compose_character_scene(scene_path: str,
                              char_paths: List[str],
                              output_path: str = "",
                              positions: List[Tuple[float, float]] = None,
                              scales: List[float] = None) -> Image.Image:
    """
    便捷函数：快速合成角色+场景图

    Args:
        scene_path: 场景图路径
        char_paths: 角色图路径列表
        output_path: 输出路径
        positions: 角色位置列表 [(x, y), ...]
        scales: 角色大小比例列表

    Returns:
        合成后的图片
    """
    composer = create_composer()

    if positions is None:
        # 默认位置：从左到右排列
        n = len(char_paths)
        positions = [(0.2 + 0.6 * i / max(n - 1, 1), 0.7) for i in range(n)]

    if scales is None:
        scales = [0.4] * len(char_paths)

    placements = []
    for i, char_path in enumerate(char_paths):
        x, y = positions[i] if i < len(positions) else (0.5, 0.7)
        scale = scales[i] if i < len(scales) else 0.4
        placements.append(CharacterPlacement(
            char_image_path=char_path,
            position_x=x,
            position_y=y,
            scale=scale,
        ))

    return composer.compose(scene_path, placements, output_path)


if __name__ == "__main__":
    print("=" * 60)
    print("角色+场景合成图生成器 v1.0")
    print("=" * 60)
    print(f"Pillow: {'✅ 可用' if _PIL_AVAILABLE else '❌ 不可用'}")

    if not _PIL_AVAILABLE:
        print("\n请先安装Pillow: pip install Pillow")
        exit(1)

    # 创建测试图片
    test_dir = os.path.join(os.path.dirname(__file__), "test_composite")
    os.makedirs(test_dir, exist_ok=True)

    # 创建测试场景图（渐变背景）
    scene_path = os.path.join(test_dir, "test_scene.png")
    scene = Image.new("RGB", (800, 600), (40, 40, 60))
    draw = ImageDraw.Draw(scene)
    # 模拟暖光
    for i in range(200):
        alpha = int(100 * (1 - i / 200))
        draw.ellipse([(300 - i, 100 - i), (500 + i, 300 + i)],
                      fill=(255, 200, 100, alpha))
    scene.save(scene_path)

    # 创建测试角色图（带透明背景的人形）
    char_path = os.path.join(test_dir, "test_character.png")
    char = Image.new("RGBA", (200, 400), (0, 0, 0, 0))
    char_draw = ImageDraw.Draw(char)
    # 头
    char_draw.ellipse([(60, 20), (140, 100)], fill=(200, 150, 100, 255))
    # 身体
    char_draw.rectangle([(50, 100), (150, 300)], fill=(100, 100, 200, 255))
    # 腿
    char_draw.rectangle([(55, 300), (95, 400)], fill=(50, 50, 100, 255))
    char_draw.rectangle([(105, 300), (145, 400)], fill=(50, 50, 100, 255))
    char.save(char_path)

    print(f"\n测试图片已创建:")
    print(f"  场景图: {scene_path}")
    print(f"  角色图: {char_path}")

    # 测试合成
    output_path = os.path.join(test_dir, "test_composite.png")
    result = compose_character_scene(
        scene_path=scene_path,
        char_paths=[char_path],
        output_path=output_path,
        positions=[(0.5, 0.65)],
        scales=[0.5],
    )

    print(f"\n✅ 合成完成: {output_path}")
    print(f"  尺寸: {result.size}")
    print(f"  格式: {result.mode}")

    # 测试多角色合成
    output_path2 = os.path.join(test_dir, "test_multi_composite.png")
    result2 = compose_character_scene(
        scene_path=scene_path,
        char_paths=[char_path, char_path],
        output_path=output_path2,
        positions=[(0.3, 0.65), (0.7, 0.65)],
        scales=[0.4, 0.45],
    )

    print(f"\n✅ 多角色合成完成: {output_path2}")
    print(f"  尺寸: {result2.size}")

    print("\n" + "=" * 60)
    print("✅ 角色+场景合成图生成器自测通过")
    print("=" * 60)
