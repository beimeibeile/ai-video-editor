# AI Video Editor — 自学习累积型框架架构

> 版本：v3.0 | 设计原则：模块化、可插拔、自学习、素材复用、经验沉淀、环境自适应、开源友好

## v3.0 更新（开源准备）

新增三层基础框架，确保不同用户环境可自适应：

1. **配置管理层** (`core/config.py`)：统一管理API Key、路径等配置，优先级：环境变量 > .env文件 > 默认值，敏感信息不硬编码
2. **环境检测层** (`core/environment.py`)：启动时检测ComfyUI/剪映/AnySearch/ffmpeg/Python依赖，返回状态报告
3. **能力降级层** (`core/capability_loader.py`增强版)：每个能力模块声明依赖，不可用时自动降级或舍弃，提供降级方案提示

新增能力模块：
- `capabilities/cap_search/`：基于AnySearch的网络搜索能力（通用搜索/批量搜索/页面提取）

## 一、设计目标

1. **能力模块化**：每个剪辑能力独立封装，可单独加载、单独升级
2. **可插拔扩展**：新能力只需放入 `capabilities/` 目录，核心自动发现
3. **自学习机制**：每次任务的经验、教训、验证结果自动沉淀到知识库
4. **素材复用**：生成的可复用素材自动归档，避免重复生成
5. **知识检索**：知识库按领域分类，支持快速检索
6. **版本可追溯**：所有封板决策、已知问题、验证模式有记录
7. **环境自适应**：不同用户环境自动检测，能力不可用时降级或舍弃
8. **开源友好**：API Key等敏感信息不硬编码，通过.env和环境变量配置

## 二、目录结构

```
ai-video-editor/
├── SKILL.md                      # 主入口：模式识别 + 任务调度 + 全局规则
├── ARCHITECTURE.md               # 本文档：框架架构说明
├── core/                         # 核心层
│   ├── config.py                 # 配置管理（.env+环境变量，密钥不硬编码）
│   ├── environment.py            # 环境检测（ComfyUI/剪映/AnySearch/ffmpeg）
│   ├── task_router.py            # 任务路由器（模式识别→能力调度）
│   ├── capability_loader.py      # 能力模块加载器（依赖声明+降级策略）
│   └── knowledge_manager.py      # 知识管理器（读写经验/案例/决策）
├── .env.example                  # 配置模板（不含真实密钥，开源用）
├── .gitignore                    # Git忽略规则
├── capabilities/                 # 能力模块层（可插拔，每个模块独立）
│   ├── cap_material_creator/     # 🟢 制作素材（已实现）
│   │   ├── SKILL.md              # 模块说明 + 触发条件 + API
│   │   ├── outline_generator.py  # 轮廓图生成（黑底白边）
│   │   ├── texture_generator.py  # 纹理图生成（渐变/流体/火焰/赛博）
│   │   ├── blend_compositor.py   # 混合模式合成（正片叠底等）
│   │   ├── placeholder_generator.py  # 占位图生成（数字/纯色）
│   │   └── background_generator.py   # 背景图生成
│   ├── cap_video_analyzer/       # 🟡 视频分析（待迁移）
│   ├── cap_subtitle_designer/    # 🟡 字幕设计（待迁移 artistic_subtitle.py）
│   ├── cap_effect_library/       # ⚪ 特效库（待实现）
│   ├── cap_keyframe_engine/      # ⚪ 关键帧引擎（待实现）
│   └── cap_audio_designer/       # ⚪ 音频设计（待实现）
├── knowledge/                    # 知识管理层（自学习核心）
│   ├── jianying/                 # 剪映领域知识
│   │   ├── api_reference.md      # API速查
│   │   ├── gui_operations.md     # GUI操作SOP
│   │   └── version_compatibility.md  # 版本兼容性
│   ├── editing/                  # 剪辑技巧知识
│   │   ├── transitions.md        # 转场技巧
│   │   ├── keyframes.md          # 关键帧技巧
│   │   └── color_grading.md      # 调色技巧
│   ├── cases/                    # 案例库（每次任务归档）
│   │   └── case_index.md         # 案例索引
│   └── lessons/                  # 经验教训（自学习沉淀）
│       ├── verified_patterns.md  # 验证过的模式（✅可复用）
│       ├── known_issues.md       # 已知问题（❌避坑）
│       └── decision_log.md       # 封板决策日志
├── assets/                       # 素材资产层
│   ├── reusable/                 # 可复用素材（自动归档）
│   │   ├── placeholders/         # 占位图（0~30号，9:16/16:9）
│   │   ├── textures/             # 纹理图（彩虹/火焰/赛博等）
│   │   ├── outlines/             # 轮廓图模板
│   │   └── backgrounds/          # 背景图
│   └── templates/                # 工程模板
├── utils/                        # 工具函数层
│   ├── common.py                 # 通用工具（路径/时间/日志）
│   ├── ffmpeg_helper.py          # ffmpeg封装
│   ├── image_helper.py           # 图像处理（裁剪/缩放/合成）
│   └── json_helper.py            # JSON操作（读写草稿）
├── references/                   # 参考文档（保留现有）
└── scripts/                      # 业务脚本（保留现有，逐步迁移到capabilities）
```

## 三、能力模块规范

每个能力模块必须包含：

| 文件 | 作用 | 必填 |
|---|---|---|
| `SKILL.md` | 模块说明：触发条件、输入输出、API、已知限制 | ✅ |
| `__init__.py` | 模块入口，导出核心函数 | ✅ |
| 代码文件 | 具体实现 | ✅ |

