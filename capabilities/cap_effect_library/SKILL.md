# cap_effect_library — 特效库模块

## 概述

转场/滤镜预设，根据视频主题自动匹配风格，解决"转场特效错位"问题。

## 依赖

- jianying-editor（pyJianYingDraft）

## API

```python
from capabilities.cap_effect_library import (
    add_transition, auto_add_transitions, get_style_preset,
    list_transitions, list_filters, list_style_presets
)

# 1. 添加单个转场
add_transition(project, segment, transition_type="dissolve", duration="0.4s")

# 2. 批量自动转场
auto_add_transitions(project, segments, transition_type="zoom")

# 3. 根据主题获取风格预设
preset = get_style_preset("国风")
# {'transition': 'dissolve', 'filter': 'warm', 'subtitle': 'epic', 'bgm': '国风'}

# 4. 查看可用选项
print(list_transitions())  # 转场列表
print(list_filters())      # 滤镜列表
print(list_style_presets()) # 风格预设列表
```

## 转场类型

| 类型 | 名称 | 风格 |
|------|------|------|
| dissolve | 叠化 | 柔和 |
| fade_black | 闪黑 | 电影感 |
| fade_white | 闪白 | 炫酷 |
| blur | 模糊 | 柔和 |
| slide_left/right | 滑动 | 动感 |
| zoom | 缩放 | 炫酷 |
| glitch | 故障 | 赛博 |

## 风格预设

| 主题 | 转场 | 滤镜 | 字幕 | BGM |
|------|------|------|------|-----|
| 国风 | 叠化 | 暖色 | epic | 国风 |
| 治愈 | 叠化 | 暖色 | warm | 治愈 |
| 卡点 | 缩放 | 鲜艳 | fun | 电子 |
| 电影 | 闪黑 | 电影感 | cinema | 电影 |
| 赛博 | 故障 | 赛博 | fun | 电子 |
| 极简 | 叠化 | 清新 | minimal | 轻音乐 |
| 复古 | 闪白 | 复古 | warm | 复古 |
