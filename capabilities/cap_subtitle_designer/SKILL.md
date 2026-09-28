# cap_subtitle_designer — 字幕设计模块

## 概述

动态艺术组合式字幕，多轨道叠加+动画+样式，解决"字幕过于简单"问题。

## 依赖

- jianying-editor（pyJianYingDraft）

## API

```python
from capabilities.cap_subtitle_designer import (
    add_artistic_subtitle, add_simple_subtitle, add_hook_title, list_styles
)

# 1. 艺术组合字幕（主标题+副标题+旁白，三层叠加）
add_artistic_subtitle(project, "主标题", "0s", "5s",
                       style="epic", sub_text="副标题", narration="旁白文字")

# 2. 简单底部字幕
add_simple_subtitle(project, "这是一句旁白", "1s", "3s")

# 3. 开篇钩子标题
add_hook_title(project, "你绝对想不到...", "0s", "3s", style="fun")

# 4. 查看风格
print(list_styles())
# [('epic', '国风史诗'), ('warm', '温暖治愈'), ('fun', '趣味卡点'), ('minimal', '极简'), ('cinema', '电影感')]
```

## 字幕风格

| 风格 | 特点 | 适用场景 |
|------|------|----------|
| epic | 金色大字+扫光动画 | 国风、史诗、震撼 |
| warm | 暖色调+弹入动画 | 治愈、情感、生活 |
| fun | 亮色+弹性动画 | 卡点、趣味、搞笑 |
| minimal | 白色小字+渐显 | 极简、文艺、高级 |
| cinema | 黑白+打字机 | 电影感、叙事 |

## 三层字幕结构

- **ArtTitle轨道**：主标题（大字号，带动画）
- **ArtSubtitle轨道**：副标题（中字号，辅助信息）
- **ArtNarration轨道**：旁白（底部小字号，逐字显示）
