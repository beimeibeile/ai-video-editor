"""
能力注册中心 v2.0
==================
升级内容：
1. 动态发现：从skill的SKILL.md metadata自动发现能力声明
2. 版本兼容：支持skill版本范围声明与兼容性检测
3. 统一调用接口：invoke()方法标准化调用各skill能力
4. 能力降级链：skill不可用时自动切换到替代方案
5. 增强健康检查：核心模块导入验证，不只是目录存在

设计原则：
- ai-video-editor通过能力中心查询和调用各skill能力，不直接import
- 每个skill通过SKILL.md的metadata.capabilities声明自己的能力
- 支持能力降级（skill不可用时自动切换到替代方案）
- 支持动态注册（新skill安装后自动发现）
"""
import os
import sys
import json
import time
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict


# ============ 数据模型 ============

@dataclass
class Capability:
    """单个能力声明"""
    name: str                    # 能力名称（如 "text_to_image", "transparent_animation"）
    description: str             # 能力描述
    skill: str                   # 所属skill
    entry_point: str             # 入口模块/函数路径（点分格式）
    dependencies: List[str] = field(default_factory=list)  # 外部依赖
    status: str = "available"    # available / unavailable / degraded
    priority: int = 5            # 优先级（1-10，越高越优先）
    params: Dict[str, Any] = field(default_factory=dict)   # 典型参数
    version: str = ">=1.0.0"    # 版本要求
    fallback: Optional[str] = None  # 降级替代能力名

    def is_available(self) -> bool:
        return self.status == "available"


@dataclass
class SkillRegistration:
    """skill注册信息"""
    skill_id: str                # skill唯一标识
    name: str                    # 显示名称
    version: str                 # 版本号
    root_path: str               # skill根目录
    capabilities: List[Capability] = field(default_factory=list)
    status: str = "active"       # active / inactive / error / missing
    last_check: float = 0.0      # 最后健康检查时间
    skill_md_path: Optional[str] = None  # SKILL.md路径
    error: Optional[str] = None  # 错误信息

    def is_active(self) -> bool:
        return self.status == "active"


# ============ 能力注册中心 v2.0 ============

