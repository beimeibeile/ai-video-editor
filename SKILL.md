---
name: ai-video-editor
description: "AI短视频剪辑三模式+算力技能。模式A「制作视频」：用户上传图片/视频素材，AI完成分镜设计、资产准备、剪映工程合成（旁白TTS、BGM、字幕、转场、贴纸、关键帧），输出剪映草稿+可选mp4。触发词：制作视频、给图剪视频、用剪映剪辑、百万剪辑师、卡点变装、氛围感短片、旗袍视频。极速模式「快剪视频」：模式A免确认版，用户说快剪视频+上传素材，AI跳过方案确认直接开工，文字说明权重高于素材理解，优先按文字要求生成方案再用素材优化。触发词：快剪视频、快速剪辑、直接剪、不用确认。模式B「仿制模板」：用户上传参考视频，AI逆向分析镜头结构/运镜/特效/转场/多轨道叠加关系/字幕/音轨，生成可发布到剪映平台的模板草稿——原始素材（图片/视频/音频/贴纸）放轨道，所有特效/转场/滤镜/关键帧/蒙版在剪映工程内通过GUI实现，用户标记可替换素材后发布为模板，其他用户替换简单素材即得同款效果。触发词：仿制模板、复刻视频、照着这个做、模仿这个视频、模板替换、剪映模板。算力模式「ComfyUI」：操作本地ComfyUI执行批量/耗时/耗算力任务，支持图片超分（RealESRGAN等9种模型）、Z-Image-Turbo极速文生图（4步出图）、LTX-2.5 INT8文生视频/图生视频/首尾帧视频（22B参数，电影级动效，动作控制精准，RTX 3080 12GB可跑768x432）、批量图生视频（多图→多视频）、多镜头批量生成（分镜脚本→视频片段）、动效素材生成器（float/zoom/pan/pulse预设运动+可选抠图）、人脸统一、批量抠图、Qwen角色三视图。触发词：超分、图片超分、批量超分、提升画质、ComfyUI、人脸统一、批量抠图、图生视频、文生视频、生成视频、批量动效、多镜头、动效素材。搜索能力「AnySearch」：基于AnySearch API的网络搜索，支持通用搜索/批量搜索/页面提取，用于热点文案、BGM推荐、原视频信息、剪辑技巧检索。触发词：搜索、查一下、找资料、网络搜索。依赖jianying-editor(JyProject)、computer-use-automation(剪映GUI操作)、ffmpeg/ffprobe、本地ComfyUI(127.0.0.1:8188)、AnySearch API Key(可选)。v3.0框架支持环境自适应：配置管理(.env+环境变量，密钥不硬编码)、环境检测(ComfyUI/剪映/AnySearch/ffmpeg)、能力降级(模块不可用时自动代偿或舍弃)，开源友好。"
---

# AI 短视频剪辑（三模式）

> **核心原则：能剪映搞定的优先用剪映，不浪费外部额度；只有图生视频动态化必须用外部工具。**

## 模式识别

根据用户触发词自动判断模式：

| 模式 | 触发词 | 输入 | 输出 | 确认门控 |
|---|---|---|---|---|
| **A 制作视频** | 制作视频/给图剪视频/用剪映剪辑/百万剪辑师/卡点变装/氛围感短片 | 3~10张图片或视频片段（支持混合） | 剪映工程草稿 + 可选导出mp4 | 有（方案确认后开工） |
| **⚡ 极速模式** | 快剪视频/快速剪辑/直接剪/不用确认 | 图片/视频素材 + 可选文字说明 | 剪映工程草稿 + 可选导出mp4 | **无（直接开工）** |
| **B 仿制模板** | 仿制模板/复刻视频/照着这个做/模仿这个视频/模板替换/剪映模板 | 1个参考视频 | 可发布的剪映模板草稿（多轨道+特效） + 模板发布指引 + 分析报告 | 有（方案确认后开工） |

无法判断时主动询问用户。

## 一键成片（新手友好）

上传素材目录 + 指定主题，自动生成剪映工程。无需手动配置分镜、转场、字幕、BGM。

`ash
python easy_build.py --input ./素材 --theme 国风 --output 我的视频
`

**支持主题**：国风 / 治愈 / 卡点 / 电影 / 赛博 / 极简 / 复古

**自动完成**：
1. 扫描素材（图片+视频，递归子目录）
2. 根据主题匹配风格（转场/滤镜/字幕/BGM）
3. 生成分镜（合理时长）
4. 添加转场
5. 添加关键帧运镜（Ken Burns，解决静止图片单调）
6. 添加艺术字幕（钩子标题）
7. 添加BGM
8. 输出剪映工程草稿

**能力模块**：
- cap_keyframe_engine — 8种运镜预设（推近/拉远/左移/右移/上移/下移/组合），淡入淡出
- cap_subtitle_designer — 5种艺术字幕风格，三层叠加（主标题/副标题/旁白）
- cap_effect_library — 10种转场+8种滤镜，7种主题风格自动匹配

## 搜索能力（AnySearch）

基于AnySearch API的统一网络搜索，可选能力（未配置API Key时自动跳过）：

```python
from capabilities.cap_search import search, extract
results = search("抖音爆款文案", max_results=5)  # 通用搜索
content = extract("https://example.com")          # 页面全文提取(Markdown)
```

**适用场景**：
- 制作视频：搜索热点话题、文案素材、BGM推荐
- 仿制模板：搜索原视频相关信息、同类爆款分析
- 素材准备：搜索参考图、风格趋势、配色方案
- 知识沉淀：搜索剪辑技巧、特效教程

## 环境自适应与配置（v3.0）

所有敏感配置通过 `.env` 文件管理，不硬编码：
```
ANYSEARCH_API_KEY=as_sk_xxx      # AnySearch API Key（可选）
COMFYUI_ADDRESS=127.0.0.1:8188   # ComfyUI地址
JIANYING_PATH=C:\...\JianyingPro.exe  # 剪映路径
```

启动时自动检测环境，能力不可用时自动降级：
- ComfyUI不可用 → 跳过高算力功能，使用原始素材
- 剪映不可用 → 只输出方案和素材清单
- AnySearch不可用 → 跳过网络搜索，使用内置知识

