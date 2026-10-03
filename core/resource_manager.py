"""
资源管理与自动清理模块 v1.0

解决问题：脚本执行完后ComfyUI模型仍占用显存/内存，Python进程不退出。

功能：
1. ComfyUI模型卸载（free API）
2. 显存/内存使用检测与报告
3. 上下文管理器（with语句自动清理）
4. 装饰器（函数执行完自动清理）
5. 子进程管理（确保子进程退出）

使用方法：
    from core.resource_manager import ResourceManager, auto_cleanup

    # 方式1：上下文管理器
    with ResourceManager() as rm:
        # 执行任务
        result = do_work()
    # 退出with块时自动清理

    # 方式2：装饰器
    @auto_cleanup
    def my_task():
        # 执行任务
        return result

    # 方式3：手动调用
    rm = ResourceManager()
    rm.free_comfyui_models()
    rm.cleanup()
"""

import os
import sys
import time
import signal
import json
import subprocess
import urllib.request
import urllib.error
from typing import Optional, Callable, Any
from contextlib import contextmanager
from functools import wraps

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


class ResourceManager:
    """资源管理器：跟踪并自动清理GPU/CPU资源"""

    def __init__(
        self,
        comfyui_url: str = "http://127.0.0.1:8188",
        auto_free_on_exit: bool = True,
        verbose: bool = True,
    ):
        """
        Args:
            comfyui_url: ComfyUI API地址
            auto_free_on_exit: 退出时是否自动卸载ComfyUI模型
            verbose: 是否打印详细信息
        """
        self.comfyui_url = comfyui_url.rstrip("/")
        self.auto_free_on_exit = auto_free_on_exit
        self.verbose = verbose
        self._child_processes = []
        self._start_time = time.time()
        self._cleaned = False

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [资源管理] {msg}")

    def register_child_process(self, proc: subprocess.Popen):
        """注册子进程，退出时自动终止"""
        self._child_processes.append(proc)

    def get_gpu_memory(self) -> Optional[dict]:
        """获取GPU显存使用情况"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                return {
                    "used_mb": int(parts[0].strip()),
                    "total_mb": int(parts[1].strip()),
                    "utilization": int(parts[2].strip()),
                }
        except Exception:
            pass
        return None

    def get_memory_usage(self) -> Optional[dict]:
        """获取当前进程内存使用情况"""
        if _PSUTIL_AVAILABLE:
            try:
                proc = psutil.Process(os.getpid())
                return {
                    "rss_mb": int(proc.memory_info().rss / 1024 / 1024),
                    "vms_mb": int(proc.memory_info().vms / 1024 / 1024),
                    "cpu_percent": proc.cpu_percent(),
                }
            except Exception:
                pass
        return None

    def print_status(self, label: str = "当前"):
        """打印资源使用状态"""
        gpu = self.get_gpu_memory()
        mem = self.get_memory_usage()
        elapsed = time.time() - self._start_time

        print(f"\n{'='*50}")
        print(f"  资源状态 - {label}")
        print(f"  运行时长: {elapsed:.1f}秒")
        if gpu:
            print(f"  GPU显存: {gpu['used_mb']}MB / {gpu['total_mb']}MB "
                  f"({gpu['used_mb']/gpu['total_mb']*100:.0f}%), 利用率{gpu['utilization']}%")
        if mem:
            print(f"  内存(RSS): {mem['rss_mb']}MB, CPU: {mem['cpu_percent']}%")
        print(f"{'='*50}\n")

    def _comfyui_post(self, endpoint: str, data: dict, timeout: int = 30) -> bool:
        """用urllib调用ComfyUI POST API"""
        url = f"{self.comfyui_url}/{endpoint}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except urllib.error.URLError as e:
            if "Connection refused" in str(e) or "WinError 10061" in str(e):
                self._log("ComfyUI未运行，跳过API调用")
            else:
                self._log(f"ComfyUI API调用失败: {e}")
            return False
        except Exception as e:
            self._log(f"ComfyUI API调用异常: {e}")
            return False

    def free_comfyui_models(self) -> bool:
        """
        调用ComfyUI free API卸载模型，释放显存

        Returns:
            bool: 是否成功
        """
        try:
            # 先中断队列中的任务
            self._comfyui_post("queue", {"clear": True}, timeout=5)

            # 卸载模型
            success = self._comfyui_post(
                "free",
                {"unload_models": True, "free_memory": True},
                timeout=30
            )
            if success:
                self._log("ComfyUI模型已卸载，显存已释放")
                time.sleep(2)
                return True
            else:
                self._log("ComfyUI卸载失败")
                return False
        except Exception as e:
            self._log(f"ComfyUI卸载异常: {e}")
            return False

    def terminate_child_processes(self):
        """终止所有注册的子进程"""
        for proc in self._child_processes:
            try:
                if proc.poll() is None:  # 还在运行
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    self._log(f"子进程已终止 (PID={proc.pid})")
            except Exception:
                pass
        self._child_processes.clear()

    def cleanup(self):
        """执行完整清理"""
        if self._cleaned:
            return

        self._log("开始资源清理...")

        # 1. 卸载ComfyUI模型
        if self.auto_free_on_exit:
            self.free_comfyui_models()

        # 2. 终止子进程
        self.terminate_child_processes()

        # 3. 强制垃圾回收
        import gc
        gc.collect()

        # 4. 打印清理后状态
        self.print_status("清理后")

        self._cleaned = True
        self._log("资源清理完成")

    def __enter__(self):
        self.print_status("开始")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False  # 不抑制异常


def auto_cleanup(func: Callable) -> Callable:
    """
    装饰器：函数执行完后自动清理资源

    使用方法：
        @auto_cleanup
        def my_task():
            # 执行任务
            return result
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        rm = ResourceManager(auto_free_on_exit=True, verbose=True)
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            rm.cleanup()
    return wrapper


@contextmanager
def managed_comfyui_task(
    comfyui_url: str = "http://127.0.0.1:8188",
    verbose: bool = True,
):
    """
    简化的ComfyUI任务上下文管理器

    使用方法：
        with managed_comfyui_task() as rm:
            # 执行ComfyUI任务
            pass
        # 自动卸载模型
    """
    rm = ResourceManager(comfyui_url=comfyui_url, verbose=verbose)
    rm.print_status("任务开始")
    try:
        yield rm
    finally:
        rm.cleanup()


def setup_signal_handlers():
    """
    设置信号处理器，确保Ctrl+C时也能清理资源

    注意：只能在主线程调用
    """
    def _signal_handler(signum, frame):
        print(f"\n  [资源管理] 收到信号 {signum}，正在清理...")
        # 尝试卸载ComfyUI模型
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8188/free",
                data=json.dumps({"unload_models": True}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass
        sys.exit(1)

    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except (ValueError, AttributeError):
        # 非主线程或不支持的平台
        pass


if __name__ == "__main__":
    print("=" * 50)
    print("  资源管理模块 v1.0 测试")
    print("=" * 50)

    # 测试1：状态检测
    rm = ResourceManager(verbose=True)
    rm.print_status("测试")

    # 测试2：ComfyUI模型卸载
    print("\n测试ComfyUI模型卸载...")
    success = rm.free_comfyui_models()
    print(f"卸载结果: {'成功' if success else '失败/跳过'}")

    # 测试3：上下文管理器
    print("\n测试上下文管理器...")
    with ResourceManager(verbose=True) as rm2:
        print("  执行任务中...")
        time.sleep(1)
    print("  已退出with块，资源应已清理")

    print("\n✅ 资源管理模块测试完成")
