"""
复合片段工具模块
支持在剪映草稿中创建复合片段（嵌套草稿结构）

复合片段存储格式：
1. materials.drafts 数组中添加 type="combination" 的条目
2. 包含完整嵌套子草稿（draft字段，内含tracks/materials）
3. materials.videos 中添加 type="video"、name="复合片段N" 的条目
4. 主轨道片段 material_id 指向该视频条目
5. 主片段 extra_material_refs 包含复合片段 id

使用方法：
    from compound_segment import create_compound_segment
    create_compound_segment(project, segments, name="复合片段1")
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional


def _generate_id() -> str:
    """生成UUID（大写，无连字符）"""
    return uuid.uuid4().hex.upper()


def create_compound_segment(
    project,
    name: str = "复合片段1",
    width: int = 1080,
    height: int = 1920,
    duration_us: int = 3000000,
) -> Dict[str, Any]:
    """
    创建空复合片段（标记，保存时注入）

    Args:
        project: JyProject 实例
        name: 复合片段名称
        width: 画布宽
        height: 画布高
        duration_us: 持续时长（微秒）

    Returns:
        dict: 复合片段信息（id, video_material_id, combination_id）
    """
    combination_id = _generate_id()
    video_material_id = _generate_id()
    draft_id = _generate_id()

    # 构建嵌套子草稿结构
    sub_draft = {
        "canvas_config": {"height": height, "ratio": "original", "width": width},
        "color_space": 0,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": False,
            "material_save_mode": 0,
            "multi_language_current": "none",
            "multi_language_list": [],
            "multi_language_main": "none",
            "multi_language_mode": "none",
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_keywords_config": None,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "video_mute": False,
            "zoom_info_params": None,
        },
        "cover": None,
        "create_time": 0,
        "duration": duration_us,
        "extra_info": None,
        "fps": 30.0,
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": draft_id,
        "keyframe_graph_list": [],
        "keyframes": {
            "adjusts": [], "audios": [], "effects": [], "filters": [],
            "handwrites": [], "stickers": [], "texts": [], "videos": [],
        },
        "last_modified_platform": {
            "app_id": 0, "app_source": "", "app_version": "",
            "device_id": "", "hard_disk_id": "", "mac_address": "",
            "os": "", "os_version": "",
        },
        "materials": {
            "ai_translates": [], "audio_balances": [], "audio_effects": [],
            "audio_fades": [], "audio_track_indexes": [], "audios": [],
            "beats": [], "canvases": [], "chromas": [], "color_curves": [],
            "digital_humans": [], "drafts": [], "effects": [], "flowers": [],
            "green_screens": [], "handwrites": [], "hsl": [], "images": [],
            "log_color_wheels": [], "loudnesses": [], "manual_deformations": [],
            "masks": [], "material_animations": [], "material_colors": [],
            "multi_language_refs": [], "placeholders": [], "plugin_effects": [],
            "primary_color_wheels": [], "realtime_denoises": [], "shapes": [],
            "smart_crops": [], "smart_relights": [], "sound_channel_mappings": [],
            "speeds": [], "stickers": [], "tail_leaders": [], "text_templates": [],
            "texts": [], "time_marks": [], "transitions": [], "video_effects": [],
            "video_trackings": [], "videos": [], "vocal_beautifys": [],
            "vocal_separations": [],
        },
        "mutable_config": None,
        "name": "",
        "new_version": "110.0.0",
        "platform": {
            "app_id": 0, "app_source": "", "app_version": "",
            "device_id": "", "hard_disk_id": "", "mac_address": "",
            "os": "", "os_version": "",
        },
        "relationships": [],
        "render_index_track_mode_on": True,
        "retouch_cover": None,
        "source": "default",
        "static_cover_image_path": "",
        "time_marks": None,
        "tracks": [],
        "update_time": 0,
        "version": 360000,
    }

    # 复合片段条目（materials.drafts）
    combination = {
        "category_id": "",
        "category_name": "",
        "combination_id": _generate_id(),
        "draft": sub_draft,
        "formula_id": "",
        "id": combination_id,
        "name": "",
        "precompile_combination": False,
        "type": "combination",
    }

    # 复合片段对应的视频素材（materials.videos）
    video_material = {
        "aigc_type": "none",
        "audio_fade": None,
        "cartoon_path": "",
        "category_id": "",
        "category_name": "",
        "check_flag": 63487,
        "crop": {
            "lower_left_x": 0.0, "lower_left_y": 1.0,
            "lower_right_x": 1.0, "lower_right_y": 1.0,
            "upper_left_x": 0.0, "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0,
        },
        "crop_ratio": "free",
        "crop_scale": 1.0,
        "duration": duration_us,
        "extra_type_option": 2,
        "formula_id": "",
        "freeze": None,
        "has_audio": False,
        "height": height,
        "id": video_material_id,
        "intensifies_audio_path": "",
        "intensifies_path": "",
        "is_ai_generate_content": False,
        "is_copyright": True,
        "is_text_edit_overdub": False,
        "is_unified_beauty_mode": False,
        "local_id": "",
        "local_material_id": "",
        "material_id": "",
        "material_name": name,
        "material_url": "",
        "matting": {
            "flag": 0, "has_use_quick_brush": False,
            "has_use_quick_eraser": False,
            "interactiveTime": [], "path": "", "strokes": [],
        },
        "media_path": "",
        "object_locked": None,
        "origin_material_id": "",
        "path": "",
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "request_id": "",
        "reverse_intensifies_path": "",
        "reverse_path": "",
        "smart_motion": None,
        "source": 0,
        "source_platform": 0,
        "stable": {
            "matrix_path": "", "stable_level": 0,
            "time_range": {"duration": 0, "start": 0},
        },
        "team_id": "",
        "type": "video",
        "video_algorithm": {
            "algorithms": [], "complement_frame_config": None,
            "deflicker": None, "gameplay_configs": [],
            "motion_blur_config": None, "noise_reduction": None,
            "path": "", "quality_enhance": None, "time_range": None,
        },
        "width": width,
    }

    # 标记需要注入
    if not hasattr(project, '_compound_patches'):
        project._compound_patches = []
    project._compound_patches.append({
        "combination": combination,
        "video_material": video_material,
        "name": name,
        "duration_us": duration_us,
    })

    return {
        "combination_id": combination_id,
        "video_material_id": video_material_id,
        "draft_id": draft_id,
        "name": name,
    }


def add_media_to_compound(
    compound_info: Dict[str, Any],
    media_path: str,
    start_us: int = 0,
    duration_us: int = 3000000,
    track_type: str = "video",
) -> bool:
    """
    向复合片段中添加媒体（需要在保存前调用，修改 compound_info 中的子草稿）

    注意：此函数目前只支持标记，实际注入在 save_with_compound 中完成。
    更复杂的复合片段编辑建议直接操作 JSON。

    Args:
        compound_info: create_compound_segment 返回的信息
        media_path: 媒体文件路径
        start_us: 起始时间（微秒）
        duration_us: 持续时长（微秒）
        track_type: 轨道类型（video/sticker/text）

    Returns:
        bool: 是否成功
    """
    # 标记需要添加的媒体
    if '_pending_media' not in compound_info:
        compound_info['_pending_media'] = []
    compound_info['_pending_media'].append({
        "media_path": media_path,
        "start_us": start_us,
        "duration_us": duration_us,
        "track_type": track_type,
    })
    return True


def inject_compound_to_draft(draft_path: str, patches: list) -> bool:
    """
    将复合片段注入到草稿文件（在 project.save() 后调用）

    Args:
        draft_path: 草稿目录路径
        patches: 复合片段补丁列表

    Returns:
        bool: 是否成功
    """
    if not patches:
        return True

    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        info_file = os.path.join(draft_path, "draft_info.json")
        if os.path.exists(info_file):
            import shutil
            shutil.copy2(info_file, content_file)
        else:
            print(f"❌ 草稿文件不存在: {draft_path}")
            return False

    try:
        with open(content_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        materials = data.setdefault("materials", {})
        drafts = materials.setdefault("drafts", [])
        videos = materials.setdefault("videos", [])

        for patch in patches:
            combination = patch["combination"]
            video_material = patch["video_material"]

            # 添加复合片段到 materials.drafts
            drafts.append(combination)

            # 添加视频素材到 materials.videos
            videos.append(video_material)

        with open(content_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 已注入 {len(patches)} 个复合片段到草稿")
        return True
    except Exception as e:
        print(f"❌ 注入复合片段失败: {e}")
        return False


def save_with_compound(project) -> dict:
    """
    保存工程并自动注入复合片段

    Args:
        project: JyProject 实例

    Returns:
        dict: 保存结果
    """
    result = project.save()
    draft_path = result.get("draft_path", "")

    patches = getattr(project, '_compound_patches', [])
    if patches and draft_path:
        inject_compound_to_draft(draft_path, patches)
        result["compound_injected"] = len(patches)
    else:
        result["compound_injected"] = 0

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("复合片段工具模块")
    print("=" * 60)
    print("\n使用方法:")
    print("  info = create_compound_segment(project, name='复合片段1')")
    print("  # 向主轨道添加引用复合片段的片段（material_id=info['video_material_id']）")
    print("  save_with_compound(project)")
    print("\n注意: 复合片段内部的媒体编辑需要直接操作子草稿JSON")
