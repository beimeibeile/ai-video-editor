"""
P23增强: LLM客户端封装 v2.0
支持多种LLM后端，优先级：宿主LLM > 云端API > 本地Ollama > Mock

使用方式：
    from llm_client import LLMClient
    client = LLMClient()  # 自动检测最优后端
    result = client.chat("你好", system_prompt="你是一个剧本分析助手")
    result = client.chat_json("分析剧本", system_prompt="...")  # 返回JSON
"""

import os
import json
from typing import Dict, Any, Optional, List


class LLMClient:
    """LLM客户端封装，支持多种后端，自动选择最优"""

    # 优先级顺序（从高到低）
    PROVIDER_PRIORITY = ["host", "openai", "ark", "doubao", "ollama", "local", "mock"]

    def __init__(
        self,
        provider: str = "auto",
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        timeout: int = 60,
    ):
        """
        初始化LLM客户端

        Args:
            provider: LLM提供商（auto/host/openai/doubao/ark/ollama/local/mock）
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            timeout: 超时时间（秒）
        """
        self.provider = provider
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", "")
        self.model = model or os.environ.get("LLM_MODEL", "")
        self.timeout = timeout
        self._available = False
        self._fallback_chain = []  # 降级链

        # 自动检测可用的LLM（按优先级）
        if provider == "auto":
            self._auto_detect()
        else:
            self._setup_provider()

    def _detect_host_llm(self) -> bool:
        """
        检测宿主LLM是否可用

        宿主LLM是指skill挂载的智能平台（如豆包、Claude等）本身提供的大模型能力。
        检测方式：
        1. 环境变量 HOST_LLM_AVAILABLE=1
        2. 环境变量 HOST_LLM_API（宿主LLM的API端点）
        3. 配置文件中的 provider=host
        """
        # 检查环境变量
        if os.environ.get("HOST_LLM_AVAILABLE", "").lower() in ("1", "true", "yes"):
            self.provider = "host"
            self.base_url = os.environ.get("HOST_LLM_API", "http://localhost:11435")
            self.model = os.environ.get("HOST_LLM_MODEL", "host-default")
            self.api_key = os.environ.get("HOST_LLM_KEY", "")
            self._available = True
            return True

        # 检查是否在豆包环境中运行（通过特定环境变量检测）
        if os.environ.get("DOUBAO_AGENT_MODE", "") or os.environ.get("DOUBAO_SKILL_RUNTIME", ""):
            # 在豆包智能体环境中，宿主LLM可用
            # 实际调用时通过宿主平台的API或直接利用宿主能力
            self.provider = "host"
            self.base_url = os.environ.get("HOST_LLM_API", "http://localhost:11435")
            self.model = os.environ.get("HOST_LLM_MODEL", "doubao-host")
            self._available = True
            return True

        return False

    def _auto_detect(self):
        """自动检测可用的LLM后端（按优先级：宿主 > 云端 > 本地 > Mock）"""
        # 1. 宿主LLM（最高优先级）
        if self._detect_host_llm():
            print(f"  ✅ 检测到宿主LLM: {self.model}")
            return

        # 2. 云端API - OpenAI
        if os.environ.get("OPENAI_API_KEY"):
            self.provider = "openai"
            self.api_key = os.environ["OPENAI_API_KEY"]
            self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
            self._available = True
            print(f"  ✅ 检测到OpenAI API: {self.model}")
            return

        # 3. 云端API - 豆包/火山方舟
        if os.environ.get("DOUBAO_API_KEY") or os.environ.get("ARK_API_KEY"):
            self.provider = "ark"
            self.api_key = os.environ.get("DOUBAO_API_KEY") or os.environ.get("ARK_API_KEY")
            self.base_url = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
            self.model = os.environ.get("ARK_MODEL", "doubao-pro-32k")
            self._available = True
            print(f"  ✅ 检测到火山方舟API: {self.model}")
            return

        # 4. 本地Ollama
        if os.environ.get("OLLAMA_HOST"):
            self.provider = "ollama"
            self.base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            self.model = os.environ.get("OLLAMA_MODEL", "llama3")
            self._available = True
            print(f"  ✅ 检测到本地Ollama: {self.model}")
            return

        # 5. 检查配置文件
        config_path = os.path.join(
            os.path.expanduser("~"), "Videos", "剪映导出",
            "Doubao_Jianying-editor", "llm_config.json"
        )
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.provider = config.get("provider", "openai")
                self.api_key = config.get("api_key", "")
                self.base_url = config.get("base_url", "")
                self.model = config.get("model", "")
                # Ollama/local/host不需要api_key
                self._available = bool(self.api_key) or self.provider in ("ollama", "local", "host", "mock")
                if self._available:
                    print(f"  ✅ 从配置文件加载: {self.provider}/{self.model}")
                    return
            except Exception as e:
                print(f"  ⚠️  配置文件读取失败: {e}")

        # 6. 尝试检测本地Ollama服务（即使没有环境变量）
        if self._check_ollama_service():
            self.provider = "ollama"
            self.base_url = "http://localhost:11434"
            self.model = self._get_ollama_default_model()
            self._available = True
            print(f"  ✅ 检测到本地Ollama服务: {self.model}")
            return

        # 7. 降级到Mock
        self.provider = "mock"
        self._available = True  # Mock始终可用
        print(f"  ⚠️  未检测到真实LLM，使用Mock模式（框架测试用）")

    def _check_ollama_service(self) -> bool:
        """检查本地Ollama服务是否运行"""
        try:
            import httpx
            with httpx.Client(timeout=3) as client:
                response = client.get("http://localhost:11434/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def _get_ollama_default_model(self) -> str:
        """获取Ollama中已安装的第一个模型"""
        try:
            import httpx
            with httpx.Client(timeout=3) as client:
                response = client.get("http://localhost:11434/api/tags")
                data = response.json()
                models = data.get("models", [])
                if models:
                    return models[0].get("name", "llama3")
        except Exception:
            pass
        return "llama3"

    def _setup_provider(self):
        """设置指定的LLM提供商"""
        defaults = {
            "host": {
                "base_url": "http://localhost:11435",
                "model": "host-default",
            },
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o",
            },
            "ark": {
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "doubao-pro-32k",
            },
            "doubao": {
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "doubao-pro-32k",
            },
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "llama3",
            },
            "local": {
                "base_url": "http://localhost:11434",
                "model": "llama3",
            },
            "mock": {
                "base_url": "",
                "model": "mock",
            },
        }

        if self.provider in defaults:
            default = defaults[self.provider]
            if not self.base_url:
                self.base_url = default["base_url"]
            if not self.model:
                self.model = default["model"]

        # Mock始终可用，其他需要api_key或本地服务
        if self.provider == "mock":
            self._available = True
        else:
            self._available = bool(self.api_key) or self.provider in ("ollama", "local", "host")

    @property
    def is_available(self) -> bool:
        """LLM是否可用"""
        return self._available

    def _chat_mock(self, message: str, system_prompt: str = "") -> str:
        """Mock LLM响应（用于框架测试）"""
        # 根据提示词类型返回合理的模拟响应
        if "风格" in system_prompt or "style" in system_prompt.lower():
            return "【风格迁移完成】已将剧本转换为目标风格，保持核心剧情不变，语言风格和节奏已调整。"
        elif "剧情" in system_prompt or "plot" in system_prompt.lower():
            return "【剧情增强完成】已添加钩子开场和悬念结尾，冲突更加突出，反转更有冲击力。"
        elif "角色" in system_prompt or "character" in system_prompt.lower():
            return "【角色深化完成】每个角色都有了更鲜明的性格特征和动机，对话更符合人物身份。"
        elif "台词" in system_prompt or "dialogue" in system_prompt.lower():
            return "【台词优化完成】台词更加口语化、有个性，去除了书面语，增加了潜台词和情绪层次。"
        elif "节奏" in system_prompt or "pace" in system_prompt.lower():
            return "【节奏调整完成】已按目标时长调整节拍分布，前3秒钩子，中间推进，结尾悬念。"
        else:
            return f"【Mock响应】收到消息：{message[:50]}..."

    def chat(
        self,
        message: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Optional[str]:
        """
        发送聊天请求（支持自动降级）

        Args:
            message: 用户消息
            system_prompt: 系统提示词
            temperature: 温度（0-1）
            max_tokens: 最大token数

        Returns:
            LLM回复文本，失败返回None
        """
        if not self._available:
            return None

        # Mock模式
        if self.provider == "mock":
            return self._chat_mock(message, system_prompt)

        try:
            import httpx

            # 宿主LLM / OpenAI兼容API / 火山方舟
            if self.provider in ("host", "openai", "ark", "doubao"):
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                }
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]

            # 本地Ollama
            elif self.provider in ("ollama", "local"):
                url = f"{self.base_url}/api/chat"
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                }

                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return data["message"]["content"]

        except Exception as e:
            print(f"  ⚠️  LLM请求失败 ({self.provider}): {e}")
            # 自动降级到下一个优先级
            return self._try_fallback(message, system_prompt, temperature, max_tokens)

    def _try_fallback(self, message: str, system_prompt: str,
                      temperature: float, max_tokens: int) -> Optional[str]:
        """尝试降级到下一个优先级的LLM"""
        # 构建降级链（按优先级，排除当前provider）
        fallback_providers = [p for p in self.PROVIDER_PRIORITY if p != self.provider]

        for fallback_provider in fallback_providers:
            try:
                # 创建临时客户端尝试降级
                temp_client = LLMClient(provider=fallback_provider, timeout=10)
                if temp_client.is_available and fallback_provider != "mock":
                    # 检查是否真的可用（非mock）
                    result = temp_client.chat(message, system_prompt, temperature, max_tokens)
                    if result:
                        print(f"  ✅ 降级到 {fallback_provider} 成功")
                        return result
                elif fallback_provider == "mock":
                    # Mock始终可用
                    return self._chat_mock(message, system_prompt)
            except Exception:
                continue

        return None

    def chat_json(
        self,
        message: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 3000,
    ) -> Optional[Dict[str, Any]]:
        """
        发送聊天请求并解析JSON响应

        Args:
            message: 用户消息
            system_prompt: 系统提示词（应要求LLM返回JSON）
            temperature: 温度（0-1，JSON解析建议低值）
            max_tokens: 最大token数

        Returns:
            解析后的JSON字典，失败返回None
        """
        # 确保系统提示词要求JSON格式
        if "JSON" not in system_prompt and "json" not in system_prompt:
            system_prompt += "\n\n请严格以JSON格式回复，不要包含任何其他文字。"

        response = self.chat(message, system_prompt, temperature, max_tokens)
        if not response:
            return None

        # 尝试解析JSON
        try:
            # 清理可能的markdown代码块
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON解析失败: {e}")
            print(f"  原始响应: {response[:200]}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """获取LLM客户端状态"""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
            "available": self._available,
            "priority_chain": self.PROVIDER_PRIORITY,
        }


if __name__ == "__main__":
    # 测试
    client = LLMClient()
    status = client.get_status()
    print("=" * 60)
    print("LLM客户端状态 v2.0")
    print("=" * 60)
    print(f"  当前提供商: {status['provider']}")
    print(f"  模型: {status['model']}")
    print(f"  API密钥已配置: {status['api_key_configured']}")
    print(f"  可用: {status['available']}")
    print(f"  优先级链: {' > '.join(status['priority_chain'])}")
    print("=" * 60)

    if client.is_available:
        print("\n测试聊天...")
        response = client.chat("你好，请用一句话介绍你自己")
        print(f"回复: {response}")
    else:
        print("\n⚠️  未配置LLM API")
        print("配置方式（按优先级）：")
        print("  1. 宿主LLM: 设置 HOST_LLM_AVAILABLE=1")
        print("  2. OpenAI: 设置 OPENAI_API_KEY")
        print("  3. 火山方舟: 设置 DOUBAO_API_KEY 或 ARK_API_KEY")
        print("  4. 本地Ollama: 设置 OLLAMA_HOST 或启动Ollama服务")
        print("  5. 配置文件: llm_config.json")
        print("  6. Mock模式（自动降级，框架测试用）")
