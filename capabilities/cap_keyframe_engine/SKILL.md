# cap_keyframe_engine — 关键帧引擎

## 概述

为静态图片/视频片段自动添加运镜效果，解决"全是静止图片观感单调"问题。

## 依赖

- jianying-editor（pyJianYingDraft）

## API

```python
from capabilities.cap_keyframe_engine import (
    add_ken_burns, add_fade_in_out, auto_keyframe_for_still_image, list_camera_moves
)

# 1. Ken Burns运镜
add_ken_burns(segment, start_us, duration_us, move_type="zoom_in", intensity=1.0)

# 2. 淡入淡出
add_fade_in_out(segment, start_us, duration_us, fade_in_us=300000, fade_out_us=300000)

# 3. 一键自动关键帧（成片用）
auto_keyframe_for_still_image(segment, start_us, duration_us, index=0)

# 4. 查看可用运镜
print(list_camera_moves())
# ['zoom_in', 'zoom_out', 'pan_left', 'pan_right', 'pan_up', 'pan_down', 'zoom_in_left', 'zoom_in_right']
```

## 运镜类型

| 类型 | 描述 | 效果 |
|------|------|------|
| zoom_in | 推近 | 缓慢放大 |
| zoom_out | 拉远 | 缓慢缩小 |
| pan_left | 左移 | 画面左移 |
| pan_right | 右移 | 画面右移 |
| pan_up | 上移 | 画面上移 |
| pan_down | 下移 | 画面下移 |
| zoom_in_left | 推近+左移 | 组合运镜 |
| zoom_in_right | 推近+右移 | 组合运镜 |

## 使用场景

- 静态图片轮播：每个图片用不同运镜，避免单调
- 视频片段：添加淡入淡出，转场更自然
- 一键成片：auto_keyframe_for_still_image自动分配运镜
