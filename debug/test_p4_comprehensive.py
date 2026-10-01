"""
P4工业化阶段综合测试验证
测试所有P4模块的核心功能
"""
import os
import sys
import json
import time

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))

results = []

def test(name, func):
    """运行测试并记录结果"""
    print(f"\n{'='*60}")
    print(f"🧪 测试: {name}")
    print(f"{'='*60}")
    try:
        result = func()
        results.append({"name": name, "passed": True, "result": result})
        print(f"✅ 通过: {result}")
        return True
    except Exception as e:
        import traceback
        results.append({"name": name, "passed": False, "error": str(e)})
        print(f"❌ 失败: {e}")
        traceback.print_exc()
        return False


# ==================== P4-1 战斗群v2测试 ====================

def test_carrier_group_v2():
    from cap_carrier_group.carrier_group_v2 import CarrierGroup
    group = CarrierGroup()
    status = group.get_status()

    assert status["combat_mode"] == "full", f"战斗模式应为full，实际为{status['combat_mode']}"
    assert status["ready_projects"] == 4, f"应4个项目就位，实际{status['ready_projects']}"
    assert status["available_capabilities"] >= 20, f"应至少20项能力，实际{status['available_capabilities']}"

    # 测试能力路由
    from cap_carrier_group.carrier_group_v2 import CAPABILITY_ROUTING
    assert "script_engine" in CAPABILITY_ROUTING
    assert CAPABILITY_ROUTING["script_engine"] == "ai-video-editor"
    assert CAPABILITY_ROUTING["deep_search"] == "anysearch-skill"
    assert CAPABILITY_ROUTING["text_to_image"] == "comfyui-controls-skill"
    assert CAPABILITY_ROUTING["3d_rendering"] == "blender-controls-skill"

    return f"战斗模式={status['combat_mode']}, 项目={status['ready_projects']}/4, 能力={status['available_capabilities']}/{status['total_capabilities']}"


# ==================== P4-2 API服务测试 ====================

def test_api_server():
    from cap_api_server.api_server import APIServer, AuthManager, API_SPEC

    # 测试认证管理器
    auth = AuthManager()
    valid, msg = auth.validate("")  # 无API Key，开放访问
    assert valid, "无API Key时应开放访问"

    # 测试API文档
    assert API_SPEC["openapi"] == "3.0.0"
    assert "/api/health" in API_SPEC["paths"]
    assert "/api/script/generate" in API_SPEC["paths"]
    assert "/api/pipeline/run" in API_SPEC["paths"]
    assert len(API_SPEC["paths"]) >= 8

    return f"API端点={len(API_SPEC['paths'])}个, 认证=开放访问"


# ==================== P4-3 算力调度测试 ====================

def test_compute_scheduler():
    from cap_compute_scheduler.compute_scheduler import ComputeScheduler, TaskPriority

    scheduler = ComputeScheduler(health_check_interval=999)  # 禁用健康检查

    # 注册实例
    scheduler.register_instance("test_local", "http://127.0.0.1:9999", location="local")
    instances = scheduler.list_instances()
    assert len(instances) == 1
    assert instances[0]["instance_id"] == "test_local"

    # 提交任务
    task_id = scheduler.submit_task(
        workflow={"test": "workflow"},
        priority="normal",
    )
    assert task_id.startswith("task_")

    # 获取任务状态
    status = scheduler.get_task_status(task_id)
    assert status is not None
    assert status["priority"] == "normal"

    # 统计
    stats = scheduler.get_stats()
    assert stats["total_instances"] == 1
    assert stats["total_tasks"] == 1

    scheduler.stop()
    return f"实例={stats['total_instances']}, 任务={stats['total_tasks']}, 队列={stats['queue_size']}"


# ==================== P4-4 模板市场测试 ====================

def test_template_market():
    from cap_template_market.template_market import TemplateMarket

    market = TemplateMarket(storage_dir=os.path.join(SKILL_ROOT, "debug", "test_template_market"))

    # 上传模板
    tid = market.upload_template(
        name="测试模板",
        description="这是一个测试模板",
        author="test_user",
        category="vlog",
        tags=["测试", "vlog"],
        duration=30,
    )
    assert tid is not None

    # 搜索模板
    results = market.search_templates(keyword="测试")
    assert len(results) >= 1
    assert results[0]["name"] == "测试模板"

    # 评分
    market.rate_template(tid, 5)
    market.rate_template(tid, 4)
    template = market.get_template(tid) if hasattr(market, "get_template") else None
    # 直接从搜索结果获取
    search_result = market.search_templates(keyword="测试")[0]
    assert search_result["rating_count"] == 2

    # 分类列表
    categories = market.list_categories()
    assert any(c["category"] == "vlog" for c in categories)

    # 统计
    stats = market.get_stats()
    assert stats["total_templates"] >= 1

    return f"模板={stats['total_templates']}, 分类={len(categories)}, 评分={search_result['rating']}"


# ==================== P4-5 教程消化测试 ====================

def test_tutorial_digester():
    from cap_tutorial_digester.tutorial_digester import TutorialDigester, TutorialStatus

    digester = TutorialDigester(storage_dir=os.path.join(SKILL_ROOT, "debug", "test_tutorial_digester"))

    # 添加教程
    tid = digester.add_tutorial(
        title="测试教程",
        url="https://test.com/tutorial",
        platform="douyin",
        description="这是一个测试教程",
        tags=["测试", "文字"],
    )
    assert tid is not None

    # 解析教程
    digester.parse_tutorial(
        tid,
        key_steps=[
            {"step": 1, "description": "第一步"},
            {"step": 2, "description": "第二步"},
        ],
        effect_name="test_effect",
        effect_category="text",
    )

    tutorial = digester.get_tutorial(tid)
    assert tutorial["status"] == TutorialStatus.PARSED
    assert len(tutorial["key_steps"]) == 2

    # 生成代码
    code_path = digester.generate_effect_code(tid, effect_name="test_effect")
    assert code_path is not None
    assert os.path.exists(code_path)

    # 统计
    stats = digester.get_stats()
    assert stats["total_tutorials"] >= 1

    return f"教程={stats['total_tutorials']}, 代码生成={code_path is not None}"


# ==================== 运行所有测试 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 P4工业化阶段综合测试验证")
    print("=" * 60)

    test("P4-1 战斗群v2", test_carrier_group_v2)
    test("P4-2 API服务化", test_api_server)
    test("P4-3 算力调度", test_compute_scheduler)
    test("P4-4 模板市场", test_template_market)
    test("P4-5 教程消化", test_tutorial_digester)

    # 汇总
    print(f"\n{'='*60}")
    print("📊 测试汇总")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"通过: {passed}/{total}")

    for r in results:
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon} {r['name']}")
        if r["passed"]:
            print(f"     结果: {r.get('result', '')}")
        else:
            print(f"     错误: {r.get('error', '')}")

    print(f"\n{'='*60}")
    if passed == total:
        print("🎉 所有测试通过！P4工业化阶段验证完成")
    else:
        print(f"⚠️ {total - passed}个测试失败，需要修复")
    print(f"{'='*60}")