**模块触发方式**：
- **用户触发**：用户明确要求（如"制作发光轮廓素材"）
- **自主触发**：主流程在素材准备阶段判断需要某类素材时自动调用

**模块间通信**：通过文件系统传递（生成的素材存到临时目录，路径返回给主流程），不通过内存对象传递，保证模块独立性。

## 四、自学习机制

### 4.1 经验沉淀流程

每次任务完成后，主流程自动：
1. **记录验证过的模式** → `knowledge/lessons/verified_patterns.md`
2. **记录遇到的问题** → `knowledge/lessons/known_issues.md`
3. **记录封板决策** → `knowledge/lessons/decision_log.md`
4. **归档可复用素材** → `assets/reusable/` 对应子目录
5. **归档案例** → `knowledge/cases/`

### 4.2 知识检索

任务开始前，主流程自动检索：
- `known_issues.md`：避免重复踩坑
- `verified_patterns.md`：复用已验证方案
- `assets/reusable/`：优先使用已有素材

### 4.3 素材命名规范

```
{类型}_{描述}_{比例}.{ext}
例：placeholder_05_9x16.png
    texture_rainbow_16x9.png
    outline_circle_16x9.png
    background_dark_gradient_9x16.png
```

## 五、三模式与能力模块的关系

| 模式 | 调用的能力模块 |
|---|---|
| A 制作视频 | cap_material_creator（按需）→ cap_subtitle_designer → cap_keyframe_engine → cap_audio_designer |
| ⚡ 快剪视频 | 同上（免确认，AI自主决策） |
| B 仿制模板 | cap_video_analyzer → cap_material_creator（占位素材）→ cap_effect_library |

## 六、扩展新能力的步骤

1. 在 `capabilities/` 下创建 `cap_xxx/` 目录
2. 编写 `SKILL.md`（触发条件+API+限制）
3. 编写 `__init__.py` 和代码文件
4. 在 `SKILL.md` 主入口的能力模块表中登记
5. 在 `knowledge/lessons/decision_log.md` 记录新增决策

## 七、版本状态

| 模块 | 状态 | 说明 |
|---|---|---|
| cap_material_creator | 🟢 v1.0 | 轮廓图/纹理图/正片叠底/占位图/背景图 |
| cap_video_analyzer | 🟡 待迁移 | 现有 analyze_video.py |
| cap_subtitle_designer | 🟡 待迁移 | 现有 artistic_subtitle.py |
| cap_effect_library | ⚪ 待实现 | 特效名称映射+自动添加 |
| cap_keyframe_engine | ⚪ 待实现 | Ken Burns/运镜预设 |
| cap_audio_designer | ⚪ 待实现 | BGM匹配/TTS旁白 |


## 八、环境自适应与能力降级（v3.0新增）

### 8.1 配置管理

所有敏感信息和环境相关配置通过 `core/config.py` 统一管理：
- 优先级：环境变量 > `.env`文件 > 默认值
- API Key不硬编码，从 `ANYSEARCH_API_KEY` 等环境变量读取
- 开源部署时只需复制 `.env.example` 为 `.env` 并填入实际值

### 8.2 环境检测

启动时 `core/environment.py` 自动检测：
| 环境模块 | 检测内容 | 不可用时的影响 |
|---|---|---|
| ComfyUI | API端口可访问 | 跳过超分/抠图/人脸统一/三视图/文生图 |
| 剪映 | 安装路径存在 | 只输出方案和素材，不生成剪映草稿 |
| AnySearch | API Key有效 | 跳过网络搜索，使用内置知识 |
| FFmpeg | 命令在PATH中 | 跳过视频转码/音频提取 |
| Python依赖 | requests/PIL可用 | 影响所有需要图像处理的模块 |

### 8.3 能力降级策略

每个能力模块在 `capability_loader.py` 中声明依赖：
```python
CAPABILITY_DEPENDENCIES = {
    "cap_comfyui_runner": ["comfyui", "python_deps"],
    "cap_search": ["anysearch", "python_deps"],
    ...
}
```

模块状态：
- **available**：所有依赖满足，正常使用
- **degraded**：部分依赖缺失，有降级方案，可有限使用
- **unavailable**：关键依赖缺失，功能不可用

降级方案示例：
- ComfyUI不可用 → 不超分/不抠图，使用原始素材
- 剪映不可用 → 只输出分镜方案和素材清单
- AnySearch不可用 → 跳过网络搜索，使用用户提供的信息

## 九、开源部署指南

### 9.1 快速开始

```bash
# 1. 克隆项目
git clone <repo-url>
cd ai-video-editor

# 2. 配置环境
cp .env.example .env
# 编辑.env，填入API Key和路径

# 3. 安装依赖
pip install requests pillow numpy

# 4. 验证环境
python -c "from core.environment import env; print(env.get_summary())"
```

### 9.2 必需 vs 可选环境

| 组件 | 必需 | 说明 |
|---|---|---|
| Python 3.10+ | ✅ | 运行环境 |
| requests, PIL | ✅ | 基础依赖 |
| 剪映5.9 | ⚠️ 可选 | 不安装则只输出方案 |
| ComfyUI | ⚠️ 可选 | 不安装则跳过高算力功能 |
| AnySearch API Key | ⚠️ 可选 | 不配置则跳过网络搜索 |
| FFmpeg | ⚠️ 可选 | 不安装则跳过视频转码 |

### 9.3 安全注意事项

- `.env` 文件包含API Key，已在 `.gitignore` 中排除，不要提交
- 所有路径配置支持相对路径和环境变量
- 开源前确认没有硬编码的密钥或个人路径