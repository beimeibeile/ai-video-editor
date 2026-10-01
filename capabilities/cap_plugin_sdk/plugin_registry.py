"""
插件注册中心
管理所有已注册的插件和扩展点
"""

import os
import json
import importlib
import importlib.util
from typing import Dict, List, Any, Optional, Callable, Type
from .plugin_base import PluginBase, PluginState, PluginMetadata


class ExtensionRegistry:
    """扩展点注册中心（全局）"""

    def __init__(self):
        self._extensions = {}  # name -> {handler, plugin, description}
        self._plugins = {}  # plugin_name -> PluginBase

    def register_extension(self, name: str, handler: Callable,
                            plugin_name: str, description: str = "") -> bool:
        """注册扩展点"""
        if name in self._extensions:
            return False
        self._extensions[name] = {
            "handler": handler,
            "plugin": plugin_name,
            "description": description,
        }
        return True

    def unregister_extension(self, name: str) -> bool:
        """注销扩展点"""
        if name not in self._extensions:
            return False
        del self._extensions[name]
        return True

    def get_extension(self, name: str) -> Optional[Dict[str, Any]]:
        """获取扩展点"""
        return self._extensions.get(name)

    def call_extension(self, name: str, *args, **kwargs) -> Any:
        """调用扩展点"""
        ext = self._extensions.get(name)
        if not ext or not ext.get("handler"):
            return None
        return ext["handler"](*args, **kwargs)

    def list_extensions(self, plugin_name: str = None) -> List[Dict[str, Any]]:
        """列出所有扩展点"""
        result = []
        for name, ext in self._extensions.items():
            if plugin_name and ext["plugin"] != plugin_name:
                continue
            result.append({
                "name": name,
                "plugin": ext["plugin"],
                "description": ext["description"],
            })
        return result


class PluginRegistry:
    """插件注册中心"""

    def __init__(self):
        self._plugins = {}  # name -> PluginBase
        self._extension_registry = ExtensionRegistry()
        self._plugin_dirs = []  # 插件搜索目录

    @property
    def extension_registry(self) -> ExtensionRegistry:
        return self._extension_registry

    def register_plugin(self, plugin: PluginBase) -> bool:
        """
        注册插件实例

        Args:
            plugin: 插件实例

        Returns:
            是否注册成功
        """
        name = plugin.name
        if name in self._plugins:
            return False
        self._plugins[name] = plugin
        return True

    def unregister_plugin(self, name: str) -> bool:
        """注销插件"""
        if name not in self._plugins:
            return False
        plugin = self._plugins[name]
        # 停止并卸载
        try:
            if plugin.get_state() == PluginState.RUNNING:
                plugin.on_stop()
            plugin.on_unload()
        except Exception:
            pass
        # 注销所有扩展点
        for ext_name in list(self._extension_registry._extensions.keys()):
            ext = self._extension_registry._extensions[ext_name]
            if ext["plugin"] == name:
                del self._extension_registry._extensions[ext_name]
        del self._plugins[name]
        return True

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """获取插件"""
        return self._plugins.get(name)

    def list_plugins(self, state: PluginState = None,
                      category: str = None) -> List[Dict[str, Any]]:
        """列出所有插件"""
        result = []
        for name, plugin in self._plugins.items():
            if state and plugin.get_state() != state:
                continue
            if category and plugin.metadata.category != category:
                continue
            result.append(plugin.to_dict())
        return result

    def start_plugin(self, name: str) -> bool:
        """启动插件"""
        plugin = self._plugins.get(name)
        if not plugin:
            return False
        try:
            if plugin.get_state() == PluginState.UNLOADED:
                if not plugin.on_load():
                    plugin.set_state(PluginState.ERROR)
                    return False
                plugin.set_state(PluginState.LOADED)
            if plugin.get_state() in (PluginState.LOADED, PluginState.STOPPED):
                if not plugin.on_start():
                    plugin.set_state(PluginState.ERROR)
                    return False
                plugin.set_state(PluginState.RUNNING)
            return True
        except Exception as e:
            plugin.set_state(PluginState.ERROR)
            plugin.error(f"启动失败: {e}")
            return False

    def stop_plugin(self, name: str) -> bool:
        """停止插件"""
        plugin = self._plugins.get(name)
        if not plugin:
            return False
        try:
            if plugin.get_state() == PluginState.RUNNING:
                plugin.on_stop()
                plugin.set_state(PluginState.STOPPED)
            return True
        except Exception as e:
            plugin.error(f"停止失败: {e}")
            return False

    def start_all(self) -> Dict[str, bool]:
        """启动所有已注册插件"""
        results = {}
        for name in self._plugins:
            results[name] = self.start_plugin(name)
        return results

    def stop_all(self) -> Dict[str, bool]:
        """停止所有运行中的插件"""
        results = {}
        for name, plugin in self._plugins.items():
            if plugin.get_state() == PluginState.RUNNING:
                results[name] = self.stop_plugin(name)
        return results

    def add_plugin_dir(self, directory: str) -> None:
        """添加插件搜索目录"""
        if os.path.isdir(directory) and directory not in self._plugin_dirs:
            self._plugin_dirs.append(directory)

    def discover_plugins(self) -> List[str]:
        """
        发现插件目录中的所有插件
        返回发现的插件名称列表
        """
        discovered = []
        for plugin_dir in self._plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                if os.path.isdir(item_path):
                    # 检查是否有 plugin.json 或 __init__.py
                    if (os.path.exists(os.path.join(item_path, "plugin.json")) or
                            os.path.exists(os.path.join(item_path, "__init__.py"))):
                        discovered.append(item)
                elif item.endswith(".py") and item != "__init__.py":
                    # 单文件插件
                    plugin_name = item[:-3]
                    if plugin_name not in discovered:
                        discovered.append(plugin_name)
        return discovered

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        states = {}
        categories = {}
        for plugin in self._plugins.values():
            state = plugin.get_state().value
            states[state] = states.get(state, 0) + 1
            cat = plugin.metadata.category
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_plugins": len(self._plugins),
            "states": states,
            "categories": categories,
            "total_extensions": len(self._extension_registry._extensions),
            "plugin_dirs": len(self._plugin_dirs),
        }
