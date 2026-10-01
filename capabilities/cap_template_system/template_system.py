"""
视频模板系统 v1.0
预设视频模板，一键套用，参数化定制

模板类型：
- exploration_food: 探店美食（钩子+菜品展示+价格+地址+号召）
- talking_head: 口播知识（钩子+3个要点+总结+关注）
- vlog_daily: 日常Vlog（开场+3个片段+结尾）
- tutorial: 教程演示（问题+步骤1-3+效果+号召）
- product_review: 产品测评（外观+功能+对比+购买建议）
- emotional_story: 剧情情感（场景+冲突+转折+感悟）

使用方法：
    from template_system import TemplateSystem
    ts = TemplateSystem()
    templates = ts.list_templates()
    result = ts.apply("exploration_food", topic="城市夜景咖啡店", duration=30)
"""
import os
import sys
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

from cap_e2e_pipeline.pipeline_script_driver import ScriptDrivenPipeline


@dataclass
class VideoTemplate:
    """视频模板定义"""
    id: str
    name: str
    description: str
    video_type: str  # exploration/talking/vlog/tutorial/product/story/ecommerce/promo
    default_duration: float
    default_hook_effect: str
    scene_structure: List[Dict[str, Any]]  # 场景结构预设
    style_params: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


# 模板库
TEMPLATE_LIBRARY = {
    "exploration_food": VideoTemplate(
        id="exploration_food",
        name="探店美食",
        description="网红店探店模板：钩子吸引→环境展示→招牌菜→价格地址→到店号召",
        video_type="exploration",
        default_duration=30,
        default_hook_effect="subtitle_bar",
        scene_structure=[
            {"type": "hook", "duration_ratio": 0.15, "content": "悬念式开场，抛出问题或反差"},
            {"type": "environment", "duration_ratio": 0.2, "content": "店铺环境+氛围展示"},
            {"type": "food_showcase", "duration_ratio": 0.35, "content": "招牌菜品特写+口感描述"},
            {"type": "price_address", "duration_ratio": 0.15, "content": "人均价格+地址信息"},
            {"type": "cta", "duration_ratio": 0.15, "content": "到店号召+关注引导"},
        ],
        style_params={"tone": "活泼", "music": "轻快", "subtitle_style": "pill_warm"},
        tags=["探店", "美食", "本地生活", "餐饮"],
    ),
    "talking_head": VideoTemplate(
        id="talking_head",
        name="口播知识",
        description="知识口播模板：钩子提问→3个要点→总结→关注引导",
        video_type="talking",
        default_duration=45,
        default_hook_effect="character_card",
        scene_structure=[
            {"type": "hook", "duration_ratio": 0.15, "content": "提问式钩子，引发好奇"},
            {"type": "point_1", "duration_ratio": 0.22, "content": "第一个要点+案例"},
            {"type": "point_2", "duration_ratio": 0.22, "content": "第二个要点+案例"},
            {"type": "point_3", "duration_ratio": 0.22, "content": "第三个要点+案例"},
            {"type": "summary", "duration_ratio": 0.1, "content": "总结回顾"},
            {"type": "cta", "duration_ratio": 0.09, "content": "关注引导"},
        ],
        style_params={"tone": "专业", "music": "节奏", "subtitle_style": "rect_dark"},
        tags=["口播", "知识", "干货", "教育"],
    ),
    "vlog_daily": VideoTemplate(
        id="vlog_daily",
        name="日常Vlog",
        description="生活Vlog模板：开场问候→3个日常片段→感悟结尾",
        video_type="vlog",
        default_duration=60,
        default_hook_effect="date_badge",
        scene_structure=[
            {"type": "intro", "duration_ratio": 0.1, "content": "开场问候+日期地点"},
            {"type": "moment_1", "duration_ratio": 0.25, "content": "第一个日常片段"},
            {"type": "moment_2", "duration_ratio": 0.25, "content": "第二个日常片段"},
            {"type": "moment_3", "duration_ratio": 0.25, "content": "第三个日常片段"},
            {"type": "outro", "duration_ratio": 0.15, "content": "感悟+下期预告"},
        ],
        style_params={"tone": "温暖", "music": "治愈", "subtitle_style": "rect_minimal"},
        tags=["Vlog", "生活", "日常", "记录"],
    ),
    "tutorial_howto": VideoTemplate(
        id="tutorial_howto",
        name="教程演示",
        description="技能教程模板：问题引入→步骤拆解→效果展示→行动号召",
        video_type="tutorial",
        default_duration=45,
        default_hook_effect="wipe",
        scene_structure=[
            {"type": "problem", "duration_ratio": 0.15, "content": "痛点问题引入"},
            {"type": "step_1", "duration_ratio": 0.22, "content": "第一步操作演示"},
            {"type": "step_2", "duration_ratio": 0.22, "content": "第二步操作演示"},
            {"type": "step_3", "duration_ratio": 0.22, "content": "第三步操作演示"},
            {"type": "result", "duration_ratio": 0.12, "content": "最终效果展示"},
            {"type": "cta", "duration_ratio": 0.07, "content": "收藏+关注引导"},
        ],
        style_params={"tone": "清晰", "music": "轻快", "subtitle_style": "pill_cool"},
        tags=["教程", "技能", "演示", "干货"],
    ),
    "product_review": VideoTemplate(
        id="product_review",
        name="产品测评",
        description="产品测评模板：外观开箱→功能体验→优缺点→购买建议",
        video_type="product",
        default_duration=60,
        default_hook_effect="layout",
        scene_structure=[
            {"type": "unboxing", "duration_ratio": 0.2, "content": "外观开箱+第一印象"},
            {"type": "features", "duration_ratio": 0.3, "content": "核心功能体验"},
            {"type": "pros_cons", "duration_ratio": 0.25, "content": "优点缺点对比"},
            {"type": "verdict", "duration_ratio": 0.15, "content": "购买建议+适合人群"},
            {"type": "cta", "duration_ratio": 0.1, "content": "链接+关注引导"},
        ],
        style_params={"tone": "客观", "music": "电子", "subtitle_style": "pill_cyber"},
        tags=["测评", "数码", "产品", "开箱"],
    ),
    "emotional_story": VideoTemplate(
        id="emotional_story",
        name="剧情情感",
        description="情感剧情模板：场景建立→冲突展开→转折高潮→感悟收尾",
        video_type="story",
        default_duration=90,
        default_hook_effect="bg_slide",
        scene_structure=[
            {"type": "setup", "duration_ratio": 0.2, "content": "场景+人物建立"},
            {"type": "conflict", "duration_ratio": 0.3, "content": "冲突或困境展开"},
            {"type": "turning", "duration_ratio": 0.25, "content": "转折或高潮"},
            {"type": "resolution", "duration_ratio": 0.15, "content": "解决+感悟"},
            {"type": "outro", "duration_ratio": 0.1, "content": "金句收尾+互动"},
        ],
        style_params={"tone": "深情", "music": "钢琴", "subtitle_style": "rect_minimal"},
        tags=["剧情", "情感", "故事", "短剧"],
    ),
}


