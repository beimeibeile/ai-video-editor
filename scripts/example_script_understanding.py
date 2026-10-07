# -*- coding: utf-8 -*-
"""
P23深度语义增强使用示例
展示如何用script_understanding_engine指导相册模板构建

使用方法：
    python example_script_understanding.py --video 原视频.mp4 --bgm bgm.mp3 --output 输出目录
"""
import os
import sys
import json
import argparse

# 添加skill脚本路径
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

from script_understanding_engine import ScriptUnderstandingEngine


def main():
    parser = argparse.ArgumentParser(description="P23深度语义增强使用示例")
    parser.add_argument("--video", required=True, help="原视频路径")
    parser.add_argument("--bgm", help="BGM路径")
    parser.add_argument("--output", help="输出目录")
    parser.add_argument("--ffmpeg", default=r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe")
    parser.add_argument("--ffprobe", default=r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe")
    args = parser.parse_args()

    # 创建引擎
    engine = ScriptUnderstandingEngine(args.ffmpeg, args.ffprobe)

    print("=" * 60)
    print("P23深度语义增强 - 相册模板构建指导")
    print("=" * 60)

    # 1. 深度分析原视频
    print("\n[1/3] 深度分析原视频...")
    analysis = engine.analyze_video(args.video, args.bgm)
    print(f"  ✅ {analysis.summary}")

    # 2. 生成二创方案
    print("\n[2/3] 生成模板化改编方案...")
    plan = engine.plan_adaptation(analysis, adaptation_type="模板化")
    print(f"  ✅ {plan.adaptation_type}方案")
    print(f"  核心理念: {plan.core_concept}")
    print(f"  难度: {plan.difficulty}")
    print(f"  预估工作量: {plan.estimated_effort}")

    # 3. 输出构建指导
    print("\n[3/3] 相册模板构建指导:")
    print(f"\n  【情绪结构】")
    for seg in analysis.emotion_segments:
        print(f"    {seg.start_time:.1f}-{seg.end_time:.1f}s: {seg.emotion}"
              f"(强度{seg.intensity:.1f}) -> {seg.recommended_camera} / {seg.recommended_effect}")

    print(f"\n  【镜头计划】({len(plan.shot_plan)}个镜头)")
    for shot in plan.shot_plan:
        print(f"    [{shot['index']:2d}] {shot['start_time']:5.1f}s "
              f"dur={shot['duration']:.1f}s "
              f"{shot['emotion']:4s} "
              f"{shot['camera_move']}(强度{shot['camera_intensity']:.3f}) "
              f"转场:{shot['transition_in']}")

    print(f"\n  【素材需求】")
    for req in plan.material_requirements:
        print(f"    - {req['type']}: {req['count']}个 ({req['note']})")

    print(f"\n  【保留元素】")
    for elem in plan.preserved_elements:
        print(f"    ✓ {elem}")

    print(f"\n  【可替换元素】")
    for elem in plan.replaced_elements:
        print(f"    ⟳ {elem}")

    # 保存结果
    if args.output:
        os.makedirs(args.output, exist_ok=True)
        result = {
            "video_analysis": analysis.to_dict(),
            "adaptation_plan": plan.to_dict(),
        }
        output_file = os.path.join(args.output, "understanding_result.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n  📁 结果已保存: {output_file}")

    print("\n" + "=" * 60)
    print("完成！可基于以上指导构建剪映相册模板工程")
    print("=" * 60)


if __name__ == "__main__":
    main()
