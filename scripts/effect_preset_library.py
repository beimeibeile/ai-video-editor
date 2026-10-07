"""
P2-5: 特效组合预设库
20+场景化特效组合预设，支持一键应用到剪映工程

预设结构:
{
    "name": "预设名称",
    "category": "开场/转场/结尾/产品/情绪/风格",
    "description": "描述",
    "duration": 总时长(秒),
    "effects": [
        {
            "effect_type": VideoSceneEffectType.XXX,
            "start": 开始时间(秒),
            "duration": 持续时间(秒),
            "params": [参数列表],
            "track": "effect" / "filter",
        },
        ...
    ],
    "recommended_transition": "推荐转场",
}
"""

import sys
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 添加jianying-editor路径
JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
if JY_SKILL not in sys.path:
    sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))
    sys.path.insert(0, os.path.join(JY_SKILL, "scripts", "vendor"))

from pyJianYingDraft.metadata.video_scene_effect import VideoSceneEffectType
from pyJianYingDraft.metadata.transition_meta import TransitionType


@dataclass
class EffectStep:
    """特效步骤"""
    effect_name: str
    effect_type: Any  # VideoSceneEffectType
    start: float  # 秒
    duration: float  # 秒
    params: List[float] = field(default_factory=list)
    track: str = "effect"  # effect / filter


@dataclass
class EffectPreset:
    """特效组合预设"""
    name: str
    category: str
    description: str
    duration: float
    effects: List[EffectStep] = field(default_factory=list)
    recommended_transition: str = ""
    tags: List[str] = field(default_factory=list)


