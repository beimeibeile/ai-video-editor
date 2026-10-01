"""
插件基类
所有第三方插件必须继承此类，实现生命周期方法
"""

import os
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


class PluginState(Enum):
    """插件状态"""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    author: str = ""
    description: str = ""
    category: str = "general"  # effect/transition/filter/export/general
    tags: List[str] = field(default_factory=list)
    min_version: str = "1.0.0"
    max_version: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""
    config_schema: Dict[str, Any] = field(default_factory=dict)


class PluginBase:
    """
    插件基类

    生命周期：
    1. __init__ - 实例化
    2. on_load - 加载（读取配置、初始化资源）
    3. on_start - 启动（注册能力、订阅事件）
    4. on_stop - 停止（取消注册、释放资源）
    5. on_unload - 卸载（清理）
    """

    def __init__(self, context=None, config: Dict[str, Any] = None):
        """
        初始化插件

        Args:
            context: 插件上下文（提供系统能力访问）
            config: 插件配置
        """
        self.context = context
        self.config = config or {}
        self.state = PluginState.UNLOADED
        self._metadata = self._load_metadata()
        self._extension_points = {}  # name -> ExtensionPoint
        self._event_handlers = {}  # event_name -> [handlers]

    def _load_metadata(self) -> PluginMetadata:
        """加载插件元数据（子类可覆盖）"""
        return PluginMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            description="",
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    @property
    def name(self) -> str:
        return self._metadata.name

    @property
    def version(self) -> str:
        return self._metadata.version

    # ==================== 生命周期方法（子类覆盖） ====================

    def on_load(self) -> bool:
        """
        加载插件（读取配置、初始化资源）
        返回True表示成功，False表示失败
        """
        return True

    def on_start(self) -> bool:
        """
        启动插件（注册能力、订阅事件）
        返回True表示成功，False表示失败
        """
        return True

    def on_stop(self) -> bool:
        """
        停止插件（取消注册、释放资源）
        返回True表示成功，False表示失败
        """
        return True

    def on_unload(self) -> bool:
        """
        卸载插件（最终清理）
        返回True表示成功，False表示失败
        """
        return True

    # ==================== 扩展点管理 ====================

    def register_extension_point(self, name: str, description: str = "",
                                  handler: Callable = None) -> bool:
        """
        注册扩展点（插件向系统提供的能力）

        Args:
            name: 扩展点名称（全局唯一，建议 plugin_name.point_name）
            description: 描述
            handler: 处理函数

        Returns:
            是否注册成功
        """
        if name in self._extension_points:
            return False
        self._extension_points[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "plugin": self.name,
        }
        # 同时注册到全局注册中心
        if self.context and hasattr(self.context, 'registry') and self.context.registry:
            self.context.registry.extension_registry.register_extension(name, handler, self.name, description)
        return True

    def unregister_extension_point(self, name: str) -> bool:
        """注销扩展点"""
        if name not in self._extension_points:
            return False
        del self._extension_points[name]
        if self.context and hasattr(self.context, 'registry') and self.context.registry:
            self.context.registry.extension_registry.unregister_extension(name)
        return True

    def get_extension_points(self) -> Dict[str, Any]:
        """获取所有扩展点"""
        return dict(self._extension_points)

    # ==================== 事件订阅 ====================

    def subscribe_event(self, event_name: str, handler: Callable) -> bool:
        """
        订阅系统事件

        Args:
            event_name: 事件名称
            handler: 处理函数

        Returns:
            是否订阅成功
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
        if self.context and hasattr(self.context, 'event_bus') and self.context.event_bus:
            self.context.event_bus.subscribe(event_name, handler)
        return True

    def unsubscribe_event(self, event_name: str, handler: Callable = None) -> bool:
        """取消订阅事件"""
        if event_name not in self._event_handlers:
            return False
        if handler:
            self._event_handlers[event_name] = [
                h for h in self._event_handlers[event_name] if h != handler
            ]
        else:
            del self._event_handlers[event_name]
        return True

    # ==================== 配置管理 ====================

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """设置配置项"""
        self.config[key] = value

    def save_config(self) -> bool:
        """保存配置到文件"""
        if not self.context:
            return False
        config_dir = getattr(self.context, 'config_dir', None)
        if not config_dir:
            return False
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, f"{self.name}.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    # ==================== 日志 ====================

    def log(self, level: str, message: str) -> None:
        """记录日志"""
        if self.context and self.context.logger and hasattr(self.context.logger, 'log'):
            self.context.logger.log(level, f"[{self.name}] {message}")
        else:
            print(f"[{level.upper()}] [{self.name}] {message}")

    def info(self, message: str) -> None:
        self.log("info", message)

    def warning(self, message: str) -> None:
        self.log("warning", message)

    def error(self, message: str) -> None:
        self.log("error", message)

    # ==================== 状态管理 ====================

    def get_state(self) -> PluginState:
        return self.state

    def set_state(self, state: PluginState) -> None:
        self.state = state

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "state": self.state.value,
            "metadata": asdict(self._metadata),
            "extension_points": list(self._extension_points.keys()),
            "config": self.config,
        }
