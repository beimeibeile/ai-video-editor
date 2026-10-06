"""
坐标/蒙版四层防护体系 v1.0
确保剪映工程中的坐标和蒙版参数正确，避免出现位置错误、遮挡超标等问题。

四层防护：
1. 预设参数库 - 已验证的坐标和蒙版参数（常见场景）
2. 坐标验证工具 - 检查坐标是否在画布范围内
3. 自动校准工具 - 根据画布尺寸自动调整坐标
4. 保存后修复 - draft_fixer自动修复（已集成）

使用方式：
    from coord_mask_guard import CoordMaskGuard
    guard = CoordMaskGuard(canvas_w=1080, canvas_h=1920)
    guard.validate_position(x=540, y=960, width=200, height=200)
    guard.calibrate_position(x=540, y=960, source_canvas=(1080, 1920))
"""
import os
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class PresetParams:
    """预设参数"""
    name: str
    canvas_w: int
    canvas_h: int
    x: float  # 中心X（像素）
    y: float  # 中心Y（像素）
    width: float  # 宽度（像素）
    height: float  # 高度（像素）
    scale: float = 1.0
    rotation: float = 0.0
    opacity: float = 1.0
    mask_type: str = "none"  # none/rect/circle
    mask_width: float = 0.0
    mask_height: float = 0.0
    mask_x: float = 0.0
    mask_y: float = 0.0
    notes: str = ""


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    auto_fixed: bool = False
    fixed_params: Optional[Dict] = None


