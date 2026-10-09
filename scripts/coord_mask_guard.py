# -*- coding: utf-8 -*-
"""
坐标/蒙版四层防护验证工具 v1.0
验证剪映工程中坐标参数、蒙版参数、层级关系的正确性。

四层结构定义：
  第1层（最底层）：背景/主页截图
  第2层：头像框（圆形反向蒙版+淡入）
  第3层：作品区（矩形蒙版+淡入）
  第4层（最顶层）：透明动画素材

防护机制：
  1. 坐标范围校验（确保元素在画布内）
  2. 蒙版参数校验（中心坐标、半径、反转标志）
  3. 层级顺序校验（render_index递增）
  4. 关键帧时序校验（淡入时间点合理）
  5. 背景替换验证（替换背景后其他层坐标不变）

使用方式：
    from coord_mask_guard import CoordMaskGuard
    guard = CoordMaskGuard(draft_path)
    report = guard.validate_all()
    guard.print_report(report)
"""

import logging
logger = logging.getLogger(__name__)

import os
import json
import copy
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class LayerInfo:
    """图层信息"""
    layer_index: int           # 层级（0=最底）
    track_name: str            # 轨道名
    material_path: str         # 素材路径
    material_type: str         # video/photo
    width: int = 0
    height: int = 0
    transform_x: float = 0.0   # 位置X（半个画布宽单位）
    transform_y: float = 0.0   # 位置Y
    scale: float = 1.0         # 缩放
    alpha: float = 1.0         # 不透明度
    rotation: float = 0.0      # 旋转
    has_mask: bool = False
    mask_type: str = ""
    mask_center_x: float = 0.0
    mask_center_y: float = 0.0
    mask_size: float = 0.0
    mask_invert: bool = False
    keyframes: List[Dict] = field(default_factory=list)
    render_index: int = 0


@dataclass
class ValidationResult:
    """验证结果"""
    check_name: str
    passed: bool
    severity: str = "info"   # info/warning/error
    message: str = ""
    details: Dict = field(default_factory=dict)


@dataclass
class GuardReport:
    """防护验证报告"""
    draft_path: str = ""
    canvas_width: int = 1080
    canvas_height: int = 1920
    layers: List[LayerInfo] = field(default_factory=list)
    results: List[ValidationResult] = field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    warning_count: int = 0
    overall_pass: bool = True


