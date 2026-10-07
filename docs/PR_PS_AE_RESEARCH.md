# Pr/Ps/Ae 控制skill预研方向 v1.0

## 背景

当前已完成jianying/comfyui/blender/remotion/anysearch五个底层skill的工程化。
未来需扩展Adobe生态（Premiere Pro / Photoshop / After Effects）控制能力。

## Premiere Pro (Pr)

### 已有基础
- 剪映支持导入.prproj工程（已验证：时间线结构保留，媒体需重新链接）
- .prproj是XML格式（gzip压缩），可直接解析

### 技术路线
1. **XML直接生成**：.prproj本质是gzip压缩的XML，可直接生成
2. **ExtendScript (JSX)**：通过Pr的ExtendScript API控制
3. **CEP面板**：开发Pr扩展面板，通过Node.js通信
4. **Premiere Pro API**：官方API（需授权）

### 核心能力
- 工程创建/读取/修改
- 多轨时间线操作
- 特效/转场/调色
- 导出设置
- 与剪映工程互转

### 优先级：中（剪映已覆盖大部分场景）

---

## Photoshop (Ps)

### 技术路线
1. **ExtendScript (JSX)**：通过Ps的ExtendScript API控制
2. **UDT插件**：UXP (Unified Extensibility Platform) 开发
3. **PSD文件解析**：直接读写.psd文件（psd-tools库）
4. **COM自动化**：Windows COM接口控制Ps

### 核心能力
- 图层操作（创建/修改/合并/蒙版）
- 批量处理（调色/裁剪/导出）
- 模板生成（智能对象替换）
- 抠图/合成
- 与ComfyUI工作流集成

### 优先级：高（影像后期核心工具）

---

## After Effects (Ae)

### 技术路线
1. **ExtendScript (JSX)**：通过Ae的ExtendScript API控制
2. **aescripts + aeplugins**：第三方脚本生态
3. **.aep项目解析**：二进制格式，较复杂
4. **Bodymovin/Lottie**：导出为Web动画

### 核心能力
- 合成创建/修改
- 关键帧动画
- 特效/表达式
- 渲染队列
- 模板系统（.aet）

### 优先级：中（Remotion已覆盖程序化动画，Ae适合复杂MG动画）

---

## 实施建议

### 第一阶段（Ps优先）
1. 调研psd-tools库能力
2. 开发Ps ExtendScript控制脚本
3. 封装为photoshop-controls-skill
4. 与ai-video-editor集成（素材后期处理）

### 第二阶段（Pr）
1. 解析.prproj XML格式
2. 开发工程生成器
3. 封装为premiere-controls-skill
4. 剪映↔Pr工程互转

### 第三阶段（Ae）
1. 调研ExtendScript API
2. 开发基础控制能力
3. 封装为aftereffects-controls-skill

---

## 与现有架构的集成

所有新skill必须遵循 `docs/SKILL_TEMPLATE.md` 规范：
- 统一目录结构
- 统一主控入口（XxxControls类）
- 统一冒烟测试
- 在 `adapters/capability_registry.py` 注册能力
- ai-video-editor通过适配层调用，不直接import
