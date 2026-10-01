"""
第三方工具集成模块
统一适配器层，与OBS/PR/AE/Blender/ComfyUI等工具集成
"""

import os
import json
import subprocess
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


class ToolState(Enum):
    """工具状态"""
    UNKNOWN = "unknown"
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    version: str = ""
    path: str = ""
    state: ToolState = ToolState.UNKNOWN
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


class ToolAdapterBase:
    """
    工具适配器基类
    所有第三方工具适配器必须继承此类
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._info = ToolInfo(name=self.__class__.__name__)
        self._state = ToolState.UNKNOWN

    @property
    def info(self) -> ToolInfo:
        return self._info

    @property
    def name(self) -> str:
        return self._info.name

    @property
    def state(self) -> ToolState:
        return self._state

    # ==================== 生命周期 ====================

    def detect(self) -> ToolState:
        """
        检测工具是否安装
        子类必须实现
        """
        raise NotImplementedError

    def start(self) -> bool:
        """启动工具"""
        return True

    def stop(self) -> bool:
        """停止工具"""
        return True

    def is_running(self) -> bool:
        """检查工具是否运行中"""
        return self._state == ToolState.RUNNING

    # ==================== 能力调用 ====================

    def get_capabilities(self) -> List[str]:
        """获取工具能力列表"""
        return list(self._info.capabilities)

    def has_capability(self, capability: str) -> bool:
        """检查是否有指定能力"""
        return capability in self._info.capabilities

    def call(self, action: str, **kwargs) -> Any:
        """
        调用工具能力
        子类必须实现
        """
        raise NotImplementedError(f"工具 {self.name} 不支持动作 {action}")

    # ==================== 配置管理 ====================

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        self.config[key] = value

    # ==================== 工具方法 ====================

    def _run_command(self, command: List[str], timeout: int = 30,
                      cwd: str = None) -> Dict[str, Any]:
        """运行外部命令"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "timeout", "returncode": -1}
        except Exception as e:
            return {"success": False, "error": str(e), "returncode": -1}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self._state.value,
            "info": asdict(self._info),
            "config": self.config,
        }


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools = {}  # name -> ToolAdapterBase

    def register(self, tool: ToolAdapterBase) -> bool:
        """注册工具"""
        name = tool.name
        if name in self._tools:
            return False
        self._tools[name] = tool
        return True

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name not in self._tools:
            return False
        del self._tools[name]
        return True

    def get(self, name: str) -> Optional[ToolAdapterBase]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self, state: ToolState = None) -> List[Dict[str, Any]]:
        """列出所有工具"""
        result = []
        for name, tool in self._tools.items():
            if state and tool.state != state:
                continue
            result.append(tool.to_dict())
        return result

    def detect_all(self) -> Dict[str, ToolState]:
        """检测所有工具"""
        results = {}
        for name, tool in self._tools.items():
            results[name] = tool.detect()
        return results

    def call(self, tool_name: str, action: str, **kwargs) -> Any:
        """调用工具能力"""
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"工具 {tool_name} 未注册")
        return tool.call(action, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        states = {}
        total_capabilities = 0
        for tool in self._tools.values():
            state = tool.state.value
            states[state] = states.get(state, 0) + 1
            total_capabilities += len(tool.get_capabilities())
        return {
            "total_tools": len(self._tools),
            "states": states,
            "total_capabilities": total_capabilities,
        }