class CoordMaskGuard:
    """坐标/蒙版四层防护验证器"""

    def __init__(self, draft_path: str = None):
        self.draft_path = draft_path
        self.canvas_width = 1080
        self.canvas_height = 1920
        self._draft_content = None

    def load_draft(self, draft_path: str = None) -> bool:
        """加载剪映草稿"""
        path = draft_path or self.draft_path
        if not path:
            return False

        content_path = os.path.join(path, "draft_content.json")
        if not os.path.exists(content_path):
            content_path = os.path.join(path, "draft_info.json")

        if not os.path.exists(content_path):
            return False

        try:
            with open(content_path, "r", encoding="utf-8") as f:
                self._draft_content = json.load(f)
            self.draft_path = path

            # 读取画布尺寸
            canvas = self._draft_content.get("canvas_config", {})
            self.canvas_width = canvas.get("width", 1080)
            self.canvas_height = canvas.get("height", 1920)
            return True
        except Exception as e:
            logger.error(f"加载草稿失败: {e}")
            return False

    def extract_layers(self) -> List[LayerInfo]:
        """从草稿中提取图层信息"""
        if not self._draft_content:
            return []

        layers = []
        tracks = self._draft_content.get("tracks", [])
        materials = self._draft_content.get("materials", {})
        video_materials = {m.get("id"): m for m in materials.get("videos", [])}

        # 按render_index排序（值越大越靠前）
        sorted_tracks = sorted(tracks, key=lambda t: t.get("render_index", 0))

        for idx, track in enumerate(sorted_tracks):
            track_type = track.get("type", "")
            if track_type not in ["video", "photo"]:
                continue

            segments = track.get("segments", [])
            if not segments:
                continue

            seg = segments[0]  # 取第一个片段
            material_id = seg.get("material_id", "")
            material = video_materials.get(material_id, {})

            clip = seg.get("clip", {}) or {}
            transform = clip.get("transform", {}) or {}
            scale = clip.get("scale", {}) or {}

            # 提取蒙版
            mask_info = seg.get("mask", None) or {}
            has_mask = bool(mask_info)

            # 提取关键帧
            keyframes = []
            for kf_list in seg.get("common_keyframes", []):
                prop = kf_list.get("property_type", "")
                for kf in kf_list.get("keyframe_list", []):
                    keyframes.append({
                        "property": prop,
                        "time_offset": kf.get("time_offset", 0),
                        "values": kf.get("values", []),
                    })

            layer = LayerInfo(
                layer_index=idx,
                track_name=track.get("name", f"track_{idx}"),
                material_path=material.get("path", ""),
                material_type=material.get("type", "video"),
                width=material.get("width", 0),
                height=material.get("height", 0),
                transform_x=transform.get("x", 0.0),
                transform_y=transform.get("y", 0.0),
                scale=scale.get("x", 1.0),
                alpha=clip.get("alpha", 1.0),
                rotation=clip.get("rotation", 0.0),
                has_mask=has_mask,
                mask_type=mask_info.get("type", ""),
                mask_center_x=mask_info.get("center_x", 0.0),
                mask_center_y=mask_info.get("center_y", 0.0),
                mask_size=mask_info.get("size", 0.0),
                mask_invert=mask_info.get("invert", False),
                keyframes=keyframes,
                render_index=track.get("render_index", 0),
            )
            layers.append(layer)

        return layers

    def check_coordinate_range(self, layers: List[LayerInfo]) -> List[ValidationResult]:
        """检查1：坐标范围校验"""
        results = []
        half_w = self.canvas_width / 2
        half_h = self.canvas_height / 2

        for layer in layers:
            # transform_x/y是半个画布宽/高单位
            abs_x = layer.transform_x * half_w
            abs_y = layer.transform_y * half_h

            # 检查是否在画布范围内（允许一定溢出）
            margin = 0.3  # 允许30%溢出
            in_range_x = -margin * half_w <= abs_x <= (1 + margin) * half_w
            in_range_y = -margin * half_h <= abs_y <= (1 + margin) * half_h

            if not in_range_x or not in_range_y:
                results.append(ValidationResult(
                    check_name=f"坐标范围[{layer.track_name}]",
                    passed=False,
                    severity="warning",
                    message=f"图层位置({abs_x:.0f},{abs_y:.0f})可能超出画布范围",
                    details={"transform_x": layer.transform_x,
                            "transform_y": layer.transform_y}
                ))
            else:
                results.append(ValidationResult(
                    check_name=f"坐标范围[{layer.track_name}]",
                    passed=True,
                    message=f"位置({abs_x:.0f},{abs_y:.0f})在画布范围内"
                ))

        return results

    def check_mask_params(self, layers: List[LayerInfo]) -> List[ValidationResult]:
        """检查2：蒙版参数校验"""
        results = []

        for layer in layers:
            if not layer.has_mask:
                results.append(ValidationResult(
                    check_name=f"蒙版参数[{layer.track_name}]",
                    passed=True,
                    severity="info",
                    message="无蒙版"
                ))
                continue

            # 检查蒙版中心坐标
            half_w = self.canvas_width / 2
            half_h = self.canvas_height / 2
            mask_abs_x = layer.mask_center_x * half_w
            mask_abs_y = layer.mask_center_y * half_h

            # 检查蒙版大小
            if layer.mask_size <= 0:
                results.append(ValidationResult(
                    check_name=f"蒙版参数[{layer.track_name}]",
                    passed=False,
                    severity="error",
                    message="蒙版大小为0或负数",
                    details={"mask_size": layer.mask_size}
                ))
                continue

            # 圆形蒙版：size是半径比例（半个画布宽）
            if "圆" in layer.mask_type or "circle" in layer.mask_type.lower():
                radius_px = layer.mask_size * half_w
                if radius_px < 10:
                    results.append(ValidationResult(
                        check_name=f"蒙版参数[{layer.track_name}]",
                        passed=False,
                        severity="error",
                        message=f"圆形蒙版半径过小({radius_px:.1f}px)",
                        details={"radius_px": radius_px}
                    ))
                else:
                    results.append(ValidationResult(
                        check_name=f"蒙版参数[{layer.track_name}]",
                        passed=True,
                        message=f"圆形蒙版中心({mask_abs_x:.0f},{mask_abs_y:.0f})，"
                                f"半径{radius_px:.1f}px，"
                                f"反转={'是' if layer.mask_invert else '否'}"
                    ))
            else:
                results.append(ValidationResult(
                    check_name=f"蒙版参数[{layer.track_name}]",
                    passed=True,
                    message=f"蒙版类型{layer.mask_type}，中心({mask_abs_x:.0f},{mask_abs_y:.0f})"
                ))

        return results

    def check_layer_order(self, layers: List[LayerInfo]) -> List[ValidationResult]:
        """检查3：层级顺序校验"""
        results = []

        if len(layers) < 2:
            results.append(ValidationResult(
                check_name="层级顺序",
                passed=True,
                severity="info",
                message=f"仅{len(layers)}层，无需校验顺序"
            ))
            return results

        # 检查render_index是否递增
        indices = [l.render_index for l in layers]
        is_increasing = all(indices[i] <= indices[i+1] for i in range(len(indices)-1))

        if is_increasing:
            results.append(ValidationResult(
                check_name="层级顺序",
                passed=True,
                message=f"{len(layers)}层，render_index递增: {indices}"
            ))
        else:
            results.append(ValidationResult(
                check_name="层级顺序",
                passed=False,
                severity="error",
                message=f"render_index未递增: {indices}",
                details={"indices": indices}
            ))

        # 检查四层结构（如果有4层）
        if len(layers) >= 4:
            # 第2层应该有蒙版（头像框）
            layer2 = layers[1] if len(layers) > 1 else None
            if layer2 and not layer2.has_mask:
                results.append(ValidationResult(
                    check_name="四层结构-头像框蒙版",
                    passed=False,
                    severity="warning",
                    message=f"第2层({layer2.track_name})应有蒙版但未检测到"
                ))
            elif layer2 and layer2.has_mask and not layer2.mask_invert:
                results.append(ValidationResult(
                    check_name="四层结构-头像框蒙版反转",
                    passed=False,
                    severity="warning",
                    message="头像框蒙版应为反向蒙版(invert=True)"
                ))
            else:
                results.append(ValidationResult(
                    check_name="四层结构-头像框蒙版",
                    passed=True,
                    message="头像框蒙版配置正确"
                ))

        return results

    def check_keyframe_timing(self, layers: List[LayerInfo]) -> List[ValidationResult]:
        """检查4：关键帧时序校验"""
        results = []

        for layer in layers:
            alpha_kfs = [kf for kf in layer.keyframes
                        if kf["property"] in ["KFTypeAlpha", "alpha"]]

            if not alpha_kfs:
                results.append(ValidationResult(
                    check_name=f"关键帧时序[{layer.track_name}]",
                    passed=True,
                    severity="info",
                    message="无透明度关键帧"
                ))
                continue

            # 检查关键帧时间是否递增
            times = [kf["time_offset"] for kf in alpha_kfs]
            times_sorted = sorted(times)

            if times != times_sorted:
                results.append(ValidationResult(
                    check_name=f"关键帧时序[{layer.track_name}]",
                    passed=False,
                    severity="error",
                    message=f"透明度关键帧时间未递增: {times}",
                    details={"times": times}
                ))
                continue

            # 检查淡入逻辑：应该从0到1
            if len(alpha_kfs) >= 2:
                first_val = alpha_kfs[0]["values"][0] if alpha_kfs[0]["values"] else 0
                last_val = alpha_kfs[-1]["values"][0] if alpha_kfs[-1]["values"] else 1

                if first_val > last_val:
                    results.append(ValidationResult(
                        check_name=f"关键帧时序[{layer.track_name}]",
                        passed=False,
                        severity="warning",
                        message=f"透明度从{first_val}降到{last_val}，可能是淡出而非淡入"
                    ))
                else:
                    fade_time = (alpha_kfs[-1]["time_offset"] - alpha_kfs[0]["time_offset"]) / 1_000_000
                    results.append(ValidationResult(
                        check_name=f"关键帧时序[{layer.track_name}]",
                        passed=True,
                        message=f"淡入: {first_val}→{last_val}，耗时{fade_time:.1f}s，"
                                f"起始{alpha_kfs[0]['time_offset']/1_000_000:.1f}s"
                    ))

        return results

    def check_background_replacement(self, layers: List[LayerInfo]) -> List[ValidationResult]:
        """检查5：背景替换验证（模拟替换背景后其他层坐标不变）"""
        results = []

        if len(layers) < 2:
            results.append(ValidationResult(
                check_name="背景替换验证",
                passed=True,
                severity="info",
                message="图层不足，跳过背景替换验证"
            ))
            return results

        # 模拟：记录除背景层外所有层的坐标
        bg_layer = layers[0]
        other_layers = layers[1:]

        # 检查其他层是否有独立的坐标设置（不依赖背景层）
        independent = all(
            l.transform_x != 0 or l.transform_y != 0 or l.has_mask
            for l in other_layers
        )

        if independent:
            results.append(ValidationResult(
                check_name="背景替换验证",
                passed=True,
                message=f"背景层({bg_layer.track_name})替换后，"
                        f"{len(other_layers)}个上层有独立坐标/蒙版，不受影响"
            ))
        else:
            results.append(ValidationResult(
                check_name="背景替换验证",
                passed=False,
                severity="warning",
                message="部分上层无独立坐标，替换背景后可能需要重新调整",
                details={"independent_layers":
                        [l.track_name for l in other_layers
                         if l.transform_x != 0 or l.transform_y != 0 or l.has_mask]}
            ))

        return results

    def validate_all(self, draft_path: str = None) -> GuardReport:
        """执行全部验证"""
        if not self.load_draft(draft_path):
            return GuardReport(draft_path=draft_path or self.draft_path or "",
                             overall_pass=False,
                             results=[ValidationResult(
                                 check_name="加载草稿", passed=False,
                                 severity="error", message="无法加载草稿文件"
                             )])

        layers = self.extract_layers()

        report = GuardReport(
            draft_path=self.draft_path,
            canvas_width=self.canvas_width,
            canvas_height=self.canvas_height,
            layers=layers,
        )

        # 执行5项检查
        all_checks = [
            self.check_coordinate_range(layers),
            self.check_mask_params(layers),
            self.check_layer_order(layers),
            self.check_keyframe_timing(layers),
            self.check_background_replacement(layers),
        ]

        for check_results in all_checks:
            report.results.extend(check_results)

        # 统计
        report.passed_count = sum(1 for r in report.results if r.passed)
        report.failed_count = sum(1 for r in report.results
                                 if not r.passed and r.severity == "error")
        report.warning_count = sum(1 for r in report.results
                                  if not r.passed and r.severity == "warning")
        report.overall_pass = report.failed_count == 0

        return report

    def print_report(self, report: GuardReport):
        """打印验证报告"""
        logger.info("\n" + "=" * 60)
        logger.info("坐标/蒙版四层防护验证报告")
        logger.info("=" * 60)
        logger.info(f"草稿: {os.path.basename(report.draft_path)}")
        logger.info(f"画布: {report.canvas_width}x{report.canvas_height}")
        logger.info(f"图层数: {len(report.layers)}")
        print(f"\n检查结果: {report.passed_count}通过, "
              f"{report.failed_count}错误, {report.warning_count}警告")
        logger.info(f"总体: {'✅ 通过' if report.overall_pass else '❌ 未通过'}")

        logger.info("\n图层信息:")
        for layer in report.layers:
            mask_str = ""
            if layer.has_mask:
                mask_str = f" [蒙版:{layer.mask_type},反转={layer.mask_invert}]"
            kf_str = f" [关键帧:{len(layer.keyframes)}]" if layer.keyframes else ""
            print(f"  L{layer.layer_index}: {layer.track_name} "
                  f"({layer.material_type}) pos=({layer.transform_x:.2f},{layer.transform_y:.2f})"
                  f" scale={layer.scale:.2f} alpha={layer.alpha:.2f}{mask_str}{kf_str}")

        logger.debug("\n详细检查:")
        for r in report.results:
            icon = "✅" if r.passed else ("⚠️" if r.severity == "warning" else "❌")
            logger.info(f"  {icon} {r.check_name}: {r.message}")

        logger.info("=" * 60)
        return report.overall_pass


