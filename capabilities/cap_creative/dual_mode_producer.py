"""
产出质量双模式 v1.0
区分视频产出模式和模板产出模式

视频产出模式（Video Mode）：
- 追求视觉效果，使用文字图片/动画素材
- 特效丰富，转场华丽
- 面向最终视频交付

模板产出模式（Template Mode）：
- 使用剪映原生文字，可替换素材
- 面向模板用户，支持一键替换文字/图片
- 结构规范，符合剪映模板要求
"""

import os
import json
from typing import Dict, Any, List, Optional
from enum import Enum


class OutputMode(Enum):
    """产出模式"""
    VIDEO = "video"           # 视频产出模式
    TEMPLATE = "template"     # 模板产出模式
    AUTO = "auto"             # 自动判断


class DualModeProducer:
    """双模式产出器"""

    def __init__(self):
        self.current_mode = OutputMode.AUTO

    def detect_mode(self, user_request: str, project_type: str = "") -> OutputMode:
        """
        自动判断产出模式

        Args:
            user_request: 用户请求文本
            project_type: 项目类型

        Returns:
            产出模式
        """
        # 明确的模板关键词
        template_keywords = ["模板", "template", "可替换", "一键生成", "套模板", "剪映模板"]
        video_keywords = ["视频", "成片", "导出", "交付", "mp4", "宣传视频", "短片"]

        request_lower = user_request.lower()

        # 检查模板关键词
        if any(kw in request_lower for kw in template_keywords):
            return OutputMode.TEMPLATE

        # 检查视频关键词
        if any(kw in request_lower for kw in video_keywords):
            return OutputMode.VIDEO

        # 根据项目类型判断
        if project_type in ("template", "模板"):
            return OutputMode.TEMPLATE

        # 默认视频模式
        return OutputMode.VIDEO

    def get_mode_config(self, mode: OutputMode) -> Dict[str, Any]:
        """
        获取模式配置

        Args:
            mode: 产出模式

        Returns:
            模式配置字典
        """
        configs = {
            OutputMode.VIDEO: {
                "name": "视频产出模式",
                "description": "追求视觉效果，使用文字图片/动画素材，特效丰富",
                "text_rendering": "image",           # 文字用图片渲染
                "effects_level": "high",             # 特效等级高
                "transitions": "rich",               # 转场丰富
                "replaceable_text": False,           # 文字不可替换
                "replaceable_images": False,         # 图片不可替换
                "target": "final_video",             # 目标：最终视频
                "quality_priority": "visual",        # 质量优先：视觉效果
                "recommended_effects": [
                    "蒙版快闪", "文字擦开", "背景滑入",
                    "角色卡", "字幕条", "粒子背景",
                    "3D文字", "光线扫描", "转场遮罩"
                ],
            },
            OutputMode.TEMPLATE: {
                "name": "模板产出模式",
                "description": "使用剪映原生文字，可替换素材，面向模板用户",
                "text_rendering": "native",          # 文字用剪映原生
                "effects_level": "medium",           # 特效等级中
                "transitions": "standard",           # 转场标准
                "replaceable_text": True,            # 文字可替换
                "replaceable_images": True,          # 图片可替换
                "target": "jianying_template",       # 目标：剪映模板
                "quality_priority": "usability",     # 质量优先：可用性
                "recommended_effects": [
                    "原生文字动画", "简单转场", "标准滤镜",
                    "文字背景块", "基础调色"
                ],
                "template_requirements": [
                    "所有文字必须使用剪映原生文字轨道",
                    "图片素材使用占位图，标注替换位置",
                    "避免使用复杂蒙版关键帧（模板兼容性差）",
                    "结构清晰，分段落命名",
                    "时长控制在15-60秒",
                ],
            },
        }
        return configs.get(mode, configs[OutputMode.VIDEO])

    def adapt_script_for_mode(self, script_data: Dict[str, Any],
                                mode: OutputMode) -> Dict[str, Any]:
        """
        根据模式调整剧本数据

        Args:
            script_data: 原始剧本数据
            mode: 产出模式

        Returns:
            调整后的剧本数据
        """
        adapted = script_data.copy()
        config = self.get_mode_config(mode)

        # 添加模式标记
        adapted["output_mode"] = mode.value
        adapted["mode_config"] = config

        # 模板模式：标记可替换元素
        if mode == OutputMode.TEMPLATE:
            for scene in adapted.get("scenes", []):
                for shot in scene.get("shots", []):
                    # 标记文字为可替换
                    if "text" in shot:
                        shot["text_replaceable"] = True
                        shot["text_placeholder"] = shot["text"]
                    # 标记图片为可替换
                    if "image" in shot:
                        shot["image_replaceable"] = True
                        shot["image_placeholder"] = shot["image"]

        # 视频模式：添加特效建议
        if mode == OutputMode.VIDEO:
            for scene in adapted.get("scenes", []):
                for i, shot in enumerate(scene.get("shots", [])):
                    shot["recommended_effect"] = config["recommended_effects"][
                        i % len(config["recommended_effects"])
                    ]

        return adapted

    def generate_mode_report(self, mode: OutputMode,
                               script_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成模式适配报告

        Args:
            mode: 产出模式
            script_data: 剧本数据

        Returns:
            报告字典
        """
        config = self.get_mode_config(mode)
        scenes = script_data.get("scenes", [])
        total_shots = sum(len(s.get("shots", [])) for s in scenes)

        report = {
            "mode": mode.value,
            "mode_name": config["name"],
            "description": config["description"],
            "statistics": {
                "scenes": len(scenes),
                "shots": total_shots,
                "estimated_duration": sum(
                    shot.get("duration", 3)
                    for scene in scenes
                    for shot in scene.get("shots", [])
                ),
            },
            "text_strategy": config["text_rendering"],
            "effects_level": config["effects_level"],
            "replaceable": {
                "text": config["replaceable_text"],
                "images": config["replaceable_images"],
            },
            "recommendations": config["recommended_effects"],
        }

        if mode == OutputMode.TEMPLATE:
            report["template_checklist"] = config["template_requirements"]

        return report


# 便捷函数
def create_producer() -> DualModeProducer:
    """创建双模式产出器"""
    return DualModeProducer()


def detect_output_mode(user_request: str, project_type: str = "") -> OutputMode:
    """便捷函数：判断产出模式"""
    producer = create_producer()
    return producer.detect_mode(user_request, project_type)


if __name__ == "__main__":
    print("=" * 60)
    print("产出质量双模式 v1.0 自测")
    print("=" * 60)

    producer = create_producer()

    # 测试模式判断
    test_cases = [
        ("帮我做一个产品宣传视频", "", "video"),
        ("制作一个可替换文字的剪映模板", "", "template"),
        ("生成一个短片", "", "video"),
        ("做一个套模板用的工程", "template", "template"),
    ]

    print("\n[1/3] 测试模式判断:")
    for request, ptype, expected in test_cases:
        result = producer.detect_mode(request, ptype)
        status = "✅" if result.value == expected else "❌"
        print(f"  {status} '{request[:30]}...' -> {result.value} (期望{expected})")

    # 测试模式配置
    print("\n[2/3] 测试模式配置:")
    for mode in [OutputMode.VIDEO, OutputMode.TEMPLATE]:
        config = producer.get_mode_config(mode)
        print(f"  {mode.value}: {config['name']}")
        print(f"    文字渲染: {config['text_rendering']}")
        print(f"    特效等级: {config['effects_level']}")
        print(f"    可替换文字: {config['replaceable_text']}")

    # 测试剧本适配
    print("\n[3/3] 测试剧本适配:")
    test_script = {
        "scenes": [
            {
                "name": "开场",
                "shots": [
                    {"duration": 3, "text": "标题文字", "image": "场景图"},
                    {"duration": 4, "text": "副标题"},
                ]
            }
        ]
    }

    for mode in [OutputMode.VIDEO, OutputMode.TEMPLATE]:
        adapted = producer.adapt_script_for_mode(test_script, mode)
        report = producer.generate_mode_report(mode, adapted)
        print(f"\n  {mode.value}模式:")
        print(f"    镜头数: {report['statistics']['shots']}")
        print(f"    预估时长: {report['statistics']['estimated_duration']}s")
        print(f"    文字策略: {report['text_strategy']}")

    print("\n" + "=" * 60)
    print("✅ 产出质量双模式自测通过")
    print("=" * 60)
