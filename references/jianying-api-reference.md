# jianying-editor API 速查 + 常见坑

## 环境初始化（每个脚本开头必须）

```python
import os, sys

# 探测 jianying-editor skill 路径
skill_root = next((p for p in [
    os.getenv("JY_SKILL_ROOT", "").strip(),
    r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor",
    r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor",
] if p and os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py"))), None)

if not skill_root:
    raise ImportError("Could not find jianying-editor skill root.")

sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject, draft
```

## 核心 API

### 创建工程
```python
project = JyProject("项目名", width=1080, height=1920, overwrite=True)
```
- 竖屏9:16：width=1080, height=1920
- 横屏16:9：width=1920, height=1080
- 方形1:1：width=1080, height=1080

### 导入素材
```python
seg = project.add_media_safe(
    media_path,        # 本地绝对路径
    start_time="0s",   # 起始时间，支持"2.5s"/"00:00:02.500"
    duration="3s",     # 持续时长
    track_name="VideoTrack"  # 轨道名
)
```
- 返回 VideoSegment 对象，保存引用用于转场
- 视频会自动预处理（normalize），图片直接导入
- 素材会自动复制进草稿目录（自包含）

### 自动转场
```python
project.add_transition_simple(
    "叠化",                    # 转场名
    video_segment=seg,        # 后一个片段的segment
    duration="0.4s"           # 转场时长
)
```
- 必须传入 video_segment（后一个片段）
- 支持的转场枚举见 pyJianYingDraft.TransitionType
- 常见：叠化、淡入、淡出、闪黑、闪白

### 旁白 TTS
```python
project.add_tts_intelligent(
    text="旁白文案",
    speaker="zh_female_xiaopengyou",  # 音色
    start_time="0.5s",
    track_name="Narration"
)
```
- 常见音色：zh_female_xiaopengyou（少女）、zh_male_huajian（花间男声）
- 自动生成音频并导入对应轨道

### BGM 云端音乐
```python
project.add_cloud_music(
    query="国风",          # 搜索关键词
    start_time="0s",
    duration="15s",
    track_name="BGM"
)
```
- 搜索剪映云端音乐库
- 失败时标注"手动补BGM"

### 音效
```python
project.add_cloud_media(
    query="鼓点",
    start_time="2.5s",
    duration="0.5s",
    track_name="SFX"
)
```
- 全片≤6个音效
- 只在4类关键位置：转场/重鼓/定格/氛围

### 字幕
```python
project.add_text_simple(
    text="字幕内容",
    start_time="0.3s",
    duration="2s",
    clip_settings=draft.ClipSettings(transform_y=-0.7),  # 位置
    font_size=10.0,
    color_rgb=(1, 1, 1)  # 白色
)
```
- transform_y：-1.0（底部）到 1.0（顶部），-0.7 偏下
- font_size：相对值，10.0 约等于常规大小
- color_rgb：(R, G, B)，范围 0~1

### 贴纸
```python
project.add_cloud_media(
    query="手机框",
    start_time="0s",
    duration="10s",
    track_name="Sticker"
)
```
- 全片≤3个贴纸，谨慎使用
- 多数精美贴纸是VIP，免费贴纸样式有限

### 保存
```python
project.save()
```

### 画中画（PIP）
```python
seg = project.add_media_safe(
    path, start_time, duration,
    track_name="PIP_Track"  # 自定义轨道名即画中画
)
```
- 画中画的 clip_settings（缩放/位置）不会自动写入
- 需直接修改 draft_info.json 注入 scale/transform

## 关键帧运镜（手动或直接改JSON）

jianying-editor 的关键帧API不完善，建议：
- 简单缩放关键帧：直接修改 draft_info.json 的 clip_settings
- 复杂运镜：标注"剪映里手动加关键帧"

≥2秒静态图加缩放 1.0→1.15，0.5秒快切不加。

## 自动导出

```bash
python <jianying-editor>/scripts/auto_exporter.py "工程名" "output.mp4" --res 1080 --fps 60
```
- 仅支持 Windows
- 需剪映处于打开状态
- 失败时提示用户剪映手动导出，**不做ffmpeg兜底**

## 草稿验证

```bash
# 列出所有草稿
python <jianying-editor>/scripts/draft_inspector.py list --limit 20

# 查看工程摘要
python <jianying-editor>/scripts/draft_inspector.py summary --name "工程名"

# 查看详细内容（JSON）
python <jianying-editor>/scripts/draft_inspector.py show --name "工程名" --kind content --json
```

## 🚨 必须修复的 Bug

### media_normalizer.py
文件：`jianying-editor/scripts/utils/media_normalizer.py` 第59行

**问题**：`width % 16 != 0` 过度严格，1080%16=8 导致竖屏视频被误判需要归一化，强制转成1920×1080横屏。

**修复**：改为 `width % 2 != 0`（H.264规范只要求偶数宽度）。

## 常见坑

| 坑 | 解决方案 |
|---|---|
| 视频导入后变小/有黑边 | 必须ffmpeg预处理为画布分辨率+H264+yuv420p+无音频 |
| 视频原音频混入 | 预处理时加 `-an` 去除音频 |
| 草稿无法打开 | 删除损坏草稿，用新工程名重建 |
| 画中画缩放不生效 | clip_settings需直接修改draft_info.json注入 |
| 音频导入失败 | 用mp3格式，aac格式可能返回None |
| 转场不生效 | add_transition_simple必须传入后一个片段的video_segment |
| 自动导出失败 | 需剪映打开状态；失败提示手动导出 |
| 贴纸大部分是VIP | 免费贴纸样式有限，标注手动换 |
| 脚本放错位置 | 业务脚本必须放项目根目录，禁止放skill目录 |

## 依赖安装

```bash
python -m pip install uiautomation edge-tts pymediainfo psutil requests websockets Pillow
```
必须用 `python -m pip`，不能直接用 `pip`。
