# Skill 模板规范 v1.0

> 所有新建底层控制skill（Pr/Ps/Ae等）必须遵循此模板，确保与ai-video-editor架构兼容。

## 目录结构

```
<skill-name>/
├── SKILL.md                    # 技能描述（YAML frontmatter + 使用文档）
├── README.md                   # 项目说明
├── pyproject.toml              # 包配置
├── requirements.txt            # 依赖
├── <skill_name>_controls.py    # 主控入口（统一Controls类）
├── capabilities/               # 能力模块（可插拔）
│   ├── cap_api_wrapper/        # API封装
│   │   ├── __init__.py
│   │   ├── api.py              # 核心API类
│   │   └── client.py           # 客户端
│   ├── cap_<feature1>/         # 功能模块1
│   │   ├── __init__.py
│   │   └── <feature>.py
│   └── cap_<feature2>/
├── tests/                      # 测试
│   ├── __init__.py
│   ├── conftest.py
│   └── test_smoke.py           # 冒烟测试（≥5个用例）
├── examples/                   # 示例脚本
│   ├── 01_minimal_status.py
│   └── 02_<feature>.py
├── docs/                       # 文档
│   └── API_REFERENCE.md
├── rules/                      # AI调用规则
│   └── usage_rules.md
└── templates/                  # 模板/预设（可选）
```

## 主控入口规范

```python
"""<skill_name>_controls.py - 统一入口"""
import os, sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# capabilities路径注入
_CAP_DIR = Path(__file__).parent / "capabilities"
if str(_CAP_DIR) not in sys.path:
    sys.path.insert(0, str(_CAP_DIR))

class <SkillName>Controls:
    """统一控制类"""
    def __init__(self, **kwargs):
        self.status = {"initialized": False, "features": {}}
        self._init_features()

    def _init_features(self):
        """初始化各能力模块（try/except降级）"""
        pass

    def get_status(self) -> Dict[str, Any]:
        """返回状态信息"""
        return self.status

    @classmethod
    def create(cls, **kwargs) -> "<SkillName>Controls":
        """工厂方法"""
        return cls(**kwargs)

def create_controls(**kwargs) -> "<SkillName>Controls":
    return <SkillName>Controls.create(**kwargs)
```

## SKILL.md 规范

```yaml
---
name: <skill-name>
version: 1.0.0
description: |
  <技能描述>。核心能力：xxx、xxx、xxx。
  Use when asked to <触发词1>、<触发词2>.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
triggers:
  - <触发词1>
  - <触发词2>
metadata:
  license: MIT
  requires:
    bins:
      - <必需二进制>
    services:
      - <必需服务>
---
```

## 冒烟测试规范

```python
# tests/test_smoke.py
import os, sys
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)

passed = 0; failed = 0
def check(name, func):
    global passed, failed
    try:
        func(); print(f"  PASS: {name}"); passed += 1
    except Exception as e:
        print(f"  FAIL: {name} -> {type(e).__name__}: {e}"); failed += 1

# 1. 模块导入测试
# 2. 主控初始化测试
# 3. 能力模块测试
# 4. 常量/配置测试

print(f"=== 结果: {passed} passed, {failed} failed ===")
sys.exit(1 if failed > 0 else 0)
```

## 能力注册规范

新skill创建后，必须在 `ai-video-editor/adapters/capability_registry.py` 的 `_auto_discover()` 方法中注册：

```python
"<skill-name>": {
    "name": "<显示名称>",
    "capabilities": [
        Capability("<能力名>", "<描述>", "<skill-name>",
                   "<入口路径>", ["<依赖>"], priority=<1-10>),
    ],
},
```

## 验收标准（DoD）

1. ✅ 目录结构完整（capabilities/tests/examples/docs/rules）
2. ✅ 主控入口可导入、可初始化
3. ✅ 冒烟测试 ≥5个用例，全部通过
4. ✅ pyproject.toml + requirements.txt
5. ✅ SKILL.md 符合规范
6. ✅ API_REFERENCE.md 文档完整
7. ✅ usage_rules.md AI调用规则
8. ✅ 在能力注册中心注册
9. ✅ 无硬编码路径（通过配置/环境变量）
10. ✅ 独立工作（不import其他skill）
