#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自学习系统数据积累脚本
记录各模块使用数据，验证参数推荐功能
"""
import sys
import os
import json
import time
import random

sys.path.insert(0, r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\ai-video-editor\scripts")

from self_learning_system import get_self_learning_system, log_usage, log_quality


def main():
    print("=== 自学习系统数据积累 ===")
    sls = get_self_learning_system()

    # 模拟H3视频生成使用记录
    print("\n1. 记录H3视频生成使用数据...")
    h3_configs = [
        {"model_variant": "FL2VA", "width": 768, "height": 1344, "frames": 81, "steps": 20, "sampler": "res_multistep"},
        {"model_variant": "FL2VA", "width": 768, "height": 1344, "frames": 81, "steps": 4, "sampler": "res_multistep", "lora": "turbo_4step"},
        {"model_variant": "REF2VA", "width": 768, "height": 1344, "frames": 81, "steps": 20, "sampler": "res_multistep"},
    ]

    for i, config in enumerate(h3_configs):
        # 模拟多次使用
        for j in range(3):
            duration = random.uniform(90, 150) if "turbo" not in str(config) else random.uniform(30, 50)
            success = random.random() > 0.1  # 90%成功率
            log_usage(
                module="minimax_h3_runner",
                action="text_to_video" if j == 0 else "image_to_video",
                params=config,
                duration=duration,
                success=success,
                error="" if success else "CUDA OOM",
            )
            if success:
                log_quality(
                    module="minimax_h3_runner",
                    output_path=f"h3_output_{i}_{j}.mp4",
                    score=random.uniform(6.5, 9.0),
                    feedback="motion quality good" if "turbo" not in str(config) else "fast but lower quality",
                )

    print("  ✅ H3使用记录已记录")

    # 模拟TTS使用记录
    print("\n2. 记录TTS使用数据...")
    tts_voices = ["豆包", "顾客", "客服", "少年", "御姐", "总裁"]
    tts_emotions = ["happy", "sad", "angry", "calm", "excited", "normal"]

    for voice in tts_voices:
        for emotion in tts_emotions[:3]:
            duration = random.uniform(3, 10)
            success = random.random() > 0.05
            log_usage(
                module="tts_executor",
                action="synthesize",
                params={"character": voice, "emotion": emotion},
                duration=duration,
                success=success,
                error="" if success else "ComfyUI timeout",
            )

    print("  ✅ TTS使用记录已记录")

    # 模拟模板复刻使用记录
    print("\n3. 记录模板复刻使用数据...")
    template_types = ["cinematic_bar", "music_player", "book_flip", "photo_album", "vlog"]
    for t in template_types:
        for i in range(2):
            duration = random.uniform(15, 40)
            success = random.random() > 0.15
            log_usage(
                module="template_creator",
                action="create_template",
                params={"template_type": t, "segments": random.randint(4, 8)},
                duration=duration,
                success=success,
                error="" if success else "font not found",
            )

    print("  ✅ 模板复刻使用记录已记录")

    # 模拟剪映工程使用记录
    print("\n4. 记录剪映工程使用数据...")
    transitions = ["叠化", "运镜", "模糊", "滑动", "闪黑"]
    for t in transitions:
        for i in range(2):
            log_usage(
                module="smart_transition_selector",
                action="select_transition",
                params={"emotion": random.choice(["happy", "sad", "energetic"]), "transition": t},
                duration=0.1,
                success=True,
            )

    print("  ✅ 剪映工程使用记录已记录")

    # 生成学习报告
    print("\n5. 生成自学习报告...")
    report = sls.generate_report()
    print(f"  总使用记录: {report['total_usage_records']}")
    print(f"  质量记录: {report['total_quality_records']}")
    print(f"  模块数: {len(report['modules'])}")
    print(f"  踩坑记录: {report['pitfalls_count']}")

    # 测试参数推荐
    print("\n6. 测试最优参数推荐...")
    best = sls.get_best_params("minimax_h3_runner", "text_to_video")
    if best:
        print(f"  H3文生视频最优参数:")
        print(f"    平均耗时: {best.get('avg_duration', 0):.1f}s")
        print(f"    成功率: {best.get('success_rate', 0):.1%}")
        print(f"    推荐配置: {json.dumps(best.get('most_successful_params', {}), ensure_ascii=False)[:100]}")

    # 测试踩坑匹配
    print("\n7. 测试踩坑自动诊断...")
    pitfalls = sls.match_pitfall("CUDA out of memory")
    if pitfalls:
        print(f"  匹配到踩坑: {pitfalls.get('title', '未知')}")
        print(f"  解决方案: {pitfalls.get('solution', '无')[:80]}")
    else:
        print("  未匹配到已知踩坑（已添加OOM踩坑记录）")
        sls.add_pitfall(
            module="minimax_h3_runner",
            symptom="CUDA out of memory 显存不足",
            root_cause="分辨率/帧数过高，VAE解码显存不足",
            solution="降低分辨率/帧数，使用分块VAE解码，启用加速LoRA减少步数",
            error_pattern="CUDA out of memory|out of memory|OOM",
        )
        print("  ✅ 已添加OOM踩坑记录")

    # 添加更多踩坑记录
    print("\n8. 添加常见踩坑记录...")
    common_pitfalls = [
        {
            "module": "comfyui_executor",
            "symptom": "ComfyUI连接超时/未运行",
            "root_cause": "ComfyUI服务未启动或地址错误",
            "solution": "检查ComfyUI是否启动，默认地址http://127.0.0.1:8188",
            "error_pattern": "Connection refused|timeout|未运行",
        },
        {
            "module": "minimax_h3_runner",
            "symptom": "图片上传失败 Invalid image file",
            "root_cause": "LoadImage节点只能加载ComfyUI input目录下的图片",
            "solution": "必须先调用upload_image上传到ComfyUI input目录，不能直接用本地路径",
            "error_pattern": "Invalid image file|LoadImage.*error",
        },
        {
            "module": "jianying_executor",
            "symptom": "转场错位",
            "root_cause": "转场加在了错误的片段上",
            "solution": "转场必须加在前一个片段上，加在后片段会导致错位",
            "error_pattern": "transition.*错位|转场位置错误",
        },
        {
            "module": "template_creator",
            "symptom": "黑边遮罩跑到画面中间",
            "root_cause": "独立遮罩轨道默认居中显示",
            "solution": "独立遮罩轨道无法实现上下黑边，需将黑边内置到素材图片中",
            "error_pattern": "遮罩.*居中|letterbox.*center",
        },
        {
            "module": "tts_executor",
            "symptom": "TTS音色不可用",
            "root_cause": "角色名与映射表不匹配",
            "solution": "使用list_voices()查询可用音色，角色名需与映射表匹配",
            "error_pattern": "voice.*not found|音色不存在",
        },
    ]
    for p in common_pitfalls:
        sls.add_pitfall(**p)
    print(f"  ✅ 已添加{len(common_pitfalls)}条常见踩坑记录")

    # 最终报告
    print("\n" + "="*50)
    print("自学习系统数据积累完成!")
    print(f"  使用记录: {report['total_usage_records']}条")
    print(f"  踩坑记录: {len(sls.get_pitfalls())}条")
    print(f"  模块覆盖: {len(report['modules'])}个")
    print("="*50)


if __name__ == "__main__":
    main()
