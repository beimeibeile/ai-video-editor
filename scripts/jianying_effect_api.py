# -*- coding: utf-8 -*-
"""
剪映统一特效API v1.1
=====================
封装pyJianYingDraft的EffectSegment/FilterSegment/Animation，提供：
- 按名称/分类/关键词检索2309种内置特效 + 402种片段动画
- 一键应用场景特效、滤镜、角色特效
- 片段动画（入场/出场/组合）应用与检索
- 多特效链式叠加
- 特效参数调节

使用方式：
    from jianying_effect_api import JianyingEffectAPI
    api = JianyingEffectAPI()
    
    # 搜索特效
    results = api.search('故障')
    
    # 应用场景特效到工程
    api.apply_scene_effect(project, '闪白', start=0, duration=0.5)
    
    # 应用滤镜
    api.apply_filter(project, '电影感', start=0, duration=5, intensity=0.8)
    
    # 应用片段动画（必须在add_segment之前设置）
    api.apply_animation(segment, 'in', '渐显', start=0, duration=0.5)
    api.apply_animation(segment, 'out', '渐隐', start=2.5, duration=0.5)
    
    # 链式应用多个特效
    api.apply_chain(project, [
        {'type': 'scene', 'name': '闪白', 'start': 0, 'duration': 0.3},
        {'type': 'filter', 'name': '复古胶片', 'start': 0, 'duration': 10, 'intensity': 0.6},
    ])
"""
import os
import json
import sys
import logging
from typing import List, Dict, Optional, Union, Any

logger = logging.getLogger(__name__)

# pyJianYingDraft路径
JY_VENDOR = r'C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor\scripts\vendor'
if JY_VENDOR not in sys.path:
    sys.path.insert(0, JY_VENDOR)

from pyJianYingDraft.effect_segment import EffectSegment, FilterSegment
from pyJianYingDraft.metadata import VideoSceneEffectType, VideoCharacterEffectType, FilterType
from pyJianYingDraft.metadata import IntroType, OutroType, GroupAnimationType
from pyJianYingDraft.metadata import TransitionType, TextIntro, TextOutro, TextLoopAnim
from pyJianYingDraft.metadata import AudioSceneEffectType, ToneEffectType
from pyJianYingDraft.metadata import FontType, MaskType
from pyJianYingDraft.animation import VideoAnimation, SegmentAnimations
from pyJianYingDraft.time_util import Timerange, tim
from pyJianYingDraft.track import TrackType

# 特效索引路径
CATALOG_PATH = r'D:\DobaoWork_Project\Ai_Video_Editor\effect_catalog\effect_catalog.json'


