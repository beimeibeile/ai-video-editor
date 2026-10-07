# 剪映特效效果速查表 v1.0

> 基于pyJianYingDraft元数据逆向工程生成，覆盖1779个有参数的特效。
> 生成时间: 2026-10-08

## 一、特效总览

| 分类 | 数量 | 说明 |
|------|------|------|
| 视频场景特效 | 985 | 有可调参数 |
| 滤镜 | 489 | 有可调参数 |
| 视频人物特效 | 213 | 有可调参数 |
| 音频场景特效 | 85 | 有可调参数 |
| 音色特效 | 7 | 有可调参数 |
| **合计** | **1779** | |

## 二、核心参数说明

| 参数名 | 中文含义 | 使用频率 | 范围 | 说明 |
|--------|----------|----------|------|------|
| effects_adjust_speed | 速度 | 868次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_filter | 滤镜强度 | 816次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_size | 大小 | 343次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_background_animation | 背景动画 | 320次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_intensity | 强度 | 305次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_color | 颜色 | 231次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_blur | 模糊 | 191次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_luminance | 亮度 | 180次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_vertical_shift | effects_adjust_vertical_shift | 144次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_range | 范围 | 143次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_texture | 纹理 | 107次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_horizontal_shift | effects_adjust_horizontal_shift | 99次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_number | effects_adjust_number | 81次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_distortion | 扭曲 | 80次 | 0-1 | 0-100输入映射到0-1 |
| effects_adjust_rotate | effects_adjust_rotate | 69次 | 0-1 | 0-100输入映射到0-1 |

**参数使用注意**: API传入范围是0-100，parse_params会自动映射到特效定义的min-max范围（通常0-1）。

## 三、按情绪/场景推荐特效

### 激昂/高能

- **推荐特效**: 动感放大, 震动, 闪白, RGB描边, X-Signal, 彩噪画质
- **参数建议**: 速度>0.7, 强度>0.6, 滤镜强度>0.5
- **适用场景**: 高潮、转场、产品展示

### 舒缓/文艺

- **推荐特效**: 模糊聚焦, 丁达尔旋焦, 梦幻辉光, 柔焦, VCR, 90s画质
- **参数建议**: 速度<0.4, 模糊>0.5, 亮度>0.6
- **适用场景**: 回忆、慢镜头、情感表达

### 紧张/悬疑

- **推荐特效**: CCD闪光, DV录制框, betamax, JVC, 晃动抽帧, 老电视
- **参数建议**: 速度0.3-0.5, 噪点>0.5, 滤镜强度>0.6
- **适用场景**: 悬疑、恐怖、纪实

### 温馨/治愈

- **推荐特效**: 柔光, 暖色调, 爱心扫光, 泡泡光斑, 梦幻辉光
- **参数建议**: 亮度>0.6, 颜色偏暖, 强度0.4-0.6
- **适用场景**: 生活记录、宠物、亲子

### 复古/怀旧

- **推荐特效**: VCR, DV录制框, betamax, JVC, 90s画质, 70s, 1998
- **参数建议**: 滤镜强度>0.7, 锐化>0.5, 色差>0.4
- **适用场景**: 回忆、复古风格、年代感

### 科技/未来

- **推荐特效**: RGB描边, X-Signal, X开幕, 全息, 赛博朋克, 动态侦测
- **参数建议**: 速度>0.6, 色差>0.5, 强度>0.5
- **适用场景**: 科技产品、未来感、游戏

### 搞笑/搞怪

- **推荐特效**: 大头, 变形, 镜像, 哈哈镜, 抖动, 震动
- **参数建议**: 扭曲>0.6, 大小变化, 速度>0.5
- **适用场景**: 搞笑视频、表情包、娱乐

### 美食/诱人

- **推荐特效**: 美食增强, 暖色调, 高光, 柔焦, 丁达尔
- **参数建议**: 饱和度>0.6, 亮度>0.5, 锐化>0.4
- **适用场景**: 美食探店、烹饪、吃播

## 四、常用特效TOP50（按参数丰富度排序）

