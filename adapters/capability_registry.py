"""
能力注册中心 v1.0
统一管理所有底层skill的能力声明，ai-video-editor通过此中心查询和调用各skill能力。

设计原则：
1. 每个skill注册自己的能力清单（名称/描述/入口/依赖/状态）
2. ai-video-editor通过能力中心查询可用能力，不直接import其他skill
3. 支持能力降级（skill不可用时自动切换到替代方案）
4. 支持动态注册（新skill安装后自动发现）
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict


@dataclass
class Capability:
    """单个能力声明"""
    name: str                    # 能力名称（如 "text_to_image", "transparent_animation"）
    description: str             # 能力描述
    skill: str                   # 所属skill
    entry_point: str             # 入口模块/函数路径
    dependencies: List[str] = field(default_factory=list)  # 外部依赖
    status: str = "available"    # available / unavailable / degraded
    priority: int = 5            # 优先级（1-10，越高越优先）
    params: Dict[str, Any] = field(default_factory=dict)   # 典型参数


@dataclass
class SkillRegistration:
    """skill注册信息"""
    skill_id: str                # skill唯一标识
    name: str                    # 显示名称
    version: str                 # 版本号
    root_path: str               # skill根目录
    capabilities: List[Capability] = field(default_factory=list)
    status: str = "active"       # active / inactive / error
    last_check: float = 0.0      # 最后健康检查时间


class CapabilityRegistry:
    """能力注册中心（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.skills: Dict[str, SkillRegistration] = {}
        self._skill_root = Path(r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills")
        self._auto_discover()

    def _auto_discover(self):
        """自动发现已安装的skill并注册基础信息"""
        known_skills = {
            "jianying-editor": {
                "name": "剪映编辑器",
                "capabilities": [
                    Capability("draft_creation", "剪映草稿工程创建", "jianying-editor",
                               "scripts.jy_wrapper.JyProject", priority=10),
                    Capability("video_effects", "2309种视频特效", "jianying-editor",
                               "scripts.vendor.pyJianYingDraft.metadata", priority=9),
                    Capability("animations", "入场/出场/循环动画", "jianying-editor",
                               "scripts.vendor.pyJianYingDraft.animation", priority=9),
                    Capability("transitions", "130种转场效果", "jianying-editor",
                               "scripts.vendor.pyJianYingDraft.metadata.transition_meta", priority=8),
                    Capability("text_styles", "文字样式/字幕", "jianying-editor",
                               "scripts.vendor.pyJianYingDraft.text_segment", priority=8),
                    Capability("keyframes", "关键帧动画", "jianying-editor",
                               "scripts.vendor.pyJianYingDraft.keyframe", priority=8),
                ],
            },
            "comfyui-controls-skill": {
                "name": "ComfyUI控制器",
                "capabilities": [
                    Capability("text_to_image", "文生图（Z-Image-Turbo）", "comfyui-controls-skill",
                               "comfy_controls.ComfyControls.run_workflow", ["ComfyUI"], priority=8),
                    Capability("image_to_video", "图生视频（LTX/混元）", "comfyui-controls-skill",
                               "comfy_controls.ComfyControls.run_workflow", ["ComfyUI"], priority=8),
                    Capability("tts", "语音合成（Qwen3-TTS）", "comfyui-controls-skill",
                               "comfy_controls.ComfyControls.run_workflow", ["ComfyUI"], priority=7),
                    Capability("background_remove", "逐帧抠图", "comfyui-controls-skill",
                               "comfy_controls.ComfyControls.run_workflow", ["ComfyUI"], priority=7),
                    Capability("batch_generation", "批量生成", "comfyui-controls-skill",
                               "capabilities.cap_batch_generator", ["ComfyUI"], priority=6),
                ],
            },
            "blender-controls-skill": {
                "name": "Blender控制器",
                "capabilities": [
                    Capability("3d_intro", "3D片头生成", "blender-controls-skill",
                               "blender_controls.BlenderControls.render_intro", ["blender"], priority=6),
                    Capability("3d_effects", "3D特效库", "blender-controls-skill",
                               "blender_controls.BlenderControls.render_effect", ["blender"], priority=6),
                ],
            },
            "remotion-controls-skill": {
                "name": "Remotion控制器",
                "capabilities": [
                    Capability("transparent_animation", "透明背景动画（ProRes 4444）", "remotion-controls-skill",
                               "capabilities.cap_animation_renderer.renderer.AnimationRenderer",
                               ["node", "remotion", "ffmpeg"], priority=7),
                    Capability("animation_templates", "动画模板库（6内置+自定义）", "remotion-controls-skill",
                               "capabilities.cap_template_library.library.TemplateLibrary", priority=6),
                    Capability("keyframe_builder", "关键帧/多图层构建", "remotion-controls-skill",
                               "capabilities.cap_animation_renderer.renderer.KeyframeBuilder", priority=6),
                ],
            },
            "anysearch-skill": {
                "name": "深度搜索",
                "capabilities": [
                    Capability("deep_search", "23垂类深度搜索", "anysearch-skill",
                               "scripts.anysearch_cli", priority=5),
                    Capability("report_generation", "搜索报告生成", "anysearch-skill",
                               "scripts.generate", priority=5),
                ],
            },
            "ai-video-editor": {
                "name": "AI视频编辑器（本项目）",
                "capabilities": [
                    Capability("script_understanding", "剧本理解/情绪分析", "ai-video-editor",
                               "scripts.script_understanding_engine", priority=10),
                    Capability("storyboard_design", "分镜设计", "ai-video-editor",
                               "scripts.director_engine", priority=9),
                    Capability("photo_slideshow", "照片短视频生成（4风格）", "ai-video-editor",
                               "scripts.photo_slideshow_generator", priority=8),
                    Capability("multi_track_mix", "多轨混音", "ai-video-editor",
                               "scripts.multi_track_mixer", ["ffmpeg"], priority=7),
                    Capability("effect_api", "统一特效API", "ai-video-editor",
                               "scripts.jianying_effect_api", priority=8),
                ],
            },
        }

        for skill_id, info in known_skills.items():
            root = self._skill_root / skill_id
            registration = SkillRegistration(
                skill_id=skill_id,
                name=info["name"],
                version="1.0.0",
                root_path=str(root),
                capabilities=info["capabilities"],
                status="active" if root.exists() else "missing",
            )
            self.skills[skill_id] = registration

    def register(self, registration: SkillRegistration):
        """注册/更新skill"""
        self.skills[registration.skill_id] = registration

    def unregister(self, skill_id: str):
        """注销skill"""
        self.skills.pop(skill_id, None)

    def get_capability(self, name: str) -> Optional[Capability]:
        """按名称查找能力（返回优先级最高的可用能力）"""
        candidates = []
        for skill in self.skills.values():
            if skill.status != "active":
                continue
            for cap in skill.capabilities:
                if cap.name == name and cap.status == "available":
                    candidates.append(cap)
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.priority)

    def list_capabilities(self, skill_id: str = None) -> List[Capability]:
        """列出所有能力（可按skill过滤）"""
        result = []
        for skill in self.skills.values():
            if skill_id and skill.skill_id != skill_id:
                continue
            result.extend(skill.capabilities)
        return result

    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有注册的skill"""
        return [
            {
                "id": s.skill_id,
                "name": s.name,
                "version": s.version,
                "status": s.status,
                "capabilities": len(s.capabilities),
                "path": s.root_path,
            }
            for s in self.skills.values()
        ]

    def check_health(self) -> Dict[str, str]:
        """健康检查：验证各skill根目录存在"""
        import time
        results = {}
        for skill in self.skills.values():
            exists = Path(skill.root_path).exists()
            skill.status = "active" if exists else "missing"
            skill.last_check = time.time()
            results[skill.skill_id] = skill.status
        return results

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "skills": {
                sid: {
                    "name": s.name,
                    "version": s.version,
                    "status": s.status,
                    "capabilities": [asdict(c) for c in s.capabilities],
                }
                for sid, s in self.skills.items()
            }
        }

    def save(self, path: str):
        """保存注册信息到JSON"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


# 便捷函数
def get_registry() -> CapabilityRegistry:
    """获取全局注册中心实例"""
    return CapabilityRegistry()


if __name__ == "__main__":
    registry = get_registry()
    print("=== 已注册Skill ===")
    for s in registry.list_skills():
        print(f"  [{s['status']}] {s['name']} ({s['id']}) - {s['capabilities']}个能力")
    print()
    print("=== 所有能力 ===")
    for cap in registry.list_capabilities():
        print(f"  {cap.name}: {cap.description} (优先级{cap.priority})")
    print()
    print("=== 健康检查 ===")
    for sid, status in registry.check_health().items():
        print(f"  {sid}: {status}")
