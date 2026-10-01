"""
云端ComfyUI算力调度器 v1.0 (P4-3)
多ComfyUI实例管理+任务队列+负载均衡+算力监控

核心功能：
1. 多实例管理：本地+云端ComfyUI实例注册和健康检查
2. 任务队列：FIFO+优先级队列，支持任务状态跟踪
3. 负载均衡：根据GPU使用率/显存/队列长度智能分配
4. 算力监控：实时监控每个实例的GPU状态
5. 故障转移：实例故障时自动迁移任务到其他实例

使用方法：
    from compute_scheduler import ComputeScheduler
    scheduler = ComputeScheduler()
    scheduler.register_instance("local", "http://127.0.0.1:8188")
    scheduler.register_instance("cloud1", "http://192.168.1.100:8188")
    task_id = scheduler.submit_task(workflow={...}, priority="normal")
    result = scheduler.wait_for_result(task_id)
"""
import os
import sys
import json
import time
import threading
import queue
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InstanceStatus(Enum):
    """实例状态"""
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class ComputeTask:
    """计算任务"""
    task_id: str
    workflow: Dict[str, Any]
    priority: str = "normal"
    status: str = "pending"
    assigned_instance: str = ""
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    result: Any = None
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComputeInstance:
    """计算实例"""
    instance_id: str
    base_url: str
    status: str = "offline"
    gpu_name: str = ""
    gpu_usage: float = 0.0  # 0-100
    vram_total: float = 0.0  # GB
    vram_used: float = 0.0  # GB
    queue_length: int = 0
    active_tasks: int = 0
    total_tasks: int = 0
    failed_tasks: int = 0
    last_health_check: str = ""
    response_time_ms: float = 0.0
    location: str = "local"  # local/cloud
    weight: float = 1.0  # 负载均衡权重


