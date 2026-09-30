r"""
cap_creative - 影视剧创作模块（阶段二预留）

模块定位：
    阶段一（当前）：提供通用质量门框架，用于剪辑质量检查
    阶段二（未来）：剧本解析改编、角色塑造、分镜定版、整剧小样

子模块：
    quality_gate    - 通用质量门框架（已可用）
    draft_extractor - 剪映工程数据提取器（已可用）
    report_renderer - HTML报告生成器（已可用）
    outline         - 大纲改编（预留）
    characters      - 角色塑造（预留）
    script          - 剧本创作（预留）
    storyboard      - 分镜定版（预留）

参考：shuohao-skills (D:\Ai\research\shuohao-skills)
"""

from .quality_gate import (
    GateResult,
    GateReport,
    GateRegistry,
    GateStatus,
    get_registry,
    validate,
)
from .draft_extractor import extract_draft_data, extract_draft_from_content
from .report_renderer import render_html_report

__all__ = [
    "GateResult",
    "GateReport",
    "GateRegistry",
    "GateStatus",
    "get_registry",
    "validate",
    "extract_draft_data",
    "extract_draft_from_content",
    "render_html_report",
]
