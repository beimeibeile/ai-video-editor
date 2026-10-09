#!/usr/bin/env python3
"""
Remotion 动画素材执行器
集成 Remotion-controls-skill 的 PNG序列→ProRes 4444 管线
为 director_engine / central_orchestrator 提供标准动画素材生成接口

用法:
    from remotion_executor import RemotionExecutor
    exe = RemotionExecutor()
    result = exe.render_animation(
        composition="AnimationTemplate",
        output="out/animation.mov",
        config={"layers": [...]},
        fps=30, width=1080, height=1920,
    )
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
logger = logging.getLogger(__name__)

# 路径配置
try:
    from paths import PATHS
    REMOTION_SKILL = PATHS.get("remotion_skill_root", "")
except ImportError:
    REMOTION_SKILL = os.environ.get(
        "REMOTION_SKILL_ROOT",
        r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default"
        r"\.doubao\agent_mode\workspace\.user_skills\remotion-controls-skill"
    )

REMOTION_CONTROLS = os.path.join(REMOTION_SKILL, "remotion_controls.py")
PYTHON = sys.executable


class RemotionExecutor:
    """Remotion 动画素材执行器"""

    def __init__(self, skill_root: Optional[str] = None):
        self.skill_root = Path(skill_root or REMOTION_SKILL)
        self.controls_script = self.skill_root / "remotion_controls.py"
        self._available = None

    @property
    def available(self) -> bool:
        """检查Remotion环境是否可用"""
        if self._available is not None:
            return self._available
        if not self.controls_script.exists():
            self._available = False
            return False
        # 检查node_modules
        node_modules = self.skill_root / "remotion-project" / "node_modules"
        self._available = node_modules.exists()
        return self._available

    def render_animation(
        self,
        composition: str,
        output: str,
        *,
        config: Optional[Dict[str, Any]] = None,
        config_file: Optional[str] = None,
        fps: int = 30,
        width: int = 1080,
        height: int = 1920,
        frames: Optional[str] = None,
        output_format: str = "prores",
        verify_alpha: bool = True,
    ) -> Dict[str, Any]:
        """
        渲染带透明背景的动画素材（PNG序列→ProRes 4444）

        Args:
            composition: Composition名称
            output: 输出文件路径(.mov)
            config: 动画配置字典（写入animation-config.ts）
            config_file: 动画配置JSON文件路径（优先于config）
            fps: 帧率
            width: 宽度
            height: 高度
            frames: 渲染帧范围，如 "0-150"
            output_format: 输出格式 (prores/apng)
            verify_alpha: 是否验证Alpha通道

        Returns:
            渲染结果字典
        """
        if not self.available:
            return {
                "success": False,
                "error": "Remotion环境不可用",
                "skill_root": str(self.skill_root),
            }

        cmd = [
            PYTHON, str(self.controls_script),
            "render-transparent",
            "--comp", composition,
            "--output", output,
            "--fps", str(fps),
            "--width", str(width),
            "--height", str(height),
            "--format", output_format,
        ]

        if frames:
            cmd.extend(["--frames", frames])

        if config_file:
            cmd.extend(["--props-file", config_file])
        elif config:
            # 写入临时配置文件
            import tempfile
            tmp_cfg = Path(tempfile.mkstemp(suffix=".json", prefix="remotion_cfg_")[1])
            tmp_cfg.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            cmd.extend(["--props-file", str(tmp_cfg)])

        logger.info(f"[Remotion] 渲染: {composition} -> {output}")
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

        # 解析输出中的JSON结果
        output_path = Path(output)
        success = output_path.exists()

        result_data = {
            "success": success,
            "output": str(output_path.absolute()) if success else None,
            "composition": composition,
            "format": output_format,
            "file_size_mb": round(output_path.stat().st_size / 1024 / 1024, 2) if success else 0,
        }

        # 验证Alpha通道
        if success and verify_alpha:
            alpha = self.check_alpha(output)
            result_data["alpha_channel"] = alpha.get("has_alpha", False)
            result_data["pix_fmt"] = alpha.get("pix_fmt", "")
            if not alpha.get("has_alpha"):
                result_data["warning"] = "Alpha通道丢失！剪映中背景将不透明"
                logger.info(f"  ⚠️ Alpha通道丢失: {alpha.get('pix_fmt')}")
            else:
                logger.info(f"  ✅ Alpha通道正常: {alpha.get('pix_fmt')}")

        if not success:
            result_data["error"] = "渲染失败"
            result_data["stderr"] = result.stderr[-500:] if result.stderr else ""
            logger.info(f"  ❌ 渲染失败: {result.stderr[-200:]}")

        # 清理临时配置文件
        if config and not config_file:
            try:
                tmp_cfg.unlink(missing_ok=True)
            except Exception:
                pass

        return result_data

    def render_from_json(
        self,
        config_file: str,
        output: str,
        *,
        composition: Optional[str] = None,
        fps: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        从动画配置JSON文件渲染

        配置文件格式:
        {
          "composition": "AnimationTemplate",
          "fps": 30,
          "width": 1080,
          "height": 1920,
          "duration": 20,
          "layers": [...]
        }
        """
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        return self.render_animation(
            composition=composition or cfg.get("composition", "AnimationTemplate"),
            output=output,
            config=cfg,
            fps=fps or cfg.get("fps", 30),
            width=width or cfg.get("width", 1080),
            height=height or cfg.get("height", 1920),
        )

    def check_alpha(self, video_path: str) -> Dict[str, Any]:
        """检查视频Alpha通道"""
        cmd = [
            PYTHON, str(self.controls_script),
            "check-alpha", "--video", video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"has_alpha": False, "error": "解析失败"}

    def list_compositions(self) -> List[Dict[str, Any]]:
        """列出可用的Composition"""
        cmd = [PYTHON, str(self.controls_script), "list"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        # 输出可能包含进度信息，尝试解析JSON
        try:
            # 找到最后一个{开始的JSON
            idx = result.stdout.rfind("{")
            if idx >= 0:
                data = json.loads(result.stdout[idx:])
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, ValueError):
            pass
        return []


# 便捷函数
def render_transparent_animation(
    composition: str,
    output: str,
    *,
    config: Optional[Dict[str, Any]] = None,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
) -> Dict[str, Any]:
    """便捷函数：渲染带透明背景的动画"""
    exe = RemotionExecutor()
    return exe.render_animation(
        composition=composition,
        output=output,
        config=config,
        fps=fps,
        width=width,
        height=height,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    import argparse
    parser = argparse.ArgumentParser(description="Remotion动画素材执行器")
    parser.add_argument("--comp", required=True, help="Composition名称")
    parser.add_argument("--output", required=True, help="输出文件路径")
    parser.add_argument("--config", help="动画配置JSON文件")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--frames", help="帧范围，如 0-150")
    args = parser.parse_args()

    exe = RemotionExecutor()
    logger.info(f"Remotion可用: {exe.available}")

    result = exe.render_animation(
        composition=args.comp,
        output=args.output,
        config_file=args.config,
        fps=args.fps,
        width=args.width,
        height=args.height,
        frames=args.frames,
    )
    logger.info(json.dumps(result, ensure_ascii=False, indent=2))
