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
        """生成 .comp 文件的 Lua 代码（标准Fusion格式）"""
        lines = []
        lines.append("Composition {")
        lines.append(f"\tCurrentTime = 0,")
        lines.append(f"\tRenderRange = {{ 0, {self.duration} }},")
        lines.append(f"\tGlobalIn = 0,")
        lines.append(f"\tGlobalOut = {self.duration},")
        lines.append(f"\tOutputs = {{")
        lines.append(f"\t\tOutput1 = Instance \"Output\" {{")
        lines.append(f"\t\t\tSourceOp = \"{self.output_node or self.nodes[-1].name}\",")
        lines.append(f"\t\t\tSourceOutput = 1,")
        lines.append(f"\t\t}},")
        lines.append(f"\t}},")
        lines.append(f"\tTools = {{")

        for idx, node in enumerate(self.nodes):
            pos_x = 100 + (idx % 4) * 200
            pos_y = 100 + (idx // 4) * 150
            lines.append(f"\t\t{node.name} = Instance \"{node.node_type}\" {{")
            lines.append(f"\t\t\tCtrlWZoom = false,")
            lines.append(f"\t\t\tInputs = {{")
            # 节点参数
            for key, value in node.params.items():
                lua_val = self._lua_value(value)
                lines.append(f"\t\t\t\t{key} = Input {{ Value = {lua_val}, }},")
            # 输入连接
            if node.inputs:
                for i, input_node in enumerate(node.inputs):
                    input_name = "Input" if i == 0 else f"Input{i+1}"
                    lines.append(f"\t\t\t\t{input_name} = Input {{")
                    lines.append(f"\t\t\t\t\tSourceOp = \"{input_node}\",")
                    lines.append(f"\t\t\t\t\tSourceOutput = 1,")
                    lines.append(f"\t\t\t\t}},")
            lines.append(f"\t\t\t}},")
            lines.append(f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos_x}, {pos_y} }} }},")
            lines.append(f"\t\t}},")

        lines.append(f"\t}},")
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

    def is_resolve_running(self) -> bool:
        """检查 DaVinci Resolve 是否正在运行"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Resolve.exe"],
                capture_output=True, text=True, timeout=10
            )
            return "Resolve.exe" in result.stdout
        except Exception:
            return False

    def render_comp(self, comp_path: str, output_path: str,
                    start_frame: int = 0, end_frame: int = None,
                    timeout: int = 300, wait_for_resolve: bool = True) -> Tuple[bool, str]:
        """
        渲染 Fusion 合成

        需要 DaVinci Resolve 正在运行。如果未运行，会提示用户启动。

        Args:
            comp_path: .comp 文件路径
            output_path: 输出视频路径
            start_frame: 起始帧
            end_frame: 结束帧（None=使用comp默认范围）
            timeout: 超时时间（秒）
            wait_for_resolve: 是否等待Resolve启动（最多60秒）

        Returns:
            (成功, 输出)
        """
        if not self.is_available():
            return False, "fuscript.exe 不存在"

        # 检查Resolve是否运行
        if not self.is_resolve_running():
            if wait_for_resolve:
                print("  DaVinci Resolve 未运行，正在启动...")
                try:
                    subprocess.Popen([self.resolve_exe], cwd=self.resolve_dir)
                    # 等待Resolve启动（最多60秒）
                    for i in range(60):
                        import time
                        time.sleep(1)
                        if self.is_resolve_running():
                            print(f"  Resolve已启动（等待{i+1}秒）")
                            break
                    else:
                        return False, "DaVinci Resolve 启动超时，请手动启动后重试"
                except Exception as e:
                    return False, f"无法启动Resolve: {e}"
            else:
                return False, "DaVinci Resolve 未运行，请先启动Resolve"

        # 生成渲染脚本
        comp_path_norm = comp_path.replace("\\", "/")
        output_path_norm = output_path.replace("\\", "/")
        end_frame_str = str(end_frame) if end_frame is not None else "nil"

        lua_code = f"""
local fusion = Fusion()
if fusion == nil then
    print("ERROR: 无法连接Fusion")
    return
end

local comp = fusion:LoadComp("{comp_path_norm}")
if comp == nil then
    print("ERROR: 无法加载合成文件")
    return
end

print("合成加载成功")

