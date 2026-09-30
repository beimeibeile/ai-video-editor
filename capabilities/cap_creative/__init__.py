"""
cap_creative - 影视剧创作模块（阶段二预留）

模块定位：
    阶段一（当前）：提供通用质量门框架，用于剪辑质量检查
    阶段二（未来）：剧本解析改编、角色塑造、分镜定版、整剧小样

子模块：
    quality_gate  - 通用质量门框架（已可用）
    outline       - 大纲改编（预留）
    characters    - 角色塑造（预留）
    script        - 剧本创作（预留）
    storyboard    - 分镜定版（预留）

参考：shuohao-skills (D:\Ai\research\shuohao-skills)
"""

from .quality_gate import (
    QualityGate,
    GateResult,
    GateReport,
    GateRegistry,
    GateStatus,
    get_registry,
    validate,
)

__all__ = [
    "QualityGate",
    "GateResult",
    "GateReport",
    "GateRegistry",
    "GateStatus",
    "get_registry",
    "validate",
]
