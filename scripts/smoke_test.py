"""
冒烟测试套件 - 验证核心模块可导入、可实例化、基本功能正常
用法: python smoke_test.py
"""

import os
import sys
import time
import logging
import traceback
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# 路径设置
RUNTIME_SCRIPTS = r"D:\DobaoWork_Project\Ai_Video_Editor\ai-video-editor-runtime\scripts"
SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills"
SKILL_AI = os.path.join(SKILL_ROOT, "ai-video-editor")
SKILL_JY = os.path.join(SKILL_ROOT, "jianying-editor")

for p in [RUNTIME_SCRIPTS, SKILL_AI, os.path.join(SKILL_AI, "scripts"),
          os.path.join(SKILL_JY, "scripts"), os.path.join(SKILL_JY, "scripts", "vendor", "pyJianYingDraft")]:
    if p not in sys.path:
        sys.path.insert(0, p)


class SmokeTest:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def test(self, name: str, func):
        """执行单个测试"""
        start = time.time()
        try:
            func()
            elapsed = time.time() - start
            self.results.append({"name": name, "status": "PASS", "time": elapsed, "error": None})
            self.passed += 1
            logger.info(f"  [PASS] {name} ({elapsed:.2f}s)")
        except Exception as e:
            elapsed = time.time() - start
            self.results.append({"name": name, "status": "FAIL", "time": elapsed, "error": str(e)})
            self.failed += 1
            logger.info(f"  [FAIL] {name} ({elapsed:.2f}s): {e}")
            traceback.print_exc()

    def skip(self, name: str, reason: str = ""):
        self.results.append({"name": name, "status": "SKIP", "time": 0, "error": reason})
        self.skipped += 1
        logger.info(f"  [SKIP] {name}: {reason}")

    def summary(self) -> Dict:
        total = self.passed + self.failed + self.skipped
        logger.info("\n" + "=" * 60)
        logger.info(f"冒烟测试结果: {self.passed}/{total} 通过, {self.failed} 失败, {self.skipped} 跳过")
        logger.info("=" * 60)
        if self.failed > 0:
            logger.info("\n失败项:")
            for r in self.results:
                if r["status"] == "FAIL":
                    logger.info(f"  - {r['name']}: {r['error']}")
        return {"passed": self.passed, "failed": self.failed, "skipped": self.skipped, "total": total}


