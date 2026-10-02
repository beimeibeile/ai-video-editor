import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from quality_loop import EndToEndQualityLoop
from fanshen_v4_script import SCRIPT_V4

loop = EndToEndQualityLoop()
result = loop.evaluate_full_video(SCRIPT_V4)

print("=" * 60)
print("《翻身》v4 端到端质量验收")
print("=" * 60)
print(f"综合评分: {result['total_score']}/100 ({result['grade']})")
print(f"通过: {result['passed']} | 失败: {result['failed']} | 警告: {result['warnings']}")
print("\n详细检查:")
for check in result["checks"]:
    status = "PASS" if check["passed"] else "FAIL"
    print(f"  [{status}] {check['name']}: {check['score']}分 - {check['message']}")

output_dir = os.path.join(os.path.dirname(__file__), "quality_test_output", "fanshen_v4")
os.makedirs(output_dir, exist_ok=True)
json_path = loop.save_json_report(result, os.path.join(output_dir, "report.json"))
html_path = loop.generate_html_report(result, os.path.join(output_dir, "report.html"))
print(f"\n报告: {json_path}")
print(f"报告: {html_path}")
print("\n质量验收完成")
