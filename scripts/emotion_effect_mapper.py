"""
P2-4: 情绪→特效智能映射增强模块
基于剪映1779个有参数特效，建立6种情绪→特效组合映射，支持参数自动调节

使用方式:
    from emotion_effect_mapper import EmotionEffectMapper
    mapper = EmotionEffectMapper()
    effects = mapper.get_effects_for_emotion("激昂", intensity=0.8)
    for effect in effects:
        script.add_effect(effect["type"], effect["timerange"], params=effect["params"])
"""

import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

# 添加jianying-editor路径
JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
if JY_SKILL not in sys.path:
    sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))
    sys.path.insert(0, os.path.join(JY_SKILL, "scripts", "vendor"))

from pyJianYingDraft.metadata.video_scene_effect import VideoSceneEffectType
from pyJianYingDraft.metadata.filter_meta import FilterType
from pyJianYingDraft.metadata.transition_meta import TransitionType


@dataclass
class EffectPreset:
    """特效预设"""
    name: str
    effect_type: Any  # VideoSceneEffectType / FilterType / TransitionType
    category: str  # "video_effect" / "filter" / "transition"
    params: List[float] = field(default_factory=list)  # 0-100范围
    description: str = ""
    min_intensity: float = 0.0  # 适用的最低情绪强度
    max_intensity: float = 1.0  # 适用的最高情绪强度


@dataclass
class EmotionEffectPackage:
    """情绪特效包"""
    emotion: str
    description: str
    video_effects: List[EffectPreset] = field(default_factory=list)
    filters: List[EffectPreset] = field(default_factory=list)
    transitions: List[EffectPreset] = field(default_factory=list)
    recommended_params: Dict[str, float] = field(default_factory=dict)


