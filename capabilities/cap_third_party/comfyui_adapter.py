"""
ComfyUI工具适配器
封装已有的ComfyUI能力
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from .tool_base import ToolAdapterBase, ToolState, ToolInfo


class ComfyUIAdapter(ToolAdapterBase):
    """ComfyUI工具适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._info = ToolInfo(
            name="comfyui",
            description="ComfyUI AI图像/视频生成工具",
            capabilities=["text_to_image", "image_to_image", "text_to_video", "image_to_video",
                          "upscale", "inpaint", "outpaint", "workflow_run"],
        )
        self._api_url = self.config.get("api_url", "http://127.0.0.1:8188")
        self._client_id = "ai_video_editor"

    def detect(self) -> ToolState:
        """检测ComfyUI是否运行"""
        try:
            response = self._api_request("GET", "/system_stats")
            if response:
                self._state = ToolState.RUNNING
                # 获取版本
                self._info.version = response.get("system", {}).get("comfyui_version", "unknown")
                return self._state
        except Exception:
            pass

        # 检查安装目录
        install_dir = self.config.get("install_dir", r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI")
        if os.path.exists(install_dir):
            self._state = ToolState.INSTALLED
        else:
            self._state = ToolState.NOT_INSTALLED
        return self._state

    def start(self) -> bool:
        """启动ComfyUI"""
        if self._state == ToolState.RUNNING:
            return True
        if self._state != ToolState.INSTALLED:
            return False

        install_dir = self.config.get("install_dir", r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI")
        python_path = self.config.get("python_path", r"D:\Ai\ComfyUI-aki-v3.2\python\python.exe")

        if not os.path.exists(python_path):
            return False

        try:
            import subprocess
            subprocess.Popen(
                [python_path, "main.py", "--listen", "127.0.0.1", "--port", "8188"],
                cwd=install_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            # 等待启动
            for _ in range(30):
                time.sleep(1)
                try:
                    self._api_request("GET", "/system_stats")
                    self._state = ToolState.RUNNING
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def stop(self) -> bool:
        """停止ComfyUI"""
        # 通过API无法直接停止，需要外部进程管理
        self._state = ToolState.INSTALLED
        return True

    def call(self, action: str, **kwargs) -> Any:
        """
        调用ComfyUI能力

        支持的action:
        - text_to_image: 文生图
        - image_to_image: 图生图
        - text_to_video: 文生视频
        - image_to_video: 图生视频
        - run_workflow: 运行工作流
        - get_history: 获取历史记录
        - get_queue: 获取队列状态
        """
        if self._state != ToolState.RUNNING:
            raise RuntimeError(f"ComfyUI未运行，当前状态: {self._state}")

        if action == "text_to_image":
            return self._text_to_image(kwargs)
        elif action == "image_to_image":
            return self._image_to_image(kwargs)
        elif action == "text_to_video":
            return self._text_to_video(kwargs)
        elif action == "image_to_video":
            return self._image_to_video(kwargs)
        elif action == "run_workflow":
            return self._run_workflow(kwargs.get("workflow"), kwargs.get("timeout", 120))
        elif action == "get_history":
            return self._api_request("GET", "/history")
        elif action == "get_queue":
            return self._api_request("GET", "/queue")
        else:
            raise ValueError(f"ComfyUI不支持动作: {action}")

    def _api_request(self, method: str, endpoint: str, data: Dict = None) -> Any:
        """发送API请求"""
        url = f"{self._api_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if method == "GET":
            req = urllib.request.Request(url, headers=headers)
        else:
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"),
                                          headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(f"ComfyUI API请求失败: {e}")

    def _run_workflow(self, workflow: Dict, timeout: int = 120) -> Dict[str, Any]:
        """运行工作流"""
        # 提交工作流
        response = self._api_request("POST", "/prompt", {
            "prompt": workflow,
            "client_id": self._client_id
        })
        prompt_id = response.get("prompt_id")
        if not prompt_id:
            return {"success": False, "error": "未获取到prompt_id"}

        # 等待完成
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(1)
            history = self._api_request("GET", f"/history/{prompt_id}")
            if prompt_id in history:
                return {"success": True, "prompt_id": prompt_id, "result": history[prompt_id]}

        return {"success": False, "error": "超时", "prompt_id": prompt_id}

    def _text_to_image(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """文生图（使用简单工作流）"""
        prompt = kwargs.get("prompt", "")
        negative_prompt = kwargs.get("negative_prompt", "")
        width = kwargs.get("width", 1024)
        height = kwargs.get("height", 1024)
        steps = kwargs.get("steps", 20)
        cfg = kwargs.get("cfg", 7.0)
        checkpoint = kwargs.get("checkpoint", "sd_xl_turbo_1.0_fp16.safetensors")

        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": int(time.time()),
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint}
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]}
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt, "clip": ["4", 1]}
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "ai_video_editor", "images": ["8", 0]}
            }
        }
        return self._run_workflow(workflow, kwargs.get("timeout", 120))

    def _image_to_image(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """图生图"""
        # 简化实现，实际需要上传图片
        return {"success": False, "error": "图生图需要上传图片，暂未实现简化接口"}

    def _text_to_video(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """文生视频"""
        return {"success": False, "error": "文生视频需要特定工作流，请使用run_workflow"}

    def _image_to_video(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """图生视频"""
        return {"success": False, "error": "图生视频需要特定工作流，请使用run_workflow"}
