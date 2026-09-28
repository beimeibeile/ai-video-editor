# cap_material_creator — 制作素材能力模块

> 版本：v1.0 | 状态：🟢 已实现 | 触发：用户命令 / 主流程自主调用

## 模块定位

在视频制作的素材准备阶段，根据方案需求**自主设计并生成**所需素材，避免依赖外部工具额度。生成的素材自动归档到 `assets/reusable/` 供后续复用。

## 触发条件

### 用户触发
- "制作发光轮廓素材" / "生成轮廓图"
- "生成彩色纹理" / "做个渐变背景"
- "生成占位图" / "做几张数字图"
- "制作素材" + 具体描述

### 自主触发（主流程判断）
- 方案需要**正片叠底/混合模式**效果 → 自动生成轮廓图+纹理图+Python合成
- 模式B仿制模板需要**可替换占位素材** → 自动生成数字占位图
- 方案需要**纯色/渐变背景** → 自动生成背景图
- jianying-editor API不支持的效果（如混合模式）→ 用Python预合成替代

## API 速查

### 轮廓图生成
```python
from capabilities.cap_material_creator import generate_outline, generate_outline_from_text

# 几何轮廓
generate_outline(shape="circle", size=(1920,1080), output_path="outline.png")
# shape: circle / rect / star

# 文字轮廓（黑底白边描边）
generate_outline_from_text("GLOW", font_size=200, output_path="outline_text.png")
```

### 纹理图生成
```python
from capabilities.cap_material_creator import generate_texture, TEXTURE_PRESETS

# 预设纹理
generate_texture(preset="rainbow", size=(1920,1080), output_path="tex.png")
# preset: rainbow(彩虹流体) / fire(火焰) / cyber(赛博朋克) / sunset(日落) / ocean(海洋) / neon(霓虹)

# 自定义
generate_texture(colors=[(255,0,0),(0,0,255)], mode="radial_gradient", output_path="tex.png")
```

### 混合模式合成（替代剪映blend_mode）
```python
from capabilities.cap_material_creator import multiply_blend, screen_blend

# 正片叠底：黑底白边轮廓 + 彩色纹理 → 黑底彩色轮廓
multiply_blend("outline.png", "texture.png", "result.png")

# 滤色：黑底发光素材 + 背景 → 发光叠加
screen_blend("glow.png", "bg.png", "result.png")
```

### 占位图生成
```python
from capabilities.cap_material_creator import generate_placeholder, generate_placeholder_batch

# 单张
generate_placeholder(number=1, ratio="9:16", output_path="p1.png")

# 批量（自动归档到 assets/reusable/placeholders/）
generate_placeholder_batch(start=0, end=30, ratio="9:16")
generate_placeholder_batch(start=0, end=30, ratio="16:9")
```

### 背景图生成
```python
from capabilities.cap_material_creator import generate_background

generate_background(style="dark_gradient", ratio="16:9", output_path="bg.png")
# style: solid / dark_gradient / light_gradient / radial_glow / noise
```

### 半透明字幕条生成（替代剪映复合片段，支持文字烧录/非烧录/动态）
```python
from capabilities.cap_material_creator import (
    generate_subtitle_bar, generate_subtitle_bar_preset,
    generate_subtitle_bar_animated, SUBTITLE_BAR_PRESETS, ANIMATION_PRESETS
)

# 模式1：文字烧录（静态成品，排版精确，一次性使用）
generate_subtitle_bar_preset("sunset", title_text="MR. Dong", subtitle_text="EDITOR", output_path="bar.png")

# 模式2：非烧录（只生成背景条，文字在剪映中添加，可保存为文字预设复用）
generate_subtitle_bar_preset("ocean", burn_text=False, output_path="bar_bg.png")

# 模式3：动态背景条（MP4，黑色背景，剪映中用"滤色"混合去黑）
generate_subtitle_bar_animated(
    output_path="bar_anim.mp4", duration=3.0, fps=30,
    animation="glow_pulse",  # glow_pulse/subtle_bounce/light_sweep/breath
    gradient_colors=((0,200,255),(0,50,150)),
    burn_text=False  # 动态模式建议非烧录，文字在剪映添加
)
```
> **三种模式选择**：
> - `burn_text=True`（默认）：文字烧进PNG，适合一次性静态素材，排版精确
> - `burn_text=False`：只输出背景条PNG，文字在剪映单独添加，可保存为**文字预设**随时修改复用
> - `generate_subtitle_bar_animated()`：生成3秒可循环MP4，4种轻微动效（微变背景光/轻微律动/流光扫过/呼吸透明度），黑色背景导入剪映后用"混合模式-滤色"去黑
>
> jianying-editor不支持复合片段，此为Python预合成替代方案。

## 典型工作流：动态发光轮廓效果

```
1. generate_outline("circle")          → 黑底白边圆形轮廓
2. generate_texture("rainbow")         → 彩虹渐变纹理
3. multiply_blend(轮廓, 纹理)          → 黑底彩色轮廓（Python预合成）
4. 导入剪映 + add_effect_simple("梦幻辉光") + add_effect_simple("梦境")
5. Ken Burns关键帧缩放 → 动态发光效果
```

**为什么用Python预合成而不是剪映混合模式？**
jianying-editor 的 ClipSettings 不支持 `blend_mode` 字段，draft_info.json 中无混合模式相关字段，5.9 版本无 draft_content.json。Python 正片叠底公式 `result = upper × lower / 255` 效果完全一致，且更可靠。

## 素材归档规范

生成的可复用素材自动命名并归档：
```
assets/reusable/
├── placeholders/    placeholder_{编号}_{比例}.png
├── textures/        texture_{名称}_{比例}.png
├── outlines/        outline_{形状}_{比例}.png
└── backgrounds/     background_{样式}_{比例}.png
```

## 已知限制

- 轮廓图目前支持几何形状（圆/方/星）和文字，**复杂人物/物体轮廓**需用 image_edit 参考图生成
- 纹理图为程序化渐变，**复杂流体/烟雾纹理**需用 image_edit 生成
- 混合模式目前支持 multiply/screen/overlay，其他模式（如颜色减淡/线性光）待扩展
- 大尺寸图片（>4K）像素级合成较慢，建议 ≤1920×1080
