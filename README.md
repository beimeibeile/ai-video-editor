[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-Ready-FF9E0F?style=for-the-badge)](https://github.com/comfyanonymous/ComfyUI)
[![Jianying](https://img.shields.io/badge/剪映-5.9%2B-00D669?style=for-the-badge)]()
[![Blender](https://img.shields.io/badge/Blender-5.0%2B-F5792A?style=for-the-badge&logo=blender&logoColor=white)]()

# AI Video Editor

> **一句话，剪出专业视频。** AI 驱动的智能视频剪辑框架——把繁杂的手工剪辑操作变成自然语言指令。ComfyUI 算力 + 剪映工程合成 + Blender 3D 特效，全链路自动化。

## 为什么用它

| 痛点 | AI Video Editor 的解法 |
|------|----------------------|
| 剪辑软件操作复杂，学习成本高 | 一句话描述需求，自动完成分镜、剪辑、特效、字幕 |
| AI 生成素材分散，手动拼接费时 | ComfyUI 文生图/图生视频直接接入，素材到成品一条流水线 |
| 特效制作门槛高，模板千篇一律 | 14+ 自研特效库持续扩展，蒙版关键帧、混合模式、发光轮廓全部自动化 |
| 3D 特效需要专业软件 | Blender 后台渲染，粒子背景、光线扫描、3D 片头一键生成 |
| 质量不可控，返工频繁 | 双重质量门（分镜+剪辑），HTML 可视化报告，问题一目了然 |

## 核心能力

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Video Editor                          │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  三模式剪辑   │  ComfyUI 算力 │  剪映合成    │  Blender 3D   │
│  制作视频     │  文生图       │  多轨道时间线 │  3D片头       │
│  ⚡快剪视频   │  图生视频     │  转场字幕     │  粒子背景     │
│  仿制模板     │  批量抠图     │  14+特效库    │  光线扫描     │
│              │  人脸统一     │  蒙版关键帧   │  转场遮罩     │
├──────────────┴──────────────┴──────────────┴────────────────┤
│  智能极简操作  │  一句话指令 · 自动分镜 · 自动选特效 · 环境自适应  │
├─────────────────────────────────────────────────────────────┤
│  自我进化      │  教程自动消化 · 特效库扩展 · 质量门自动校验      │
└─────────────────────────────────────────────────────────────┘
```

## 三模式剪辑

| 模式 | 触发词 | 适用场景 |
|------|--------|---------|
| **A 制作视频** | 制作视频 / 给图剪视频 | 上传素材 → AI 分镜 → 资产准备 → 剪映工程合成 |
| **⚡ 快剪视频** | 快剪 / 快速剪辑 | 模式 A 免确认版，文字说明权重高于素材理解 |
| **B 仿制模板** | 仿制模板 / 复刻视频 | 分析参考视频 → 生成可发布的剪映模板草稿 |

## 特效库（14+ 持续扩展）

| 类别 | 特效 | 说明 |
|------|------|------|
| **转场** | 蒙版展开快闪 | 四色块从四角汇聚，蒙版关键帧驱动 |
| | 百叶窗分屏 | 4 方向分屏展开 |
| | Blender 转场 | 淡入/滑动/缩放/旋转 |
| **文字** | 羽化擦开 | 蒙版擦开，主文左→右，副文右→左 |
| | 背景块滑入 | 色块滑入 + 文字淡入 |
| | 文字排版艺术 | 5 种预设（竖排错落/横排标题/斜向层叠等） |
| | 半透明字幕条 | 3 种风格 |
| **视觉** | 动态发光轮廓 | 正片叠底 + 梦幻辉光 + 梦境 |
| | 混合模式 | 10 种已逆向（正片叠底/滤色/叠加等） |
| | 拍立得照片墙 | 散落堆叠入场 |
| | 多层图片堆叠 | 错落入场 |
| **3D** | Blender 片头 | 4 种风格（电影感/科技/简约/活力） |
| | 粒子背景 | 星空/雪花/光斑/烟花/霓虹 |
| | 光线扫描 | 高光扫过画面 |

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/beimeibeile/ai-video-editor.git
cd ai-video-editor

# 2. 配置
cp .env.example .env
# 编辑 .env，填入 API Key 和本地软件路径

# 3. 依赖
pip install requests pillow numpy

# 4. 验证
python -c "from core.environment import env; print(env.get_summary())"
```

然后在 AI 助手（豆包/Claude/Codex 等）中加载本 Skill，说一句：
> "帮我制作一个 30 秒的旅行 vlog，用我上传的 5 张照片，风格轻快，加字幕和 BGM"

## 环境要求

| 组件 | 必需 | 说明 |
|------|------|------|
| **Python 3.10+** | ✅ | 运行框架 |
| **剪映 5.9** | ⚡推荐 | 不安装则输出方案+素材，不生成剪映草稿 |
| **ComfyUI** | ⚡推荐 | 不安装则跳过高算力功能，使用原始素材 |
| **Blender 5.0+** | 可选 | 不安装则跳过 3D 特效，使用原生片头 |
| **FFmpeg** | 可选 | 视频转码/音频提取 |
| **AnySearch API Key** | 可选 | 热点文案/BGM 推荐/剪辑技巧检索 |

> **环境自适应**：缺少任何组件都会自动降级，不中断流程。首次运行自动检测并出具环境报告。

## 姊妹项目（航空母舰战斗群）

AI Video Editor 是战斗群的**指挥中枢（航母）**，与三个姊妹项目协同作战：

| 项目 | 角色 | 能力 |
|------|------|------|
| **[ai-video-editor](https://github.com/beimeibeile/ai-video-editor)** | 🚢 航母（指挥中枢） | 全流程剪辑、特效库、质量门、pipeline 编排 |
| **[Comfyui-controls-skill](https://github.com/beimeibeile/Comfyui-controls-skill)** | 🚀 导弹（AI 算力） | 工作流管理、模型进化、批量出图出视频 |
| **[Blender-controls-skill](https://github.com/beimeibeile/Blender-controls-skill)** | 💥 舰载机（3D 特效） | 场景管理、批量渲染、3D 特效库 |
| **[anysearch-skill](https://github.com/beimeibeile/anysearch-skill)** | 📡 雷达（情报搜索） | 23 垂类深度搜索、结构化输出、全文提取 |

**单体可独立工作，任意组合互相增强，聚齐即航空母舰。** 四个项目更新同步。

## 质量门

- **分镜质量门**：12 道检查（时长/节奏/字幕/转场/镜头连续性等），未通过不进入合成
- **剪辑质量门**：7 道检查（轨道/片段/字幕/转场/特效/时长/完整性），合成后自动校验
- **HTML 报告**：双击打开，✓/✗ 烘进页面，未过弹病灶横幅

## 项目结构

```
ai-video-editor/
├── capabilities/       # 可插拔能力模块
│   ├── cap_e2e_pipeline/   # 端到端流程
│   ├── cap_comfyui_runner/ # ComfyUI 算力
│   ├── cap_blender_runner/ # Blender 合成
│   ├── cap_env_checker/    # 环境检测
│   ├── cap_creative/       # 创意引擎 + 质量门
│   └── cap_asset_library/  # 素材库管理
├── scripts/            # 特效/片头/转场业务脚本
├── core/               # 配置、环境、任务路由
├── knowledge/          # 自学习知识库
├── workbench/          # 导演工作台（HTML 交互面板）
└── utils/              # 工具函数
```

## 边界（不做什么）

- 不替代剪映的精细手动调整——输出可编辑的剪映草稿，最终精修在剪映中完成
- 不做口型/唇形同步——属于视频生成模型的能力
- 不收费、不订阅——全部本地运行，API 费用自理

## License

[MIT](LICENSE)