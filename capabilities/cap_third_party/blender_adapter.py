"""
Blender工具适配器
封装已有的Blender能力
"""

import os
from typing import Dict, Any, Optional
from .tool_base import ToolAdapterBase, ToolState, ToolInfo


class BlenderAdapter(ToolAdapterBase):
    """Blender工具适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._info = ToolInfo(
            name="blender",
            description="Blender 3D建模与渲染工具",
            capabilities=["render", "model", "animate", "particle", "text_3d", "transition"],
        )
        self._blender_path = self.config.get("blender_path", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
        self._runner = None

    def detect(self) -> ToolState:
        """检测Blender是否安装"""
        if os.path.exists(self._blender_path):
            self._state = ToolState.INSTALLED
            # 获取版本
            try:
                result = self._run_command([self._blender_path, "--version"], timeout=10)
                if result["success"] and result["stdout"]:
                    version_line = result["stdout"].split("\n")[0]
                    self._info.version = version_line.strip()
            except Exception:
                pass
        else:
            self._state = ToolState.NOT_INSTALLED
        return self._state

    def start(self) -> bool:
        """启动Blender（后台模式）"""
        if self._state != ToolState.INSTALLED:
            return False
        # Blender通常以-b（后台）模式运行脚本，不需要常驻进程
        self._state = ToolState.RUNNING
        return True

    def stop(self) -> bool:
        """停止Blender"""
        self._state = ToolState.INSTALLED
        return True

    def call(self, action: str, **kwargs) -> Any:
        """
        调用Blender能力

        支持的action:
        - render: 渲染场景
        - run_script: 运行Python脚本
        - create_particles: 创建粒子效果
        - create_text_intro: 创建3D文字入场
        - create_transition: 创建转场遮罩
        """
        if self._state not in (ToolState.INSTALLED, ToolState.RUNNING):
            raise RuntimeError(f"Blender未安装，当前状态: {self._state}")

        if action == "run_script":
            return self._run_script(kwargs.get("script_path"), kwargs.get("output_dir"))
        elif action == "render":
            return self._render(kwargs.get("blend_path"), kwargs.get("output_dir"),
                                kwargs.get("fps", 30))
        elif action == "create_particles":
            return self._create_particles(kwargs)
        elif action == "create_text_intro":
            return self._create_text_intro(kwargs)
        elif action == "create_transition":
            return self._create_transition(kwargs)
        else:
            raise ValueError(f"Blender不支持动作: {action}")

    def _run_script(self, script_path: str, output_dir: str = None) -> Dict[str, Any]:
        """运行Blender Python脚本"""
        if not script_path or not os.path.exists(script_path):
            return {"success": False, "error": "脚本不存在"}
        cmd = [self._blender_path, "-b", "-P", script_path]
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        result = self._run_command(cmd, timeout=120, cwd=output_dir)
        return result

    def _render(self, blend_path: str, output_dir: str, fps: int = 30) -> Dict[str, Any]:
        """渲染Blender工程"""
        if not blend_path or not os.path.exists(blend_path):
            return {"success": False, "error": "工程文件不存在"}
        os.makedirs(output_dir, exist_ok=True)
        cmd = [
            self._blender_path, "-b", blend_path,
            "-o", os.path.join(output_dir, "frame_"),
            "-F", "PNG", "-x", "1", "-a"
        ]
        result = self._run_command(cmd, timeout=300)
        return result

    def _create_particles(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """创建粒子效果（委托给blender_effects模块）"""
        try:
            from blender_effects import create_particle_background
            output_dir = kwargs.get("output_dir", "./output")
            preset = kwargs.get("preset", "stars")
            duration = kwargs.get("duration", 3.0)
            result = create_particle_background(output_dir, preset=preset, duration=duration)
            return {"success": result is not None, "output": result}
        except ImportError:
            return {"success": False, "error": "blender_effects模块不可用"}

    def _create_text_intro(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """创建3D文字入场"""
        try:
            from blender_effects import create_text_intro
            result = create_text_intro(
                text=kwargs.get("text", "Title"),
                output_dir=kwargs.get("output_dir", "./output"),
                subtitle=kwargs.get("subtitle", ""),
                duration=kwargs.get("duration", 3.0),
                style=kwargs.get("style", "zoom"),
            )
            return {"success": result is not None, "output": result}
        except ImportError:
            return {"success": False, "error": "blender_effects模块不可用"}

    def _create_transition(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """创建转场遮罩"""
        try:
            from blender_effects import create_transition
            result = create_transition(
                output_dir=kwargs.get("output_dir", "./output"),
                style=kwargs.get("style", "fade"),
                duration=kwargs.get("duration", 1.0),
            )
            return {"success": result is not None, "output": result}
        except ImportError:
            return {"success": False, "error": "blender_effects模块不可用"}