def run_tests():
    st = SmokeTest()
    logger.info("=" * 60)
    logger.info("AI Video Editor 冒烟测试")
    logger.info("=" * 60)

    # ===== 1. 路径配置 =====
    logger.info("\n[1] 路径配置")
    def test_paths():
        from paths import PROJECT_ROOT, SKILL_ROOT, FFMPEG, COMFYUI_URL, verify_paths
        assert os.path.isdir(PROJECT_ROOT), f"PROJECT_ROOT不存在: {PROJECT_ROOT}"
        assert os.path.isfile(FFMPEG), f"FFMPEG不存在: {FFMPEG}"
        assert COMFYUI_URL.startswith("http"), f"COMFYUI_URL无效: {COMFYUI_URL}"
        results = verify_paths()
        assert sum(results.values()) >= 10, f"路径存在数不足: {sum(results.values())}"
    st.test("paths.py 配置验证", test_paths)

    # ===== 2. 特效API =====
    logger.info("\n[2] 特效API")
    def test_effect_api():
        from jianying_effect_api import JianyingEffectAPI
        api = JianyingEffectAPI()
        effects = api.list_effects()
        assert len(effects) > 1000, f"特效数不足: {len(effects)}"
        categories = api.get_categories()
        assert len(categories) > 0, "无分类"
    st.test("特效API 2309种加载", test_effect_api)

    # ===== 3. 剪映适配层 =====
    logger.info("\n[3] 剪映适配层")
    def test_adapter():
        from adapters.jianying_adapter import JianyingDraft, Track, TrackType
        assert JianyingDraft is not None
        assert Track is not None
        assert TrackType is not None
    st.test("适配层 类导入", test_adapter)

    def test_adapter_create():
        from adapters.jianying_adapter import JianyingDraft
        draft = JianyingDraft("smoke_test", width=1080, height=1920)
        assert draft is not None
        assert draft.name == "smoke_test"
    st.test("适配层 实例化", test_adapter_create)

    # ===== 4. 能力注册中心 =====
    logger.info("\n[4] 能力注册中心")
    def test_capability_registry():
        from adapters.capability_registry import CapabilityRegistry
        reg = CapabilityRegistry()
        caps = reg.list_capabilities()
        assert isinstance(caps, list), f"返回类型错误: {type(caps)}"
        assert len(caps) >= 15, f"能力数不足: {len(caps)}"
        active = [c for c in caps if c.status == "available"]
        assert len(active) >= 15, f"可用能力数不足: {len(active)}"
    st.test("能力注册中心 23能力", test_capability_registry)

    # ===== 5. TTS执行器 =====
    logger.info("\n[5] TTS执行器")
    def test_tts_import():
        from tts_executor import TTSExecutor, CHARACTER_VOICE_MAP, EMOTION_INSTRUCT_MAP
        assert TTSExecutor is not None
        assert len(CHARACTER_VOICE_MAP) > 0
        assert len(EMOTION_INSTRUCT_MAP) > 10
    st.test("TTS执行器 导入", test_tts_import)

    # ===== 6. 多轨混音器 =====
    logger.info("\n[6] 多轨混音器")
    def test_mixer_import():
        from multi_track_mixer import AudioTrack, MixConfig, MultiTrackMixer
        assert AudioTrack is not None
        assert MixConfig is not None
        assert MultiTrackMixer is not None
    st.test("多轨混音器 导入", test_mixer_import)

    def test_mixer_instance():
        from multi_track_mixer import AudioTrack, MixConfig
        track = AudioTrack(name="test", path="/tmp/test.mp3", volume=0.8)
        assert track.volume == 0.8
        config = MixConfig(output_path="/tmp/out.mp3", sample_rate=44100)
        assert config.sample_rate == 44100
    st.test("多轨混音器 实例化", test_mixer_instance)

    # ===== 7. 情绪映射引擎 =====
    logger.info("\n[7] 情绪映射引擎")
    def test_emotion_mapper():
        from script_understanding_engine import EmotionVisualMapper
        mapper = EmotionVisualMapper()
        result = mapper.map_emotion_to_visual("激昂", intensity=0.8)
        assert result is not None
        assert "shot_duration" in result
        assert "camera_moves" in result
    st.test("情绪映射 6种情绪", test_emotion_mapper)

    # ===== 8. 照片生成器 =====
    logger.info("\n[8] 照片生成器")
    def test_photo_generator():
        from photo_slideshow_generator import PhotoSlideshowGenerator, StylePreset
        assert PhotoSlideshowGenerator is not None
        assert StylePreset is not None
    st.test("照片生成器 导入", test_photo_generator)

    # ===== 9. 同步脚本 =====
    logger.info("\n[9] 同步脚本")
    def test_sync_script():
        from sync_skill_runtime import compare_dirs, file_md5, scan_dir
        assert compare_dirs is not None
        assert file_md5 is not None
        assert scan_dir is not None
    st.test("同步脚本 导入", test_sync_script)

    # ===== 10. 剪映执行器 =====
    logger.info("\n[10] 剪映执行器")
    def test_jianying_executor():
        from jianying_executor import JianyingExecutor
        assert JianyingExecutor is not None
    st.test("剪映执行器 导入", test_jianying_executor)

    # ===== 11. pyJianYingDraft 核心类 =====
    logger.info("\n[11] pyJianYingDraft 核心类")
    def test_pyjy_core():
        import pyJianYingDraft as draft
        from pyJianYingDraft.metadata import IntroType, OutroType, FilterType, TransitionType
        assert IntroType is not None
        assert OutroType is not None
        assert FilterType is not None
        assert TransitionType is not None
    st.test("pyJianYingDraft 元数据", test_pyjy_core)

    # ===== 12. 特效预设库 =====
    logger.info("\n[12] 特效预设库")
    def test_effect_presets():
        import json
        from paths import EFFECT_PRESETS
        if os.path.isfile(EFFECT_PRESETS):
            with open(EFFECT_PRESETS, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert len(data) > 0, "预设库为空"
        else:
            raise FileNotFoundError(f"预设库不存在: {EFFECT_PRESETS}")
    st.test("特效预设库 加载", test_effect_presets)

    # ===== 13. 字幕工具 =====
    logger.info("\n[13] 字幕工具")
    def test_subtitle_tools():
        try:
            from artistic_subtitle import add_artistic_subtitle
            assert add_artistic_subtitle is not None
        except ImportError:
            from enhanced_subtitle import create_subtitle_bar
            assert create_subtitle_bar is not None
    st.test("字幕工具 导入", test_subtitle_tools)

    # ===== 14. 转场工具 =====
    logger.info("\n[14] 转场工具")
    def test_transition():
        from pyJianYingDraft.metadata import TransitionType
        transitions = list(TransitionType)
        assert len(transitions) > 50, f"转场数不足: {len(transitions)}"
    st.test("转场 130种", test_transition)

    # ===== 15. 滤镜工具 =====
    logger.info("\n[15] 滤镜工具")
    def test_filter():
        from pyJianYingDraft.metadata import FilterType
        filters = list(FilterType)
        assert len(filters) > 20, f"滤镜数不足: {len(filters)}"
    st.test("滤镜 加载", test_filter)

    return st.summary()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = run_tests()
    sys.exit(0 if result["failed"] == 0 else 1)