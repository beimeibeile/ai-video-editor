# 导演工作台 (Director Workbench)

可视化任务配置面板，用户在前端配置参数，智能体后台执行剪辑任务。

## 架构

```
用户交互层          任务桥接层           执行层
┌──────────┐      ┌──────────┐      ┌──────────────┐
│ index.html│ ───→ │ task.json│ ───→ │ task_runner  │
│ (浏览器)  │      │ (JSON)   │      │ (Python)     │
└──────────┘      └──────────┘      └──────────────┘
     ↑                                    │
     └──────── 结果回写 ──────────────────┘
```

## 使用方法

### 1. 打开工作台
```bash
# 直接在浏览器中打开
start workbench/index.html
```

### 2. 配置任务
- 选择特效（左侧特效库）
- 上传素材（图片/视频）
- 配置参数（比例/片头/字幕/转场）
- 点击"生成任务" → 下载 `task.json`

### 3. 提交任务
将 `task.json` 放入 `workbench/tasks/` 目录

### 4. 执行任务
```bash
# 单次执行所有待处理任务
python workbench/task_runner.py --once

# 持续轮询（后台运行）
python workbench/task_runner.py --interval 5

# 执行指定任务
python workbench/task_runner.py --task tasks/task_xxx.json
```

### 5. 查看结果
执行完成后生成 `task_xxx_result.json`，包含工程名和执行状态。

## 功能模块

### 特效库浏览器
- 对接 `effects/showcase/index.json`
- 显示特效名称/分类/还原度/集成状态
- 点击选择特效

### 素材管理
- 支持图片/视频上传
- 素材列表展示/删除
- （需用户提供素材绝对路径供执行器使用）

### 参数配置
- 工程名称
- 视频比例（9:16/16:9/1:1/4:3）
- 片头风格（5种模板）
- 主标题/副标题
- 字幕样式（6种）
- 转场效果

### 时间线预览
- 可视化分镜片段
- 片头/正片/结尾时间分配

## 任务JSON格式

```json
{
  "task_id": "task_1234567890",
  "created_at": "2026-09-30T12:00:00",
  "status": "pending",
  "config": {
    "project_name": "我的视频",
    "width": 1080,
    "height": 1920,
    "ratio": "9:16",
    "intro_style": "flash_title",
    "main_title": "主标题",
    "sub_title": "副标题",
    "subtitle_style": "pill_cyber",
    "transition_style": "叠化",
    "selected_effect": "intro_builder"
  },
  "materials": ["img1.jpg", "video1.mp4"],
  "result": {
    "project_name": "我的视频",
    "intro_duration": 3.0
  }
}
```

## 后续优化方向

1. **实时预览**：集成视频预览，播放生成结果
2. **分镜编辑器**：可视化拖拽分镜，调整时长/顺序
3. **特效参数微调**：每个特效的详细参数面板
4. **素材库对接**：直接从素材库索引选择素材
5. **进度实时推送**：WebSocket实时更新执行进度
6. **历史任务管理**：任务列表/重新执行/收藏
7. **模板保存**：保存常用配置为模板一键复用
