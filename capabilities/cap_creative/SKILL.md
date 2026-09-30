# cap_creative — 影视剧创作模块

## 定位

ai-video-editor 三阶段路线图的**阶段二**核心模块，当前阶段提供质量门框架底座。

```
阶段一（当前）：影视级剪片功底
  └─ cap_creative 提供质量门框架，用于剪辑质量检查

阶段二（未来）：影视剧创作
  ├─ outline    — 剧本解析改编（小说→短剧大纲）
  ├─ characters — 角色性格与分剧情重塑
  ├─ script     — 剧本创作与多轮打造
  └─ storyboard — 全剧分镜头定版

阶段三：素材及分镜制作剪辑流程
  └─ 阶段一+阶段二串联成完整 pipeline
```

## 当前可用能力

### 质量门框架 (`quality_gate.py`)

通用质量门检查框架，参考 shuohao-skills 的14-18道确定性检查机制。

**已注册的质量门类别：**

| 类别 | 门数量 | 用途 |
|------|--------|------|
| `edit` | 7道 | 剪辑质量检查（时长/片段数/转场对齐/字幕覆盖/画幅/帧对齐/黑屏） |
| `storyboard` | 3道 | 分镜质量检查（镜头时长/钩子/节拍认领） |

**使用方法：**

```python
from capabilities.cap_creative import validate, get_registry

# 批量检查
report = validate("edit", edit_data)
print(report.summary())
print(report.all_passed)  # True/False

# 注册自定义门
def my_gate(data):
    from capabilities.cap_creative import GateResult
    if data.get("foo") != "bar":
        return GateResult.fail("C001", "自定义门", "foo不是bar")
    return GateResult.pass_("C001", "自定义门")

registry = get_registry()
registry.register("edit", my_gate)
```

**质量门设计原则：**
1. 每道门是确定性函数，不靠模型自觉
2. 每道门必须有击穿用例，证明它真的会拦
3. 检查结果可序列化为 JSON，可渲染为报告
4. 门可注册、可扩展，不修改核心代码

## 预留模块（阶段二）

### outline — 大纲改编
- 小说→短剧大纲五件套（改编说明/人物表/爽点表/分集梗概/资产清单）
- 质量门：角色分档上限、主场景上限随集数动态、爽点间隔≤3集、第1集有钩子

### characters — 角色塑造
- 角色设定集（人物画像/形象提示词/音色提示词/角色设定图）
- 锚点一致性方案（正面全身锚点，其余视图只参考锚点）

### script — 剧本创作
- 场次+节拍流（动作与台词交替）
- 逐集时长按语速确定性折算
- 台词本按角色聚合带音色提示词对接TTS

### storyboard — 分镜定版
- 三层结构：段(≤15秒)→分镜(2-5秒)→分镜图
- 镜头认领节拍机制（可机械对账）
- 投产包导出（H3/Seedance提示词+参考图清单）

## 参考项目

shuohao-skills（只读研究参考，不直接集成）：
- 位置：`D:\Ai\research\shuohao-skills`
- 核心借鉴：质量门机制、锚点一致性、分镜投产包、报告三件套
- License: Apache 2.0

## 数据格式约定

所有子模块的输入输出统一使用 JSON，结构参考 shuohao-skills：
- `outline.json` — 大纲数据
- `cast.json` — 角色数据
- `script.json` — 剧本数据
- `storyboard.json` — 分镜数据

当前阶段先建立格式约定，未来模块开发时直接对齐。
