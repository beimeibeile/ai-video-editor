"""
复合片段工具模块 v2
支持在剪映草稿中创建复合片段（嵌套草稿结构）

复合片段存储格式：
1. materials.drafts 数组中添加 type="combination" 的条目（内含完整嵌套子草稿）
2. materials.videos 中添加 type="video"、extra_type_option=2 的代理视频素材
3. 主轨道片段 material_id 指向代理视频素材
4. 主片段 extra_material_refs 包含复合片段 id

使用方法：
    from compound_segment import create_compound, add_image_to_compound, save_with_compound
    info = create_compound(project, name="复合片段1")
    add_image_to_compound(info, "photo.jpg")
    save_with_compound(project, info)
"""

import logging
logger = logging.getLogger(__name__)


import os
import json
import uuid
import shutil
import hashlib
from typing import Dict, Any, Optional


def _generate_id() -> str:
    """生成UUID（大写，无连字符）"""
    return uuid.uuid4().hex.upper()


def _make_sub_draft(width: int, height: int, duration_us: int) -> Dict[str, Any]:
    """构建空的嵌套子草稿结构"""
    sub_draft_id = _generate_id()
    return {
        "canvas_config": {"height": height, "ratio": "original", "width": width},
        "color_space": 0,
        "config": {
            "adjust_max_index": 1, "attachment_info": [], "combination_max_index": 1,
            "export_range": None, "extract_audio_last_index": 1,
            "lyrics_recognition_id": "", "lyrics_sync": True, "lyrics_taskinfo": [],
            "maintrack_adsorb": False, "material_save_mode": 0,
            "multi_language_current": "none", "multi_language_list": [],
            "multi_language_main": "none", "multi_language_mode": "none",
            "original_sound_last_index": 1, "record_audio_last_index": 1,
            "sticker_max_index": 1, "subtitle_keywords_config": None,
            "subtitle_recognition_id": "", "subtitle_sync": True, "subtitle_taskinfo": [],
            "system_font_list": [], "video_mute": False, "zoom_info_params": None,
        },
        "cover": None, "create_time": 0, "duration": duration_us,
        "extra_info": None, "fps": 30.0, "free_render_index_mode_on": False,
        "group_container": None, "id": sub_draft_id, "keyframe_graph_list": [],
        "keyframes": {"adjusts": [], "audios": [], "effects": [], "filters": [],
                      "handwrites": [], "stickers": [], "texts": [], "videos": []},
        "last_modified_platform": {"app_id": 0, "app_source": "", "app_version": "",
                                    "device_id": "", "hard_disk_id": "", "mac_address": "",
                                    "os": "", "os_version": ""},
        "materials": {k: [] for k in [
            "ai_translates","audio_balances","audio_effects","audio_fades",
            "audio_track_indexes","audios","beats","canvases","chromas",
            "color_curves","digital_humans","drafts","effects","flowers",
            "green_screens","handwrites","hsl","images","log_color_wheels",
            "loudnesses","manual_deformations","masks","material_animations",
            "material_colors","multi_language_refs","placeholders","plugin_effects",
            "primary_color_wheels","realtime_denoises","shapes","smart_crops",
            "smart_relights","sound_channel_mappings","speeds","stickers",
            "tail_leaders","text_templates","texts","time_marks","transitions",
            "video_effects","video_trackings","videos","vocal_beautifys","vocal_separations"
        ]},
        "mutable_config": None, "name": "", "new_version": "110.0.0",
        "platform": {"app_id": 0, "app_source": "", "app_version": "",
                     "device_id": "", "hard_disk_id": "", "mac_address": "",
                     "os": "", "os_version": ""},
        "relationships": [], "render_index_track_mode_on": True,
        "retouch_cover": None, "source": "default", "static_cover_image_path": "",
        "time_marks": None, "tracks": [], "update_time": 0, "version": 360000,
    }


def _make_video_proxy(name: str, width: int, height: int, duration_us: int) -> Dict[str, Any]:
    """构建复合片段的代理视频素材（extra_type_option=2）"""
    return {
        "aigc_type": "none", "audio_fade": None, "cartoon_path": "",
        "category_id": "", "category_name": "", "check_flag": 63487,
        "crop": {"lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0,
                 "lower_right_y": 1.0, "upper_left_x": 0.0, "upper_left_y": 0.0,
                 "upper_right_x": 1.0, "upper_right_y": 0.0},
        "crop_ratio": "free", "crop_scale": 1.0, "duration": duration_us,
        "extra_type_option": 2, "formula_id": "", "freeze": None,
        "has_audio": False, "height": height, "id": _generate_id(),
        "intensifies_audio_path": "", "intensifies_path": "",
        "is_ai_generate_content": False, "is_copyright": True,
        "is_text_edit_overdub": False, "is_unified_beauty_mode": False,
        "local_id": "", "local_material_id": "", "material_id": "",
        "material_name": name, "material_url": "",
        "matting": {"flag": 0, "has_use_quick_brush": False,
                    "has_use_quick_eraser": False, "interactiveTime": [],
                    "path": "", "strokes": []},
        "media_path": "", "object_locked": None, "origin_material_id": "",
        "path": "", "picture_from": "none", "picture_set_category_id": "",
        "picture_set_category_name": "", "request_id": "",
        "reverse_intensifies_path": "", "reverse_path": "",
        "smart_motion": None, "source": 0, "source_platform": 0,
        "stable": {"matrix_path": "", "stable_level": 0,
                   "time_range": {"duration": 0, "start": 0}},
        "team_id": "", "type": "video",
        "video_algorithm": {"algorithms": [], "complement_frame_config": None,
                            "deflicker": None, "gameplay_configs": [],
                            "motion_blur_config": None, "noise_reduction": None,
                            "path": "", "quality_enhance": None, "time_range": None},
        "width": width,
    }


