import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from quality_loop import EndToEndQualityLoop
from fanshen_v4_script import SCRIPT_V4

loop = EndToEndQualityLoop()
result = loop.evaluate_full_video(SCRIPT_V4)

print("=" * 60)
print("《翻身》v4 端到端质量验收")
print("=" * 60)
print(f"综合评分: {result.total_score}/100 ({result.overall_level})")
print(f"通过: {result.passed_count} | 失败: {result.failed_count} | 警告: {result.warning_count}")
print(f"需重生成: {len(result.regenerate_needed)}个镜头")
print(f"评估耗时: {result.duration_seconds:.1f}s")

if result.shot_results:
    print(f"\n镜头评估: {len(result.shot_results)}个镜头")
    for sr in result.shot_results[:5]:
        print(f"  {sr.shot_id}: {sr.score}分 - {sr.notes}")

output_dir = os.path.join(os.path.dirname(__file__), "quality_test_output", "fanshen_v4")
os.makedirs(output_dir, exist_ok=True)

# 保存JSON
report_dict = {
    "total_score": result.total_score,
    "overall_level": str(result.overall_level),
    "passed_count": result.passed_count,
    "failed_count": result.failed_count,
    "warning_count": result.warning_count,
    "regenerate_needed": result.regenerate_needed,
    "generated_at": result.generated_at,
}
json_path = os.path.join(output_dir, "report.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(report_dict, f, ensure_ascii=False, indent=2)
print(f"\nJSON报告: {json_path}")
print("质量验收完成")
