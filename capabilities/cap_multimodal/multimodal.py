"""
多模态交互接口 v1.0 (P5-5)
支持文字+语音+图片+参考视频多模态输入，统一交互接口

核心功能：
1. 多模态输入统一接口：文字/语音/图片/视频统一处理
2. 输入解析：自动识别输入类型并提取关键信息
3. 参考素材管理：管理参考图片/参考视频
4. 多模态融合：将多种输入融合为统一的生成指令
5. 输入验证：验证输入有效性和完整性

支持的输入类型：
- text: 自然语言文字指令
- voice: 语音输入（需先转文字）
- image: 参考图片（风格参考/内容参考/构图参考）
- video: 参考视频（节奏参考/运镜参考/风格参考）
- mixed: 混合输入（多种类型组合）

使用方法：
    from multimodal import MultimodalInterface
    interface = MultimodalInterface()
    result = interface.process_input(
        text="做一个30秒的探店视频",
        images=["style_ref.jpg"],
        video="reference.mp4",
    )
    print(result)
"""
import os
import sys
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class MultimodalInput:
    """多模态输入"""
    input_id: str = ""
    timestamp: str = ""
    # 文字输入
    text: str = ""
    text_type: str = "command"  # command/description/keyword/script
    # 语音输入
    voice_file: str = ""
    voice_transcript: str = ""
    # 图片输入
    images: List[str] = field(default_factory=list)
    image_roles: Dict[str, str] = field(default_factory=dict)  # 图片路径→角色(style/content/composition)
    # 视频输入
    video: str = ""
    video_role: str = "reference"  # reference/rhythm/camera/style
    # 其他参数
    parameters: Dict[str, Any] = field(default_factory=dict)
    # 元数据
    input_mode: str = "mixed"  # text/voice/image/video/mixed


@dataclass
class ProcessedInput:
    """处理后的输入"""
    original: MultimodalInput = field(default_factory=MultimodalInput)
    # 提取的生成参数
    video_type: str = "exploration"
    topic: str = ""
    duration: float = 30.0
    style: str = "cinematic"
    hook_effect: str = "wipe"
    aspect_ratio: str = "9:16"
    keywords: List[str] = field(default_factory=list)
    # 参考素材
    reference_images: List[str] = field(default_factory=list)
    reference_video: str = ""
    # 分析结果
    input_types_detected: List[str] = field(default_factory=list)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    # 生成指令（可直接传给pipeline）
    generation_command: Dict[str, Any] = field(default_factory=dict)


