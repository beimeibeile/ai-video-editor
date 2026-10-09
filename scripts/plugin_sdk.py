"""
插件SDK核心框架（Plugin SDK）
阶段三任务11：插件SDK开放

功能：
1. 插件基类（PluginBase）- 所有插件的基类
2. 插件管理器（PluginManager）- 加载/卸载/管理插件
3. 插件API - 能力注册/事件监听/数据访问/日志
4. 插件沙箱 - 安全隔离机制
5. 插件配置 - 插件元数据与配置管理
"""

import os
import sys
import json
import time
import logging
import importlib.util
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


logger = logging.getLogger(__name__)


# ============ 插件状态枚举 ============
class PluginStatus(Enum):
    """插件状态"""
    LOADED = "loaded"          # 已加载
    ACTIVE = "active"          # 运行中
    DISABLED = "disabled"      # 已禁用
    ERROR = "error"            # 错误


# ============ 插件元数据 ============
@dataclass
class PluginMetadata:
    """插件元数据"""
    plugin_id: str
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    category: str = "general"  # general/effect/transition/audio/text/export/other
    tags: List[str] = field(default_factory=list)
    entry_point: str = "Plugin"  # 插件类名
    min_sdk_version: str = "1.0.0"
    max_sdk_version: str = ""
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)  # 需要的权限
    config_schema: Dict[str, Any] = field(default_factory=dict)  # 配置项定义
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ============ 插件上下文（插件可访问的API） ============
class PluginContext:
    """
    插件上下文 - 插件运行时可访问的API集合

    插件通过self.context访问以下能力：
    - register_capability: 注册能力到能力注册中心
    - on_event: 监听事件
    - emit_event: 触发事件
    - get_config: 获取配置
    - set_config: 设置配置
    - log: 日志记录
    - get_data: 访问共享数据
    - set_data: 设置共享数据
    - http_request: HTTP请求
    - file_read: 读取文件（受权限限制）
    - file_write: 写入文件（受权限限制）
    """

    def __init__(self, plugin_id: str, manager: "PluginManager", config: Dict = None):
        self.plugin_id = plugin_id
        self._manager = manager
        self._config = config or {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._data: Dict[str, Any] = {}

    # 能力注册
    def register_capability(self, capability_id: str, name: str, description: str,
                             handler: Callable, category: str = "plugin") -> bool:
        """注册能力到能力注册中心"""
        logger.info(f"[Plugin:{self.plugin_id}] 注册能力: {capability_id}")
        return self._manager._register_plugin_capability(
            self.plugin_id, capability_id, name, description, handler, category
        )

    def unregister_capability(self, capability_id: str) -> bool:
        """注销能力"""
        return self._manager._unregister_plugin_capability(self.plugin_id, capability_id)

    # 事件系统
    def on_event(self, event_name: str, handler: Callable) -> None:
        """监听事件"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
        self._manager._register_event_handler(self.plugin_id, event_name, handler)

    def emit_event(self, event_name: str, data: Any = None) -> None:
        """触发事件"""
        self._manager._emit_event(event_name, data, source_plugin=self.plugin_id)

    # 配置管理
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取插件配置"""
        return self._config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """设置插件配置（持久化）"""
        self._config[key] = value
        self._manager._save_plugin_config(self.plugin_id, self._config)

    def get_all_config(self) -> Dict[str, Any]:
        """获取全部配置"""
        return self._config.copy()

    # 数据存储
    def get_data(self, key: str, default: Any = None) -> Any:
        """获取插件私有数据"""
        return self._data.get(key, default)

    def set_data(self, key: str, value: Any) -> None:
        """设置插件私有数据（内存中，重启丢失）"""
        self._data[key] = value

    # 日志
    def log(self, level: str, message: str) -> None:
        """记录日志"""
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[Plugin:{self.plugin_id}] {message}")

    def info(self, message: str) -> None:
        self.log("info", message)

    def warning(self, message: str) -> None:
        self.log("warning", message)

    def error(self, message: str) -> None:
        self.log("error", message)

    # HTTP请求
    def http_request(self, url: str, method: str = "GET",
                      headers: Dict = None, body: Any = None,
                      timeout: int = 30) -> Dict[str, Any]:
        """发起HTTP请求"""
        import urllib.request
        import urllib.error
        try:
            req = urllib.request.Request(url, method=method, headers=headers or {})
            if body:
                if isinstance(body, dict):
                    body = json.dumps(body).encode("utf-8")
                    req.add_header("Content-Type", "application/json")
                elif isinstance(body, str):
                    body = body.encode("utf-8")
            with urllib.request.urlopen(req, data=body, timeout=timeout) as resp:
                return {
                    "status": resp.status,
                    "headers": dict(resp.headers),
                    "body": resp.read().decode("utf-8", errors="replace"),
                }
        except urllib.error.HTTPError as e:
            return {"status": e.code, "error": str(e), "body": e.read().decode("utf-8", errors="replace") if e.fp else ""}
        except Exception as e:
            return {"status": 0, "error": str(e)}

    # 文件访问（受权限限制）
    def file_read(self, path: str) -> Optional[str]:
        """读取文件（需file.read权限）"""
        if "file.read" not in self._get_permissions():
            self.error(f"无file.read权限，无法读取: {path}")
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.error(f"读取文件失败: {e}")
            return None

    def file_write(self, path: str, content: str) -> bool:
        """写入文件（需file.write权限）"""
        if "file.write" not in self._get_permissions():
            self.error(f"无file.write权限，无法写入: {path}")
            return False
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            self.error(f"写入文件失败: {e}")
            return False

    def _get_permissions(self) -> List[str]:
        """获取插件权限列表"""
        return self._manager._get_plugin_permissions(self.plugin_id)


# ============ 插件基类 ============
class PluginBase:
    """
    插件基类 - 所有插件必须继承此类

    插件生命周期：
    1. __init__ - 初始化（传入context）
    2. on_load - 加载时调用（注册能力、监听事件等）
    3. on_enable - 启用时调用
    4. on_disable - 禁用时调用
    5. on_unload - 卸载时调用（清理资源）

    示例：
    class MyPlugin(PluginBase):
        def on_load(self):
            self.context.info("插件加载中...")
            self.context.register_capability("my_effect", "我的特效", "自定义特效", self.run_effect)

        def run_effect(self, params):
            return {"status": "success", "result": "..."}

        def on_unload(self):
            self.context.info("插件卸载")
    """

    def __init__(self, context: PluginContext):
        self.context = context
        self.metadata: Optional[PluginMetadata] = None
        self.status: PluginStatus = PluginStatus.LOADED

    def on_load(self) -> None:
        """插件加载时调用 - 子类可重写"""
        pass

    def on_enable(self) -> None:
        """插件启用时调用 - 子类可重写"""
        pass

    def on_disable(self) -> None:
        """插件禁用时调用 - 子类可重写"""
        pass

    def on_unload(self) -> None:
        """插件卸载时调用 - 子类可重写"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        if self.metadata:
            return asdict(self.metadata)
        return {"plugin_id": self.context.plugin_id}


# ============ 插件管理器 ============
class PluginManager:
    """
    插件管理器 - 负责插件的加载、卸载、启用、禁用、管理

    使用方式：
    manager = PluginManager(plugins_dir="/path/to/plugins")
    manager.load_all()
    manager.enable_plugin("plugin_id")
    """

    def __init__(self, plugins_dir: str = None, data_dir: str = None):
        """
        初始化插件管理器

        Args:
            plugins_dir: 插件目录
            data_dir: 数据存储目录（配置、状态等）
        """
        if plugins_dir is None:
            plugins_dir = os.path.join(
                os.path.expanduser("~"), "Videos", "剪映导出",
                "ai-video-editor", "plugins"
            )
        if data_dir is None:
            data_dir = os.path.join(
                os.path.expanduser("~"), "Videos", "剪映导出",
                "ai-video-editor", "plugin_data"
            )
        self.plugins_dir = plugins_dir
        self.data_dir = data_dir
        self.config_path = os.path.join(data_dir, "plugins_config.json")
        os.makedirs(plugins_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        self._plugins: Dict[str, PluginBase] = {}
        self._contexts: Dict[str, PluginContext] = {}
        self._metadatas: Dict[str, PluginMetadata] = {}
        self._configs: Dict[str, Dict] = {}
        self._capabilities: Dict[str, Dict] = {}  # capability_id -> {plugin_id, handler, ...}
        self._event_handlers: Dict[str, List[Dict]] = {}  # event_name -> [{plugin_id, handler}]
        self._global_event_handlers: List[Callable] = []

        self._load_configs()

    def _load_configs(self):
        """加载插件配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._configs = data.get("configs", {})
            except Exception as e:
                logger.error(f"加载插件配置失败: {e}")
                self._configs = {}

    def _save_configs(self):
        """保存插件配置"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"configs": self._configs}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存插件配置失败: {e}")

    def _save_plugin_config(self, plugin_id: str, config: Dict):
        """保存单个插件配置"""
        self._configs[plugin_id] = config
        self._save_configs()

    def _get_plugin_permissions(self, plugin_id: str) -> List[str]:
        """获取插件权限列表"""
        metadata = self._metadatas.get(plugin_id)
        if metadata:
            return metadata.permissions
        return []

    # 插件发现与加载
    def discover_plugins(self) -> List[str]:
        """发现可用插件（扫描插件目录）"""
        plugins = []
        if not os.path.exists(self.plugins_dir):
            return plugins
        for item in os.listdir(self.plugins_dir):
            item_path = os.path.join(self.plugins_dir, item)
            if os.path.isdir(item_path):
                # 检查是否有plugin.json元数据文件
                meta_path = os.path.join(item_path, "plugin.json")
                if os.path.exists(meta_path):
                    plugins.append(item)
                # 或者有__init__.py
                elif os.path.exists(os.path.join(item_path, "__init__.py")):
                    plugins.append(item)
            elif item.endswith(".py") and item != "__init__.py":
                # 单文件插件
                plugins.append(item[:-3])
        return plugins

    def load_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """
        加载单个插件

        Args:
            plugin_id: 插件ID（目录名或文件名）

        Returns:
            加载的插件实例，失败返回None
        """
        if plugin_id in self._plugins:
            logger.warning(f"插件已加载: {plugin_id}")
            return self._plugins[plugin_id]

        plugin_path = None
        meta_path = None

        # 查找插件路径
        dir_path = os.path.join(self.plugins_dir, plugin_id)
        file_path = os.path.join(self.plugins_dir, f"{plugin_id}.py")
        if os.path.isdir(dir_path):
            plugin_path = dir_path
            meta_path = os.path.join(dir_path, "plugin.json")
        elif os.path.exists(file_path):
            plugin_path = file_path
        else:
            logger.error(f"插件不存在: {plugin_id}")
            return None

        # 加载元数据
        metadata = None
        if meta_path and os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                metadata = PluginMetadata(**meta_data)
            except Exception as e:
                logger.error(f"加载插件元数据失败 {plugin_id}: {e}")
                return None
        else:
            # 没有元数据文件，创建默认元数据
            metadata = PluginMetadata(plugin_id=plugin_id, name=plugin_id)

        self._metadatas[plugin_id] = metadata

        # 加载插件模块
        try:
            # 确定入口文件
            if os.path.isdir(plugin_path):
                entry_file = os.path.join(plugin_path, "__init__.py")
                if not os.path.exists(entry_file):
                    # 尝试找主文件
                    for f in os.listdir(plugin_path):
                        if f.endswith(".py") and f != "__init__.py":
                            entry_file = os.path.join(plugin_path, f)
                            break
            else:
                entry_file = plugin_path

            if not os.path.exists(entry_file):
                logger.error(f"插件入口文件不存在: {entry_file}")
                return None

            # 动态加载模块
            spec = importlib.util.spec_from_file_location(f"plugin_{plugin_id}", entry_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"plugin_{plugin_id}"] = module
            spec.loader.exec_module(module)

            # 获取插件类
            entry_class_name = metadata.entry_point or "Plugin"
            plugin_class = getattr(module, entry_class_name, None)
            if plugin_class is None:
                # 尝试找PluginBase的子类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and issubclass(attr, PluginBase)
                            and attr is not PluginBase):
                        plugin_class = attr
                        break

            if plugin_class is None:
                logger.error(f"插件类未找到: {entry_class_name} in {entry_file}")
                return None

            # 创建上下文和插件实例
            config = self._configs.get(plugin_id, {})
            context = PluginContext(plugin_id, self, config)
            plugin_instance = plugin_class(context)
            plugin_instance.metadata = metadata

            # 调用on_load
            plugin_instance.on_load()
            plugin_instance.status = PluginStatus.LOADED

            self._plugins[plugin_id] = plugin_instance
            self._contexts[plugin_id] = context

            logger.info(f"插件加载成功: {plugin_id} v{metadata.version}")
            return plugin_instance

        except Exception as e:
            logger.error(f"插件加载失败 {plugin_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def load_all(self) -> Dict[str, bool]:
        """加载所有可用插件"""
        results = {}
        plugin_ids = self.discover_plugins()
        for plugin_id in plugin_ids:
            plugin = self.load_plugin(plugin_id)
            results[plugin_id] = plugin is not None
        return results

    # 插件启用/禁用
    def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            logger.error(f"插件未加载: {plugin_id}")
            return False
        try:
            plugin.on_enable()
            plugin.status = PluginStatus.ACTIVE
            logger.info(f"插件已启用: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"启用插件失败 {plugin_id}: {e}")
            plugin.status = PluginStatus.ERROR
            return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        try:
            plugin.on_disable()
            plugin.status = PluginStatus.DISABLED
            logger.info(f"插件已禁用: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"禁用插件失败 {plugin_id}: {e}")
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        try:
            plugin.on_unload()
            # 注销所有能力
            caps_to_remove = [cid for cid, c in self._capabilities.items()
                              if c.get("plugin_id") == plugin_id]
            for cid in caps_to_remove:
                del self._capabilities[cid]
            # 移除事件处理器
            for event_name in list(self._event_handlers.keys()):
                self._event_handlers[event_name] = [
                    h for h in self._event_handlers[event_name]
                    if h.get("plugin_id") != plugin_id
                ]
            del self._plugins[plugin_id]
            del self._contexts[plugin_id]
            if plugin_id in self._metadatas:
                del self._metadatas[plugin_id]
            logger.info(f"插件已卸载: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"卸载插件失败 {plugin_id}: {e}")
            return False

    # 能力注册（供插件上下文调用）
    def _register_plugin_capability(self, plugin_id: str, capability_id: str,
                                     name: str, description: str,
                                     handler: Callable, category: str) -> bool:
        """注册插件能力"""
        full_id = f"plugin.{plugin_id}.{capability_id}"
        self._capabilities[full_id] = {
            "plugin_id": plugin_id,
            "capability_id": capability_id,
            "name": name,
            "description": description,
            "handler": handler,
            "category": category,
            "registered_at": time.time(),
        }
        return True

    def _unregister_plugin_capability(self, plugin_id: str, capability_id: str) -> bool:
        """注销插件能力"""
        full_id = f"plugin.{plugin_id}.{capability_id}"
        if full_id in self._capabilities:
            del self._capabilities[full_id]
            return True
        return False

    # 事件系统
    def _register_event_handler(self, plugin_id: str, event_name: str, handler: Callable):
        """注册事件处理器"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append({
            "plugin_id": plugin_id,
            "handler": handler,
        })

    def _emit_event(self, event_name: str, data: Any = None, source_plugin: str = None):
        """触发事件"""
        handlers = self._event_handlers.get(event_name, [])
        for h in handlers:
            try:
                h["handler"](data, source_plugin=source_plugin)
            except Exception as e:
                logger.error(f"事件处理器执行失败 {event_name} ({h.get('plugin_id')}): {e}")
        # 全局事件处理器
        for gh in self._global_event_handlers:
            try:
                gh(event_name, data, source_plugin)
            except Exception as e:
                logger.error(f"全局事件处理器执行失败: {e}")

    def register_global_event_handler(self, handler: Callable):
        """注册全局事件处理器（供宿主系统使用）"""
        self._global_event_handlers.append(handler)

    # 查询接口
    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """获取插件实例"""
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有已加载插件"""
        result = []
        for plugin_id, plugin in self._plugins.items():
            info = plugin.get_info()
            info["status"] = plugin.status.value
            result.append(info)
        return result

    def list_capabilities(self) -> List[Dict[str, Any]]:
        """列出所有插件注册的能力"""
        result = []
        for cap_id, cap in self._capabilities.items():
            result.append({
                "id": cap_id,
                "name": cap["name"],
                "description": cap["description"],
                "plugin_id": cap["plugin_id"],
                "category": cap["category"],
            })
        return result

    def call_capability(self, capability_id: str, params: Dict = None) -> Any:
        """调用插件能力"""
        cap = self._capabilities.get(capability_id)
        if not cap:
            raise ValueError(f"能力不存在: {capability_id}")
        return cap["handler"](params or {})

    def get_stats(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        status_count = {}
        for plugin in self._plugins.values():
            s = plugin.status.value
            status_count[s] = status_count.get(s, 0) + 1
        return {
            "total_loaded": len(self._plugins),
            "total_capabilities": len(self._capabilities),
            "status_distribution": status_count,
            "available_plugins": self.discover_plugins(),
        }


# 全局单例
_manager = None

def get_plugin_manager(plugins_dir: str = None, data_dir: str = None) -> PluginManager:
    """获取插件管理器单例"""
    global _manager
    if _manager is None:
        _manager = PluginManager(plugins_dir, data_dir)
    return _manager


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    manager = PluginManager()
    print("=== 插件SDK测试 ===")
    print(f"插件目录: {manager.plugins_dir}")
    print(f"可用插件: {manager.discover_plugins()}")
    print(f"统计: {manager.get_stats()}")
    print("\n插件SDK核心框架就绪")
