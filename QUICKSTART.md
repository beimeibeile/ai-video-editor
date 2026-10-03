# ai-video-editor 快速开始指南 v1.0

## 一、这是什么

ai-video-editor 是一个**AI视频自动化生产系统**，支持两种内容模式：

| 模式 | 适用场景 | 核心能力 | 典型耗时 |
|------|----------|----------|----------|
| **电影模式** | 剧类、故事片、人物短片 | I2V真正动态视频 + 镜头语言分镜 + 质量门 | 15秒约1.5小时 |
| **短视频模式** | 旅拍、卡点、特效、标签视频 | 碎片剪辑 + 卡点 + 特效 + 原生字幕 | 30秒约5分钟 |

## 二、环境要求

### 硬件
- **GPU**: NVIDIA RTX 3080 12GB（推荐）或更高
- **内存**: 32GB以上
- **磁盘**: 100GB以上空闲空间（模型+素材）

### 软件
- **ComfyUI**: v3.2（绘世启动器启动，必须）
- **剪映**: 5.9免安装版（禁止更新）
- **Python**: 3.11（需numpy、psutil）
- **Blender**: 5.2（可选，用于3D特效）

### 必需模型
| 模型 | 大小 | 用途 |
|------|------|------|
| hunyuanvideo1.5_720p_i2v_fp16.safetensors | 15.5GB | 混元I2V图生视频 |
| qwen_2.5_vl_7b_fp8_scaled.safetensors | - | CLIP编码器1 |
| byt5_small_glyphxl_fp16.safetensors | - | CLIP编码器2 |
| hunyuanvideo15_vae_fp16.safetensors | - | VAE |
| Lightning/juggernautXL_v9-Lightning_4S | - | 快速文生图 |

## 三、5分钟快速上手

### 方式1：Python API（推荐）

```python
from easy_video import make_movie, make_short_video

# 生成剧类视频（电影模式）
result = make_movie(
    script="一个颓废的职场人发现了AI工具，经过努力后成功翻身",
    name="翻身",
    duration=15,
    quality="test",  # test=24fps快速, delivery=48fps高质量
)

# 生成短视频（标签模式）
result = make_short_video(
    topic="旅拍宣传片",
    tags=["旅行", "风景", "卡点"],
    duration=30,
    quality="test",
)
```

### 方式2：命令行

```bash
# 电影模式
python easy_video.py --mode movie --script "剧本内容" --name 我的视频 --duration 15

# 短视频模式
python easy_video.py --mode short --topic 旅拍 --tags 旅行,风景 --duration 30

# 高质量交付
python easy_video.py --mode movie --script "..." --name 成品 --quality delivery
```

## 四、双模式选择决策树

```
你的视频是什么类型？
│
├─ 有剧情、有人物、有对话 → 电影模式
│   ├─ 需要真正的动态画面（不是静态图推镜）
│   ├─ 分镜用镜头语言（推/拉/摇/移/跟）
│   └─ 质量门自动检查（3秒一切、台词装得下、景别变化）
│
└─ 碎片素材组合、卡点、特效、标签 → 短视频模式
    ├─ 图片/视频素材碎片剪辑
    ├─ BGM自动卡点
    ├─ 特效库25+种（蒙版快闪、字幕条、角色卡等）
    └─ 剪映原生字幕（可替换文字）
```

## 五、电影模式完整流程

```
剧本输入
  ↓
剧本解析（三幕结构+场景节拍+镜头拆解）
  ↓
分镜生成（镜头语言+景别+运镜+台词）
  ↓
质量门验证（24项检查+常见病诊断+自动修复）
  ↓
参考图生成（Lightning 4步快速出图，每镜一张）
  ↓
I2V视频生成（混元Video 1.5，49帧/2秒，逐个生成）
  ↓
剪映工程构建（镜头拼接+BGM+字幕+转场）
  ↓
资源自动清理（卸载ComfyUI模型+释放显存）
  ↓
交付（剪映工程已复制到5.9草稿目录）
```

