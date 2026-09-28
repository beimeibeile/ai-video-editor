"""
ComfyUI API客户端封装
支持：提交工作流、查询状态、上传图片、下载输出、批量任务
"""
import requests
import json
import time
import os
import uuid
from typing import Optional, Dict, List, Any


class ComfyClient:
    """ComfyUI API客户端"""

    def __init__(self, server_addr: str = "127.0.0.1:8188", client_id: str = None):
        self.server_addr = server_addr
        self.client_id = client_id or str(uuid.uuid4())
        self.base_url = f"http://{server_addr}"
        self.session = requests.Session()

    def is_running(self) -> bool:
        """检测ComfyUI是否运行"""
        try:
            r = self.session.get(f"{self.base_url}/system_stats", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def get_system_stats(self) -> Dict:
        """获取系统状态（GPU显存等）"""
        r = self.session.get(f"{self.base_url}/system_stats", timeout=5)
        return r.json()

    def get_object_info(self, node_class: str = None) -> Dict:
        """获取节点信息（全部或指定节点）"""
        if node_class:
            r = self.session.get(f"{self.base_url}/object_info/{node_class}", timeout=10)
        else:
            r = self.session.get(f"{self.base_url}/object_info", timeout=15)
        return r.json()

    def upload_image(self, image_path: str, subfolder: str = "") -> Dict:
        """上传图片到ComfyUI输入目录"""
        with open(image_path, "rb") as f:
            files = {"image": (os.path.basename(image_path), f, "image/png")}
            data = {"subfolder": subfolder, "type": "input"}
            r = self.session.post(f"{self.base_url}/upload/image", files=files, data=data)
        return r.json()

    def queue_prompt(self, workflow: Dict) -> str:
        """提交工作流到队列，返回prompt_id"""
        payload = {
            "prompt": workflow,
            "client_id": self.client_id,
        }
        r = self.session.post(f"{self.base_url}/prompt", json=payload)
        if r.status_code != 200:
            raise Exception(f"提交失败: {r.status_code} {r.text}")
        data = r.json()
        return data["prompt_id"]

    def get_history(self, prompt_id: str) -> Optional[Dict]:
        """获取执行历史（含输出文件）"""
        r = self.session.get(f"{self.base_url}/history/{prompt_id}", timeout=10)
        data = r.json()
        return data.get(prompt_id)

    def wait_for_completion(self, prompt_id: str, timeout: int = 600,
                             poll_interval: float = 2.0,
                             progress_callback=None) -> Dict:
        """等待任务完成，返回历史记录"""
        start = time.time()
        while time.time() - start < timeout:
            history = self.get_history(prompt_id)
            if history:
                status = history.get("status", {})
                if status.get("completed"):
                    return history
                if status.get("status_str") == "error":
                    raise Exception(f"任务执行失败: {json.dumps(status, ensure_ascii=False)}")
            if progress_callback:
                progress_callback(time.time() - start)
            time.sleep(poll_interval)
        raise TimeoutError(f"任务超时 ({timeout}s)")

    def get_output_images(self, history: Dict) -> List[Dict]:
        """从历史记录中提取输出图片信息"""
        outputs = history.get("outputs", {})
        images = []
        for node_id, node_out in outputs.items():
            for img in node_out.get("images", []):
                images.append({
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                    "node_id": node_id,
                })
        return images

    def download_image(self, filename: str, subfolder: str = "",
                       save_path: str = None, type_: str = "output") -> str:
        """下载输出图片到本地"""
        params = {"filename": filename, "subfolder": subfolder, "type": type_}
        r = self.session.get(f"{self.base_url}/view", params=params, timeout=30)
        if r.status_code != 200:
            raise Exception(f"下载失败: {r.status_code}")
        if save_path is None:
            save_path = filename
        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(r.content)
        return save_path

    def run_workflow(self, workflow: Dict, input_images: Dict[str, str] = None,
                     output_dir: str = None, timeout: int = 600) -> List[str]:
        """
        完整执行工作流：上传图片 → 提交 → 等待 → 下载输出

        Args:
            workflow: 工作流JSON（节点字典）
            input_images: {节点中的文件名占位符: 本地图片路径}，用于替换LoadImage节点
            output_dir: 输出目录
            timeout: 超时秒数

        Returns:
            下载到本地的输出文件路径列表
        """
        # 上传输入图片并替换工作流中的文件名
        if input_images:
            for placeholder, local_path in input_images.items():
                upload_result = self.upload_image(local_path)
                uploaded_name = upload_result["name"]
                # 替换工作流中所有LoadImage节点的image字段
                for node_id, node in workflow.items():
                    if node.get("class_type") == "LoadImage":
                        if node["inputs"].get("image") == placeholder:
                            node["inputs"]["image"] = uploaded_name

        # 提交工作流
        prompt_id = self.queue_prompt(workflow)
        print(f"  任务已提交: {prompt_id}")

        # 等待完成
        history = self.wait_for_completion(prompt_id, timeout=timeout)

        # 下载输出
        output_images = self.get_output_images(history)
        saved_paths = []
        for img_info in output_images:
            save_name = img_info["filename"]
            if output_dir:
                save_path = os.path.join(output_dir, save_name)
            else:
                save_path = save_name
            self.download_image(
                img_info["filename"],
                subfolder=img_info["subfolder"],
                save_path=save_path,
                type_=img_info["type"]
            )
            saved_paths.append(save_path)
            print(f"  输出已保存: {save_path}")

        return saved_paths

    def clear_queue(self):
        """清空任务队列"""
        self.session.post(f"{self.base_url}/queue", json={"clear": True})


def load_workflow_template(template_path: str, **kwargs) -> Dict:
    """
    加载工作流模板JSON，替换占位符

    模板中使用 {{key}} 作为占位符，运行时替换为实际值
    """
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    for key, value in kwargs.items():
        if isinstance(value, str):
            escaped = json.dumps(value)[1:-1]
            content = content.replace("{{" + key + "}}", escaped)
        else:
            content = content.replace("{{" + key + "}}", str(value))
    return json.loads(content)
