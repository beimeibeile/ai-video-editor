# HyperFrames + ui2v 研究报告

> 研究日期：2026-10-04
> 研究目的：评估HyperFrames作为ai-video-editor系统第4个执行器的可行性，以及ui2v动效包管理对特效库的借鉴价值

---

## 一、HyperFrames 是什么

**HeyGen开源的HTML-to-MP4渲染框架**，42K stars，TypeScript编写。

核心理念：**视频 = 构建产物（build artifact）**。写HTML+GSAP动画代码，运行命令，得到确定性MP4。和Remotion类似，但更agent-friendly。

### 技术架构

```
HTML/CSS/GSAP → Puppeteer（headless Chromium）→ 逐帧截图 → FFmpeg编码 → MP4
```

关键机制：`gsap.globalTimeline.seek(time)` —— 跳转到动画时间线任意位置截图，不需要实时播放。这解决了Remotion中GSAP动画丢帧的问题。

### 核心概念

| 概念 | 说明 |
|---|---|
| **Composition（组合）** | 基本分组单元，支持嵌套。每个组合有自己的GSAP时间线 |
| **Clip（片段）** | video/img/audio/div[composition]，用data-attributes描述时间 |
| **data-start** | 开始时间，支持绝对秒数或相对引用（`intro + 2`） |
| **data-duration** | 持续时间（img必填，video/audio可选） |
| **data-track-index** | 轨道号，高层轨道在前面，同轨道不能重叠 |
| **data-composition-id** | 组合ID，用于嵌套和时间线注册 |
| **data-width/height** | 渲染分辨率（仅根组合需要） |

### 两层架构

1. **HTML层**：声明式结构——什么播放、什么时候、哪个轨道
2. **Script层**：GSAP动画创意——转场、特效、动态DOM、Canvas、SVG

框架自动管理：媒体播放、片段挂载/卸载、时间线同步、媒体加载。脚本不控制媒体播放，只做视觉动画。

### 时间线契约

每个组合必须有脚本创建GSAP时间线并注册：
```js
const tl = gsap.timeline({ paused: true });
window.__timelines["<composition-id>"] = tl;
```
框架自动嵌套子组合时间线，不需要手动管理。

### Agent集成

- **MCP Server**：agent可以直接调用渲染工具
- **skills.sh**：`npx skills add heygen-com/hyperframes` 安装skill集
- **CLI**：`hyperframes render` 非交互式渲染
- 每次渲染是全新Puppeteer实例，无状态泄漏

### 输出

- 默认H.264 MP4，支持H.265/VP9/ProRes
- 支持alpha通道（VP9透明或ProRes 4444）
- 确定性输出：相同HTML总是产生相同视频

---

## 二、ui2v 是什么

**视频动效资产库**，让动效像UI组件一样可复用。

两层架构：
- **HyperFrames**：创作/预览/渲染动效
- **UI2V CLI**：动效包的搜索/安装/发布/同步/更新

### 包格式

```
my-motion/
├── registry-item.json    # type: "hyperframes:block"
├── index.html            # 入口组合HTML
└── assets/               # 依赖的媒体资源
```

### CLI命令

```bash
ui2v search "logo sting"     # 搜索动效
ui2v install <slug>          # 安装到工作区
ui2v motion publish ./motion --version 1.0.0  # 发布
ui2v update --all            # 更新所有
ui2v list                    # 列出已安装
```

---

## 三、对ai-video-editor系统的价值

### 3.1 作为P25第4个执行器（高价值）

| 执行器 | 擅长 | 不擅长 |
|---|---|---|
| **剪映** | 素材合成、多轨道、蒙版、关键帧、转场 | 精确文字排版、代码控制的复杂动画 |
| **Blender** | 3D素材、粒子、物理模拟 | 2D文字动画、快速迭代 |
| **ComfyUI** | AI生图/生视频、TTS | 精确时间控制的动画 |
| **HyperFrames**（新增） | 文字排版、动态字幕、转场特效、片头片尾、数据可视化 | 真实素材合成、AI生成内容 |

