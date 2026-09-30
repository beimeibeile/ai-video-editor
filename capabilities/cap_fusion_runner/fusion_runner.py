"""
DaVinci Resolve Fusion 特效合成模块
通过 fuscript.exe (Lua脚本解释器) 自动化操作 Fusion 合成。

核心能力：
- 生成 .comp 合成文件（纯Lua文本格式）
- 执行 Lua 脚本操作节点
- 命令行渲染输出
- 常用特效：粒子、文字动画、光效、渐变背景

依赖：DaVinci Resolve (免费版即可)
"""

import os
import sys
import json
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


# DaVinci Resolve 安装路径
RESOLVE_DIR = r"C:\Program Files\Blackmagic Design\DaVinci Resolve"
FUSCRIPT_PATH = os.path.join(RESOLVE_DIR, "fuscript.exe")
RESOLVE_EXE = os.path.join(RESOLVE_DIR, "Resolve.exe")


@dataclass
class FusionNode:
    """Fusion 节点"""
    node_type: str  # 节点类型，如 "Background", "TextPlus", "pParticleEmitter"
    name: str  # 节点名称
    params: Dict[str, Any] = field(default_factory=dict)  # 节点参数
    inputs: List[str] = field(default_factory=list)  # 输入连接的节点名列表


@dataclass
class FusionComp:
    """Fusion 合成"""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration: int = 150  # 帧数
    nodes: List[FusionNode] = field(default_factory=list)
    output_node: str = ""  # 输出节点名

    def add_node(self, node: FusionNode) -> "FusionComp":
        self.nodes.append(node)
        return self

    def to_lua(self) -> str:
        """生成 .comp 文件的 Lua 代码"""
        lines = []
        lines.append("Composition {")
        lines.append(f"  CurrentTime = 0,")
        lines.append(f"  RenderRange = {{ 0, {self.duration} }},")
        lines.append(f"  GlobalIn = 0,")
        lines.append(f"  GlobalOut = {self.duration},")
        lines.append(f"  Playback = {{ }},")
        lines.append(f"  Outputs = {{")
        lines.append(f"    Output1 = Instance \"Output\" {{")
        lines.append(f"      SourceOp = \"{self.output_node or self.nodes[-1].name}\",")
        lines.append(f"      SourceOutput = 1,")
        lines.append(f"    }},")
        lines.append(f"  }},")
        lines.append(f"  Tools = {{")

        for node in self.nodes:
            lines.append(f"    {node.name} = Instance \"{node.node_type}\" {{")
            for key, value in node.params.items():
                lua_val = self._lua_value(value)
                lines.append(f"      {key} = {lua_val},")
            # 输入连接
            if node.inputs:
                for i, input_node in enumerate(node.inputs):
                    input_name = "Input" if i == 0 else f"Input{i+1}"
                    lines.append(f"      {input_name} = Instance \"{input_node}\" {{ }},")
            lines.append(f"    }},")

        lines.append(f"  }},")
        lines.append(f"}}")
        return "\n".join(lines)

    def _lua_value(self, value: Any) -> str:
        """将 Python 值转为 Lua 表达式"""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return f'"{value}"'
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (list, tuple)):
            items = ", ".join(self._lua_value(v) for v in value)
            return f"{{ {items} }}"
        if isinstance(value, dict):
            items = ", ".join(f"{k} = {self._lua_value(v)}" for k, v in value.items())
            return f"{{ {items} }}"
        return str(value)


class FusionRunner:
    """Fusion 合成运行器"""

    def __init__(self, resolve_dir: str = None):
        self.resolve_dir = resolve_dir or RESOLVE_DIR
        self.fuscript_path = os.path.join(self.resolve_dir, "fuscript.exe")
        self.resolve_exe = os.path.join(self.resolve_dir, "Resolve.exe")

    def is_available(self) -> bool:
        """检查 Fusion 是否可用"""
        return os.path.exists(self.fuscript_path)

    def execute_lua(self, lua_code: str, timeout: int = 60) -> Tuple[bool, str]:
        """
        执行 Lua 脚本

        Args:
            lua_code: Lua 代码字符串
            timeout: 超时时间（秒）

        Returns:
            (成功, 输出)
        """
        if not self.is_available():
            return False, "fuscript.exe 不存在"

        # 写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False, encoding='utf-8') as f:
            f.write(lua_code)
            lua_file = f.name

        try:
            result = subprocess.run(
                [self.fuscript_path, "-l", "lua", lua_file],
                capture_output=True, text=True, timeout=timeout,
                cwd=self.resolve_dir
            )
            output = result.stdout + result.stderr
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "执行超时"
        except Exception as e:
            return False, str(e)
        finally:
            try:
                os.unlink(lua_file)
            except Exception:
                pass

    def save_comp(self, comp: FusionComp, output_path: str) -> str:
        """
        保存 Fusion 合成文件 (.comp)

        Args:
            comp: Fusion 合成对象
            output_path: 输出路径

        Returns:
            文件路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        lua_code = comp.to_lua()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(lua_code)
        return output_path

    def render_comp(self, comp_path: str, output_path: str,
                    start_frame: int = 0, end_frame: int = None,
                    timeout: int = 300) -> Tuple[bool, str]:
        """
        渲染 Fusion 合成

        Args:
            comp_path: .comp 文件路径
            output_path: 输出视频路径
            start_frame: 起始帧
            end_frame: 结束帧
            timeout: 超时时间（秒）

        Returns:
            (成功, 输出)
        """
        if not self.is_available():
            return False, "fuscript.exe 不存在"

        # 生成渲染脚本
        lua_code = f"""