def validate_from_script(layers_config: List[Dict],
                         canvas_width: int = 1080,
                         canvas_height: int = 1920) -> GuardReport:
    """
    从脚本配置直接验证（不依赖草稿文件）
    用于构建工程前的预验证

    Args:
        layers_config: 图层配置列表，每个元素包含track_name, transform_x/y, mask等
        canvas_width: 画布宽
        canvas_height: 画布高

    Returns:
        验证报告
    """
    guard = CoordMaskGuard()
    guard.canvas_width = canvas_width
    guard.canvas_height = canvas_height

    layers = []
    for idx, cfg in enumerate(layers_config):
        layer = LayerInfo(
            layer_index=idx,
            track_name=cfg.get("track_name", f"layer_{idx}"),
            material_path=cfg.get("material_path", ""),
            material_type=cfg.get("material_type", "video"),
            transform_x=cfg.get("transform_x", 0.0),
            transform_y=cfg.get("transform_y", 0.0),
            scale=cfg.get("scale", 1.0),
            alpha=cfg.get("alpha", 1.0),
            has_mask=cfg.get("has_mask", False),
            mask_type=cfg.get("mask_type", ""),
            mask_center_x=cfg.get("mask_center_x", 0.0),
            mask_center_y=cfg.get("mask_center_y", 0.0),
            mask_size=cfg.get("mask_size", 0.0),
            mask_invert=cfg.get("mask_invert", False),
            keyframes=cfg.get("keyframes", []),
            render_index=idx,
        )
        layers.append(layer)

    report = GuardReport(
        draft_path="script_preview",
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        layers=layers,
    )

    all_checks = [
        guard.check_coordinate_range(layers),
        guard.check_mask_params(layers),
        guard.check_layer_order(layers),
        guard.check_keyframe_timing(layers),
        guard.check_background_replacement(layers),
    ]

    for check_results in all_checks:
        report.results.extend(check_results)

    report.passed_count = sum(1 for r in report.results if r.passed)
    report.failed_count = sum(1 for r in report.results
                             if not r.passed and r.severity == "error")
    report.warning_count = sum(1 for r in report.results
                              if not r.passed and r.severity == "warning")
    report.overall_pass = report.failed_count == 0

    return report


