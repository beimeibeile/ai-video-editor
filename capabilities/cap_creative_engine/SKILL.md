# 创意引擎模块 (cap_creative_engine)

AI短视频剪辑的创意大脑，负责理解用户诉求、生成创意方向、设计专业分镜脚本。

## 核心能力

### 1. 诉求分析
- 自动识别主题（赛博朋克/国风/治愈/卡点/电影感/极简/复古）
- 检测平台（抖音/小红书/B站/视频号）
- 识别目的（分享/带货/教程/品牌宣传）
- 提取关键词

### 2. 热点搜索（AnySearch集成）
- 抖音/小红书热门话题搜索
- BGM推荐搜索
- 爆款文案参考
- 风格趋势和配色方案
- 基于热点生成钩子文案

### 3. 创意方向生成
- 每个任务生成3个创意方向：
  - 经典版：稳扎稳打，受众广泛
  - 节奏版：快节奏强化，适合算法推荐
  - 叙事版：情绪故事感，高级品质
- 每个方向包含：钩子、节奏、核心视觉、目标受众、情绪曲线、优缺点

### 4. 专业分镜脚本
每个镜头包含：
- **景别**：特写/近景/中景/全景/远景
- **运镜**：zoom_in/zoom_out/pan_left/pan_right/pan_up/pan_down/static
- **转场**：入点/出点转场类型
- **字幕**：内容+风格（epic/warm/fun/minimal/cinema）
- **音效**：关键词提示
- **素材建议**：根据景别和位置给出选择建议
- **调色**：单镜头+整体调色建议

### 5. 节奏模式
- **快切**：每个镜头0.7倍时长，视觉冲击强
- **舒缓**：每个镜头1.2倍时长，情绪铺垫
- **递进**：从慢到快，情绪升温
- **混合**：开篇/结尾稍长，中间紧凑

### 6. 改进建议
自动检查分镜脚本并给出优化建议：
- 节奏时长建议
- 景别变化检查
- 运镜多样性检查
- 字幕完整性检查
- 转场多样性检查

## 使用方法

```python
from capabilities.cap_creative_engine import CreativeEngine

# 初始化
engine = CreativeEngine(anysearch_api_key="your_api_key")  # API Key可选

# 完整流程
result = engine.full_pipeline(
    user_input="做一个赛博朋克风格的短视频",
    num_shots=6,
    output_dir="./output"
)

# 结果包含：
# - requirement: 诉求分析
# - directions: 3个创意方向
# - storyboard: 分镜脚本对象
# - suggestions: 改进建议
# - files: 生成的JSON和Markdown文件

# 单独生成分镜
storyboard = engine.generate_storyboard(
    theme="赛博朋克",
    num_shots=6,
    hook="未来都市｜赛博朋克"
)

# 导出
storyboard.save("storyboard.json", fmt="json")
storyboard.save("storyboard.md", fmt="md")
print(storyboard.to_markdown())
```

## 主题模板

内置7个主题模板，每个包含：
- 钩子文案模板（3个）
- 节奏模式
- 景别序列
- 运镜序列
- 转场序列
- 字幕风格
- BGM情绪
- 调色建议
- 音效提示

可用主题：赛博朋克、国风、治愈、卡点、电影感、极简、复古

## 文件结构

```
cap_creative_engine/
├── __init__.py          # 模块入口
├── creative_engine.py   # 创意引擎主类
├── storyboard.py        # 分镜脚本生成器（Shot/Storyboard数据类）
├── hot_trends.py        # 热点搜索器（AnySearch集成）
├── templates.py         # 创意模板库（7个主题）
└── SKILL.md             # 本文档
```

## 与easy_build集成

easy_build.py已集成创意引擎，自动完成：
1. 解析用户指定的主题
2. 生成专业分镜脚本
3. 根据分镜脚本导入素材、添加运镜、转场、字幕
4. 输出剪映工程

## 依赖

- 可选：AnySearch API（用于热点搜索，未配置时自动跳过）
- 无强制外部依赖