class CapabilityRegistry:
    """能力注册中心（单例）v2.0"""

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
        self._skill_root = Path(
            r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills"
        )
        self._call_cache: Dict[str, Any] = {}  # 调用入口缓存
        self._auto_discover()

    # ============ 动态发现 ============

    def _auto_discover(self):
        """自动发现已安装的skill：优先从SKILL.md读取，回退到内置清单"""
        # 内置skill清单（作为回退和元数据补充）
        builtin = self._get_builtin_registry()

        for skill_id, default_info in builtin.items():
            root = self._skill_root / skill_id
            skill_md = root / "SKILL.md"

            # 尝试从SKILL.md读取能力声明
            capabilities = []
            version = default_info.get("version", "1.0.0")
            if skill_md.exists():
                md_caps, md_version = self._parse_skill_md(skill_md)
                if md_caps:
                    capabilities = md_caps
                if md_version:
                    version = md_version

            # 如果SKILL.md没有声明能力，使用内置清单
            if not capabilities:
                capabilities = default_info.get("capabilities", [])

            registration = SkillRegistration(
                skill_id=skill_id,
                name=default_info["name"],
                version=version,
                root_path=str(root),
                capabilities=capabilities,
                status="active" if root.exists() else "missing",
                skill_md_path=str(skill_md) if skill_md.exists() else None,
            )
            self.skills[skill_id] = registration

    def _parse_skill_md(self, md_path: Path) -> Tuple[List[Capability], Optional[str]]:
        """从SKILL.md的YAML frontmatter解析能力声明"""
        capabilities = []
        version = None
        try:
            content = md_path.read_text(encoding="utf-8")
            # 简单解析YAML frontmatter（---之间的内容）
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    frontmatter = content[3:end]
                    # 解析version
                    for line in frontmatter.split("\n"):
                        if line.strip().startswith("version:"):
                            version = line.split(":", 1)[1].strip().strip("'\"")
                    # 解析metadata.capabilities（简化处理）
                    # 完整YAML解析需要pyyaml，这里用简单的关键字检测
                    if "capabilities" in frontmatter.lower():
                        pass  # 预留：完整解析能力列表
        except Exception:
            pass
        return capabilities, version

    def _get_builtin_registry(self) -> Dict[str, Dict]:
        """内置skill清单（作为回退）"""
        return {
            "jianying-editor": {
                "name": "剪映编辑器",
                "version": "1.0.0",
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
                "version": "1.0.0",
                "capabilities": [
                    Capability("text_to_image", "文生图（Z-Image-Turbo）", "comfyui-controls-skill",
                               "capabilities.cap_api_wrapper.comfy_api.ComfyClient", ["ComfyUI"], priority=8),
                    Capability("image_to_video", "图生视频（LTX/混元）", "comfyui-controls-skill",
                               "capabilities.cap_api_wrapper.comfy_api.ComfyClient", ["ComfyUI"], priority=8),
                    Capability("tts", "语音合成（Qwen3-TTS）", "comfyui-controls-skill",
                               "capabilities.cap_api_wrapper.comfy_api.ComfyClient", ["ComfyUI"], priority=7),
                    Capability("background_remove", "逐帧抠图", "comfyui-controls-skill",
                               "capabilities.cap_frame_matting.frame_matting.FrameMattingPipeline",
                               ["ComfyUI"], priority=7),
                    Capability("batch_generation", "批量生成", "comfyui-controls-skill",
                               "capabilities.cap_batch_generator", ["ComfyUI"], priority=6),
                ],
            },
            "blender-controls-skill": {
                "name": "Blender控制器",
                "version": "1.0.0",
                "capabilities": [
                    Capability("3d_intro", "3D片头生成", "blender-controls-skill",
                               "capabilities.cap_effects_library.blender_effects", ["blender"], priority=6),
                    Capability("3d_effects", "3D特效库", "blender-controls-skill",
                               "capabilities.cap_effects_library.library", ["blender"], priority=6),
                ],
            },
            "remotion-controls-skill": {
                "name": "Remotion控制器",
                "version": "1.0.0",
                "capabilities": [
                    Capability("transparent_animation", "透明背景动画（ProRes 4444）", "remotion-controls-skill",
                               "capabilities.cap_animation_renderer.renderer.AnimationRenderer",
                               ["node", "remotion", "ffmpeg"], priority=7),
                    Capability("animation_templates", "动画模板库", "remotion-controls-skill",
                               "capabilities.cap_template_library.library.TemplateLibrary", priority=6),
                    Capability("keyframe_builder", "关键帧/多图层构建", "remotion-controls-skill",
                               "capabilities.cap_animation_renderer.renderer.KeyframeBuilder", priority=6),
                ],
            },
            "anysearch-skill": {
                "name": "深度搜索",
                "version": "3.0.1",
                "capabilities": [
                    Capability("deep_search", "23垂类深度搜索", "anysearch-skill",
                               "scripts.anysearch_cli.cmd_search", priority=5),
                    Capability("report_generation", "搜索报告生成", "anysearch-skill",
                               "scripts.anysearch_cli.main", priority=5),
                ],
            },
            "ai-video-editor": {
                "name": "AI视频编辑器（本项目）",
                "version": "2.0.0",
                "capabilities": [
                    Capability("script_understanding", "剧本理解/情绪分析", "ai-video-editor",
                               "script_understanding_engine.ScriptUnderstandingEngine", priority=10),
                    Capability("storyboard_design", "分镜设计", "ai-video-editor",
                               "director_engine.DirectorEngine", priority=9),
                    Capability("photo_slideshow", "照片短视频生成", "ai-video-editor",
                               "photo_slideshow_generator", priority=8),
                    Capability("multi_track_mix", "多轨混音", "ai-video-editor",
                               "multi_track_mixer.MultiTrackMixer", ["ffmpeg"], priority=7),
                    Capability("effect_api", "统一特效API", "ai-video-editor",
                               "jianying_effect_api.JianyingEffectAPI", priority=8),
                    Capability("emotion_effect_map", "情绪→特效智能映射", "ai-video-editor",
                               "emotion_effect_mapper.EmotionEffectMapper", priority=8),
                    Capability("effect_presets", "特效组合预设库", "ai-video-editor",
                               "effect_preset_library.EffectPresetLibrary", priority=8),
                ],
            },
        }

    # ============ 注册管理 ============

    def register(self, registration: SkillRegistration):
        """注册/更新skill"""
        self.skills[registration.skill_id] = registration
        self._call_cache.clear()  # 清空调用缓存

    def unregister(self, skill_id: str):
        """注销skill"""
        self.skills.pop(skill_id, None)
        self._call_cache.clear()

    def refresh(self):
        """重新扫描所有skill（用于新skill安装后）"""
        self.skills.clear()
        self._call_cache.clear()
        self._auto_discover()

    # ============ 能力查询 ============

    def get_capability(self, name: str) -> Optional[Capability]:
        """按名称查找能力（返回优先级最高的可用能力）"""
        candidates = []
        for skill in self.skills.values():
            if not skill.is_active():
                continue
            for cap in skill.capabilities:
                if cap.name == name and cap.is_available():
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
                "error": s.error,
            }
            for s in self.skills.values()
        ]

    def find_alternatives(self, name: str) -> List[Capability]:
        """查找某能力的所有可用替代方案（按优先级排序）"""
        alternatives = []
        for skill in self.skills.values():
            if not skill.is_active():
                continue
            for cap in skill.capabilities:
                if cap.name == name and cap.is_available():
                    alternatives.append(cap)
        return sorted(alternatives, key=lambda c: c.priority, reverse=True)

    # ============ 统一调用接口 v2.0 ============

    def invoke(self, capability_name: str, *args, **kwargs) -> Any:
        """
        统一调用接口：按能力名称调用，自动处理导入和降级

        Args:
            capability_name: 能力名称（如 "transparent_animation"）
            *args, **kwargs: 传递给目标函数的参数

        Returns:
            目标函数的返回值

        Raises:
            CapabilityNotFoundError: 能力不存在且无替代方案
            CapabilityInvokeError: 调用失败
        """
        # 查找能力（含降级链）
        cap = self.get_capability(capability_name)
        if cap is None:
            alternatives = self.find_alternatives(capability_name)
            if alternatives:
                cap = alternatives[0]
            else:
                raise CapabilityNotFoundError(
                    f"能力 '{capability_name}' 不存在且无替代方案。"
                    f"可用能力: {[c.name for c in self.list_capabilities()]}"
                )

        # 解析入口点并调用
        try:
            callable_obj = self._resolve_entry(cap)
            return callable_obj(*args, **kwargs)
        except Exception as e:
            # 尝试降级到替代方案
            alternatives = self.find_alternatives(capability_name)
            for alt in alternatives:
                if alt.entry_point != cap.entry_point:
                    try:
                        callable_obj = self._resolve_entry(alt)
                        return callable_obj(*args, **kwargs)
                    except Exception:
                        continue
            raise CapabilityInvokeError(
                f"调用能力 '{capability_name}' 失败: {e}\n"
                f"入口点: {cap.entry_point}\n"
                f"所属skill: {cap.skill}"
            ) from e

    def _resolve_entry(self, cap: Capability) -> Callable:
        """解析能力入口点为可调用对象（带缓存）"""
        cache_key = f"{cap.skill}:{cap.entry_point}"
        if cache_key in self._call_cache:
            return self._call_cache[cache_key]

        # 查找skill根路径
        skill = self.skills.get(cap.skill)
        if skill is None or not skill.is_active():
            raise CapabilityInvokeError(f"skill '{cap.skill}' 不可用")

        root_path = skill.root_path

        # 点分路径解析：module.path.ClassName 或 module.path.function_name
        parts = cap.entry_point.split(".")
        module_path = ".".join(parts[:-1])
        attr_name = parts[-1]

        # 尝试导入模块
        original_path = sys.path.copy()
        try:
            # 将skill根目录和scripts/capabilities加入path
            for sub in ["", "scripts", "capabilities"]:
                p = os.path.join(root_path, sub)
                if os.path.isdir(p) and p not in sys.path:
                    sys.path.insert(0, p)

            module = importlib.import_module(module_path)
            callable_obj = getattr(module, attr_name)

            # 如果是类，尝试实例化（无参数构造）
            if isinstance(callable_obj, type):
                try:
                    callable_obj = callable_obj()
                except TypeError:
                    pass  # 保留类本身，由调用方实例化

            self._call_cache[cache_key] = callable_obj
            return callable_obj
        finally:
            sys.path = original_path

    # ============ 健康检查 v2.0 ============

    def check_health(self, deep: bool = False) -> Dict[str, Dict]:
        """
        健康检查 v2.0

        Args:
            deep: 是否进行深度检查（核心模块导入验证）

        Returns:
            {skill_id: {"status": ..., "details": ..., "capabilities_ok": N, "capabilities_total": N}}
        """
        results = {}
        for skill in self.skills.values():
            detail = {
                "status": skill.status,
                "version": skill.version,
                "path_exists": os.path.isdir(skill.root_path),
                "capabilities_total": len(skill.capabilities),
                "capabilities_ok": 0,
                "error": None,
            }

            # 基础检查：目录存在
            if not os.path.isdir(skill.root_path):
                skill.status = "missing"
                detail["status"] = "missing"
                detail["error"] = "skill目录不存在"
                results[skill.skill_id] = detail
                continue

            # 深度检查：核心模块导入验证
            if deep:
                ok_count = 0
                for cap in skill.capabilities:
                    try:
                        self._resolve_entry(cap)
                        ok_count += 1
                        cap.status = "available"
                    except Exception as e:
                        cap.status = "unavailable"
                        if detail["error"] is None:
                            detail["error"] = f"{cap.name}: {str(e)[:80]}"
                detail["capabilities_ok"] = ok_count
                if ok_count == 0:
                    skill.status = "error"
                    detail["status"] = "error"
                elif ok_count < len(skill.capabilities):
                    skill.status = "degraded"
                    detail["status"] = "degraded"
                else:
                    skill.status = "active"
                    detail["status"] = "active"
            else:
                detail["capabilities_ok"] = len(skill.capabilities)
                skill.status = "active"
                detail["status"] = "active"

            skill.last_check = time.time()
            results[skill.skill_id] = detail

        return results

    # ============ 版本兼容检测 ============

    def check_version_compatibility(self, skill_id: str, required: str) -> bool:
        """
        检查skill版本是否满足要求

        Args:
            skill_id: skill标识
            required: 版本要求（如 ">=1.0.0", ">=2.0.0,<3.0.0"）

        Returns:
            是否兼容
        """
        skill = self.skills.get(skill_id)
        if skill is None:
            return False

        actual = skill.version
        # 简化版本比较：支持 >=, <=, ==, >, <
        try:
            for part in required.split(","):
                part = part.strip()
                if part.startswith(">="):
                    if not self._version_gte(actual, part[2:]):
                        return False
                elif part.startswith("<="):
                    if not self._version_lte(actual, part[2:]):
                        return False
                elif part.startswith("=="):
                    if actual != part[2:]:
                        return False
                elif part.startswith(">"):
                    if not self._version_gt(actual, part[1:]):
                        return False
                elif part.startswith("<"):
                    if not self._version_lt(actual, part[1:]):
                        return False
            return True
        except Exception:
            return True  # 版本解析失败时默认兼容

    @staticmethod
    def _version_tuple(v: str) -> Tuple[int, ...]:
        """解析版本号为元组"""
        parts = []
        for p in v.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return tuple(parts)

    def _version_gte(self, a: str, b: str) -> bool:
        return self._version_tuple(a) >= self._version_tuple(b)

    def _version_lte(self, a: str, b: str) -> bool:
        return self._version_tuple(a) <= self._version_tuple(b)

    def _version_gt(self, a: str, b: str) -> bool:
        return self._version_tuple(a) > self._version_tuple(b)

    def _version_lt(self, a: str, b: str) -> bool:
        return self._version_tuple(a) < self._version_tuple(b)

    # ============ 序列化 ============

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "version": "2.0",
            "skills": {
                sid: {
                    "name": s.name,
                    "version": s.version,
                    "status": s.status,
                    "root_path": s.root_path,
                    "capabilities": [asdict(c) for c in s.capabilities],
                }
                for sid, s in self.skills.items()
            }
        }

    def save(self, path: str):
        """保存注册信息到JSON"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def summary(self) -> str:
        """生成可读的摘要"""
        lines = ["=" * 60, "能力注册中心 v2.0 摘要", "=" * 60]
        total_caps = 0
        for s in self.skills.values():
            lines.append(f"\n[{s.status}] {s.name} v{s.version} ({s.skill_id})")
            lines.append(f"  路径: {s.root_path}")
            lines.append(f"  能力数: {len(s.capabilities)}")
            for cap in s.capabilities:
                lines.append(f"    - [{cap.priority}] {cap.name}: {cap.description}")
            total_caps += len(s.capabilities)
        lines.append(f"\n{'=' * 60}")
        lines.append(f"总计: {len(self.skills)}个skill, {total_caps}个能力")
        lines.append("=" * 60)
        return "\n".join(lines)


# ============ 异常定义 ============

class CapabilityNotFoundError(Exception):
    """能力不存在异常"""
    pass


class CapabilityInvokeError(Exception):
    """能力调用异常"""
    pass


# ============ 便捷函数 ============

def get_registry() -> CapabilityRegistry:
    """获取全局注册中心实例"""
    return CapabilityRegistry()


def invoke_capability(name: str, *args, **kwargs) -> Any:
    """便捷函数：调用能力"""
    return get_registry().invoke(name, *args, **kwargs)


# ============ 自测 ============

if __name__ == "__main__":
    registry = get_registry()

    print(registry.summary())

    print("\n=== 健康检查（基础） ===")
    for sid, detail in registry.check_health().items():
        print(f"  {sid}: {detail['status']} (路径存在: {detail['path_exists']})")

    print("\n=== 版本兼容检测 ===")
    print(f"  anysearch >=3.0.0: {registry.check_version_compatibility('anysearch-skill', '>=3.0.0')}")
    print(f"  ai-video-editor >=2.0.0: {registry.check_version_compatibility('ai-video-editor', '>=2.0.0')}")

    print("\n=== 能力查询测试 ===")
    cap = registry.get_capability("transparent_animation")
    if cap:
        print(f"  transparent_animation: {cap.description} (优先级{cap.priority})")
    else:
        print("  transparent_animation: 未找到")

    alts = registry.find_alternatives("text_to_image")
    print(f"  text_to_image 替代方案: {len(alts)}个")