def _make_image_material(path: str, width: int, height: int, duration_us: int, name: str = "图片") -> Dict[str, Any]:
    """构建子草稿内的图片素材"""
    return {
        "category_id": "", "category_name": "", "check_flag": 63487,
        "crop": {"lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0,
                 "lower_right_y": 1.0, "upper_left_x": 0.0, "upper_left_y": 0.0,
                 "upper_right_x": 1.0, "upper_right_y": 0.0},
        "crop_ratio": "free", "crop_scale": 1.0,
        "duration": duration_us, "extra_type_option": 0,
        "formula_id": "", "height": height, "id": _generate_id(),
        "is_ai_generate_content": False, "is_copyright": True,
        "local_id": "", "local_material_id": "", "material_id": "",
        "material_name": name, "material_url": "",
        "path": path, "picture_from": "none",
        "picture_set_category_id": "", "picture_set_category_name": "",
        "request_id": "", "source": 0, "source_platform": 0,
        "team_id": "", "type": "photo", "width": width,
    }


def _make_segment(material_id: str, start_us: int, duration_us: int, render_index: int = 0) -> Dict[str, Any]:
    """构建子草稿内的片段"""
    speed_id = _generate_id()
    return {
        "adaptive_type": 0, "animation": None,
        "clip": {"alpha": 1.0, "brightness": 0.0, "contrast": 0.0,
                 "exposure": 0.0, "highlights": 0.0, "hue": 0.0,
                 "rotation": 0.0, "saturation": 0.0, "scale": 1.0,
                 "shadows": 0.0, "temperature": 0.0, "transform_x": 0.0,
                 "transform_y": 0.0, "vignette": 0.0},
        "common_keyframes": [],
        "enable_adjust": False, "enable_color_correct_adjust": False,
        "enable_color_curves": False, "enable_color_wheels": False,
        "enable_lut": False, "enable_smart_relight": False,
        "extra_material_refs": [speed_id],
        "id": _generate_id(), "intensifies_audio_path": "",
        "is_tone_modify": False, "material_id": material_id,
        "render_index": render_index, "reverse": False,
        "source_timerange": {"duration": duration_us, "start": start_us},
        "speed": 1.0, "target_timerange": {"duration": duration_us, "start": start_us},
        "uniform_scale": {"on": True, "value": 1.0},
        "volume": 1.0,
    }


def create_compound(
    project,
    name: str = "复合片段1",
    width: int = 1080,
    height: int = 1920,
    duration_us: int = 3000000,
) -> Dict[str, Any]:
    """
    创建复合片段（标记，保存时注入）

    Args:
        project: JyProject 实例
        name: 复合片段名称
        width: 画布宽
        height: 画布高
        duration_us: 持续时长（微秒）

    Returns:
        dict: 复合片段信息，用于后续添加素材和保存
    """
    combination_id = _generate_id()
    video_material = _make_video_proxy(name, width, height, duration_us)
    sub_draft = _make_sub_draft(width, height, duration_us)

    combination = {
        "category_id": "", "category_name": "",
        "combination_id": _generate_id(),
        "draft": sub_draft,
        "formula_id": "", "id": combination_id, "name": "",
        "precompile_combination": False, "type": "combination",
    }

    info = {
        "combination_id": combination_id,
        "video_material_id": video_material["id"],
        "name": name,
        "width": width,
        "height": height,
        "duration_us": duration_us,
        "combination": combination,
        "video_material": video_material,
        "sub_draft": sub_draft,
        "_pending_images": [],
    }

    if not hasattr(project, '_compound_patches'):
        project._compound_patches = []
    project._compound_patches.append(info)

    logger.info(f"  ✅ 复合片段已创建: {name} (id={combination_id[:8]}...)")
    return info


def add_image_to_compound(
    compound_info: Dict[str, Any],
    image_path: str,
    start_us: int = 0,
    duration_us: int = None,
    track_index: int = 0,
) -> Optional[str]:
    """
    向复合片段内部添加图片素材

    Args:
        compound_info: create_compound 返回的信息
        image_path: 图片文件路径
        start_us: 起始时间（微秒）
        duration_us: 持续时长（微秒，None则用复合片段时长）
        track_index: 轨道索引

    Returns:
        片段id或None
    """
    if duration_us is None:
        duration_us = compound_info["duration_us"]

    compound_info["_pending_images"].append({
        "path": image_path,
        "start_us": start_us,
        "duration_us": duration_us,
        "track_index": track_index,
    })
    logger.info(f"  ✅ 已标记添加图片到复合片段: {os.path.basename(image_path)}")
    return True