## 前置检查（每次任务必做）

### 1. jianying-editor bug 修复（必须）

`jianying-editor/scripts/utils/media_normalizer.py` 第59行有 bug：`width % 16 != 0` 过度严格，导致 1080 宽竖屏视频被强制转成 1920×1080 横屏。

**修复**：将 `width % 16 != 0` 改为 `width % 2 != 0`（H.264 规范只要求偶数宽度）。

每次新环境首次使用前检查并修复。

### 2. 依赖检查

确认以下可用：
- Python 3.11+（用 `python -m pip` 安装依赖）
- ffmpeg / ffprobe
- jianying-editor skill 已安装
- 已安装：uiautomation、edge-tts、pymediainfo、psutil、requests、websockets、Pillow

### 3. 剪映版本选择（强制使用5.9）

**模式B强制使用剪映5.9版本**。jianying-editor的README明确要求最佳适配v5.9。2026-09-27完整仿制任务验证通过（9轨道工程+画中画缩放+特效添加+导出全流程）。

| 版本 | 多轨道显示 | 画中画GUI调整 | 特效添加 | 工程兼容性 | 草稿目录 |
|---|---|---|---|---|---|
| **5.9 ✅强制** | 9轨道全部正常显示 | 缩放/位置实时生效 | 拖拽到时间线成功 | jianying-editor工程可打开 | `D:\JianyingProDrafts\JianyingPro Drafts\` |
| 11.6 ❌禁用 | 只显示4轨（11轨工程） | 修改clip不生效 | cu不支持拖拽 | 可打开但显示异常 | `C:\Users\...\AppData\Local\JianyingPro\...` |

**5.9版本关键路径**：
- 5.9免安装版（英文路径）：`C:\JianyingPro_5.9\JianyingPro.exe`
- 5.9桌面快捷方式：`C:\Users\Administrator\Desktop\5.9.lnk`
- 5.9草稿目录：`D:\JianyingProDrafts\JianyingPro Drafts\`
- jianying-editor创建的工程默认在C盘AppData，**必须复制到D盘5.9草稿目录**才能在5.9中打开
- 5.9无法打开11.6创建的工程（提示"软件版本需要升级"）
- 5.9免安装版需从中文路径复制到英文路径避免启动问题
- **不能同时运行两个剪映实例**
- **🚨 5.9版本绝对禁止点击更新/升级**：一旦更新就会变成最新版（11.6+），失去多轨道正常显示、特效可拖拽等核心优势。5.9启动后如弹出更新提示，立即关闭，不要点任何更新按钮

**5.9版本PowerShell GUI操作模板**（5.9在系统桌面运行，cu虚拟桌面看不到窗口，必须用PowerShell Windows API）：
```powershell
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint cButtons, uint dwExtraInfo);
    [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
    public const int MOUSEEVENTF_LEFTDOWN = 0x02;
    public const int MOUSEEVENTF_LEFTUP = 0x04;
    public const int MOUSEEVENTF_MOVE = 0x01;
    public const int KEYEVENTF_KEYUP = 0x02;
    public const int VK_CONTROL = 0x11;
    public const int VK_RETURN = 0x0D;
    public const int VK_HOME = 0x24;
    public const int VK_S = 0x53;
    public const int VK_E = 0x45;
    public const int VK_W = 0x57;
}
"@
Add-Type -AssemblyName System.Windows.Forms

# 激活窗口
$proc = Get-Process | Where-Object {$_.ProcessName -like "*Jianying*" -and $_.MainWindowTitle -ne ""} | Select-Object -First 1
$hwnd = $proc.MainWindowHandle
[Win32]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 500

# 点击（按屏幕百分比计算坐标，2560x1440）
$clickX = [int](2560 * 0.25)
$clickY = [int](1440 * 0.55)
[Win32]::SetCursorPos($clickX, $clickY)
Start-Sleep -Milliseconds 500  # 必须等鼠标到位再点击
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 100
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

