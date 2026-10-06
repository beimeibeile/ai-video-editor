"""
宿主LLM深度改写模块 v1.0

利用宿主LLM（豆包/OpenAI/Ollama等）进行深度剧本改写：
1. 风格迁移 - 按目标风格重写剧本
2. 剧情增强 - 增加冲突、反转、钩子
3. 角色深化 - 丰富角色性格和动机
4. 台词优化 - 让台词更自然、有个性
5. 节奏调整 - 按目标时长调整节奏

集成到script_rewriter中，LLM可用时自动启用，不可用时降级到规则增强。
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class RewriteSuggestion:
    """单条改写建议"""
    type: str  # style/plot/character/dialogue/pace
    original: str
    suggestion: str
    reason: str
    confidence: float = 0.0


@dataclass
class LLMRewriteResult:
    """LLM改写结果"""
    success: bool = False
    rewritten_script: Optional[Dict[str, Any]] = None
    suggestions: List[RewriteSuggestion] = field(default_factory=list)
    rewrite_type: str = ""  # 执行的改写类型
    tokens_used: int = 0
    model: str = ""
    error: str = ""

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "rewrite_type": self.rewrite_type,
            "suggestions": [asdict(s) for s in self.suggestions],
            "tokens_used": self.tokens_used,
            "model": self.model,
            "error": self.error,
        }


class HostLLMRewriter:
    """
    宿主LLM深度改写器

    使用方式：
        rewriter = HostLLMRewriter()
        if rewriter.available:
            result = rewriter.rewrite_style(script, target_style="悬疑")
        else:
            print("LLM不可用，使用规则增强")
    """

    # 改写策略提示词模板
    # JSON格式约束（所有prompt共用）
    JSON_FORMAT_RULES = """【输出格式铁律】
必须输出合法JSON，不要任何额外文字、解释、markdown标记。格式如下：

{
  "scenes": [
    {
      "name": "场景名称",
      "environment": "环境描述",
      "shots": [
        {
          "character": "角色名",
          "emotion": "情绪",
          "dialogue": "台词内容",
          "action": "动作描述",
          "is_hook": false,
          "is_suspense": false
        }
      ]
    }
  ]
}

【字段规则】
- character: 2-4个中文字的人名或职业名（顾客/服务员/老板/张三），全剧一致
- emotion: 2-4字情绪词（惊讶/愤怒/平静/得意）
- dialogue: 台词内容，不超过35字
- action: 动作描述，**必填**，每个shot必须有动作（如：拍桌、转身、皱眉、微笑），无动作时写"站立"或"静坐"
- is_hook: 布尔值，开场第一个有冲击力的shot设为true（钩子）
- is_suspense: 布尔值，结尾最后一个留悬念的shot设为true（悬念）
- name: 场景名称
- environment: 环境描述，可为空字符串

【钩子悬念要求】
- 第一个scene的第一个shot必须is_hook=true，内容要有悬念/冲突/反常识
- 最后一个scene的最后一个shot必须is_suspense=true，内容要留悬念或反转

