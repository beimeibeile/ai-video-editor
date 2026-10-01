"""
ComfyUI配置管理模块 v1.0
自动检测可用模型，消除硬编码checkpoint路径

功能:
1. 自动检测ComfyUI可用的checkpoint/LoRA/VAE
2. 智能选择默认模型（优先turbo/快速模型）
3. 支持环境变量和配置文件覆盖
4. 模型路径规范化（双反斜杠兼容）

使用方法:
    from comfy_config import ComfyConfig
    config = ComfyConfig(server_addr="127.0.0.1:8188")
    default_ckpt = config.get_default_checkpoint()
    available = config.list_checkpoints()
"""
import os
import json
from typing import Optional, List, Dict, Any

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


# 优先级排序的模型关键词（越靠前越优先作为默认）
CHECKPOINT_PRIORITY = [
    "sd_xl_turbo",       # SDXL Turbo - 最快
    "turbo",             # 其他turbo模型
    "sdxl",              # SDXL系列
    "majicmix",          # MajicMix写实
    "realistic",         # 写实模型
    "dreamshaper",       # DreamShaper
    "anything",          # Anything系列
    "counterfeit",       # Counterfeit
]


class ComfyConfig:
    """ComfyUI配置管理器"""

    def __init__(self, server_addr: str = "127.0.0.1:8188",
                 config_path: str = None):
        """
        Args:
            server_addr: ComfyUI服务器地址
            config_path: 配置文件路径（可选）
        """
        if server_addr.startswith("http://"):
            server_addr = server_addr[7:]
        self.server_addr = server_addr
        self.base_url = f"http://{server_addr}"
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "comfy_config.json"
        )
        self._cache: Dict[str, Any] = {}
        self._user_config = self._load_user_config()

    def _load_user_config(self) -> Dict[str, Any]:
        """加载用户配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_user_config(self, config: Dict[str, Any]):
        """保存用户配置"""
        self._user_config.update(config)
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._user_config, f, ensure_ascii=False, indent=2)

    def is_server_running(self) -> bool:
        """检测ComfyUI服务器是否运行"""
        if not _REQUESTS_AVAILABLE:
            return False
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def list_checkpoints(self, force_refresh: bool = False) -> List[str]:
        """
        获取可用的checkpoint列表

        Returns:
            checkpoint名称列表（含子目录路径）
        """
        if "checkpoints" in self._cache and not force_refresh:
            return self._cache["checkpoints"]

        # 优先从用户配置读取
        if "checkpoints" in self._user_config:
            self._cache["checkpoints"] = self._user_config["checkpoints"]
            return self._cache["checkpoints"]

        # 从ComfyUI API检测
        checkpoints = []
        if self.is_server_running():
            try:
                r = requests.get(
                    f"{self.base_url}/object_info/CheckpointLoaderSimple",
                    timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    ckpt_info = data.get("CheckpointLoaderSimple", {})
                    required = ckpt_info.get("input", {}).get("required", {})
                    ckpt_name = required.get("ckpt_name", [[]])
                    if isinstance(ckpt_name, list) and len(ckpt_name) > 0:
                        checkpoints = ckpt_name[0]
            except Exception:
                pass

        # 如果API检测失败，尝试从常见目录扫描
        if not checkpoints:
            checkpoints = self._scan_checkpoint_dirs()

        self._cache["checkpoints"] = checkpoints
        return checkpoints

    def _scan_checkpoint_dirs(self) -> List[str]:
        """从常见ComfyUI模型目录扫描checkpoint"""
        checkpoints = []
        possible_dirs = [
            r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\models\checkpoints",
            r"D:\Ai\ComfyUI\models\checkpoints",
            r"C:\ComfyUI\models\checkpoints",
            os.path.expanduser("~/ComfyUI/models/checkpoints"),
        ]

        for d in possible_dirs:
            if os.path.isdir(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith(('.safetensors', '.ckpt', '.pth')):
                            rel_path = os.path.relpath(
                                os.path.join(root, f), d
                            ).replace("\\", "\\\\")
                            checkpoints.append(rel_path)
                if checkpoints:
                    break

        return checkpoints

    def get_default_checkpoint(self) -> str:
        """
        智能选择默认checkpoint

        优先级:
        1. 用户配置中的default_checkpoint
        2. 环境变量COMFY_DEFAULT_CHECKPOINT
        3. 按优先级关键词自动选择
        4. 第一个可用模型
        """
        # 1. 用户配置
        if "default_checkpoint" in self._user_config:
            return self._user_config["default_checkpoint"]

        # 2. 环境变量
        env_ckpt = os.environ.get("COMFY_DEFAULT_CHECKPOINT")
        if env_ckpt:
            return env_ckpt

        # 3. 自动选择
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return "sd_xl_turbo_1.0_fp16.safetensors"  # 兜底默认

        # 按优先级关键词匹配
        for keyword in CHECKPOINT_PRIORITY:
            for ckpt in checkpoints:
                if keyword.lower() in ckpt.lower():
                    return ckpt

        # 4. 第一个可用模型
        return checkpoints[0]

    def normalize_checkpoint_path(self, ckpt_name: str) -> str:
        """
        规范化checkpoint路径（ComfyUI API需要双反斜杠）

        Args:
            ckpt_name: checkpoint名称

        Returns:
            规范化后的路径
        """
        # 统一用双反斜杠
        return ckpt_name.replace("/", "\\\\").replace("\\", "\\\\")

    def validate_checkpoint(self, ckpt_name: str) -> bool:
        """验证checkpoint是否可用"""
        available = self.list_checkpoints()
        # 同时检查原始路径和规范化路径
        return (ckpt_name in available or
                self.normalize_checkpoint_path(ckpt_name) in available)

    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        checkpoints = self.list_checkpoints()
        return {
            "server_running": self.is_server_running(),
            "server_addr": self.server_addr,
            "default_checkpoint": self.get_default_checkpoint(),
            "available_checkpoints_count": len(checkpoints),
            "available_checkpoints": checkpoints[:10],  # 最多显示10个
            "user_config_path": self.config_path,
        }


# 全局单例
_default_config: Optional[ComfyConfig] = None


def get_config(server_addr: str = "127.0.0.1:8188") -> ComfyConfig:
    """获取全局配置单例"""
    global _default_config
    if _default_config is None or _default_config.server_addr != server_addr:
        _default_config = ComfyConfig(server_addr)
    return _default_config


def get_default_checkpoint(server_addr: str = "127.0.0.1:8188") -> str:
    """便捷函数：获取默认checkpoint"""
    return get_config(server_addr).get_default_checkpoint()


if __name__ == "__main__":
    print("=" * 60)
    print("ComfyUI配置管理模块 v1.0")
    print("=" * 60)

    config = ComfyConfig()
    summary = config.get_config_summary()

    print(f"\n服务器: {summary['server_addr']}")
    print(f"运行状态: {'✅ 运行中' if summary['server_running'] else '❌ 未运行'}")
    print(f"默认模型: {summary['default_checkpoint']}")
    print(f"可用模型数: {summary['available_checkpoints_count']}")
    print(f"\n可用模型列表:")
    for ckpt in summary["available_checkpoints"]:
        print(f"  - {ckpt}")
    print(f"\n配置文件: {summary['user_config_path']}")
