# 已知问题（避坑指南）

> 每次任务遇到的问题自动记录于此，后续任务优先检查。

## jianying-editor API 限制

| 问题 | 根因 | 解决方案 | 状态 |
|---|---|---|---|
| 不支持混合模式(blend_mode) | ClipSettings无此字段，draft_info.json无相关字段 | Python预合成(multiply_blend) | ✅ 已解决 |
| add_styled_text()未实现 | 文档提及但代码缺失 | 用add_text_simple+TextBorder/TextBackground替代 | ⚠️ 待实现 |
| 云端音乐中文搜索失败 | asset_search不支持中文组合关键词 | 直接读CSV用Python搜索，用music_id | ✅ 已解决 |
| JyProject(overwrite=False)覆盖工程 | 不能加载已有工程，会创建空工程覆盖 | 必须一次性创建完整工程 | ✅ 已确认 |
| 转场给后一片段导致错位 | 转场应在前一片段结尾 | add_transition_simple(video_segment=前一片段) | ✅ 已解决 |
| 多特效同轨道重叠报错 | EffectTrack只能有一个同时段特效 | 用不同track_name(GlobalEffect等) | ✅ 已解决 |
| media_normalizer.py width%16过严 | H.264只要求偶数宽度 | 改为width%2 | ⚠️ 待修复 |

## 剪映版本兼容性

| 问题 | 版本 | 解决方案 |
|---|---|---|
| 多轨道只显示4轨 | 11.6 | 强制使用5.9 |
| 画中画位置调整不生效 | 11.6 | 强制使用5.9 |
| 特效无法添加(cu不支持拖拽) | 11.6 | 强制使用5.9 + PowerShell API |
| draft_content.json加密 | 11.6 | 5.9无此文件，用draft_info.json |
| 含BGM工程显示00:00 | 5.9 | BGM路径在豆包cloud_cache目录，5.9无法访问 |
| 5.9启动后弹出更新 | 5.9 | 立即关闭，禁止点更新 |

## GUI操作问题

| 问题 | 根因 | 解决方案 |
|---|---|---|
| 鼠标点击向左偏移 | 参考系混淆(UI坐标vs全屏坐标) | 窗口最大化，用实际屏幕分辨率计算 |
| 点错位置打开即梦页面 | 主轨道为空时进入即梦AI页面 | 工程必须有主轨道素材 |
| 点击"回到主页"刷新广告 | 主页刷新机制 | 用Ctrl+W关闭编辑标签页 |
| 鼠标未到位就点击 | 缺少延时 | 移动后加300-500ms延时再点击 |
| 草稿单击打不开 | 5.9需双击 | 双击打开草稿 |

## 素材处理

| 问题 | 根因 | 解决方案 |
|---|---|---|
| RGBA PNG不能save为JPEG | PIL不支持直接转换 | 先convert('RGB')再save |
| 旁白字幕轨道重叠 | 浮点除法2.75s→2.8s四舍五入 | 固定时长2.5s+间隔0.3s |
| add_text_simple空字符串创建片段 | main_text=""仍创建 | 判断if main_text才添加 |
| text_animations.csv是GBK编码 | Python默认utf-8解码报错 | 用errors='replace'或检测编码 |
| inspect.py与标准库冲突 | 文件名=inspect | 避免用标准库模块名命名脚本 |

## 复合片段(Compound Clip)支持情况

| 功能 | 支持状态 | 说明 |
|---|---|---|
| add_compound_project | ❌ 未实现 | compound_clip_demo.py用hasattr检查，不存在则回退普通overlay |
| CompoundSegment类 | ⚠️ 仅数据结构 | mocking_ops.py中有简单序列化类，未集成到JyProject |
| group_container字段 | ⚠️ 数据预留 | draft_info_template.json中有group_container: null |
| 剪映GUI复合片段 | ✅ 支持 | 选中多轨道→右键→创建复合片段，可整体加蒙版/特效/不透明度 |

**替代方案**：
- 需要复合片段效果时，用Python预合成带透明通道的PNG图片，导入剪映作为单图层
- 或在剪映GUI中手动选中多轨道→创建复合片段
