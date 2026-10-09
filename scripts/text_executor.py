"""
P25执行器: 文字排版
支持多种文字样式和动画，生成文字素材或定义剪映文字参数
"""

import os
from typing import Dict, Any, List, Optional
import logging
logger = logging.getLogger(__name__)


# 文字样式预设
TEXT_STYLES = {
    "normal": {
        "font_size": 8, "font_color": "#FFFFFF", "background_color": "#00000080",
        "position": "bottom", "animation": "fade",
    },
    "artistic": {
        "font_size": 12, "font_color": "#FFD700", "background_color": "#00000000",
        "position": "center", "animation": "wipe",
    },
    "vertical": {
        "font_size": 10, "font_color": "#FFFFFF", "background_color": "#00000000",
        "position": "right", "animation": "slide", "vertical": True,
    },
    "handwriting": {
        "font_size": 14, "font_color": "#FFFFFF", "background_color": "#00000000",
        "position": "center", "animation": "fade", "font_family": "手写体",
    },
    "poetic": {
        "font_size": 10, "font_color": "#E8E8E8", "background_color": "#00000060",
        "position": "bottom", "animation": "fade", "font_family": "楷体",
    },
    "subtitle_bar": {
        "font_size": 8, "font_color": "#FFFFFF", "background_color": "#000000CC",
        "position": "bottom", "animation": "slide", "bar_style": "gradient",
    },
}

# 文字动画映射
ANIMATION_MAP = {
    "fade": "淡入淡出",
    "slide": "滑入",
    "wipe": "擦开",
    "mask": "蒙版展开",
    "typewriter": "打字机",
    "bounce": "弹跳",
}


class TextExecutor:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor", "director_engine_output", "text"
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def get_style(self, style_name: str) -> Dict:
        return TEXT_STYLES.get(style_name, TEXT_STYLES["normal"])

    def generate_text_params(self, text: str, style_name: str = "normal",
                              start_time: float = 0.0, duration: float = 3.0,
                              position: str = None) -> Dict[str, Any]:
        """生成剪映文字参数（不生成素材，直接定义参数）"""
        style = self.get_style(style_name)
        pos = position or style.get("position", "bottom")

        # 位置映射
        position_map = {
            "top": (0, 0.7), "center": (0, 0), "bottom": (0, -0.7),
            "left": (-0.7, 0), "right": (0.7, 0),
        }
        x, y = position_map.get(pos, (0, -0.7))

        return {
            "text": text,
            "style": style_name,
            "font_size": style.get("font_size", 8),
            "font_color": style.get("font_color", "#FFFFFF"),
            "background_color": style.get("background_color", "#00000080"),
            "position_x": x,
            "position_y": y,
            "animation": style.get("animation", "fade"),
            "vertical": style.get("vertical", False),
            "font_family": style.get("font_family", None),
            "start_time": start_time,
            "duration": duration,
        }

    def generate_text_asset(self, text: str, style_name: str = "normal",
                             output_file: str = None) -> Optional[str]:
        """生成文字素材PNG（用于复杂样式）"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.info("  ⚠️  PIL不可用，跳过文字素材生成")
            return None

        if output_file is None:
            safe_text = text[:10].replace("/", "_").replace("\\", "_")
            output_file = os.path.join(self.output_dir, f"text_{style_name}_{safe_text}.png")

        style = self.get_style(style_name)
        width, height = 1080, 200
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 背景
        bg_color = style.get("background_color", "#00000080")
        if bg_color and bg_color != "#00000000":
            bg_rgba = self._hex_to_rgba(bg_color)
            draw.rounded_rectangle([20, 20, width-20, height-20], radius=20, fill=bg_rgba)

        # 文字
        font_size = int(style.get("font_size", 8) * 10)
        font_color = self._hex_to_rgba(style.get("font_color", "#FFFFFF"))
        try:
            font = ImageFont.truetype("msyh.ttc", font_size)
        except Exception:
            font = ImageFont.load_default()

        # 居中绘制
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        draw.text((x, y), text, fill=font_color, font=font)

        img.save(output_file, "PNG")
        logger.info(f"  ✅ 文字素材: {style_name} - {text[:20]}")
        return output_file

    def _hex_to_rgba(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            hex_color += "FF"
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))

    def execute(self, text_instructions: List[Dict]) -> Dict[str, Any]:
        logger.info(f"\n{'='*60}")
        logger.info(f"文字执行器: {len(text_instructions)}条指令")
        logger.info(f"{'='*60}")
        results = []
        for i, instr in enumerate(text_instructions):
            text = instr.get("text", "")
            style = instr.get("style", "normal")
            start_time = instr.get("start_time", 0.0)
            duration = instr.get("duration", 3.0)
            generate_asset = instr.get("generate_asset", False)

            if generate_asset:
                output_file = os.path.join(self.output_dir, f"text_{i:03d}_{style}.png")
                path = self.generate_text_asset(text, style, output_file)
                results.append({
                    "text": text, "style": style, "type": "asset",
                    "output_path": path, "success": path is not None
                })
            else:
                params = self.generate_text_params(text, style, start_time, duration)
                logger.info(f"  ✅ 文字参数: {style} - {text[:20]}")
                results.append({
                    "text": text, "style": style, "type": "params",
                    "params": params, "success": True
                })

        success_count = sum(1 for r in results if r["success"])
        logger.info(f"\n  完成: {success_count}成功 / {len(results)-success_count}失败")
        return {
            "status": "success" if success_count == len(results) else "partial",
            "total": len(results), "success": success_count,
            "failed": len(results)-success_count, "output_dir": self.output_dir,
            "results": results
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    executor = TextExecutor()
    test = [
        {"text": "大家好，我是豆包！", "style": "normal", "start_time": 0, "duration": 3},
        {"text": "好痛啊...", "style": "poetic", "start_time": 3, "duration": 2},
        {"text": "别跑！", "style": "artistic", "start_time": 5, "duration": 2},
    ]
    result = executor.execute(test)
    logger.info(f"结果: {result['status']}")