# 截图验证（用Python PIL，cu.screenshot看不到系统桌面）
python -c "from PIL import ImageGrab; ImageGrab.grab().save('screenshot.png')"
```

**5.9版本快捷键清单**：
| 快捷键 | 功能 |
|---|---|
| Ctrl+S | 保存工程 |
| Ctrl+E | 打开导出对话框 |
| Ctrl+W | 关闭当前编辑标签页返回主页（不刷新，无广告） |
| Home | 播放头移到开头 |
| Enter | 确认数值输入/对话框 |
| Ctrl+Z | 撤销 |

**⚠️ 禁止操作**：
- 不要点击"回到主页"按钮（会刷新打开广告），用Ctrl+W关闭编辑标签页
- 不要用cu（虚拟桌面）操作5.9（看不到窗口）
- 不要同时运行5.9和11.6两个实例

### 4. 平台说明

- 自动导出仅支持 Windows（需剪映打开状态）
- macOS 用户生成工程后需在剪映里手动导出
- 导出失败时提示用户剪映手动导出，**不做 ffmpeg 兜底**

## 模式 A：制作视频（阶段 0~6）

### 阶段 0：发起任务，上传素材
- 用户上传图片/视频素材（支持混合）
- 记录本地路径；URL 素材先下载到本地
- **输出**：素材清单

### 阶段 1：理解视频制作要求
必须确认：主题、风格、目的/平台、时长（默认15s）、比例（默认9:16）、是否旁白、是否升格、是否封面图。

### 阶段 2：素材探查
1. Read 全部素材，分析人物一致性、色调、质量、叙事潜力
2. **人脸一致性询问**：多张 AI 图有差异时主动询问是否需要统一
3. 筛选剔除：模糊/严重瑕疵/高度重复的剔除
4. 排序：按色彩递进/情绪起伏排列
- **输出**：筛选后素材清单 + 排序理由 + 剔除原因

### 阶段 3：方案设计、确认
- 主题命名、时长比例风格定调、节奏设计
- **分镜设计表**：时间/素材/景别/运镜/字幕/转场/音效
- 声音设计：旁白文案 + TTS音色、BGM关键词、音效点
- **确认门控**：必须等用户明确确认后开工

### 阶段 4：视图层资产准备
**比例适配（强制）**：用 ffprobe 检测所有素材分辨率，非目标比例的图片统一裁剪缩放至画布分辨率（如 9:16→1080×1920），裁剪后 Read 验证构图。

**视频预处理（强制）**：所有视频提前用 ffmpeg 预处理为画布分辨率、H.264、yuv420p、30fps、无音频：
```
ffmpeg -i input.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -an -r 30 -c:v libx264 -pix_fmt yuv420p output.mp4
```

**视图层资产**：
- 静态原图：直接用（快切/关键帧运镜）
- 普通动态片段：image_to_video（钩子/收尾，5秒）
- 升格慢动作：image_to_video（高潮，prompt 强调 240fps/逆光/丁达尔/衣袂飘动）
- 一次最多并行 2 个 image_to_video

**其他层仅确认文案**：音频层（旁白+BGM关键词+音效点）、字幕层（字幕表）、贴纸层（关键词），均在阶段5剪映里调用。

- **资产确认门控**：视图层文件就绪 + 其他层文案确认后进入合成

### 阶段 5：jianying-editor 剪映合成
详细 API 和脚本模板见 `references/jianying-api-reference.md` 和 `scripts/build_video.py`。

核心步骤：
1. 创建工程：`JyProject(name, width=1080, height=1920, overwrite=True)`
2. 导入视图素材：按分镜时间线 `add_media_safe(path, start_time, duration)`
3. Ken Burns关键帧：每个≥2秒静态图加缩放关键帧，交替放大/缩小，Bezier缓动
4. 自动转场：遍历相邻 segment，给**前一片段结尾**添加 `add_transition_simple("叠化", video_segment=seg, duration="0.5s")`
5. 多音轨：旁白(TTS)、BGM(云端音乐)、音效(云端音效≤6个)
6. **动态艺术组合式字幕**：三轨道叠加（ArtTitle主标题+ArtSubtitle副标题+ArtNarration旁白），每层独立动画+样式，详见专章
7. 贴纸（谨慎≤3个）：云端贴纸
8. 保存：`project.save()`
9. 导出：auto_exporter 自动导出（Windows），失败则提示手动导出

### 阶段 6：验证与交付
- ffprobe 确认时长/分辨率/音视频流
- 抽帧验证（至少3帧：钩子/快切/高潮）
- draft_inspector 验证轨道结构
- 封面生成（如用户确认需要）
- present_files 交付 mp4 + 告知工程路径和手动补充项

## ⚡ 极速模式：快剪视频（模式A免确认版）

> **核心定位**：模式A的免确认极速版。用户说"快剪视频"+上传素材，AI跳过方案确认门控，直接按最佳默认方案开工。**文字说明权重高于素材理解**——用户有文字要求时优先按文字生成核心方案，再根据素材内容优化方案和挑选加工素材。

### 与模式A的区别

| 维度 | 模式A | 极速模式 |
|---|---|---|
| 方案确认 | 必须等用户确认分镜表后开工 | **跳过确认，直接开工** |
| 素材探查 | 详细分析+人脸一致性询问 | 快速筛选（剔除明显废片），不询问 |
| 参数默认 | 询问用户（时长/比例/风格等） | **用默认最佳值**（15s/9:16/氛围感） |
| 文字说明 | 参考 | **最高优先级**，必须严格执行 |
| 适用场景 | 精细定制、重要作品 | 快速出片、日常剪辑、批量生产 |

### 极速模式执行流程（5步，无确认门控）

#### 步骤1：接收任务 + 素材探查（快速）
- 用户上传素材（图片/视频/文件夹）+ 可选文字说明
- **文字说明优先解析**：提取主题、风格、时长、比例、旁白要求、特效要求等
- 快速Read素材，剔除模糊/严重瑕疵/高度重复的废片
- 不询问人脸一致性，直接按素材原样使用
- **输出**：筛选后素材清单 + 文字要求摘要

#### 步骤2：方案生成（AI自主决策，不确认）
- 根据**文字说明**生成核心方案（主题/风格/节奏/分镜）
- 根据**素材内容**优化方案：挑选最适合的素材、调整排序、匹配景别
- 默认参数：时长15s、比例9:16、风格氛围感、BGM自动匹配、旁白自动生成（如文字要求）
- 生成分镜表（内部使用，不展示给用户确认）
- **直接进入下一步，不等用户确认**

#### 步骤3：资产准备（自动）
- 比例适配：非9:16素材自动裁剪缩放至1080×1920
- 视频预处理：ffmpeg转码为画布分辨率+H264+yuv420p+30fps+无音频
- 旁白TTS（如文字要求有旁白）：自动生成文案+配音
- BGM：根据风格自动选择（云端音乐或默认）
- 字幕：根据旁白自动生成
- **不等待用户确认，直接进入合成**

#### 步骤4：剪映工程合成（自动，动态艺术组合式字幕）
- 创建工程→导入素材→Ken Burns关键帧→转场→多音轨→**动态艺术组合式字幕**→保存
- **Ken Burns关键帧**：每个≥2秒静态图加缩放关键帧，交替放大(1.0→1.15)/缩小(1.15→1.0)，Bezier缓动
- **转场**：必须给**前一片段结尾**添加（`add_transition_simple("叠化", video_segment=segments[i])`），给后一片段加会错位
- **动态艺术组合式字幕**：见下方专章，三轨道叠加（主标题ArtTitle+副标题ArtSubtitle+旁白ArtNarration），每层独立动画+样式
- 旁白字幕固定时长2.5s+间隔0.3s，避免浮点四舍五入导致轨道重叠（2.75s→2.8s会重叠）
- 贴纸≤3个，谨慎使用
- 保存工程

#### 步骤5：导出 + 交付
- auto_exporter自动导出（Windows），失败则提示手动导出
- ffprobe验证参数
- 抽帧验证（3帧）
- present_files交付mp4 + 工程路径
- **简要说明**：用了哪些素材、什么风格、有哪些可手动优化的点

### 文字说明优先级规则（铁律）

当用户同时提供文字说明和素材时，按以下优先级处理：

1. **文字明确要求的参数**（时长/比例/风格/主题）→ 严格执行，覆盖默认值
2. **文字明确要求的内容**（旁白文案/字幕内容/BGM风格）→ 严格执行
3. **文字明确要求的特效**（升格/卡点/转场类型）→ 尽力实现，复杂的标注手动补
4. **素材内容**→ 在文字要求框架内优化，挑选最匹配的素材
5. **默认值**→ 文字和素材都没提及时使用

**示例**：
- 用户说"快剪视频，做一个30秒的卡点变装，用这些图片" → 时长30s、卡点节奏、变装主题，素材按变装前后排序
- 用户说"快剪视频，氛围感短片"（无素材）→ 提示需要素材，或用占位图生成模板
- 用户只说"快剪视频"+上传素材 → 全部默认值，AI自主判断最佳风格

### 极速模式注意事项
- 极速模式**不适合**需要精细定制的重要作品（用模式A）
- 如果素材质量太差（全部模糊/不相关），暂停并询问用户
- 如果文字说明与素材严重冲突（如要求"美食视频"但素材全是人像），暂停并询问
- 导出后用户可要求修改，修改时切换为模式A的精细调整流程

## 动态艺术组合式字幕（模式A/极速模式通用）

> **核心思路**：用三个独立文字轨道叠加，每层有独立的动画+样式，形成有层次感的艺术字幕效果。替代传统的单轨道简单字幕。

### 三轨道结构

| 轨道名 | 内容 | 位置 | 动画 | 样式 |
|---|---|---|---|---|
| **ArtTitle** | 主标题（视频主题/金句） | 屏幕上方 (y=0.5) | 入场+循环动画 | 大号加粗+描边+阴影 |
| **ArtSubtitle** | 副标题（解释/补充） | 标题下方 (y=0.2) | 入场动画 | 中号字 |
| **ArtNarration** | 旁白字幕（逐句） | 屏幕底部 (y=-0.8) | 打字机/逐字动画 | 小号+描边 |

### 四种风格预设

| 风格 | 适用场景 | 主标题颜色 | 入场动画 | 循环动画 | 旁白入场 |
|---|---|---|---|---|---|
| **epic** 史诗 | 国风/神话/史诗/热血 | 金色 (1,0.85,0.3) | 放大 | 扫光 | 打字机_I |
| **warm** 治愈 | 温暖/治愈/情感/日常 | 暖橙 (1,0.7,0.4) | 弹入 | 彩虹 | 逐字显影 |
| **fun** 卡通 | 趣味/卡点/冒险/童趣 | 青色 (0.2,0.9,1.0) | 弹性伸缩 | 晃动 | 逐字旋转 |
| **minimal** 极简 | 高级/简约/文艺/品牌 | 白色 | 渐显 | 无 | 渐显 |

### 可用动画库（jianying-editor）

- **入场动画 TextIntro**：70+种免费（打字机系列/弹入系列/滑动系列/擦除系列/水墨晕开/逐字旋转/逐字显影/拖尾/甩出/生长/溶解/冲屏位移/卡拉OK等）
- **出场动画 TextOutro**：50+种免费
- **循环动画 TextLoopAnim**：40+种免费（彩虹/扫光/摇摆/晃动/闪烁/颤抖/旋转/VHS/弹幕滚动/吹泡泡等）

**动画使用规则**：
- 先加入场/出场动画，再加循环动画
- 每个片段每种类型只能有一个动画
- 用法：`add_text_simple(text, anim_in="放大", anim_loop="扫光")`

### 文字样式系统

- **字体**：800+种（HarmonyOS Sans SC/源云明体/LXGW文楷/HG行書体等中文字体）
- **TextStyle**：size/bold/italic/underline/color(RGB 0-1)/alpha/align/vertical/letter_spacing/line_spacing
- **TextBorder**：描边（color/alpha/width）
- **TextShadow**：阴影（color/diffuse/distance/angle）
- **TextBackground**：背景框（color/round_radius/height/width/offset）
- **RichTextSpan**：富文本（按字符范围设置独立颜色/大小/加粗）

### 实现代码模板

```python
# 主标题（大号+放大入场+扫光循环+描边+阴影）
project.add_text_simple(
    "云端龙吟", start_time="0s", duration="3s",
    font_size=14.0, color_rgb=(1.0, 0.85, 0.3),
    style=draft.TextStyle(size=14.0, bold=True),
    border=draft.TextBorder(color=(0,0,0), width=60),
    shadow=draft.TextShadow(color=(0,0,0), distance=8, diffuse=15),
    clip_settings=draft.ClipSettings(transform_y=0.5),
    anim_in="放大", anim_loop="扫光",
    track_name="ArtTitle",
)
# 副标题
project.add_text_simple(
    "白龙少女的东方神话", start_time="0s", duration="3s",
    font_size=7.0, color_rgb=(1,1,1),
    clip_settings=draft.ClipSettings(transform_y=0.2),
    anim_in="向上滑动",
    track_name="ArtSubtitle",
)
# 旁白（固定2.5s+0.3s间隔，从3s开始）
for i, narr in enumerate(narrations):
    start = 3.0 + i * 2.8
    project.add_text_simple(
        narr, start_time=f"{start:.2f}s", duration="2.5s",
        font_size=5.5, color_rgb=(1,1,1),
        border=draft.TextBorder(color=(0,0,0), width=40),
        clip_settings=draft.ClipSettings(transform_y=-0.8),
        anim_in="打字机_I",
        track_name="ArtNarration",
    )
