"""
P3剪映指令执行器（完整版v2）
正确使用pyJianYingDraft API：直接传枚举类型
"""
import os
import sys
import json
import logging

logger = logging.getLogger(__name__)

SCRIPTS = r"D:\DobaoWork_Project\Ai_Video_Editor\ai-video-editor-runtime\scripts"
sys.path.insert(0, SCRIPTS)

JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

from jy_wrapper import JyProject
from paths import get_all_paths
# 必须使用与jy_wrapper一致的导入方式（import pyJianYingDraft），
# 否则会导致模块加载两次、类不匹配、isinstance检查失败
import pyJianYingDraft as draft
from pyJianYingDraft import (
    FilterType, VideoSceneEffectType,
    IntroType, OutroType, TransitionType,
)
from pyJianYingDraft.keyframe import KeyframeProperty

# 使用已验证的特效API
_AI_SCRIPTS = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\ai-video-editor\scripts"
if _AI_SCRIPTS not in sys.path:
    sys.path.insert(0, _AI_SCRIPTS)
from jianying_effect_api import JianyingEffectAPI
_effect_api = JianyingEffectAPI()

# P3特效名称→实际存在的剪映特效名称映射
SCENE_EFFECT_MAP = {
    "暖阳": "夕阳",
    "清新": "丁达尔光线",
    "复古": "复古发光",
    "日系": "光晕",
    "赛博朋克": "霓虹光线",
    "赛博": "霓虹光线",
    "梦幻": "光晕",
    "电影感": "电影感",  # 已存在
}

def resolve_scene_effect(name: str) -> str:
    """解析P3特效名称为实际存在的剪映特效名称"""
    mapped = SCENE_EFFECT_MAP.get(name, name)
    try:
        VideoSceneEffectType.from_name(mapped)
        return mapped
    except ValueError:
        return None

# P3动画名称→实际存在的剪映动画名称映射
ANIMATION_NAME_MAP = {
    "淡入": "渐显",
    "淡出": "渐隐",
    "放大": "动感放大",
    "缩小": "动感缩小",
    "向上滑入": "向上滑动",
    "向下滑入": "向下滑动",
    "向左滑入": "向左滑动",
    "向右滑入": "向右滑动",
    "旋转进入": "旋转",
    "缩放": "动感放大",
}

def resolve_animation_name(name: str, anim_type: str) -> str:
    """解析P3动画名称为实际存在的剪映动画名称"""
    mapped = ANIMATION_NAME_MAP.get(name, name)
    try:
        if anim_type == 'in':
            IntroType.from_name(mapped)
        elif anim_type == 'out':
            OutroType.from_name(mapped)
        return mapped
    except ValueError:
        return None