| # | 特效名称 | 分类 | 参数数 | 核心参数 |
|---|----------|------|--------|----------|
| 1 | 动态侦测 | 视频场景特效 | 9 | 速度, effects_adjust_number, 颜色 |
| 2 | 圆形监控 | 视频场景特效 | 9 | 强度, 大小, 噪点 |
| 3 | 泡泡光斑 | 视频场景特效 | 9 | 大小, effects_adjust_number, 速度 |
| 4 | 单色涂鸦 | 视频场景特效 | 8 | 颜色, 滤镜强度, effects_adjust_number |
| 5 | Ins描边 | 视频场景特效 | 8 | 颜色, 强度, 水平色差 |
| 6 | 动感竖线 | 视频场景特效 | 8 | 扭曲, 速度, 范围 |
| 7 | 变色闪光 | 视频场景特效 | 8 | 范围, 大小, 颜色 |
| 8 | 折叠拜年 | 视频场景特效 | 8 | effects_adjust_horizontal_shift, effects_adjust_rotate, 扭曲 |
| 9 | 涂鸦vlog | 视频场景特效 | 8 | 范围, effects_adjust_number, 大小 |
| 10 | 爱心扫光 | 视频场景特效 | 8 | 亮度, effects_adjust_soft, effects_adjust_rotate |
| 11 | 彩噪画质 | 视频场景特效 | 7 | 强度, 速度, 大小 |
| 12 | 祝福环绕 | 视频场景特效 | 7 | 颜色, 大小, effects_adjust_horizontal_shift |
| 13 | 2024边框 | 视频场景特效 | 7 | 速度, 大小, effects_adjust_vertical_shift |
| 14 | 丁达尔旋焦 | 视频场景特效 | 7 | 纹理, 滤镜强度, 亮度 |
| 15 | 丝印涂鸦 | 视频场景特效 | 7 | 颜色, 强度, 大小 |
| 16 | 像素屏闪 | 视频场景特效 | 7 | 强度, 背景动画, 颜色 |
| 17 | 动感扫光 | 视频场景特效 | 7 | 强度, 速度, 大小 |
| 18 | 双重辉光 | 视频场景特效 | 7 | 范围, effects_adjust_horizontal_shift, 垂直色差 |
| 19 | 发光HDR | 视频场景特效 | 7 | 亮度, 范围, 大小 |
| 20 | 变速推镜 | 视频场景特效 | 7 | effects_adjust_horizontal_shift, effects_adjust_vertical_shift, 强度 |
| 21 | 复古拼贴 | 视频场景特效 | 7 | 速度, 滤镜强度, 纹理 |
| 22 | 局部推镜 | 视频场景特效 | 7 | 速度, 强度, 亮度 |
| 23 | 弯曲故障 | 视频场景特效 | 7 | 速度, 扭曲, 背景动画 |
| 24 | 彩色像素 | 视频场景特效 | 7 | 亮度, 模糊, 背景动画 |
| 25 | 彩色珠滴 | 视频场景特效 | 7 | effects_adjust_number, 模糊, 速度 |
| 26 | 恭喜发财 II | 视频场景特效 | 7 | 速度, effects_adjust_vertical_shift, effects_adjust_horizontal_shift |
| 27 | 新年仙女棒 | 视频场景特效 | 7 | 大小, effects_adjust_horizontal_shift, effects_adjust_vertical_shift |
| 28 | 新春海报 | 视频场景特效 | 7 | 速度, 滤镜强度, 大小 |
| 29 | 曲线模糊 | 视频场景特效 | 7 | 速度, 亮度, 强度 |
| 30 | 梦幻辉光 | 视频场景特效 | 7 | 亮度, 范围, 大小 |
| 31 | 欧根纱II | 视频场景特效 | 7 | 亮度, 强度, 范围 |
| 32 | 法式涂鸦 | 视频场景特效 | 7 | 颜色, 范围, 滤镜强度 |
| 33 | 泛光扫描 | 视频场景特效 | 7 | 强度, 亮度, 模糊 |
| 34 | 流体冲屏 | 视频场景特效 | 7 | 速度, 范围, 颜色 |
| 35 | 瀑布烟花 | 视频场景特效 | 7 | 大小, effects_adjust_horizontal_shift, effects_adjust_vertical_shift |
| 36 | 热恋 | 视频场景特效 | 7 | 大小, effects_adjust_number, effects_adjust_rotate |
| 37 | 电光波动 | 视频场景特效 | 7 | 速度, 范围, 亮度 |
| 38 | 画质清晰 | 视频场景特效 | 7 | 亮度, 滤镜强度, 锐化 |
| 39 | 竖向闪光 | 视频场景特效 | 7 | effects_adjust_number, 模糊, 强度 |
| 40 | 精致辉光 | 视频场景特效 | 7 | 亮度, 范围, 大小 |
| 41 | 紫光夜 | 视频场景特效 | 7 | effects_adjust_number, 颜色, 强度 |
| 42 | 色差震闪 | 视频场景特效 | 7 | 强度, 垂直色差, 模糊 |
| 43 | 边缘扫光 | 视频场景特效 | 7 | effects_adjust_soft, 亮度, 大小 |
| 44 | 雨滴 | 视频场景特效 | 7 | 大小, 纹理, 模糊 |
| 45 | 雨滴2 | 视频场景特效 | 7 | 大小, 纹理, 模糊 |
| 46 | 震动光束 | 视频场景特效 | 7 | 强度, 颜色, effects_adjust_vertical_shift |
| 47 | 霓虹光线 | 视频场景特效 | 7 | 亮度, 模糊, 强度 |
| 48 | 拼贴抽帧 | 视频人物特效 | 7 | 垂直色差, 水平色差, 大小 |
| 49 | 电光描边 II | 视频人物特效 | 7 | 亮度, 扭曲, 大小 |
| 50 | 迷幻分身 | 视频人物特效 | 7 | 速度, effects_adjust_number, 模糊 |

