"""
P1任务3端到端验证：pipeline_script_driver全链路测试
剧本引擎 → 智能调度器 → E2E Pipeline → 质量门
"""
import sys
import os

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

from cap_e2e_pipeline.pipeline_script_driver import ScriptDrivenPipeline

if __name__ == "__main__":
    print("=" * 70)
    print("P1任务3 端到端验证: ScriptDrivenPipeline 全链路")
    print("=" * 70)

    driver = ScriptDrivenPipeline(
        project_dir=os.path.join(SKILL_ROOT, "debug", "script_driver_test"),
        output_dir=os.path.join(SKILL_ROOT, "debug", "script_driver_test", "outputs"),
    )

    result = driver.run(
        topic="城市夜景探店",
        video_type="exploration",
        duration=30,
        project_name="ScriptDriver_E2E_Test",
        hook_effect="wipe",
    )

    print("\n" + "=" * 70)
    print("验证结果汇总")
    print("=" * 70)
    print(f"  状态: {result['status']}")
    print(f"  主题: {result['topic']}")
    print(f"  类型: {result['video_type']}")
    print(f"  目标时长: {result['target_duration']}秒")
    print(f"  工程名: {result['project_name']}")

    for step, info in result.get("steps", {}).items():
        status = info.get("status", "?")
        print(f"  Step {step}: {status}")

    if result["status"] == "success":
        print(f"\n  ✅ 全链路验证通过! 耗时: {result.get('elapsed_seconds', 0):.1f}秒")
        synth = result["steps"].get("synthesize", {})
        print(f"  工程路径: {synth.get('draft_path', 'N/A')}")
        print(f"  片段数: {synth.get('segment_count', 'N/A')}")
        print(f"  时长: {synth.get('duration', 'N/A')}秒")
    else:
        print(f"\n  ❌ 全链路失败: {result.get('error', '未知错误')}")
