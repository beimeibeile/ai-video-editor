# 片头生成器

## 基本信息

| 字段 | 内容 |
|------|------|
| 特效ID | intro_builder |
| 分类 | combo（组合特效） |
| 来源 | 特效组合（蒙版快闪+字幕条） |
| 还原度 | ⭐⭐⭐⭐⭐ 自主设计 |
| 状态 | ✅ 已验证 + 已集成pipeline |

## 设计思路

组合两个基础特效生成短视频片头：
1. **蒙版展开快闪** - 开场视觉冲击（色块依次展开）
2. **半透明字幕条** - 标题展示（渐变背景+文字）

适用于短视频开头2-4秒的钩子环节。

## 可用模板（5种）

| 模板 | 风格 | 时长 | 快闪色块 | 字幕条样式 | 适用场景 |
|------|------|------|----------|------------|----------|
| flash_title | 卡点炫酷 | 3.0s | 3色块 | pill_cyber | 通用短视频 |
| minimal_title | 治愈文艺 | 2.5s | 无 | rect_minimal | 文艺、生活 |
| warm_intro | 生活情感 | 3.0s | 3色块 | pill_warm | 情感、故事 |
| cyber_intro | 科技未来 | 3.5s | 4色块 | pill_cyber | 科技、游戏 |
| tag_intro | 短视频钩子 | 2.0s | 1色块 | tag_small | 快节奏、钩子 |

## API接口

```python
from intro_builder import create_intro, create_intro_batch, add_intro_to_project

# 创建独立片头工程
result = create_intro(
    template="cyber_intro",
    title="未来已来",
    subtitle="AI Video Editor",
    project_name="MyIntro",
)

# 批量创建
create_intro_batch([
    {"template": "flash_title", "title": "片头1"},
    {"template": "warm_intro", "title": "片头2"},
])

# 在已有工程中添加片头（模式A集成用）
intro_duration = add_intro_to_project(
    project,
    template="flash_title",
    title="精彩开始",
    start_time=0.0,
    width=1080, height=1920,
)
```

## Pipeline集成

已深度集成到E2EPipeline：
- `add_intro=True` 时自动使用特效库片头
- 风格自动映射：impact→flash_title, cute→warm_intro等
- 降级机制：特效库不可用时回退原生片头

## 测试工程

- `Intro_flash_title` - 快闪标题
- `Intro_minimal_title` - 极简标题
- `Intro_warm_intro` - 温暖开场
- `Intro_cyber_intro` - 赛博开场
- `Intro_tag_intro` - 标签开场
- `Intro_Integrate_Test` - 集成到已有工程测试

## 后续优化方向

- 更多片头模板（粒子、光效、3D文字）
- 支持自定义BGM和音效
- 片头时长自适应（根据正片总时长调整）
- 支持用户上传logo
