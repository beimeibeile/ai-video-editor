"""
通用素材库模块 (cap_asset_library)
带逻辑索引的素材管理系统，秒级检索最佳匹配素材

核心能力：
- 多维标签索引：type/style/mood/tags/duration/format
- 智能匹配：根据上下文加权评分推荐
- 使用统计：越用越优先
- 自动扫描：目录扫描自动生成索引
- 素材管理：添加/更新/移除

使用：
    from cap_asset_library import get_library
    lib = get_library()
    lib.scan_directory()  # 扫描素材目录
    best = lib.get_best_match("sfx", context="片头主标题出现", style="impact")
"""
from .asset_library import AssetLibrary, get_library

__all__ = ["AssetLibrary", "get_library"]