## 六、性能基准（RTX 3080 12GB）

### 混元I2V

| 帧数 | 时长 | 预估时间 | 显存峰值 | 质量 | 用途 |
|------|------|----------|----------|------|------|
| 13 | 0.54s | 5分钟 | 8GB | 低 | 快速预览 |
| 25 | 1.04s | 9分钟 | 9.5GB | 中 | 短视频片段 |
| **49** | **2.04s** | **17分钟** | **11GB** | **高** | **正式交付（推荐）** |
| 81 | 3.38s | 30分钟 | 11.8GB | 极高 | 长镜头（接近上限） |

### 文生图

| 模型 | 步数 | 时间 | 用途 |
|------|------|------|------|
| Lightning 4S | 4 | 12秒 | 开发测试参考图 |
| SDXL | 20 | 30秒 | 高质量交付参考图 |

### 帧率策略

| 模式 | 帧率 | 用途 |
|------|------|------|
| test | 24fps | 开发测试，节省时间 |
| delivery | 48fps | 正式交付，流畅度更高 |

## 七、常见问题

### Q: ComfyUI启动失败？
A: 必须用绘世启动器（`D:\Ai\ComfyUI-aki-v3.2\绘世启动器.exe`）启动，不能直接运行python main.py。

### Q: 剪映工程打开后素材丢失？
A: jianying-editor创建的工程默认在C盘AppData，必须复制到D盘5.9草稿目录（`D:\JianyingProDrafts\JianyingPro Drafts\`）才能在5.9中打开。系统已自动处理。

### Q: I2V生成超时？
A: 49帧/2秒在RTX 3080上需要约17分钟，确保timeout设置为1800秒（30分钟）。系统已默认设置。

### Q: 显存不足（OOM）？
A: 确保low_vram=True（fp8量化+TiledVAE），720x1280是12GB显存的最佳分辨率。不要尝试1080x1920。

### Q: 生成完后显存还占用着？
A: 系统已集成资源自动清理（ResourceManager），脚本执行完会自动调用ComfyUI free API卸载模型。也可以手动调用：
```python
from core.resource_manager import ResourceManager
rm = ResourceManager()
rm.free_comfyui_models()
```

### Q: 同时运行两个剪映实例？
A: 不行。5.9版本不能同时运行两个实例，会导致工程损坏。

### Q: 蒙版关键帧不生效？
A: 剪映5.9中蒙版位置属性名是`KFTypeMaskPostionX/Y`（注意Postion拼写错误，少一个i），系统已正确处理。

## 八、项目结构

```
ai-video-editor/
├── easy_video.py              # 一键式入口（推荐使用）
├── core/
│   ├── resource_manager.py    # 资源管理与自动清理
│   ├── unified_api.py         # 四姊妹项目统一API
│   ├── config.py              # 配置管理
│   └── environment.py         # 环境检测
├── capabilities/
│   └── cap_creative/
│       ├── dual_mode_pipeline.py    # 双模式Pipeline
│       ├── movie_storyboard.py      # 电影模式分镜引擎
│       ├── hunyuan_i2v_runner.py    # 混元I2V运行器
│       ├── short_video_composer.py  # 短视频合成器
│       ├── real_bgm_generator.py    # 真实BGM生成器
│       ├── sound_engine.py          # 声音引擎
│       └── tag_engine.py            # 标签引擎
├── scripts/
│   ├── mask_keyframe.py       # 蒙版关键帧工具
│   ├── camera_moves.py        # 运镜预设库
│   ├── auto_beat.py           # 自动卡点
│   ├── effect_library.py      # 特效库调用器
│   └── ...（25+种特效脚本）
└── user_outputs/              # 用户输出目录
```

## 九、下一步

- 查看 `dev_workbench/` 开发工作台（http://localhost:8000）
- 阅读 `references/` 中的教程和参考文档
- 尝试用 `easy_video.py` 生成你的第一个视频
- 查看 `p19_4_benchmark/performance_benchmark.json` 详细性能数据
