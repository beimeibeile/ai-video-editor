# 半透明字幕条特效

## 基本信息

| 字段 | 内容 |
|------|------|
| 特效ID | subtitle_bar |
| 分类 | text（文字特效） |
| 来源 | 抖音教程 - 剪辑进阶 |
| 教程时长 | 157秒 |
| 还原度 | ⭐⭐⭐⭐ 高度还原 |
| 状态 | ✅ 已验证 |

## 原始教程核心手法

1. 矩形贴纸作为字幕条背景（半透明+渐变）
2. 圆形贴纸放在矩形两端，用圆形蒙版反转做圆角效果
3. 复合片段组合矩形+圆形
4. 高光圆形贴纸增加质感
5. 文字放在字幕条上方

## 封装实现方案

**API限制**：剪映贴纸/复合片段通过API不好控制位置和蒙版

**降级方案**：Pillow预生成半透明渐变圆角矩形PNG，作为画中画轨道叠加
- 渐变圆角矩形背景（支持线性渐变）
- 高光圆形（独立画中画轨道）
- 文字（文本轨道）
- 入场动画（渐显/弹入/向上滑动）

## 可用预设（6种）

| 预设 | 风格 | 适用场景 |
|------|------|----------|
| pill_warm | 暖色药丸 | 生活、情感 |
| pill_cool | 冷色药丸 | 科技、商务 |
| pill_cyber | 赛博药丸 | 赛博朋克、游戏 |
| rect_dark | 深色矩形 | 影视、纪录片 |
| rect_minimal | 极简矩形 | 极简、文艺 |
| tag_small | 小标签 | 角标、分类标签 |

## 自定义参数

- `bg_color` / `bg_color2` - 渐变起止颜色
- `opacity` - 不透明度（0-1）
- `corner_radius` - 圆角半径
- `position_y` - 垂直位置（-1到1）
- `width_ratio` - 宽度比例（0-1）
- `anim_in` - 入场动画（fade/pop/slide_up）

## API接口

```python
from subtitle_bar import add_subtitle_bar, add_subtitle_bars

# 单个字幕条
add_subtitle_bar(
    project,
    text="这是字幕文字",
    start_time="1s",
    duration="3s",
    style="pill_cyber",
    position_y=0.5,
    anim_in="pop",
)

# 批量字幕条
add_subtitle_bars(project, [
    {"text": "第一句", "start_time": "0s", "duration": "2s"},
    {"text": "第二句", "start_time": "2s", "duration": "2s"},
], style="pill_warm")
```

## 测试工程

- `SubtitleBar_Demo` - 6种样式演示工程

## 已知限制

1. 进阶版复合片段+圆形蒙版反转未实现（用Pillow预生成圆角替代）
2. 阴影/描边美化层未实现
3. 字幕条微变背景光效/律动未实现

## 后续优化方向

- 支持动态背景光效（轻微律动）
- 支持阴影+描边美化层
- 优秀作品纳入预设库