class EmotionEffectMapper:
    """情绪→特效智能映射器"""

    def __init__(self):
        self.packages = self._build_packages()

    def _build_packages(self) -> Dict[str, EmotionEffectPackage]:
        """构建6种情绪的特效包"""
        packages = {}

        # ========== 1. 激昂 ==========
        packages["激昂"] = EmotionEffectPackage(
            emotion="激昂",
            description="高能、动感、冲击力强，适合高潮、转场、产品展示",
            recommended_params={"speed": 75, "intensity": 70, "filter": 60},
            video_effects=[
                EffectPreset("RGB描边", VideoSceneEffectType.RGB描边, "video_effect",
                            [70, 60, 50], "赛博朋克风格描边", 0.5, 1.0),
                EffectPreset("X-Signal", VideoSceneEffectType.X_Signal, "video_effect",
                            [80], "故障信号效果", 0.6, 1.0),
                EffectPreset("噪点", VideoSceneEffectType.噪点, "video_effect",
                            [60, 30, 70, 80, 40, 50], "彩色噪点颗粒", 0.4, 1.0),
                EffectPreset("动感竖线", VideoSceneEffectType.动感竖线, "video_effect",
                            [60, 50, 40, 80, 20, 90, 50, 70], "动感竖线扫描", 0.5, 1.0),
                EffectPreset("变色闪光", VideoSceneEffectType.变色闪光, "video_effect",
                            [70, 40, 30, 80, 50, 90, 60, 70], "彩色闪光", 0.6, 1.0),
                EffectPreset("像素屏闪", VideoSceneEffectType.像素屏闪, "video_effect",
                            [70, 70, 30, 60, 60, 80, 50], "像素化闪烁", 0.5, 1.0),
                EffectPreset("双重辉光", VideoSceneEffectType.双重辉光, "video_effect",
                            [50, 40, 80, 70, 80, 100, 70], "双重发光效果", 0.4, 1.0),
                EffectPreset("发光HDR", VideoSceneEffectType.发光HDR, "video_effect",
                            [60, 70, 60, 50, 70, 80, 90, 30], "HDR发光", 0.5, 1.0),
                EffectPreset("故障", VideoSceneEffectType.故障, "video_effect",
                            [50, 50, 40, 40, 40, 70, 40], "故障效果", 0.6, 1.0),
                EffectPreset("变速推镜", VideoSceneEffectType.变速推镜, "video_effect",
                            [60, 30, 80, 100, 100, 70, 50], "变速推进镜头", 0.5, 1.0),
            ],
            filters=[
                EffectPreset("高对比", None, "filter", [80], "高对比度滤镜"),
                EffectPreset("锐化", None, "filter", [70], "锐化增强"),
                EffectPreset("色彩增强", None, "filter", [65], "饱和度提升"),
            ],
        )

        # ========== 2. 舒缓 ==========
        packages["舒缓"] = EmotionEffectPackage(
            emotion="舒缓",
            description="柔和、缓慢、文艺，适合回忆、慢镜头、情感表达",
            recommended_params={"speed": 30, "blur": 60, "luminance": 65},
            video_effects=[
                EffectPreset("模糊", VideoSceneEffectType.模糊, "video_effect",
                            [70, 80, 40], "模糊聚焦效果", 0.0, 0.7),
                EffectPreset("丁达尔旋焦", VideoSceneEffectType.丁达尔旋焦, "video_effect",
                            [80, 50, 60, 50, 50, 40, 100], "丁达尔光效", 0.0, 0.6),
                EffectPreset("梦幻辉光", VideoSceneEffectType.梦幻辉光, "video_effect",
                            [60, 70, 60, 50, 60, 70, 40], "梦幻发光", 0.0, 0.6),
                EffectPreset("动感模糊", VideoSceneEffectType.动感模糊, "video_effect",
                            [50, 70, 50, 100, 50, 50, 100], "动感模糊", 0.0, 0.7),
                EffectPreset("爱心光斑", VideoSceneEffectType.爱心光斑, "video_effect",
                            [60, 40, 40, 80, 50, 30, 60, 40, 40], "爱心散景", 0.0, 0.5),
                EffectPreset("爱心扫光", VideoSceneEffectType.爱心扫光, "video_effect",
                            [60, 40, 50, 40, 70, 50, 70, 60], "爱心形扫光", 0.0, 0.6),
                EffectPreset("VCR", VideoSceneEffectType.VCR, "video_effect",
                            [40, 50, 60, 50, 40], "VCR复古", 0.2, 0.8),
                EffectPreset("90s画质", VideoSceneEffectType._90s画质, "video_effect",
                            [60, 50, 40, 40], "90年代画质", 0.2, 0.7),
                EffectPreset("MV封面", VideoSceneEffectType.MV封面, "video_effect",
                            [50, 60], "MV风格封面", 0.1, 0.6),
                EffectPreset("JVC", VideoSceneEffectType.JVC, "video_effect",
                            [40, 50, 60], "JVC复古画质", 0.2, 0.7),
            ],
            filters=[
                EffectPreset("柔焦", None, "filter", [50], "柔焦滤镜"),
                EffectPreset("低饱和", None, "filter", [40], "低饱和度"),
                EffectPreset("暖色调", None, "filter", [55], "暖色调"),
            ],
        )

        # ========== 3. 紧张 ==========
        packages["紧张"] = EmotionEffectPackage(
            emotion="紧张",
            description="悬疑、压迫、纪实感，适合悬疑、恐怖、纪实",
            recommended_params={"speed": 45, "noise": 60, "filter": 65},
            video_effects=[
                EffectPreset("CCD闪光", VideoSceneEffectType.CCD闪光, "video_effect",
                            [50, 70, 60, 70], "CCD相机闪光", 0.3, 1.0),
                EffectPreset("DV录制框", VideoSceneEffectType.DV录制框, "video_effect",
                            [40, 60, 70, 50], "DV录制框", 0.4, 0.9),
                EffectPreset("betamax", VideoSceneEffectType.betamax, "video_effect",
                            [60, 70, 50, 60, 50, 40], "Betamax复古", 0.4, 0.9),
                EffectPreset("圆形监控", VideoSceneEffectType.圆形监控, "video_effect",
                            [40, 50, 70, 80, 40, 30, 30, 50, 50], "监控画面", 0.5, 1.0),
                EffectPreset("黑色老电视", VideoSceneEffectType.黑色老电视, "video_effect",
                            [60, 50], "老电视效果", 0.4, 0.9),
                EffectPreset("抽帧拖影", VideoSceneEffectType.抽帧拖影, "video_effect",
                            [50, 50, 50, 50, 50], "抽帧拖影", 0.5, 1.0),
                EffectPreset("X开幕", VideoSceneEffectType.X开幕, "video_effect",
                            [50], "X形开幕", 0.6, 1.0),
                EffectPreset("动态侦测", VideoSceneEffectType.动态侦测, "video_effect",
                            [55, 70, 98, 30, 80, 30, 70, 30, 20], "动态侦测框", 0.5, 1.0),
                EffectPreset("局部推镜", VideoSceneEffectType.局部推镜, "video_effect",
                            [40, 60, 60, 50, 40, 50, 50], "局部推进", 0.4, 0.9),
                EffectPreset("I_Lose_You", VideoSceneEffectType.I_Lose_You, "video_effect",
                            [40], "失落感效果", 0.3, 0.8),
            ],
            filters=[
                EffectPreset("冷色调", None, "filter", [60], "冷色调"),
                EffectPreset("暗角", None, "filter", [50], "暗角"),
                EffectPreset("高对比", None, "filter", [55], "高对比"),
            ],
        )

        # ========== 4. 温馨 ==========
        packages["温馨"] = EmotionEffectPackage(
            emotion="温馨",
            description="温暖、治愈、柔和，适合生活记录、宠物、亲子",
            recommended_params={"luminance": 65, "color_warm": 60, "intensity": 50},
            video_effects=[
                EffectPreset("梦幻辉光", VideoSceneEffectType.梦幻辉光, "video_effect",
                            [55, 65, 55, 55, 60, 65, 45], "温暖发光", 0.0, 0.7),
                EffectPreset("爱心光斑", VideoSceneEffectType.爱心光斑, "video_effect",
                            [55, 35, 45, 70, 45, 35, 55, 45, 45], "温暖散景", 0.0, 0.6),
                EffectPreset("爱心扫光", VideoSceneEffectType.爱心扫光, "video_effect",
                            [55, 45, 50, 45, 65, 50, 65, 55], "温暖扫光", 0.0, 0.6),
                EffectPreset("丁达尔旋焦", VideoSceneEffectType.丁达尔旋焦, "video_effect",
                            [70, 45, 55, 45, 45, 35, 90], "温暖光效", 0.0, 0.5),
                EffectPreset("模糊", VideoSceneEffectType.模糊, "video_effect",
                            [60, 70, 35], "柔和聚焦", 0.0, 0.6),
                EffectPreset("New_Year", VideoSceneEffectType.New_Year, "video_effect",
                            [50, 50, 50, 50, 50], "新年氛围", 0.2, 0.7),
                EffectPreset("I_Love_You", VideoSceneEffectType.I_Love_You, "video_effect",
                            [40], "爱意表达", 0.0, 0.5),
                EffectPreset("MV封面", VideoSceneEffectType.MV封面, "video_effect",
                            [45, 55], "温馨MV风格", 0.1, 0.6),
                EffectPreset("发光HDR", VideoSceneEffectType.发光HDR, "video_effect",
                            [50, 55, 50, 45, 60, 70, 80, 25], "温暖HDR", 0.1, 0.6),
                EffectPreset("动感模糊", VideoSceneEffectType.动感模糊, "video_effect",
                            [45, 60, 45, 90, 45, 45, 90], "柔和模糊", 0.0, 0.5),
            ],
            filters=[
                EffectPreset("暖色调", None, "filter", [60], "暖色调"),
                EffectPreset("柔焦", None, "filter", [45], "柔焦"),
                EffectPreset("光晕", None, "filter", [50], "光晕"),
            ],
        )

        # ========== 5. 高潮 ==========
        packages["高潮"] = EmotionEffectPackage(
            emotion="高潮",
            description="爆发、震撼、极致冲击，适合高潮点、结尾爆发",
            recommended_params={"speed": 85, "intensity": 80, "saturation": 75},
            video_effects=[
                EffectPreset("RGB描边", VideoSceneEffectType.RGB描边, "video_effect",
                            [80, 70, 60], "强烈描边", 0.6, 1.0),
                EffectPreset("彩噪画质", VideoSceneEffectType.彩噪画质, "video_effect",
                            [70, 40, 80, 90, 50, 60], "强烈噪点", 0.6, 1.0),
                EffectPreset("变色闪光", VideoSceneEffectType.变色闪光, "video_effect",
                            [80, 50, 40, 90, 60, 100, 70, 80], "强烈闪光", 0.7, 1.0),
                EffectPreset("像素屏闪", VideoSceneEffectType.像素屏闪, "video_effect",
                            [80, 80, 40, 70, 70, 90, 60], "强烈屏闪", 0.7, 1.0),
                EffectPreset("动感竖线", VideoSceneEffectType.动感竖线, "video_effect",
                            [70, 60, 50, 90, 30, 100, 60, 80], "强烈动感", 0.6, 1.0),
                EffectPreset("双重辉光", VideoSceneEffectType.双重辉光, "video_effect",
                            [60, 50, 90, 80, 90, 100, 80], "强烈辉光", 0.6, 1.0),
                EffectPreset("弯曲故障", VideoSceneEffectType.弯曲故障, "video_effect",
                            [60, 60, 50, 50, 50, 80, 50], "强烈故障", 0.7, 1.0),
                EffectPreset("X-Signal", VideoSceneEffectType.X_Signal, "video_effect",
                            [90], "强烈信号", 0.7, 1.0),
                EffectPreset("变速推镜", VideoSceneEffectType.变速推镜, "video_effect",
                            [70, 40, 90, 100, 100, 80, 60], "强烈推进", 0.6, 1.0),
                EffectPreset("发光HDR", VideoSceneEffectType.发光HDR, "video_effect",
                            [70, 80, 70, 60, 80, 90, 100, 40], "强烈HDR", 0.6, 1.0),
            ],
            filters=[
                EffectPreset("过曝", None, "filter", [70], "过曝"),
                EffectPreset("高饱和", None, "filter", [75], "高饱和"),
                EffectPreset("动态模糊", None, "filter", [60], "动态模糊"),
            ],
        )

        # ========== 6. 收束 ==========
        packages["收束"] = EmotionEffectPackage(
            emotion="收束",
            description="渐弱、平静、收尾，适合结尾、淡出、回忆",
            recommended_params={"speed": 25, "blur": 50, "luminance": 40},
            video_effects=[
                EffectPreset("模糊", VideoSceneEffectType.模糊, "video_effect",
                            [80, 90, 30], "渐强模糊", 0.0, 0.5),
                EffectPreset("曲线模糊", VideoSceneEffectType.曲线模糊, "video_effect",
                            [40, 80, 40, 100, 40, 40, 100], "渐强模糊", 0.0, 0.5),
                EffectPreset("VCR", VideoSceneEffectType.VCR, "video_effect",
                            [30, 40, 50, 40, 30], "复古收尾", 0.0, 0.6),
                EffectPreset("90s画质", VideoSceneEffectType._90s画质, "video_effect",
                            [50, 40, 30, 30], "年代收尾", 0.0, 0.5),
                EffectPreset("MV封面", VideoSceneEffectType.MV封面, "video_effect",
                            [40, 50], "MV收尾", 0.0, 0.5),
                EffectPreset("梦幻辉光", VideoSceneEffectType.梦幻辉光, "video_effect",
                            [50, 60, 50, 50, 55, 60, 35], "渐弱辉光", 0.0, 0.5),
                EffectPreset("丁达尔旋焦", VideoSceneEffectType.丁达尔旋焦, "video_effect",
                            [60, 40, 50, 40, 40, 30, 80], "渐弱光效", 0.0, 0.4),
                EffectPreset("JVC", VideoSceneEffectType.JVC, "video_effect",
                            [30, 40, 50], "JVC收尾", 0.0, 0.5),
                EffectPreset("70s", VideoSceneEffectType._70s, "video_effect",
                            [30], "70年代收尾", 0.0, 0.4),
                EffectPreset("1998", VideoSceneEffectType._1998, "video_effect",
                            [50, 50], "1998收尾", 0.0, 0.5),
            ],
            filters=[
                EffectPreset("渐暗", None, "filter", [60], "渐暗"),
                EffectPreset("低饱和", None, "filter", [50], "低饱和"),
                EffectPreset("柔焦", None, "filter", [55], "柔焦"),
            ],
        )

        return packages

    def get_effects_for_emotion(
        self,
        emotion: str,
        intensity: float = 0.5,
        max_effects: int = 5,
        include_filters: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        获取指定情绪的特效组合

        Args:
            emotion: 情绪名称（激昂/舒缓/紧张/温馨/高潮/收束）
            intensity: 情绪强度 0.0-1.0
            max_effects: 最多返回的特效数量
            include_filters: 是否包含滤镜

        Returns:
            特效列表，每个特效包含:
            - name: 特效名称
            - type: 特效类型对象（VideoSceneEffectType等）
            - category: "video_effect" / "filter"
            - params: 参数列表（0-100范围）
            - description: 描述
        """
        if emotion not in self.packages:
            raise ValueError(f"不支持的情绪: {emotion}，支持: {list(self.packages.keys())}")

        package = self.packages[emotion]
        results = []

        # 筛选适用强度范围的视频特效
        applicable = [
            e for e in package.video_effects
            if e.min_intensity <= intensity <= e.max_intensity
        ]

        # 按与强度的匹配度排序
        def match_score(preset):
            mid = (preset.min_intensity + preset.max_intensity) / 2
            return -abs(intensity - mid)

        applicable.sort(key=match_score)

        for preset in applicable[:max_effects]:
            # 根据强度调整参数
            adjusted_params = self._adjust_params_by_intensity(preset.params, intensity)
            results.append({
                "name": preset.name,
                "type": preset.effect_type,
                "category": preset.category,
                "params": adjusted_params,
                "description": preset.description,
            })

        # 添加滤镜
        if include_filters:
            for preset in package.filters[:2]:
                results.append({
                    "name": preset.name,
                    "type": None,  # FilterType需要单独处理
                    "category": "filter",
                    "params": preset.params,
                    "description": preset.description,
                })

        return results

    def _adjust_params_by_intensity(self, params: List[float], intensity: float) -> List[float]:
        """根据情绪强度调整参数"""
        if not params:
            return params
        # 强度越高，参数值越偏向高值
        factor = 0.7 + 0.6 * intensity  # 0.7-1.3
        return [min(100, max(0, p * factor)) for p in params]

    def list_emotions(self) -> List[str]:
        """列出所有支持的情绪"""
        return list(self.packages.keys())

    def get_emotion_info(self, emotion: str) -> Dict[str, Any]:
        """获取情绪详细信息"""
        if emotion not in self.packages:
            raise ValueError(f"不支持的情绪: {emotion}")
        pkg = self.packages[emotion]
        return {
            "emotion": pkg.emotion,
            "description": pkg.description,
            "video_effect_count": len(pkg.video_effects),
            "filter_count": len(pkg.filters),
            "recommended_params": pkg.recommended_params,
            "video_effects": [e.name for e in pkg.video_effects],
            "filters": [e.name for e in pkg.filters],
        }


# 全局单例
_mapper = None

def get_mapper() -> EmotionEffectMapper:
    """获取全局映射器单例"""
    global _mapper
    if _mapper is None:
        _mapper = EmotionEffectMapper()
    return _mapper


if __name__ == "__main__":
    mapper = EmotionEffectMapper()
    print("=== 情绪→特效映射测试 ===")
    print(f"支持情绪: {mapper.list_emotions()}")
    print()

    for emotion in mapper.list_emotions():
        info = mapper.get_emotion_info(emotion)
        print(f"【{emotion}】{info['description']}")
        print(f"  视频特效: {info['video_effect_count']}个")
        print(f"  滤镜: {info['filter_count']}个")
        print(f"  推荐参数: {info['recommended_params']}")
        print()

    # 测试获取特效
    print("=== 激昂(强度0.8)推荐特效 ===")
    effects = mapper.get_effects_for_emotion("激昂", intensity=0.8, max_effects=5)
    for e in effects:
        print(f"  {e['name']}: params={e['params'][:3]}...")
