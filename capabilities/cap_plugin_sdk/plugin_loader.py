"""
插件加载器
从目录动态加载插件
"""

import os
import sys
import json
import importlib
import importlib.util
from typing import Dict, List, Any, Optional, Type
from .plugin_base import PluginBase, PluginState, PluginMetadata
from .plugin_registry import PluginRegistry


class PluginContext:
    """
    插件上下文
    提供插件访问系统能力的接口
    """

    def __init__(self, registry: PluginRegistry = None, config_dir: str = None,
                 logger=None, event_bus=None):
        self.registry = registry
        self.config_dir = config_dir or os.path.join(os.path.expanduser("~"), ".ai_video_editor", "plugins")
        self.logger = logger
        self.event_bus = event_bus
        self._shared_data = {}  # 插件间共享数据

    def get_shared_data(self, key: str, default: Any = None) -> Any:
        """获取共享数据"""
        return self._shared_data.get(key, default)

    def set_shared_data(self, key: str, value: Any) -> None:
        """设置共享数据"""
        self._shared_data[key] = value

    def call_extension(self, name: str, *args, **kwargs) -> Any:
        """调用扩展点"""
        if self.registry:
            return self.registry.extension_registry.call_extension(name, *args, **kwargs)
        return None

    def list_extensions(self) -> List[Dict[str, Any]]:
        """列出所有扩展点"""
        if self.registry:
            return self.registry.extension_registry.list_extensions()
        return []

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """获取其他插件实例"""
        if self.registry:
            return self.registry.get_plugin(name)
        return None

    def log(self, level: str, message: str) -> None:
        """记录日志"""
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level.upper()}] {message}")


class PluginLoader:
    """插件加载器"""

    def __init__(self, registry: PluginRegistry = None, context: PluginContext = None):
        self.registry = registry or PluginRegistry()
        self.context = context or PluginContext(registry=self.registry)
        self._loaded_modules = {}  # module_name -> module

    def load_plugin_from_file(self, file_path: str,
                               plugin_class: str = None) -> Optional[PluginBase]:
        """
        从Python文件加载插件

        Args:
            file_path: 插件文件路径
            plugin_class: 插件类名（默认查找第一个PluginBase子类）

        Returns:
            插件实例或None
        """
        if not os.path.exists(file_path):
            return None

        module_name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self._loaded_modules[module_name] = module

            # 查找插件类
            plugin_cls = None
            if plugin_class and hasattr(module, plugin_class):
                plugin_cls = getattr(module, plugin_class)
            else:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                            issubclass(attr, PluginBase) and
                            attr is not PluginBase):
                        plugin_cls = attr
                        break

            if not plugin_cls:
                return None

            # 实例化插件
            plugin = plugin_cls(context=self.context)
            return plugin

        except Exception as e:
            print(f"加载插件失败 {file_path}: {e}")
            return None

    def load_plugin_from_dir(self, dir_path: str) -> Optional[PluginBase]:
        """
        从目录加载插件

        Args:
            dir_path: 插件目录路径

        Returns:
            插件实例或None
        """
        if not os.path.isdir(dir_path):
            return None

        # 检查plugin.json
        plugin_json_path = os.path.join(dir_path, "plugin.json")
        plugin_config = {}
        entry_point = None
        plugin_class = None

        if os.path.exists(plugin_json_path):
            try:
                with open(plugin_json_path, "r", encoding="utf-8") as f:
                    plugin_config = json.load(f)
                entry_point = plugin_config.get("entry_point", "plugin.py")
                plugin_class = plugin_config.get("plugin_class")
            except Exception:
                pass

        # 确定入口文件
        if entry_point:
            entry_file = os.path.join(dir_path, entry_point)
        elif os.path.exists(os.path.join(dir_path, "plugin.py")):
            entry_file = os.path.join(dir_path, "plugin.py")
        elif os.path.exists(os.path.join(dir_path, "__init__.py")):
            entry_file = os.path.join(dir_path, "__init__.py")
        else:
            # 查找第一个py文件
            for f in os.listdir(dir_path):
                if f.endswith(".py") and f != "__init__.py":
                    entry_file = os.path.join(dir_path, f)
                    break
            else:
                return None

        if not os.path.exists(entry_file):
            return None

        # 加载插件
        plugin = self.load_plugin_from_file(entry_file, plugin_class)
        if plugin:
            # 应用plugin.json中的配置
            if plugin_config:
                plugin.config.update(plugin_config.get("config", {}))
                # 更新元数据
                if "name" in plugin_config:
                    plugin._metadata.name = plugin_config["name"]
                if "version" in plugin_config:
                    plugin._metadata.version = plugin_config["version"]
                if "description" in plugin_config:
                    plugin._metadata.description = plugin_config["description"]
                if "author" in plugin_config:
                    plugin._metadata.author = plugin_config["author"]
                if "category" in plugin_config:
                    plugin._metadata.category = plugin_config["category"]
        return plugin

    def load_plugins_from_dir(self, plugins_dir: str,
                                auto_start: bool = False) -> Dict[str, bool]:
        """
        从目录批量加载插件

        Args:
            plugins_dir: 插件根目录
            auto_start: 是否自动启动

        Returns:
            加载结果 {plugin_name: success}
        """
        results = {}
        if not os.path.isdir(plugins_dir):
            return results

        self.registry.add_plugin_dir(plugins_dir)

        for item in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item)
            plugin = None

            if os.path.isdir(item_path):
                plugin = self.load_plugin_from_dir(item_path)
            elif item.endswith(".py") and item != "__init__.py":
                plugin = self.load_plugin_from_file(item_path)

            if plugin:
                name = plugin.name
                # 注册
                if self.registry.register_plugin(plugin):
                    results[name] = True
                    # 自动加载
                    try:
                        plugin.on_load()
                        plugin.set_state(PluginState.LOADED)
                    except Exception as e:
                        plugin.error(f"加载失败: {e}")
                        plugin.set_state(PluginState.ERROR)
                        results[name] = False
                    # 自动启动
                    if auto_start and results[name]:
                        results[name] = self.registry.start_plugin(name)
                else:
                    results[name] = False
            else:
                results[item] = False

        return results

    def unload_plugin(self, name: str) -> bool:
        """卸载插件"""
        return self.registry.unregister_plugin(name)

    def get_loaded_plugins(self) -> List[str]:
        """获取所有已加载的插件名"""
        return list(self.registry._plugins.keys())
