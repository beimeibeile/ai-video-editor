"""
统一配置管理模块
优先级：环境变量 > .env文件 > 默认值
所有敏感信息（API Key、路径等）不硬编码，支持开源部署
"""
import os
from pathlib import Path

# 项目根目录
SKILL_ROOT = Path(__file__).parent.parent
ENV_FILE = SKILL_ROOT / ".env"


class Config:
    """统一配置管理器"""

    _instance = None
    _env_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_env()
        return cls._instance

    def _load_env(self):
        """加载.env文件（如果存在）"""
        if self._env_loaded:
            return
        if ENV_FILE.exists():
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = value
        self._env_loaded = True

    def get(self, key: str, default: str = None) -> str:
        """获取配置值"""
        return os.environ.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        val = self.get(key, str(default)).lower()
        return val in ("true", "1", "yes", "on")

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        try:
            return int(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    # ── AnySearch 配置 ──
    @property
    def anysearch_api_key(self) -> str:
        return self.get("ANYSEARCH_API_KEY", "")

    @property
    def anysearch_enabled(self) -> bool:
        return bool(self.anysearch_api_key)

    @property
    def anysearch_endpoint(self) -> str:
        return self.get("ANYSEARCH_API_ENDPOINT", "https://api.anysearch.com")

    # ── ComfyUI 配置 ──
    @property
    def comfyui_address(self) -> str:
        return self.get("COMFYUI_ADDRESS", "127.0.0.1:8188")

    @property
    def comfyui_enabled(self) -> bool:
        return self.get_bool("COMFYUI_ENABLED", True)

    # ── 剪映配置 ──
    @property
    def jianying_path(self) -> str:
        return self.get("JIANYING_PATH", "")

    @property
    def jianying_version(self) -> str:
        return self.get("JIANYING_VERSION", "5.9")

    @property
    def jianying_enabled(self) -> bool:
        return self.get_bool("JIANYING_ENABLED", True)

    # ── 输出配置 ──
    @property
    def output_dir(self) -> str:
        return self.get("OUTPUT_DIR", str(SKILL_ROOT / "output"))

    @property
    def temp_dir(self) -> str:
        return self.get("TEMP_DIR", str(SKILL_ROOT / "temp"))

    # ── 调试配置 ──
    @property
    def debug_mode(self) -> bool:
        return self.get_bool("DEBUG_MODE", False)

    @property
    def dry_run(self) -> bool:
        return self.get_bool("DRY_RUN", False)


# 全局单例
config = Config()
