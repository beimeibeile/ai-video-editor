"""
特效库调用器
统一接口调用特效库中的各种特效，支持按名称/标签/分类检索

使用方式：
    from effect_library import EffectLibrary
    lib = EffectLibrary()
    lib.list_effects()                    # 列出所有特效
    lib.search("快闪")                    # 搜索特效
    lib.apply("mask_flash_transition", project, **kwargs)  # 应用特效
"""

import logging
logger = logging.getLogger(__name__)


import os
import json
import sys
import importlib.util
from typing import Dict, List, Any, Optional


class EffectLibrary:
    """特效库统一调用器"""

    def __init__(self, skill_root: str = None):
        if skill_root is None:
            skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.skill_root = skill_root
        self.index_path = os.path.join(skill_root, "effects", "index.json")
        self.effects = self._load_index()
        self._modules = {}

    def _load_index(self) -> Dict:
        """加载特效索引"""
        if os.path.exists(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "1.0", "effects": [], "categories": {}}

    def _save_index(self):
        """保存特效索引"""
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self.effects, f, ensure_ascii=False, indent=2)

    def _load_module(self, module_path: str):
        """动态加载特效模块"""
        if module_path in self._modules:
            return self._modules[module_path]

        full_path = os.path.join(self.skill_root, module_path)
        if not os.path.exists(full_path):
            return None

        spec = importlib.util.spec_from_file_location(
            os.path.splitext(os.path.basename(module_path))[0],
            full_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._modules[module_path] = module
        return module

    def list_effects(self, category: str = None) -> List[Dict]:
        """列出所有特效

        Args:
            category: 按分类筛选（transitions/text/visual）
        """
        effects = self.effects.get("effects", [])
        if category:
            effects = [e for e in effects if e.get("category") == category]
        return effects

    def search(self, keyword: str) -> List[Dict]:
        """搜索特效（名称/描述/标签）"""
        keyword = keyword.lower()
        results = []
        for effect in self.effects.get("effects", []):
            search_text = " ".join([
                effect.get("name", ""),
                effect.get("description", ""),
                " ".join(effect.get("tags", [])),
            ]).lower()
            if keyword in search_text:
                results.append(effect)
        return results

    def get_effect(self, effect_id: str) -> Optional[Dict]:
        """获取特效详情"""
        for effect in self.effects.get("effects", []):
            if effect.get("id") == effect_id:
                return effect
        return None

    def apply(self, effect_id: str, project=None, **kwargs) -> Any:
        """应用特效

        Args:
            effect_id: 特效ID
            project: JyProject实例（部分特效需要）
            **kwargs: 特效参数

        Returns:
            特效执行结果
        """
        effect = self.get_effect(effect_id)
        if not effect:
            raise ValueError(f"特效 '{effect_id}' 不存在")

        module = self._load_module(effect["module"])
        if not module:
            raise ImportError(f"无法加载特效模块: {effect['module']}")

        # 根据特效类型选择调用方式
        if effect_id == "mask_flash_transition":
            return self._apply_mask_flash(module, project, **kwargs)
        elif effect_id == "subtitle_bar":
            return self._apply_subtitle_bar(module, project, **kwargs)
        else:
            # 通用：尝试调用模块中的主函数
            main_func = getattr(module, "main", None) or getattr(module, "create", None)
            if main_func:
                return main_func(**kwargs)
            raise NotImplementedError(f"特效 '{effect_id}' 暂不支持统一调用")

    def _apply_mask_flash(self, module, project, **kwargs):
        """应用蒙版展开快闪特效"""
        mode = kwargs.pop("mode", "basic")  # basic / stripe / apply_to_segments
        if mode == "basic":
            return module.create_mask_flash_basic(**kwargs)
        elif mode == "stripe":
            return module.create_stripe_flash(**kwargs)
        elif mode == "apply":
            return module.apply_expand_to_segments(project, **kwargs)
        else:
            return module.create_mask_flash_basic(**kwargs)

    def _apply_subtitle_bar(self, module, project, **kwargs):
        """应用半透明字幕条特效"""
        if project is None:
            raise ValueError("字幕条特效需要传入project参数")
        items = kwargs.pop("items", None)
        if items:
            return module.add_subtitle_bars(project, items, **kwargs)
        return module.add_subtitle_bar(project, **kwargs)

    def register(self, effect_id: str, name: str, category: str,
                 module_path: str, description: str = "",
                 tags: List[str] = None, api: List[str] = None,
                 source: str = "", difficulty: str = "medium"):
        """注册新特效到索引"""
        effect = {
            "id": effect_id,
            "name": name,
            "category": category,
            "module": module_path,
            "source": source,
            "difficulty": difficulty,
            "status": "registered",
            "description": description,
            "tags": tags or [],
            "api": api or [],
        }
        # 检查是否已存在
        for i, e in enumerate(self.effects.get("effects", [])):
            if e.get("id") == effect_id:
                self.effects["effects"][i] = effect
                self._save_index()
                return effect
        self.effects.setdefault("effects", []).append(effect)
        self._save_index()
        return effect

    def print_library(self):
        """打印特效库概览"""
        logger.info("=" * 60)
        logger.info(f"特效库 v{self.effects.get('version', '1.0')}")
        logger.info(f"共 {len(self.effects.get('effects', []))} 个特效")
        logger.info("=" * 60)

        categories = self.effects.get("categories", {})
        for cat_id, cat_name in categories.items():
            cat_effects = [e for e in self.effects.get("effects", []) if e.get("category") == cat_id]
            if cat_effects:
                logger.info(f"\n【{cat_name}】({len(cat_effects)})")
                for e in cat_effects:
                    status = "✅" if e.get("status") == "verified" else "🔧"
                    logger.info(f"  {status} {e['id']}: {e['name']}")
                    logger.info(f"     {e.get('description', '')[:50]}")
                    logger.info(f"     标签: {', '.join(e.get('tags', []))}")


if __name__ == "__main__":
    lib = EffectLibrary()
    lib.print_library()
    logger.info("\n搜索'字幕':")
    for e in lib.search("字幕"):
        logger.info(f"  - {e['id']}: {e['name']}")
