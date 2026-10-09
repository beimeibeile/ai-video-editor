#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2.5-3 Skill协同端到端验证脚本
验证ai-video-editor通过能力注册中心调用其他skill的能力
"""

import logging
logger = logging.getLogger(__name__)

import sys
import os
import time
from pathlib import Path

# 添加ai-video-editor路径
SKILL_ROOT = Path(r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills")
sys.path.insert(0, str(SKILL_ROOT / "ai-video-editor"))

from adapters.capability_registry import (
    get_registry, CapabilityRegistry,
    CapabilityNotFoundError, CapabilityInvokeError
)


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def record(self, name, ok, detail=""):
        status = "PASS" if ok else "FAIL"
        self.results.append((name, status, detail))
        if ok:
            self.passed += 1
        else:
            self.failed += 1
        logger.info(f"  [{status}] {name}" + (f" - {detail}" if detail else ""))

    def summary(self):
        total = self.passed + self.failed
        logger.info(f"\n{'='*60}")
        logger.info(f"验证结果: {self.passed}/{total} 通过")
        if self.failed > 0:
            logger.error(f"失败项:")
            for name, status, detail in self.results:
                if status == "FAIL":
                    logger.info(f"  - {name}: {detail}")
        logger.info("="*60)
        return self.failed == 0


def test_registry_init(result: TestResult):
    """测试1：能力注册中心初始化"""
    logger.info("\n=== 测试1：能力注册中心初始化 ===")
    try:
        registry = get_registry()
        result.record("注册中心单例", registry is not None)
        result.record("注册中心类型", isinstance(registry, CapabilityRegistry))
    except Exception as e:
        result.record("注册中心初始化", False, str(e))


def test_skill_registration(result: TestResult):
    """测试2：6个skill注册"""
    logger.info("\n=== 测试2：6个skill注册 ===")
    registry = get_registry()
    skills = registry.list_skills()

    expected_skills = [
        "jianying-editor",
        "comfyui-controls-skill",
        "blender-controls-skill",
        "remotion-controls-skill",
        "anysearch-skill",
        "ai-video-editor",
    ]

    skill_ids = [s["id"] for s in skills]
    for expected in expected_skills:
        found = expected in skill_ids
        status = "active" if found else "missing"
        if found:
            skill_info = next(s for s in skills if s["id"] == expected)
            status = skill_info["status"]
        result.record(f"skill注册: {expected}", found, f"状态={status}")

    result.record("skill总数=6", len(skills) == 6, f"实际={len(skills)}")


def test_capability_registration(result: TestResult):
    """测试3：25个能力注册"""
    logger.info("\n=== 测试3：能力注册 ===")
    registry = get_registry()
    all_caps = registry.list_capabilities()

    result.record("能力总数>=25", len(all_caps) >= 25, f"实际={len(all_caps)}")

    # 按skill统计
    for skill_id in ["jianying-editor", "comfyui-controls-skill", "remotion-controls-skill",
                      "blender-controls-skill", "anysearch-skill", "ai-video-editor"]:
        skill_caps = registry.list_capabilities(skill_id=skill_id)
        result.record(f"{skill_id}能力数>0", len(skill_caps) > 0, f"实际={len(skill_caps)}")


def test_capability_query(result: TestResult):
    """测试4：能力查询"""
    logger.info("\n=== 测试4：能力查询 ===")
    registry = get_registry()

    test_cases = [
        ("transparent_animation", "透明背景动画"),
        ("text_to_image", "文生图"),
        ("tts", "语音合成"),
        ("deep_search", "深度搜索"),
        ("draft_creation", "剪映工程创建"),
        ("effect_api", "统一特效API"),
        ("emotion_effect_map", "情绪特效映射"),
    ]

    for cap_name, desc in test_cases:
        cap = registry.get_capability(cap_name)
        result.record(f"查询能力: {cap_name}", cap is not None,
                     cap.description if cap else "未找到")

    # 测试不存在的能力
    cap = registry.get_capability("nonexistent_cap_xyz")
    result.record("查询不存在能力返回None", cap is None)


def test_health_check(result: TestResult):
    """测试5：健康检查"""
    logger.info("\n=== 测试5：健康检查（基础） ===")
    registry = get_registry()
    health = registry.check_health(deep=False)

    for skill_id, detail in health.items():
        result.record(f"健康检查: {skill_id}",
                     detail["status"] == "active",
                     f"状态={detail['status']}, 路径存在={detail['path_exists']}")


def test_version_compatibility(result: TestResult):
    """测试6：版本兼容检测"""
    logger.info("\n=== 测试6：版本兼容检测 ===")
    registry = get_registry()

    result.record("anysearch >=3.0.0",
                 registry.check_version_compatibility("anysearch-skill", ">=3.0.0"))
    result.record("ai-video-editor >=2.0.0",
                 registry.check_version_compatibility("ai-video-editor", ">=2.0.0"))
    result.record("jianying >=1.0.0",
                 registry.check_version_compatibility("jianying-editor", ">=1.0.0"))
    result.record("不存在skill版本检测返回False",
                 not registry.check_version_compatibility("nonexistent", ">=1.0.0"))


def test_entry_resolution(result: TestResult):
    """测试7：入口点解析（核心能力）"""
    logger.info("\n=== 测试7：入口点解析（核心能力） ===")
    registry = get_registry()

    # 测试几个核心能力的入口点解析
    test_caps = [
        ("effect_api", "统一特效API"),
        ("emotion_effect_map", "情绪特效映射"),
        ("effect_presets", "特效预设库"),
        ("deep_search", "深度搜索"),
    ]

    for cap_name, desc in test_caps:
        try:
            cap = registry.get_capability(cap_name)
            if cap is None:
                result.record(f"入口解析: {cap_name}", False, "能力未找到")
                continue
            callable_obj = registry._resolve_entry(cap)
            result.record(f"入口解析: {cap_name}", callable_obj is not None,
                         f"类型={type(callable_obj).__name__}")
        except Exception as e:
            result.record(f"入口解析: {cap_name}", False, str(e)[:100])


def test_invoke_with_fallback(result: TestResult):
    """测试8：调用降级机制"""
    logger.info("\n=== 测试8：调用降级机制 ===")
    registry = get_registry()

    # 测试不存在的能力抛出异常
    try:
        registry.invoke("nonexistent_cap_xyz")
        result.record("不存在能力抛出异常", False, "未抛出异常")
    except CapabilityNotFoundError:
        result.record("不存在能力抛出CapabilityNotFoundError", True)
    except Exception as e:
        result.record("不存在能力抛出异常", False, f"异常类型错误: {type(e).__name__}")


def test_registry_serialization(result: TestResult):
    """测试9：注册中心序列化"""
    logger.info("\n=== 测试9：注册中心序列化 ===")
    registry = get_registry()

    try:
        d = registry.to_dict()
        result.record("to_dict返回字典", isinstance(d, dict))
        result.record("包含skills字段", "skills" in d)
        result.record("包含version字段", "version" in d)
        result.record("version=2.0", d.get("version") == "2.0")
        result.record("skills数量=6", len(d.get("skills", {})) == 6)
    except Exception as e:
        result.record("序列化", False, str(e))


def test_summary_output(result: TestResult):
    """测试10：摘要输出"""
    logger.info("\n=== 测试10：摘要输出 ===")
    registry = get_registry()
    try:
        summary = registry.summary()
        result.record("摘要生成", isinstance(summary, str) and len(summary) > 100)
        result.record("摘要包含skill数量", "6个skill" in summary or "总计:" in summary)
    except Exception as e:
        result.record("摘要输出", False, str(e))


def main():
    logger.info("="*60)
    logger.info("P2.5-3 Skill协同端到端验证")
    logger.info(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

    result = TestResult()

    test_registry_init(result)
    test_skill_registration(result)
    test_capability_registration(result)
    test_capability_query(result)
    test_health_check(result)
    test_version_compatibility(result)
    test_entry_resolution(result)
    test_invoke_with_fallback(result)
    test_registry_serialization(result)
    test_summary_output(result)

    return result.summary()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
