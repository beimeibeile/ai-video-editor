"""
统一日志模块
所有模块应使用此模块进行日志输出
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


_LOGGER_INITIALIZED = False
_DEFAULT_LOGGER_NAME = "ave"


def setup_logger(
    name: str = _DEFAULT_LOGGER_NAME,
    level: str = None,
    log_file: str = None,
    console: bool = True,
) -> logging.Logger:
    """
    配置并返回logger实例

    Args:
        name: logger名称
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径（可选）
        console: 是否输出到控制台

    Returns:
        配置好的logger实例
    """
    global _LOGGER_INITIALIZED

    logger = logging.getLogger(name)

    # 环境变量覆盖
    if level is None:
        level = os.environ.get("AVE_LOG_LEVEL", "INFO")
    if log_file is None:
        log_file = os.environ.get("AVE_LOG_FILE")

    # 设置级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 格式化
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件输出
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _LOGGER_INITIALIZED = True
    return logger


def get_logger(name: str = _DEFAULT_LOGGER_NAME) -> logging.Logger:
    """获取logger实例（如未初始化则自动初始化）"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


# 便捷函数
def debug(msg: str, *args, **kwargs):
    get_logger().debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    get_logger().info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    get_logger().warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    get_logger().error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    get_logger().critical(msg, *args, **kwargs)


if __name__ == "__main__":
    # 测试
    logger = setup_logger(level="DEBUG")
    logger.debug("调试信息")
    logger.info("普通信息")
    logger.warning("警告信息")
    logger.error("错误信息")
    logger.info("日志模块测试完成")