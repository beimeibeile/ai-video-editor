"""
批量视频生产系统
从CSV/JSON读取批量任务，逐个生成视频，跟踪进度和状态
"""
from .batch_processor import BatchProcessor, BatchTask

__all__ = ["BatchProcessor", "BatchTask"]
__version__ = "1.0.0"
