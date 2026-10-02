"""
《翻身》v4 关键画面批量生成
使用ComfyUI sd_xl_turbo快速生成
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from comfyui_image_pipeline import ComfyUIImagePipeline

# 关键画面任务
KEY_IMAGES = [
    {
        "name": "01_linmo_depressed",
        "prompt": "a tired 32-year-old Chinese office worker, dark circles under eyes, wrinkled shirt, slumped at desk late at night, only computer screen blue light, cinematic lighting, photorealistic, 9:16 vertical",
        "width": 768, "height": 1024,
    },
    {
        "name": "02_linmo_confident",
        "prompt": "a confident 32-year-old Chinese man, neat shirt, bright eyes, slight smile, standing by window with city skyline, warm morning light, cinematic, photorealistic, 9:16 vertical",
        "width": 768, "height": 1024,
    },
    {
        "name": "03_office_night",
        "prompt": "empty modern office at night, only one desk lit by computer screen, dark and moody, blue tones, cinematic wide shot, photorealistic, 9:16 vertical",
        "width": 768, "height": 1024,
    },
    {
        "name": "04_home_computer",
        "prompt": "small apartment room, man sitting on sofa using laptop, warm desk lamp light, cozy but slightly messy, late night, cinematic, photorealistic, 9:16 vertical",
        "width": 768, "height": 1024,
    },
    {
        "name": "05_creative_space",
        "prompt": "modern bright creative studio, multiple people working on computers, large windows, plants, minimalist design, warm natural light, cinematic wide shot, photorealistic, 9:16 vertical",
        "width": 768, "height": 1024,
    },
]

def main():
    pipeline = ComfyUIImagePipeline()
    print(f"ComfyUI在线: {pipeline.is_online()}")

    if not pipeline.is_online():
        print("❌ ComfyUI离线，无法生成")
        return

    results = []
    for i, task in enumerate(KEY_IMAGES):
        print(f"\n[{i+1}/{len(KEY_IMAGES)}] 生成: {task['name']}")
        print(f"  Prompt: {task['prompt'][:60]}...")

        result = pipeline.generate_with_reference(
            prompt=task["prompt"],
            width=task["width"],
            height=task["height"],
            steps=6,
            cfg=2.0,
        )

        if result.success:
            # 重命名文件
            new_path = os.path.join(pipeline.output_dir, f"{task['name']}.png")
            try:
                import shutil
                shutil.copy2(result.image_path, new_path)
                print(f"  ✅ 完成: {new_path}")
                print(f"     质量: {result.quality_score:.0f}")
                results.append({"name": task["name"], "path": new_path, "score": result.quality_score})
            except Exception as e:
                print(f"  ⚠️ 重命名失败: {e}")
                results.append({"name": task["name"], "path": result.image_path, "score": result.quality_score})
        else:
            print(f"  ❌ 失败: {result.error}")
            results.append({"name": task["name"], "path": "", "score": 0, "error": result.error})

    print("\n" + "=" * 60)
    print("生成结果汇总:")
    success = sum(1 for r in results if r["path"])
    print(f"  成功: {success}/{len(results)}")
    for r in results:
        status = "✅" if r["path"] else "❌"
        print(f"  {status} {r['name']}: 质量{r.get('score', 0):.0f}")

    # 保存结果清单
    import json
    manifest_path = os.path.join(pipeline.output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n清单已保存: {manifest_path}")

if __name__ == "__main__":
    main()
