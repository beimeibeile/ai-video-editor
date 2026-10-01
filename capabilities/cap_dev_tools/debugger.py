"""
调试器与性能分析器
提供调用追踪、性能分析、日志管理等开发辅助功能
"""

import os
import sys
import time
import json
import functools
import traceback
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager


@dataclass
class CallRecord:
    """调用记录"""
    func_name: str
    start_time: float
    end_time: float = 0.0
    duration: float = 0.0
    success: bool = True
    error: str = ""
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    result_size: int = 0


@dataclass
class PerformanceStats:
    """性能统计"""
    func_name: str
    call_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    success_count: int = 0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "func_name": self.func_name,
            "call_count": self.call_count,
            "total_time": round(self.total_time, 4),
            "avg_time": round(self.avg_time, 4),
            "min_time": round(self.min_time, 4) if self.min_time != float("inf") else 0,
            "max_time": round(self.max_time, 4),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": round(self.success_count / self.call_count * 100, 1) if self.call_count else 0,
        }


class Debugger:
    """调试器"""

    def __init__(self, log_level: str = "INFO", log_file: str = None):
        self.log_level = log_level
        self.log_file = log_file
        self.call_records: List[CallRecord] = []
        self.performance_stats: Dict[str, PerformanceStats] = {}
        self._tracing = False
        self._profiling = False
        self._log_buffer: List[str] = []

    # ==================== 日志 ====================

    def log(self, level: str, message: str):
        """记录日志"""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if levels.index(level) < levels.index(self.log_level):
            return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self._log_buffer.append(log_entry)

        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
            except Exception:
                pass

    def debug(self, message: str):
        self.log("DEBUG", message)

    def info(self, message: str):
        self.log("INFO", message)

    def warning(self, message: str):
        self.log("WARNING", message)

    def error(self, message: str):
        self.log("ERROR", message)

    def get_logs(self, level: str = None) -> List[str]:
        """获取日志"""
        if not level:
            return list(self._log_buffer)
        return [log for log in self._log_buffer if f"[{level}]" in log]

    # ==================== 调用追踪 ====================

    @contextmanager
    def trace(self, func_name: str = "anonymous"):
        """
        调用追踪上下文管理器

        使用:
            with debugger.trace("my_function"):
                result = my_function()
        """
        start = time.time()
        record = CallRecord(func_name=func_name, start_time=start)
        try:
            yield
            record.success = True
        except Exception as e:
            record.success = False
            record.error = str(e)
            raise
        finally:
            record.end_time = time.time()
            record.duration = record.end_time - record.start_time
            self.call_records.append(record)
            self._update_stats(record)
            self.debug(f"调用 {func_name}: {record.duration*1000:.2f}ms "
                       f"{'✅' if record.success else '❌ ' + record.error}")

    def trace_decorator(self, func: Callable) -> Callable:
        """
        调用追踪装饰器

        使用:
            @debugger.trace_decorator
            def my_function():
                pass
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.trace(func.__name__):
                return func(*args, **kwargs)
        return wrapper

    # ==================== 性能分析 ====================

    def _update_stats(self, record: CallRecord):
        """更新性能统计"""
        if record.func_name not in self.performance_stats:
            self.performance_stats[record.func_name] = PerformanceStats(
                func_name=record.func_name
            )
        stats = self.performance_stats[record.func_name]
        stats.call_count += 1
        stats.total_time += record.duration
        stats.avg_time = stats.total_time / stats.call_count
        stats.min_time = min(stats.min_time, record.duration)
        stats.max_time = max(stats.max_time, record.duration)
        if record.success:
            stats.success_count += 1
        else:
            stats.error_count += 1

    @contextmanager
    def profile(self, label: str = "profile"):
        """
        性能分析上下文管理器

        使用:
            with debugger.profile("my_operation"):
                my_operation()
        """
        start = time.time()
        self.info(f"⏱️  开始性能分析: {label}")
        try:
            yield
        finally:
            duration = time.time() - start
            self.info(f"⏱️  性能分析完成: {label} - {duration*1000:.2f}ms")

    def get_performance_report(self, sort_by: str = "total_time",
                                limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取性能报告

        Args:
            sort_by: 排序方式（total_time/avg_time/call_count/max_time）
            limit: 返回数量

        Returns:
            性能统计列表
        """
        stats = list(self.performance_stats.values())
        if sort_by == "total_time":
            stats.sort(key=lambda x: x.total_time, reverse=True)
        elif sort_by == "avg_time":
            stats.sort(key=lambda x: x.avg_time, reverse=True)
        elif sort_by == "call_count":
            stats.sort(key=lambda x: x.call_count, reverse=True)
        elif sort_by == "max_time":
            stats.sort(key=lambda x: x.max_time, reverse=True)

        return [s.to_dict() for s in stats[:limit]]

    # ==================== 异常处理 ====================

    def handle_exception(self, e: Exception, context: str = ""):
        """处理异常"""
        self.error(f"异常在 {context}: {type(e).__name__}: {e}")
        self.error(f"堆栈:\n{traceback.format_exc()}")

    # ==================== 报告生成 ====================

    def generate_report(self, output_path: str = None) -> Dict[str, Any]:
        """生成调试报告"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "log_level": self.log_level,
            "total_calls": len(self.call_records),
            "total_errors": sum(1 for r in self.call_records if not r.success),
            "total_time": round(sum(r.duration for r in self.call_records), 4),
            "performance_top10": self.get_performance_report(limit=10),
            "recent_errors": [
                {"func": r.func_name, "error": r.error, "time": r.end_time}
                for r in self.call_records if not r.success
            ][-10:],
        }

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            self.info(f"调试报告已保存: {output_path}")

        return report

    def reset(self):
        """重置调试器状态"""
        self.call_records.clear()
        self.performance_stats.clear()
        self._log_buffer.clear()
