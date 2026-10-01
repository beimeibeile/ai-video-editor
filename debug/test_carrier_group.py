"""测试航空母舰战斗群"""
import sys
import os

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))

from cap_carrier_group import CarrierGroup

cg = CarrierGroup()
cg.detect_all()

r = cg.get_combat_readiness()
print(f"\n战备: {r['deployed_count']}/{r['total_count']} 部署, {r['available_capabilities']}/{r['total_capabilities']} 能力可用")
print(f"合体模式: {'全员就位' if r['carrier_mode'] else '部分合体' if r['partial_mode'] else '仅母舰'}")

cg.save_status()
print("\n✅ 战斗群检测完成")
