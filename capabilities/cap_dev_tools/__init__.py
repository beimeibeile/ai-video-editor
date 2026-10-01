"""
开发者工具链模块
CLI工具 + 调试器 + 性能分析器
"""
from .cli import CLI, main as cli_main
from .debugger import Debugger, CallRecord, PerformanceStats

__all__ = [
    "CLI",
    "cli_main",
    "Debugger",
    "CallRecord",
    "PerformanceStats",
]
__version__ = "1.0.0"
