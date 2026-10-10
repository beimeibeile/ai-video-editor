#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T3-3: 自学习与进化系统
收集使用数据，评估效果，自动优化参数，沉淀最佳实践
"""
import os
import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# 数据存储目录
DATA_DIR = r"D:\DobaoWork_Project\Ai_Video_Editor\self_learning"
os.makedirs(DATA_DIR, exist_ok=True)

# 数据文件
USAGE_LOG = os.path.join(DATA_DIR, "usage_log.jsonl")
QUALITY_LOG = os.path.join(DATA_DIR, "quality_log.jsonl")
PARAM_STATS = os.path.join(DATA_DIR, "param_stats.json")
BEST_PRACTICES = os.path.join(DATA_DIR, "best_practices.json")
PITFALLS = os.path.join(DATA_DIR, "pitfalls.json")


@dataclass
class UsageRecord:
    """使用记录"""
    timestamp: str
    module: str  # 模块名称（tts/h3/comfyui/template/pipeline等）
    action: str  # 操作类型
    params: Dict[str, Any]  # 参数
    success: bool  # 是否成功
    duration: float  # 耗时（秒）
    error: Optional[str] = None  # 错误信息
    output_path: Optional[str] = None  # 输出路径
    quality_score: Optional[float] = None  # 质量评分（0-10）


@dataclass
class QualityRecord:
    """质量评估记录"""
    timestamp: str
    module: str
    output_path: str
    score: float  # 综合评分（0-10）
    dimensions: Dict[str, float]  # 各维度评分
    feedback: Optional[str] = None  # 用户反馈


@dataclass
class ParamStat:
    """参数统计"""
    param_name: str
    module: str
    values: Dict[str, Any] = field(default_factory=dict)  # 值->统计
    best_value: Optional[Any] = None
    best_success_rate: float = 0.0
    best_avg_duration: float = 0.0


@dataclass
class BestPractice:
    """最佳实践"""
    id: str
    module: str
    title: str
    description: str
    params: Dict[str, Any]
    success_rate: float
    avg_duration: float
    created_at: str
    usage_count: int = 0


@dataclass
class Pitfall:
    """踩坑记录"""
    id: str
    module: str
    symptom: str  # 现象
    root_cause: str  # 根因
    solution: str  # 解决方案
    error_pattern: Optional[str] = None  # 错误模式（用于自动识别）
    created_at: str = ""
    hit_count: int = 0


class SelfLearningSystem:
    """自学习与进化系统"""

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.usage_log = os.path.join(self.data_dir, "usage_log.jsonl")
        self.quality_log = os.path.join(self.data_dir, "quality_log.jsonl")
        self.param_stats_file = os.path.join(self.data_dir, "param_stats.json")
        self.best_practices_file = os.path.join(self.data_dir, "best_practices.json")
        self.pitfalls_file = os.path.join(self.data_dir, "pitfalls.json")

        # 加载已有数据
        self.param_stats = self._load_json(self.param_stats_file, {})
        self.best_practices = self._load_json(self.best_practices_file, {})
        self.pitfalls = self._load_json(self.pitfalls_file, {})

    def _load_json(self, path: str, default: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return default
        return default

    def _save_json(self, path: str, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _append_jsonl(self, path: str, record: Dict):
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_usage(self, module: str, action: str, params: Dict,
                  success: bool, duration: float, error: str = None,
                  output_path: str = None, quality_score: float = None):
        """记录使用情况"""
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            module=module,
            action=action,
            params=params,
            success=success,
            duration=round(duration, 2),
            error=error,
            output_path=output_path,
            quality_score=quality_score,
        )
        self._append_jsonl(self.usage_log, asdict(record))
        self._update_param_stats(module, action, params, success, duration)
        logger.debug(f"[学习系统] 记录: {module}/{action} 成功={success} 耗时={duration:.1f}s")

    def log_quality(self, module: str, output_path: str, score: float,
                    dimensions: Dict[str, float] = None, feedback: str = None):
        """记录质量评估"""
        record = QualityRecord(
            timestamp=datetime.now().isoformat(),
            module=module,
            output_path=output_path,
            score=score,
            dimensions=dimensions or {},
            feedback=feedback,
        )
        self._append_jsonl(self.quality_log, asdict(record))
        logger.info(f"[学习系统] 质量记录: {module} 评分={score}/10")

    def _update_param_stats(self, module: str, action: str, params: Dict,
                            success: bool, duration: float):
        """更新参数统计"""
        key = f"{module}/{action}"
        if key not in self.param_stats:
            self.param_stats[key] = {"total": 0, "success": 0, "total_duration": 0,
                                     "params": {}}

        stats = self.param_stats[key]
        stats["total"] += 1
        if success:
            stats["success"] += 1
        stats["total_duration"] += duration

        # 统计每个参数的值
        for param_name, param_value in params.items():
            # 只统计简单类型参数
            if isinstance(param_value, (str, int, float, bool)):
                value_str = str(param_value)
                if param_name not in stats["params"]:
                    stats["params"][param_name] = {}
                if value_str not in stats["params"][param_name]:
                    stats["params"][param_name][value_str] = {"count": 0, "success": 0, "total_duration": 0}
                pstats = stats["params"][param_name][value_str]
                pstats["count"] += 1
                if success:
                    pstats["success"] += 1
                pstats["total_duration"] += duration

        self._save_json(self.param_stats_file, self.param_stats)

    def get_best_params(self, module: str, action: str) -> Dict[str, Any]:
        """获取最优参数推荐"""
        key = f"{module}/{action}"
        if key not in self.param_stats:
            return {}

        stats = self.param_stats[key]
        best_params = {}

        for param_name, value_stats in stats.get("params", {}).items():
            best_value = None
            best_rate = -1
            best_duration = float("inf")

            for value_str, vstats in value_stats.items():
                if vstats["count"] >= 2:  # 至少有2次样本
                    rate = vstats["success"] / vstats["count"]
                    avg_dur = vstats["total_duration"] / vstats["count"]
                    # 优先成功率，其次耗时
                    if rate > best_rate or (rate == best_rate and avg_dur < best_duration):
                        best_rate = rate
                        best_duration = avg_dur
                        best_value = value_str

            if best_value is not None:
                # 尝试转换回原始类型
                try:
                    if best_value.lower() == "true":
                        best_value = True
                    elif best_value.lower() == "false":
                        best_value = False
                    else:
                        try:
                            best_value = int(best_value)
                        except ValueError:
                            try:
                                best_value = float(best_value)
                            except ValueError:
                                pass
                except Exception:
                    pass
                best_params[param_name] = best_value

        return best_params

    def get_module_stats(self, module: str = None) -> Dict[str, Any]:
        """获取模块统计"""
        result = {}
        for key, stats in self.param_stats.items():
            mod = key.split("/")[0]
            if module and mod != module:
                continue
            if mod not in result:
                result[mod] = {"total": 0, "success": 0, "total_duration": 0, "actions": {}}
            result[mod]["total"] += stats["total"]
            result[mod]["success"] += stats["success"]
            result[mod]["total_duration"] += stats["total_duration"]
            action = key.split("/")[1] if "/" in key else "unknown"
            result[mod]["actions"][action] = {
                "total": stats["total"],
                "success": stats["success"],
                "success_rate": round(stats["success"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0,
                "avg_duration": round(stats["total_duration"] / stats["total"], 1) if stats["total"] > 0 else 0,
            }

        # 计算总成功率
        for mod in result:
            r = result[mod]
            r["success_rate"] = round(r["success"] / r["total"] * 100, 1) if r["total"] > 0 else 0
            r["avg_duration"] = round(r["total_duration"] / r["total"], 1) if r["total"] > 0 else 0

        return result

    def add_pitfall(self, module: str, symptom: str, root_cause: str,
                    solution: str, error_pattern: str = None) -> str:
        """添加踩坑记录"""
        pitfall_id = f"pit_{int(time.time())}"
        pitfall = Pitfall(
            id=pitfall_id,
            module=module,
            symptom=symptom,
            root_cause=root_cause,
            solution=solution,
            error_pattern=error_pattern,
            created_at=datetime.now().isoformat(),
        )
        self.pitfalls[pitfall_id] = asdict(pitfall)
        self._save_json(self.pitfalls_file, self.pitfalls)
        logger.info(f"[学习系统] 新增踩坑记录: {module} - {symptom[:30]}")
        return pitfall_id

    def match_pitfall(self, error_message: str) -> Optional[Dict]:
        """匹配踩坑记录（自动诊断）"""
        for pid, pitfall in self.pitfalls.items():
            if pitfall.get("error_pattern") and pitfall["error_pattern"] in error_message:
                pitfall["hit_count"] = pitfall.get("hit_count", 0) + 1
                self._save_json(self.pitfalls_file, self.pitfalls)
                return pitfall
        return None

    def add_best_practice(self, module: str, title: str, description: str,
                          params: Dict, success_rate: float, avg_duration: float) -> str:
        """添加最佳实践"""
        bp_id = f"bp_{int(time.time())}"
        bp = BestPractice(
            id=bp_id,
            module=module,
            title=title,
            description=description,
            params=params,
            success_rate=success_rate,
            avg_duration=avg_duration,
            created_at=datetime.now().isoformat(),
        )
        self.best_practices[bp_id] = asdict(bp)
        self._save_json(self.best_practices_file, self.best_practices)
        logger.info(f"[学习系统] 新增最佳实践: {module} - {title}")
        return bp_id

    def get_best_practices(self, module: str = None) -> List[Dict]:
        """获取最佳实践列表"""
        result = []
        for bp in self.best_practices.values():
            if module and bp["module"] != module:
                continue
            result.append(bp)
        # 按成功率排序
        result.sort(key=lambda x: x.get("success_rate", 0), reverse=True)
        return result

    def get_pitfalls(self, module: str = None) -> List[Dict]:
        """获取踩坑记录列表"""
        result = []
        for p in self.pitfalls.values():
            if module and p["module"] != module:
                continue
            result.append(p)
        # 按命中次数排序
        result.sort(key=lambda x: x.get("hit_count", 0), reverse=True)
        return result

    def generate_report(self) -> Dict[str, Any]:
        """生成学习系统报告"""
        # 统计使用记录数
        usage_count = 0
        if os.path.exists(self.usage_log):
            with open(self.usage_log, "r", encoding="utf-8") as f:
                usage_count = sum(1 for _ in f)

        quality_count = 0
        if os.path.exists(self.quality_log):
            with open(self.quality_log, "r", encoding="utf-8") as f:
                quality_count = sum(1 for _ in f)

        module_stats = self.get_module_stats()

        return {
            "total_usage_records": usage_count,
            "total_quality_records": quality_count,
            "modules": module_stats,
            "best_practices_count": len(self.best_practices),
            "pitfalls_count": len(self.pitfalls),
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []
        module_stats = self.get_module_stats()

        for module, stats in module_stats.items():
            if stats["total"] >= 5:
                if stats["success_rate"] < 80:
                    recommendations.append(
                        f"⚠️ {module} 成功率仅 {stats['success_rate']}%，建议检查常见错误并优化"
                    )
                if stats["avg_duration"] > 120:
                    recommendations.append(
                        f"⏱️ {module} 平均耗时 {stats['avg_duration']}s，建议优化性能或增加缓存"
                    )

                # 检查最优参数
                for action, astats in stats.get("actions", {}).items():
                    best = self.get_best_params(module, action)
                    if best:
                        recommendations.append(
                            f"💡 {module}/{action} 推荐参数: {best}"
                        )

        if not recommendations:
            recommendations.append("✅ 系统运行良好，暂无优化建议")

        return recommendations


# 全局单例
_system = None


def get_self_learning_system() -> SelfLearningSystem:
    """获取自学习系统单例"""
    global _system
    if _system is None:
        _system = SelfLearningSystem()
    return _system


# 便捷函数
def log_usage(module: str, action: str, params: Dict, success: bool,
              duration: float, **kwargs):
    """便捷记录使用情况"""
    get_self_learning_system().log_usage(
        module, action, params, success, duration, **kwargs
    )


def log_quality(module: str, output_path: str, score: float, **kwargs):
    """便捷记录质量评估"""
    get_self_learning_system().log_quality(module, output_path, score, **kwargs)


def get_best_params(module: str, action: str) -> Dict:
    """便捷获取最优参数"""
    return get_self_learning_system().get_best_params(module, action)


def match_pitfall(error_message: str) -> Optional[Dict]:
    """便捷匹配踩坑记录"""
    return get_self_learning_system().match_pitfall(error_message)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    system = SelfLearningSystem()

    # 模拟一些使用记录
    logger.info("=== 自学习系统测试 ===")

    # 记录使用
    system.log_usage("tts", "synthesize", {"character": "豆包", "emotion": "happy"},
                     True, 5.2, output_path="test.mp3")
    system.log_usage("h3", "text_to_video", {"width": 768, "height": 1344, "frames": 81},
                     True, 132.5, output_path="h3_output.mp4")
    system.log_usage("h3", "text_to_video", {"width": 768, "height": 1344, "frames": 81},
                     False, 45.0, error="OOM")

    # 添加踩坑记录
    pid = system.add_pitfall(
        module="h3",
        symptom="生成视频时显存不足",
        root_cause="分辨率过高或帧数过多，超出显存限制",
        solution="降低分辨率至768x1344，帧数控制在81帧以内，使用分块VAE解码",
        error_pattern="OOM"
    )
    logger.info(f"添加踩坑记录: {pid}")

    # 匹配踩坑
    matched = system.match_pitfall("CUDA OOM error")
    if matched:
        logger.info(f"匹配到踩坑: {matched['symptom']}")
        logger.info(f"解决方案: {matched['solution']}")

    # 获取最优参数
    best = system.get_best_params("h3", "text_to_video")
    logger.info(f"最优参数: {best}")

    # 生成报告
    report = system.generate_report()
    logger.info(f"\n=== 学习系统报告 ===")
    logger.info(f"使用记录: {report['total_usage_records']}")
    logger.info(f"模块统计: {list(report['modules'].keys())}")
    logger.info(f"优化建议:")
    for rec in report['recommendations']:
        logger.info(f"  {rec}")
