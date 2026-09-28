# AI Video Editor

> AI短视频剪辑三模式+算力技能，自学习累积型智能剪辑框架

## 功能特性

### 三模式剪辑

| 模式 | 触发词 | 说明 |
|------|--------|------|
| **A 制作视频** | 制作视频/给图剪视频/百万剪辑师 | 上传素材→分镜设计→资产准备→剪映工程合成 |
| **⚡ 快剪视频** | 快剪视频/快速剪辑/直接剪 | 模式A免确认版，文字说明权重高于素材理解 |
| **B 仿制模板** | 仿制模板/复刻视频/照着这个做 | 分析参考视频→生成可发布的剪映模板草稿 |

### 算力能力（ComfyUI）

- 图片超分（RealESRGAN等9种模型）
- 批量抠图（BiRefNet/RMBG，RGBA透明）
- 人脸统一（ReActor，只换脸保留服装背景）
- 角色三视图（Qwen-Image-Edit，正面/侧面/背面）
- 极速文生图（Z-Image-Turbo，8秒/张）

### 搜索能力（AnySearch）

- 通用网页搜索、批量并行搜索、页面全文提取
- 用于热点文案、BGM推荐、原视频信息、剪辑技巧检索

### 素材制作能力

- 轮廓图生成（黑底白边，发光轮廓效果）
- 纹理图生成（渐变/流体/火焰/赛博）
- 占位图生成（数字/纯色，9:16/16:9）
- 字幕条背景生成（半透明文本框效果）
- 混合模式合成（正片叠底等）

## 环境要求

### 必需

- Python 3.10+
- requests, Pillow

### 可选（能力降级）

| 组件 | 不安装的影响 |
|------|-------------|
| 剪映5.9 | 只输出方案和素材，不生成剪映草稿 |
| ComfyUI | 跳过高算力功能，使用原始素材 |
| AnySearch API Key | 跳过网络搜索，使用内置知识 |
| FFmpeg | 跳过视频转码/音频提取 |

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/colrais/ai-video-editor.git
cd ai-video-editor

# 2. 配置环境
cp .env.example .env
# 编辑.env，填入API Key和路径

# 3. 安装依赖
pip install requests pillow numpy

# 4. 验证环境
python -c "from core.environment import env; print(env.get_summary())"
```

## 配置说明

复制 `.env.example` 为 `.env` 并配置：

```env
# AnySearch搜索API（可选）
ANYSEARCH_API_KEY=as_sk_xxxxxxxxxxxxxxxx
ANYSEARCH_API_ENDPOINT=https://api.anysearch.com

# ComfyUI（可选）
COMFYUI_ENABLED=true
COMFYUI_ADDRESS=127.0.0.1:8188

# 剪映（可选）
JIANYING_ENABLED=true
JIANYING_PATH=C:\path\to\JianyingPro.exe
JIANYING_VERSION=5.9
```

## 项目架构

```
ai-video-editor/
├── core/                         # 核心层
│   ├── config.py                 # 配置管理（.env+环境变量）
│   ├── environment.py            # 环境检测与能力降级
│   ├── task_router.py            # 任务路由器
│   ├── capability_loader.py      # 能力模块加载器
│   └── knowledge_manager.py      # 知识管理器
├── capabilities/                 # 能力模块（可插拔）
│   ├── cap_comfyui_runner/       # ComfyUI算力
│   ├── cap_material_creator/     # 素材制作
│   ├── cap_search/               # 网络搜索
│   ├── cap_video_analyzer/       # 视频分析
│   └── ...
├── knowledge/                    # 知识库（自学习）
├── assets/                       # 可复用素材
├── utils/                        # 工具函数
└── scripts/                      # 业务脚本
```

## 环境自适应

框架启动时自动检测环境，能力不可用时自动降级：

- **ComfyUI不可用** → 不超分/不抠图，使用原始素材
- **剪映不可用** → 只输出分镜方案和素材清单
- **AnySearch不可用** → 跳过网络搜索，使用用户提供的信息
- **FFmpeg不可用** → 跳过视频转码/音频提取

## 依赖

- [jianying-editor](https://github.com/) - 剪映Python API（JyProject）
- [computer-use-automation] - 剪映GUI自动化操作
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - 本地AI算力
- [AnySearch](https://www.anysearch.com) - 网络搜索API

## 许可证

MIT License
