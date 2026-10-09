#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P28-4 HyperFrames文字动画代码生成器
将文字样式/转场特效/动画指令转换为HyperFrames兼容的HTML+GSAP代码

支持的动画类型:
- 入场: fade_in, slide_up, slide_down, slide_left, slide_right, zoom_in, typewriter, bounce
- 出场: fade_out, slide_up_out, slide_down_out, zoom_out
- 循环: pulse, shake, float, wiggle, glow
- 转场: crossfade, wipe_left, wipe_right, blur_in
- 样式: 渐变文字, 描边文字, 发光文字, 阴影文字, 打字机光标
"""

import os
import json
from typing import Dict, Any, List
from dataclasses import dataclass, field
import logging
logger = logging.getLogger(__name__)


# ============ 文字样式预设 ============

TEXT_STYLES = {
    "default": {
        "font_family": "Inter, ui-sans-serif, system-ui, sans-serif",
        "font_weight": "600",
        "font_size": "72px",
        "color": "#f4f4f5",
        "text_align": "center",
        "letter_spacing": "-0.03em",
    },
    "epic": {
        "font_family": "Inter, ui-sans-serif, system-ui, sans-serif",
        "font_weight": "800",
        "font_size": "120px",
        "color": "#ffffff",
        "text_align": "center",
        "letter_spacing": "0.05em",
        "text_shadow": "0 0 40px rgba(99,102,241,0.8), 0 0 80px rgba(99,102,241,0.4)",
    },
    "warm": {
        "font_family": "Georgia, serif",
        "font_weight": "400",
        "font_size": "64px",
        "color": "#fbbf24",
        "text_align": "center",
        "letter_spacing": "0.02em",
    },
    "fun": {
        "font_family": "Comic Sans MS, cursive",
        "font_weight": "700",
        "font_size": "80px",
        "color": "#f472b6",
        "text_align": "center",
        "letter_spacing": "0.02em",
    },
    "minimal": {
        "font_family": "Inter, ui-sans-serif, system-ui, sans-serif",
        "font_weight": "300",
        "font_size": "48px",
        "color": "#a1a1aa",
        "text_align": "center",
        "letter_spacing": "0.1em",
    },
    "cinematic": {
        "font_family": "Georgia, serif",
        "font_weight": "700",
        "font_size": "96px",
        "color": "#e5e5e5",
        "text_align": "center",
        "letter_spacing": "0.15em",
        "text_transform": "uppercase",
    },
    "neon": {
        "font_family": "Inter, ui-sans-serif, system-ui, sans-serif",
        "font_weight": "700",
        "font_size": "88px",
        "color": "#22d3ee",
        "text_align": "center",
        "letter_spacing": "0.1em",
        "text_shadow": "0 0 10px #22d3ee, 0 0 20px #22d3ee, 0 0 40px #22d3ee, 0 0 80px #0891b2",
    },
    "gradient": {
        "font_family": "Inter, ui-sans-serif, system-ui, sans-serif",
        "font_weight": "800",
        "font_size": "100px",
        "text_align": "center",
        "letter_spacing": "-0.02em",
        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)",
        "background_clip": "text",
        "-webkit-background-clip": "text",
        "color": "transparent",
    },
}


# ============ 入场动画GSAP映射 ============

INTRO_ANIMATIONS = {
    "fade_in": 'tl.fromTo("#text",{opacity:0},{opacity:1,duration:0.8,ease:"power2.out"},0);',
    "slide_up": 'tl.fromTo("#text",{opacity:0,y:80},{opacity:1,y:0,duration:0.8,ease:"power3.out"},0);',
    "slide_down": 'tl.fromTo("#text",{opacity:0,y:-80},{opacity:1,y:0,duration:0.8,ease:"power3.out"},0);',
    "slide_left": 'tl.fromTo("#text",{opacity:0,x:120},{opacity:1,x:0,duration:0.8,ease:"power3.out"},0);',
    "slide_right": 'tl.fromTo("#text",{opacity:0,x:-120},{opacity:1,x:0,duration:0.8,ease:"power3.out"},0);',
    "zoom_in": 'tl.fromTo("#text",{opacity:0,scale:0.3},{opacity:1,scale:1,duration:0.8,ease:"back.out(1.7)"},0);',
    "bounce": 'tl.fromTo("#text",{opacity:0,y:-100},{opacity:1,y:0,duration:1.0,ease:"bounce.out"},0);',
    "typewriter": 'tl.fromTo("#text",{opacity:0,width:0},{opacity:1,width:"100%",duration:1.5,ease:"steps(30)"},0);',
    "blur_in": 'tl.fromTo("#text",{opacity:0,filter:"blur(20px)"},{opacity:1,filter:"blur(0px)",duration:0.8,ease:"power2.out"},0);',
    "rotate_in": 'tl.fromTo("#text",{opacity:0,rotation:-15,scale:0.8},{opacity:1,rotation:0,scale:1,duration:0.8,ease:"back.out(1.7)"},0);',
    "flip_in": 'tl.fromTo("#text",{opacity:0,rotationX:90},{opacity:1,rotationX:0,duration:0.8,ease:"power2.out"},0);',
}

# ============ 出场动画GSAP映射 ============

OUTRO_ANIMATIONS = {
    "fade_out": 'tl.to("#text",{opacity:0,duration:0.5,ease:"power2.in"},out_start);',
    "slide_up_out": 'tl.to("#text",{opacity:0,y:-60,duration:0.5,ease:"power2.in"},out_start);',
    "slide_down_out": 'tl.to("#text",{opacity:0,y:60,duration:0.5,ease:"power2.in"},out_start);',
    "zoom_out": 'tl.to("#text",{opacity:0,scale:0.5,duration:0.5,ease:"power2.in"},out_start);',
    "blur_out": 'tl.to("#text",{opacity:0,filter:"blur(20px)",duration:0.5,ease:"power2.in"},out_start);',
}

# ============ 循环动画GSAP映射 ============

LOOP_ANIMATIONS = {
    "pulse": 'tl.to("#text",{scale:1.05,duration:0.5,ease:"sine.inOut",yoyo:true,repeat:-1},loop_start);',
    "shake": 'tl.to("#text",{x:5,duration:0.1,ease:"none",repeat:5,yoyo:true},loop_start);',
    "float": 'tl.to("#text",{y:-15,duration:1.5,ease:"sine.inOut",yoyo:true,repeat:-1},loop_start);',
    "wiggle": 'tl.to("#text",{rotation:3,duration:0.3,ease:"sine.inOut",yoyo:true,repeat:-1},loop_start);',
    "glow": 'tl.to("#text",{textShadow:"0 0 20px currentColor,0 0 40px currentColor",duration:1.0,ease:"sine.inOut",yoyo:true,repeat:-1},loop_start);',
    "color_shift": 'tl.to("#text",{color:"#f472b6",duration:1.0,ease:"sine.inOut",yoyo:true,repeat:-1},loop_start);',
}


@dataclass
class TextAnimationConfig:
    """文字动画配置"""
    text: str
    duration: float = 5.0
    style: str = "default"
    intro: str = "fade_in"
    outro: str = "fade_out"
    loop: str = None  # None表示无循环
    subtitle: str = None
    bg_color: str = "#0a0a0a"
    width: int = 1920
    height: int = 1080
    position: str = "center"  # center/top/bottom
    custom_css: str = ""
    custom_gsap: str = ""


class HyperFramesTextAnimator:
    """HyperFrames文字动画生成器

    将文字动画配置转换为完整的HTML+GSAP代码，可直接被HyperFramesExecutor渲染
    """

    def __init__(self):
        self.templates = TEXT_STYLES
        self.intro_anims = INTRO_ANIMATIONS
        self.outro_anims = OUTRO_ANIMATIONS
        self.loop_anims = LOOP_ANIMATIONS

    def generate_html(self, config: TextAnimationConfig) -> str:
        """生成完整的HyperFrames HTML

        Args:
            config: 文字动画配置

        Returns:
            完整的HTML字符串
        """
        style = self.templates.get(config.style, self.templates["default"])

        # 构建CSS
        css_parts = []
        css_parts.append(f"font-family: {style.get('font_family', 'sans-serif')};")
        css_parts.append(f"font-weight: {style.get('font_weight', '600')};")
        css_parts.append(f"font-size: {style.get('font_size', '72px')};")
        css_parts.append(f"text-align: {style.get('text_align', 'center')};")
        css_parts.append(f"letter-spacing: {style.get('letter_spacing', '0em')};")

        if style.get("color"):
            css_parts.append(f"color: {style['color']};")
        if style.get("text_shadow"):
            css_parts.append(f"text-shadow: {style['text_shadow']};")
        if style.get("background"):
            css_parts.append(f"background: {style['background']};")
        if style.get("background_clip"):
            css_parts.append(f"background-clip: {style['background_clip']};")
            css_parts.append(f"-webkit-background-clip: {style['-webkit-background-clip']};")
        if style.get("text_transform"):
            css_parts.append(f"text-transform: {style['text_transform']};")

        text_css = "\n        ".join(css_parts)

        # 位置样式
        position_css = {
            "center": "align-items: center; justify-content: center;",
            "top": "align-items: flex-start; justify-content: center; padding-top: 120px;",
            "bottom": "align-items: flex-end; justify-content: center; padding-bottom: 120px;",
        }.get(config.position, "align-items: center; justify-content: center;")

        # 构建GSAP动画
        gsap_parts = []
        gsap_parts.append("const tl = gsap.timeline({ paused: true });")

        # 入场动画
        intro = self.intro_anims.get(config.intro, self.intro_anims["fade_in"])
        gsap_parts.append(intro)

        # 循环动画
        if config.loop and config.loop in self.loop_anims:
            loop_start = min(1.0, config.duration * 0.2)
            gsap_parts.append(f"const loop_start = {loop_start};")
            gsap_parts.append(self.loop_anims[config.loop])

        # 出场动画
        if config.outro and config.outro in self.outro_anims:
            out_start = max(0, config.duration - 0.8)
            gsap_parts.append(f"const out_start = {out_start};")
            gsap_parts.append(self.outro_anims[config.outro])

        # 自定义GSAP
        if config.custom_gsap:
            gsap_parts.append(config.custom_gsap)

        gsap_code = "\n      ".join(gsap_parts)

        # 副标题
        subtitle_html = ""
        if config.subtitle:
            subtitle_html = f'''<p id="subtitle" class="clip" data-start="0.3" data-duration="{config.duration - 0.3}" data-track-index="1" style="font-size: 32px; color: #a1a1aa; margin-top: 24px; font-weight: 400;">{config.subtitle}</p>'''

        # 自定义CSS
        custom_css = config.custom_css or ""

        html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={config.width}, height={config.height}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ margin:0; width:{config.width}px; height:{config.height}px; overflow:hidden; background:{config.bg_color}; }}
#root {{ width:100%; height:100%; display:flex; flex-direction:column; {position_css} }}
#text {{
        {text_css}
}}
{custom_css}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{config.duration}"
     data-width="{config.width}" data-height="{config.height}">
  <h1 id="text" class="clip" data-start="0" data-duration="{config.duration}" data-track-index="0">{config.text}</h1>
  {subtitle_html}
</div>
<script>
      {gsap_code}
      window.__timelines["main"] = tl;
      tl.seek(0);
</script>
</body>
</html>'''
        return html

    def generate_from_instruction(self, instruction: Dict[str, Any]) -> str:
        """从指令字典生成HTML

        Args:
            instruction: 指令字典，支持字段:
                - text: 文字内容（必需）
                - duration: 时长
                - style: 样式名称
                - intro/outro/loop: 动画类型
                - subtitle: 副标题
                - bg_color: 背景色
                - position: 位置

        Returns:
            HTML字符串
        """
        config = TextAnimationConfig(
            text=instruction.get("text", ""),
            duration=instruction.get("duration", 5.0),
            style=instruction.get("style", "default"),
            intro=instruction.get("intro", "fade_in"),
            outro=instruction.get("outro", "fade_out"),
            loop=instruction.get("loop"),
            subtitle=instruction.get("subtitle"),
            bg_color=instruction.get("bg_color", "#0a0a0a"),
            width=instruction.get("width", 1920),
            height=instruction.get("height", 1080),
            position=instruction.get("position", "center"),
        )
        return self.generate_html(config)

    def list_styles(self) -> List[str]:
        """列出可用样式"""
        return list(self.templates.keys())

    def list_animations(self) -> Dict[str, List[str]]:
        """列出可用动画"""
        return {
            "intro": list(self.intro_anims.keys()),
            "outro": list(self.outro_anims.keys()),
            "loop": list(self.loop_anims.keys()),
        }


# ============ 快捷函数 ============

def generate_title_card(text: str, subtitle: str = None,
                        style: str = "epic", duration: float = 5.0,
                        intro: str = "zoom_in", outro: str = "fade_out") -> str:
    """快捷生成标题卡片HTML"""
    animator = HyperFramesTextAnimator()
    config = TextAnimationConfig(
        text=text, subtitle=subtitle, style=style,
        duration=duration, intro=intro, outro=outro,
    )
    return animator.generate_html(config)


def generate_kinetic_typography(lines: List[Dict[str, Any]],
                                 duration: float = 8.0,
                                 bg_color: str = "#0a0a0a") -> str:
    """生成动态排版（多行文字依次出现）

    Args:
        lines: 每行配置 [{text, style, intro, delay, duration}]
        duration: 总时长
        bg_color: 背景色
    """
    animator = HyperFramesTextAnimator()

    # 构建多行HTML
    line_htmls = []
    gsap_parts = ["const tl = gsap.timeline({ paused: true });"]

    for i, line in enumerate(lines):
        line_id = f"line_{i}"
        line_text = line.get("text", "")
        line_style = line.get("style", "default")
        line_intro = line.get("intro", "slide_up")
        line_delay = line.get("delay", i * 0.8)
        line_duration = line.get("duration", duration - line_delay - 0.5)

        style = TEXT_STYLES.get(line_style, TEXT_STYLES["default"])
        css = f"font-family:{style.get('font_family')};font-weight:{style.get('font_weight')};font-size:{style.get('font_size')};color:{style.get('color','#fff')};margin:12px 0;"

        line_htmls.append(
            f'<div id="{line_id}" class="clip" data-start="{line_delay}" '
            f'data-duration="{line_duration}" data-track-index="{i}" style="{css}">{line_text}</div>'
        )

        # 入场动画
        intro_gsap = INTRO_ANIMATIONS.get(line_intro, INTRO_ANIMATIONS["fade_in"])
        intro_gsap = intro_gsap.replace('"#text"', f'"#{line_id}"')
        intro_gsap = intro_gsap.replace("},0);", f"}},{line_delay});")
        gsap_parts.append(intro_gsap)

    gsap_code = "\n      ".join(gsap_parts)
    lines_html = "\n    ".join(line_htmls)

    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920, height=1080" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ margin:0; width:1920px; height:1080px; overflow:hidden; background:{bg_color}; }}
#root {{ width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{duration}"
     data-width="1920" data-height="1080">
    {lines_html}
</div>
<script>
      {gsap_code}
      window.__timelines["main"] = tl;
      tl.seek(0);
</script>
</body>
</html>'''


# ============ 测试 ============

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("=== HyperFrames文字动画生成器测试 ===")
    animator = HyperFramesTextAnimator()

    logger.info(f"\n可用样式: {animator.list_styles()}")
    logger.info(f"可用动画: {json.dumps(animator.list_animations(), ensure_ascii=False, indent=2)}")

    # 测试1: 标题卡片
    logger.info("\n--- 测试1: 标题卡片 ---")
    html1 = generate_title_card("AI Video Editor", "HyperFrames文字动画", style="epic")
    logger.info(f"HTML长度: {len(html1)}字符")

    # 测试2: 动态排版
    logger.info("\n--- 测试2: 动态排版 ---")
    html2 = generate_kinetic_typography([
        {"text": "第一行", "style": "epic", "intro": "slide_up", "delay": 0},
        {"text": "第二行", "style": "neon", "intro": "fade_in", "delay": 1.0},
        {"text": "第三行", "style": "gradient", "intro": "zoom_in", "delay": 2.0},
    ], duration=6.0)
    logger.info(f"HTML长度: {len(html2)}字符")

    # 测试3: 从指令生成
    logger.info("\n--- 测试3: 从指令生成 ---")
    instruction = {
        "text": "测试文字",
        "style": "neon",
        "intro": "blur_in",
        "loop": "pulse",
        "duration": 4.0,
    }
    html3 = animator.generate_from_instruction(instruction)
    logger.info(f"HTML长度: {len(html3)}字符")

    # 写入测试文件
    test_dir = r"D:\DobaoWork_Project\Ai_Video_Editor\p28_hyperframes_test"
    os.makedirs(test_dir, exist_ok=True)
    with open(os.path.join(test_dir, "test_title_card.html"), "w", encoding="utf-8") as f:
        f.write(html1)
    with open(os.path.join(test_dir, "test_kinetic.html"), "w", encoding="utf-8") as f:
        f.write(html2)
    logger.info(f"\n测试HTML已写入: {test_dir}")
    logger.info("完成!")