-- 添加Saver节点用于输出
local saver = comp:AddTool("Saver")
if saver then
    saver.Clip = "{output_path_norm}"
    -- 连接到comp的输出
    local tools = comp:GetToolList()
    if #tools > 0 then
        saver.Input = tools[#tools].Output
    end
end

-- 渲染
print("开始渲染...")
comp:Render({{startFrame = {start_frame}, endFrame = {end_frame_str}}})
print("渲染完成")

-- 检查输出
local file = io.open("{output_path_norm}", "r")
if file then
    local size = file:seek("end")
    file:close()
    print("输出文件大小: " .. size .. " bytes")
else
    print("WARNING: 输出文件未生成")
end
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

    def create_particle_effect(self, output_path: str,
                                width: int = 1920, height: int = 1080,
                                duration: int = 150,
                                particle_count: int = 500,
                                particle_size: float = 0.02,
                                emitter_type: str = "Point",
                                velocity: float = 0.5,
                                lifetime: float = 1.0,
                                color: Tuple[float, float, float] = (1, 0.8, 0.3),
                                bg_color: Tuple[float, float, float] = (0, 0, 0)) -> str:
        """
        创建粒子特效合成

        Args:
            output_path: 输出 .comp 路径
            width/height: 分辨率
            duration: 帧数
            particle_count: 粒子数量
            particle_size: 粒子大小（相对画布）
            emitter_type: 发射器类型 Point/Line/Area
            velocity: 发射速度
            lifetime: 粒子生命周期（秒）
            color: 粒子颜色 (0-1)
            bg_color: 背景色 (0-1)

        Returns:
            .comp 文件路径
        """
        comp = FusionComp(width=width, height=height, duration=duration)

        # 背景
        bg = FusionNode(
            node_type="Background",
            name="Background1",
            params={
                "TopLeftRed": bg_color[0], "TopLeftGreen": bg_color[1], "TopLeftBlue": bg_color[2],
                "Width": width, "Height": height,
            }
        )
        comp.add_node(bg)

        # 粒子发射器
        emitter = FusionNode(
            node_type="pParticleEmitter",
            name="pParticleEmitter1",
            params={
                "Number": particle_count,
                "Size": particle_size,
                "Velocity": velocity,
                "LifeTime": lifetime,
                "ColorRed": color[0],
                "ColorGreen": color[1],
                "ColorBlue": color[2],
                "EmitterType": emitter_type,
            },
            inputs=["Background1"]
        )
        comp.add_node(emitter)

        # 粒子渲染
        renderer = FusionNode(
            node_type="pRender",
            name="pRender1",
            params={
                "Size": particle_size,
                "ColorRed": color[0],
                "ColorGreen": color[1],
                "ColorBlue": color[2],
            },
            inputs=["pParticleEmitter1"]
        )
        comp.add_node(renderer)
        comp.output_node = "pRender1"

        return self.save_comp(comp, output_path)

    def create_text_animation(self, output_path: str,
                               text: str,
                               width: int = 1920, height: int = 1080,
                               duration: int = 150,
                               font_size: int = 120,
                               text_color: Tuple[float, float, float] = (1, 1, 1),
                               bg_color: Tuple[float, float, float] = (0, 0, 0),
                               animation_type: str = "fade_in",
                               position: Tuple[float, float] = (0.5, 0.5)) -> str:
        """
        创建文字动画合成

        Args:
            output_path: 输出 .comp 路径
            text: 文字内容
            width/height: 分辨率
            duration: 帧数
            font_size: 字号
            text_color: 文字颜色 (0-1)
            bg_color: 背景色 (0-1)
            animation_type: 动画类型 fade_in/slide_up/scale_in/typewriter
            position: 文字位置 (0-1, 0-1)

        Returns:
            .comp 文件路径
        """
        comp = FusionComp(width=width, height=height, duration=duration)

        # 背景
        bg = FusionNode(
            node_type="Background",
            name="Background1",
            params={
                "TopLeftRed": bg_color[0], "TopLeftGreen": bg_color[1], "TopLeftBlue": bg_color[2],
                "Width": width, "Height": height,
            }
        )
        comp.add_node(bg)

        # 文字+节点
        text_params = {
            "StyledText": text,
            "Size": font_size,
            "Red": text_color[0],
            "Green": text_color[1],
            "Blue": text_color[2],
            "Center": {position[0], position[1]},
        }

        # 根据动画类型设置关键帧
        if animation_type == "fade_in":
            text_params["Opacity"] = 0  # 起始透明
        elif animation_type == "slide_up":
            text_params["Center"] = {position[0], position[1] + 0.3}  # 从下方滑入
        elif animation_type == "scale_in":
            text_params["Size"] = font_size * 0.1  # 从小放大

        text_node = FusionNode(
            node_type="TextPlus",
            name="Text1",
            params=text_params,
            inputs=["Background1"]
        )
        comp.add_node(text_node)
        comp.output_node = "Text1"

        return self.save_comp(comp, output_path)

    def create_lens_flare(self, output_path: str,
                          width: int = 1920, height: int = 1080,
                          duration: int = 150,
                          flare_position: Tuple[float, float] = (0.5, 0.5),
                          intensity: float = 1.0,
                          color: Tuple[float, float, float] = (1, 0.9, 0.7),
                          bg_color: Tuple[float, float, float] = (0, 0, 0)) -> str:
        """
        创建镜头光晕特效合成

        Args:
            output_path: 输出 .comp 路径
            width/height: 分辨率
            duration: 帧数
            flare_position: 光晕位置 (0-1, 0-1)
            intensity: 光晕强度
            color: 光晕颜色 (0-1)
            bg_color: 背景色 (0-1)

        Returns:
            .comp 文件路径
        """
        comp = FusionComp(width=width, height=height, duration=duration)

        # 背景
        bg = FusionNode(
            node_type="Background",
            name="Background1",
            params={
                "TopLeftRed": bg_color[0], "TopLeftGreen": bg_color[1], "TopLeftBlue": bg_color[2],
                "Width": width, "Height": height,
            }
        )
        comp.add_node(bg)

        # 镜头光晕
        flare = FusionNode(
            node_type="LensFlare",
            name="LensFlare1",
            params={
                "Center": {flare_position[0], flare_position[1]},
                "Intensity": intensity,
                "ColorRed": color[0],
                "ColorGreen": color[1],
                "ColorBlue": color[2],
                "LightSource": 1,
            },
            inputs=["Background1"]
        )
        comp.add_node(flare)

        # 辉光增强
        glow = FusionNode(
            node_type="Glow",
            name="Glow1",
            params={
                "Glow": 0.5,
                "Size": 0.1,
            },
            inputs=["LensFlare1"]
        )
        comp.add_node(glow)
        comp.output_node = "Glow1"

        return self.save_comp(comp, output_path)

    def create_glow_effect(self, output_path: str,
                           width: int = 1920, height: int = 1080,
                           duration: int = 150,
                           glow_size: float = 0.1,
                           glow_intensity: float = 0.8,
                           source_color: Tuple[float, float, float] = (0, 1, 1),
                           bg_color: Tuple[float, float, float] = (0, 0, 0)) -> str:
        """
        创建辉光特效合成

        Args:
            output_path: 输出 .comp 路径
            width/height: 分辨率
            duration: 帧数
            glow_size: 辉光大小
            glow_intensity: 辉光强度
            source_color: 源颜色 (0-1)
            bg_color: 背景色 (0-1)

        Returns:
            .comp 文件路径
        """
        comp = FusionComp(width=width, height=height, duration=duration)

        # 背景
        bg = FusionNode(
            node_type="Background",
            name="Background1",
            params={
                "TopLeftRed": bg_color[0], "TopLeftGreen": bg_color[1], "TopLeftBlue": bg_color[2],
                "Width": width, "Height": height,
            }
        )
        comp.add_node(bg)

        # 源形状（圆形）
        source = FusionNode(
            node_type="Background",
            name="Source1",
            params={
                "TopLeftRed": source_color[0], "TopLeftGreen": source_color[1], "TopLeftBlue": source_color[2],
                "Width": int(width * 0.2), "Height": int(height * 0.2),
            }
        )
        comp.add_node(source)

        # 变换到中心
        transform = FusionNode(
            node_type="Transform",
            name="Transform1",
            params={
                "Center": {0.5, 0.5},
            },
            inputs=["Source1"]
        )
        comp.add_node(transform)

        # 辉光
        glow = FusionNode(
            node_type="Glow",
            name="Glow1",
            params={
                "Glow": glow_intensity,
                "Size": glow_size,
            },
            inputs=["Transform1"]
        )
        comp.add_node(glow)

        # 合并到背景
        merge = FusionNode(
            node_type="Merge",
            name="Merge1",
            params={
                "Center": {0.5, 0.5},
            },
            inputs=["Background1", "Glow1"]
        )
        comp.add_node(merge)
        comp.output_node = "Merge1"

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
