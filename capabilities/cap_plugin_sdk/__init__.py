"""
插件SDK模块
第三方插件开发框架与API

核心组件：
- PluginBase: 插件基类（生命周期、扩展点、事件订阅）
- PluginRegistry: 插件注册中心（管理插件和扩展点）
- PluginLoader: 插件加载器（从目录动态加载）
- PluginContext: 插件上下文（系统能力访问接口）
- PluginMetadata: 插件元数据
- PluginState: 插件状态枚举

使用示例：
    from cap_plugin_sdk import PluginBase, PluginLoader, PluginRegistry

    class MyPlugin(PluginBase):
        def on_start(self):
            self.register_extension_point("my_plugin.effect", "自定义特效", self.do_effect)
            return True

        def do_effect(self, *args, **kwargs):
            pass

    # 加载并启动
    loader = PluginLoader()
    loader.load_plugins_from_dir("./plugins", auto_start=True)
"""
from .plugin_base import PluginBase, PluginState, PluginMetadata
from .plugin_registry import PluginRegistry, ExtensionRegistry
from .plugin_loader import PluginLoader, PluginContext

__all__ = [
    "PluginBase",
    "PluginState",
    "PluginMetadata",
    "PluginRegistry",
    "ExtensionRegistry",
    "PluginLoader",
    "PluginContext",
]
__version__ = "1.0.0"