class TemplateSystem:
    """视频模板系统"""

    def __init__(self, output_dir: str = None):
        self.templates = TEMPLATE_LIBRARY
        self.output_dir = output_dir or os.path.join(SKILL_ROOT, "template_outputs")
        os.makedirs(self.output_dir, exist_ok=True)

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有可用模板"""
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "video_type": t.video_type,
                "default_duration": t.default_duration,
                "tags": t.tags,
                "scene_count": len(t.scene_structure),
            }
            for t in self.templates.values()
        ]

    def get_template(self, template_id: str) -> Optional[VideoTemplate]:
        """获取模板详情"""
        return self.templates.get(template_id)

    def apply(
        self,
        template_id: str,
        topic: str,
        duration: float = None,
        project_name: str = None,
        custom_params: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        套用模板生成视频

        Args:
            template_id: 模板ID
            topic: 视频主题
            duration: 时长（默认用模板默认值）
            project_name: 工程名
            custom_params: 自定义参数覆盖

        Returns:
            生成结果字典
        """
        template = self.templates.get(template_id)
        if not template:
            return {"status": "failed", "error": f"模板不存在: {template_id}"}

        dur = duration or template.default_duration
        params = {**template.style_params, **(custom_params or {})}

        # 构建增强的topic（融入模板结构提示）
        enhanced_topic = self._build_enhanced_topic(topic, template)

        print(f"\n{'='*60}")
        print(f"🎬 模板生成: {template.name}")
        print(f"   主题: {topic}")
        print(f"   时长: {dur}秒")
        print(f"   结构: {len(template.scene_structure)}个场景")
        print(f"{'='*60}")

        # 调用pipeline生成
        driver = ScriptDrivenPipeline(
            project_dir=os.path.join(self.output_dir, project_name or f"tpl_{template_id}"),
            output_dir=os.path.join(self.output_dir, project_name or f"tpl_{template_id}", "outputs"),
        )

        result = driver.run(
            topic=enhanced_topic,
            video_type=template.video_type,
            duration=dur,
            project_name=project_name or f"tpl_{template_id}_{int(os.times()[4])}",
            hook_effect=template.default_hook_effect,
        )

        result["template_id"] = template_id
        result["template_name"] = template.name
        result["enhanced_topic"] = enhanced_topic

        # 保存模板应用记录
        record = {
            "template_id": template_id,
            "template_name": template.name,
            "topic": topic,
            "duration": dur,
            "params": params,
            "result": {k: v for k, v in result.items() if k != "result"},
        }
        record_path = os.path.join(self.output_dir, f"last_template_record.json")
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2, default=str)

        return result

    def _build_enhanced_topic(self, topic: str, template: VideoTemplate) -> str:
        """根据模板结构构建增强的主题描述"""
        structure_desc = "→".join([s["type"] for s in template.scene_structure])
        return f"{topic}。视频结构：{structure_desc}。风格：{template.style_params.get('tone', '自然')}。"


if __name__ == "__main__":
    print("=" * 60)
    print("视频模板系统 v1.0")
    print("=" * 60)

    ts = TemplateSystem()
    templates = ts.list_templates()

    print(f"\n可用模板 ({len(templates)}个):")
    for t in templates:
        print(f"  [{t['id']}] {t['name']} - {t['description'][:40]}...")
        print(f"       类型:{t['video_type']} 默认时长:{t['default_duration']}s 场景数:{t['scene_count']}")

    print(f"\n使用示例:")
    print(f"  ts.apply('exploration_food', topic='城市夜景咖啡店', duration=30)")
