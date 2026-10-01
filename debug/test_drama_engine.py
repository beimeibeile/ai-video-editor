"""测试影视剧剧本引擎"""
import sys
import os

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))

from cap_drama_engine import DramaEngine

test_script = """测试剧本
作者: 测试编剧
类型: 剧情

内景 咖啡馆 - 日

小明
（紧张）
你好，我是小明。

小红
（微笑）
你好，很高兴认识你。

（两人握手，气氛融洽）

外景 公园 - 黄昏

小明
这里的风景真美。

小红
是啊，我们常来这里散步。
"""

engine = DramaEngine()
script = engine.parse_script(test_script)

print("\n角色分析:")
for name, char in script.characters.items():
    print(f"  {name}: {char.line_count}句台词, {char.scene_count}个场景, 首次出场:{char.first_appearance}")

shots = engine.generate_storyboard(script)
print(f"\n分镜数: {len(shots)}")
for s in shots[:5]:
    print(f"  {s.shot_id}: {s.shot_size} {s.camera_move} - {s.description[:30]} ({s.duration:.1f}s)")

print("\n✅ 剧本引擎测试完成")