【禁止】
- 禁止输出markdown代码块标记（```json）
- 禁止输出任何解释或总结
- 禁止在character字段放动作词或情绪词
- 禁止角色名加"们"字"""

    PROMPTS = {
        "style_transfer": """你是专业短剧编剧。请将以下剧本改写为「{style}」风格。

{JSON_FORMAT_RULES}

【改写要求】
1. 保持核心剧情和角色不变
2. 调整语言风格、节奏、氛围以匹配目标风格
3. 台词要符合角色性格

原始剧本：
{script}

输出JSON：""",

        "plot_enhancement": """你是专业短剧编剧。请增强以下剧本的戏剧性：

{JSON_FORMAT_RULES}

【改写要求】
1. 在关键节点增加冲突或反转
2. 开场钩子：第一个shot的dialogue或action必须有悬念/冲突/反常识，3秒内抓住观众
3. 结尾悬念：最后一个shot的dialogue必须留悬念或反转
4. 保持角色行为逻辑一致

原始剧本：
{script}

输出JSON：""",

        "character_deepening": """你是专业短剧编剧。请深化以下剧本中的角色：

{JSON_FORMAT_RULES}

【改写要求】
1. 给每个角色增加独特的语言习惯和小动作
2. 丰富角色动机和背景
3. 让角色之间的互动更有张力
4. 保持核心剧情不变

原始剧本：
{script}

输出JSON：""",

        "dialogue_optimization": """你是专业短剧编剧。请优化以下剧本的台词：

{JSON_FORMAT_RULES}

【改写要求】
1. 台词要口语化、自然，符合角色身份
2. 每句台词不超过35字（适合短视频）
3. 增加潜台词和言外之意
4. 关键台词要有记忆点

原始剧本：
{script}

输出JSON：""",

        "pace_adjustment": """你是专业短剧编剧。请将以下剧本调整为约{duration}秒的节奏：

{JSON_FORMAT_RULES}

【改写要求】
1. 总时长控制在{duration}秒左右（中文语速约3.5字/秒）
2. 开场3秒内必须有钩子
3. 每5-8秒一个小高潮或反转
4. 结尾留悬念或反转

原始剧本：
{script}

输出JSON：""",
    }

    def __init__(self, llm_client=None):
        """
        初始化

        Args:
            llm_client: LLM客户端实例（None则自动创建，优先使用适配层）
        """
        self.llm_client = llm_client
        self.llm_adapter = None
        self.available = False
        self.model = ""

        # 优先使用适配层LLM适配器
        if self.llm_client is None:
            try:
                import sys
                adapters_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "adapters"
                )
                if adapters_path not in sys.path:
                    sys.path.insert(0, adapters_path)
                from llm_adapter import LLMAdapter
                self.llm_adapter = LLMAdapter()
                self.available = self.llm_adapter.is_available
                self.model = getattr(self.llm_adapter, 'model', '') or getattr(self.llm_adapter._status, 'model', '')
                if self.available:
                    print(f"  🤖 适配层LLM可用: {self.model}")
                else:
                    print(f"  ⚠️  适配层LLM不可用，尝试直接初始化LLM客户端")
            except Exception as e:
                print(f"  ⚠️  适配层LLM初始化失败: {e}，尝试直接初始化LLM客户端")

        # 适配层不可用时，回退到直接初始化LLM客户端
        if not self.available and self.llm_client is None:
            try:
                from llm_client import LLMClient
                self.llm_client = LLMClient()
                if not self.llm_client.is_available:
                    print(f"  ⚠️  真实LLM不可用，使用模拟LLM客户端（框架测试模式）")
                    from mock_llm_client import MockLLMClient
                    self.llm_client = MockLLMClient()
            except Exception as e:
                print(f"  ⚠️  LLM客户端初始化失败: {e}，使用模拟LLM客户端")
                try:
                    from mock_llm_client import MockLLMClient
                    self.llm_client = MockLLMClient()
                except Exception as e2:
                    print(f"  ⚠️  模拟LLM客户端也加载失败: {e2}")

        # 检测LLM可用性
        if self.llm_client:
            try:
                avail = getattr(self.llm_client, 'is_available', False)
                if callable(avail):
                    self.available = avail()
                else:
                    self.available = avail
                self.model = getattr(self.llm_client, 'model', '')
            except Exception:
                self.available = False

        if self.available and self.llm_adapter:
            print(f"  🤖 宿主LLM可用（适配层）: {self.model}")
        elif self.available:
            print(f"  🤖 宿主LLM可用（直连）: {self.model}")
        else:
            print(f"  ⚠️  宿主LLM不可用，深度改写将降级为规则增强")

    def _call_llm(self, prompt: str, system_prompt: str = "你是专业短剧编剧。") -> Optional[str]:
        """调用LLM（优先使用适配层，回退到直连）"""
        if not self.available:
            return None

        # 优先使用适配层
        if self.llm_adapter:
            try:
                response = self.llm_adapter.chat(
                    message=prompt,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=2000,
                )
                if response and response.success:
                    return response.content
                else:
                    error = getattr(response, 'error', '未知错误') if response else '无响应'
                    print(f"  ⚠️  适配层LLM调用失败: {error}，回退到直连")
            except Exception as e:
                print(f"  ⚠️  适配层LLM调用异常: {e}，回退到直连")

        # 回退到直连LLM客户端
        if self.llm_client:
            try:
                response = self.llm_client.chat(
                    message=prompt,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=2000,
                )
                return response
            except Exception as e:
                print(f"  ⚠️  LLM调用失败: {e}")
                return None

        return None

    def _script_to_text(self, script: Dict[str, Any]) -> str:
        """将剧本JSON转为文本格式"""
        if isinstance(script, str):
            return script

        lines = []
        scenes = script.get("scenes", script.get("shots", []))
        for i, scene in enumerate(scenes, 1):
            scene_name = scene.get("name", scene.get("scene", f"场景{i}"))
            lines.append(f"场景{i}：{scene_name}")

            shots = scene.get("shots", scene.get("beats", []))
            for shot in shots:
                if isinstance(shot, dict):
                    action = shot.get("action", shot.get("description", ""))
                    dialogue = shot.get("dialogue", shot.get("text", ""))
                    character = shot.get("character", shot.get("speaker", ""))
                    if action:
                        lines.append(f"  动作：{action}")
                    if dialogue:
                        lines.append(f"  {character}：{dialogue}")
            lines.append("")

        return "\n".join(lines)

    def _text_to_script(self, text: str, base_script: Dict[str, Any]) -> Dict[str, Any]:
        """
        将LLM返回的JSON转为剧本JSON
        优先解析JSON格式，失败时降级为文本保存（后续P23解析）
        """
        result = dict(base_script) if isinstance(base_script, dict) else {}

        # 尝试提取JSON（LLM可能输出markdown代码块或前后有多余文字）
        json_str = self._extract_json(text)

        if json_str:
            try:
                parsed = json.loads(json_str)
                if "scenes" in parsed and isinstance(parsed["scenes"], list):
                    # JSON解析成功，直接构建结构化剧本
                    result["scenes"] = self._normalize_json_scenes(parsed["scenes"])
                    result["llm_json_parsed"] = True
                    result["llm_rewritten_text"] = text
                    result["llm_rewrite_applied"] = True
                    # 从scenes中提取角色
                    result["characters"] = self._extract_characters_from_scenes(result["scenes"])
                    return result
            except json.JSONDecodeError:
                pass

        # JSON解析失败，降级为文本保存
        result["llm_rewritten_text"] = text
        result["llm_json_parsed"] = False
        result["llm_rewrite_applied"] = True
        return result

    def _extract_json(self, text: str) -> Optional[str]:
        """从LLM输出中提取JSON字符串"""
        if not text:
            return None

        # 尝试直接解析
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # 尝试提取markdown代码块中的JSON
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return match.group(1)

        # 尝试提取第一个{到最后一个}之间的内容
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]

        return None

    # 情绪→默认动作映射（用于补全缺失的action）
    EMOTION_DEFAULT_ACTION = {
        "惊讶": "瞪大双眼，身体后仰",
        "愤怒": "握拳，眉头紧锁",
        "平静": "静坐，表情淡然",
        "得意": "嘴角上扬，双手抱胸",
        "尴尬": "挠头，眼神躲闪",
        "紧张": "搓手，坐立不安",
        "开心": "笑容满面，拍手",
        "难过": "低头，眼眶泛红",
        "疑惑": "歪头，皱眉思考",
        "期待": "身体前倾，眼神热切",
        "歉意": "低头鞠躬，双手合十",
        "专注": "凝神注视，一动不动",
    }

    def _normalize_json_scenes(self, scenes: List[Dict]) -> List[Dict]:
        """将LLM返回的JSON场景规范化为内部格式，自动估算时长，补全缺失action"""
        normalized = []
        current_time = 0.0
        for i, scene in enumerate(scenes):
            norm_scene = {
                "id": f"scene_{i}",
                "name": scene.get("name", scene.get("scene", f"场景{i+1}")),
                "environment": scene.get("environment", scene.get("location", "")),
                "shots": [],
            }

            shots = scene.get("shots", scene.get("beats", []))
            scene_start = current_time
            for j, shot in enumerate(shots):
                if isinstance(shot, dict):
                    dialogue = shot.get("dialogue", shot.get("text", ""))
                    action = shot.get("action", shot.get("description", ""))
                    emotion = shot.get("emotion", "平静")
                    # 补全缺失的action（Q06：每场至少一个动作节拍）
                    if not action:
                        action = self.EMOTION_DEFAULT_ACTION.get(emotion, "静坐，表情自然")
                    # 根据台词字数估算时长（中文约3.5字/秒，最少1秒）
                    if dialogue:
                        est_duration = max(1.0, len(dialogue) / 3.5)
                    elif action:
                        est_duration = max(1.0, len(action) / 5.0)
                    else:
                        est_duration = 1.0
                    # 如果LLM提供了duration，优先使用
                    duration = shot.get("duration", est_duration)

                    norm_shot = {
                        "id": f"shot_{i}_{j}",
                        "character": shot.get("character", shot.get("speaker", "")),
                        "emotion": emotion,
                        "dialogue": dialogue,
                        "action": action,
                        "duration": round(duration, 2),
                        "start_time": round(current_time, 2),
                        "is_hook": shot.get("is_hook", False),
                        "is_suspense": shot.get("is_suspense", False),
                    }
                    norm_scene["shots"].append(norm_shot)
                    current_time += duration

            norm_scene["start_time"] = round(scene_start, 2)
            norm_scene["duration"] = round(current_time - scene_start, 2)
            normalized.append(norm_scene)

        return normalized

    def _extract_characters_from_scenes(self, scenes: List[Dict]) -> List[Dict]:
        """从场景中提取角色列表"""
        char_map = {}
        for scene in scenes:
            for shot in scene.get("shots", []):
                name = shot.get("character", "")
                if name and name not in char_map:
                    char_map[name] = {
                        "id": f"char_{len(char_map)}",
                        "name": name,
                        "description": "",
                        "voice": "中性",
                        "emotion_default": shot.get("emotion", "平静"),
                    }
        return list(char_map.values())

    def rewrite_style(self, script: Dict[str, Any], target_style: str) -> LLMRewriteResult:
        """风格迁移改写"""
        result = LLMRewriteResult(rewrite_type="style_transfer")

        if not self.available:
            result.error = "LLM不可用"
            return result

        script_text = self._script_to_text(script)
        prompt = self.PROMPTS["style_transfer"].format(
            style=target_style, script=script_text, JSON_FORMAT_RULES=self.JSON_FORMAT_RULES)

        response = self._call_llm(prompt)
        if response:
            result.success = True
            result.rewritten_script = self._text_to_script(response, script)
            result.suggestions.append(RewriteSuggestion(
                type="style",
                original=script_text[:100],
                suggestion=f"已改写为{target_style}风格",
                reason="LLM风格迁移",
                confidence=0.8,
            ))
        else:
            result.error = "LLM调用失败"

        return result

    def enhance_plot(self, script: Dict[str, Any]) -> LLMRewriteResult:
        """剧情增强"""
        result = LLMRewriteResult(rewrite_type="plot_enhancement")

        if not self.available:
            result.error = "LLM不可用"
            return result

        script_text = self._script_to_text(script)
        prompt = self.PROMPTS["plot_enhancement"].format(
            script=script_text, JSON_FORMAT_RULES=self.JSON_FORMAT_RULES)

        response = self._call_llm(prompt)
        if response:
            result.success = True
            result.rewritten_script = self._text_to_script(response, script)
        else:
            result.error = "LLM调用失败"

        return result

    def deepen_characters(self, script: Dict[str, Any]) -> LLMRewriteResult:
        """角色深化"""
        result = LLMRewriteResult(rewrite_type="character_deepening")

        if not self.available:
            result.error = "LLM不可用"
            return result

        script_text = self._script_to_text(script)
        prompt = self.PROMPTS["character_deepening"].format(
            script=script_text, JSON_FORMAT_RULES=self.JSON_FORMAT_RULES)

        response = self._call_llm(prompt)
        if response:
            result.success = True
            result.rewritten_script = self._text_to_script(response, script)
        else:
            result.error = "LLM调用失败"

        return result

    def optimize_dialogue(self, script: Dict[str, Any]) -> LLMRewriteResult:
        """台词优化"""
        result = LLMRewriteResult(rewrite_type="dialogue_optimization")

        if not self.available:
            result.error = "LLM不可用"
            return result

        script_text = self._script_to_text(script)
        prompt = self.PROMPTS["dialogue_optimization"].format(
            script=script_text, JSON_FORMAT_RULES=self.JSON_FORMAT_RULES)

        response = self._call_llm(prompt)
        if response:
            result.success = True
            result.rewritten_script = self._text_to_script(response, script)
        else:
            result.error = "LLM调用失败"

        return result

    def adjust_pace(self, script: Dict[str, Any], target_duration: float) -> LLMRewriteResult:
        """节奏调整"""
        result = LLMRewriteResult(rewrite_type="pace_adjustment")

        if not self.available:
            result.error = "LLM不可用"
            return result

        script_text = self._script_to_text(script)
        prompt = self.PROMPTS["pace_adjustment"].format(
            duration=target_duration, script=script_text, JSON_FORMAT_RULES=self.JSON_FORMAT_RULES)

        response = self._call_llm(prompt)
        if response:
            result.success = True
            result.rewritten_script = self._text_to_script(response, script)
        else:
            result.error = "LLM调用失败"

        return result

    def deep_rewrite(
        self,
        script: Dict[str, Any],
        style: str = "",
        duration: float = 0,
        enable_plot: bool = True,
        enable_character: bool = True,
        enable_dialogue: bool = True,
    ) -> LLMRewriteResult:
        """
        综合深度改写（按顺序执行多种改写）

        Args:
            script: 原始剧本
            style: 目标风格（空则不做风格迁移）
            duration: 目标时长（0则不做节奏调整）
            enable_plot: 是否启用剧情增强
            enable_character: 是否启用角色深化
            enable_dialogue: 是否启用台词优化

        Returns:
            LLMRewriteResult
        """
        result = LLMRewriteResult(rewrite_type="deep_rewrite")
        current_script = script

        if not self.available:
            result.error = "LLM不可用"
            return result

        # 按顺序执行改写
        steps = []
        if style:
            steps.append(("style_transfer", lambda s: self.rewrite_style(s, style)))
        if enable_plot:
            steps.append(("plot_enhancement", lambda s: self.enhance_plot(s)))
        if enable_character:
            steps.append(("character_deepening", lambda s: self.deepen_characters(s)))
        if enable_dialogue:
            steps.append(("dialogue_optimization", lambda s: self.optimize_dialogue(s)))
        if duration > 0:
            steps.append(("pace_adjustment", lambda s: self.adjust_pace(s, duration)))

        all_suggestions = []
        for step_name, step_func in steps:
            print(f"  [LLM改写] {step_name}...")
            step_result = step_func(current_script)
            if step_result.success and step_result.rewritten_script:
                current_script = step_result.rewritten_script
                all_suggestions.extend(step_result.suggestions)
            else:
                print(f"    ⚠️  {step_name}跳过: {step_result.error}")

        result.success = True
        result.rewritten_script = current_script
        result.suggestions = all_suggestions
        result.model = self.model

        return result


if __name__ == "__main__":
    print("="*60)
    print("宿主LLM深度改写测试")
    print("="*60)

    rewriter = HostLLMRewriter()

    if rewriter.available:
        test_script = {
            "scenes": [
                {
                    "name": "办公室",
                    "shots": [
                        {"action": "深夜，小明独自在加班", "dialogue": "好累啊", "character": "小明"},
                        {"action": "电脑屏幕突然闪烁", "dialogue": "什么情况？", "character": "小明"},
                    ]
                }
            ]
        }

        result = rewriter.deep_rewrite(test_script, style="悬疑", duration=15.0)
        print(f"\n改写成功: {result.success}")
        print(f"改写类型: {result.rewrite_type}")
        print(f"建议数: {len(result.suggestions)}")
        if result.rewritten_script:
            print(f"改写后文本: {result.rewritten_script.get('llm_rewritten_text', '')[:200]}")
    else:
        print("LLM不可用，跳过测试")
        print("提示：配置OPENAI_API_KEY或DOUBAO_API_KEY环境变量后可启用深度改写")
