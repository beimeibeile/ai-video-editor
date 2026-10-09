"""
坐标验证工具 v1.0
在剪映工程的4个角落+中心放置带坐标标注的测试图，
用户打开后可立即确认x/y轴方向、缩放比例、坐标范围。

使用方法：
    python coord_verify.py
    # 生成"坐标验证"工程，用剪映打开确认

验证点：
    - 左上角: x=-0.8, y=+0.8 (y正=上)
    - 右上角: x=+0.8, y=+0.8
    - 左下角: x=-0.8, y=-0.8
    - 右下角: x=+0.8, y=-0.8
    - 中心:   x=0,    y=0
    - 头像框: x=-0.653, y=+0.561 (1080x1920)
"""

import logging
logger = logging.getLogger(__name__)

import sys, os
sys.path.insert(0, r'C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor\scripts')
from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

OUT_DIR = r'D:\DobaoWork_Project\Ai_Video_Editor\coord_verify'
os.makedirs(OUT_DIR, exist_ok=True)


def make_label(text, color, size=300):
    """生成带文字的纯色测试图"""
    if not PIL_OK:
        return None
    img = Image.new('RGBA', (size, size), color + (255,))
    draw = ImageDraw.Draw(img)
    # 白色边框
    draw.rectangle([5, 5, size-5, size-5], outline=(255,255,255,255), width=4)
    # 文字
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((size-tw)//2, (size-th)//2), text, fill=(255,255,255,255), font=font)
    path = os.path.join(OUT_DIR, f"{text.replace(' ','_').replace('(','').replace(')','')}.png")
    img.save(path)
    return path


def main():
    logger.info("=" * 60)
    logger.info("坐标验证工具 v1.0")
    logger.info("=" * 60)

    # 生成6张测试图
    points = [
        ("左上 TL", (-0.8, 0.8), (200, 50, 50)),
        ("右上 TR", (0.8, 0.8), (50, 200, 50)),
        ("左下 BL", (-0.8, -0.8), (50, 50, 200)),
        ("右下 BR", (0.8, -0.8), (200, 200, 50)),
        ("中心 C", (0, 0), (200, 50, 200)),
        ("头像框 AV", (-0.653, 0.561), (50, 200, 200)),
    ]

    images = []
    for label, (x, y), color in points:
        path = make_label(label, color)
        if path:
            images.append((label, x, y, path))
            logger.info(f"  ✅ {label}: ({x}, {y}) -> {os.path.basename(path)}")

    if not images:
        logger.info("❌ Pillow不可用，无法生成测试图")
        return

    # 创建剪映工程
    logger.info(f"\n创建工程: 坐标验证 (1080x1920)")
    project = JyProject("坐标验证", width=1080, height=1920, overwrite=True)

    # 黑色背景
    bg_path = make_label("BG", (10, 10, 10), size=1080)
    project.add_media_safe(bg_path, start_time='0s', duration='5s', track_name='BG')

    # 每个点一张图，scale=0.25
    for label, x, y, path in images:
        seg = project.add_media_safe(path, start_time='0s', duration='5s', track_name=f'Point_{label.split()[0]}')
        seg.add_keyframe(draft.KeyframeProperty.position_x, 0, x)
        seg.add_keyframe(draft.KeyframeProperty.position_y, 0, y)
        seg.add_keyframe(draft.KeyframeProperty.uniform_scale, 0, 0.25)
        logger.info(f"  ✅ {label} 位置已设置")

    # 保存
    result = project.save()
    draft_path = result.get('draft_path', '')

    # 复制到D盘
    import shutil
    dst = r'D:\JianyingProDrafts\JianyingPro Drafts\坐标验证'
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(draft_path, dst)

    logger.info(f"\n✅ 坐标验证工程已创建:")
    logger.info(f"   {dst}")
    logger.info(f"\n验证清单:")
    logger.info(f"   1. 左上(红)应在屏幕左上角附近")
    logger.info(f"   2. 右上(绿)应在屏幕右上角附近")
    logger.info(f"   3. 左下(蓝)应在屏幕左下角附近")
    logger.info(f"   4. 右下(黄)应在屏幕右下角附近")
    logger.info(f"   5. 中心(紫)应在屏幕正中心")
    logger.info(f"   6. 头像框(青)应在左上角圆形头像框位置")
    logger.info(f"\n如果位置不对，说明坐标方向理解有误，需要调整转换公式。")


if __name__ == "__main__":
    main()
