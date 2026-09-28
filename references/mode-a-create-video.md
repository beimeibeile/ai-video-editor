# 模式 A：制作视频 — 完整流程

## 阶段 0：发起任务，上传素材

- 用户上传图片/视频素材（支持混合，3~10个）
- 记录每个素材的本地绝对路径
- URL 素材先用 `curl -L -o` 下载到本地项目目录
- 输出素材清单表格：文件名/路径/类型/分辨率/时长

## 阶段 1：理解视频制作要求

必须向用户确认以下参数（用户已给出的跳过）：

| 参数 | 默认值 | 说明 |
|---|---|---|
| 主题 | 必填 | 视频主题/叙事线 |
| 风格 | 氛围感/高级感 | 视觉调性 |
| 目的/平台 | 抖音 | 影响比例和节奏 |
| 时长 | 15s | 15/20/30s |
| 比例 | 9:16 | 9:16/1:1/16:9 |
| 是否旁白 | 是 | 剪映TTS生成 |
| 是否升格 | 否 | 需image_to_video生成240fps片段 |
| 是否封面图 | 询问 | 需要时从视频抽帧+加标题 |

## 阶段 2：素材探查

### 2.1 逐张 Read 分析
- 人物一致性：脸型/发型/服装/肤色是否统一
- 色调：冷暖/明暗/饱和度
- 质量：清晰度/噪点/构图
- 叙事潜力：情绪/动作/场景

### 2.2 人脸一致性询问
多张 AI 生成图存在差异时，主动询问：
> "检测到素材中人物五官/身材有差异，是否需要以某张图为基准统一？（统一需额外image_to_video生成，不统一则直接使用）"

### 2.3 筛选剔除
- 模糊/严重瑕疵 → 剔除
- 高度重复（同场景同角度）→ 保留最佳1张
- 与主题无关 → 剔除

### 2.4 排序
按色彩递进/情绪起伏/叙事逻辑排列，输出排序理由。

## 阶段 3：方案设计、确认

### 3.1 节奏设计（快慢对比公式）
```
慢动作钩子(2.5s) → 快切爆发(2s, 0.5s×4) → 升格高潮(5s) → 缓推收尾(2.5s) → 黑场slogan(3s) = 15s
```
可伸缩：
- 20秒版：钩子3s + 快切3s + 升格6s + 收尾4s + 黑场4s
- 30秒版：加第二组镜头循环

### 3.2 分镜设计表

| 镜头# | 时间 | 时长 | 素材 | 景别 | 运镜 | 字幕 | 转场 | 音效 |
|---|---|---|---|---|---|---|---|---|
| 1 | 0-2.5s | 2.5s | img_01 | 特写 | 缓推 | "钩子文案" | 淡入 | 氛围音 |
| 2 | 2.5-3s | 0.5s | img_02 | 近景 | 固定 | 无 | 硬切 | 鼓点 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

景别：特写/近景/中景/全景/远景
运镜：固定/缓推/缓拉/左摇/右摇/上移/下移/旋转/升格

### 3.3 声音设计
- 旁白文案：完整台词，标注每句起止时间
- TTS音色：zh_female_xiaopengyou（默认）/ zh_male_huajian 等
- BGM关键词：国风/电子/抒情/摇滚等
- 音效点：转场音/重鼓/定格音/氛围音（≤6个）

### 3.4 确认门控
输出完整方案后必须等用户明确回复"确认/可以/开始"才能开工。

## 阶段 4：视图层资产准备

### 4.1 比例适配（强制）
```bash
# 检测分辨率
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 input.jpg

# 裁剪缩放至画布分辨率（9:16 → 1080×1920）
ffmpeg -i input.jpg -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" output.jpg
```
裁剪后必须 Read 验证构图（人物是否被裁掉关键部位）。

### 4.2 视频预处理（强制）
所有视频素材必须预处理：
```bash
ffmpeg -i input.mp4 \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
  -an -r 30 -c:v libx264 -pix_fmt yuv420p \
  output.mp4
```
关键点：画布分辨率 + H.264 + yuv420p + 30fps + **无音频**（-an）

### 4.3 图生视频动态化
- 普通动态片段：image_to_video，5秒，seedance_2.0_fast
- 升格慢动作：image_to_video，prompt强调"240fps super slow motion, backlight, tyndall effect, clothes flowing"
- 一次最多并行2个
- 生成前必须用户确认参数（时长/比例/prompt）

### 4.4 资产确认门控
视图层文件全部就绪 + 其他层文案确认后，进入合成阶段。

## 阶段 5：剪映合成（详见 jianying-api-reference.md）

## 阶段 6：验证与交付

### 6.1 技术验证
```bash
# 确认时长/分辨率/音视频流
ffprobe -v error -show_format -show_streams output.mp4

# 抽帧验证（至少3帧）
ffmpeg -ss 1 -i output.mp4 -frames:v 1 frame_hook.png
ffmpeg -ss 5 -i output.mp4 -frames:v 1 frame_quick.png
ffmpeg -ss 8 -i output.mp4 -frames:v 1 frame_climax.png
```

### 6.2 结构验证
```bash
python <jianying-editor>/scripts/draft_inspector.py summary --name "工程名"
```

### 6.3 交付
- present_files 交付 mp4
- 告知剪映工程路径（可继续编辑）
- 列出手动补充项（滤镜/特效/贴纸微调等）
