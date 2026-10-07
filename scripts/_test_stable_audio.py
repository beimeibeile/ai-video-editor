"""测试Stable Audio 3音效生成"""
import sys
import os

SCRIPT_DIR = r"D:\DobaoWork_Project\Ai_Video_Editor\ai-video-editor-runtime\scripts"
sys.path.insert(0, SCRIPT_DIR)

from sfx_executor import SFXExecutor

executor = SFXExecutor()

print("=" * 60)
print("测试 Stable Audio 3 层3 AI生成")
print("=" * 60)

# 测试生成一个环境音（层3）
result = executor.generate("雨声", "normal", 3.0)
if result:
    print(f"\n✅ 生成成功!")
    print(f"  路径: {result['path']}")
    print(f"  评级: {result['rating']}")
    print(f"  时长: {result['duration']:.1f}s")
    print(f"  来源: {result['source']}")
    print(f"  缓存: {result['from_cache']}")
else:
    print("\n❌ 生成失败")

print("\n" + "=" * 60)
print("音效库统计:")
stats = executor.get_library_stats()
for k, v in stats.items():
    print(f"  {k}: {v}")