class EffectPresetLibrary:
    """特效组合预设库"""

    def __init__(self):
        self.presets = self._build_presets()

    def _build_presets(self) -> Dict[str, EffectPreset]:
        """构建20+场景化预设"""
        presets = {}

        # ========== 开场类 ==========
        presets["炫酷开场"] = EffectPreset(
            name="炫酷开场",
            category="开场",
            description="RGB描边+故障+闪光，高能炫酷开场，适合科技/游戏/潮流内容",
            duration=3.0,
            effects=[
                EffectStep("RGB描边", VideoSceneEffectType.RGB描边, 0, 1.5, [80, 70, 60]),
                EffectStep("故障", VideoSceneEffectType.故障, 0.5, 1.0, [60, 60, 50, 50, 50, 80, 50]),
                EffectStep("变色闪光", VideoSceneEffectType.变色闪光, 1.0, 1.0, [80, 50, 40, 90, 60, 100, 70, 80]),
                EffectStep("像素屏闪", VideoSceneEffectType.像素屏闪, 2.0, 1.0, [80, 80, 40, 70, 70, 90, 60]),
            ],
            recommended_transition="闪白",
            tags=["炫酷", "科技", "高能", "开场"],
        )

        presets["复古DV开场"] = EffectPreset(
            name="复古DV开场",
            category="开场",
            description="VCR+DV录制框+CCD闪光，复古DV质感开场",
            duration=4.0,
            effects=[
                EffectStep("VCR", VideoSceneEffectType.VCR, 0, 4.0, [40, 50, 60, 50, 40]),
                EffectStep("DV录制框", VideoSceneEffectType.DV录制框, 0, 4.0, [40, 60, 70, 50]),
                EffectStep("CCD闪光", VideoSceneEffectType.CCD闪光, 0.5, 1.0, [50, 70, 60, 70]),
                EffectStep("betamax", VideoSceneEffectType.betamax, 2.0, 2.0, [60, 70, 50, 60, 50, 40]),
            ],
            recommended_transition="叠化",
            tags=["复古", "DV", "纪实", "开场"],
        )

        presets["温馨开场"] = EffectPreset(
            name="温馨开场",
            category="开场",
            description="梦幻辉光+爱心光斑+丁达尔光线，温暖治愈开场",
            duration=4.0,
            effects=[
                EffectStep("梦幻辉光", VideoSceneEffectType.梦幻辉光, 0, 4.0, [55, 65, 55, 55, 60, 65, 45]),
                EffectStep("爱心光斑", VideoSceneEffectType.爱心光斑, 0.5, 3.5, [55, 35, 45, 70, 45, 35, 55, 45, 45]),
                EffectStep("丁达尔光线", VideoSceneEffectType.丁达尔光线, 1.0, 3.0, [70, 45, 55, 45, 45, 35, 90]),
            ],
            recommended_transition="柔光转场",
            tags=["温馨", "治愈", "柔和", "开场"],
        )

        presets["赛博朋克开场"] = EffectPreset(
            name="赛博朋克开场",
            category="开场",
            description="RGB描边+X-Signal+双重辉光，赛博朋克风格开场",
            duration=3.0,
            effects=[
                EffectStep("RGB描边", VideoSceneEffectType.RGB描边, 0, 3.0, [70, 60, 50]),
                EffectStep("X-Signal", VideoSceneEffectType.X_Signal, 0, 1.5, [80]),
                EffectStep("双重辉光", VideoSceneEffectType.双重辉光, 1.0, 2.0, [60, 50, 90, 80, 90, 100, 80]),
                EffectStep("噪点", VideoSceneEffectType.噪点, 0.5, 2.5, [50, 30, 60, 70, 40, 50]),
            ],
            recommended_transition="故障转场",
            tags=["赛博朋克", "科技", "未来", "开场"],
        )

        # ========== 转场类 ==========
        presets["闪白转场"] = EffectPreset(
            name="闪白转场",
            category="转场",
            description="变色闪光+发光HDR，0.5秒快速闪白转场",
            duration=0.8,
            effects=[
                EffectStep("变色闪光", VideoSceneEffectType.变色闪光, 0, 0.5, [90, 60, 50, 100, 70, 100, 80, 90]),
                EffectStep("发光HDR", VideoSceneEffectType.发光HDR, 0.2, 0.6, [70, 80, 70, 60, 80, 90, 100, 40]),
            ],
            recommended_transition="闪白",
            tags=["转场", "闪白", "快速"],
        )

        presets["故障转场"] = EffectPreset(
            name="故障转场",
            category="转场",
            description="故障+RGB描边+像素屏闪，1秒故障风格转场",
            duration=1.2,
            effects=[
                EffectStep("故障", VideoSceneEffectType.故障, 0, 0.8, [70, 70, 60, 60, 60, 90, 60]),
                EffectStep("RGB描边", VideoSceneEffectType.RGB描边, 0.3, 0.9, [80, 70, 60]),
                EffectStep("像素屏闪", VideoSceneEffectType.像素屏闪, 0.5, 0.7, [80, 80, 40, 70, 70, 90, 60]),
            ],
            recommended_transition="故障",
            tags=["转场", "故障", "科技"],
        )

        presets["模糊转场"] = EffectPreset(
            name="模糊转场",
            category="转场",
            description="模糊+动感模糊，1.5秒柔和模糊转场",
            duration=1.5,
            effects=[
                EffectStep("模糊", VideoSceneEffectType.模糊, 0, 1.5, [80, 90, 40]),
                EffectStep("动感模糊", VideoSceneEffectType.动感模糊, 0.3, 1.2, [60, 80, 60, 100, 60, 60, 100]),
            ],
            recommended_transition="叠化",
            tags=["转场", "模糊", "柔和"],
        )

        presets["缩放转场"] = EffectPreset(
            name="缩放转场",
            category="转场",
            description="变速推镜+发光HDR，1秒缩放推进转场",
            duration=1.0,
            effects=[
                EffectStep("变速推镜", VideoSceneEffectType.变速推镜, 0, 1.0, [70, 40, 90, 100, 100, 80, 60]),
                EffectStep("发光HDR", VideoSceneEffectType.发光HDR, 0.3, 0.7, [60, 70, 60, 50, 70, 80, 90, 30]),
            ],
            recommended_transition="缩放",
            tags=["转场", "缩放", "推进"],
        )

        # ========== 结尾类 ==========
        presets["渐暗结尾"] = EffectPreset(
            name="渐暗结尾",
            category="结尾",
            description="模糊+VCR+90s画质，渐暗复古结尾",
            duration=3.0,
            effects=[
                EffectStep("模糊", VideoSceneEffectType.模糊, 0, 3.0, [70, 80, 30]),
                EffectStep("VCR", VideoSceneEffectType.VCR, 0.5, 2.5, [30, 40, 50, 40, 30]),
                EffectStep("90s画质", VideoSceneEffectType._90s画质, 1.0, 2.0, [50, 40, 30, 30]),
            ],
            recommended_transition="淡出",
            tags=["结尾", "渐暗", "复古"],
        )

        presets["高光结尾"] = EffectPreset(
            name="高光结尾",
            category="结尾",
            description="双重辉光+发光HDR+变色闪光，高光爆发结尾",
            duration=2.5,
            effects=[
                EffectStep("双重辉光", VideoSceneEffectType.双重辉光, 0, 2.5, [60, 50, 90, 80, 90, 100, 80]),
                EffectStep("发光HDR", VideoSceneEffectType.发光HDR, 0.5, 2.0, [70, 80, 70, 60, 80, 90, 100, 40]),
                EffectStep("变色闪光", VideoSceneEffectType.变色闪光, 1.5, 1.0, [80, 50, 40, 90, 60, 100, 70, 80]),
            ],
            recommended_transition="闪白",
            tags=["结尾", "高光", "爆发"],
        )

        presets["温馨结尾"] = EffectPreset(
            name="温馨结尾",
            category="结尾",
            description="梦幻辉光+爱心扫光+丁达尔光线，温暖收尾",
            duration=3.5,
            effects=[
                EffectStep("梦幻辉光", VideoSceneEffectType.梦幻辉光, 0, 3.5, [50, 60, 50, 50, 55, 60, 35]),
                EffectStep("爱心扫光", VideoSceneEffectType.爱心扫光, 0.5, 3.0, [55, 45, 50, 45, 65, 50, 65, 55]),
                EffectStep("丁达尔光线", VideoSceneEffectType.丁达尔光线, 1.0, 2.5, [60, 40, 50, 40, 40, 30, 80]),
            ],
            recommended_transition="淡出",
            tags=["结尾", "温馨", "治愈"],
        )

        # ========== 产品展示类 ==========
        presets["产品特写"] = EffectPreset(
            name="产品特写",
            category="产品",
            description="发光HDR+双重辉光+锐化，产品特写展示",
            duration=5.0,
            effects=[
                EffectStep("发光HDR", VideoSceneEffectType.发光HDR, 0, 5.0, [60, 70, 60, 50, 70, 80, 90, 30]),
                EffectStep("双重辉光", VideoSceneEffectType.双重辉光, 0.5, 4.5, [50, 40, 80, 70, 80, 100, 70]),
                EffectStep("局部推镜", VideoSceneEffectType.局部推镜, 1.0, 3.0, [40, 60, 60, 50, 40, 50, 50]),
            ],
            recommended_transition="缩放",
            tags=["产品", "特写", "展示", "电商"],
        )

        presets["产品对比"] = EffectPreset(
            name="产品对比",
            category="产品",
            description="VCR+发光HDR，使用前后对比展示",
            duration=6.0,
            effects=[
                EffectStep("VCR", VideoSceneEffectType.VCR, 0, 3.0, [50, 60, 70, 60, 50]),
                EffectStep("发光HDR", VideoSceneEffectType.发光HDR, 3.0, 3.0, [70, 80, 70, 60, 80, 90, 100, 40]),
                EffectStep("双重辉光", VideoSceneEffectType.双重辉光, 3.5, 2.5, [60, 50, 90, 80, 90, 100, 80]),
            ],
            recommended_transition="闪白",
            tags=["产品", "对比", "前后", "电商"],
        )

        # ========== 风格类 ==========
        presets["电影感"] = EffectPreset(
            name="电影感",
            category="风格",
            description="模糊+发光HDR+丁达尔光线，电影级质感",
            duration=10.0,
            effects=[
                EffectStep("模糊", VideoSceneEffectType.模糊, 0, 10.0, [40, 50, 30]),
                EffectStep("发光HDR", VideoSceneEffectType.发光HDR, 0, 10.0, [50, 60, 50, 40, 60, 70, 80, 20]),
                EffectStep("丁达尔光线", VideoSceneEffectType.丁达尔光线, 2.0, 6.0, [60, 40, 50, 40, 40, 30, 80]),
            ],
            recommended_transition="叠化",
            tags=["电影", "质感", "高级", "风格"],
        )

        presets["日系清新"] = EffectPreset(
            name="日系清新",
            category="风格",
            description="梦幻辉光+模糊+爱心光斑，日系清新风格",
            duration=10.0,
            effects=[
                EffectStep("梦幻辉光", VideoSceneEffectType.梦幻辉光, 0, 10.0, [45, 55, 45, 45, 50, 55, 35]),
                EffectStep("模糊", VideoSceneEffectType.模糊, 0, 10.0, [30, 40, 20]),
                EffectStep("爱心光斑", VideoSceneEffectType.爱心光斑, 1.0, 9.0, [45, 30, 40, 60, 40, 30, 45, 40, 40]),
            ],
            recommended_transition="叠化",
            tags=["日系", "清新", "柔和", "风格"],
        )

        presets["悬疑纪实"] = EffectPreset(
            name="悬疑纪实",
            category="风格",
            description="圆形监控+动态侦测+CCD闪光，悬疑纪实风格",
            duration=10.0,
            effects=[
                EffectStep("圆形监控", VideoSceneEffectType.圆形监控, 0, 10.0, [40, 50, 70, 80, 40, 30, 30, 50, 50]),
                EffectStep("动态侦测", VideoSceneEffectType.动态侦测, 1.0, 8.0, [55, 70, 98, 30, 80, 30, 70, 30, 20]),
                EffectStep("CCD闪光", VideoSceneEffectType.CCD闪光, 3.0, 2.0, [50, 70, 60, 70]),
                EffectStep("抽帧拖影", VideoSceneEffectType.抽帧拖影, 5.0, 3.0, [50, 50, 50, 50, 50]),
            ],
            recommended_transition="跳切",
            tags=["悬疑", "纪实", "监控", "风格"],
        )

        presets["复古Vlog"] = EffectPreset(
            name="复古Vlog",
            category="风格",
            description="VCR+DV录制框+betamax，复古Vlog风格",
            duration=10.0,
            effects=[
                EffectStep("VCR", VideoSceneEffectType.VCR, 0, 10.0, [40, 50, 60, 50, 40]),
                EffectStep("DV录制框", VideoSceneEffectType.DV录制框, 0, 10.0, [40, 60, 70, 50]),
                EffectStep("betamax", VideoSceneEffectType.betamax, 2.0, 6.0, [60, 70, 50, 60, 50, 40]),
                EffectStep("90s画质", VideoSceneEffectType._90s画质, 5.0, 5.0, [60, 50, 40, 40]),
            ],
            recommended_transition="叠化",
            tags=["复古", "Vlog", "DV", "风格"],
        )

        # ========== 情绪类（基于P2-4） ==========
        presets["高能情绪"] = EffectPreset(
            name="高能情绪",
            category="情绪",
            description="RGB描边+噪点+动感竖线+变色闪光，高能激昂情绪",
            duration=5.0,
            effects=[
                EffectStep("RGB描边", VideoSceneEffectType.RGB描边, 0, 5.0, [80, 70, 60]),
                EffectStep("噪点", VideoSceneEffectType.噪点, 0, 5.0, [70, 40, 80, 90, 50, 60]),
                EffectStep("动感竖线", VideoSceneEffectType.动感竖线, 0.5, 4.5, [70, 60, 50, 90, 30, 100, 60, 80]),
                EffectStep("变色闪光", VideoSceneEffectType.变色闪光, 2.0, 1.5, [80, 50, 40, 90, 60, 100, 70, 80]),
            ],
            recommended_transition="闪白",
            tags=["情绪", "高能", "激昂", "高潮"],
        )

        presets["柔和情绪"] = EffectPreset(
            name="柔和情绪",
            category="情绪",
            description="梦幻辉光+模糊+丁达尔光线，柔和舒缓情绪",
            duration=8.0,
            effects=[
                EffectStep("梦幻辉光", VideoSceneEffectType.梦幻辉光, 0, 8.0, [55, 65, 55, 55, 60, 65, 45]),
                EffectStep("模糊", VideoSceneEffectType.模糊, 0, 8.0, [60, 70, 35]),
                EffectStep("丁达尔光线", VideoSceneEffectType.丁达尔光线, 1.0, 6.0, [70, 45, 55, 45, 45, 35, 90]),
                EffectStep("爱心光斑", VideoSceneEffectType.爱心光斑, 2.0, 5.0, [55, 35, 45, 70, 45, 35, 55, 45, 45]),
            ],
            recommended_transition="叠化",
            tags=["情绪", "柔和", "舒缓", "温馨"],
        )

        presets["紧张情绪"] = EffectPreset(
            name="紧张情绪",
            category="情绪",
            description="CCD闪光+圆形监控+动态侦测+抽帧拖影，紧张悬疑情绪",
            duration=6.0,
            effects=[
                EffectStep("CCD闪光", VideoSceneEffectType.CCD闪光, 0, 6.0, [50, 70, 60, 70]),
                EffectStep("圆形监控", VideoSceneEffectType.圆形监控, 0.5, 5.5, [40, 50, 70, 80, 40, 30, 30, 50, 50]),
                EffectStep("动态侦测", VideoSceneEffectType.动态侦测, 1.0, 4.0, [55, 70, 98, 30, 80, 30, 70, 30, 20]),
                EffectStep("抽帧拖影", VideoSceneEffectType.抽帧拖影, 2.0, 3.0, [50, 50, 50, 50, 50]),
            ],
            recommended_transition="跳切",
            tags=["情绪", "紧张", "悬疑", "压迫"],
        )

        return presets

    def get_preset(self, name: str) -> Optional[EffectPreset]:
        """获取指定预设"""
        return self.presets.get(name)

    def list_presets(self, category: str = None) -> List[str]:
        """列出所有预设（可按分类筛选）"""
        if category:
            return [name for name, p in self.presets.items() if p.category == category]
        return list(self.presets.keys())

    def list_categories(self) -> List[str]:
        """列出所有分类"""
        return list(set(p.category for p in self.presets.values()))

    def search_presets(self, keyword: str) -> List[str]:
        """按关键词搜索预设"""
        keyword = keyword.lower()
        results = []
        for name, p in self.presets.items():
            if (keyword in name.lower() or
                keyword in p.description.lower() or
                any(keyword in tag.lower() for tag in p.tags)):
                results.append(name)
        return results

    def apply_preset_to_script(self, script, preset_name: str, start_time: float = 0.0,
                                track_name: str = "EffectTrack") -> bool:
        """
        将预设应用到ScriptFile工程

        Args:
            script: pyJianYingDraft ScriptFile实例
            preset_name: 预设名称
            start_time: 开始时间偏移（秒）
            track_name: 特效轨道名称

        Returns:
            是否成功
        """
        preset = self.get_preset(preset_name)
        if not preset:
            print(f"预设不存在: {preset_name}")
            return False

        from pyJianYingDraft.time_util import Timerange, tim

        # 确保轨道存在
        try:
            script.add_track(type(script).track_type.effect, track_name)
        except Exception:
            pass  # 轨道已存在

        for step in preset.effects:
            start_us = int((start_time + step.start) * 1_000_000)
            duration_us = int(step.duration * 1_000_000)
            try:
                script.add_effect(
                    step.effect_type,
                    Timerange(start_us, duration_us),
                    track_name=track_name,
                    params=step.params if step.params else None,
                )
            except Exception as e:
                print(f"  应用特效失败 {step.effect_name}: {e}")

        return True

    def get_preset_info(self, name: str) -> Dict[str, Any]:
        """获取预设详细信息"""
        preset = self.get_preset(name)
        if not preset:
            return {}
        return {
            "name": preset.name,
            "category": preset.category,
            "description": preset.description,
            "duration": preset.duration,
            "effect_count": len(preset.effects),
            "effects": [
                {
                    "name": e.effect_name,
                    "start": e.start,
                    "duration": e.duration,
                    "params": e.params,
                }
                for e in preset.effects
            ],
            "recommended_transition": preset.recommended_transition,
            "tags": preset.tags,
        }


# 全局单例
_library = None

def get_library() -> EffectPresetLibrary:
    """获取全局预设库单例"""
    global _library
    if _library is None:
        _library = EffectPresetLibrary()
    return _library


if __name__ == "__main__":
    lib = EffectPresetLibrary()
    print("=== 特效组合预设库 ===")
    print(f"预设总数: {len(lib.presets)}")
    print(f"分类: {lib.list_categories()}")
    print()

    for cat in lib.list_categories():
        names = lib.list_presets(cat)
        print(f"【{cat}】({len(names)}个)")
        for name in names:
            info = lib.get_preset_info(name)
            print(f"  - {name}: {info['description'][:40]}... ({info['effect_count']}特效, {info['duration']}秒)")
        print()
