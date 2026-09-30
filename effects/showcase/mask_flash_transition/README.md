# 蒙版展开快闪特效

## 基本信息

| 字段 | 内容 |
|------|------|
| 特效ID | mask_flash_transition |
| 分类 | transitions（转场特效） |
| 来源 | 抖音教程 - 李华Liha |
| 教程时长 | 366秒 |
| 还原度 | ⭐⭐⭐ 基本还原 |
| 状态 | ✅ 已验证 |

## 原始教程核心手法

1. 多个纯色块分别放在不同画中画轨道
2. 每个色块添加矩形蒙版
3. 蒙版大小/位置关键帧动画，从0展开到全屏
4. 各轨道起始时间错开，形成依次展开效果
5. 配合快节奏BGM卡点

## 封装实现方案

**API限制**：pyJianYingDraft的KeyframeProperty不支持蒙版属性（position_x/y, rotation, scale_x/y, uniform_scale, alpha, saturation, contrast, brightness, volume）

**降级方案**：用scale+transform关键帧模拟蒙版展开效果
- 色块从0缩放到1（模拟展开）
- position_x/y位移（模拟方向展开）
- alpha淡入淡出

## 可用参数

### 展开方向（7种）
- `left` - 从左展开
- `right` - 从右展开
- `top` - 从上展开
- `bottom` - 从下展开
- `center` - 中心扩散
- `horizontal` - 水平双向展开
- `vertical` - 垂直双向展开

### 配色预设（6种）
- `cyberpunk` - 赛博朋克（青/紫/粉）
- `warm` - 温暖（橙/红/黄）
- `cool` - 冷色（蓝/青/绿）
- `mono` - 单色（黑白灰）
- `neon` - 霓虹（高饱和）
- `pastel` - 柔和（低饱和）

## API接口

```python
from mask_flash_transition import create_mask_flash_basic, create_stripe_flash

# 基础快闪
create_mask_flash_basic(
    project_name="MyFlash",
    colors=[(0,200,255), (255,0,200), (200,255,0)],
    direction="center",
    width=1080, height=1920,
)

# 条纹快闪
create_stripe_flash(
    project_name="StripeFlash",
    stripe_count=5,
    color_preset="neon",
)
```

## 测试工程

- `MaskFlash_Cyberpunk` - 赛博朋克配色，中心展开
- `StripeFlash_Neon` - 霓虹条纹快闪

## 已知限制

1. 真正的蒙版关键帧动画未实现（API不支持），用缩放模拟
2. 进阶版复合片段+线性蒙版旋转未实现
3. 贝塞尔曲线蒙版未实现

## 后续优化方向

- 逆向draft_content.json中蒙版关键帧格式
- 支持自定义蒙版形状（圆形/线性/镜面）
- 支持贝塞尔曲线缓动
