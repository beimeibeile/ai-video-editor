# ai-video-editor 独立能力边界 v1.0

## 架构定位

ai-video-editor 是**综合智能视频编辑技能**，具备两层能力：

### 第一层：自身独立能力（无其他skill加持时可用）
| 能力模块 | 说明 | 依赖 |
|---------|------|------|
| 剧本理解引擎 | 情绪分析、节拍解析、角色提取 | 纯Python |
| 分镜设计器 | 镜头语言、画面构图、时长分配 | 纯Python |
| 情绪视觉映射 | 6种情绪→视觉参数映射 | 纯Python |
| 照片短视频生成器 | 4种风格预设，端到端出片 | 剪映适配层 |
| TTS配音执行器 | Qwen3-TTS via ComfyUI API | HTTP请求 |
| 多轨混音器 | 人声/BGM/闪避/标准化 | ffmpeg |
| 剪映工程构建器 | 多轨视频/文字/特效/动画 | **适配层** |
| 统一特效API | 2309种特效/972滤镜/130转场 | **适配层** |

### 第二层：通过宿主/其他skill获得的能力补全
| 能力 | 来源skill | 补全方式 |
|------|----------|---------|
| AI图像/视频生成 | comfyui-controls-skill | ComfyUI API |
| 3D特效/片头 | blender-controls-skill | Blender CLI |
| 透明背景动画 | remotion-controls-skill | Remotion CLI |
| 深度搜索/灵感 | anysearch-skill | AnySearch API |
| 剪映底层操作 | jianying-editor | **适配层封装** |

## 解耦策略

### 已完成
- ✅ `adapters/jianying_adapter.py` - 剪映适配层（封装pyJianYingDraft全部常用类）
- ✅ `scripts/jianying_executor.py` - 核心执行器已迁移到适配层
- ✅ 迁移脚本 `scripts/migrate_to_adapter.py` - 批量迁移工具

### 待迁移（30个文件）
运行 `python scripts/migrate_to_adapter.py --dry-run` 查看变更，
确认后运行 `python scripts/migrate_to_adapter.py` 执行迁移。

### 适配层使用规范
```python
# ✅ 正确：通过适配层访问
from adapters.jianying_adapter import VideoSegment, Timerange, IntroType

# ❌ 禁止：直接import pyJianYingDraft
from pyJianYingDraft.video_segment import VideoSegment
import pyJianYingDraft as draft
```

## 独立工作流程（无其他skill时）

1. 输入：自然语言描述/剧本/照片集
2. 剧本理解 → 情绪分析 → 分镜设计
3. 素材准备（用户提供/简单生成）
4. 剪映工程构建（适配层）
5. TTS配音（ComfyUI API，无需comfyui-skill）
6. 多轨混音（ffmpeg）
7. 输出：剪映草稿工程

## 能力增强路径

| 阶段 | 目标 | 依赖skill |
|------|------|----------|
| 当前 | 模板化快速出片 | 仅适配层 |
| 短期 | AI素材自动生成 | comfyui-controls-skill |
| 中期 | 3D特效/透明动画 | blender/remotion-controls-skill |
| 长期 | 全流程自动化 | 全部skill协同 |
