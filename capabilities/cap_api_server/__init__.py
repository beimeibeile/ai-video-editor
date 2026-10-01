"""
API服务化模块
REST API封装所有能力，统一认证+限流+API文档自动生成
"""
from .api_server import APIServer, AuthManager, APIHandler

__all__ = ["APIServer", "AuthManager", "APIHandler"]
__version__ = "1.0.0"
