"""
模拟LLM客户端（MockLLMClient）
用于在没有实际LLM服务时跑通系统框架，预留配置结构。
当用户配置实际LLM服务后，可直接切换到真实LLMClient。

使用方式：
    from mock_llm_client import MockLLMClient
    client = MockLLMClient()
    result = client.chat("你好")
"""

import json
import random
from typing import Dict, Any, Optional, List


class MockLLMClient:
    """模拟LLM客户端，用于框架测试"""

    def __init__(self, provider: str = "mock", model: str = "mock-llm"):
        self.provider = provider
        self.model = model
        self.api_key = "mock-key"
        self.base_url = "http://localhost:11434"
        self._available = True

    @property
    def is_available(self) -> bool:
        return self._available

    def chat(
        self,
        message: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Optional[str]:
        """
        模拟LLM聊天回复
        根据提示词类型返回合理的模拟响应
        """
        # 根据提示词内容判断改写类型
        if "风格" in message and "改写" in message:
            return self._mock_style_transfer(message)
        elif "剧情" in message and "增强" in message:
            return self._mock_plot_enhancement(message)
        elif "角色" in message and "深化" in message:
            return self._mock_character_deepening(message)
        elif "台词" in message and "优化" in message:
            return self._mock_dialogue_optimization(message)
        elif "节奏" in message and "调整" in message:
            return self._mock_pace_adjustment(message)
        else:
            return self._mock_general_response(message)

    def chat_json(
        self,
        message: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 3000,
    ) -> Optional[Dict[str, Any]]:
        """模拟JSON响应"""
        response = self.chat(message, system_prompt, temperature, max_tokens)
        if not response:
            return None
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"response": response}

    def _mock_style_transfer(self, message: str) -> str:
        """模拟风格迁移"""
        return """场景1：餐厅·特写
动作：顾客皱眉，放下筷子
顾客：这菜也太咸了吧！

场景2：餐厅·中景
动作：服务员慌张跑过来
服务员：对不起对不起，我马上给您换一份！

场景3：餐厅·特写
动作：顾客得意地笑
顾客：不用换，咸点好下饭。

场景4：餐厅·全景
动作：服务员愣住，顾客大口扒饭
旁白：有时候，咸也是一种智慧。"""

    def _mock_plot_enhancement(self, message: str) -> str:
        """模拟剧情增强"""
        return """场景1：餐厅·特写（0-3秒）
动作：顾客猛地放下筷子，眉头紧锁
顾客：这菜也太咸了吧！是想咸死我吗？
音效：筷子放下的清脆声

场景2：餐厅·中景（3-6秒）
动作：服务员慌张跑过来，手里还拿着菜单
服务员：对不起对不起！我马上给您换一份！这是我们的失误！
动作：顾客抬手制止
顾客：等等...

场景3：餐厅·特写（6-10秒）
动作：顾客嘴角上扬，露出得意的笑容
顾客：不用换。
服务员：啊？
顾客：咸点好，下饭啊。

场景4：餐厅·全景（10-15秒）
动作：服务员愣住，顾客大口扒饭，吃得津津有味
旁白：高手过招，往往就在一句话之间。
音效：背景音乐突然变得激昂"""

    def _mock_character_deepening(self, message: str) -> str:
        """模拟角色深化"""
        return """场景1：餐厅·特写
角色：顾客（精明的中年男人，喜欢占便宜，说话慢条斯理）
动作：顾客慢慢放下筷子，用纸巾擦了擦嘴
顾客（慢条斯理）：这菜，有点咸啊。

场景2：餐厅·中景
角色：服务员（年轻小姑娘，刚入职，容易紧张）
动作：服务员小跑过来，双手攥着围裙
服务员（慌张）：对、对不起！我马上给您换！
动作：顾客摆摆手
顾客：不用。

场景3：餐厅·特写
动作：顾客露出狡黠的笑容
顾客：咸点好，下饭。
动作：服务员愣住

场景4：餐厅·全景
动作：顾客大口吃饭，服务员在一旁哭笑不得"""

    def _mock_dialogue_optimization(self, message: str) -> str:
        """模拟台词优化"""
        return """顾客：这菜也太咸了！
服务员：对不起，马上换！
顾客：不用。
服务员：啊？
顾客：咸点好，下饭啊。
服务员：...您真会吃。"""

    def _mock_pace_adjustment(self, message: str) -> str:
        """模拟节奏调整"""
        return """场景1（0-3秒）：顾客放下筷子，皱眉
顾客：这菜太咸了！

场景2（3-6秒）：服务员跑过来
服务员：对不起，马上换！

场景3（6-10秒）：顾客得意地笑
顾客：不用换，咸点好下饭。

场景4（10-15秒）：服务员愣住，顾客大口吃饭
旁白：这就是高手。"""

    def _mock_general_response(self, message: str) -> str:
        """模拟通用回复"""
        return "这是一个模拟的LLM回复。系统框架已跑通，配置实际LLM服务后将返回真实回复。"

    def get_status(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_configured": True,
            "available": self._available,
            "note": "模拟模式，配置实际LLM后可切换",
        }


if __name__ == "__main__":
    print("=" * 60)
    print("模拟LLM客户端测试")
    print("=" * 60)

    client = MockLLMClient()
    status = client.get_status()
    print(f"提供商: {status['provider']}")
    print(f"模型: {status['model']}")
    print(f"可用: {status['available']}")

    print("\n测试聊天...")
    response = client.chat("你好")
    print(f"回复: {response[:100]}")
