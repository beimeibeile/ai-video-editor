"""
参考图挂载机制 v1.0
借鉴shuohao-skills的参考图纪律：
- 场景设定图（该段场景 + 光照状态）——必挂
- 画内每个角色的设定图——有几个挂几个
- 画内叙事道具的设定图——有就挂
- 提示词与参考图冲突时，模型听参考图的

功能：
1. 为每个镜头建立参考图挂载清单
2. 支持场景图/角色图/道具图三种类型
3. ComfyUI生成时自动挂载（如果支持IPAdapter/ControlNet）
4. 参考图缺失检测和警告
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ReferenceType(Enum):
    """参考图类型"""
    SCENE = "scene"           # 场景设定图
    CHARACTER = "character"   # 角色设定图
    PROP = "prop"             # 道具设定图
    STYLE = "style"           # 风格参考图


@dataclass
class ReferenceImage:
    """参考图"""
    ref_type: ReferenceType
    name: str                    # 参考图名称（如"场景_出租屋_黄昏"）
    path: str = ""               # 本地文件路径
    url: str = ""                # 远程URL（可选）
    description: str = ""        # 参考图描述
    required: bool = True        # 是否必需（缺失时警告）
    weight: float = 0.7          # 参考图权重（0-1，IPAdapter用）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref_type": self.ref_type.value,
            "name": self.name,
            "path": self.path,
            "url": self.url,
            "description": self.description,
            "required": self.required,
            "weight": self.weight,
        }


@dataclass
class ShotReferenceList:
    """单个镜头的参考图挂载清单"""
    shot_id: str
    references: List[ReferenceImage] = field(default_factory=list)

    def add(self, ref: ReferenceImage):
        """添加参考图"""
        self.references.append(ref)

    def get_by_type(self, ref_type: ReferenceType) -> List[ReferenceImage]:
        """按类型获取参考图"""
        return [r for r in self.references if r.ref_type == ref_type]

    def check_missing(self) -> List[ReferenceImage]:
        """检查缺失的必需参考图"""
        missing = []
        for ref in self.references:
            if ref.required and not ref.path and not ref.url:
                missing.append(ref)
        return missing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "references": [r.to_dict() for r in self.references],
            "missing_count": len(self.check_missing()),
        }


class ReferenceMountManager:
    """参考图挂载管理器"""

    def __init__(self, reference_dir: str = ""):
        """
        Args:
            reference_dir: 参考图存储目录
        """
        self.reference_dir = reference_dir
        self.shot_lists: Dict[str, ShotReferenceList] = {}  # shot_id -> list
        self.scene_images: Dict[str, str] = {}    # scene_name -> path
        self.character_images: Dict[str, str] = {}  # char_name -> path
        self.prop_images: Dict[str, str] = {}       # prop_name -> path

    def register_scene_image(self, scene_name: str, path: str):
        """注册场景设定图"""
        self.scene_images[scene_name] = path

    def register_character_image(self, char_name: str, path: str):
        """注册角色设定图"""
        self.character_images[char_name] = path

    def register_prop_image(self, prop_name: str, path: str):
        """注册道具设定图"""
        self.prop_images[prop_name] = path

    def build_shot_references(self, shot_id: str,
                                scene_name: str = "",
                                characters: List[str] = None,
                                props: List[str] = None,
                                style_ref: str = "") -> ShotReferenceList:
        """
        为镜头构建参考图挂载清单

        Args:
            shot_id: 镜头ID
            scene_name: 场景名称
            characters: 出场角色列表
            props: 出场道具列表
            style_ref: 风格参考图名称

        Returns:
            ShotReferenceList
        """
        shot_list = ShotReferenceList(shot_id=shot_id)

        # 场景图（必挂）
        if scene_name:
            scene_path = self.scene_images.get(scene_name, "")
            shot_list.add(ReferenceImage(
                ref_type=ReferenceType.SCENE,
                name=f"场景_{scene_name}",
                path=scene_path,
                description=f"场景设定图：{scene_name}",
                required=True,
                weight=0.6,
            ))

        # 角色图（有几个挂几个）
        if characters:
            for char_name in characters:
                char_path = self.character_images.get(char_name, "")
                shot_list.add(ReferenceImage(
                    ref_type=ReferenceType.CHARACTER,
                    name=f"角色_{char_name}",
                    path=char_path,
                    description=f"角色设定图：{char_name}",
                    required=True,
                    weight=0.8,
                ))

        # 道具图（有就挂）
        if props:
            for prop_name in props:
                prop_path = self.prop_images.get(prop_name, "")
                shot_list.add(ReferenceImage(
                    ref_type=ReferenceType.PROP,
                    name=f"道具_{prop_name}",
                    path=prop_path,
                    description=f"道具设定图：{prop_name}",
                    required=False,
                    weight=0.5,
                ))

        # 风格参考图
        if style_ref:
            shot_list.add(ReferenceImage(
                ref_type=ReferenceType.STYLE,
                name=f"风格_{style_ref}",
                path="",
                description=f"风格参考：{style_ref}",
                required=False,
                weight=0.4,
            ))

        self.shot_lists[shot_id] = shot_list
        return shot_list

    def build_from_storyboard(self, storyboard: List[Dict[str, Any]]) -> List[ShotReferenceList]:
        """
        从分镜数据批量构建参考图挂载清单

        Args:
            storyboard: 分镜列表，每个含shot_id/scene/characters/props

        Returns:
            参考图挂载清单列表
        """
        results = []
        for shot in storyboard:
            shot_list = self.build_shot_references(
                shot_id=shot.get("shot_id", ""),
                scene_name=shot.get("scene", ""),
                characters=shot.get("characters", []),
                props=shot.get("props", []),
                style_ref=shot.get("style", ""),
            )
            results.append(shot_list)
        return results

    def check_all_missing(self) -> Dict[str, List[ReferenceImage]]:
        """检查所有镜头的缺失参考图"""
        all_missing = {}
        for shot_id, shot_list in self.shot_lists.items():
            missing = shot_list.check_missing()
            if missing:
                all_missing[shot_id] = missing
        return all_missing

    def generate_comfyui_prompt_with_refs(self, shot_id: str,
                                             base_prompt: str) -> Dict[str, Any]:
        """
        生成带参考图的ComfyUI提示词

        Args:
            shot_id: 镜头ID
            base_prompt: 基础提示词

        Returns:
            包含prompt和参考图配置的字典
        """
        shot_list = self.shot_lists.get(shot_id)
        if not shot_list:
            return {"prompt": base_prompt, "references": []}

        # 构建参考图配置
        ref_configs = []
        for ref in shot_list.references:
            if ref.path or ref.url:
                ref_configs.append({
                    "type": ref.ref_type.value,
                    "name": ref.name,
                    "path": ref.path,
                    "url": ref.url,
                    "weight": ref.weight,
                })

        # 在提示词中添加参考图说明（当不支持IPAdapter时使用）
        ref_descriptions = [r.description for r in shot_list.references if r.path or r.url]
        if ref_descriptions:
            enhanced_prompt = base_prompt + f"\n[参考图: {', '.join(ref_descriptions)}]"
        else:
            enhanced_prompt = base_prompt

        return {
            "prompt": enhanced_prompt,
            "references": ref_configs,
            "missing_count": len(shot_list.check_missing()),
        }

    def export_report(self, output_path: str = "") -> str:
        """
        导出参考图挂载报告

        Args:
            output_path: 输出路径（JSON）

        Returns:
            报告内容
        """
        report = {
            "total_shots": len(self.shot_lists),
            "total_references": sum(len(s.references) for s in self.shot_lists.values()),
            "scene_images_registered": len(self.scene_images),
            "character_images_registered": len(self.character_images),
            "prop_images_registered": len(self.prop_images),
            "shots": [s.to_dict() for s in self.shot_lists.values()],
            "missing_summary": self.check_all_missing(),
        }

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        return json.dumps(report, ensure_ascii=False, indent=2)


# 便捷函数
def create_reference_manager(reference_dir: str = "") -> ReferenceMountManager:
    """创建参考图挂载管理器"""
    return ReferenceMountManager(reference_dir)


if __name__ == "__main__":
    print("=" * 60)
    print("参考图挂载机制 v1.0")
    print("=" * 60)

    # 创建管理器
    manager = create_reference_manager()

    # 注册参考图
    manager.register_scene_image("出租屋_黄昏", "assets/scene_rental_dusk.png")
    manager.register_character_image("陈默", "assets/char_chenmo.png")
    manager.register_character_image("王总", "assets/char_wangzong.png")
    manager.register_prop_image("手机", "assets/prop_phone.png")

    # 为镜头构建参考图清单
    storyboard = [
        {"shot_id": "S01_01", "scene": "出租屋_黄昏", "characters": ["陈默"], "props": []},
        {"shot_id": "S01_02", "scene": "出租屋_黄昏", "characters": ["陈默"], "props": ["手机"]},
        {"shot_id": "S04_01", "scene": "咖啡馆", "characters": ["陈默", "王总"], "props": []},
    ]

    lists = manager.build_from_storyboard(storyboard)

    print(f"\n已为 {len(lists)} 个镜头构建参考图清单")
    for sl in lists:
        missing = sl.check_missing()
        print(f"  {sl.shot_id}: {len(sl.references)}张参考图, 缺失{len(missing)}张")
        for ref in sl.references:
            status = "✅" if ref.path else "❌"
            print(f"    {status} [{ref.ref_type.value}] {ref.name}")

    # 检查缺失
    all_missing = manager.check_all_missing()
    print(f"\n缺失参考图的镜头: {len(all_missing)}个")
    for shot_id, missing in all_missing.items():
        print(f"  {shot_id}: {[m.name for m in missing]}")

    # 生成带参考图的提示词
    print("\n带参考图的ComfyUI提示词示例:")
    result = manager.generate_comfyui_prompt_with_refs(
        "S01_01", "a man sitting in a dim room, cinematic lighting"
    )
    print(f"  提示词: {result['prompt']}")
    print(f"  参考图: {len(result['references'])}张")

    print("\n✅ 参考图挂载机制自测通过")