def inject_compound_to_draft(draft_path: str, patches: list) -> bool:
    """
    将复合片段注入到草稿文件（在 project.save() 后调用）

    Args:
        draft_path: 草稿目录路径
        patches: 复合片段补丁列表（create_compound 返回的 info 列表）

    Returns:
        bool: 是否成功
    """
    if not patches:
        return True

    content_file = os.path.join(draft_path, "draft_content.json")
    info_file = os.path.join(draft_path, "draft_info.json")

    if not os.path.exists(content_file):
        if os.path.exists(info_file):
            shutil.copy2(info_file, content_file)
        else:
            logger.info(f"❌ 草稿文件不存在: {draft_path}")
            return False

    try:
        with open(content_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        materials = data.setdefault("materials", {})
        drafts = materials.setdefault("drafts", [])
        videos = materials.setdefault("videos", [])

        mat_dir = os.path.join(draft_path, "materials")
        os.makedirs(mat_dir, exist_ok=True)

        for patch in patches:
            combination = patch["combination"]
            video_material = patch["video_material"]
            sub_draft = patch["sub_draft"]

            # 处理待添加的图片
            for img_info in patch.get("_pending_images", []):
                src_path = img_info["path"]
                if not os.path.exists(src_path):
                    logger.info(f"  ⚠️  图片不存在: {src_path}")
                    continue

                # 复制到草稿目录
                digest = hashlib.md5(src_path.encode("utf-8")).hexdigest()
                ext = os.path.splitext(src_path)[1]
                staged = os.path.join(mat_dir, f"{digest}{ext}")
                if not os.path.exists(staged):
                    shutil.copy2(src_path, staged)

                # 添加图片素材到子草稿
                img_mat = _make_image_material(
                    staged, patch["width"], patch["height"],
                    img_info["duration_us"], os.path.basename(src_path)
                )
                sub_draft["materials"]["images"].append(img_mat)

                # 添加片段到子草稿轨道
                seg = _make_segment(
                    img_mat["id"], img_info["start_us"],
                    img_info["duration_us"], render_index=img_info["track_index"]
                )

                # 确保轨道存在
                track_idx = img_info["track_index"]
                while len(sub_draft["tracks"]) <= track_idx:
                    sub_draft["tracks"].append({
                        "id": _generate_id(),
                        "render_index": len(sub_draft["tracks"]),
                        "segments": [],
                        "type": "video",
                    })
                sub_draft["tracks"][track_idx]["segments"].append(seg)

            # 添加复合片段到 materials.drafts
            drafts.append(combination)
            # 添加代理视频素材到 materials.videos
            videos.append(video_material)

            # 修改主轨道第一个片段指向复合片段
            if data.get("tracks") and data["tracks"][0].get("segments"):
                main_seg = data["tracks"][0]["segments"][0]
                main_seg["material_id"] = video_material["id"]
                main_seg["extra_material_refs"] = [combination["id"]]
                main_seg["source_timerange"] = {"duration": patch["duration_us"], "start": 0}
                main_seg["target_timerange"] = {"duration": patch["duration_us"], "start": 0}

        with open(content_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 同步 draft_info.json
        if os.path.exists(info_file):
            with open(info_file, "r", encoding="utf-8") as f:
                idata = json.load(f)
            idrafts = idata.setdefault("materials", {}).setdefault("drafts", [])
            ivideos = idata["materials"].setdefault("videos", [])
            for patch in patches:
                idrafts.append(patch["combination"])
                ivideos.append(patch["video_material"])
            if idata.get("tracks") and idata["tracks"][0].get("segments"):
                imseg = idata["tracks"][0]["segments"][0]
                imseg["material_id"] = patches[0]["video_material"]["id"]
                imseg["extra_material_refs"] = [patches[0]["combination"]["id"]]
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(idata, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✅ 已注入 {len(patches)} 个复合片段到草稿")
        return True
    except Exception as e:
        logger.error(f"❌ 注入复合片段失败: {e}")
        import traceback
        traceback.print_exc()
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
    logger.info("=" * 60)
    logger.info("复合片段工具模块 v2")
    logger.info("=" * 60)
    logger.info("\n使用方法:")
    logger.info("  info = create_compound(project, name='复合片段1')")
    logger.info("  add_image_to_compound(info, 'photo.jpg')")
    logger.info("  save_with_compound(project)")
    logger.info("\n核心函数:")
    logger.info("  create_compound() - 创建复合片段")
    logger.info("  add_image_to_compound() - 向复合片段内添加图片")
    logger.info("  inject_compound_to_draft() - 注入到草稿JSON")
    logger.info("  save_with_compound() - 保存并自动注入")