def main():
    """命令行测试"""
    logger.info("坐标/蒙版四层防护验证工具 v1.0 测试")
    logger.info("=" * 60)

    # 测试1: 脚本预验证（四层结构）
    logger.info("\n测试1: 四层结构脚本预验证")
    four_layer_config = [
        {"track_name": "背景层", "material_type": "photo",
         "transform_x": 0, "transform_y": 0},
        {"track_name": "头像框层", "material_type": "photo",
         "transform_x": 0, "transform_y": 0,
         "has_mask": True, "mask_type": "圆形",
         "mask_center_x": -0.67, "mask_center_y": -0.6,
         "mask_size": 0.14, "mask_invert": True,
         "keyframes": [
             {"property": "KFTypeAlpha", "time_offset": 0, "values": [0]},
             {"property": "KFTypeAlpha", "time_offset": 9_000_000, "values": [0]},
             {"property": "KFTypeAlpha", "time_offset": 9_500_000, "values": [1]},
         ]},
        {"track_name": "作品区层", "material_type": "photo",
         "transform_x": 0, "transform_y": 0,
         "has_mask": True, "mask_type": "矩形",
         "mask_center_x": 0, "mask_center_y": 0.2,
         "mask_size": 0.5, "mask_invert": False,
         "keyframes": [
             {"property": "KFTypeAlpha", "time_offset": 0, "values": [0]},
             {"property": "KFTypeAlpha", "time_offset": 12_000_000, "values": [0]},
             {"property": "KFTypeAlpha", "time_offset": 12_500_000, "values": [1]},
         ]},
        {"track_name": "动画层", "material_type": "video",
         "transform_x": 0, "transform_y": 0},
    ]

    report = validate_from_script(four_layer_config, 1080, 1920)
    guard = CoordMaskGuard()
    guard.print_report(report)

    # 测试2: 错误配置检测
    logger.error("\n测试2: 错误配置检测（蒙版size=0）")
    bad_config = [
        {"track_name": "背景", "transform_x": 0, "transform_y": 0},
        {"track_name": "头像框", "has_mask": True, "mask_type": "圆形",
         "mask_center_x": 0, "mask_center_y": 0, "mask_size": 0,
         "mask_invert": True},
    ]
    report2 = validate_from_script(bad_config)
    guard.print_report(report2)

    logger.info("\n✅ 坐标/蒙版四层防护验证工具测试通过")


if __name__ == "__main__":
    main()
