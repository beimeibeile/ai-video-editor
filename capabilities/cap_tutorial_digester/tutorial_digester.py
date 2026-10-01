"""
教程持续消化自动化 v1.0 (P4-5)
教程抓取+解析+特效封装+特效库自动更新

核心功能：
1. 教程管理：添加/删除/更新教程元数据
2. 教程解析：分析教程内容，提取特效制作步骤
3. 特效封装：将教程中的特效封装为可复用Python模块
4. 特效库更新：自动注册新特效到特效库
5. 消化进度跟踪：待消化/消化中/已完成/失败

工作流程：
1. 添加教程（标题/链接/平台/描述）
2. 解析教程（提取关键步骤和参数）
3. 生成特效代码模板
4. 人工确认和调整
5. 注册到特效库
6. 标记为已完成

使用方法：
    from tutorial_digester import TutorialDigester
    digester = TutorialDigester()
    digester.add_tutorial(title="文字排版技巧", url="https://...", platform="douyin")
    digester.parse_tutorial(tutorial_id)
    digester.generate_effect_code(tutorial_id, effect_name="text_layout")
    digester.register_effect(tutorial_id)
"""
import os
import sys
import json
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


class TutorialStatus:
    """教程状态"""
    PENDING = "pending"  # 待消化
    PARSING = "parsing"  # 解析中
    PARSED = "parsed"  # 已解析
    GENERATING = "generating"  # 生成代码中
    GENERATED = "generated"  # 已生成代码
    REVIEWING = "reviewing"  # 人工审核中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


@dataclass
class Tutorial:
    """教程"""
    tutorial_id: str
    title: str
    url: str = ""
    platform: str = "douyin"  # douyin/bilibili/other
    description: str = ""
    tags: List[str] = field(default_factory=list)
    status: str = "pending"
    added_at: str = ""
    parsed_at: str = ""
    completed_at: str = ""
    # 解析结果
    key_steps: List[Dict[str, Any]] = field(default_factory=list)
    effect_name: str = ""
    effect_category: str = "text"  # text/transition/mask/particle/color/other
    effect_params: Dict[str, Any] = field(default_factory=dict)
    # 生成结果
    generated_code_path: str = ""
    registered: bool = False
    error: str = ""
    notes: str = ""


@dataclass
class EffectTemplate:
    """特效代码模板"""
    effect_name: str
    category: str
    description: str
    params: Dict[str, Any]
    code_template: str


# 特效代码模板库
EFFECT_TEMPLATES = {
    "text_animation": EffectTemplate(
        effect_name="text_animation",
        category="text",
        description="文字动画特效模板",
        params={"text": "str", "duration": "float", "anim_type": "str"},
        code_template='''"""
{description}
基于教程《{tutorial_title}》封装

制作手法：
{key_steps_summary}
"""
import os
import sys
from typing import Dict, Any, Optional

skill_root = r"{skill_root}"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft


def create_{effect_name}(
    project_name: str,
    text: str = "{default_text}",
    duration: float = 3.0,
    width: int = 1080,
    height: int = 1920,
    **kwargs
) -> Dict[str, Any]:
    """
    创建{effect_name}特效工程

    Args:
        project_name: 工程名
        text: 文字内容
        duration: 时长（秒）
        width/height: 画布尺寸

    Returns:
        工程信息字典
    """
    print(f"\\n[1/3] 创建工程: {{project_name}}")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    print(f"[2/3] 添加文字: {{text}}")
    seg = project.add_text_simple(
        text=text,
        start_time="0s",
        duration=f"{{duration}}s",
        track_name="Text",
    )

    print(f"[3/3] 保存工程")
    result = project.save()

    return {{
        "status": "success",
        "project_name": project_name,
        "draft_path": result.get("draft_path", ""),
    }}


if __name__ == "__main__":
    create_{effect_name}("测试", text="测试文字")
''',
    ),
    "mask_transition": EffectTemplate(
        effect_name="mask_transition",
        category="mask",
        description="蒙版转场特效模板",
        params={"direction": "str", "duration": "float"},
        code_template='''"""
{description}
基于教程《{tutorial_title}》封装
"""
import os
import sys
from typing import Dict, Any

skill_root = r"{skill_root}"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from mask_keyframe import apply_mask_expand, save_with_mask_keyframes
    _MASK_AVAILABLE = True
except ImportError:
    _MASK_AVAILABLE = False


def create_{effect_name}(
    project_name: str,
    direction: str = "left",
    duration: float = 1.0,
    width: int = 1080,
    height: int = 1920,
    **kwargs
) -> Dict[str, Any]:
    """创建{effect_name}转场工程"""
    project = JyProject(project_name, width=width, height=height, overwrite=True)
    # TODO: 根据教程步骤实现具体逻辑
    result = project.save()
    return {"status": "success", "draft_path": result.get("draft_path", "")}
''',
    ),
}