class JianyingEffectAPI:
    """剪映统一特效API"""

    def __init__(self, catalog_path: str = None):
        self.catalog_path = catalog_path or CATALOG_PATH
        self.catalog = self._load_catalog()
        self._name_to_enum = self._build_name_index()

    def _load_catalog(self) -> Dict:
        """加载特效分类索引"""
        if os.path.exists(self.catalog_path):
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'items': {'scene_effects': [], 'filters': [], 'character_effects': []}}

    def _build_name_index(self) -> Dict[str, Any]:
        """构建名称→枚举映射"""
        index = {}
        # 场景特效
        for e in VideoSceneEffectType:
            index[e.name] = {'enum': e, 'type': 'scene'}
        # 角色特效
        for e in VideoCharacterEffectType:
            index[e.name] = {'enum': e, 'type': 'character'}
        # 滤镜
        for e in FilterType:
            index[e.name] = {'enum': e, 'type': 'filter'}
        return index

    # ============ 检索功能 ============

    def list_effects(self, effect_type: str = None, category: str = None) -> List[Dict]:
        """列出特效

        Args:
            effect_type: 'scene'/'filter'/'character'/None(全部)
            category: 分类名称，如'故障'/'光效'/'电影感'
        """
        results = []
        type_map = {
            'scene': 'scene_effects',
            'filter': 'filters',
            'character': 'character_effects'
        }
        keys = [type_map[effect_type]] if effect_type else list(type_map.values())
        for key in keys:
            for item in self.catalog.get('items', {}).get(key, []):
                if category and item.get('category') != category:
                    continue
                results.append(item)
        return results

    def search(self, keyword: str, effect_type: str = None) -> List[Dict]:
        """搜索特效（名称模糊匹配）

        Args:
            keyword: 搜索关键词
            effect_type: 限定类型 'scene'/'filter'/'character'/None
        """
        keyword_lower = keyword.lower()
        results = []
        for item in self.list_effects(effect_type):
            if keyword_lower in item['name'].lower():
                results.append(item)
        return results

    def get_categories(self, effect_type: str = None) -> Dict[str, int]:
        """获取分类统计

        Returns:
            {分类名: 数量}
        """
        if effect_type:
            type_key = {'scene': 'scene_effects', 'filter': 'filters', 'character': 'character_effects'}[effect_type]
            return self.catalog.get('categories', {}).get(type_key, {})
        # 合并所有分类
        merged = {}
        for type_key in ['scene_effects', 'filters', 'character_effects']:
            for cat, count in self.catalog.get('categories', {}).get(type_key, {}).items():
                merged[cat] = merged.get(cat, 0) + count
        return merged

    def get_effect_info(self, name: str) -> Optional[Dict]:
        """获取特效详情"""
        if name in self._name_to_enum:
            info = self._name_to_enum[name]
            # 从catalog中找分类信息
            cat_info = None
            for key in ['scene_effects', 'filters', 'character_effects']:
                for item in self.catalog.get('items', {}).get(key, []):
                    if item['name'] == name:
                        cat_info = item
                        break
                if cat_info:
                    break
            return {
                'name': name,
                'type': info['type'],
                'enum': info['enum'],
                'category': cat_info.get('category') if cat_info else None,
                'value': info['enum'].value if hasattr(info['enum'], 'value') else None
            }
        return None

    # ============ 应用功能 ============

    def _ensure_track(self, script, track_type: TrackType, track_name: str):
        """确保指定类型和名称的轨道存在，不存在则创建"""
        for t in script.tracks.values():
            if hasattr(t, 'track_type') and t.track_type == track_type:
                if getattr(t, 'name', '') == track_name:
                    return
        script.add_track(track_type, track_name)

    def apply_scene_effect(self, project, effect_name: str,
                            start: Union[str, int, float],
                            duration: Union[str, int, float],
                            params: List[float] = None,
                            track_name: str = None) -> bool:
        """应用场景特效

        Args:
            project: JyProject或ScriptFile对象
            effect_name: 特效名称，如'闪白'/'故障'/'三屏'
            start: 起始时间（秒或tim格式如'00:00:03.000'）
            duration: 持续时间（秒或tim格式）
            params: 特效参数列表（可选，取值0-100与剪映一致）
            track_name: 特效轨道名称（默认自动创建）

        Returns:
            True成功，False失败
        """
        info = self.get_effect_info(effect_name)
        if not info or info['type'] != 'scene':
            logger.error(f'场景特效不存在: {effect_name}')
            return False

        try:
            start_us = tim(start) if isinstance(start, str) else int(start * 1_000_000)
            dur_us = tim(duration) if isinstance(duration, str) else int(duration * 1_000_000)
            tr = Timerange(start_us, dur_us)

            script = project.script if hasattr(project, 'script') else project
            # 确保特效轨道存在（add_effect不会自动创建轨道）
            self._ensure_track(script, TrackType.effect, track_name or 'EffectTrack')
            # 使用pyJianYingDraft专用方法，自动处理素材注册
            script.add_effect(info['enum'], tr, track_name=track_name, params=params)
            return True
        except Exception as e:
            logger.error(f'应用场景特效失败 {effect_name}: {e}')
            import traceback
            traceback.print_exc()
            return False

    def apply_filter(self, project, filter_name: str,
                     start: Union[str, int, float],
                     duration: Union[str, int, float],
                     intensity: float = 100.0,
                     track_name: str = None) -> bool:
        """应用滤镜

        Args:
            project: JyProject或ScriptFile对象
            filter_name: 滤镜名称，如'电影感'/'复古胶片'/'清新'
            start: 起始时间
            duration: 持续时间
            intensity: 强度 0-100（与剪映一致，默认100）
            track_name: 滤镜轨道名称

        Returns:
            True成功，False失败
        """
        info = self.get_effect_info(filter_name)
        if not info or info['type'] != 'filter':
            logger.error(f'滤镜不存在: {filter_name}')
            return False

        try:
            start_us = tim(start) if isinstance(start, str) else int(start * 1_000_000)
            dur_us = tim(duration) if isinstance(duration, str) else int(duration * 1_000_000)
            tr = Timerange(start_us, dur_us)

            script = project.script if hasattr(project, 'script') else project
            # 确保滤镜轨道存在
            self._ensure_track(script, TrackType.filter, track_name or 'FilterTrack')
            # 使用pyJianYingDraft专用方法，自动处理素材注册
            script.add_filter(info['enum'], tr, track_name=track_name, intensity=intensity)
            return True
        except Exception as e:
            logger.error(f'应用滤镜失败 {filter_name}: {e}')
            import traceback
            traceback.print_exc()
            return False

    def apply_character_effect(self, project, effect_name: str,
                                start: Union[str, int, float],
                                duration: Union[str, int, float],
                                params: List[float] = None,
                                track_name: str = None) -> bool:
        """应用角色特效

        Args:
            project: JyProject或ScriptFile对象
            effect_name: 角色特效名称
            start: 起始时间
            duration: 持续时间
            params: 特效参数（取值0-100与剪映一致）
            track_name: 轨道名称
        """
        info = self.get_effect_info(effect_name)
        if not info or info['type'] != 'character':
            logger.error(f'角色特效不存在: {effect_name}')
            return False

        try:
            start_us = tim(start) if isinstance(start, str) else int(start * 1_000_000)
            dur_us = tim(duration) if isinstance(duration, str) else int(duration * 1_000_000)
            tr = Timerange(start_us, dur_us)

            script = project.script if hasattr(project, 'script') else project
            # 确保特效轨道存在
            self._ensure_track(script, TrackType.effect, track_name or 'EffectTrack')
            # add_effect同时支持VideoSceneEffectType和VideoCharacterEffectType
            script.add_effect(info['enum'], tr, track_name=track_name, params=params)
            return True
        except Exception as e:
            logger.error(f'应用角色特效失败 {effect_name}: {e}')
            import traceback
            traceback.print_exc()
            return False

    def apply_chain(self, project, effects: List[Dict]) -> Dict[str, int]:
        """链式应用多个特效

        Args:
            project: JyProject或ScriptFile对象
            effects: 特效配置列表，每个元素格式：
                {
                    'type': 'scene'|'filter'|'character',
                    'name': '特效名称',
                    'start': 0,           # 起始时间（秒）
                    'duration': 5,        # 持续时间（秒）
                    'intensity': 0.8,     # 仅filter用
                    'params': [...],      # 仅scene/character用
                    'track_name': '...'   # 可选
                }

        Returns:
            {'success': 成功数, 'failed': 失败数, 'failed_names': [失败名称列表]}
        """
        success = 0
        failed = 0
        failed_names = []

        for cfg in effects:
            etype = cfg.get('type', 'scene')
            name = cfg.get('name', '')
            start = cfg.get('start', 0)
            duration = cfg.get('duration', 5)
            track_name = cfg.get('track_name')

            ok = False
            if etype == 'scene':
                ok = self.apply_scene_effect(project, name, start, duration,
                                              params=cfg.get('params'), track_name=track_name)
            elif etype == 'filter':
                ok = self.apply_filter(project, name, start, duration,
                                       intensity=cfg.get('intensity', 1.0), track_name=track_name)
            elif etype == 'character':
                ok = self.apply_character_effect(project, name, start, duration,
                                                  params=cfg.get('params'), track_name=track_name)

            if ok:
                success += 1
            else:
                failed += 1
                failed_names.append(name)

        return {'success': success, 'failed': failed, 'failed_names': failed_names}

    # ============ 片段动画（入场/出场/组合） ============

    def list_animations(self, anim_type: str = 'all') -> List[Dict]:
        """列出可用的片段动画

        Args:
            anim_type: 'in'(入场) / 'out'(出场) / 'group'(组合) / 'all'(全部)

        Returns:
            动画列表 [{name, type, default_duration}]
        """
        results = []
        enums = []
        if anim_type in ('in', 'all'):
            enums.append(('in', IntroType))
        if anim_type in ('out', 'all'):
            enums.append(('out', OutroType))
        if anim_type in ('group', 'all'):
            enums.append(('group', GroupAnimationType))

        for atype, enum_cls in enums:
            for name, member in enum_cls.__members__.items():
                meta = member.value
                raw_dur = getattr(meta, 'duration', 0.5)
                # AnimationMeta的duration单位是微秒，转为秒
                dur_sec = raw_dur / 1_000_000 if raw_dur > 1000 else raw_dur
                results.append({
                    'name': meta.title,
                    'type': atype,
                    'default_duration': dur_sec,
                    'enum_name': name,
                })
        return results

    def search_animations(self, keyword: str, anim_type: str = 'all') -> List[Dict]:
        """搜索片段动画

        Args:
            keyword: 搜索关键词
            anim_type: 'in'/'out'/'group'/'all'
        """
        keyword = keyword.lower()
        return [a for a in self.list_animations(anim_type)
                if keyword in a['name'].lower()]

    def apply_animation(self, segment, anim_type: str, anim_name: str,
                         start: float = 0, duration: float = None) -> bool:
        """为视频片段应用入场/出场/组合动画

        Args:
            segment: VideoSegment对象（已添加到轨道的片段）
            anim_type: 'in'(入场) / 'out'(出场) / 'group'(组合)
            anim_name: 动画名称，如'渐显'/'放大'/'叠叠乐'
            start: 动画相对片段开头的偏移（秒），入场默认0，出场建议设为片段时长-动画时长
            duration: 动画持续时间（秒），默认使用动画默认时长

        Returns:
            True成功，False失败

        注意：
            - 必须在add_segment之前设置animations_instance
            - pyJianYingDraft不会自动关联animation_id到extra_material_refs，
              此方法会自动修复此bug
        """
        # 查找动画枚举
        enum_map = {'in': IntroType, 'out': OutroType, 'group': GroupAnimationType}
        enum_cls = enum_map.get(anim_type)
        if not enum_cls:
            logger.error(f'动画类型无效: {anim_type}（应为in/out/group）')
            return False

        target_enum = None
        for name, member in enum_cls.__members__.items():
            if member.value.title == anim_name:
                target_enum = member
                break
        if not target_enum:
            # 模糊匹配
            for name, member in enum_cls.__members__.items():
                if anim_name.lower() in member.value.title.lower():
                    target_enum = member
                    break
        if not target_enum:
            logger.error(f'动画不存在: {anim_name}（类型={anim_type}）')
            return False

        try:
            meta = target_enum.value
            raw_dur = getattr(meta, 'duration', 0.5)
            default_dur = raw_dur / 1_000_000 if raw_dur > 1000 else raw_dur
            dur = duration if duration is not None else default_dur
            start_us = int(start * 1_000_000)
            dur_us = int(dur * 1_000_000)

            anim = VideoAnimation(target_enum, start_us, dur_us)

            # 获取或创建SegmentAnimations
            if segment.animations_instance is None:
                segment.animations_instance = SegmentAnimations()

            segment.animations_instance.add_animation(anim)

            # 修复pyJianYingDraft bug：手动关联animation_id到extra_material_refs
            anim_id = segment.animations_instance.animation_id
            if anim_id not in segment.extra_material_refs:
                segment.extra_material_refs.append(anim_id)

            return True
        except Exception as e:
            logger.error(f'应用动画失败 {anim_name}: {e}')
            import traceback
            traceback.print_exc()
            return False

    def apply_animations_to_segment(self, segment, animations: List[Dict]) -> bool:
        """为视频片段批量应用多个动画（入场+出场组合）

        Args:
            segment: VideoSegment对象
            animations: 动画配置列表，每个元素：
                {'type': 'in'/'out'/'group', 'name': '渐显', 'start': 0, 'duration': 0.5}

        Returns:
            True全部成功，False有失败
        """
        all_ok = True
        for cfg in animations:
            ok = self.apply_animation(
                segment,
                cfg.get('type', 'in'),
                cfg.get('name', ''),
                start=cfg.get('start', 0),
                duration=cfg.get('duration'),
            )
            if not ok:
                all_ok = False
        return all_ok

    # ============ 转场特效 ============

    def list_transitions(self, only_free: bool = True) -> List[Dict]:
        """列出转场特效

        Args:
            only_free: 仅列出免费转场（默认True，VIP转场需会员）

        Returns:
            转场列表 [{name, is_vip, default_duration, resource_id, effect_id}]
        """
        results = []
        for name, member in TransitionType.__members__.items():
            meta = member.value
            if only_free and meta.is_vip:
                continue
            dur_sec = meta.default_duration / 1_000_000
            results.append({
                'name': meta.name,
                'is_vip': meta.is_vip,
                'default_duration': dur_sec,
                'resource_id': meta.resource_id,
                'effect_id': meta.effect_id,
                'is_overlap': meta.is_overlap,
            })
        return results

    def search_transitions(self, keyword: str, only_free: bool = True) -> List[Dict]:
        """搜索转场特效"""
        keyword = keyword.lower()
        return [t for t in self.list_transitions(only_free)
                if keyword in t['name'].lower()]

    def apply_transition(self, segment, transition_name: str,
                         duration: float = None) -> bool:
        """为视频片段应用转场特效（设置在片段开头，与上一个片段之间）

        Args:
            segment: VideoSegment对象（必须在add_segment之前设置）
            transition_name: 转场名称，如'叠化'/'淡入淡出'/'翻页'
            duration: 转场持续时间（秒），默认使用转场默认时长

        Returns:
            True成功，False失败

        注意：
            - 转场设置在片段开头，需要该片段前面有另一个片段才能看到效果
            - 必须在add_segment之前设置segment.transition
        """
        target_enum = None
        for name, member in TransitionType.__members__.items():
            if member.value.name == transition_name:
                target_enum = member
                break
        if not target_enum:
            for name, member in TransitionType.__members__.items():
                if transition_name.lower() in member.value.name.lower():
                    target_enum = member
                    break
        if not target_enum:
            logger.error(f'转场不存在: {transition_name}')
            return False

        try:
            meta = target_enum.value
            dur = duration if duration is not None else meta.default_duration / 1_000_000
            from pyJianYingDraft.video_segment import Transition
            segment.transition = Transition(target_enum, int(dur * 1_000_000))
            return True
        except Exception as e:
            logger.error(f'应用转场失败 {transition_name}: {e}')
            import traceback
            traceback.print_exc()
            return False

    # ============ 文本动画 ============

    def list_text_animations(self, anim_type: str = 'all') -> List[Dict]:
        """列出文本动画

        Args:
            anim_type: 'in'(入场) / 'out'(出场) / 'loop'(循环) / 'all'(全部)
        """
        results = []
        enums = []
        if anim_type in ('in', 'all'):
            enums.append(('in', TextIntro))
        if anim_type in ('out', 'all'):
            enums.append(('out', TextOutro))
        if anim_type in ('loop', 'all'):
            enums.append(('loop', TextLoopAnim))

        for atype, enum_cls in enums:
            for name, member in enum_cls.__members__.items():
                meta = member.value
                raw_dur = getattr(meta, 'duration', 0.5)
                dur_sec = raw_dur / 1_000_000 if raw_dur > 1000 else raw_dur
                results.append({
                    'name': meta.title,
                    'type': atype,
                    'default_duration': dur_sec,
                })
        return results

    def search_text_animations(self, keyword: str, anim_type: str = 'all') -> List[Dict]:
        """搜索文本动画"""
        keyword = keyword.lower()
        return [a for a in self.list_text_animations(anim_type)
                if keyword in a['name'].lower()]

    # ============ 音频特效 ============

    def list_audio_effects(self, effect_type: str = 'all', only_free: bool = True) -> List[Dict]:
        """列出音频特效

        Args:
            effect_type: 'scene'(场景音效) / 'tone'(变声音调) / 'all'(全部)
            only_free: 仅列出免费特效
        """
        results = []
        enums = []
        if effect_type in ('scene', 'all'):
            enums.append(('scene', AudioSceneEffectType))
        if effect_type in ('tone', 'all'):
            enums.append(('tone', ToneEffectType))

        for etype, enum_cls in enums:
            for name, member in enum_cls.__members__.items():
                meta = member.value
                is_vip = getattr(meta, 'is_vip', False)
                if only_free and is_vip:
                    continue
                results.append({
                    'name': meta.name,
                    'type': etype,
                    'is_vip': is_vip,
                    'params_count': len(getattr(meta, 'params', [])),
                    'resource_id': getattr(meta, 'resource_id', ''),
                    'effect_id': getattr(meta, 'effect_id', ''),
                })
        return results

    def search_audio_effects(self, keyword: str, effect_type: str = 'all') -> List[Dict]:
        """搜索音频特效"""
        keyword = keyword.lower()
        return [e for e in self.list_audio_effects(effect_type)
                if keyword in e['name'].lower()]

    def apply_audio_effect(self, segment, effect_name: str,
                            params: List[float] = None) -> bool:
        """为音频片段应用音频特效（场景音效或变声音调）

        Args:
            segment: AudioSegment对象
            effect_name: 特效名称，如'回音'/'混响'/'大叔音'/'萝莉音'
            params: 特效参数列表（取值0-100与剪映一致，None使用默认值）

        Returns:
            True成功，False失败

        注意：同一类音效只能添加一个（如不能同时添加两个场景音效）
        """
        target_enum = None
        target_cls = None
        for enum_cls in (AudioSceneEffectType, ToneEffectType):
            for name, member in enum_cls.__members__.items():
                if member.value.name == effect_name:
                    target_enum = member
                    target_cls = enum_cls
                    break
            if target_enum:
                break
        if not target_enum:
            for enum_cls in (AudioSceneEffectType, ToneEffectType):
                for name, member in enum_cls.__members__.items():
                    if effect_name.lower() in member.value.name.lower():
                        target_enum = member
                        target_cls = enum_cls
                        break
                if target_enum:
                    break
        if not target_enum:
            logger.error(f'音频特效不存在: {effect_name}')
            return False

        try:
            segment.add_effect(target_enum, params)
            return True
        except Exception as e:
            logger.error(f'应用音频特效失败 {effect_name}: {e}')
            import traceback
            traceback.print_exc()
            return False

    # ============ 字体 ============

    def list_fonts(self, only_free: bool = True) -> List[Dict]:
        """列出可用字体

        Args:
            only_free: 仅列出免费字体
        """
        results = []
        for name, member in FontType.__members__.items():
            meta = member.value
            is_vip = getattr(meta, 'is_vip', False)
            if only_free and is_vip:
                continue
            results.append({
                'name': meta.name,
                'is_vip': is_vip,
                'resource_id': getattr(meta, 'resource_id', ''),
                'effect_id': getattr(meta, 'effect_id', ''),
            })
        return results

    def search_fonts(self, keyword: str, only_free: bool = True) -> List[Dict]:
        """搜索字体"""
        keyword = keyword.lower()
        return [f for f in self.list_fonts(only_free)
                if keyword in f['name'].lower()]

    # ============ 蒙版 ============

    def list_masks(self) -> List[Dict]:
        """列出可用蒙版形状（6种）"""
        results = []
        for name, member in MaskType.__members__.items():
            meta = member.value
            results.append({
                'name': getattr(meta, 'name', name),
                'resource_id': getattr(meta, 'resource_id', ''),
                'effect_id': getattr(meta, 'effect_id', ''),
            })
        return results

    # ============ 统计信息 ============

    def stats(self) -> Dict:
        """获取特效库统计信息"""
        return {
            'total': self.catalog.get('total', 0),
            'scene_effects': len(self.catalog.get('items', {}).get('scene_effects', [])),
            'filters': len(self.catalog.get('items', {}).get('filters', [])),
            'character_effects': len(self.catalog.get('items', {}).get('character_effects', [])),
            'categories': self.get_categories()
        }


