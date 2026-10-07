"""批量验证迁移后文件的导入"""
import os, sys, traceback

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

FILES = [
    "jianying_executor",
    "artistic_subtitle",
    "enhanced_subtitle",
    "build_video",
    "clone_template",
    "photo_slideshow_generator",
    "multi_track_mixer",
    "tts_executor",
    "script_understanding_engine",
]

passed = 0
failed = 0
for mod in FILES:
    try:
        __import__(mod)
        print(f"  PASS: {mod}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {mod} -> {type(e).__name__}: {e}")
        traceback.print_exc()
        failed += 1

print(f"\n=== 导入验证: {passed} passed, {failed} failed ===")