def build_full_project(result_path: str, output_name: str = "p3_full_test"):
    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ji = data.get('jianying_instructions', {})
    segments = data.get('segments', [])

    logger.info(f"=== P3完整工程构建 v2 ===")
    logger.info(f"素材:{len(ji.get('tracks',[]))} 特效:{len(ji.get('effects',[]))} 动画:{len(ji.get('animations',[]))} 转场:{len(ji.get('transitions',[]))}")

    paths = get_all_paths()
    drafts_root = paths.get('JIANYING_DRAFTS_ROOT', r"D:\JianyingProDrafts\JianyingPro Drafts")

    project = JyProject(project_name=output_name, width=720, height=1280, drafts_root=drafts_root)

    colors = {'calm': (100,150,200), 'happy': (255,220,100), 'excited': (255,100,100), 'warm': (255,180,120)}

    # 1. 添加素材
    track_infos = ji.get('tracks', [])
    segment_objects = []
    current_time = 0.0
    for i, track in enumerate(track_infos):
        start = float(track.get('start', current_time))
        duration = float(track.get('duration', 4.0))
        seg_idx = track.get('segment_index', i)
        emotion = segments[seg_idx].get('emotion', 'calm') if seg_idx < len(segments) else 'calm'
        from PIL import Image
        ph = os.path.join(project.draft_dir, "materials", f"ph_{i}.png")
        os.makedirs(os.path.dirname(ph), exist_ok=True)
        Image.new('RGB', (720, 1280), colors.get(emotion, (128,128,128))).save(ph)
        seg = project.add_media_safe(ph, start_time=start, duration=duration, track_name="VideoTrack")
        segment_objects.append(seg)
        current_time = start + duration

    # 2. 特效（滤镜+场景特效）
    logger.info("\n--- 特效 ---")
    for eff in ji.get('effects', []):
        si = eff.get('segment_index', 0)
        if si >= len(segment_objects): continue
        seg = segment_objects[si]
        etype = eff.get('type', 'filter')
        ename = eff.get('name', '')
        intensity = float(eff.get('intensity', 50))
        try:
            if etype == 'filter':
                fenum = FilterType.from_name(ename)
                seg.add_filter(fenum, intensity=intensity)
                logger.info(f"  片段{si}: 滤镜={ename}({intensity}%)")
            elif etype == 'scene_effect':
                resolved = resolve_scene_effect(ename)
                if resolved:
                    eenum = VideoSceneEffectType.from_name(resolved)
                    seg.add_effect(eenum)
                    logger.info(f"  片段{si}: 场景特效={ename}→{resolved}")
                else:
                    logger.warning(f"  片段{si}: 场景特效'{ename}'无映射，跳过")
        except Exception as e:
            logger.error(f"  片段{si}: {etype}={ename}失败: {e}")

    # 3. 动画（入场/出场）- 使用已验证的JianyingEffectAPI
    logger.info("\n--- 动画 ---")
    for anim in ji.get('animations', []):
        si = anim.get('segment_index', 0)
        if si >= len(segment_objects): continue
        seg = segment_objects[si]
        atype = anim.get('anim_type', 'intro')
        aname = anim.get('anim_name', '')
        astart = float(anim.get('start', 0))
        adur = float(anim.get('duration', 1.0))
        # 转换类型：intro->in, outro->out
        api_type = 'in' if atype == 'intro' else ('out' if atype == 'outro' else 'group')
        # 解析动画名称映射
        resolved_name = resolve_animation_name(aname, api_type)
        if resolved_name:
            ok = _effect_api.apply_animation(seg, api_type, resolved_name, start=astart, duration=adur)
            if ok:
                logger.info(f"  片段{si}: {atype}={aname}→{resolved_name}({astart:.1f}s,{adur:.1f}s)")
            else:
                logger.warning(f"  片段{si}: {atype}={aname}→{resolved_name}失败")
        else:
            logger.warning(f"  片段{si}: {atype}={aname}无映射，跳过")

    # 4. 转场（必须添加在前面的片段上）
    logger.info("\n--- 转场 ---")
    for trans in ji.get('transitions', []):
        from_seg = trans.get('from_segment', 0)
        tname = trans.get('name', '叠化')
        tdur = int(float(trans.get('duration', 0.6)) * 1000000)
        if from_seg >= len(segment_objects): continue
        try:
            tenum = TransitionType.from_name(tname)
            segment_objects[from_seg].add_transition(tenum, duration=tdur)
            logger.info(f"  片段{from_seg}->: {tname}({tdur/1000000:.1f}s)")
        except Exception as e:
            logger.error(f"  片段{from_seg}: {tname}失败: {e}")

    # 5. 关键帧（缩放/位移/旋转）
    logger.info("\n--- 关键帧 ---")
    kf_by_seg = {}
    for kf in ji.get('keyframes', []):
        si = kf.get('segment_index', 0)
        if si not in kf_by_seg:
            kf_by_seg[si] = []
        kf_by_seg[si].append(kf)

    for si, kfs in kf_by_seg.items():
        if si >= len(segment_objects): continue
        seg = segment_objects[si]
        kf_count = 0
        for kf in sorted(kfs, key=lambda x: x.get('time', 0)):
            t_us = int(float(kf.get('time', 0)) * 1000000)
            scale = kf.get('scale')
            x = kf.get('x')
            y = kf.get('y')
            rot = kf.get('rotation')
            try:
                if scale is not None and scale != 1.0:
                    seg.add_keyframe(KeyframeProperty.uniform_scale, t_us, float(scale))
                    kf_count += 1
                if x is not None and x != 0:
                    seg.add_keyframe(KeyframeProperty.position_x, t_us, float(x))
                    kf_count += 1
                if y is not None and y != 0:
                    seg.add_keyframe(KeyframeProperty.position_y, t_us, float(y))
                    kf_count += 1
                if rot is not None and rot != 0:
                    seg.add_keyframe(KeyframeProperty.rotation, t_us, float(rot))
                    kf_count += 1
            except Exception as e:
                logger.error(f"  片段{si}: 关键帧失败: {e}")
        logger.info(f"  片段{si}: {kf_count}个关键帧")

    project.save()
    logger.info(f"\n✅ 工程已保存: {project.draft_dir}")

    # 验证
    with open(os.path.join(project.draft_dir, "draft_content.json"), 'r', encoding='utf-8') as f:
        content = json.load(f)
    vt = [t for t in content.get('tracks', []) if t.get('type') == 'video']
    ts = sum(len(t.get('segments', [])) for t in vt)
    # 统计特效/动画/转场
    total_effects = 0
    total_animations = 0
    total_transitions = 0
    for t in vt:
        for s in t.get('segments', []):
            total_effects += len(s.get('effects', []))
            ai = s.get('animations_instance', {})
            if ai:
                total_animations += len(ai.get('animations', []))
            if s.get('transition'):
                total_transitions += 1
    logger.info(f"验证: {len(vt)}轨道 {ts}片段 | 特效:{total_effects} 动画:{total_animations} 转场:{total_transitions}")
    return project.draft_dir


if __name__ == "__main__":
    build_full_project(r"D:\DobaoWork_Project\Ai_Video_Editor\p3_pipeline_output\pipeline_result.json", "p3_full_effects_v2")
