"""
特效库批量注册脚本
将scripts目录下已有的特效模块批量注册到effects/index.json
"""

import logging
logger = logging.getLogger(__name__)

import json
import os

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
INDEX_PATH = os.path.join(SKILL_ROOT, "effects", "index.json")

# 待注册的特效列表
NEW_EFFECTS = [
    {
        "id": "text_wipe",
        "name": "羽化擦开文字",
        "category": "text",
        "module": "scripts/text_wipe_animation.py",
        "source": "抖音教程-文字排版003",
        "difficulty": "medium",
        "status": "verified",
        "description": "主文字从左向右擦开+副文字从右向左擦开，蒙版羽化边缘，配合延迟节奏感",
        "tags": ["文字擦开", "蒙版", "羽化", "入场", "节奏感"],
        "api": ["create_text_wipe_animation", "add_text_wipe_to_project"]
    },
    {
        "id": "text_bg_slide",
        "name": "文字背景块滑入",
        "category": "text",
        "module": "scripts/text_background_slide.py",
        "source": "抖音教程-文字排版004",
        "difficulty": "easy",
        "status": "verified",
        "description": "纯色背景块从左/右/上/下滑入+文字叠加，4种滑入方向，支持延迟淡入",
        "tags": ["背景块", "滑入", "文字", "标题", "强调"],
        "api": ["create_text_bg_slide", "add_text_bg_slide_to_project"]
    },
    {
        "id": "character_card",
        "name": "人物介绍卡v2",
        "category": "combo",
        "module": "scripts/character_card.py",
        "source": "狂飙人物介绍升级版",
        "difficulty": "medium",
        "status": "verified",
        "description": "角色照片+红色边框淡入放大+爆闪灯+名字标签上部，4种预设风格",
        "tags": ["人物卡", "角色介绍", "爆闪", "边框", "名字"],
        "api": ["add_character_card", "create_character_card_demo", "CARD_STYLES"]
    },
    {
        "id": "date_badge",
        "name": "圆形日期标签",
        "category": "text",
        "module": "scripts/circular_date_badge.py",
        "source": "抖音教程-日期标签",
        "difficulty": "easy",
        "status": "verified",
        "description": "圆形/圆角日期标签，支持年月日分层显示，弹入动画",
        "tags": ["日期", "标签", "圆形", "时间", "弹入"],
        "api": ["add_date_badge", "create_date_badge_demo"]
    },
    {
        "id": "blinds_transition",
        "name": "百叶窗分屏展开",
        "category": "transitions",
        "module": "scripts/blinds_transition.py",
        "source": "抖音教程-百叶窗特效",
        "difficulty": "medium",
        "status": "verified",
        "description": "多轨道色块依次展开形成百叶窗效果，支持水平/垂直方向，转场专用",
        "tags": ["百叶窗", "分屏", "转场", "展开", "多轨道"],
        "api": ["create_blinds_transition", "add_blinds_to_project"]
    },
    {
        "id": "stack_intro",
        "name": "堆叠开场",
        "category": "combo",
        "module": "scripts/stack_intro.py",
        "source": "特效组合",
        "difficulty": "medium",
        "status": "verified",
        "description": "多层色块堆叠入场+标题文字，层次感强，适合科技/商务类视频开场",
        "tags": ["堆叠", "开场", "层次", "科技", "商务"],
        "api": ["create_stack_intro", "add_stack_intro_to_project"]
    },
    {
        "id": "camera_moves",
        "name": "镜头运动预设",
        "category": "visual",
        "module": "scripts/camera_moves.py",
        "source": "剪映关键帧封装",
        "difficulty": "easy",
        "status": "verified",
        "description": "推/拉/摇/移/跟5种镜头运动关键帧预设，支持速度曲线调节",
        "tags": ["镜头运动", "推拉摇移", "关键帧", "Ken Burns", "运镜"],
        "api": ["add_camera_move", "create_camera_move_demo", "CAMERA_PRESETS"]
    },
    {
        "id": "artistic_subtitle",
        "name": "艺术字幕",
        "category": "text",
        "module": "scripts/artistic_subtitle.py",
        "source": "抖音教程-艺术字幕",
        "difficulty": "medium",
        "status": "verified",
        "description": "渐变文字+描边+阴影+入场动画组合，适合电影感/文艺类视频字幕",
        "tags": ["艺术字幕", "渐变", "描边", "电影感", "文艺"],
        "api": ["add_artistic_subtitle", "create_artistic_subtitle_demo"]
    },
    {
        "id": "pip_layouts",
        "name": "画中画布局",
        "category": "visual",
        "module": "scripts/pip_layouts.py",
        "source": "剪映画中画封装",
        "difficulty": "easy",
        "status": "verified",
        "description": "6种画中画布局预设（左右分屏/上下分屏/画中画小窗/九宫格等），自动计算位置缩放",
        "tags": ["画中画", "分屏", "布局", "多画面", "对比"],
        "api": ["add_pip_layout", "create_pip_demo", "PIP_LAYOUTS"]
    },
    {
        "id": "blender_particles",
        "name": "Blender粒子背景",
        "category": "visual",
        "module": "scripts/blender_effects.py",
        "source": "Blender 3D特效",
        "difficulty": "hard",
        "status": "verified",
        "description": "Blender渲染粒子背景视频（星空/雪花/光斑/烟花/霓虹5种预设），带发光效果",
        "tags": ["Blender", "粒子", "背景", "3D", "星空", "雪花"],
        "api": ["create_particle_background", "PARTICLE_PRESETS"],
        "dependencies": ["blender"]
    },
    {
        "id": "blender_text_intro",
        "name": "Blender 3D文字入场",
        "category": "combo",
        "module": "scripts/blender_effects.py",
        "source": "Blender 3D特效",
        "difficulty": "hard",
        "status": "verified",
        "description": "Blender渲染3D立体文字入场动画（缩放/滑动/淡入/旋转4种风格），带粒子+发光",
        "tags": ["Blender", "3D文字", "入场", "立体", "发光"],
        "api": ["create_text_intro"],
        "dependencies": ["blender"]
    },
    {
        "id": "blender_light_sweep",
        "name": "Blender光线扫描",
        "category": "visual",
        "module": "scripts/blender_effects.py",
        "source": "Blender 3D特效",
        "difficulty": "hard",
        "status": "verified",
        "description": "Blender渲染光线扫过效果，适合产品展示/科技感视频的高光转场",
        "tags": ["Blender", "光线扫描", "高光", "产品展示", "科技"],
        "api": ["create_light_sweep"],
        "dependencies": ["blender"]
    },
    {
        "id": "mask_keyframe_tool",
        "name": "蒙版关键帧工具",
        "category": "tool",
        "module": "scripts/mask_keyframe.py",
        "source": "剪映5.9草稿逆向",
        "difficulty": "hard",
        "status": "verified",
        "description": "蒙版关键帧标记+注入工具，支持大小/位置/旋转/羽化/圆角6种属性，10种展开方向",
        "tags": ["蒙版", "关键帧", "工具", "逆向", "注入"],
        "api": ["apply_mask_keyframe", "apply_mask_expand", "save_with_mask_keyframes", "inject_mask_keyframes_to_draft"]
    },
    {
        "id": "compound_segment",
        "name": "复合片段工具",
        "category": "tool",
        "module": "scripts/compound_segment.py",
        "source": "剪映5.9草稿逆向",
        "difficulty": "hard",
        "status": "verified",
        "description": "将多轨道片段合并为复合片段，支持嵌套/解组，适合复杂特效的组织管理",
        "tags": ["复合片段", "嵌套", "工具", "分组", "组织"],
        "api": ["create_compound_segment", "decompose_segment"]
    },
    {
        "id": "auto_beat",
        "name": "自动节拍卡点",
        "category": "tool",
        "module": "scripts/auto_beat.py",
        "source": "音频分析封装",
        "difficulty": "medium",
        "status": "partial",
        "description": "分析音频节拍自动生成卡点时间点，配合转场/特效实现自动踩点",
        "tags": ["节拍", "卡点", "音频分析", "自动", "踩点"],
        "api": ["detect_beats", "apply_beat_transitions"],
        "dependencies": ["ffmpeg"]
    },
    {
        "id": "enhanced_subtitle",
        "name": "增强字幕",
        "category": "text",
        "module": "scripts/enhanced_subtitle.py",
        "source": "剪映字幕增强",
        "difficulty": "easy",
        "status": "verified",
        "description": "批量字幕导入+样式统一+逐字动画+双语字幕支持",
        "tags": ["增强字幕", "批量", "双语", "逐字", "样式"],
        "api": ["import_subtitles", "apply_subtitle_style", "add_bilingual_subtitles"]
    },
    {
        "id": "blender_transition",
        "name": "Blender转场遮罩",
        "category": "transitions",
        "module": "scripts/blender_effects.py",
        "source": "Blender 3D特效",
        "difficulty": "hard",
        "status": "verified",
        "description": "Blender渲染转场遮罩视频（淡入/左滑/右滑/放大/缩小5种风格），可作为转场素材",
        "tags": ["Blender", "转场", "遮罩", "3D", "滑动"],
        "api": ["create_transition"],
        "dependencies": ["blender"]
    },
]

# 新增分类
NEW_CATEGORIES = {
    "tool": "工具类",
}


def main():
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        index = json.load(f)

    existing_ids = {e['id'] for e in index.get('effects', [])}
    added = 0
    skipped = 0

    for effect in NEW_EFFECTS:
        if effect['id'] in existing_ids:
            logger.warning(f"  ⏭ 跳过(已存在): {effect['id']}")
            skipped += 1
        else:
            index['effects'].append(effect)
            logger.info(f"  ✅ 新增: {effect['id']} - {effect['name']}")
            added += 1

    # 更新分类
    for cat_id, cat_name in NEW_CATEGORIES.items():
        if cat_id not in index.get('categories', {}):
            index['categories'][cat_id] = cat_name
            logger.info(f"  📁 新增分类: {cat_id} - {cat_name}")

    index['last_updated'] = '2026-10-02'
    index['version'] = '1.4'

    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    total = len(index['effects'])
    logger.info(f"\n✅ 特效库更新完成:")
    logger.info(f"   新增: {added}")
    logger.warning(f"   跳过: {skipped}")
    logger.info(f"   总计: {total}个特效")
    logger.info(f"   分类: {list(index['categories'].keys())}")


if __name__ == "__main__":
    main()