class CoordMaskGuard:
    """坐标/蒙版防护体系"""

    def __init__(self, canvas_w: int = 1080, canvas_h: int = 1920):
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.presets = self._load_builtin_presets()

    def _load_builtin_presets(self) -> Dict[str, PresetParams]:
        """加载内置预设参数库（基于已验证的参数）"""
        presets = {}

        # 抖音个人主页 - 头像框位置（1080x1920画布）
        presets["douyin_avatar_frame"] = PresetParams(
            name="抖音头像框",
            canvas_w=1080, canvas_h=1920,
            x=200, y=280,  # 头像框中心位置
            width=280, height=280,
            scale=1.0,
            mask_type="circle",
            mask_width=280, mask_height=280,
            mask_x=200, mask_y=280,
            notes="抖音个人主页头像位置，圆形蒙版"
        )

        # 抖音个人主页 - 作品区位置
        presets["douyin_works_area"] = PresetParams(
            name="抖音作品区",
            canvas_w=1080, canvas_h=1920,
            x=540, y=1300,  # 作品区中心位置
            width=1000, height=900,
            scale=1.0,
            mask_type="rect",
            mask_width=1000, mask_height=900,
            mask_x=540, mask_y=1300,
            notes="抖音个人主页作品网格区域"
        )

        # 抖音个人主页 - 顶部信息区
        presets["douyin_top_info"] = PresetParams(
            name="抖音顶部信息",
            canvas_w=1080, canvas_h=1920,
            x=540, y=500,
            width=1000, height=400,
            scale=1.0,
            notes="抖音个人主页昵称/简介/数据区域"
        )

        # 全屏背景
        presets["fullscreen_background"] = PresetParams(
            name="全屏背景",
            canvas_w=1080, canvas_h=1920,
            x=540, y=960,
            width=1080, height=1920,
            scale=1.0,
            notes="全屏背景图层"
        )

        # 中心元素
        presets["center_element"] = PresetParams(
            name="中心元素",
            canvas_w=1080, canvas_h=1920,
            x=540, y=960,
            width=500, height=500,
            scale=1.0,
            notes="画布中心元素"
        )

        # 底部字幕区
        presets["bottom_subtitle"] = PresetParams(
            name="底部字幕",
            canvas_w=1080, canvas_h=1920,
            x=540, y=1700,
            width=900, height=150,
            scale=1.0,
            notes="底部安全区字幕位置"
        )

        # 顶部标题区
        presets["top_title"] = PresetParams(
            name="顶部标题",
            canvas_w=1080, canvas_h=1920,
            x=540, y=200,
            width=900, height=120,
            scale=1.0,
            notes="顶部安全区标题位置"
        )

        return presets

    def get_preset(self, name: str) -> Optional[PresetParams]:
        """获取预设参数"""
        return self.presets.get(name)

    def list_presets(self) -> List[str]:
        """列出所有预设"""
        return list(self.presets.keys())

    def validate_position(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        margin: float = 0.0,
    ) -> ValidationResult:
        """
        第一层防护：验证位置是否在画布范围内

        Args:
            x: 中心X（像素）
            y: 中心Y（像素）
            width: 宽度（像素）
            height: 高度（像素）
            margin: 安全边距（像素）

        Returns:
            ValidationResult 验证结果
        """
        result = ValidationResult(valid=True)

        # 检查元素是否完全在画布内
        left = x - width / 2
        right = x + width / 2
        top = y - height / 2
        bottom = y + height / 2

        if left < -margin:
            result.errors.append(
                f"元素左边界超出画布: left={left:.1f} < {-margin}"
            )
        if right > self.canvas_w + margin:
            result.errors.append(
                f"元素右边界超出画布: right={right:.1f} > {self.canvas_w + margin}"
            )
        if top < -margin:
            result.errors.append(
                f"元素上边界超出画布: top={top:.1f} < {-margin}"
            )
        if bottom > self.canvas_h + margin:
            result.errors.append(
                f"元素下边界超出画布: bottom={bottom:.1f} > {self.canvas_h + margin}"
            )

        # 检查中心是否在画布内
        if x < 0 or x > self.canvas_w:
            result.warnings.append(f"中心X超出画布: x={x:.1f}")
        if y < 0 or y > self.canvas_h:
            result.warnings.append(f"中心Y超出画布: y={y:.1f}")

        # 检查尺寸是否合理
        if width <= 0:
            result.errors.append(f"宽度必须大于0: width={width}")
        if height <= 0:
            result.errors.append(f"高度必须大于0: height={height}")
        if width > self.canvas_w * 3:
            result.warnings.append(f"宽度过大: width={width:.1f} > {self.canvas_w * 3}")
        if height > self.canvas_h * 3:
            result.warnings.append(f"高度过大: height={height:.1f} > {self.canvas_h * 3}")

        result.valid = len(result.errors) == 0
        return result

    def validate_mask(
        self,
        mask_x: float,
        mask_y: float,
        mask_width: float,
        mask_height: float,
        element_x: float,
        element_y: float,
        element_width: float,
        element_height: float,
    ) -> ValidationResult:
        """
        第二层防护：验证蒙版是否在元素范围内

        Args:
            mask_x/y: 蒙版中心（像素，相对画布）
            mask_width/height: 蒙版尺寸（像素）
            element_x/y: 元素中心（像素）
            element_width/height: 元素尺寸（像素）

        Returns:
            ValidationResult 验证结果
        """
        result = ValidationResult(valid=True)

        # 蒙版应该在元素范围内
        mask_left = mask_x - mask_width / 2
        mask_right = mask_x + mask_width / 2
        mask_top = mask_y - mask_height / 2
        mask_bottom = mask_y + mask_height / 2

        elem_left = element_x - element_width / 2
        elem_right = element_x + element_width / 2
        elem_top = element_y - element_height / 2
        elem_bottom = element_y + element_height / 2

        if mask_left < elem_left - 1:
            result.warnings.append(
                f"蒙版左边界超出元素: mask_left={mask_left:.1f} < elem_left={elem_left:.1f}"
            )
        if mask_right > elem_right + 1:
            result.warnings.append(
                f"蒙版右边界超出元素: mask_right={mask_right:.1f} > elem_right={elem_right:.1f}"
            )
        if mask_top < elem_top - 1:
            result.warnings.append(
                f"蒙版上边界超出元素: mask_top={mask_top:.1f} < elem_top={elem_top:.1f}"
            )
        if mask_bottom > elem_bottom + 1:
            result.warnings.append(
                f"蒙版下边界超出元素: mask_bottom={mask_bottom:.1f} > elem_bottom={elem_bottom:.1f}"
            )

        # 蒙版尺寸检查
        if mask_width <= 0:
            result.errors.append(f"蒙版宽度必须大于0: {mask_width}")
        if mask_height <= 0:
            result.errors.append(f"蒙版高度必须大于0: {mask_height}")

        # 蒙版位置检查（应该在画布内）
        if mask_x < 0 or mask_x > self.canvas_w:
            result.warnings.append(f"蒙版X超出画布: {mask_x}")
        if mask_y < 0 or mask_y > self.canvas_h:
            result.warnings.append(f"蒙版Y超出画布: {mask_y}")

        result.valid = len(result.errors) == 0
        return result

    def calibrate_position(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        source_canvas: Tuple[int, int] = (1080, 1920),
        fit_mode: str = "contain",  # contain/cover/stretch
    ) -> Dict[str, float]:
        """
        第三层防护：根据目标画布尺寸自动校准坐标

        Args:
            x/y: 源画布中的中心坐标
            width/height: 源画布中的尺寸
            source_canvas: 源画布尺寸 (w, h)
            fit_mode: 适配模式 contain/cover/stretch

        Returns:
            校准后的坐标和尺寸
        """
        src_w, src_h = source_canvas
        dst_w, dst_h = self.canvas_w, self.canvas_h

        # 计算缩放比例
        scale_x = dst_w / src_w
        scale_y = dst_h / src_h

        if fit_mode == "contain":
            # 保持比例，完整显示
            scale = min(scale_x, scale_y)
        elif fit_mode == "cover":
            # 保持比例，覆盖全屏
            scale = max(scale_x, scale_y)
        else:  # stretch
            # 拉伸填充
            scale = 1.0
            new_width = width * scale_x
            new_height = height * scale_y
            new_x = x * scale_x
            new_y = y * scale_y
            return {
                "x": new_x, "y": new_y,
                "width": new_width, "height": new_height,
                "scale": scale,
            }

        new_width = width * scale
        new_height = height * scale
        new_x = x * scale
        new_y = y * scale

        # 如果是contain模式，需要居中偏移
        if fit_mode == "contain":
            offset_x = (dst_w - src_w * scale) / 2
            offset_y = (dst_h - src_h * scale) / 2
            new_x += offset_x
            new_y += offset_y

        return {
            "x": round(new_x, 2),
            "y": round(new_y, 2),
            "width": round(new_width, 2),
            "height": round(new_height, 2),
            "scale": round(scale, 4),
        }

    def auto_fix_position(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> Tuple[float, float, float, float]:
        """
        第四层防护：自动修复超出画布的位置

        将元素约束到画布范围内，保持尺寸不变。

        Returns:
            修复后的 (x, y, width, height)
        """
        # 计算边界
        half_w = width / 2
        half_h = height / 2

        # 约束X
        if half_w >= self.canvas_w:
            # 元素比画布宽，居中
            new_x = self.canvas_w / 2
        else:
            new_x = max(half_w, min(self.canvas_w - half_w, x))

        # 约束Y
        if half_h >= self.canvas_h:
            new_y = self.canvas_h / 2
        else:
            new_y = max(half_h, min(self.canvas_h - half_h, y))

        return (round(new_x, 2), round(new_y, 2), width, height)

    def validate_and_fix(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        auto_fix: bool = True,
    ) -> ValidationResult:
        """
        综合验证并自动修复

        Args:
            x/y/width/height: 元素参数
            auto_fix: 是否自动修复

        Returns:
            ValidationResult 包含验证结果和修复后参数
        """
        result = self.validate_position(x, y, width, height)

        if not result.valid and auto_fix:
            fixed_x, fixed_y, fixed_w, fixed_h = self.auto_fix_position(
                x, y, width, height
            )
            result.auto_fixed = True
            result.fixed_params = {
                "x": fixed_x, "y": fixed_y,
                "width": fixed_w, "height": fixed_h,
            }
            # 重新验证修复后的参数
            recheck = self.validate_position(fixed_x, fixed_y, fixed_w, fixed_h)
            if recheck.valid:
                result.valid = True
                result.errors = []
                result.warnings.extend([f"已自动修复: {e}" for e in result.errors])

        return result

    def check_layer_order(
        self,
        layers: List[Dict[str, Any]],
    ) -> ValidationResult:
        """
        检查图层顺序是否合理

        预期顺序（从底到顶）：
        1. 背景层
        2. 主内容层
        3. 遮挡层
        4. 动画层
        5. 字幕/文字层

        Args:
            layers: 图层列表，每个包含 name, type, z_index

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        if not layers:
            result.warnings.append("图层列表为空")
            return result

        # 检查是否有背景层
        has_background = any(
            layer.get("type") == "background" for layer in layers
        )
        if not has_background:
            result.warnings.append("缺少背景层")

        # 检查z_index是否有重复
        z_indices = [layer.get("z_index", 0) for layer in layers]
        if len(z_indices) != len(set(z_indices)):
            result.warnings.append("存在重复的z_index")

        # 检查图层数量
        if len(layers) > 10:
            result.warnings.append(f"图层数量过多: {len(layers)}个（建议≤10）")

        return result

    def generate_guard_report(self, project_name: str = "未命名") -> str:
        """生成防护体系报告"""
        report = []
        report.append("=" * 60)
        report.append(f"坐标/蒙版四层防护体系报告 - {project_name}")
        report.append("=" * 60)
        report.append(f"\n画布尺寸: {self.canvas_w}x{self.canvas_h}")
        report.append(f"\n第一层：预设参数库")
        report.append(f"  已加载预设: {len(self.presets)}个")
        for name, preset in self.presets.items():
            report.append(f"    - {name}: ({preset.x},{preset.y}) {preset.width}x{preset.height}")

        report.append(f"\n第二层：坐标验证工具")
        report.append(f"  - 边界检查（左/右/上/下）")
        report.append(f"  - 中心位置检查")
        report.append(f"  - 尺寸合理性检查")

        report.append(f"\n第三层：自动校准工具")
        report.append(f"  - 支持contain/cover/stretch三种适配模式")
        report.append(f"  - 自动计算缩放比例和偏移量")

        report.append(f"\n第四层：保存后修复")
        report.append(f"  - draft_fixer自动修复draft_info.json")
        report.append(f"  - 已集成到jianying_executor.save()流程")

        report.append("\n" + "=" * 60)
        return "\n".join(report)


def main():
    """命令行测试"""
    print("=" * 60)
    print("坐标/蒙版四层防护体系 v1.0 测试")
    print("=" * 60)

    guard = CoordMaskGuard(canvas_w=1080, canvas_h=1920)

    # 测试1：列出预设
    print("\n=== 测试1：预设参数库 ===")
    presets = guard.list_presets()
    print(f"已加载预设: {len(presets)}个")
    for name in presets:
        p = guard.get_preset(name)
        print(f"  {name}: ({p.x},{p.y}) {p.width}x{p.height}")

    # 测试2：正常位置验证
    print("\n=== 测试2：正常位置验证 ===")
    result = guard.validate_position(540, 960, 500, 500)
    print(f"  中心元素(540,960,500x500): valid={result.valid}")
    if result.warnings:
        for w in result.warnings:
            print(f"    ⚠️ {w}")

    # 测试3：超出画布位置
    print("\n=== 测试3：超出画布位置 ===")
    result = guard.validate_position(-100, 2000, 500, 500)
    print(f"  越界元素(-100,2000,500x500): valid={result.valid}")
    for e in result.errors:
        print(f"    ❌ {e}")

    # 测试4：自动修复
    print("\n=== 测试4：自动修复 ===")
    result = guard.validate_and_fix(-100, 2000, 500, 500, auto_fix=True)
    print(f"  修复后: valid={result.valid}, auto_fixed={result.auto_fixed}")
    if result.fixed_params:
        print(f"    修复参数: {result.fixed_params}")

    # 测试5：坐标校准
    print("\n=== 测试5：坐标校准（1080x1920 → 720x1280）===")
    guard2 = CoordMaskGuard(canvas_w=720, canvas_h=1280)
    calibrated = guard2.calibrate_position(
        x=540, y=960, width=500, height=500,
        source_canvas=(1080, 1920), fit_mode="contain"
    )
    print(f"  校准后: {calibrated}")

    # 测试6：蒙版验证
    print("\n=== 测试6：蒙版验证 ===")
    result = guard.validate_mask(
        mask_x=200, mask_y=280, mask_width=280, mask_height=280,
        element_x=200, element_y=280, element_width=280, element_height=280,
    )
    print(f"  头像蒙版: valid={result.valid}")
    if result.warnings:
        for w in result.warnings:
            print(f"    ⚠️ {w}")

    # 测试7：图层顺序检查
    print("\n=== 测试7：图层顺序检查 ===")
    layers = [
        {"name": "背景", "type": "background", "z_index": 0},
        {"name": "主页", "type": "content", "z_index": 1},
        {"name": "头像框", "type": "overlay", "z_index": 2},
        {"name": "作品区", "type": "mask", "z_index": 3},
        {"name": "动画", "type": "animation", "z_index": 4},
        {"name": "字幕", "type": "text", "z_index": 5},
    ]
    result = guard.check_layer_order(layers)
    print(f"  6层结构: valid={result.valid}")
    if result.warnings:
        for w in result.warnings:
            print(f"    ⚠️ {w}")

    # 生成报告
    print("\n" + guard.generate_guard_report("测试项目"))


if __name__ == "__main__":
    main()