```

### 已知限制

- `add_styled_text()`（花字）文档提及但**代码未实现**，目前只有3种红色花字本地素材无API入口
- 气泡效果需手动注入effect_id和resource_id
- 艺术性需在实践中积累，当前为基础框架

## 模式 B：仿制模板（阶段 0~7）

> **核心目标**：仿制原视频效果，生成可发布到剪映平台的模板草稿。其他用户打开模板后，用简单原始素材（无特效的图片/视频）替换标记为"可替换"的轨道素材，即可得到模板中的视频效果。
>
> **铁律**：素材只放原始件（图片/视频/音频/贴纸），所有特效/转场/滤镜/关键帧/蒙版/运镜全部在剪映工程内通过GUI实现。禁止在素材准备阶段给图片/视频加特效。

### 阶段 0：发起任务，上传参考视频
- 用户上传 1 个参考视频（mp4/mov 等）
- 记录本地路径；抖音等在线视频请用户手动下载后上传
- **输出**：参考视频路径 + 基础信息

### 阶段 1：原视频深度分析
详细分析方法见 `references/video-analysis.md`，分析脚本见 `scripts/analyze_video.py`。

**必须分析的维度**：
1. **基础信息**：时长、分辨率、帧率、码率、音轨
2. **镜头分割**：ffmpeg scene detection 找出每个镜头起止时间
3. **每镜头抽帧分析**：景别/主体/构图/色调/运动方向
4. **多轨道叠加关系**：主轨内容、画中画层数、文字层、特效层、贴纸层（这是模板还原的关键）
5. **运镜与关键帧**：固定/推近/拉远/摇移/旋转/升格，关键帧参数（缩放/位移/旋转/透明度的起止值）
6. **蒙版与抠像**：蒙版形状（矩形/圆形/自定义）、蒙版位置/大小/羽化、抠像类型
7. **特效与滤镜**：画面特效（粒子/光效/抖动/模糊）、全片滤镜、混合模式（滤色/正片叠底等）
8. **转场**：硬切/叠化/闪白/闪黑/缩放/滑动
9. **字幕提取**：OCR 识别字幕内容、时间点、位置、字体样式
10. **音频分析**：BGM风格/BPM/旁白/音效点
11. **分析汇总**：输出完整仿制分镜表（含轨道层级）+ 可替换素材清单 + 特效实现清单

### 阶段 2：仿制方案确认
- 输出完整分镜表（含多轨道层级）+ 可替换素材清单 + 特效实现清单
- 明确标注：哪些素材可替换（图片/视频）、哪些固定（特效/文字/音频）
- 明确标注：哪些特效可通过GUI自动实现、哪些需手动微调
- **确认门控**：用户确认后进入素材准备

### 阶段 3：原始素材准备（只放原始件，不加特效）
**比例适配（强制）**：所有占位图片裁剪缩放至画布分辨率。

**视频预处理（强制）**：所有占位视频预处理为画布分辨率+H264+yuv420p+30fps+无音频。

**准备的素材类型**（仅限原始素材）：
- **占位图片**：纯色/数字/简单图形，用于标记可替换位置（如"替换图片1"）
- **占位视频**：从原视频裁剪的镜头片段（用户后续替换），或简单动态素材
- **音频**：原视频BGM（提取mp3）、旁白、音效
- **贴纸**：透明PNG/动图（如需）
- **文字**：字幕文案（在剪映里添加文字层）

**禁止**：在素材准备阶段给图片/视频加任何特效、滤镜、转场、关键帧。

### 阶段 4：创建剪映草稿（多轨道导入原始素材）
详细脚本见 `scripts/clone_template.py`。

**轨道结构**（按层级从下到上）：
```
┌─────────────────────────────────────────┐
│  特效轨道（粒子/光效/抖动等，最上层）      │
├─────────────────────────────────────────┤
│  文字轨道（字幕/标题/花字）               │
├─────────────────────────────────────────┤
│  贴纸轨道（透明PNG/动图）                 │
├─────────────────────────────────────────┤
│  画中画轨道2（上层画面，可带蒙版）         │
├─────────────────────────────────────────┤
│  画中画轨道1（下层画面）                  │
├─────────────────────────────────────────┤
│  主轨道（背景/基础画面）                  │
├─────────────────────────────────────────┤
│  音频轨道（BGM/旁白/音效，多轨叠加）       │
└─────────────────────────────────────────┘
```

**创建步骤**：
1. 创建工程：分辨率/帧率同原视频
2. 主轨道：按时间线导入基础画面素材
3. 画中画轨道：按分析结果导入叠加画面（多层）
4. 文字轨道：按时间轴添加字幕（`add_text_simple`）
5. 贴纸轨道：导入贴纸素材
6. 音频轨道：BGM+旁白+音效分轨导入
7. 保存工程

**注意**：此阶段只导入原始素材和文字，不加任何特效/转场/滤镜/关键帧/蒙版。

### 阶段 5：剪映GUI实现特效（5.9版本，强制）

使用PowerShell Windows API操作剪映5.9电脑版，按特效实现清单逐步操作。**5.9在系统桌面运行，cu虚拟桌面看不到窗口，必须用PowerShell操作。**

#### 5.1 启动剪映5.9并打开草稿

```powershell
# 启动5.9（如未运行）
Start-Process "C:\JianyingPro_5.9\JianyingPro.exe"
Start-Sleep -Seconds 8

