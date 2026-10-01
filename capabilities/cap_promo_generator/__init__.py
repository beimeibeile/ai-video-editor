"""
宣传视频生成器 (cap_promo_generator)
专门针对宣传视频优化，解决黑屏/文字图片/无ComfyUI素材问题

核心特性：
- 全程背景覆盖（全局+场景级，无黑屏）
- 剪映原生文字轨道（非文字图片）
- ComfyUI可选生成场景图片
- 自动淡入淡出转场
- 快速模式（quick_promo）一键生成
"""
from .promo_generator import PromoVideoGenerator, GRADIENT_PRESETS

__all__ = ["PromoVideoGenerator", "GRADIENT_PRESETS"]
__version__ = "1.0.0"