## 五、免费特效推荐（非VIP）

- **视频场景特效** (534个免费): 单色涂鸦, 彩噪画质, 祝福环绕, betamax, 圆形虚线放大镜, 波纹扭曲, 流动烟雾, 甜心投影, 箭头放大镜, 蔡国强烟花
- **视频人物特效** (138个免费): 拼贴抽帧, 圣诞小熊, 圣诞铃铛, 多屏圣诞树, 日系大头贴, 氛围大头贴, 流光描边, 人影爆闪, 分头行动, 分身
- **滤镜** (96个免费): 书意, 亮夏, 元气新年, 克洛伊, 冬日烧烤, 净白肤, 凛冬, 凝黛, 千金妝, 去黄增质
- **音频场景特效** (12个免费): 8bit, 回音, 环绕音, 颤音, 麦霸, 黑胶, 低保真, 合成器, 扩音器, 水下
- **音色特效** (7个免费): 大叔, 女生, 怪物, 男生, 花栗鼠, 萝莉, 机器人

## 六、API使用示例

```python
import pyJianYingDraft as draft
from pyJianYingDraft.metadata.video_scene_effect import VideoSceneEffectType
from pyJianYingDraft.time_util import Timerange, tim

# 创建工程
script = draft.ScriptFile(1080, 1920, 30, True)
script.add_track(draft.TrackType.effect, 'EffectTrack')

# 添加特效（默认参数）
script.add_effect(
    VideoSceneEffectType.CCD闪光,
    Timerange(tim('00:00:00'), tim('00:00:03')),
    track_name='EffectTrack',
)

# 添加特效（自定义参数，范围0-100）
script.add_effect(
    VideoSceneEffectType.VCR,
    Timerange(tim('00:00:00'), tim('00:00:05')),
    track_name='EffectTrack',
    params=[60, 70, 80, 50, 90],  # 速度,锐化,滤镜,水平色差,垂直色差
)

# 保存
script.save_path = 'path/to/draft_content.json'
script.save()
```

## 七、注意事项

1. **参数范围**: API传入0-100，内部映射到特效定义的min-max（通常0-1）
2. **参数顺序**: 必须按特效定义的参数顺序传入，可通过`effect.value.params`查看
3. **参数字段**: JSON中字段名为`adjust_params`，不是`effect_adjust_params`
4. **特效轨道**: 必须先创建`TrackType.effect`轨道才能添加特效
5. **VIP特效**: 部分特效需要VIP会员，`is_vip=True`标识
6. **转场/动画**: 转场和入场/出场/组合动画没有params定义，不支持参数调节