**HyperFrames最适合的场景**：
- 动态字幕和文字排版（HTML/CSS精确控制）
- 转场特效（GSAP动画，确定性渲染）
- 片头片尾（logo sting、title sequence）
- 数据可视化视频（图表动画）
- 表情包/贴纸动画层

### 3.2 和导演引擎的契合度

导演引擎核心理念：**结构化输入 → 代码生成 → 确定性渲染**

HyperFrames完全契合：
- P24指令翻译器可以把"文字样式/转场/特效"指令翻译成HTML+GSAP代码
- P25调度器调用`hyperframes render`生成MP4
- 生成的MP4可以作为素材导入剪映工程合成

### 3.3 ui2v包管理对特效库的借鉴

当前特效库（effect_library）是本地JSON索引，无版本无分发。可升级为：
- 特效包版本化管理（semver）
- 远程注册表（搜索/安装/更新）
- 特效包 = HyperFrames组合 + 元数据 + 缩略图
- `effect install <slug>` 一键安装

---

## 四、可行性评估

### 优势
1. **Agent-First设计**：MCP + skills + CLI，专门为AI agent设计
2. **确定性输出**：相同代码相同结果，适合自动化流水线
3. **HTML/CSS/GSAP**：成熟的Web技术栈，学习成本低
4. **Seek-driven渲染**：比Remotion更适合GSAP动画
5. **HeyGen背书**：42K stars，活跃维护
6. **本地运行**：不需要云端API，隐私安全

### 风险/限制
1. **需要Node.js 22+**：当前环境是Python311为主，需要安装Node
2. **Puppeteer依赖Chromium**：首次安装需要下载Chromium
3. **不做真实素材合成**：需要和剪映配合，不能单独完成全片
4. **GSAP学习曲线**：虽然是成熟技术，但需要掌握GSAP时间线API
5. **中文渲染**：需要确保中文字体在Puppeteer中正确加载

### 实施路径

**P28: HyperFrames执行器集成**
1. 安装Node.js 22+ 和 HyperFrames CLI
2. 验证基础渲染（简单HTML→MP4）
3. 封装HyperFramesExecutor（P25执行器）
4. P24翻译器增加"文字动画/转场特效"→HTML+GSAP代码生成
5. 生成的MP4自动导入剪映工程合成
6. 用《酒店外卖风云》实例验证：动态字幕用HyperFrames生成

**P29: 特效库包管理升级**（借鉴ui2v）
1. 特效包格式标准化（registry-item.json + index.html + assets）
2. 版本化管理（semver）
3. 本地注册表（搜索/安装/更新）
4. 可选：远程注册表发布

---

## 五、关键参考链接

- HyperFrames GitHub: https://github.com/heygen-com/hyperframes
- ui2v GitHub: https://github.com/illli-studio/ui2v
- HyperFrames文档: https://cdn.jsdelivr.net/npm/@hyperframes/core@0.2.4/docs/versions/v0.1/core.md
- HyperFrames vs Remotion对比: https://arceapps.com/blog/hyperframes-vs-remotion-2026/
- Agent-First设计深度分析: https://dev.to/mech_app_ai/hyperframes-html-to-mp4-rendering-as-an-agent-first-primitive-33k7
- html-video（OpenDesign元层）: https://open-design.ai/html-video/

---

## 六、结论

**HyperFrames值得集成**，作为P25调度器的第4个执行器，和剪映形成互补。它特别适合文字排版、动态字幕、转场特效这类"代码精确控制"的场景，能显著提升系统在这些方面的能力上限。

ui2v的包管理设计也值得借鉴，用于升级当前的特效库，让特效资产可版本化、可搜索、可安装、可发布。

建议优先级：
1. **P28 HyperFrames执行器**（高价值，和当前TTS调教完成后的下一步自然衔接）
2. **P29 特效库包管理**（中价值，可在P28稳定后推进）