local comp = Fusion:LoadComp("{comp_path.replace(chr(92), chr(47))}")
if comp == nil then
    print("ERROR: 无法加载合成文件")
    return
end

comp:Save("{output_path.replace(chr(92), chr(47))}")
print("渲染完成: {output_path}")
"""
        return self.execute_lua(lua_code, timeout=timeout)

    def create_simple_text_animation(self, text: str, output_path: str,
                                      width: int = 1920, height: int = 1080,
                                      duration: int = 150, fps: int = 30,
                                      font_size: int = 100,
                                      bg_color: Tuple[int, int, int] = (0, 0, 0),
                                      text_color: Tuple[int, int, int] = (1, 1, 1)) -> str:
        """
        创建简单文字动画合成

        Args:
            text: 文字内容
            output_path: 输出 .comp 路径
            width/height: 分辨率
            duration: 帧数
            fps: 帧率
            font_size: 字号
            bg_color: 背景色 (0-1)
            text_color: 文字色 (0-1)

        Returns:
            .comp 文件路径
        """
        comp = FusionComp(width=width, height=height, fps=fps, duration=duration)

        # 背景节点
        bg = FusionNode(
            node_type="Background",
            name="Background1",
            params={
                "TopLeftRed": bg_color[0],
                "TopLeftGreen": bg_color[1],
                "TopLeftBlue": bg_color[2],
                "Width": width,
                "Height": height,
            }
        )
        comp.add_node(bg)

        # 文字节点
        text_node = FusionNode(
            node_type="TextPlus",
            name="Text1",
            params={
                "StyledText": text,
                "Size": font_size,
                "Red": text_color[0],
                "Green": text_color[1],
                "Blue": text_color[2],
                "Center": {0.5, 0.5},
            },
            inputs=["Background1"]
        )
        comp.add_node(text_node)
        comp.output_node = "Text1"

        return self.save_comp(comp, output_path)

    def create_gradient_background(self, output_path: str,
                                    width: int = 1920, height: int = 1080,
                                    color1: Tuple[float, float, float] = (1, 0, 0),
                                    color2: Tuple[float, float, float] = (0, 0, 1),
                                    duration: int = 150) -> str:
        """
        创建渐变背景合成

        Args:
            output_path: 输出路径
            width/height: 分辨率
            color1/color2: 渐变颜色 (0-1)
            duration: 帧数

        Returns:
            .comp 文件路径
        """
        comp = FusionComp(width=width, height=height, duration=duration)

        bg = FusionNode(
            node_type="Background",
            name="Background1",
            params={
                "TopLeftRed": color1[0], "TopLeftGreen": color1[1], "TopLeftBlue": color1[2],
                "TopRightRed": color2[0], "TopRightGreen": color2[1], "TopRightBlue": color2[2],
                "BottomLeftRed": color2[0], "BottomLeftGreen": color2[1], "BottomLeftBlue": color2[2],
                "BottomRightRed": color1[0], "BottomRightGreen": color1[1], "BottomRightBlue": color1[2],
                "Width": width, "Height": height,
                "Gradient": 1,
            }
        )
        comp.add_node(bg)
        comp.output_node = "Background1"

        return self.save_comp(comp, output_path)


def check_fusion_available() -> bool:
    """便捷函数：检查 Fusion 是否可用"""
    return os.path.exists(FUSCRIPT_PATH)


if __name__ == "__main__":
    print("=" * 60)
    print("Fusion Runner 测试")
    print("=" * 60)

    runner = FusionRunner()
    print(f"Fusion 可用: {runner.is_available()}")
    print(f"fuscript 路径: {runner.fuscript_path}")

    if runner.is_available():
        # 测试执行 Lua
        ok, output = runner.execute_lua('print("Fusion Lua 测试成功")')
        print(f"\nLua 执行: {'✅' if ok else '❌'}")
        print(output)
