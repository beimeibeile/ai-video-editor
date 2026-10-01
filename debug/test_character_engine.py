"""测试角色性格引擎"""
import sys
import os

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))

from cap_drama_engine import DramaEngine
from cap_character_engine import CharacterEngine

test_script = """测试剧本

内景 咖啡馆 - 日

小明
（紧张）
你好，我是小明，很高兴认识你。

小红
（微笑）
你好，我也很高兴认识你。

小明
（兴奋）
这家店的咖啡真的很棒！

小红
（开心）
是啊，我也很喜欢这里。

外景 公园 - 黄昏

小明
（坚定）
我想和你一起走下去。

小红
（感动）
我也是。
"""

drama = DramaEngine()
script = drama.parse_script(test_script)

engine = CharacterEngine()
print("\n=== 性格分析 ===")
personalities = engine.analyze_personality(script)

print("\n=== 关系图谱 ===")
relationships = engine.build_relationship_graph(script)

print("\n=== 一致性检查 ===")
issues = engine.check_consistency(script)

print("\n=== 角色弧光 ===")
arcs = engine.analyze_character_arc(script)

print("\n✅ 角色性格引擎测试完成")