class MultimodalInterface:
    """多模态交互接口"""

    def __init__(self, skill_root: str = None):
        self.skill_root = skill_root or r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
        self._nlu_engine = None

    def _get_nlu_engine(self):
        """懒加载NLU引擎"""
        if self._nlu_engine is None:
            sys.path.insert(0, self.skill_root)
            sys.path.insert(0, os.path.join(self.skill_root, "capabilities"))
            try:
                from cap_natural_language import NaturalLanguageEngine
                self._nlu_engine = NaturalLanguageEngine()
            except Exception:
                self._nlu_engine = None
        return self._nlu_engine

    # ==================== 主处理入口 ====================

    def process_input(self, text: str = "", voice_file: str = "",
                      images: List[str] = None, video: str = "",
                      parameters: Dict[str, Any] = None) -> ProcessedInput:
        """
        处理多模态输入

        Args:
            text: 文字输入
            voice_file: 语音文件路径
            images: 图片路径列表
            video: 视频路径
            parameters: 额外参数

        Returns:
            ProcessedInput 处理后的输入
        """
        # 1. 构建原始输入
        original = MultimodalInput(
            input_id=f"input_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            text=text,
            voice_file=voice_file,
            images=images or [],
            video=video,
            parameters=parameters or {},
        )

        # 2. 检测输入类型
        original.input_mode = self._detect_input_mode(original)

        # 3. 处理结果
        result = ProcessedInput(original=original)
        result.input_types_detected = self._detect_input_types(original)

        # 4. 文字处理（如果有文字或语音转文字）
        combined_text = text
        if voice_file and not combined_text:
            # 语音需要先转文字（这里只记录，实际转写由外部完成）
            result.warnings.append("语音文件需先转文字，当前使用空文字")
            combined_text = ""

        if combined_text:
            result = self._process_text(result, combined_text)

        # 5. 图片处理
        if images:
            result = self._process_images(result, images)

        # 6. 视频处理
        if video:
            result = self._process_video(result, video)

        # 7. 应用额外参数（优先级最高）
        if parameters:
            result = self._apply_parameters(result, parameters)

        # 8. 生成最终指令
        result.generation_command = self._build_generation_command(result)

        # 9. 计算置信度
        result.confidence = self._calc_confidence(result)

        # 10. 生成建议
        result.suggestions = self._generate_suggestions(result)

        return asdict(result)

    # ==================== 输入检测 ====================

    def _detect_input_mode(self, inp: MultimodalInput) -> str:
        """检测输入模式"""
        types = []
        if inp.text:
            types.append("text")
        if inp.voice_file:
            types.append("voice")
        if inp.images:
            types.append("image")
        if inp.video:
            types.append("video")

        if len(types) == 0:
            return "none"
        elif len(types) == 1:
            return types[0]
        else:
            return "mixed"

    def _detect_input_types(self, inp: MultimodalInput) -> List[str]:
        """检测所有输入类型"""
        types = []
        if inp.text:
            types.append("text")
        if inp.voice_file:
            types.append("voice")
        if inp.images:
            types.append(f"image({len(inp.images)})")
        if inp.video:
            types.append("video")
        return types

    # ==================== 各模态处理 ====================

    def _process_text(self, result: ProcessedInput, text: str) -> ProcessedInput:
        """处理文字输入"""
        nlu = self._get_nlu_engine()

        if nlu:
            # 使用NLU引擎解析（返回dict）
            parsed = nlu.parse(text)
            result.video_type = parsed.get("video_type", result.video_type)
            result.topic = parsed.get("topic", result.topic)
            result.duration = parsed.get("duration", result.duration)
            result.style = parsed.get("style", result.style)
            result.hook_effect = parsed.get("hook_effect", result.hook_effect)
            result.keywords = parsed.get("keywords", result.keywords)
            result.confidence += parsed.get("confidence", 0) * 0.5
        else:
            # 简单关键词提取
            result.topic = text[:50]
            result.confidence += 0.2

        return result

    def _process_images(self, result: ProcessedInput, images: List[str]) -> ProcessedInput:
        """处理图片输入"""
        valid_images = []
        for img in images:
            if os.path.exists(img):
                valid_images.append(img)
            else:
                result.warnings.append(f"图片不存在: {img}")

        result.reference_images = valid_images

        # 根据图片数量推断
        if len(valid_images) >= 3:
            result.suggestions.append("检测到多张参考图，建议用于分镜参考")
        elif len(valid_images) == 1:
            result.suggestions.append("检测到单张参考图，建议用于风格/构图参考")

        # 图片可能影响风格推断
        if valid_images and not result.original.text:
            result.warnings.append("仅有图片输入，主题需从图片分析或手动指定")

        return result

    def _process_video(self, result: ProcessedInput, video: str) -> ProcessedInput:
        """处理视频输入"""
        if os.path.exists(video):
            result.reference_video = video
            result.suggestions.append("检测到参考视频，可用于节奏/运镜/风格参考")
        else:
            result.warnings.append(f"视频不存在: {video}")

        return result

    def _apply_parameters(self, result: ProcessedInput,
                           parameters: Dict[str, Any]) -> ProcessedInput:
        """应用额外参数（优先级最高）"""
        param_map = {
            "video_type": "video_type",
            "type": "video_type",
            "topic": "topic",
            "duration": "duration",
            "style": "style",
            "hook_effect": "hook_effect",
            "effect": "hook_effect",
            "aspect_ratio": "aspect_ratio",
            "ratio": "aspect_ratio",
            "keywords": "keywords",
        }

        for param_key, result_key in param_map.items():
            if param_key in parameters:
                setattr(result, result_key, parameters[param_key])

        return asdict(result)

    # ==================== 生成指令构建 ====================

    def _build_generation_command(self, result: ProcessedInput) -> Dict[str, Any]:
        """构建生成指令（可直接传给pipeline）"""
        command = {
            "topic": result.topic or "未命名视频",
            "video_type": result.video_type,
            "duration": result.duration,
            "style": result.style,
            "hook_effect": result.hook_effect,
            "aspect_ratio": result.aspect_ratio,
            "keywords": result.keywords,
        }

        # 添加参考素材
        if result.reference_images:
            command["reference_images"] = result.reference_images
        if result.reference_video:
            command["reference_video"] = result.reference_video

        return command

    # ==================== 置信度和建议 ====================

    def _calc_confidence(self, result: ProcessedInput) -> float:
        """计算整体置信度"""
        confidence = 0.0

        # 文字输入贡献
        if result.original.text:
            confidence += 0.4
        # 图片输入贡献
        if result.reference_images:
            confidence += 0.2
        # 视频输入贡献
        if result.reference_video:
            confidence += 0.2
        # 主题明确性
        if result.topic:
            confidence += 0.1
        # 无警告加分
        if not result.warnings:
            confidence += 0.1

        return min(1.0, confidence)

    def _generate_suggestions(self, result: ProcessedInput) -> List[str]:
        """生成建议"""
        suggestions = list(result.suggestions)

        # 缺少主题
        if not result.topic and not result.reference_images:
            suggestions.append("💡 未检测到明确主题，建议补充文字描述或参考图")

        # 纯文字输入
        if result.original.input_mode == "text" and not result.reference_images:
            suggestions.append("💡 可添加参考图提升生成效果")

        # 多模态输入
        if result.original.input_mode == "mixed":
            suggestions.append("✅ 多模态输入已融合，生成效果更佳")

        return suggestions

    # ==================== 验证 ====================

    def validate_input(self, inp: MultimodalInput) -> Dict[str, Any]:
        """验证输入有效性"""
        issues = []
        warnings = []

        # 检查是否有任何输入
        if not inp.text and not inp.voice_file and not inp.images and not inp.video:
            issues.append("没有任何输入内容")

        # 检查文件存在性
        if inp.voice_file and not os.path.exists(inp.voice_file):
            issues.append(f"语音文件不存在: {inp.voice_file}")

        for img in inp.images:
            if not os.path.exists(img):
                warnings.append(f"图片不存在: {img}")

        if inp.video and not os.path.exists(inp.video):
            issues.append(f"视频文件不存在: {inp.video}")

        # 检查文字长度
        if inp.text and len(inp.text) > 1000:
            warnings.append("文字输入过长，可能影响解析效果")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "input_mode": inp.input_mode,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("🎛️ 多模态交互接口 v1.0")
    print("=" * 60)

    interface = MultimodalInterface()

    # 测试1：纯文字输入
    print(f"\n{'─'*60}")
    print("测试1: 纯文字输入")
    result1 = interface.process_input(text="做一个30秒的探店美食视频，主题是淮南牛肉汤")
    print(f"  输入模式: {result1.original.input_mode}")
    print(f"  视频类型: {result1.video_type}")
    print(f"  主题: {result1.topic}")
    print(f"  时长: {result1.duration}秒")
    print(f"  置信度: {result1.confidence:.0%}")

    # 测试2：文字+图片混合输入
    print(f"\n{'─'*60}")
    print("测试2: 文字+图片混合输入")
    result2 = interface.process_input(
        text="做一个产品测评视频",
        images=["nonexistent.jpg"],  # 测试不存在的图片
    )
    print(f"  输入模式: {result2.original.input_mode}")
    print(f"  检测类型: {result2.input_types_detected}")
    print(f"  警告: {result2.warnings}")
    print(f"  建议: {result2.suggestions}")

    # 测试3：带参数覆盖
    print(f"\n{'─'*60}")
    print("测试3: 带参数覆盖")
    result3 = interface.process_input(
        text="做一个vlog",
        parameters={"duration": 60, "style": "warm", "hook_effect": "subtitle_bar"},
    )
    print(f"  时长: {result3.duration}秒（参数覆盖）")
    print(f"  风格: {result3.style}（参数覆盖）")
    print(f"  特效: {result3.hook_effect}（参数覆盖）")

    # 测试4：生成指令
    print(f"\n{'─'*60}")
    print("测试4: 生成指令")
    print(f"  {json.dumps(result1.generation_command, ensure_ascii=False, indent=2)}")

    print(f"\n{'='*60}")
    print("✅ 多模态交互接口测试完成")
    print(f"{'='*60}")