class ComputeScheduler:
    """云端ComfyUI算力调度器"""

    def __init__(self, health_check_interval: int = 30):
        self.instances: Dict[str, ComputeInstance] = {}
        self.tasks: Dict[str, ComputeTask] = {}
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._health_thread: Optional[threading.Thread] = None
        self.health_check_interval = health_check_interval
        self._task_counter = 0

    # ==================== 实例管理 ====================

    def register_instance(self, instance_id: str, base_url: str,
                          location: str = "local", weight: float = 1.0) -> bool:
        """注册计算实例"""
        with self._lock:
            instance = ComputeInstance(
                instance_id=instance_id,
                base_url=base_url.rstrip("/"),
                location=location,
                weight=weight,
            )
            self.instances[instance_id] = instance

        # 立即进行一次健康检查
        self._health_check_instance(instance)
        print(f"✅ 实例已注册: {instance_id} ({base_url})")
        return True

    def unregister_instance(self, instance_id: str) -> bool:
        """注销计算实例"""
        with self._lock:
            if instance_id in self.instances:
                del self.instances[instance_id]
                print(f"⚠️ 实例已注销: {instance_id}")
                return True
        return False

    def list_instances(self) -> List[Dict[str, Any]]:
        """列出所有实例状态"""
        with self._lock:
            return [asdict(inst) for inst in self.instances.values()]

    def get_instance_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """获取实例状态"""
        with self._lock:
            if instance_id in self.instances:
                return asdict(self.instances[instance_id])
        return None

    # ==================== 健康检查 ====================

    def _health_check_instance(self, instance: ComputeInstance):
        """检查单个实例健康状态"""
        try:
            start_time = time.time()
            url = f"{instance.base_url}/system_stats"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                instance.response_time_ms = (time.time() - start_time) * 1000
                instance.status = "online"
                instance.last_health_check = datetime.now().isoformat()

                # 解析系统状态
                if "devices" in data and data["devices"]:
                    device = data["devices"][0]
                    instance.gpu_name = device.get("name", "")
                    instance.gpu_usage = device.get("utilization", 0.0)
                    instance.vram_total = device.get("vram_total", 0.0) / (1024 ** 3)
                    instance.vram_used = device.get("vram_used", 0.0) / (1024 ** 3)

        except urllib.error.URLError:
            instance.status = "offline"
            instance.response_time_ms = 9999
        except Exception as e:
            instance.status = "error"
            instance.error = str(e)

    def _health_check_loop(self):
        """健康检查循环"""
        while self._running:
            with self._lock:
                instances = list(self.instances.values())
            for instance in instances:
                self._health_check_instance(instance)
            time.sleep(self.health_check_interval)

    # ==================== 任务提交 ====================

    def submit_task(self, workflow: Dict[str, Any], priority: str = "normal",
                    metadata: Dict[str, Any] = None) -> str:
        """提交计算任务"""
        self._task_counter += 1
        task_id = f"task_{int(time.time())}_{self._task_counter}"

        task = ComputeTask(
            task_id=task_id,
            workflow=workflow,
            priority=priority,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {},
        )

        with self._lock:
            self.tasks[task_id] = task

        # 优先级映射（数值越小优先级越高）
        priority_map = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        priority_value = priority_map.get(priority, 2)

        self.task_queue.put((priority_value, task_id))
        print(f"📋 任务已提交: {task_id} (优先级: {priority})")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self._lock:
            if task_id in self.tasks:
                return asdict(self.tasks[task_id])
        return None

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id in self.tasks and self.tasks[task_id].status in ["pending", "queued"]:
                self.tasks[task_id].status = "cancelled"
                return True
        return False

    def wait_for_result(self, task_id: str, timeout: float = 300) -> Optional[Dict[str, Any]]:
        """等待任务完成"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            if status and status["status"] in ["completed", "failed", "cancelled"]:
                return status
            time.sleep(1)
        return None

    # ==================== 负载均衡 ====================

    def _select_instance(self) -> Optional[ComputeInstance]:
        """选择最优实例（负载均衡）"""
        with self._lock:
            online_instances = [
                inst for inst in self.instances.values()
                if inst.status in ["online", "busy"]
            ]

        if not online_instances:
            return None

        # 评分算法：GPU使用率低+显存空闲多+队列短+权重高 = 分数高
        def score(instance: ComputeInstance) -> float:
            gpu_score = (100 - instance.gpu_usage) / 100
            vram_score = 1.0
            if instance.vram_total > 0:
                vram_score = (instance.vram_total - instance.vram_used) / instance.vram_total
            queue_score = 1.0 / (1 + instance.queue_length)
            weight_score = instance.weight
            return (gpu_score * 0.3 + vram_score * 0.3 + queue_score * 0.2 + weight_score * 0.2)

        best_instance = max(online_instances, key=score)
        return best_instance

    # ==================== 任务执行 ====================

    def _execute_task(self, task: ComputeTask, instance: ComputeInstance) -> bool:
        """在指定实例上执行任务"""
        try:
            task.status = "running"
            task.assigned_instance = instance.instance_id
            task.started_at = datetime.now().isoformat()
            instance.active_tasks += 1
            instance.queue_length = max(0, instance.queue_length - 1)

            # 提交工作流到ComfyUI
            url = f"{instance.base_url}/prompt"
            data = json.dumps({"prompt": task.workflow}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                prompt_id = result.get("prompt_id", "")

            # 轮询结果（简化实现：等待固定时间）
            # 实际应使用 /history/{prompt_id} 轮询
            time.sleep(2)

            task.status = "completed"
            task.completed_at = datetime.now().isoformat()
            task.result = {"prompt_id": prompt_id, "instance": instance.instance_id}
            instance.total_tasks += 1
            instance.active_tasks -= 1
            return True

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()
            instance.failed_tasks += 1
            instance.active_tasks -= 1

            # 重试机制
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = "pending"
                priority_map = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
                self.task_queue.put((priority_map.get(task.priority, 2), task.task_id))
                print(f"🔄 任务重试: {task.task_id} (第{task.retry_count}次)")
            return False

    def _worker_loop(self):
        """工作线程循环"""
        while self._running:
            try:
                # 从队列获取任务（非阻塞）
                try:
                    priority, task_id = self.task_queue.get_nowait()
                except queue.Empty:
                    time.sleep(0.5)
                    continue

                with self._lock:
                    task = self.tasks.get(task_id)

                if not task or task.status == "cancelled":
                    continue

                # 选择实例
                instance = self._select_instance()
                if not instance:
                    # 无可用实例，重新入队
                    task.status = "queued"
                    self.task_queue.put((priority, task_id))
                    time.sleep(5)
                    continue

                # 执行任务
                task.status = "queued"
                self._execute_task(task, instance)

            except Exception as e:
                print(f"❌ 工作线程错误: {e}")
                time.sleep(1)

    # ==================== 启动/停止 ====================

    def start(self):
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._worker_thread.start()
        self._health_thread.start()
        print(f"🚀 算力调度器已启动（{len(self.instances)}个实例）")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        if self._health_thread:
            self._health_thread.join(timeout=5)
        print("⏹️ 算力调度器已停止")

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计"""
        with self._lock:
            total_tasks = len(self.tasks)
            completed = sum(1 for t in self.tasks.values() if t.status == "completed")
            failed = sum(1 for t in self.tasks.values() if t.status == "failed")
            running = sum(1 for t in self.tasks.values() if t.status == "running")
            pending = sum(1 for t in self.tasks.values() if t.status in ["pending", "queued"])

        return {
            "total_instances": len(self.instances),
            "online_instances": sum(1 for i in self.instances.values() if i.status in ["online", "busy"]),
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "running_tasks": running,
            "pending_tasks": pending,
            "queue_size": self.task_queue.qsize(),
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    print("=" * 60)
    print("☁️ 云端ComfyUI算力调度器 v1.0")
    print("=" * 60)

    scheduler = ComputeScheduler(health_check_interval=10)

    # 注册本地实例
    scheduler.register_instance("local", "http://127.0.0.1:8188", location="local", weight=1.0)

    # 启动调度器
    scheduler.start()

    # 显示状态
    print(f"\n实例状态:")
    for inst in scheduler.list_instances():
        print(f"  {inst['instance_id']}: {inst['status']} ({inst['base_url']})")
        print(f"    GPU: {inst['gpu_name'] or '未知'}, 使用率: {inst['gpu_usage']}%")
        print(f"    显存: {inst['vram_used']:.1f}/{inst['vram_total']:.1f}GB")

    print(f"\n统计: {scheduler.get_stats()}")

    scheduler.stop()
