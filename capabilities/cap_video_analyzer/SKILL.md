# cap_video_analyzer — 视频分析模块

## 概述

视频信息提取、场景检测、关键帧提取、缩略图生成，用于仿制模板和素材预处理。

## 依赖

- ffmpeg / ffprobe（系统PATH或指定路径）

## API

```python
from capabilities.cap_video_analyzer import (
    get_video_info, detect_scenes, extract_keyframes,
    generate_thumbnail, analyze_video, is_available
)

# 1. 检查可用性
print(is_available())  # True/False

# 2. 视频基本信息
info = get_video_info("video.mp4")
# {'duration': 10.5, 'width': 1080, 'height': 1920, 'fps': 30, 'has_audio': True, ...}

# 3. 场景检测
scenes = detect_scenes("video.mp4", threshold=0.3)
# [1.25, 3.80, 6.15, 8.90]  场景切换时间点（秒）

# 4. 提取关键帧
frames = extract_keyframes("video.mp4", "./output", num_frames=5)
# ['./output/keyframe_001.jpg', ...]

# 5. 生成缩略图
thumb = generate_thumbnail("video.mp4", "./thumb.jpg", timestamp=1.0, width=320)

# 6. 完整分析
result = analyze_video("video.mp4", output_dir="./analysis")
# {'info': {...}, 'scenes': [...], 'keyframes': [...], 'thumbnail': '...'}
```

## 使用场景

- **仿制模板**：分析原视频的场景切换点，用于分镜设计
- **素材预处理**：提取视频关键帧作为图片素材
- **视频信息**：获取时长/分辨率/帧率，用于工程设置
- **缩略图**：生成素材预览图
