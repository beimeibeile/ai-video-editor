"""测试模板系统"""
import sys
import os

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))

from cap_template_system import TemplateSystem

ts = TemplateSystem()
templates = ts.list_templates()
print(f"可用模板: {len(templates)}个")
for t in templates:
    print(f"  [{t['id']}] {t['name']} - {t['video_type']} - {t['default_duration']}s - {t['scene_count']}场景")

print()
tpl = ts.get_template('exploration_food')
print(f"探店美食模板场景结构:")
for s in tpl.scene_structure:
    print(f"  {s['type']}: {s['duration_ratio']*100:.0f}% - {s['content']}")

print()
print("✅ 模板系统导入和列表功能正常")
