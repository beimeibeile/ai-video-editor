"""
批量视频生产系统 v1.0
从CSV/JSON读取批量任务，逐个生成视频，跟踪进度和状态

使用方法：
    from batch_processor import BatchProcessor
    bp = BatchProcessor()
    results = bp.run_from_csv("tasks.csv")
    # 或
    results = bp.run_from_json("tasks.json")

CSV格式：
    topic,video_type,duration,template_id,project_name
    城市夜景探店,exploration,30,exploration_food,探店001
    美食教程,tutorial,45,tutorial_howto,教程001

JSON格式：
    [{"topic":"...","video_type":"exploration","duration":30,"template_id":"exploration_food"}]
"""
import os
import sys
import json
import csv
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

from cap_e2e_pipeline.pipeline_script_driver import ScriptDrivenPipeline
from cap_template_system import TemplateSystem


@dataclass
class BatchTask:
    """批量任务定义"""
    topic: str
    video_type: str = "exploration"
    duration: float = 30.0
    template_id: str = None
    project_name: str = None
    hook_effect: str = "wipe"
    status: str = "pending"  # pending/running/success/failed/skipped
    result: Dict[str, Any] = None
    error: str = None
    started_at: str = None
    finished_at: str = None
    elapsed_seconds: float = 0


class BatchProcessor:
    """批量视频生产处理器"""

    def __init__(self, output_dir: str = None, max_workers: int = 1):
        self.output_dir = output_dir or os.path.join(SKILL_ROOT, "batch_outputs")
        self.max_workers = max_workers  # 目前只支持串行（剪映工程不能并行）
        self.tasks: List[BatchTask] = []
        os.makedirs(self.output_dir, exist_ok=True)

    def load_from_csv(self, csv_path: str) -> List[BatchTask]:
        """从CSV加载任务列表"""
        tasks = []
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                task = BatchTask(
                    topic=row.get("topic", "").strip(),
                    video_type=row.get("video_type", "exploration").strip() or "exploration",
                    duration=float(row.get("duration", 30) or 30),
                    template_id=row.get("template_id", "").strip() or None,
                    project_name=row.get("project_name", "").strip() or None,
                    hook_effect=row.get("hook_effect", "wipe").strip() or "wipe",
                )
                if task.topic:
                    tasks.append(task)
        self.tasks = tasks
        print(f"✅ 从CSV加载 {len(tasks)} 个任务")
        return tasks

    def load_from_json(self, json_path: str) -> List[BatchTask]:
        """从JSON加载任务列表"""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tasks = []
        for item in data:
            task = BatchTask(
                topic=item.get("topic", ""),
                video_type=item.get("video_type", "exploration"),
                duration=float(item.get("duration", 30)),
                template_id=item.get("template_id"),
                project_name=item.get("project_name"),
                hook_effect=item.get("hook_effect", "wipe"),
            )
            if task.topic:
                tasks.append(task)
        self.tasks = tasks
        print(f"✅ 从JSON加载 {len(tasks)} 个任务")
        return tasks

    def run_single(self, task: BatchTask) -> BatchTask:
        """执行单个任务"""
        task.status = "running"
        task.started_at = datetime.now().isoformat()
        start_time = time.time()

        try:
            if task.project_name is None:
                task.project_name = f"batch_{int(time.time())}_{len(self.tasks)}"

            task_output = os.path.join(self.output_dir, task.project_name)
            os.makedirs(task_output, exist_ok=True)

            if task.template_id:
                # 使用模板
                ts = TemplateSystem(output_dir=task_output)
                result = ts.apply(
                    template_id=task.template_id,
                    topic=task.topic,
                    duration=task.duration,
                    project_name=task.project_name,
                )
            else:
                # 普通pipeline
                driver = ScriptDrivenPipeline(
                    project_dir=task_output,
                    output_dir=os.path.join(task_output, "outputs"),
                )
                result = driver.run(
                    topic=task.topic,
                    video_type=task.video_type,
                    duration=task.duration,
                    project_name=task.project_name,
                    hook_effect=task.hook_effect,
                )

            # 补充工程路径
            draft_path = os.path.join(
                r"C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft",
                task.project_name
            )
            if os.path.exists(draft_path):
                result["draft_path"] = draft_path

            task.result = {k: v for k, v in result.items() if k != "result"}
            task.status = "success"

        except Exception as e:
            import traceback
            task.status = "failed"
            task.error = f"{e}\n{traceback.format_exc()}"
            print(f"❌ 任务失败: {task.topic} - {e}")

        task.finished_at = datetime.now().isoformat()
        task.elapsed_seconds = round(time.time() - start_time, 1)
        return task

    def run_all(self) -> List[BatchTask]:
        """执行所有任务（串行）"""
        print(f"\n{'='*60}")
        print(f"🚀 批量生产开始：{len(self.tasks)} 个任务")
        print(f"{'='*60}")

        for i, task in enumerate(self.tasks, 1):
            print(f"\n[{i}/{len(self.tasks)}] {task.topic}")
            print(f"     类型:{task.video_type} 时长:{task.duration}s 模板:{task.template_id or '无'}")
            self.run_single(task)
            status_icon = "✅" if task.status == "success" else "❌"
            print(f"     {status_icon} {task.status} - {task.elapsed_seconds}s")

        # 生成报告
        self._save_report()

        # 统计
        success = sum(1 for t in self.tasks if t.status == "success")
        failed = sum(1 for t in self.tasks if t.status == "failed")
        total_time = sum(t.elapsed_seconds for t in self.tasks)

        print(f"\n{'='*60}")
        print(f"📊 批量生产完成")
        print(f"   成功: {success}/{len(self.tasks)}")
        print(f"   失败: {failed}/{len(self.tasks)}")
        print(f"   总耗时: {total_time:.1f}秒")
        print(f"   报告: {os.path.join(self.output_dir, 'batch_report.json')}")
        print(f"{'='*60}")

        return self.tasks

    def _save_report(self):
        """保存批量生产报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_tasks": len(self.tasks),
            "success_count": sum(1 for t in self.tasks if t.status == "success"),
            "failed_count": sum(1 for t in self.tasks if t.status == "failed"),
            "total_elapsed": sum(t.elapsed_seconds for t in self.tasks),
            "tasks": [asdict(t) for t in self.tasks],
        }
        report_path = os.path.join(self.output_dir, "batch_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        return report_path

    def run_from_csv(self, csv_path: str) -> List[BatchTask]:
        """从CSV加载并执行"""
        self.load_from_csv(csv_path)
        return self.run_all()

    def run_from_json(self, json_path: str) -> List[BatchTask]:
        """从JSON加载并执行"""
        self.load_from_json(json_path)
        return self.run_all()


if __name__ == "__main__":
    print("=" * 60)
    print("批量视频生产系统 v1.0")
    print("=" * 60)
    print("\n使用方法:")
    print("  1. 创建CSV文件，列：topic,video_type,duration,template_id,project_name")
    print("  2. python batch_processor.py --csv tasks.csv")
    print("  3. 或 python batch_processor.py --json tasks.json")
    print("\n示例CSV:")
    print("  topic,video_type,duration,template_id")
    print("  城市夜景探店,exploration,30,exploration_food")
    print("  Python入门教程,tutorial,45,tutorial_howto")
