"""
外部能力适配层（External Adapters）
所有外部能力调用必须经过此层，统一翻译为内部规范。

使用方式：
    from adapters import AdapterManager
    manager = AdapterManager()
    llm = manager.get_llm()              # 自动选择最优后端
    response = llm.chat("你好")          # 返回LLMResponse（内部规范）

设计原则：
1. 内部只认识内部规范，不直接调用外部API
2. 适配器负责双向翻译：外部格式 ↔ 内部规范
3. 外部能力变化只改适配器，不影响核心引擎
4. 自动降级链：宿主 > 云端 > 本地 > Mock
5. 能力健康检查与自动切换
"""

import os
import json
from typing import Dict, Any, Optional, List, Type
from .internal_schema import (
    CapabilityType, ProviderPriority, CapabilityStatus,
    AdapterConfig, LLMRequest, LLMResponse,
    TTSRequest, TTSResponse,
    SFXRequest, SFXResponse,
)
from .base_adapter import BaseAdapter
from .llm_adapter import LLMAdapter, create_llm_adapter
from .tts_adapter import TTSAdapter
from .sfx_adapter import SFXAdapter


class AdapterManager:
    """
    适配器管理器（单例）
    统一管理所有外部能力适配器，提供：
    - 能力探测与优先级排序
    - 自动降级链构建
    - 健康检查与自动切换
    - 配置文件支持
    - 适配器注册表
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._adapters: Dict[str, BaseAdapter] = {}
        self._registry: Dict[CapabilityType, List[Type[BaseAdapter]]] = {}
        self._config: Dict[str, Any] = {}
        self._load_config()
        self._register_defaults()
        self._initialized = True

    def _load_config(self):
        """加载适配层配置文件"""
        config_paths = [
            os.path.join(os.path.expanduser("~"), "Videos", "剪映导出",
                         "Doubao_Jianying-editor", "adapter_config.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "adapter_config.json"),
        ]
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self._config = json.load(f)
                    return
                except Exception:
                    pass
        self._config = {}

    def _register_defaults(self):
        """注册默认适配器"""
        self._registry = {
            CapabilityType.LLM: [LLMAdapter],
            CapabilityType.TTS: [TTSAdapter],
            CapabilityType.SFX: [SFXAdapter],
        }

    def register(self, capability_type: CapabilityType, adapter_class: Type[BaseAdapter]):
        """注册新的适配器类型"""
        if capability_type not in self._registry:
            self._registry[capability_type] = []
        if adapter_class not in self._registry[capability_type]:
            self._registry[capability_type].append(adapter_class)

    def _build_fallback_chain(self, capability_type: CapabilityType,
                              primary_provider: str) -> List[BaseAdapter]:
        """
        构建自动降级链
        优先级：宿主 > 云端 > 本地 > Mock
        """
        chain = []
        priority_order = ["host", "openai", "ark", "doubao", "ollama", "local", "mock"]

        # 主适配器放第一位
        if primary_provider != "auto":
            try:
                primary = self._create_adapter(capability_type, primary_provider)
                if primary:
                    chain.append(primary)
            except Exception:
                pass

        # 按优先级添加其他适配器
        for provider in priority_order:
            if provider == primary_provider:
                continue
            try:
                adapter = self._create_adapter(capability_type, provider)
                if adapter and adapter.check_availability():
                    chain.append(adapter)
            except Exception:
                continue

        return chain

    def _create_adapter(self, capability_type: CapabilityType,
                        provider: str) -> Optional[BaseAdapter]:
        """创建指定类型和提供商的适配器"""
        config = AdapterConfig(
            capability_type=capability_type,
            provider=provider,
            timeout=self._config.get("timeout", 60),
        )

        if capability_type == CapabilityType.LLM:
            return create_llm_adapter(provider)
        elif capability_type == CapabilityType.TTS:
            return TTSAdapter(config)
        elif capability_type == CapabilityType.SFX:
            return SFXAdapter(config)
        return None

    def get_adapter(self, capability_type: CapabilityType,
                    provider: str = "auto") -> BaseAdapter:
        """
        获取指定能力的适配器（自动选择最优后端+构建降级链）
        """
        key = f"{capability_type.value}_{provider}"

        if key not in self._adapters:
            # 创建主适配器
            adapter = self._create_adapter(capability_type, provider)
            if adapter:
                # 构建降级链
                fallback_chain = self._build_fallback_chain(capability_type, provider)
                if fallback_chain:
                    adapter.set_fallback_chain(fallback_chain)
                self._adapters[key] = adapter

        return self._adapters.get(key)

    def get_llm(self, provider: str = "auto") -> LLMAdapter:
        """获取LLM适配器"""
        return self.get_adapter(CapabilityType.LLM, provider)

    def get_tts(self, provider: str = "auto") -> TTSAdapter:
        """获取TTS适配器"""
        return self.get_adapter(CapabilityType.TTS, provider)

    def get_sfx(self, provider: str = "auto") -> SFXAdapter:
        """获取SFX适配器"""
        return self.get_adapter(CapabilityType.SFX, provider)

    def health_check(self) -> Dict[str, Any]:
        """
        全能力健康检查
        探测所有已注册能力的可用性，返回状态报告
        """
        report = {}
        for cap_type in CapabilityType:
            try:
                adapter = self.get_adapter(cap_type)
                if adapter:
                    available = adapter.check_availability()
                    status = adapter.get_status()
                    report[cap_type.value] = {
                        "available": available,
                        "provider": status.provider,
                        "model": status.model,
                        "latency_ms": status.latency_ms,
                        "error": status.error,
                    }
                else:
                    report[cap_type.value] = {"available": False, "error": "无适配器"}
            except Exception as e:
                report[cap_type.value] = {"available": False, "error": str(e)}
        return report

    def get_status_all(self) -> dict:
        """获取所有已初始化适配器状态"""
        status = {}
        for key, adapter in self._adapters.items():
            try:
                s = adapter.get_status()
                status[key] = {
                    "available": s.available,
                    "provider": s.provider,
                    "model": s.model,
                    "latency_ms": s.latency_ms,
                }
            except Exception as e:
                status[key] = {"error": str(e)}
        return status

    def reset(self):
        """重置所有适配器（配置变更后调用）"""
        self._adapters = {}
        self._load_config()

    def reload_config(self, config: Dict[str, Any] = None):
        """重新加载配置"""
        if config:
            self._config = config
        else:
            self._load_config()
        self.reset()


__all__ = [
    # 规范
    "CapabilityType", "ProviderPriority", "CapabilityStatus",
    "AdapterConfig", "LLMRequest", "LLMResponse",
    "TTSRequest", "TTSResponse",
    "SFXRequest", "SFXResponse",
    # 基类
    "BaseAdapter",
    # 适配器
    "LLMAdapter", "TTSAdapter", "SFXAdapter",
    "create_llm_adapter",
    # 管理器
    "AdapterManager",
]
