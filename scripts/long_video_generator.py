#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T3-1: 长视频生成与叙事引擎
将长剧本拆分为多段，逐段生成视频并拼接，支持首尾帧衔接
"""
import os
import sys
import json
import time
import logging
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# 路径配置
FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"

# ComfyUI skill 路径
COMFYUI_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\comfyui-controls-skill\scripts"
if COMFYUI_SKILL not in sys.path:
    sys.path.insert(0, COMFYUI_SKILL)


@dataclass
class StoryBeat:
    """叙事节拍"""
    beat_id: int
    title: str  # 节拍标题
    description: str  # 画面描述
    narration: str = ""  # 旁白/台词
    duration: float = 4.0  # 目标时长（秒）
    emotion: str = "normal"  # 情绪
    camera: str = "medium"  # 景别（closeup/medium/wide）
    transition: str = "cut"  # 转场方式
    first_frame_prompt: str = ""  # 首帧提示词（可选）
    last_frame_prompt: str = ""  # 尾帧提示词（可选）


@dataclass
class VideoSegment:
    """视频片段"""
    segment_id: int
    beat: StoryBeat
    output_path: str = ""
    first_frame_path: str = ""  # 首帧图片路径
    last_frame_path: str = ""  # 尾帧图片路径
    duration: float = 0.0
    success: bool = False
    error: str = ""


class NarrativeEngine:
    """叙事结构引擎 - 将长文本拆分为叙事节拍"""

    # 叙事结构模板
    STRUCTURE_TEMPLATES = {
        "three_act": {
            "name": "三幕结构",
            "acts": [
                {"name": "开场", "ratio": 0.25, "beats": ["建立场景", "引入角色", "触发事件"]},
                {"name": "发展", "ratio": 0.50, "beats": ["上升动作", "中点转折", "危机加深"]},
                {"name": "结局", "ratio": 0.25, "beats": ["高潮", "解决", "收尾"]},
            ]
        },
        "hero_journey": {
            "name": "英雄之旅",
            "acts": [
                {"name": "启程", "ratio": 0.25, "beats": ["平凡世界", "冒险召唤", "跨越门槛"]},
                {"name": "启蒙", "ratio": 0.50, "beats": ["试炼之路", "终极考验", "获得宝藏"]},
                {"name": "归来", "ratio": 0.25, "beats": ["回归之路", "复活", "满载而归"]},
            ]
        },
        "vlog": {
            "name": "Vlog结构",
            "acts": [
                {"name": "开场", "ratio": 0.15, "beats": ["钩子", "自我介绍"]},
                {"name": "主体", "ratio": 0.70, "beats": ["内容1", "内容2", "内容3"]},
                {"name": "结尾", "ratio": 0.15, "beats": ["总结", "号召行动"]},
            ]
        },
    }

    def __init__(self):
        pass

    def parse_script(self, script: str, structure: str = "three_act",
                     total_duration: float = 60.0) -> List[StoryBeat]:
        """
        将剧本解析为叙事节拍

        Args:
            script: 剧本文本
            structure: 叙事结构（three_act/hero_journey/vlog）
            total_duration: 总时长（秒）

        Returns:
            叙事节拍列表
        """
        template = self.STRUCTURE_TEMPLATES.get(structure, self.STRUCTURE_TEMPLATES["three_act"])

        # 简单的文本分段：按句子/段落拆分
        sentences = self._split_sentences(script)

        beats = []
        beat_id = 0

        # 计算每幕的节拍数和时长
        for act in template["acts"]:
            act_duration = total_duration * act["ratio"]
            beats_per_act = len(act["beats"])
            beat_duration = act_duration / beats_per_act

            for beat_name in act["beats"]:
                # 为每个节拍分配文本
                if sentences:
                    # 取一部分句子作为该节拍的描述
                    n_sentences = max(1, len(sentences) // (len(template["acts"]) * beats_per_act))
                    beat_text = " ".join(sentences[:n_sentences])
                    sentences = sentences[n_sentences:]
                else:
                    beat_text = beat_name

                beat = StoryBeat(
                    beat_id=beat_id,
                    title=beat_name,
                    description=beat_text,
                    narration=beat_text,
                    duration=beat_duration,
                    emotion="normal",
                    camera="medium",
                )
                beats.append(beat)
                beat_id += 1

        # 如果还有剩余文本，追加到最后一个节拍
        if sentences:
            if beats:
                beats[-1].description += " " + " ".join(sentences)
                beats[-1].narration += " " + " ".join(sentences)

        logger.info(f"[叙事引擎] 解析完成: {len(beats)}个节拍, 总时长{total_duration}s")
        return beats

    def _split_sentences(self, text: str) -> List[str]:
        """简单的句子分割"""
        # 按标点符号分割
        import re
        sentences = re.split(r'[。！？.!?\n]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def generate_prompts(self, beat: StoryBeat, style: str = "cinematic") -> Dict[str, str]:
        """
        为节拍生成视频生成提示词

        Args:
            beat: 叙事节拍
            style: 风格（cinematic/anime/realistic等）

        Returns:
            包含 positive_prompt, negative_prompt 的字典
        """
        # 基础风格前缀
        style_prefixes = {
            "cinematic": "cinematic film still, 8k, highly detailed, professional lighting, ",
            "anime": "anime style, vibrant colors, detailed background, ",
            "realistic": "photorealistic, 8k, natural lighting, detailed, ",
            "vlog": "casual vlog style, natural lighting, handheld camera, ",
        }
        prefix = style_prefixes.get(style, style_prefixes["cinematic"])

        # 景别描述
        camera_desc = {
            "closeup": "close-up shot, ",
            "medium": "medium shot, ",
            "wide": "wide shot, ",
        }
        camera = camera_desc.get(beat.camera, camera_desc["medium"])

        positive = f"{prefix}{camera}{beat.description}, {beat.emotion} mood"
        negative = "blurry, low quality, distorted, ugly, watermark, text"

        return {
            "positive": positive,
            "negative": negative,
        }


class LongVideoGenerator:
    """长视频生成器 - 分段生成+首尾帧衔接+拼接"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or r"C:\Users\Administrator\Videos\剪映导出\ai-video-editor\long_video"
        os.makedirs(self.output_dir, exist_ok=True)
        self.narrative = NarrativeEngine()

    def generate(self, script: str, total_duration: float = 60.0,
                 structure: str = "three_act", style: str = "cinematic",
                 width: int = 768, height: int = 1344,
                 use_first_frame: bool = True) -> Dict[str, Any]:
        """
        生成长视频

        Args:
            script: 剧本文本
            total_duration: 总时长（秒）
            structure: 叙事结构
            style: 视觉风格
            width: 视频宽度
            height: 视频高度
            use_first_frame: 是否使用首尾帧衔接

        Returns:
            生成结果
        """
        start_time = time.time()
        logger.info(f"\n{'='*60}")
        logger.info(f"长视频生成开始")
        logger.info(f"剧本长度: {len(script)}字")
        logger.info(f"目标时长: {total_duration}秒")
        logger.info(f"叙事结构: {structure}")
        logger.info(f"{'='*60}")

        # 步骤1: 解析剧本为叙事节拍
        beats = self.narrative.parse_script(script, structure, total_duration)
        logger.info(f"\n[步骤1] 叙事节拍: {len(beats)}个")

        # 步骤2: 逐段生成视频
        segments = []
        last_frame_path = None

        for i, beat in enumerate(beats):
            logger.info(f"\n[步骤2.{i+1}] 生成片段 {i+1}/{len(beats)}: {beat.title}")

            segment = self._generate_segment(
                beat=beat,
                index=i,
                style=style,
                width=width,
                height=height,
                first_frame_path=last_frame_path if use_first_frame else None,
            )
            segments.append(segment)

            if segment.success:
                last_frame_path = segment.last_frame_path
                logger.info(f"  ✅ 片段{i+1}生成成功: {os.path.basename(segment.output_path)}")
            else:
                logger.warning(f"  ❌ 片段{i+1}生成失败: {segment.error}")

        # 步骤3: 拼接视频
        logger.info(f"\n[步骤3] 拼接视频")
        successful_segments = [s for s in segments if s.success]
        final_path = ""

        if successful_segments:
            final_path = self._concat_videos(
                [s.output_path for s in successful_segments],
                os.path.join(self.output_dir, f"final_{int(time.time())}.mp4")
            )
            if final_path:
                logger.info(f"  ✅ 拼接完成: {os.path.basename(final_path)}")
            else:
                logger.warning("  ❌ 拼接失败")
        else:
            logger.warning("  ⚠️  没有成功生成的片段，跳过拼接")

        # 生成报告
        duration = time.time() - start_time
        report = {
            "status": "success" if final_path else "partial",
            "script_length": len(script),
            "target_duration": total_duration,
            "structure": structure,
            "total_beats": len(beats),
            "success_segments": len(successful_segments),
            "failed_segments": len(segments) - len(successful_segments),
            "final_output": final_path,
            "total_time": round(duration, 1),
            "segments": [asdict(s) for s in segments],
        }

        # 保存报告
        report_path = os.path.join(self.output_dir, f"report_{int(time.time())}.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        report["report_path"] = report_path

        logger.info(f"\n{'='*60}")
        logger.info(f"长视频生成完成")
        logger.info(f"成功: {len(successful_segments)}/{len(beats)} 片段")
        logger.info(f"总耗时: {duration:.1f}秒")
        logger.info(f"{'='*60}")

        return report

    def _generate_segment(self, beat: StoryBeat, index: int, style: str,
                          width: int, height: int,
                          first_frame_path: str = None) -> VideoSegment:
        """生成单个视频片段"""
        segment = VideoSegment(segment_id=index, beat=beat)

        try:
            # 生成提示词
            prompts = self.narrative.generate_prompts(beat, style)

            # 计算帧数（H3每段约3-4秒，81帧）
            frames = 81  # H3标准帧数

            # 调用 H3 runner 生成视频
            from minimax_h3_runner import MiniMaxH3Runner

            runner = MiniMaxH3Runner()
            segment_dir = os.path.join(self.output_dir, f"segment_{index:03d}")
            os.makedirs(segment_dir, exist_ok=True)

            if first_frame_path and os.path.exists(first_frame_path):
                # 使用首帧衔接（图生视频）
                logger.info(f"  使用首帧衔接: {os.path.basename(first_frame_path)}")
                output = runner.image_to_video(
                    prompt=prompts["positive"],
                    image_path=first_frame_path,
                    width=width,
                    height=height,
                    frames=frames,
                )
            else:
                # 文生视频
                output = runner.text_to_video(
                    prompt=prompts["positive"],
                    width=width,
                    height=height,
                    frames=frames,
                )

            if output and os.path.exists(output):
                segment.output_path = output
                segment.success = True

                # 提取首帧和尾帧
                segment.first_frame_path = self._extract_frame(output, 0, segment_dir, "first")
                segment.last_frame_path = self._extract_frame(output, -1, segment_dir, "last")

                # 获取实际时长
                segment.duration = self._get_video_duration(output)
            else:
                segment.success = False
                segment.error = "H3生成返回空结果"

        except Exception as e:
            segment.success = False
            segment.error = str(e)
            logger.error(f"  片段生成异常: {e}")

        return segment

    def _extract_frame(self, video_path: str, frame_index: int,
                       output_dir: str, prefix: str) -> str:
        """提取视频帧"""
        try:
            output_path = os.path.join(output_dir, f"{prefix}.png")
            if frame_index == 0:
                # 首帧
                cmd = [FFMPEG, "-y", "-i", video_path, "-vframes", "1", output_path]
            else:
                # 尾帧
                cmd = [FFMPEG, "-y", "-sseof", "-0.1", "-i", video_path,
                       "-vframes", "1", output_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if os.path.exists(output_path):
                return output_path
        except Exception as e:
            logger.warning(f"  提取帧失败: {e}")
        return ""

    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        try:
            result = subprocess.run(
                [FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True, text=True, timeout=10
            )
            return float(result.stdout.strip()) if result.stdout.strip() else 0.0
        except Exception:
            return 0.0

    def _concat_videos(self, video_paths: List[str], output_path: str) -> str:
        """拼接多个视频"""
        if not video_paths:
            return ""

        try:
            # 创建文件列表
            list_file = os.path.join(self.output_dir, "concat_list.txt")
            with open(list_file, "w", encoding="utf-8") as f:
                for p in video_paths:
                    # 使用绝对路径，转义反斜杠
                    abs_path = os.path.abspath(p).replace("\\", "/")
                    f.write(f"file '{abs_path}'\n")

            # 使用 concat demuxer 拼接
            cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0",
                   "-i", list_file, "-c", "copy", output_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return output_path
            else:
                # 如果 copy 失败，尝试重新编码
                logger.warning("  concat copy失败，尝试重新编码...")
                cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0",
                       "-i", list_file, "-c:v", "libx264", "-c:a", "aac", output_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if os.path.exists(output_path):
                    return output_path

        except Exception as e:
            logger.error(f"  拼接异常: {e}")

        return ""


# 便捷函数
def generate_long_video(script: str, total_duration: float = 60.0,
                        structure: str = "three_act", **kwargs) -> Dict[str, Any]:
    """便捷生成长视频"""
    generator = LongVideoGenerator()
    return generator.generate(script, total_duration, structure, **kwargs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    # 测试叙事引擎
    print("=== 叙事引擎测试 ===")
    engine = NarrativeEngine()
    script = "一个年轻人在城市中寻找自己的梦想。他遇到了许多困难，但从不放弃。最终，他成功实现了自己的目标，成为了一个更好的人。"
    beats = engine.parse_script(script, "three_act", 30.0)
    for beat in beats:
        print(f"  [{beat.beat_id}] {beat.title}: {beat.description[:30]}... ({beat.duration:.1f}s)")

    print("\n=== 提示词生成测试 ===")
    for beat in beats[:2]:
        prompts = engine.generate_prompts(beat, "cinematic")
        print(f"  {beat.title}:")
        print(f"    Positive: {prompts['positive'][:80]}...")

    print("\n测试完成")
