"""
《翻身》v4 质量闭环验收
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from quality_loop import EndToEndQualityLoop

def main():
    loop = EndToEndQualityLoop()

    # 模拟视频元数据
    video_meta = {
        "title": "翻身 v4",
        "duration": 145,
        "scenes": 7,
        "shots": 28,
        "has_video": True,
        "has_audio": True,
        "has_subtitles": True,
        "has_effects": True,
        "narration_count": 20,
        "dialogue_count": 8,
        "bgm_count": 7,
        "image_count": 5,
        "black_screen_duration": 0,
        "avg_shot_duration": 5.2,
    }

    # 评估
    print("=" * 60)
    print("《翻身》v4 端到端质量验收")
    print("=" * 60)

    result = loop.evaluate_full_video(video_meta)

    print(f"\n综合评分: {result['total_score']}/100 ({result['grade']})")
    print(f"通过: {result['passed']} | 失败: {result['failed']} | 警告: {result['warnings']}")

    print("\n详细检查:")
    for check in result["checks"]:
        status = "✅" if check["passed"] else "❌"
        print(f"  {status} {check['name']}: {check['score']}分 - {check['message']}")

    # 生成报告
    output_dir = os.path.join(os.path.dirname(__file__), "quality_test_output", "fanshen_v4")
    os.makedirs(output_dir, exist_ok=True)

    json_path = loop.save_json_report(result, os.path.join(output_dir, "report.json"))
    html_path = loop.generate_html_report(result, os.path.join(output_dir, "report.html"))

    print(f"\n报告已生成:")
    print(f"  JSON: {json_path}")
    print(f"  HTML: {html_path}")

    # 重生成建议
    suggestions = loop.generate_regenerate_suggestions(result)
    if suggestions:
        print("\n改进建议:")
        for s in suggestions:
            print(f"  - {s}")
    else:
        print("\n✅ 无需重生成，质量达标")

    print("\n" + "=" * 60)
    print("质量验收完成")
    print("=" * 60)

    return result

if __name__ == "__main__":
    main()
