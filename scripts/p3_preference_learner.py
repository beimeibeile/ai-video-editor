#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3-6 用户偏好自学习系统
5类偏好：特效偏好/节奏偏好/风格偏好/BGM偏好/参数偏好
支持显式反馈（点赞/点踩）+隐式反馈（人工修改记录）+统计积累
本地存储，支持导出/重置
"""
import os
import json
import time
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from collections import Counter
import logging
logger = logging.getLogger(__name__)


PREFERENCE_DIR = r"D:\DobaoWork_Project\Ai_Video_Editor\knowledge\user_preferences"


@dataclass
class PreferenceRecord:
    """偏好记录"""
    timestamp: float
    preference_type: str  # effect / rhythm / style / bgm / param
    item_id: str  # 特效名/风格名/BGM名/参数名
    action: str  # accept / reject / modify / use
    context: Dict[str, Any] = field(default_factory=dict)
    original_value: Any = None
    modified_value: Any = None


@dataclass
class UserPreferenceProfile:
    """用户偏好画像"""
    effect_prefs: Dict[str, float] = field(default_factory=dict)  # 特效名→偏好分(0-1)
    rhythm_prefs: Dict[str, float] = field(default_factory=dict)  # 节奏类型→偏好分
    style_prefs: Dict[str, float] = field(default_factory=dict)  # 风格→偏好分
    bgm_prefs: Dict[str, float] = field(default_factory=dict)  # BGM→偏好分
    param_prefs: Dict[str, Any] = field(default_factory=dict)  # 参数名→常用值
    total_records: int = 0
    created_at: float = 0
    updated_at: float = 0


class PreferenceLearner:
    """用户偏好自学习器"""

    def __init__(self, profile_path: str = None):
        self.profile_path = profile_path or os.path.join(PREFERENCE_DIR, "user_profile.json")
        self.records_path = os.path.join(PREFERENCE_DIR, "records.jsonl")
        self.profile = UserPreferenceProfile()
        self.records: List[PreferenceRecord] = []
        self._load()

    def _load(self):
        """加载偏好数据"""
        os.makedirs(PREFERENCE_DIR, exist_ok=True)

        # 加载画像
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.profile = UserPreferenceProfile(**data)
            except Exception as e:
                logger.info(f"[WARN] 加载偏好画像失败: {e}")

        # 加载记录
        if os.path.exists(self.records_path):
            try:
                with open(self.records_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            self.records.append(PreferenceRecord(**data))
            except Exception as e:
                logger.info(f"[WARN] 加载偏好记录失败: {e}")

    def _save_profile(self):
        """保存画像"""
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        self.profile.updated_at = time.time()
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(self.profile.__dict__, f, ensure_ascii=False, indent=2)

    def _save_record(self, record: PreferenceRecord):
        """追加保存记录"""
        os.makedirs(os.path.dirname(self.records_path), exist_ok=True)
        with open(self.records_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")
        self.records.append(record)
        self.profile.total_records = len(self.records)

    def record_feedback(self, preference_type: str, item_id: str,
                         action: str, context: Dict[str, Any] = None,
                         original_value: Any = None,
                         modified_value: Any = None):
        """
        记录用户反馈

        Args:
            preference_type: 偏好类型 (effect/rhythm/style/bgm/param)
            item_id: 项目ID（特效名/风格名等）
            action: 动作 (accept/reject/modify/use)
            context: 上下文信息
            original_value: 原始值（modify时使用）
            modified_value: 修改后的值（modify时使用）
        """
        record = PreferenceRecord(
            timestamp=time.time(),
            preference_type=preference_type,
            item_id=item_id,
            action=action,
            context=context or {},
            original_value=original_value,
            modified_value=modified_value,
        )
        self._save_record(record)
        self._update_profile(record)
        self._save_profile()

    def _update_profile(self, record: PreferenceRecord):
        """根据记录更新画像"""
        # 动作→分数映射
        action_score = {
            "accept": 0.3,   # 接受（不修改直接用）
            "use": 0.2,      # 使用
            "modify": -0.1,  # 修改（部分满意）
            "reject": -0.5,  # 拒绝
        }
        delta = action_score.get(record.action, 0)

        # 更新对应偏好类型
        pref_map = {
            "effect": self.profile.effect_prefs,
            "rhythm": self.profile.rhythm_prefs,
            "style": self.profile.style_prefs,
            "bgm": self.profile.bgm_prefs,
        }

        if record.preference_type in pref_map:
            target = pref_map[record.preference_type]
            current = target.get(record.item_id, 0.5)
            new_score = max(0, min(1, current + delta))
            target[record.item_id] = round(new_score, 3)

        # 参数偏好记录常用值
        if record.preference_type == "param" and record.modified_value is not None:
            self.profile.param_prefs[record.item_id] = record.modified_value

    def get_preference(self, preference_type: str, item_id: str,
                       default: float = 0.5) -> float:
        """获取某个项目的偏好分"""
        pref_map = {
            "effect": self.profile.effect_prefs,
            "rhythm": self.profile.rhythm_prefs,
            "style": self.profile.style_prefs,
            "bgm": self.profile.bgm_prefs,
        }
        if preference_type in pref_map:
            return pref_map[preference_type].get(item_id, default)
        return default

    def get_top_preferences(self, preference_type: str,
                             top_n: int = 10) -> List[Tuple[str, float]]:
        """获取偏好度最高的项目"""
        pref_map = {
            "effect": self.profile.effect_prefs,
            "rhythm": self.profile.rhythm_prefs,
            "style": self.profile.style_prefs,
            "bgm": self.profile.bgm_prefs,
        }
        if preference_type not in pref_map:
            return []
        sorted_items = sorted(pref_map[preference_type].items(),
                              key=lambda x: x[1], reverse=True)
        return sorted_items[:top_n]

    def get_param_preference(self, param_name: str, default: Any = None) -> Any:
        """获取参数偏好值"""
        return self.profile.param_prefs.get(param_name, default)

    def apply_to_effect_plan(self, candidates: List[str],
                              preference_type: str = "effect",
                              top_n: int = 5) -> List[str]:
        """
        将偏好应用到候选列表（重新排序）

        Args:
            candidates: 候选列表
            preference_type: 偏好类型
            top_n: 返回前N个

        Returns:
            按偏好排序后的候选列表
        """
        scored = [(c, self.get_preference(preference_type, c)) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in scored[:top_n]]

    def get_stats(self) -> Dict[str, Any]:
        """获取偏好统计"""
        return {
            "total_records": self.profile.total_records,
            "effect_prefs_count": len(self.profile.effect_prefs),
            "rhythm_prefs_count": len(self.profile.rhythm_prefs),
            "style_prefs_count": len(self.profile.style_prefs),
            "bgm_prefs_count": len(self.profile.bgm_prefs),
            "param_prefs_count": len(self.profile.param_prefs),
            "top_effects": self.get_top_preferences("effect", 5),
            "top_styles": self.get_top_preferences("style", 5),
            "created_at": self.profile.created_at,
            "updated_at": self.profile.updated_at,
        }

    def export(self, output_path: str):
        """导出偏好数据"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        data = {
            "profile": self.profile.__dict__,
            "records": [r.__dict__ for r in self.records],
            "stats": self.get_stats(),
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path

    def reset(self):
        """重置所有偏好数据"""
        self.profile = UserPreferenceProfile(created_at=time.time())
        self.records = []
        if os.path.exists(self.profile_path):
            os.remove(self.profile_path)
        if os.path.exists(self.records_path):
            os.remove(self.records_path)
        self._save_profile()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="用户偏好自学习系统")
    parser.add_argument("action", choices=["stats", "record", "export", "reset", "test"],
                        help="操作")
    parser.add_argument("--type", help="偏好类型")
    parser.add_argument("--item", help="项目ID")
    parser.add_argument("--action-type", help="动作类型")
    parser.add_argument("--output", help="输出路径")
    args = parser.parse_args()

    learner = PreferenceLearner()

    if args.action == "stats":
        logger.info(json.dumps(learner.get_stats(), ensure_ascii=False, indent=2))

    elif args.action == "record":
        if not all([args.type, args.item, args.action_type]):
            logger.info("需要 --type --item --action-type 参数")
            return
        learner.record_feedback(args.type, args.item, args.action_type)
        logger.info(f"已记录: {args.type}/{args.item} → {args.action_type}")

    elif args.action == "export":
        path = learner.export(args.output or "user_preferences_export.json")
        logger.info(f"已导出: {path}")

    elif args.action == "reset":
        learner.reset()
        logger.info("已重置所有偏好数据")

    elif args.action == "test":
        # 测试：模拟一些反馈
        logger.info("=== 测试用户偏好自学习 ===")
        learner.record_feedback("effect", "渐显", "accept", {"emotion": "happy"})
        learner.record_feedback("effect", "震动", "reject", {"emotion": "calm"})
        learner.record_feedback("style", "douyin", "use")
        learner.record_feedback("style", "cinematic", "use")
        learner.record_feedback("param", "filter_intensity", "modify",
                                original_value=70, modified_value=50)
        learner.record_feedback("rhythm", "fast", "accept")

        logger.info("\n=== 统计 ===")
        logger.info(json.dumps(learner.get_stats(), ensure_ascii=False, indent=2))

        logger.info("\n=== 偏好应用测试 ===")
        candidates = ["渐显", "震动", "放大", "淡入", "弹入"]
        ranked = learner.apply_to_effect_plan(candidates, "effect")
        logger.info(f"候选: {candidates}")
        logger.info(f"按偏好排序: {ranked}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
