# 人物介绍卡片特效

## 基本信息

| 字段 | 内容 |
|------|------|
| 特效ID | character_intro |
| 分类 | combo（组合特效） |
| 来源 | 抖音教程 - 狂飙人物介绍（未分类教程13435214622783193） |
| 教程时长 | 14.4秒 |
| 还原度 | ⭐⭐⭐ 基本还原 |
| 状态 | ✅ 已验证 |

## 原始教程核心手法

1. 红色渐变背景（上红下黑）
2. 人物照片带白色边框，垂直排列
3. 人物依次入场，带3D倾斜/旋转效果
4. 名字文字在人物下方，颜色区分（红/黄/绿）
5. 底部有LANG Y logo
6. 入场节奏错开，形成名单滚动效果

## 封装实现方案

**API限制**：剪映API不支持真正的3D倾斜/透视变换

**降级方案**：用2D旋转+缩放+位移模拟3D效果
- Pillow预生成带边框的人物肖像
- 渐变背景（Pillow生成）
- 入场动画：缩放0→1 + 位移入场 + 旋转回正 + 淡入
- 4个入场方向错开（up/down/left/right）
- 名字文字带颜色区分+黑色描边

## 可用预设（4种）

| 预设 | 背景 | 边框 | 名字颜色 | 适用场景 |
|------|------|------|----------|----------|
| red_drama | 红黑渐变 | 白色 | 红/黄/绿 | 影视、悬疑、角色介绍 |
| cyber_tech | 深蓝黑 | 青色 | 青/品红/黄 | 科技、游戏、战队 |
| warm_friends | 棕橙渐变 | 米白 | 橙/米/绿 | 生活、友情、团队 |
| minimal_white | 灰白渐变 | 深灰 | 灰阶 | 商务、访谈、极简 |

## 自定义参数

- `characters` - 人物列表，每项含 image/name/subtitle
- `preset` - 预设名称
- `stagger` - 入场时间差（秒）
- `card_duration` - 每张卡片持续时长
- `card_width/height` - 卡片尺寸比例
- `name_size` - 名字字号

## API接口

```python
from character_intro import create_character_intro

result = create_character_intro(
    project_name="CharacterIntro",
    characters=[
        {"image": "person1.jpg", "name": "张三", "subtitle": "主角"},
        {"image": "person2.jpg", "name": "李四", "subtitle": "反派"},
        {"image": "person3.jpg", "name": "王五", "subtitle": "配角"},
    ],
    preset="red_drama",
    width=1080, height=1920,
)
```

## 测试工程

- `CharacterIntro_Test` - 3人物红色剧情风格测试

## 已知限制

1. 3D倾斜用2D旋转模拟，缺少真正的透视变换
2. 人物照片需要用户提供（暂不支持AI生成）
3. 底部logo未实现（可手动添加）
4. 卡片退出动画未实现

## 后续优化方向

- 支持AI生成人物肖像（ComfyUI集成）
- 支持更多入场动画（翻转、弹跳、旋转入场）
- 支持卡片退出动画
- 支持自定义logo
- 支持水平排列布局
