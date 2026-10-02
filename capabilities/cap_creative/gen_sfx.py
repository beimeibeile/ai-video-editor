import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sound_engine import SoundEngine
engine = SoundEngine()
out = os.path.join(os.path.dirname(__file__), "audio_output", "fanshen_v4")
os.makedirs(out, exist_ok=True)
sfx_list = [
    ("sfx_keyboard", "keyboard"),
    ("sfx_mouse", "mouse_click"),
    ("sfx_notification", "notification"),
    ("sfx_applause", "applause"),
    ("sfx_whoosh", "whoosh"),
]
for name, stype in sfx_list:
    r = engine.generate_sfx_placeholder(sfx_type=stype, output_file=os.path.join(out, name + ".wav"))
    status = "OK" if r else "FAIL"
    print(f"  {name}: {status}")
files = os.listdir(out)
n_count = len([f for f in files if f.startswith("n")])
d_count = len([f for f in files if f.startswith("d")])
bgm_count = len([f for f in files if f.startswith("bgm")])
sfx_count = len([f for f in files if f.startswith("sfx")])
print(f"总文件: {len(files)} (旁白{n_count} 对话{d_count} BGM{bgm_count} SFX{sfx_count})")
print("SFX生成完成")