# ============ 便捷函数 ============

_default_api = None

def get_api() -> JianyingEffectAPI:
    """获取默认API单例"""
    global _default_api
    if _default_api is None:
        _default_api = JianyingEffectAPI()
    return _default_api


def apply_scene_effect(project, name, start, duration, **kwargs):
    """便捷函数：应用场景特效"""
    return get_api().apply_scene_effect(project, name, start, duration, **kwargs)


def apply_filter(project, name, start, duration, intensity=1.0, **kwargs):
    """便捷函数：应用滤镜"""
    return get_api().apply_filter(project, name, start, duration, intensity, **kwargs)


def search_effects(keyword, effect_type=None):
    """便捷函数：搜索特效"""
    return get_api().search(keyword, effect_type)


if __name__ == '__main__':
    # 配置logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # 自测
    api = JianyingEffectAPI()
    logger.info('=== 特效库统计 ===')
    stats = api.stats()
    logger.info(f"总计: {stats['total']}种")
    logger.info(f"  场景特效: {stats['scene_effects']}种")
    logger.info(f"  滤镜: {stats['filters']}种")
    logger.info(f"  角色特效: {stats['character_effects']}种")

    logger.info('\n=== 搜索"故障" ===')
    results = api.search('故障')
    for r in results[:10]:
        logger.info(f"  [{r['type']}] {r['name']} ({r.get('category', '?')})")

    logger.info('\n=== 搜索"电影"滤镜 ===')
    results = api.search('电影', effect_type='filter')
    for r in results[:10]:
        logger.info(f"  {r['name']} ({r.get('category', '?')})")

    logger.info('\n=== 场景特效分类统计 ===')
    for cat, count in sorted(api.get_categories('scene').items(), key=lambda x: -x[1]):
        logger.info(f"  {cat}: {count}种")