# 激活窗口
$proc = Get-Process | Where-Object {$_.ProcessName -like "*Jianying*" -and $_.MainWindowTitle -ne ""} | Select-Object -First 1
$hwnd = $proc.MainWindowHandle
[Win32]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 500

# 主页双击目标草稿（草稿在第一行，按屏幕百分比计算坐标）
# 第一个草稿约 (8%, 25%)，第二个约 (16%, 25%)，依此类推
$clickX = [int](2560 * 0.16)
$clickY = [int](1440 * 0.25)
[Win32]::SetCursorPos($clickX, $clickY)
Start-Sleep -Milliseconds 500
# 双击
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 100
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
Start-Sleep -Milliseconds 200
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 100
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
Start-Sleep -Seconds 5
```

**注意**：
- 草稿需**双击**打开（单击不生效）
- 工程主轨道不能为空，否则打开后进入即梦AI页面
- 每次操作后用Python PIL截图验证：`python -c "from PIL import ImageGrab; ImageGrab.grab().save('shot.png')"`

#### 5.2 返回主页（关闭当前编辑）

```powershell
# 用Ctrl+W关闭当前编辑标签页返回主页（不刷新，无广告）
# ⚠️ 不要点击"回到主页"按钮（会刷新打开广告）
[Win32]::keybd_event([Win32]::VK_CONTROL, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 50
[Win32]::keybd_event([Win32]::VK_W, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 50
[Win32]::keybd_event([Win32]::VK_W, 0, [Win32]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 50
[Win32]::keybd_event([Win32]::VK_CONTROL, 0, [Win32]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
Start-Sleep -Seconds 3
```

#### 5.3 画中画缩放/位置调整

```powershell
# 1. 点击时间线中的画中画片段选中（按轨道位置计算坐标）
# 2. 双击右侧"位置大小"面板的缩放数值框（约96%, 13.5%）
# 3. 输入百分比数字（如45）
# 4. 按Enter确认

# 示例：调整缩放为45%
$clickX = [int](2560 * 0.96)
$clickY = [int](1440 * 0.135)
[Win32]::SetCursorPos($clickX, $clickY)
Start-Sleep -Milliseconds 500
# 双击数值框
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 100
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
Start-Sleep -Milliseconds 200
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 100
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
Start-Sleep -Milliseconds 300
# 输入数值
[System.Windows.Forms.SendKeys]::SendWait("45")
Start-Sleep -Milliseconds 300
# Enter确认
[Win32]::keybd_event([Win32]::VK_RETURN, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 100
[Win32]::keybd_event([Win32]::VK_RETURN, 0, [Win32]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
```

**位置X/Y调整**：同样方法，点击位置X或Y数值框，输入数值后Enter。

#### 5.4 添加特效（拖拽到时间线）

```powershell
# 1. 点击顶部"特效"按钮（约11%, 3%）
# 2. 在特效列表中找到目标特效（按行列计算坐标）
# 3. 拖拽特效缩略图到时间线的目标位置

# 示例：拖拽特效到时间线
$startX = [int](2560 * 0.22)  # 特效缩略图位置
$startY = [int](1440 * 0.42)
$endX = [int](2560 * 0.28)    # 时间线目标位置
$endY = [int](1440 * 0.85)

[Win32]::SetCursorPos($startX, $startY)
Start-Sleep -Milliseconds 500
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 300
# 分10步移动模拟拖拽
for ($i = 1; $i -le 10; $i++) {
    $x = $startX + [int](($endX - $startX) * $i / 10)
    $y = $startY + [int](($endY - $startY) * $i / 10)
    [Win32]::SetCursorPos($x, $y)
    Start-Sleep -Milliseconds 60
}
Start-Sleep -Milliseconds 300
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
```

**注意**：
- 点击特效+号只是预览，**不会添加到时间线**，必须拖拽
- 拖拽起点坐标需精确，否则会添加错误的特效
- 添加后时间线会出现独立的特效轨道

#### 5.5 添加蒙版

1. 选中画中画片段
2. 点击右侧"蒙版"标签（约85%, 7%）
3. 选择蒙版形状（线性/镜面/圆形/矩形/爱心/星形）
4. 调整位置/旋转/大小/羽化参数

#### 5.6 添加转场

1. 确保同一轨道有两个相邻片段
2. 点击顶部"转场"按钮
3. 拖拽转场到两个片段的连接处

#### 5.7 保存与导出

```powershell
# 保存（Ctrl+S）
[Win32]::keybd_event([Win32]::VK_CONTROL, 0, 0, [UIntPtr]::Zero)
[Win32]::keybd_event([Win32]::VK_S, 0, 0, [UIntPtr]::Zero)
[Win32]::keybd_event([Win32]::VK_S, 0, [Win32]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
[Win32]::keybd_event([Win32]::VK_CONTROL, 0, [Win32]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
Start-Sleep -Seconds 2

# 导出（Ctrl+E打开导出对话框）
[Win32]::keybd_event([Win32]::VK_CONTROL, 0, 0, [UIntPtr]::Zero)
[Win32]::keybd_event([Win32]::VK_E, 0, 0, [UIntPtr]::Zero)
[Win32]::keybd_event([Win32]::VK_E, 0, [Win32]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
[Win32]::keybd_event([Win32]::VK_CONTROL, 0, [Win32]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
Start-Sleep -Seconds 3

# 点击导出按钮（约57%, 71%）
$clickX = [int](2560 * 0.57)
$clickY = [int](1440 * 0.71)
[Win32]::SetCursorPos($clickX, $clickY)
Start-Sleep -Milliseconds 500
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 100
[Win32]::mouse_event([Win32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
# 等待导出完成（约10-20秒）
```

#### 5.8 操作原则

- **每次操作后必须截图验证**，不凭记忆连续操作
- **操作鼠标后必须加0.3-0.5秒延时**再点击，否则鼠标未到位就点击会点错
- 窗口最大化后坐标更稳定
- 复杂操作（自定义蒙版路径、关键帧曲线）标注"手动微调"
- 操作失败时撤销（Ctrl+Z），不硬凑
- 全部完成后Ctrl+S保存

---

### 阶段5备用：11.6版本操作（仅当5.9不可用时）

使用 `computer-use-automation` skill 的cu操作剪映11.6电脑版。

**GUI坐标校准（每次操作前必须先校准）**：
- `cu.screenshot()` 返回1920×1080截图，实际屏幕可能是2560×1440
- 实测校准：x比例≈1.25（截图x = x_rel × 1.25），y比例≈0.727（截图y = y_rel × 0.727）
- `cu.click(x, y)` 使用0-1000相对坐标
- **操作鼠标后必须加0.3-0.5秒延时再点击**
- 草稿需双击打开
- 窗口最大化后坐标更稳定
- 即梦页面根因：工程主轨道为空时进入即梦AI页面；添加任意主轨道素材可解决

**11.6已知限制**：
- 多轨道显示异常（11轨工程只显示4轨）
- 画中画位置调整不生效
- cu不支持拖拽操作，特效无法添加
- draft_content.json加密（文件头17a106f7）

### 阶段 6：标记可替换素材 + 模板发布指引
1. 在剪映里确认哪些轨道素材标记为"可替换"（发布模板时在"片段设置"中打勾）
2. 生成**模板发布指引**：
   - 可替换素材清单（时间点/轨道/替换类型/建议尺寸）
   - 固定元素清单（特效/文字/音频/滤镜）
   - 发布步骤：导出→发布模板→填写标题/描述/话题→片段设置打勾→权限设置→发布
3. 生成**替换素材指引**（给模板使用者看）：需要几张图/几段视频、建议尺寸、替换顺序

### 阶段 7：验证与交付
- draft_inspector 验证轨道结构（轨道数/片段数/层级）
- 抽帧验证（至少3帧：开头/中间/特效密集处）
- 交付：剪映工程路径 + 模板发布指引 + 替换素材指引 + 原视频分析报告
- 用户在剪映里检查效果后，手动发布模板

## 全部决策已确认（封板）

| # | 决策项 | 结论 |
|---|---|---|
| 1 | 转场/特效 API | "工程预留+手动补"模式，叠化可自动 |
| 2 | 贴纸 | 纳入标准流程，全片≤3个，谨慎使用 |
| 3 | 音效层 | 纳入标准流程，全片≤6个，只在4类关键位置 |
| 4 | 关键帧运镜 | 纳入标准流程，只对≥2秒静态图，缩放≤1.15 |
| 5 | 导出失败处理 | 提示用户去剪映手动导出，不做ffmpeg兜底 |
| 6 | 人脸一致性 | 在素材探查阶段询问确定 |
| 7 | 调色 | 接受"剪映工程里手动套滤镜" |
| 8 | 多比例/多时长 | 参数化支持9:16/1:1/16:9，15s/20s/30s |
| 9 | 封面生成 | 询问确定，需要时从视频抽帧+image_edit加标题 |
| 10 | macOS兼容 | 技能说明里明确：Mac用户手动导出 |
| 11 | 剪映优先原则 | 能剪映搞定的优先用剪映，只有图生视频用外部工具 |
| 12 | 视频预处理 | 强制ffmpeg预处理为画布分辨率+H264+yuv420p+无音频 |
| 13 | media_normalizer bug | 必须修复width%16→width%2 |
| 14 | 双模式 | 模式A制作视频+模式B仿制模板 |
| 15 | 模式B最终产物 | 可发布到剪映平台的模板草稿，不是仿制视频 |
| 16 | 模式B素材铁律 | 只放原始素材（图片/视频/音频/贴纸），特效/转场/滤镜/关键帧/蒙版全部在剪映GUI实现 |
| 17 | 模式B多轨道 | 主轨+画中画轨+文字轨+特效轨+贴纸轨+音频轨，禁止单轨 |
| 18 | 模式B特效实现 | 通过computer-use-automation操作剪映电脑版GUI实现，复杂操作标注手动微调 |
| 19 | 模式B可替换标记 | 发布模板时在"片段设置"中标记可替换素材，固定元素不标记 |
| 20 | 模式B分析维度 | 必须分析多轨道叠加关系/蒙版/关键帧/混合模式/抠像，不止镜头分割 |
| 21 | 模式B剪映版本 | 强制使用5.9版本，11.6禁用（多轨道显示异常+特效无法添加+加密） |
| 22 | 模式B GUI操作方式 | 5.9用PowerShell Windows API（cu看不到系统桌面窗口），截图用Python PIL |
| 23 | 模式B返回主页 | 用Ctrl+W关闭编辑标签页，禁止点击"回到主页"按钮（会刷新广告） |
| 24 | 模式B特效添加 | 必须拖拽特效到时间线（点击+号只是预览），cu不支持拖拽故11.6无法添加 |
| 25 | 极速模式 | 模式A免确认版，触发词"快剪视频"，跳过方案确认直接开工 |
| 26 | 极速模式文字优先级 | 文字说明权重高于素材理解，优先按文字生成方案再用素材优化 |
| 27 | 极速模式默认参数 | 15s/9:16/氛围感，文字有要求时覆盖默认值 |
| 28 | 极速模式适用边界 | 素材全废或文字与素材严重冲突时暂停询问，否则直接开工 |
| 29 | 动态艺术组合式字幕 | 三轨道叠加（ArtTitle+ArtSubtitle+ArtNarration），每层独立动画+样式，替代单轨简单字幕 |
| 30 | 字幕风格预设 | 4种（epic史诗/warm治愈/fun卡通/minimal极简），按视频主题自动匹配 |
| 31 | Ken Burns关键帧 | 每个≥2秒静态图加缩放关键帧，交替放大(1.0→1.15)/缩小(1.15→1.0)，Bezier缓动 |
| 32 | 转场添加位置 | 必须给前一片段结尾添加，给后一片段加会导致转场图标错位 |
| 33 | 旁白时间计算 | 固定2.5s+0.3s间隔，避免浮点四舍五入（2.75→2.8）导致轨道重叠 |
| 34 | 5.9兼容性问题根因 | BGM路径指向豆包cloud_cache目录，5.9无法访问导致工程显示00:00；纯视频轨工程可正常打开 |
| 35 | add_styled_text未实现 | 花字API文档提及但代码未实现，当前用TextStyle+描边+阴影+动画组合替代 |

## 模式B验证经验与已知限制（2026-09-27实测）

### 5.9版本实测（强制使用，2026-09-27完整任务验证通过）

**完整仿制任务验证通过**（时尚人像视频，9秒，8镜头，9轨道工程）：

| 步骤 | 操作 | 结果 |
|---|---|---|
| 1 | 视频分析（ffmpeg场景检测+抽帧） | ✅ 8镜头分镜识别 |
| 2 | jianying-editor创建工程（1主轨+7画中画+1BGM） | ✅ draft_info.json结构正确 |
| 3 | 复制工程到D盘5.9草稿目录 | ✅ 5.9可识别 |
| 4 | 5.9打开工程 | ✅ **9轨道全部正常显示** |
| 5 | 画中画缩放调整（PIP_1=45%, PIP_2=42%, PIP_3=48%） | ✅ 实时预览生效 |
| 6 | 特效添加（拖拽到时间线） | ✅ 创建独立特效轨道 |
| 7 | 工程保存（Ctrl+S） | ✅ 正常 |
| 8 | 导出（Ctrl+E→导出按钮） | ✅ 720×1280 HEVC+AAC 30fps 9秒 |

**已验证可行功能（10项）**：
1. ✅ jianying-editor创建的多轨道工程可被5.9正常打开
2. ✅ 多轨道正常显示（9轨道全部可见，对比11.6只显示4轨）
3. ✅ 画中画叠加正常工作
4. ✅ GUI调整画中画缩放（双击数值框→输入→Enter，实时预览）
5. ✅ 画中画位置可通过右侧"位置大小"面板调整
6. ✅ 特效添加成功（拖拽到时间线，创建独立特效轨道，参数可调）
7. ✅ 蒙版添加成功（圆形蒙版，位置/旋转/大小/羽化可调）
8. ✅ 转场添加操作可行（需同轨两相邻片段，拖拽到连接处）
9. ✅ 工程保存正常（Ctrl+S）
10. ✅ 导出成功（720×1280，HEVC，30fps）

**5.9版本操作要点**：
- 工程创建后必须从C盘AppData复制到D盘`D:\JianyingProDrafts\JianyingPro Drafts\`
- 用PowerShell Windows API操作（cu看不到系统桌面的5.9窗口）
- 截图用Python PIL的ImageGrab.grab()
- 画中画缩放：选中片段→右侧"位置大小"→双击缩放数值框→输入百分比→Enter
- 特效添加：顶部"特效"→拖拽特效缩略图到时间线（点击+号只是预览）
- 返回主页：Ctrl+W关闭编辑标签页（不要点"回到主页"按钮）
- 导出：Ctrl+E打开对话框→点击导出按钮（约57%, 71%）
- 草稿双击打开
- 操作鼠标后必须加0.3-0.5秒延时再点击

### 11.6版本实测（不推荐）
**已验证可行**：
1. 视频分析：ffmpeg场景检测+抽帧分析可识别镜头结构
2. 工程创建：jianying-editor可创建多轨道工程，draft_info.json结构正确
3. BGM提取：从原视频提取音轨为mp3成功
4. 背景视频：ffmpeg生成纯色背景视频成功
5. 导出功能：剪映导出成功（720P，HEVC+AAC）
6. GUI坐标校准：x比例≈1.25，y比例≈0.727，操作后加0.3-0.5秒延时

**已知限制（11.6特有）**：
1. **多轨道显示问题**：jianying-editor创建的11轨工程在11.6中只显示4轨
2. **画中画位置调整**：修改draft_info.json的clip.scale/transform可保存，但11.6中不生效
3. **特效添加**：GUI中点击特效+号只是预览，需拖拽到时间线；cu不支持拖拽
4. **draft_content.json加密**：11.6将特效/蒙版/关键帧加密存储（文件头17a106f7），无法API修改
5. **复杂特效**：Glitch/百叶窗/3D立方体等高级效果需手动实现

### 通用已知限制
1. **转场**：jianying-editor的add_transition_simple受加密限制，复杂转场需GUI手动
2. **原视频剪辑手法解析**：复杂蒙版路径/自定义关键帧曲线/多层嵌套暂无法100%逆向
3. **抖音视频下载**：需用户手动下载后上传
4. **音频分离**：原视频BGM与人声混合时无法完美分离

### 后续优化方向
1. 特效拖拽起点坐标精确化（当前会添加错误特效，需建立特效位置坐标映射表）
2. 画中画位置X/Y数值框精确定位（当前点击困难，可尝试播放器拖拽方式）
3. 关键帧动画自动化（缩放/位移/旋转的关键帧添加方法）
4. 积累5.9版本常见特效的GUI操作SOP（Glitch/百叶窗/3D立方体等）
5. 研究5.9版本的draft_content.json是否加密（可能未加密或加密方式不同）
6. 转场自动化（同轨两相邻片段的转场拖拽添加）
7. 蒙版参数自动化（位置/大小/羽化的数值调整）

## References 导航

按需读取以下文件（不要一次性全部加载）：

| 文件 | 何时读取 |
|---|---|
| `references/mode-a-create-video.md` | 模式A详细流程、分镜表模板、节奏公式 |
| `references/mode-b-template-clone.md` | 模式B详细流程、仿制分镜表模板、替换指引模板 |
| `references/jianying-api-reference.md` | jianying-editor API速查、bug修复、常见坑 |
| `references/video-analysis.md` | 模式B视频分析方法（镜头分割/运镜/字幕OCR/音频） |
| `references/storyboard-template.md` | 分镜表模板+快慢对比节奏公式+prompt模板 |

## Scripts 导航

| 文件 | 用途 |
|---|---|
| `scripts/build_video.py` | 模式A剪映工程创建脚本模板（复制到项目根目录修改参数后运行） |
| `scripts/clone_template.py` | 模式B仿制草稿创建脚本模板 |
| `scripts/analyze_video.py` | 模式B视频分析脚本（镜头分割/抽帧/音轨探测） |
| `scripts/artistic_subtitle.py` | 动态艺术组合式字幕工具函数（4种风格预设+Ken Burns，复制到项目目录import使用） |
| `scripts/mask_flash_transition.py` | 蒙版展开快闪特效（多色块依次展开+条纹扫描，7种展开方向+6套配色，scale+transform关键帧模拟蒙版展开） |
| `scripts/subtitle_bar.py` | 半透明字幕条特效（渐变圆角矩形+高光+文字三层叠加，6种预设样式，Pillow预生成素材） |
| `scripts/effect_library.py` | 特效库统一调用器（检索/搜索/应用/注册，动态加载特效模块） |
| `scripts/intro_builder.py` | 片头生成器（组合蒙版快闪+字幕条，5种模板：快闪/极简/温暖/赛博/标签） |
| `effects/index.json` | 特效库索引v1.1（3个特效+1个工具，按transitions/text/visual/combo分类） |

**脚本使用规范**：所有剪辑脚本必须放在用户当前项目根目录（或子目录），**禁止在 Skill 内部目录创建业务脚本**。复制脚本模板到项目目录后修改参数运行。
