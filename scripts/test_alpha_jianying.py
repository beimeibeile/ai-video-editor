"""
Alpha通道剪映兼容性测试
创建一个简单的剪映工程：
- 底层：纯色背景（绿色，便于观察透明区域）
- 上层：AlphaTest ProRes 4444透明背景视频
验证透明背景在剪映中是否正常显示
"""
import os
import sys
import json

# 路径配置
try:
    from paths import PATHS
    JY_SKILL = PATHS.get("jianying_skill_root", "")
except ImportError:
    _la = os.environ.get("LOCALAPPDATA", os.path.join(os.environ.get("USERPROFILE", r"C:\Users\Administrator"), "AppData", "Local"))
    JY_SKILL = os.path.join(_la, "Doubao", "User Data", "Default", ".doubao", "agent_mode", "workspace", ".user_skills", "jianying-editor")

if JY_SKILL:
    sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

from jy_wrapper import JyProject
from PIL import Image, ImageDraw

# 测试视频路径
ALPHA_VIDEO = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\remotion-controls-skill\out\alpha_test_simple.mov"

# 输出目录
OUTPUT_DIR = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\out"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_green_background():
    """创建绿色背景图（便于观察透明区域）"""
    bg_path = os.path.join(OUTPUT_DIR, "alpha_test_bg_green.png")
    img = Image.new("RGB", (1080, 1920), (0, 255, 0))  # 纯绿色
    draw = ImageDraw.Draw(img)
    # 添加网格线便于观察
    for x in range(0, 1080, 100):
        draw.line([(x, 0), (x, 1920)], fill=(0, 200, 0), width=1)
    for y in range(0, 1920, 100):
        draw.line([(0, y), (1080, y)], fill=(0, 200, 0), width=1)
    # 添加文字
    draw.text((540, 960), "BG", fill=(255, 255, 255))
    img.save(bg_path)
    print(f"  ✅ 绿色背景图: {bg_path}")
    return bg_path

def create_jianying_project():
    """创建剪映工程测试Alpha通道"""
    print("\n" + "=" * 60)
    print("Alpha通道剪映兼容性测试")
    print("=" * 60)

    # 1. 创建背景图
    print("\n[1] 创建测试背景...")
    bg_path = create_green_background()

    # 2. 创建剪映工程
    print("\n[2] 创建剪映工程...")
    project = JyProject(
        project_name="AlphaTest_ProRes4444",
        width=1080,
        height=1920,
        overwrite=True,
    )
    print(f"  ✅ 工程创建: {project.name}")

    # 3. 添加背景层（主轨）
    print("\n[3] 添加背景层（绿色）...")
    bg_seg = project.add_clip(
        media_path=bg_path,
        source_start=0,
        duration=3000000,  # 3秒
        target_start=0,
        track_name="VideoTrack",
    )
    print(f"  ✅ 背景层: {bg_seg.id if hasattr(bg_seg, 'id') else 'added'}")

    # 4. 添加Alpha视频层（画中画）
    print("\n[4] 添加AlphaTest视频层（透明背景）...")
    if os.path.exists(ALPHA_VIDEO):
        alpha_seg = project.add_clip(
            media_path=ALPHA_VIDEO,
            source_start=0,
            duration=3000000,  # 3秒
            target_start=0,
            track_name="VideoTrack2",
        )
        print(f"  ✅ Alpha视频层: {alpha_seg.id if hasattr(alpha_seg, 'id') else 'added'}")
        print(f"  视频路径: {ALPHA_VIDEO}")
        print(f"  视频大小: {os.path.getsize(ALPHA_VIDEO) / 1024 / 1024:.2f}MB")
    else:
        print(f"  ❌ Alpha视频不存在: {ALPHA_VIDEO}")
        return None

    # 5. 保存工程
    print("\n[5] 保存剪映工程...")
    result = project.save()
    draft_path = result.get("draft_path", "")
    print(f"  ✅ 工程保存: {draft_path}")

    # 6. 验证工程文件
    print("\n[6] 验证工程文件...")
    info_path = os.path.join(draft_path, "draft_info.json")
    content_path = os.path.join(draft_path, "draft_content.json")

    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            info = json.load(f)
        print(f"  ✅ draft_info.json存在")
        print(f"     时长: {info.get('duration', 'N/A')}")
        print(f"     画布: {info.get('canvas_config', info.get('width', 'N/A'))}")

    if os.path.exists(content_path):
        with open(content_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        tracks = content.get("tracks", [])
        print(f"  ✅ draft_content.json存在")
        print(f"     轨道数: {len(tracks)}")
        for i, track in enumerate(tracks):
            segs = track.get("segments", [])
            print(f"     轨道{i}: {len(segs)}个片段")

    # 7. 验证素材文件
    print("\n[7] 验证素材文件...")
    materials_dir = os.path.join(draft_path, "materials")
    if os.path.exists(materials_dir):
        materials = os.listdir(materials_dir)
        print(f"  ✅ 素材目录: {len(materials)}个文件")
        for m in materials:
            mpath = os.path.join(materials_dir, m)
            size = os.path.getsize(mpath) / 1024 / 1024
            print(f"     - {m}: {size:.2f}MB")
    else:
        print(f"  ⚠️ 素材目录不存在（素材可能在其他位置）")

    print("\n" + "=" * 60)
    print("测试完成！")
    print(f"请在剪映中打开工程: AlphaTest_ProRes4444")
    print("验证要点：")
    print("  1. 绿色背景是否正常显示")
    print("  2. 红色/蓝色方块是否正常移动")
    print("  3. 方块外区域是否透明（能看到绿色背景）")
    print("  4. 'Alpha Test'文字是否正常显示")
    print("=" * 60)

    return {
        "draft_path": draft_path,
        "bg_path": bg_path,
        "alpha_video": ALPHA_VIDEO,
    }

if __name__ == "__main__":
    result = create_jianying_project()
