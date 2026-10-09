"""
视频生成能力集成模块
- 视频生成参数管理
- 视频生成质量门
- 视频生成与剪映工程集成
- 批量视频生成
"""

import os
import sys
import logging
import json
import subprocess
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 路径配置
SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills"
COMFYUI_SKILL = os.path.join(SKILL_ROOT, "comfyui-controls-skill", "scripts")
JIANYING_SKILL = os.path.join(SKILL_ROOT, "jianying-editor", "scripts")

sys.path.insert(0, COMFYUI_SKILL)
sys.path.insert(0, JIANYING_SKILL)

FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"
COMFYUI_URL = "http://127.0.0.1:8188"


@dataclass
class VideoGenConfig:
    """视频生成配置"""
    model: str = "ltx-2.5"  # ltx-2.5 / hunyuan-i2v
    mode: str = "t2v"  # t2v / i2v
    prompt: str = ""
    negative_prompt: str = ""
    image_path: str = ""  # i2v模式使用
    width: int = 768
    height: int = 512
    fps: int = 24
    duration: int = 48  # 帧数
    motion_strength: float = 0.5  # 0.0-1.0
    seed: int = -1
    steps: int = 30
    cfg: float = 7.0


@dataclass
class VideoGenResult:
    """视频生成结果"""
    success: bool = False
    output_path: str = ""
    width: int = 0
    height: int = 0
    fps: float = 0.0
    duration: float = 0.0
    file_size: int = 0
    codec: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class VideoGenerationIntegrator:
    """视频生成集成器"""

    # 支持的模型
    SUPPORTED_MODELS = {
        "ltx-2.5": {
            "name": "LTX-2.5",
            "modes": ["t2v", "i2v"],
            "max_resolution": (1024, 1024),
            "max_frames": 121,
            "description": "LTX-2.5文生视频/图生视频",
        },
        "hunyuan-i2v": {
            "name": "混元I2V",
            "modes": ["i2v"],
            "max_resolution": (1280, 720),
            "max_frames": 129,
            "description": "混元视频图生视频",
        },
        "minimax-h3": {
            "name": "MiniMax H3",
            "modes": ["t2v", "i2v", "fl2v"],
            "max_resolution": (2560, 1440),
            "max_frames": 361,
            "description": "MiniMax H3全模态视频生成，原生2K/24fps/立体声音频",
            "native_audio": True,
            "timeline_prompt": True,
        },
    }

    def __init__(self, comfyui_url: str = None):
        self.comfyui_url = comfyui_url or COMFYUI_URL
        self._comfy_client = None

    def _get_comfy_client(self):
        """获取ComfyUI客户端"""
        if self._comfy_client is None:
            try:
                from comfy_client import ComfyClient
                self._comfy_client = ComfyClient(self.comfyui_url)
            except Exception as e:
                logger.error(f"ComfyUI客户端初始化失败: {e}")
        return self._comfy_client

    def validate_config(self, config: VideoGenConfig) -> Tuple[bool, List[str]]:
        """验证视频生成配置

        Args:
            config: 视频生成配置

        Returns:
            (是否有效, 问题列表)
        """
        issues = []

        # 检查模型
        if config.model not in self.SUPPORTED_MODELS:
            issues.append(f"不支持的模型: {config.model}，支持: {list(self.SUPPORTED_MODELS.keys())}")

        model_info = self.SUPPORTED_MODELS.get(config.model, {})

        # 检查模式
        if config.mode not in model_info.get("modes", []):
            issues.append(f"模型{config.model}不支持模式{config.mode}，支持: {model_info.get('modes', [])}")

        # i2v模式需要图片
        if config.mode == "i2v" and not config.image_path:
            issues.append("i2v模式必须提供image_path")
        elif config.mode == "i2v" and not os.path.exists(config.image_path):
            issues.append(f"图片不存在: {config.image_path}")

        # 检查分辨率
        max_w, max_h = model_info.get("max_resolution", (1024, 1024))
        if config.width > max_w or config.height > max_h:
            issues.append(f"分辨率超出限制: {config.width}x{config.height}，最大: {max_w}x{max_h}")

        # 检查帧数
        max_frames = model_info.get("max_frames", 121)
        if config.duration > max_frames:
            issues.append(f"帧数超出限制: {config.duration}，最大: {max_frames}")

        # 检查运动强度
        if config.motion_strength < 0 or config.motion_strength > 1:
            issues.append(f"运动强度超出范围: {config.motion_strength}，应为0.0-1.0")

        return len(issues) == 0, issues

    def generate_video(
        self,
        config: VideoGenConfig,
        output_dir: str,
        output_name: str = None,
    ) -> VideoGenResult:
        """生成视频

        Args:
            config: 视频生成配置
            output_dir: 输出目录
            output_name: 输出文件名

        Returns:
            视频生成结果
        """
        result = VideoGenResult()

        # 验证配置
        valid, issues = self.validate_config(config)
        if not valid:
            result.errors = issues
            return result

        # 构建工作流
        try:
            # MiniMax H3使用专用runner
            if config.model == "minimax-h3":
                output_path = self._generate_with_h3(config, output_dir, output_name)
                if output_path and os.path.exists(output_path):
                    result.success = True
                    result.output_path = output_path
                    self._fill_video_metadata(result, output_path)
                else:
                    result.errors.append("MiniMax H3生成失败")
                return result

            from workflow_templates import WorkflowTemplateLibrary
            library = WorkflowTemplateLibrary()

            if config.mode == "t2v":
                workflow = library.build_video_generation_workflow({
                    "model": config.model,
                    "prompt": config.prompt,
                    "negative_prompt": config.negative_prompt,
                    "width": config.width,
                    "height": config.height,
                    "frames": config.duration,
                    "fps": config.fps,
                    "steps": config.steps,
                    "cfg": config.cfg,
                    "seed": config.seed,
                })
            else:  # i2v
                workflow = library.build_image_to_video_workflow({
                    "model": config.model,
                    "image_path": config.image_path,
                    "prompt": config.prompt,
                    "negative_prompt": config.negative_prompt,
                    "width": config.width,
                    "height": config.height,
                    "frames": config.duration,
                    "fps": config.fps,
                    "motion_strength": config.motion_strength,
                    "steps": config.steps,
                    "cfg": config.cfg,
                    "seed": config.seed,
                })

            logger.info(f"工作流构建成功: {config.model} {config.mode}")

        except Exception as e:
            result.errors.append(f"工作流构建失败: {e}")
            return result

        # 执行工作流
        client = self._get_comfy_client()
        if not client:
            result.errors.append("ComfyUI客户端不可用")
            return result

        try:
            os.makedirs(output_dir, exist_ok=True)
            output_name = output_name or f"video_{config.model}_{config.mode}_{int(config.duration)}f.mp4"
            output_path = os.path.join(output_dir, output_name)

            # 执行生成
            generated = client.execute_workflow(
                workflow,
                output_dir=output_dir,
                timeout=600,
            )

            if generated and os.path.exists(generated):
                result.output_path = generated
                result.success = True
                logger.info(f"视频生成成功: {generated}")
            else:
                result.errors.append("视频生成失败，未找到输出文件")

        except Exception as e:
            result.errors.append(f"视频生成执行失败: {e}")
            return result

        # 质量检测
        if result.success:
            self._quality_check(result)

        return result

    def _generate_with_h3(self, config: VideoGenConfig, output_dir: str,
                           output_name: str = None) -> Optional[str]:
        """使用MiniMax H3生成视频

        Args:
            config: 视频生成配置
            output_dir: 输出目录
            output_name: 输出文件名

        Returns:
            输出视频路径，失败返回None
        """
        try:
            from minimax_h3_runner import MiniMaxH3Runner, PRESETS

            # 选择预设
            preset = "turbo_768p"
            if config.width >= 2000 or config.height >= 1400:
                preset = "turbo_2k"
            if config.steps > 10:
                preset = "standard_768p" if config.width < 2000 else "quality_2k"

            runner = MiniMaxH3Runner(
                server_addr=self.comfyui_url.replace("http://", ""),
                output_dir=output_dir,
                preset=preset,
            )

            os.makedirs(output_dir, exist_ok=True)
            output_name = output_name or f"h3_{config.mode}_{config.duration}f.mp4"

            if config.mode == "t2v":
                result = runner.text_to_video(
                    prompt=config.prompt,
                    width=config.width,
                    height=config.height,
                    frames=config.duration,
                )
            elif config.mode == "i2v":
                result = runner.image_to_video(
                    prompt=config.prompt,
                    image_path=config.image_path,
                    width=config.width,
                    height=config.height,
                    frames=config.duration,
                )
            elif config.mode == "fl2v":
                # fl2v模式：image_path作为首帧，需要额外指定尾帧
                # 通过negative_prompt字段传递尾帧路径（临时方案）
                last_frame = config.negative_prompt if config.negative_prompt else config.image_path
                result = runner.first_last_to_video(
                    prompt=config.prompt,
                    first_frame_path=config.image_path,
                    last_frame_path=last_frame,
                    width=config.width,
                    height=config.height,
                    frames=config.duration,
                )
            else:
                logger.error(f"H3不支持模式: {config.mode}")
                return None

            if result and os.path.exists(result):
                # 重命名为指定文件名
                final_path = os.path.join(output_dir, output_name)
                if result != final_path:
                    import shutil
                    shutil.move(result, final_path)
                return final_path
            return None

        except Exception as e:
            logger.error(f"H3生成失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _fill_video_metadata(self, result: VideoGenResult, video_path: str):
        """填充视频元数据（分辨率/帧率/时长/编码）"""
        try:
            result.file_size = os.path.getsize(video_path)
            proc = subprocess.run(
                [FFPROBE, "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", video_path],
                capture_output=True, text=True, timeout=30
            )
            info = json.loads(proc.stdout)
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    result.width = stream.get("width", 0)
                    result.height = stream.get("height", 0)
                    result.codec = stream.get("codec_name", "")
                    fps_str = stream.get("r_frame_rate", "0/1")
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        result.fps = float(num) / float(den) if float(den) != 0 else 0
            fmt = info.get("format", {})
            result.duration = float(fmt.get("duration", 0))
        except Exception as e:
            result.warnings.append(f"元数据读取失败: {e}")

    def _quality_check(self, result: VideoGenResult):
        """视频质量检测"""
        if not os.path.exists(result.output_path):
            result.errors.append("输出文件不存在")
            result.success = False
            return

        result.file_size = os.path.getsize(result.output_path)

        # 文件大小检查
        if result.file_size < 10240:  # 小于10KB
            result.errors.append("文件过小，可能生成失败")
            result.success = False
            return

        # ffprobe检测
        try:
            proc = subprocess.run(
                [FFPROBE, "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", result.output_path],
                capture_output=True, text=True, timeout=30
            )
            info = json.loads(proc.stdout)

            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    result.width = stream.get("width", 0)
                    result.height = stream.get("height", 0)
                    result.codec = stream.get("codec_name", "")

                    fps_str = stream.get("r_frame_rate", "0/1")
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        result.fps = float(num) / float(den) if float(den) != 0 else 0

            fmt = info.get("format", {})
            result.duration = float(fmt.get("duration", 0))

        except Exception as e:
            result.warnings.append(f"质量检测失败: {e}")

        # 时长检查
        if result.duration < 0.5:
            result.warnings.append("视频时长过短")

    def batch_generate(
        self,
        configs: List[VideoGenConfig],
        output_dir: str,
    ) -> List[VideoGenResult]:
        """批量生成视频

        Args:
            configs: 配置列表
            output_dir: 输出目录

        Returns:
            结果列表
        """
        results = []
        for i, config in enumerate(configs):
            logger.info(f"批量生成 [{i+1}/{len(configs)}]: {config.model} {config.mode}")
            result = self.generate_video(
                config,
                output_dir,
                output_name=f"batch_{i:03d}.mp4",
            )
            results.append(result)

        success = sum(1 for r in results if r.success)
        logger.info(f"批量生成完成: {success}/{len(configs)}成功")
        return results

    def import_to_jianying(
        self,
        video_path: str,
        project,
        start_time: str = "0s",
        duration: str = None,
        track_name: str = "VideoTrack",
    ) -> bool:
        """将生成的视频导入剪映工程

        Args:
            video_path: 视频路径
            project: JyProject实例
            start_time: 起始时间
            duration: 时长
            track_name: 轨道名

        Returns:
            True成功，False失败
        """
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return False

        try:
            seg = project.add_media_safe(
                video_path,
                start_time,
                duration,
                track_name,
            )
            if seg:
                logger.info(f"视频已导入剪映: {os.path.basename(video_path)}")
                return True
            else:
                logger.error("视频导入剪映失败")
                return False
        except Exception as e:
            logger.error(f"视频导入剪映异常: {e}")
            return False

    def list_models(self) -> List[Dict[str, Any]]:
        """列出支持的模型"""
        return [
            {
                "id": model_id,
                "name": info["name"],
                "modes": info["modes"],
                "max_resolution": info["max_resolution"],
                "max_frames": info["max_frames"],
                "description": info["description"],
            }
            for model_id, info in self.SUPPORTED_MODELS.items()
        ]


def main():
    """测试视频生成集成器"""
    integrator = VideoGenerationIntegrator()

    print("=== 支持的视频生成模型 ===")
    for model in integrator.list_models():
        print(f"  - {model['id']}: {model['name']} ({model['description']})")
        print(f"    模式: {model['modes']}, 最大分辨率: {model['max_resolution']}, 最大帧数: {model['max_frames']}")

    # 测试配置验证
    print("\n=== 配置验证测试 ===")
    config = VideoGenConfig(
        model="ltx-2.5",
        mode="t2v",
        prompt="a cat walking in the garden",
        width=768,
        height=512,
        duration=48,
        fps=24,
    )
    valid, issues = integrator.validate_config(config)
    print(f"配置有效: {valid}")
    if issues:
        print(f"问题: {issues}")

    print("\n视频生成集成器就绪")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