class TutorialDigester:
    """教程持续消化器"""

    PLATFORMS = ["douyin", "bilibili", "youtube", "other"]
    CATEGORIES = ["text", "transition", "mask", "particle", "color", "layout", "other"]

    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or os.path.join(
            r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor",
            "tutorial_digester"
        )
        self.tutorials_file = os.path.join(self.storage_dir, "tutorials.json")
        self.effects_output_dir = os.path.join(self.storage_dir, "generated_effects")
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.effects_output_dir, exist_ok=True)
        self.tutorials: Dict[str, Tutorial] = {}
        self._load()

    def _load(self):
        """加载教程库"""
        if os.path.exists(self.tutorials_file):
            try:
                with open(self.tutorials_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for tid, tdata in data.items():
                    self.tutorials[tid] = Tutorial(**tdata)
            except Exception as e:
                print(f"⚠️ 教程库加载失败: {e}")

    def _save(self):
        """保存教程库"""
        data = {tid: asdict(t) for tid, t in self.tutorials.items()}
        with open(self.tutorials_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_id(self, title: str) -> str:
        """生成教程ID"""
        raw = f"{title}_{datetime.now().isoformat()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    # ==================== 教程管理 ====================

    def add_tutorial(self, title: str, url: str = "", platform: str = "douyin",
                     description: str = "", tags: List[str] = None) -> str:
        """添加教程"""
        tutorial_id = self._generate_id(title)
        tutorial = Tutorial(
            tutorial_id=tutorial_id,
            title=title,
            url=url,
            platform=platform if platform in self.PLATFORMS else "other",
            description=description,
            tags=tags or [],
            added_at=datetime.now().isoformat(),
        )
        self.tutorials[tutorial_id] = tutorial
        self._save()
        print(f"📚 教程已添加: {title} (ID: {tutorial_id})")
        return tutorial_id

    def remove_tutorial(self, tutorial_id: str) -> bool:
        """删除教程"""
        if tutorial_id in self.tutorials:
            del self.tutorials[tutorial_id]
            self._save()
            return True
        return False

    def get_tutorial(self, tutorial_id: str) -> Optional[Dict[str, Any]]:
        """获取教程详情"""
        if tutorial_id in self.tutorials:
            return asdict(self.tutorials[tutorial_id])
        return None

    def list_tutorials(self, status: str = "", platform: str = "",
                        tag: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """列出教程"""
        results = []
        for tutorial in self.tutorials.values():
            if status and tutorial.status != status:
                continue
            if platform and tutorial.platform != platform:
                continue
            if tag and tag not in tutorial.tags:
                continue
            results.append(asdict(tutorial))

        results.sort(key=lambda x: x["added_at"], reverse=True)
        return results[:limit]

    # ==================== 教程解析 ====================

    def parse_tutorial(self, tutorial_id: str, key_steps: List[Dict] = None,
                       effect_name: str = "", effect_category: str = "text",
                       effect_params: Dict = None) -> bool:
        """
        解析教程

        实际解析需要人工观看教程后提取关键步骤。
        此方法用于记录解析结果。

        Args:
            tutorial_id: 教程ID
            key_steps: 关键步骤列表 [{"step": 1, "description": "...", "params": {...}}]
            effect_name: 特效名称
            effect_category: 特效分类
            effect_params: 特效参数
        """
        if tutorial_id not in self.tutorials:
            return False

        tutorial = self.tutorials[tutorial_id]
        tutorial.status = TutorialStatus.PARSED
        tutorial.parsed_at = datetime.now().isoformat()

        if key_steps:
            tutorial.key_steps = key_steps
        if effect_name:
            tutorial.effect_name = effect_name
        if effect_category:
            tutorial.effect_category = effect_category if effect_category in self.CATEGORIES else "other"
        if effect_params:
            tutorial.effect_params = effect_params

        self._save()
        print(f"✅ 教程已解析: {tutorial.title} ({len(tutorial.key_steps)}个关键步骤)")
        return True

    # ==================== 特效代码生成 ====================

    def generate_effect_code(self, tutorial_id: str, effect_name: str = "",
                              template_type: str = "text_animation") -> Optional[str]:
        """
        生成特效代码

        Args:
            tutorial_id: 教程ID
            effect_name: 特效名称（默认使用教程中的名称）
            template_type: 模板类型（text_animation/mask_transition）

        Returns:
            生成的代码文件路径
        """
        if tutorial_id not in self.tutorials:
            return None

        tutorial = self.tutorials[tutorial_id]
        if not effect_name:
            effect_name = tutorial.effect_name or f"effect_{tutorial_id}"

        tutorial.status = TutorialStatus.GENERATING
        self._save()

        # 选择模板
        template = EFFECT_TEMPLATES.get(template_type, EFFECT_TEMPLATES["text_animation"])

        # 生成关键步骤摘要
        steps_summary = "\n".join(
            f"{i+1}. {step.get('description', '')}"
            for i, step in enumerate(tutorial.key_steps[:5])
        )

        # 填充模板
        skill_root = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor"
        code = template.code_template.format(
            description=tutorial.description or f"{tutorial.title}特效",
            tutorial_title=tutorial.title,
            key_steps_summary=steps_summary or "（待补充）",
            skill_root=skill_root,
            effect_name=effect_name,
            default_text="示例文字",
        )

        # 保存代码
        output_path = os.path.join(self.effects_output_dir, f"{effect_name}.py")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(code)

        tutorial.status = TutorialStatus.GENERATED
        tutorial.generated_code_path = output_path
        self._save()

        print(f"✅ 特效代码已生成: {effect_name}.py")
        return output_path

    # ==================== 特效注册 ====================

    def register_effect(self, tutorial_id: str, effects_index_path: str = None) -> bool:
        """
        注册特效到特效库

        Args:
            tutorial_id: 教程ID
            effects_index_path: 特效库索引文件路径
        """
        if tutorial_id not in self.tutorials:
            return False

        tutorial = self.tutorials[tutorial_id]
        if not tutorial.generated_code_path or not os.path.exists(tutorial.generated_code_path):
            tutorial.error = "特效代码未生成"
            tutorial.status = TutorialStatus.FAILED
            self._save()
            return False

        # 注册到特效库索引
        if effects_index_path is None:
            effects_index_path = os.path.join(
                r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor",
                "effects", "index.json"
            )

        try:
            if os.path.exists(effects_index_path):
                with open(effects_index_path, "r", encoding="utf-8") as f:
                    index = json.load(f)
            else:
                index = {"version": "1.0", "effects": [], "categories": {}}

            # 添加特效
            effect_entry = {
                "name": tutorial.effect_name or f"effect_{tutorial_id}",
                "description": tutorial.description or tutorial.title,
                "category": tutorial.effect_category,
                "tags": tutorial.tags,
                "module": f"scripts/{tutorial.effect_name}.py",
                "source_tutorial": tutorial.url,
                "added_at": datetime.now().isoformat(),
            }

            if "effects" not in index:
                index["effects"] = []
            index["effects"].append(effect_entry)

            with open(effects_index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)

            tutorial.registered = True
            tutorial.status = TutorialStatus.COMPLETED
            tutorial.completed_at = datetime.now().isoformat()
            self._save()

            print(f"✅ 特效已注册: {effect_entry['name']}")
            return True

        except Exception as e:
            tutorial.error = str(e)
            tutorial.status = TutorialStatus.FAILED
            self._save()
            print(f"❌ 特效注册失败: {e}")
            return False

    # ==================== 批量消化 ====================

    def digest_tutorial(self, tutorial_id: str, key_steps: List[Dict],
                        effect_name: str, effect_category: str = "text",
                        template_type: str = "text_animation") -> Dict[str, Any]:
        """
        一键消化教程（解析→生成→注册）

        Args:
            tutorial_id: 教程ID
            key_steps: 关键步骤
            effect_name: 特效名称
            effect_category: 特效分类
            template_type: 代码模板类型

        Returns:
            消化结果
        """
        result = {"tutorial_id": tutorial_id, "steps": {}}

        # 1. 解析
        result["steps"]["parse"] = self.parse_tutorial(
            tutorial_id, key_steps=key_steps,
            effect_name=effect_name, effect_category=effect_category
        )

        # 2. 生成代码
        code_path = self.generate_effect_code(tutorial_id, effect_name, template_type)
        result["steps"]["generate"] = code_path is not None
        result["code_path"] = code_path

        # 3. 注册（需要人工确认后调用）
        result["steps"]["register"] = "pending_manual_review"

        return result

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取消化统计"""
        total = len(self.tutorials)
        by_status = {}
        by_platform = {}

        for tutorial in self.tutorials.values():
            by_status[tutorial.status] = by_status.get(tutorial.status, 0) + 1
            by_platform[tutorial.platform] = by_platform.get(tutorial.platform, 0) + 1

        completed = sum(1 for t in self.tutorials.values() if t.status == TutorialStatus.COMPLETED)
        registered = sum(1 for t in self.tutorials.values() if t.registered)

        return {
            "total_tutorials": total,
            "completed": completed,
            "registered_effects": registered,
            "by_status": by_status,
            "by_platform": by_platform,
            "pending_review": sum(1 for t in self.tutorials.values() if t.status == TutorialStatus.GENERATED),
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    print("=" * 60)
    print("📖 教程持续消化器 v1.0")
    print("=" * 60)

    digester = TutorialDigester()

    # 添加测试教程
    tid = digester.add_tutorial(
        title="文字排版常用技巧",
        url="https://www.douyin.com/video/test",
        platform="douyin",
        description="多轨道文字叠加，竖排/横排/错落排列",
        tags=["文字", "排版"],
    )

    # 解析教程
    digester.parse_tutorial(
        tid,
        key_steps=[
            {"step": 1, "description": "创建主文字轨道"},
            {"step": 2, "description": "添加副文字轨道，位置错开"},
            {"step": 3, "description": "设置入场动画，错开时间"},
        ],
        effect_name="text_layout",
        effect_category="text",
    )

    # 生成代码
    code_path = digester.generate_effect_code(tid, effect_name="text_layout")

    print(f"\n统计: {digester.get_stats()}")
